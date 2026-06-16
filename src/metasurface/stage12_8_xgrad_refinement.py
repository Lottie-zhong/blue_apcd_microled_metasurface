from __future__ import annotations

import math, traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.apcd_diffraction import extract_fdtd_grating_orders
from metasurface.stage12_k6_fdtd import flt, read_csv_rows, write_csv_rows, build_model, normalize_order_rows, dominant_order, order_power, order_contrast
from metasurface.stage12_k6_layout import audit_geometry, find_source_plan_rows, j1_footprint

OUTPUT_DIR_NAME = "stage12_8_h500_lp_k6_xgrad_selectivity_refinement"
FORWARD_BINS = [0,60,120,180,240,300]
MAX_NEW_VARIANTS = 8
SHIFT_VALUES_NM = [-10.0,-5.0,5.0,10.0]
TARGET_ORDER = 1
EPS = 1e-12
BASELINE = {
    "variant_id":"variant_000_baseline","x_LP_target_plus1_power":0.35782382585849376,
    "y_LP_target_plus1_leakage":0.03070098955871727,"target_order_selectivity_ratio":11.655123531902342,
    "steering_angle_deg":10.0000000055,"x_LP_dominant_order":"+1","y_LP_dominant_leakage_order":"+2",
    "x_LP_order_contrast":4.4245556829,"total_transmission_selectivity_ratio":"not_validated","minimum_clearance_nm":20.0,"geometry_legal":True,
}
VARIANT_FIELDS = ["variant_id","variant_type","description","changed_bins","changed_indices","candidate_ids_by_bin","shift_nm_by_index","planned_fdtd_runs","status","notes"]
GEOM_FIELDS = ["variant_id","geometry_legal","minimum_clearance_nm","minimum_neighbor_clearance_nm","clearance_below_20nm","audit_notes"]
RUN_FIELDS = ["run_id","variant_id","polarization","run_required","gradient_axis","target_order","status","notes"]
RESULT_FIELDS = ["variant_id","run_id","polarization","fdtd_status","total_transmission","dominant_order_n","dominant_order_m","dominant_order_power","dominant_theta_deg","target_plus1_power","zero_order_power","minus1_order_power","order_contrast_plus1_vs_next","fsp_path","fsp_retained","diagnostics","notes"]
RANK_FIELDS = ["rank","variant_id","variant_type","x_LP_target_plus1_power","y_LP_target_plus1_leakage","target_order_selectivity_ratio","steering_angle_deg","x_LP_dominant_order","y_LP_dominant_leakage_order","x_LP_order_contrast","total_transmission_selectivity_ratio","minimum_clearance_nm","geometry_legal","hard_pass","preferred_pass","stretch_pass","improves_over_baseline","score"]
REJECT_FIELDS = ["variant_id","variant_type","reason","notes"]

@dataclass(frozen=True)
class Stage12_8Paths:
    strict_pool_csv: Path
    baseline_layout_csv: Path
    baseline_geometry_csv: Path
    baseline_results_csv: Path
    output_dir: Path
    fdtd_work_dir: Path

def bool_from(v): return str(v).strip().lower() in {"true","1","yes"}
def clone_rows(rows): return [dict(r) for r in rows]
def validate_same_bin_substitution(target_bin:int, candidate_row:dict[str,str])->bool:
    return int(float(candidate_row.get("bin_deg", candidate_row.get("phase_bin_deg", -999)))) == int(target_bin)
def enforce_candidate_limit(variants:list[dict], max_new:int=MAX_NEW_VARIANTS)->list[dict]:
    baseline=[v for v in variants if v["variant_id"]=="variant_000_baseline"]
    others=[v for v in variants if v["variant_id"]!="variant_000_baseline"]
    return baseline + others[:max_new]
def classify_pass(row:dict)->dict[str,bool]:
    x=flt(row.get("x_LP_target_plus1_power")); y=flt(row.get("y_LP_target_plus1_leakage")); ratio=flt(row.get("target_order_selectivity_ratio")); angle=flt(row.get("steering_angle_deg")); dom=str(row.get("x_LP_dominant_order")); legal=bool_from(row.get("geometry_legal", True))
    hard=legal and dom=="+1" and abs(angle-10.0)<=0.5 and x>=0.25 and y<=0.015 and ratio>=20
    pref=hard and x>=0.30 and y<=0.010 and ratio>=30
    stretch=hard and ratio>=50
    return {"hard_pass":hard,"preferred_pass":pref,"stretch_pass":stretch}
def metric_ratio(x:float,y:float)->float: return x/max(y,EPS)
def variant_score(x_power:float,y_leak:float,ratio:float)->float: return ratio + 10.0*x_power - 20.0*y_leak

def source_to_layout_row(base:dict[str,str], candidate:dict[str,str], source:dict[str,str])->dict[str,object]:
    row=dict(base); cx=flt(base["supercell_center_x_nm"]); cy=flt(base.get("supercell_center_y_nm"),0.0); j1w,j1h=j1_footprint(source)
    row.update({"candidate_id":candidate["candidate_id"],"source_stage":candidate.get("source_stage",""),"source_file":candidate.get("source_file",""),"source_plan_file":source.get("_source_plan_file",""),"source_plan_id":source.get("dimer_case_id") or source.get("dimer_patch_id") or source.get("candidate_id") or candidate["candidate_id"],"j1_candidate_id":source.get("j1_candidate_id",""),"j2_candidate_id":source.get("j2_candidate_id",""),"placement_type":source.get("placement_type",""),"swap_order":source.get("swap_order",""),"gap_nm":source.get("gap_nm",""),"local_offset_nm":source.get("local_offset_nm",""),"j1_shape_family":source.get("j1_shape_family",""),"j1_geometry_params":source.get("j1_geometry_params",""),"j1_center_x_nm":source.get("j1_center_x_nm",""),"j1_center_y_nm":source.get("j1_center_y_nm",""),"j1_abs_center_x_nm":cx+flt(source.get("j1_center_x_nm")),"j1_abs_center_y_nm":cy+flt(source.get("j1_center_y_nm")),"j1_footprint_x_nm":j1w,"j1_footprint_y_nm":j1h,"j2_length_nm":source.get("j2_length_nm",""),"j2_width_nm":source.get("j2_width_nm",""),"j2_rotation_deg":source.get("j2_rotation_deg",""),"j2_center_x_nm":source.get("j2_center_x_nm",""),"j2_center_y_nm":source.get("j2_center_y_nm",""),"j2_abs_center_x_nm":cx+flt(source.get("j2_center_x_nm")),"j2_abs_center_y_nm":cy+flt(source.get("j2_center_y_nm")),"j2_footprint_x_nm":flt(source.get("j2_length_nm")),"j2_footprint_y_nm":flt(source.get("j2_width_nm"))})
    return row

def shift_row_x(row:dict[str,object], dx:float)->None:
    for key in ("supercell_center_x_nm","j1_abs_center_x_nm","j2_abs_center_x_nm"):
        row[key]=flt(row[key])+dx

def audit_variant(layout_rows):
    first=layout_rows[0]; geom=audit_geometry(layout_rows, flt(first["dimer_pitch_x_nm"]), flt(first["p_y_nm"]), flt(first["supercell_period_lambda_nm"]))
    min_internal=min(flt(r["internal_clearance_nm"]) for r in geom); min_neighbor=min(flt(r["min_neighbor_clearance_nm"]) for r in geom); legal=all(bool_from(r["geometry_legal"]) for r in geom) and min_internal>=15 and min_neighbor>=15
    notes=[]
    if min_internal<20 or min_neighbor<20: notes.append("clearance_below_20nm")
    if not legal: notes.append("illegal_or_clearance_below_15nm")
    return geom,{"geometry_legal":legal,"minimum_clearance_nm":min_internal,"minimum_neighbor_clearance_nm":min_neighbor,"clearance_below_20nm":(min_internal<20 or min_neighbor<20),"audit_notes":";".join(notes) if notes else "ok"}

def top_same_bin_candidates(pool, bin_deg:int, baseline_id:str, count:int=1):
    rows=[r for r in pool if validate_same_bin_substitution(bin_deg,r) and r.get("candidate_id")!=baseline_id and bool_from(r.get("strict")) and abs(flt(r.get("phase_err_deg")))<=12 and flt(r.get("selected_x_power"))>=0.6]
    rows=sorted(rows,key=lambda r:(-flt(r.get("conversion_to_leakage_ratio")), flt(r.get("matrix_error")), abs(flt(r.get("phase_err_deg")))))
    return rows[:count]

def generate_variants(paths:Stage12_8Paths):
    baseline=read_csv_rows(paths.baseline_layout_csv); pool=read_csv_rows(paths.strict_pool_csv); rejected=[]; variants=[{"variant_id":"variant_000_baseline","variant_type":"baseline","description":"official Stage12-2 x-gradient baseline reference; no FDTD re-run","layout_rows":clone_rows(baseline),"changed_bins":"","changed_indices":"","candidate_ids_by_bin":";".join(f"{r['phase_bin_deg']}:{r['candidate_id']}" for r in baseline),"shift_nm_by_index":"","planned_fdtd_runs":0,"status":"reference","notes":"baseline metrics loaded from Stage12-2"}]
    next_id=1
    # same-bin substitutions around risk/weak bins
    for bin_deg in [240,180,120,300]:
        base_row=next(r for r in baseline if int(float(r["phase_bin_deg"]))==bin_deg); cands=top_same_bin_candidates(pool,bin_deg,base_row["candidate_id"],1)
        if not cands: continue
        cand=cands[0]
        try:
            source=find_source_plan_rows(Path.cwd(),[cand["candidate_id"]])[cand["candidate_id"]]
            layout=clone_rows(baseline); idx=next(i for i,r in enumerate(layout) if int(float(r["phase_bin_deg"]))==bin_deg); layout[idx]=source_to_layout_row(layout[idx],cand,source)
            _,audit=audit_variant(layout)
            vid=f"variant_{next_id:03d}_sub_bin{bin_deg}"; next_id+=1
            if audit["geometry_legal"]:
                variants.append({"variant_id":vid,"variant_type":"same_bin_substitution","description":f"replace bin {bin_deg} with {cand['candidate_id']}","layout_rows":layout,"changed_bins":str(bin_deg),"changed_indices":str(idx),"candidate_ids_by_bin":";".join(f"{r['phase_bin_deg']}:{r['candidate_id']}" for r in layout),"shift_nm_by_index":"","planned_fdtd_runs":2,"status":"planned","notes":audit["audit_notes"]})
            else: rejected.append({"variant_id":vid,"variant_type":"same_bin_substitution","reason":"geometry_illegal","notes":audit["audit_notes"]})
        except Exception as e:
            rejected.append({"variant_id":f"variant_{next_id:03d}_sub_bin{bin_deg}","variant_type":"same_bin_substitution","reason":"source_plan_unresolved","notes":str(e)[:500]}); next_id+=1
    # micro shifts for risk and 20nm-clearance bins
    for index in [4,2]:
        for dx in SHIFT_VALUES_NM:
            layout=clone_rows(baseline); shift_row_x(layout[index],dx); _,audit=audit_variant(layout); bin_deg=int(float(layout[index]["phase_bin_deg"])); vid=f"variant_{next_id:03d}_shift_i{index}_{dx:+.0f}nm"; next_id+=1
            if audit["geometry_legal"]:
                variants.append({"variant_id":vid,"variant_type":"x_micro_shift","description":f"shift dimer index {index} bin {bin_deg} by {dx:+.0f} nm along x","layout_rows":layout,"changed_bins":str(bin_deg),"changed_indices":str(index),"candidate_ids_by_bin":";".join(f"{r['phase_bin_deg']}:{r['candidate_id']}" for r in layout),"shift_nm_by_index":f"{index}:{dx:+.0f}","planned_fdtd_runs":2,"status":"planned","notes":audit["audit_notes"]})
            else: rejected.append({"variant_id":vid,"variant_type":"x_micro_shift","reason":"geometry_illegal","notes":audit["audit_notes"]})
    variants=enforce_candidate_limit(variants,MAX_NEW_VARIANTS)
    return variants,rejected

def build_run_matrix(variants):
    rows=[]
    for v in variants:
        if v["variant_id"]=="variant_000_baseline": continue
        for pol in ["x","y"]:
            rows.append({"run_id":f"{v['variant_id']}_{pol}","variant_id":v["variant_id"],"polarization":pol,"run_required":True,"gradient_axis":"x","target_order":"x-order +1","status":"planned","notes":"official x-gradient plane-wave scout"})
    return rows

def run_one(lumapi,runtime,variant,pol,paths):
    run_id=f"{variant['variant_id']}_{pol}"; fsp=paths.fdtd_work_dir/f"{run_id}.fsp"; paths.fdtd_work_dir.mkdir(parents=True,exist_ok=True); fdtd=None; diag=[]; orders=[]; status="failed"; note=""
    try:
        fdtd=lumapi.FDTD(hide=getattr(runtime,"hide_gui",True)); build_model(fdtd,variant["layout_rows"],pol); fdtd.save(str(fsp)); fdtd.close(); fdtd=None
        fdtd=lumapi.FDTD(hide=getattr(runtime,"hide_gui",True)); fdtd.load(str(fsp)); fdtd.run(); raw=extract_fdtd_grating_orders(fdtd,monitor_name="T",K=6,diagnostics=diag); orders=normalize_order_rows(raw,run_id,pol,flt(variant["layout_rows"][0]["lambda_nm"]),flt(variant["layout_rows"][0]["supercell_period_lambda_nm"])); status="ok"
    except Exception as e:
        note=f"{type(e).__name__}: {e}\n{''.join(traceback.format_exception(type(e),e,e.__traceback__)).strip()}"
    finally:
        if fdtd:
            try: fdtd.close()
            except Exception: pass
        if fsp.exists():
            try: fsp.unlink()
            except Exception as e: diag.append(f"failed_to_delete_fsp:{e}")
    if status!="ok" or not orders:
        return {"variant_id":variant["variant_id"],"run_id":run_id,"polarization":pol,"fdtd_status":status,"fsp_path":str(fsp),"fsp_retained":fsp.exists(),"diagnostics":" | ".join(diag),"notes":note[:2000]}
    dom=dominant_order(orders)
    return {"variant_id":variant["variant_id"],"run_id":run_id,"polarization":pol,"fdtd_status":status,"total_transmission":flt(dom.get("total_transmission")),"dominant_order_n":dom["order_n"],"dominant_order_m":dom["order_m"],"dominant_order_power":dom["order_power_source_norm"],"dominant_theta_deg":flt(dom.get("theta_deg")),"target_plus1_power":order_power(orders,1),"zero_order_power":order_power(orders,0),"minus1_order_power":order_power(orders,-1),"order_contrast_plus1_vs_next":order_contrast(orders,1),"fsp_path":str(fsp),"fsp_retained":fsp.exists(),"diagnostics":" | ".join(diag),"notes":note}

def summarize_variant(variant, geom_audit, xres, yres):
    x=flt(xres.get("target_plus1_power")); y=flt(yres.get("target_plus1_power")); ratio=metric_ratio(x,y); total_ratio=flt(xres.get("total_transmission"))/max(flt(yres.get("total_transmission")),EPS); row={"variant_id":variant["variant_id"],"variant_type":variant["variant_type"],"x_LP_target_plus1_power":x,"y_LP_target_plus1_leakage":y,"target_order_selectivity_ratio":ratio,"steering_angle_deg":flt(xres.get("dominant_theta_deg")),"x_LP_dominant_order":f"{int(float(xres.get('dominant_order_n',999))):+d}" if str(xres.get("fdtd_status"))=="ok" else "failed","y_LP_dominant_leakage_order":f"{int(float(yres.get('dominant_order_n',999))):+d}" if str(yres.get("fdtd_status"))=="ok" else "failed","x_LP_order_contrast":flt(xres.get("order_contrast_plus1_vs_next")),"total_transmission_selectivity_ratio":total_ratio,"minimum_clearance_nm":geom_audit["minimum_clearance_nm"],"geometry_legal":geom_audit["geometry_legal"],"score":variant_score(x,y,ratio)}
    row.update(classify_pass(row)); row["improves_over_baseline"]=ratio>BASELINE["target_order_selectivity_ratio"] and y<BASELINE["y_LP_target_plus1_leakage"]; return row

def baseline_rank_row():
    row={k:BASELINE[k] for k in BASELINE}; row["variant_type"]="baseline"; row["score"]=variant_score(row["x_LP_target_plus1_power"],row["y_LP_target_plus1_leakage"],row["target_order_selectivity_ratio"]); row.update(classify_pass(row)); row["improves_over_baseline"]=False; return row

def write_summaries(paths, ranked):
    best=ranked[0]; baseline=next(r for r in ranked if r["variant_id"]=="variant_000_baseline"); improved=bool(best["variant_id"]!="variant_000_baseline" and best["improves_over_baseline"])
    lines=["# Stage12-8 Best Variant Summary","",f"- Any variant improves over official baseline: {improved}.",f"- Best variant ID: {best['variant_id']}.",f"- Best target_order_selectivity_ratio: {best['target_order_selectivity_ratio']}.",f"- Best y-LP target +1 leakage: {best['y_LP_target_plus1_leakage']}.",f"- Best x-LP target +1 power: {best['x_LP_target_plus1_power']}.",f"- Hard pass: {best['hard_pass']}.",f"- Preferred pass: {best['preferred_pass']}.",f"- Stretch pass: {best['stretch_pass']}.",f"- Replace Stage12 official baseline in later freeze stage: {improved and best['hard_pass']}.",f"- Another refinement scout recommended: {not (improved and best['preferred_pass'])}.","- Boundary: still plane-wave only, not dipole-source validation.","- Boundary: no dipoles, no CP, no y-gradient, no H600/H700."]
    (paths.output_dir/"stage12_8_best_variant_summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    cmp=["# Stage12-8 Baseline vs Best Comparison","",f"| Metric | Baseline | Best ({best['variant_id']}) |","|---|---:|---:|",f"| x-LP +1 power | {baseline['x_LP_target_plus1_power']} | {best['x_LP_target_plus1_power']} |",f"| y-LP +1 leakage | {baseline['y_LP_target_plus1_leakage']} | {best['y_LP_target_plus1_leakage']} |",f"| selectivity ratio | {baseline['target_order_selectivity_ratio']} | {best['target_order_selectivity_ratio']} |",f"| hard pass | {baseline['hard_pass']} | {best['hard_pass']} |"]
    (paths.output_dir/"stage12_8_baseline_vs_best_comparison.md").write_text("\n".join(cmp)+"\n",encoding="utf-8")
    rec=["# Stage12-8 Next Recommendation","",("Freeze improved variant in Stage12-9 only after a focused confirmation run." if improved and best["hard_pass"] else "Do not replace the Stage12 official baseline yet."),"Run another targeted scout if stronger y-LP suppression is still required before Stage13 dipole-source / MicroLED coupling.","Keep the official x-gradient convention: no y-gradient, no CP branch, no H600/H700."]
    (paths.output_dir/"stage12_8_next_recommendation.md").write_text("\n".join(rec)+"\n",encoding="utf-8")

def run_stage12_8(paths, lumapi, runtime):
    paths.output_dir.mkdir(parents=True,exist_ok=True); variants,rejected=generate_variants(paths)
    plan_rows=[{k:v.get(k,"") for k in VARIANT_FIELDS} for v in variants]
    write_csv_rows(plan_rows,paths.output_dir/"stage12_8_candidate_variant_plan.csv",VARIANT_FIELDS)
    geom_rows=[]; geom_by_id={}
    for v in variants:
        _,ga=audit_variant(v["layout_rows"]); geom_by_id[v["variant_id"]]=ga; geom_rows.append({"variant_id":v["variant_id"],**ga})
    write_csv_rows(geom_rows,paths.output_dir/"stage12_8_candidate_geometry_audit.csv",GEOM_FIELDS)
    run_matrix=build_run_matrix(variants); write_csv_rows(run_matrix,paths.output_dir/"stage12_8_fdtd_run_matrix.csv",RUN_FIELDS)
    results=[]; rank=[baseline_rank_row()]
    for v in [vv for vv in variants if vv["variant_id"]!="variant_000_baseline"]:
        xres=run_one(lumapi,runtime,v,"x",paths); results.append(xres); write_csv_rows(results,paths.output_dir/"stage12_8_fdtd_results.csv",RESULT_FIELDS)
        yres=run_one(lumapi,runtime,v,"y",paths); results.append(yres); write_csv_rows(results,paths.output_dir/"stage12_8_fdtd_results.csv",RESULT_FIELDS)
        if xres.get("fdtd_status")=="ok" and yres.get("fdtd_status")=="ok": rank.append(summarize_variant(v,geom_by_id[v["variant_id"]],xres,yres))
        else: rejected.append({"variant_id":v["variant_id"],"variant_type":v["variant_type"],"reason":"fdtd_failed","notes":str(xres.get("notes",""))[:300]+str(yres.get("notes",""))[:300]})
    rank=sorted(rank,key=lambda r:(not r.get("hard_pass",False), -flt(r.get("score"))))
    for i,r in enumerate(rank,1): r["rank"]=i
    write_csv_rows(rank,paths.output_dir/"stage12_8_ranked_variants.csv",RANK_FIELDS); write_csv_rows(rejected,paths.output_dir/"stage12_8_failed_or_rejected_variants.csv",REJECT_FIELDS); write_summaries(paths,rank)
    best=rank[0]; return {"output_dir":str(paths.output_dir),"candidate_variants":len(variants),"fdtd_runs":len(run_matrix),"best_variant_id":best["variant_id"],"baseline_ratio":BASELINE["target_order_selectivity_ratio"],"best_ratio":best["target_order_selectivity_ratio"],"baseline_y_leakage":BASELINE["y_LP_target_plus1_leakage"],"best_y_leakage":best["y_LP_target_plus1_leakage"],"baseline_x_power":BASELINE["x_LP_target_plus1_power"],"best_x_power":best["x_LP_target_plus1_power"],"hard_pass":best["hard_pass"],"preferred_pass":best["preferred_pass"],"stretch_pass":best["stretch_pass"],"best_gui_fsp_generated":False}

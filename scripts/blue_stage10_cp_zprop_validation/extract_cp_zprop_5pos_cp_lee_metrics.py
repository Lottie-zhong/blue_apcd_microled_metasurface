from __future__ import annotations

import argparse, csv, json, math
from pathlib import Path
from typing import Any
import numpy as np
from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation/five_position_sweep")
FIELD_MONITOR = "top_field_monitor_zprop"
POWER_MONITOR = "top_power_monitor_zprop"
WAVELENGTH_NM = 450.0
DEFAULT_CONES = [10.0, 15.0, 20.0, 25.0, 30.0]

def parse_args():
    ap = argparse.ArgumentParser(description="Extract calibrated +z x-line CP and LEE-style metrics.")
    ap.add_argument("--runtime", default="configs/runtime.yaml")
    ap.add_argument("--output-dir", default=str(OUT_DIR))
    ap.add_argument("--grid-n", type=int, default=101)
    ap.add_argument("--cone-deg", type=float, nargs="*", default=DEFAULT_CONES)
    ap.add_argument("--show-gui", action="store_true")
    return ap.parse_args()

def write_csv(path: Path, rows: list[dict[str, Any]]):
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def read_plan(out_dir: Path):
    with (out_dir/"five_position_run_plan.csv").open("r", newline="", encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    return [r for r in rows if r.get("position_id")=="center" or str(r.get("position_id","")).startswith("x_")]

def mask_for(ux, uy, shape, cone):
    ux=np.asarray(ux,dtype=float).squeeze(); uy=np.asarray(uy,dtype=float).squeeze(); lim=math.sin(math.radians(cone))
    if ux.ndim==1 and uy.ndim==1: xx,yy=np.meshgrid(ux,uy,indexing="ij")
    else: xx,yy=np.broadcast_arrays(ux,uy)
    m=(xx**2+yy**2)<=lim**2
    try: return np.broadcast_to(m,shape)
    except Exception:
        return m.T if m.T.shape==shape else np.ones(shape,dtype=bool)

def extract_fields(fdtd, grid_n):
    vec=fdtd.farfieldvector3d(FIELD_MONITOR,1,grid_n,grid_n); arr=np.asarray(vec)
    if arr.shape[-1]>=3: ex,ey=arr[...,0],arr[...,1]
    elif arr.shape[0]>=3: ex,ey=arr[0,...],arr[1,...]
    else: raise ValueError(f"bad farfieldvector3d shape {arr.shape}")
    ux=np.asarray(fdtd.farfieldux(FIELD_MONITOR,1,grid_n,grid_n),dtype=float).squeeze()
    uy=np.asarray(fdtd.farfielduy(FIELD_MONITOR,1,grid_n,grid_n),dtype=float).squeeze()
    info={"farfieldvector3d_shape":list(arr.shape),"farfieldvector3d_complex":bool(np.iscomplexobj(arr)),"ux_shape":list(np.asarray(ux).shape),"uy_shape":list(np.asarray(uy).shape)}
    return np.asarray(ex,dtype=np.complex128).squeeze(), np.asarray(ey,dtype=np.complex128).squeeze(), ux, uy, info

def try_power(fdtd):
    top=src=None; top_note=src_note=""
    try: top=float(np.real(np.asarray(fdtd.transmission(POWER_MONITOR)).ravel()[0])); top_note="transmission(top_power_monitor_zprop)"
    except Exception as e: top_note=f"unavailable: {type(e).__name__}: {e}"
    try:
        freq=299792458.0/(WAVELENGTH_NM*1e-9); val=float(np.asarray(fdtd.sourcepower(freq),dtype=float).ravel()[0])
        if math.isfinite(val) and val>0: src=val; src_note="sourcepower(freq_450nm)"
        else: src_note="unavailable or nonpositive"
    except Exception as e: src_note=f"unavailable: {type(e).__name__}: {e}"
    return top, top_note, src, src_note

def extract_case(lumapi,runtime,row,out_dir,grid_n,cones,show_gui):
    case_id=row["case_id"]; fsp=out_dir/"_saved_fsp"/f"{case_id}.fsp"
    base={"case_id":case_id,"position_id":row["position_id"],"orientation":row["orientation"],"x_nm":row["x_nm"],"y_nm":row["y_nm"],"z_nm":row["z_nm"],"grid_n":grid_n,"result_fsp":str(fsp)}
    if not fsp.exists():
        return ([{**base,"cone_deg":c,"extraction_status":"missing_fsp","notes":"FSP not found"} for c in cones],[],{"case_id":case_id,"status":"missing_fsp"})
    fdtd=None
    try:
        fdtd=lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui); fdtd.load(str(fsp.resolve()))
        ex,ey,ux,uy,info=extract_fields(fdtd,grid_n); top,top_note,src,src_note=try_power(fdtd)
        er=(ex-1j*ey)/math.sqrt(2.0); el=(ex+1j*ey)/math.sqrt(2.0)
        cp=[]; lee=[]
        for cone in cones:
            m=mask_for(ux,uy,er.shape,cone).astype(bool); ir=float(np.sum(np.abs(er[m])**2)); il=float(np.sum(np.abs(el[m])**2)); p=ir+il
            metrics={"IR_cone":ir,"IL_cone":il,"DoCP_RminusL":(ir-il)/p if p else float("nan"),"DoCP_LminusR":(il-ir)/p if p else float("nan"),"total_cone_power":p,"L_fraction":il/p if p else float("nan"),"R_fraction":ir/p if p else float("nan")}
            cp.append({**base,"cone_deg":cone,**metrics,"extraction_status":"ok","monitor_names":f"{FIELD_MONITOR};{POWER_MONITOR}","E_components_used":"farfieldvector3d Ex/Ey for +z CP basis","notes":"cone mask from farfieldux/farfielduy"})
            lee.append({**base,"cone_deg":cone,"source_power":src if src else "","source_power_status":src_note,"top_power_T_if_available":top if top is not None else "","top_power_status":top_note,"P_cone_total":p,"L_output_cone_power":il,"R_output_cone_power":ir,"LEE_top":(top/src) if src and top is not None else "","LEE_cone":p/src if src else "","LEE_L_cone":il/src if src else "","LEE_R_cone":ir/src if src else "","normalization_status":"absolute_source_normalized" if src else "relative_extraction_power","notes":"API-normalized extraction metrics unless source normalization is independently audited."})
        return cp,lee,{"case_id":case_id,"status":"ok","array_info":info,"top_power_status":top_note,"source_power_status":src_note}
    except Exception as e:
        return ([{**base,"cone_deg":c,"extraction_status":"failed","notes":f"{type(e).__name__}: {e}"} for c in cones],[],{"case_id":case_id,"status":"failed","error":f"{type(e).__name__}: {e}"})
    finally:
        if fdtd:
            try: fdtd.close()
            except Exception: pass

def position_averages(cp_rows):
    ok=[r for r in cp_rows if r.get("extraction_status")=="ok"]; out=[]
    for pos,cone in sorted({(r["position_id"],float(r["cone_deg"])) for r in ok}):
        pair=[r for r in ok if r["position_id"]==pos and float(r["cone_deg"])==cone]
        if len({r["orientation"] for r in pair})!=2: continue
        ir=sum(float(r["IR_cone"]) for r in pair); il=sum(float(r["IL_cone"]) for r in pair); p=ir+il
        out.append({"position_id":pos,"cone_deg":cone,"included_cases":";".join(r["case_id"] for r in pair),"IR_total":ir,"IL_total":il,"P_total":p,"DoCP_total_RminusL":(ir-il)/p if p else float("nan"),"DoCP_total_LminusR":(il-ir)/p if p else float("nan"),"L_fraction_total":il/p if p else float("nan"),"R_fraction_total":ir/p if p else float("nan"),"notes":"Incoherent x/y dipole power sum only; no coherent field addition."})
    return out

def global_average(pos_rows):
    out=[]
    for cone in sorted({float(r["cone_deg"]) for r in pos_rows}):
        rows=[r for r in pos_rows if float(r["cone_deg"])==cone]; ir=sum(float(r["IR_total"]) for r in rows); il=sum(float(r["IL_total"]) for r in rows); p=ir+il
        out.append({"group_id":"available_complete_xline_position_average","cone_deg":cone,"included_positions":";".join(r["position_id"] for r in rows),"IR_5pos":ir,"IL_5pos":il,"P_5pos":p,"DoCP_5pos_RminusL":(ir-il)/p if p else float("nan"),"DoCP_5pos_LminusR":(il-ir)/p if p else float("nan"),"L_fraction_5pos":il/p if p else float("nan"),"R_fraction_5pos":ir/p if p else float("nan"),"calibrated_label":"L-output dominant" if p and il>ir else "R-output dominant" if p and ir>il else "balanced_or_unknown","notes":"Average over complete x-line positions only; incomplete until all x-line positions have x/y orientations."})
    return out

def write_reports(out_dir, plan, cp, pos, glob, lee):
    ok={r["case_id"] for r in cp if r.get("extraction_status")=="ok"}; complete={r["position_id"] for r in pos}; norm=any(r.get("normalization_status")=="absolute_source_normalized" for r in lee); off=float(plan[0].get("offset_nm",0)) if plan else float("nan")
    with (out_dir/"five_position_sweep_summary.md").open("w",encoding="utf-8") as f:
        print("# Calibrated +z x-line centerline dipole sweep summary\n",file=f)
        print("## English\n",file=f); print("This is an x-axis centerline dipole-position sweep, not a full x-y plane sweep. y is fixed at 0 nm. No DBR, no K=6, no +10 degree steering, no 41-position sweep, and no coherent x/y dipole field addition.\n",file=f)
        print(f"- offset q = {off:.6f} nm, quarter local pitch convention.",file=f); print(f"- planned x-line cases: {len(plan)}.",file=f); print(f"- extracted ok cases: {len(ok)}.",file=f); print(f"- complete x-line positions with both x/y orientations: {len(complete)} ({', '.join(sorted(complete)) if complete else 'none'}).",file=f); print(f"- sourcepower API available for extracted cases: {norm}; LEE-style values are API-normalized extraction metrics, not independently validated absolute LEE.",file=f); print("- calibrated label: negative DoCP_RminusL means L-output dominant.\n",file=f)
        print("### +/-20 degree complete-position averages\n",file=f); print("| position | DoCP_RminusL | L fraction | total cone power |",file=f); print("|---|---:|---:|---:|",file=f)
        for r in [r for r in pos if abs(float(r["cone_deg"])-20)<1e-9]: print(f"| {r['position_id']} | {float(r['DoCP_total_RminusL']):.6g} | {float(r['L_fraction_total']):.6g} | {float(r['P_total']):.6g} |",file=f)
        print("\n## 中文\n",file=f); print("这是 x 轴中心线偶极位置扫描，不是完整 x-y 平面扫描。y 固定为 0 nm。没有 DBR，没有 K=6，没有 +10° steering，没有 41-position 扫描，也没有对 x/y 偶极电场做相干叠加。\n",file=f)
        print(f"- 偏移 q = {off:.6f} nm，沿用 quarter local pitch 约定。",file=f); print(f"- 当前计划中的 x-line cases：{len(plan)}。",file=f); print(f"- 成功提取 cases：{len(ok)}。",file=f); print(f"- 同时具备 x/y 取向的完整 x-line 位置：{len(complete)}（{', '.join(sorted(complete)) if complete else '无'}）。",file=f); print(f"- 已提取 cases 的 sourcepower API 是否可用：{norm}；LEE-style 值是 API-normalized extraction metrics，不是独立验证过的 absolute LEE。",file=f)
    missing=[]
    for row in plan:
        if row["case_id"] not in ok:
            sts=[r for r in cp if r.get("case_id")==row["case_id"]]; status=sts[0].get("extraction_status","not_extracted") if sts else "not_extracted"; note=sts[0].get("notes","") if sts else ""; missing.append((row,status,note))
    with (out_dir/"five_position_sweep_gap_report.md").open("w",encoding="utf-8") as f:
        print("# x-line centerline sweep gap report\n",file=f); print("This is an x-axis centerline sweep only, not a full x-y plane sweep. y-offset cases are not part of the target plan.\n",file=f); print(f"- planned x-line metasurface cases: {len(plan)}",file=f); print(f"- extracted ok cases: {len(ok)}",file=f); print(f"- complete x-line positions with both x/y orientations: {len(complete)} ({', '.join(sorted(complete)) if complete else 'none'})",file=f); print("- bare reference: not run in this turn.\n",file=f); print("| case_id | position | orientation | status | note |",file=f); print("|---|---|---|---|---|",file=f)
        for row,status,note in missing: print(f"| {row['case_id']} | {row['position_id']} | {row['orientation']} | {status} | {str(note).replace('|','/')} |",file=f)

def write_bare_placeholder(out_dir, plan):
    write_csv(out_dir/"five_position_bare_reference_metrics.csv", [{"case_id":"BARE_"+r["case_id"],"position_id":r["position_id"],"orientation":r["orientation"],"normalization_status":"not_run","notes":"Bare reference not run in this x-line checkpoint."} for r in plan])

def main():
    args=parse_args(); out_dir=Path(args.output_dir); out_dir.mkdir(parents=True,exist_ok=True); plan=read_plan(out_dir); runtime=load_runtime_config(args.runtime); lumapi=import_lumapi(runtime)
    cp=[]; lee=[]; debug={"grid_n":args.grid_n,"cone_deg":args.cone_deg,"sweep_type":"x-axis centerline only","cases":[]}
    for row in plan:
        c,l,d=extract_case(lumapi,runtime,row,out_dir,args.grid_n,args.cone_deg,args.show_gui); cp+=c; lee+=l; debug["cases"].append(d)
    pos=position_averages(cp); glob=global_average(pos)
    write_csv(out_dir/"five_position_cp_metrics.csv",cp); write_csv(out_dir/"five_position_position_averages.csv",pos); write_csv(out_dir/"five_position_global_average.csv",glob); write_csv(out_dir/"five_position_lee_metrics.csv",lee); write_bare_placeholder(out_dir,plan)
    dbg=out_dir/"five_position_sweep_debug.json"; existing={}
    if dbg.exists():
        try: existing=json.loads(dbg.read_text(encoding="utf-8"))
        except Exception: existing={}
    existing["extraction"]=debug; dbg.write_text(json.dumps(existing,indent=2),encoding="utf-8")
    write_reports(out_dir,plan,cp,pos,glob,lee)
    print(json.dumps({"cp_rows":len(cp),"position_rows":len(pos),"global_rows":len(glob),"ok_cases":len({r['case_id'] for r in cp if r.get('extraction_status')=='ok'}),"summary":str(out_dir/"five_position_sweep_summary.md")},indent=2))
    return 0 if any(r.get("extraction_status")=="ok" for r in cp) else 1

if __name__ == "__main__":
    raise SystemExit(main())

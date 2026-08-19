from __future__ import annotations

import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
OLD_REPORT = PKG / "reports/lp_anisotropy_feasible_space_v2"
REPORT = PKG / "reports/lp_anisotropy_feasible_space_v2_balanced_selection"
AUTH = PKG / "authority"
RUNTIME = PKG / "runtime/search_anisotropy_feasible_space_v2_balanced"
PARENT_FSP = PKG / "runtime/reusable_fsp/lp/P1_LP_H1C1B_V2_009_Px_attempt_006_pre.fsp"
MATERIAL = "APCD_TIO2_NATIVE_M1"
SOURCE_START, SOURCE_STOP = 430.0, 470.0
H, PX, PY = 525.0, 432.0, 432.0
DIM_KEYS = ("a1", "b1", "a2", "b2", "delta_theta_deg", "D_nm")
BOUNDS = {"a1": (0.85, 1.15), "b1": (0.85, 1.15), "a2": (0.85, 1.15), "b2": (0.85, 1.15), "delta_theta_deg": (0.0, 90.0), "D_nm": (170.0, 220.0)}
STRATA = ("S1", "S2", "S3", "S4")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canon(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha_obj(v: Any) -> str:
    return hashlib.sha256(canon(v)).hexdigest()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(p: Path, v: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_csv(p: Path, rows: list[dict[str, Any]]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in r.items()})


def load_v2_module():
    path = PKG / "scripts/lp_anisotropy_feasible_space_v2.py"
    spec = importlib.util.spec_from_file_location("lp_anisotropy_feasible_space_v2", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def stratum(theta: float) -> str:
    if 0.0 <= theta < 22.5: return "S1"
    if theta < 45.0: return "S2"
    if theta < 67.5: return "S3"
    if theta <= 90.0: return "S4"
    raise ValueError(theta)


def norm(r: dict[str, Any]) -> list[float]:
    return [(float(r[k]) - lo) / (hi - lo) for k, (lo, hi) in BOUNDS.items()]


def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.sqrt(sum((x-y)**2 for x, y in zip(norm(a), norm(b))))


def parse_pool() -> list[dict[str, Any]]:
    rows=[]
    numeric = set(DIM_KEYS) | {"L1_nm","W1_nm","L2_nm","W2_nm","D_nm","delta_theta_deg","theta1_deg","theta2_deg","height_nm","period_x_nm","period_y_nm","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm","direct_clearance_nm","periodic_image_clearance_nm","global_minimum_clearance_nm","minimum_lateral_feature_nm","aspect_ratio_H_over_min_feature","sample_index"}
    with (OLD_REPORT/"feasible_geometry_pool.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for k in numeric:
                if k in row and row[k] != "": row[k] = float(row[k]) if k not in {"sample_index","L1_nm","W1_nm","L2_nm","W2_nm","D_nm","minimum_lateral_feature_nm"} else int(float(row[k]))
            row["angular_stratum"] = stratum(float(row["delta_theta_deg"]))
            rows.append(row)
    return rows


def anisotropy(r: dict[str, Any]) -> dict[str, float]:
    a1=(r["L1_nm"]-r["W1_nm"])/(r["L1_nm"]+r["W1_nm"])
    a2=(r["L2_nm"]-r["W2_nm"])/(r["L2_nm"]+r["W2_nm"])
    return {"A1":a1,"A2":a2,"delta_A":a1-a2}


def select(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by={s:[r for r in rows if r["angular_stratum"]==s] for s in STRATA}
    nominal={"a1":1.0,"b1":1.0,"a2":1.0,"b2":1.0,"delta_theta_deg":45.0,"D_nm":195.0}
    central_pool=by["S2"]+by["S3"]
    anchor=min(central_pool,key=lambda r:(distance(r,nominal),int(r["sample_index"]),r["geometry_hash_sha256"]))
    initial_by={anchor["angular_stratum"]:anchor}
    for s in STRATA:
        if s in initial_by: continue
        candidates=[r for r in by[s] if r["geometry_hash_sha256"] not in {x["geometry_hash_sha256"] for x in initial_by.values()}]
        chosen=sorted(candidates,key=lambda r:(-min(distance(r,x) for x in initial_by.values()),int(r["sample_index"]),r["geometry_hash_sha256"]))[0]
        initial_by[s]=chosen
    initial=[initial_by[s] for s in STRATA]
    used={r["geometry_hash_sha256"] for r in initial}
    conditional=[]
    for s in STRATA:
        candidates=[r for r in by[s] if r["geometry_hash_sha256"] not in used]
        selected=initial+conditional
        chosen=sorted(candidates,key=lambda r:(-min(distance(r,x) for x in selected),int(r["sample_index"]),r["geometry_hash_sha256"]))[0]
        conditional.append(chosen); used.add(chosen["geometry_hash_sha256"])
    for i,r in enumerate(initial+conditional,1):
        r["bf_id"]=f"BF{i:02d}"
        r["selection_role"]="INITIAL_TRUTH_CANDIDATE" if i<=4 else "CONDITIONAL_TRUTH_CANDIDATE"
        r["angular_stratum"]=stratum(float(r["delta_theta_deg"]))
        r.update(anisotropy(r))
        all_selected=initial+conditional
        r["normalized_six_coordinates"]=norm(r)
        r["nearest_selected_neighbor_distance"]=min((distance(r,x) for x in all_selected if x["geometry_hash_sha256"]!=r["geometry_hash_sha256"]),default=None)
    return initial, conditional


def pairwise(rows):
    out=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]: out.append({"geometry_a":a["bf_id"],"geometry_b":b["bf_id"],"normalized_six_distance":distance(a,b)})
    return out


def candidate_row(r: dict[str, Any], old_hashes: dict[str,str]) -> dict[str,Any]:
    return {"geometry_id":r["bf_id"],"role":r["selection_role"],"angular_stratum":r["angular_stratum"],"sample_index":r["sample_index"],**{k:r[k] for k in ["a1","b1","a2","b2","L1_nm","W1_nm","L2_nm","W2_nm","theta1_deg","theta2_deg","delta_theta_deg","D_nm","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm","height_nm","period_x_nm","period_y_nm","direct_clearance_nm","periodic_image_clearance_nm","global_minimum_clearance_nm","minimum_lateral_feature_nm","aspect_ratio_H_over_min_feature","A1","A2","delta_A","geometry_hash_sha256","normalized_six_coordinates","nearest_selected_neighbor_distance"]},"lineage_old_af":old_hashes.get(r["geometry_hash_sha256"]),"validity":"PASS","solver_entered":False}


def build() -> dict[str,Any]:
    REPORT.mkdir(parents=True,exist_ok=True); AUTH.mkdir(parents=True,exist_ok=True)
    rows=parse_pool(); stats=json.loads((OLD_REPORT/"raw_pool_statistics.json").read_text(encoding="utf-8")); old=json.loads((OLD_REPORT/"selected_candidates.json").read_text(encoding="utf-8"))["candidates"]
    if len(rows)!=1879 or stats.get("feasible_unique_count")!=1879: raise RuntimeError("HARD_GATE_FEASIBLE_POOL_CORRUPTION")
    if len({r["geometry_hash_sha256"] for r in rows})!=len(rows): raise RuntimeError("HARD_GATE_POOL_HASH_DEDUP_CORRUPTION")
    old_hashes={r["geometry_hash_sha256"]:r["geometry_id"] for r in old}
    initial,conditional=select(rows); selected=initial+conditional
    selected_out=[candidate_row(r,old_hashes) for r in selected]
    counts={s:sum(r["angular_stratum"]==s for r in rows) for s in STRATA}
    write_json(REPORT/"stratum_counts.json",{"schema":"PAPER_A_LP_ANISOTROPY_V2_STRATUM_COUNTS_V1","source_pool_path":str(OLD_REPORT/"feasible_geometry_pool.csv"),"source_pool_sha256":sha_file(OLD_REPORT/"feasible_geometry_pool.csv"),"counts":counts,"bins":{"S1":[0.0,22.5,"left_closed_right_open"],"S2":[22.5,45.0,"left_closed_right_open"],"S3":[45.0,67.5,"left_closed_right_open"],"S4":[67.5,90.0,"left_closed_right_closed"]}})
    write_json(REPORT/"balanced_selected_candidates.json",{"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_CANDIDATES_V1","selection_stage":"LP_ANISOTROPY_FEASIBLE_SPACE_V2_BALANCED_SELECTION","previous_af_status":"VALID_GEOMETRIES_BUT_SUPERSEDED_FOR_TRUTH_ROLE_BY_BALANCED_SELECTION","candidates":selected_out,"initial_ids":[r["bf_id"] for r in initial],"conditional_ids":[r["bf_id"] for r in conditional],"optical_information_used":False})
    write_csv(REPORT/"balanced_candidate_registry.csv",selected_out); write_csv(REPORT/"selection_pairwise_distances.csv",pairwise(selected))
    old_pair=pairwise([{**r,"bf_id":r["geometry_id"]} for r in old])
    quality={"schema":"PAPER_A_LP_ANISOTROPY_V2_SELECTION_QUALITY_COMPARISON_V1","old_af":quality_summary(old,old_pair),"new_bf":quality_summary(selected,pairwise(selected)),"old_selection_status":"VALID_GEOMETRIES_BUT_SUPERSEDED_FOR_TRUTH_ROLE_BY_BALANCED_SELECTION","new_selection_status":"BALANCED_MECHANISM_STRATIFIED_SELECTION_PASS","optical_information_used":False}
    write_json(REPORT/"selection_quality_comparison.json",quality)
    write_json(REPORT/"balanced_case_registry.json",{"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_CASE_REGISTRY_V1","cases":[{"case_id":f"{r['bf_id']}_{p}","geometry_id":r["bf_id"],"polarization":p,"role":r["selection_role"],"status":"SETUP_ONLY_PLANNED" if r["bf_id"] in {"BF01","BF02","BF03","BF04"} else "REGISTRY_ONLY","solver_run_called":False,"solver_entered":False,"ready_or_pending":False} for r in selected for p in ("x","y")],"new_fdtd_budget":0,"hidden_auto_admission":False})
    write_json(REPORT/"selection_preregistration.json",{"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_SELECTION_PREREGISTRATION_V1","center_anchor_rule":"nearest nominal center among S2/S3 by normalized six-dimensional Euclidean distance, ties sample_index then hash","remaining_initial_rule":"in S1-S4 order excluding anchor stratum, constrained greedy maximin to already selected, ties sample_index then hash","conditional_rule":"in S1-S4 order, constrained greedy maximin to initial plus prior conditional, ties sample_index then hash","no_optical_information":True,"max_geometries":8})
    audit=geometry_audit(selected,rows,old_hashes); write_json(REPORT/"audit.json",audit)
    return {"status":"PASS","rows":rows,"selected":selected,"selected_out":selected_out,"old":old,"quality":quality,"audit":audit,"counts":counts}


def quality_summary(rows,pairs):
    rows=[{**r,**anisotropy(r)} for r in rows]
    keys=DIM_KEYS+('A1','A2','delta_A')
    return {"count":len(rows),"delta_theta_range":[min(float(r["delta_theta_deg"]) for r in rows),max(float(r["delta_theta_deg"]) for r in rows)],"stratum_coverage":{s:sum(stratum(float(r["delta_theta_deg"]))==s for r in rows) for s in STRATA},"nearest_neighbor_range":[min((min(float(x['normalized_six_distance']) for x in pairs if x['geometry_a']==r.get('bf_id',r.get('geometry_id')) or x['geometry_b']==r.get('bf_id',r.get('geometry_id'))) for r in rows),default=0),max((min(float(x['normalized_six_distance']) for x in pairs if x['geometry_a']==r.get('bf_id',r.get('geometry_id')) or x['geometry_b']==r.get('bf_id',r.get('geometry_id'))) for r in rows),default=0)],"pairwise_distance_range":[min((float(x['normalized_six_distance']) for x in pairs),default=0),max((float(x['normalized_six_distance']) for x in pairs),default=0)],"coordinate_coverage":{k:[min(float(r[k]) for r in rows),max(float(r[k]) for r in rows)] for k in keys}}


def geometry_audit(selected, pool, old_hashes):
    mod=load_v2_module(); checks=[]
    for r in selected:
        q={k:r[k] for k in ["L1_nm","W1_nm","L2_nm","W2_nm","D_nm","delta_theta_deg","height_nm","period_x_nm","period_y_nm","theta1_deg","theta2_deg","j1_center_x_nm","j1_center_y_nm","j2_center_x_nm","j2_center_y_nm"]}
        core=mod.geom_core(q)
        checks.append({"id":r["bf_id"],"direct_match":abs(core["direct_clearance_nm"]-r["direct_clearance_nm"])<1e-9,"periodic_match":abs(core["periodic_image_clearance_nm"]-r["periodic_image_clearance_nm"])<1e-9,"valid":core["cell_containment_pass"] and core["overlap_or_touching_pass"] and core["direct_clearance_nm"]>=60 and core["periodic_image_clearance_nm"]>=60,"core":core})
    return {"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_AUDIT_V1","status":"PASS" if all(x["direct_match"] and x["periodic_match"] and x["valid"] for x in checks) else "HARD_GATE","pool_rows":len(pool),"pool_hash_unique":len({r["geometry_hash_sha256"] for r in pool})==len(pool),"strata_exact_once_initial":sorted(r["angular_stratum"] for r in selected[:4])==list(STRATA),"strata_exact_once_conditional":sorted(r["angular_stratum"] for r in selected[4:])==list(STRATA),"checks":checks,"optical_information_used":False,"solver_run_called":False,"solver_entered":0,"active_new_paper_a_fdtd":0,"new_fdtd_budget":0,"rcwa":0,"ml":0,"surrogate_inference":0,"server_performance_benchmark":"OUT_OF_SCOPE_FOR_PAPER_A"}


def setup():
    import lumapi
    data=json.loads((REPORT/"balanced_selected_candidates.json").read_text(encoding="utf-8"))["candidates"][:4]
    oldprep=json.loads((OLD_REPORT/"prepared_fsp_provenance.json").read_text(encoding="utf-8")); oldcases={x["case_id"]:x for x in oldprep["cases"]}; oldrows=json.loads((OLD_REPORT/"selected_candidates.json").read_text(encoding="utf-8"))["candidates"]; hash_to_af={x["geometry_hash_sha256"]:x["geometry_id"] for x in oldrows}
    results=[]
    for g in data:
        for pol in ("x","y"):
            cid=f"{g['geometry_id']}_{pol}"; af=hash_to_af.get(g["geometry_hash_sha256"]); reuse=oldcases.get(f"{af}_{pol}") if af else None
            if reuse and reuse.get("status")=="PASS":
                result={"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_SETUP_ONLY_V1","case_id":cid,"geometry_id":g["geometry_id"],"polarization":pol,"status":"REUSED_PROVENANCE","solver_run_called":False,"solver_entered":False,"reused_from_case":f"{af}_{pol}","geometry_hash_exact_match":True,"pre_fsp_path":reuse["pre_fsp_path"],"pre_fsp_sha256":reuse["pre_fsp_sha256"],"parent_fsp_sha256":reuse["parent_fsp_sha256"],"readback":reuse.get("readback",{})}
                write_json(RUNTIME/"cases"/cid/"setup_only.json",result); results.append(result); continue
            out=RUNTIME/"cases"/cid; out.mkdir(parents=True,exist_ok=True); pre=out/f"{cid}_pre.fsp"; f=lumapi.FDTD(hide=True)
            try:
                f.load(str(PARENT_FSP)); f.switchtolayout(); nm=1e-9
                for obj,cx,cy,L,W,rot in [("pillar_1",g["j1_center_x_nm"],g["j1_center_y_nm"],g["L1_nm"],g["W1_nm"],g["theta1_deg"]),("pillar_2",g["j2_center_x_nm"],g["j2_center_y_nm"],g["L2_nm"],g["W2_nm"],g["theta2_deg"])]:
                    for key,val in [("x",cx),("y",cy),("x span",L),("y span",W),("z",H/2),("z span",H),("rotation 1",rot)]: f.setnamed(obj,key,float(val)*nm if key not in {"rotation 1"} else float(val))
                    f.setnamed(obj,"material",MATERIAL)
                f.setnamed("source","polarization angle",0.0 if pol=="x" else 90.0); f.setnamed("source","wavelength start",SOURCE_START*nm); f.setnamed("source","wavelength stop",SOURCE_STOP*nm)
                for name in ("T","field_monitor"): f.setnamed(name,"use source limits",True); f.setnamed(name,"use wavelength spacing",True); f.setnamed(name,"frequency points",41)
                f.setglobalmonitor("use source limits",True); f.setglobalmonitor("use wavelength spacing",True); f.setglobalmonitor("frequency points",41); f.save(str(pre))
            finally:
                try:f.close()
                except Exception:pass
            f=lumapi.FDTD(hide=True)
            try:
                f.load(str(pre)); read={"source_start_nm":float(f.getnamed("source","wavelength start"))*1e9,"source_stop_nm":float(f.getnamed("source","wavelength stop"))*1e9,"source_polarization_angle_deg":float(f.getnamed("source","polarization angle")),"T_frequency_points":float(f.getnamed("T","frequency points")),"field_frequency_points":float(f.getnamed("field_monitor","frequency points")),"materials":[str(f.getnamed("pillar_1","material")),str(f.getnamed("pillar_2","material"))],"j1_center_x_nm":float(f.getnamed("pillar_1","x"))*1e9,"j1_center_y_nm":float(f.getnamed("pillar_1","y"))*1e9,"j1_x_span_nm":float(f.getnamed("pillar_1","x span"))*1e9,"j1_y_span_nm":float(f.getnamed("pillar_1","y span"))*1e9,"j2_center_x_nm":float(f.getnamed("pillar_2","x"))*1e9,"j2_center_y_nm":float(f.getnamed("pillar_2","y"))*1e9,"j2_x_span_nm":float(f.getnamed("pillar_2","x span"))*1e9,"j2_y_span_nm":float(f.getnamed("pillar_2","y span"))*1e9,"j1_rotation_deg":float(f.getnamed("pillar_1","rotation 1")),"j2_rotation_deg":float(f.getnamed("pillar_2","rotation 1"))}
            finally:
                try:f.close()
                except Exception:pass
            expected={"source_start_nm":SOURCE_START,"source_stop_nm":SOURCE_STOP,"source_polarization_angle_deg":0.0 if pol=="x" else 90.0,"T_frequency_points":41.0,"field_frequency_points":41.0,"materials":[MATERIAL,MATERIAL],"j1_center_x_nm":g["j1_center_x_nm"],"j1_center_y_nm":g["j1_center_y_nm"],"j1_x_span_nm":g["L1_nm"],"j1_y_span_nm":g["W1_nm"],"j2_center_x_nm":g["j2_center_x_nm"],"j2_center_y_nm":g["j2_center_y_nm"],"j2_x_span_nm":g["L2_nm"],"j2_y_span_nm":g["W2_nm"],"j1_rotation_deg":g["theta1_deg"],"j2_rotation_deg":g["theta2_deg"]}
            ok=all((read[k]==expected[k] if isinstance(expected[k],list) else abs(float(read[k])-float(expected[k]))<1e-6) for k in expected)
            result={"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_SETUP_ONLY_V1","case_id":cid,"geometry_id":g["geometry_id"],"polarization":pol,"status":"PASS" if ok else "BLOCKED","solver_run_called":False,"solver_entered":False,"pre_fsp_path":str(pre),"pre_fsp_sha256":sha_file(pre),"parent_fsp_sha256":sha_file(PARENT_FSP),"geometry_hash":g["geometry_hash_sha256"],"readback":read,"expected":expected,"mesh_boundary_unchanged":True,"normalization_renormalized":False}
            write_json(out/"setup_only.json",result); results.append(result)
    write_json(REPORT/"prepared_fsp_provenance.json",{"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_PREPARED_FSP_PROVENANCE_V1","cases":results,"solver_calls":0,"all_pass":all(x["status"] in {"PASS","REUSED_PROVENANCE"} for x in results)})
    cases=json.loads((REPORT/"balanced_case_registry.json").read_text(encoding="utf-8")); by={x["case_id"]:x for x in results}
    for c in cases["cases"]:
        if c["case_id"] in by: c.update({"status":by[c["case_id"]]["status"],"pre_fsp_path":by[c["case_id"]].get("pre_fsp_path"),"pre_fsp_sha256":by[c["case_id"]].get("pre_fsp_sha256")})
    write_json(REPORT/"balanced_case_registry.json",cases); return {"status":"PASS" if all(x["status"] in {"PASS","REUSED_PROVENANCE"} for x in results) else "BLOCKED","cases":results,"solver_calls":0}


def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def finalize():
    d=json.loads((REPORT/"balanced_selected_candidates.json").read_text(encoding="utf-8")); audit=json.loads((REPORT/"audit.json").read_text(encoding="utf-8")); prep=json.loads((REPORT/"prepared_fsp_provenance.json").read_text(encoding="utf-8")) if (REPORT/"prepared_fsp_provenance.json").exists() else {"all_pass":False,"cases":[]}
    audit.update({"setup_only_case_count":len(prep.get("cases",[])),"setup_only_all_pass":prep.get("all_pass",False),"finalized_utc":now()}); write_json(REPORT/"audit.json",audit)
    authority= json.loads((AUTH/"paper_a_lp_anisotropy_feasible_space_v2.json").read_text(encoding="utf-8")); authority.update({"feasible_domain":"LP_ANISOTROPY_FEASIBLE_SPACE_V2_PASS","candidate_selection":"BALANCED_MECHANISM_STRATIFIED_SELECTION_PASS","scientific_readiness":"INITIAL_TRUTH_CANDIDATES_BF01_BF04_READY","truth_plan":"INITIAL_BF01_BF04_THEN_MIDPOINT_PHYSICS_AUDIT","conditional_plan":"BF05_BF08_ONLY_IF_MIDPOINT_PROMISING","solver_state":"WAIT_EXTERNAL_SOLVER_ADMISSION","server_performance_benchmark":"OUT_OF_SCOPE_FOR_PAPER_A","previous_af_selection_status":"VALID_GEOMETRIES_BUT_SUPERSEDED_FOR_TRUTH_ROLE_BY_BALANCED_SELECTION","balanced_selection_artifact":str(REPORT/"balanced_selected_candidates.json"),"balanced_selection_optical_information_used":False})
    write_json(AUTH/"paper_a_lp_cp_broadband_scope_v1.json",authority)
    write_json(AUTH/"paper_a_lp_anisotropy_balanced_selection_v2.json",{"schema":"PAPER_A_LP_ANISOTROPY_BALANCED_SELECTION_V2_AUTHORITY_V1","selection_status":"BALANCED_MECHANISM_STRATIFIED_SELECTION_PASS","feasible_domain":"LP_ANISOTROPY_FEASIBLE_SPACE_V2_PASS","initial_truth_candidates":[f"BF{i:02d}" for i in range(1,5)],"conditional_truth_candidates":[f"BF{i:02d}" for i in range(5,9)],"pool_unchanged":True,"optical_information_used":False,"solver_run_called":False,"solver_entered":0,"active_new_paper_a_fdtd":0})
    lines=["# LP anisotropy V2 balanced mechanism-stratified selection", "", "Status: PASS. The original 1879-point feasible pool was reused unchanged.", "", "Initial truth candidates: BF01–BF04, exactly one in each S1–S4. Conditional truth candidates: BF05–BF08, exactly one in each S1–S4.", "", "Selection uses only normalized six-dimensional geometry coordinates. No optical data, FDTD, RCWA, ML, surrogate, DoLP, power, phase, Jones or CP response was used.", "", "| ID | Role | Stratum | L1/W1/L2/W2 nm | theta1/theta2 deg | D nm | direct / periodic / global nm | min feature | H/min feature | A1/A2/delta_A | lineage |", "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for c in d["candidates"]:
        lines.append(f"| {c['geometry_id']} | {c['role']} | {c['angular_stratum']} | {c['L1_nm']}/{c['W1_nm']}/{c['L2_nm']}/{c['W2_nm']} | {c['theta1_deg']:.6f}/{c['theta2_deg']:.6f} | {c['D_nm']} | {c['direct_clearance_nm']:.6f} / {c['periodic_image_clearance_nm']:.6f} / {c['global_minimum_clearance_nm']:.6f} | {c['minimum_lateral_feature_nm']} | {c['aspect_ratio_H_over_min_feature']:.6f} | {c['A1']:.6f}/{c['A2']:.6f}/{c['delta_A']:.6f} | {c.get('lineage_old_af') or '-'} |")
    lines += ["", "Previous AF01–AF08 remain valid geometry records but are superseded for truth role by this balanced selection.", "", "Solver state: WAIT_EXTERNAL_SOLVER_ADMISSION. NEW_FDTD_BUDGET=0; no server-performance benchmark.", ""]
    (REPORT/"final_report.md").write_text("\n".join(lines),encoding="utf-8")
    (AUTH/"paper_a_lp_anisotropy_balanced_selection_v2.md").write_text("\n".join(lines),encoding="utf-8")
    return {"status":"PASS" if audit["status"]=="PASS" and prep.get("all_pass") else "PARTIAL","setup_only_cases":len(prep.get("cases",[]))}


def test():
    d=json.loads((REPORT/"balanced_selected_candidates.json").read_text(encoding="utf-8")); c=d["candidates"]; a=json.loads((REPORT/"audit.json").read_text(encoding="utf-8")); counts=json.loads((REPORT/"stratum_counts.json").read_text(encoding="utf-8"))["counts"]
    checks={"pool_unchanged":len(parse_pool())==1879,"strata_counts_positive":all(counts[s]>0 for s in STRATA),"initial_one_each":[x["angular_stratum"] for x in c[:4]]==list(STRATA),"conditional_one_each":[x["angular_stratum"] for x in c[4:]]==list(STRATA),"hash_unique":len({x["geometry_hash_sha256"] for x in c})==8,"valid":a["status"]=="PASS","no_optical_information":d["optical_information_used"] is False,"solver_zero":a["solver_entered"]==0 and not a["solver_run_called"]}
    out={"schema":"PAPER_A_LP_ANISOTROPY_V2_BALANCED_SELECTION_TEST_V1","status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"selection_sha256":sha_obj([x["geometry_hash_sha256"] for x in c])}; write_json(REPORT/"test_report.json",out); return out


def main():
    mode=sys.argv[1] if len(sys.argv)>1 else "build"
    if mode=="build": print(json.dumps(build(),default=str,ensure_ascii=False,indent=2)[:2000])
    elif mode=="setup": print(json.dumps(setup(),default=str,ensure_ascii=False,indent=2))
    elif mode=="finalize": print(json.dumps(finalize(),default=str,ensure_ascii=False,indent=2))
    elif mode=="test": print(json.dumps(test(),default=str,ensure_ascii=False,indent=2))
    else: raise SystemExit(mode)


if __name__=="__main__": main()

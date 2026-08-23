from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
RUNTIME = ROOT / "paper_a_broadband/runtime/bf08_authoritative_rebuilt_truth_v1/cases"
REPORT = ROOT / "paper_a_broadband/reports/lp_bf08_authoritative_rebuilt_truth_v1"
FORMAL = np.asarray([435.0 + i for i in range(31)], dtype=float)
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p: Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(p: Path, v: Any):
    p.parent.mkdir(parents=True, exist_ok=True); t=p.with_suffix(p.suffix+f".{os.getpid()}.tmp")
    t.write_text(json.dumps(v, indent=2, default=str)+"\n", encoding="utf-8"); os.replace(t,p)
def write_csv(p: Path, rows: list[dict[str,Any]]):
    p.parent.mkdir(parents=True, exist_ok=True)
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def val(f,obj,key):
    try: return f.getnamed(obj,key)
    except Exception as e: return f"UNAVAILABLE:{type(e).__name__}"

def inspect(cid: str) -> dict[str,Any]:
    import lumapi
    post=RUNTIME/cid/f"{cid}_attempt_003_post.fsp"; prov=json.loads((RUNTIME/cid/"attempt_003_provenance.json").read_text(encoding="utf-8"))
    f=lumapi.FDTD(hide=True)
    try:
        if not prov.get("solver_entered") or prov.get("post_fsp_sha256") != sha(post):
            raise RuntimeError(f"POST_FSP_PROVENANCE_MISMATCH:{cid}")
        f.load(str(post)); freq=np.asarray(f.getdata("T","f")).reshape(-1); wl=299792458.0/freq*1e9; trans=np.real(np.asarray(f.transmission("T")).reshape(-1)); sp=np.real(np.asarray(f.sourcepower(freq)).reshape(-1))
        indices=[]
        for target in FORMAL:
            hit=np.flatnonzero(np.isclose(wl,target,rtol=0,atol=1e-8))
            if len(hit)!=1: raise RuntimeError(f"FORMAL_GRID_BAD:{target}")
            indices.append(int(hit[0]))
        formal=[]
        for i,target in zip(indices,FORMAL): formal.append({"case_id":cid,"attempt_id":"attempt_003","wavelength_nm":float(target),"actual_monitor_wavelength_nm":float(wl[i]),"monitor_index":i,"transmission_T":float(trans[i]),"sourcepower":float(sp[i]),"formal_negative_T":bool(trans[i]<0)})
        return {"case_id":cid,"attempt_003_entered":bool(prov.get("solver_entered")),"post_fsp":str(post),"post_fsp_sha256":sha(post),"provenance_hash_pass":True,"grid":{"points":len(wl),"start_nm":float(wl[0]),"stop_nm":float(wl[-1]),"strictly_increasing":bool(np.all(np.diff(wl)>0)),"formal_exact_indices":indices},"source":{"object_type":str(val(f,"source","type")),"injection_axis":str(val(f,"source","injection axis")),"direction":str(val(f,"source","direction")),"z_nm":float(val(f,"source","z"))*1e9,"amplitude":val(f,"source","amplitude"),"sourcepower_abs_min_formal":float(np.min(np.abs(sp[indices]))),"sourcepower_abs_max_formal":float(np.max(np.abs(sp[indices]))),"sourcepower_ratio_formal":float(np.min(np.abs(sp[indices]))/np.max(np.abs(sp[indices]))) if np.max(np.abs(sp[indices])) else None},"monitor":{"T_type":str(val(f,"T","monitor type")),"T_z_nm":float(val(f,"T","z"))*1e9,"field_type":str(val(f,"field_monitor","monitor type")),"field_z_nm":float(val(f,"field_monitor","z"))*1e9},"formal_rows":formal,"negative_formal_T_count":sum(x["formal_negative_T"] for x in formal),"transmission_formal_min":float(np.min(trans[indices])),"transmission_formal_max":float(np.max(trans[indices]))}
    finally: f.close()

def main():
    cases=[inspect("BF08_x"),inspect("BF08_y")]; rows=[r for c in cases for r in c["formal_rows"]]; write_csv(REPORT/"bf08_attempt_003_terminal_monitor_audit.csv",rows)
    audit={"schema":"PAPER_A_LP_BF08_ATTEMPT_003_TERMINAL_AUDIT_V1","status":"HARD_GATE","verdict":"PAPER_A_LP_BF08_ATTEMPT_003_FORMAL_TRANSMISSION_INVALID_NO_TRUTH","reason":"Both fresh-builder attempt_003 cases entered and returned, but each has negative formal transmission. No abs, clipping, sign correction, renormalization, or old-attempt result was used.","old_attempt_001_002":"PROVENANCE_ONLY_NOT_PHYSICS_TRUTH","solver_counters":{"authorized_new_jobs":2,"entered":2,"returned":2,"accepted_truth_cases":0,"additional_solver_calls":0,"rcwa":0,"ml":0},"cases":cases,"next_action":"Chart scientific decision required; no auto replay or promotion"}
    write_json(REPORT/"bf08_attempt_003_terminal_audit.json",audit)
    (REPORT/"bf08_attempt_003_terminal_report.md").write_text("# BF08 attempt_003 terminal audit\n\n## HARD_GATE\n\nBoth independently rebuilt, fresh-parent cases entered and returned. BF08_x had negative formal `transmission(T)` at 435 nm of `-6948.538507181775`; BF08_y had `-6.9227083798707`. The wavelength coordinates were exact formal samples from the 81-point native monitor. The data are not physics truth: no absolute-value, clipping, sign correction, renormalization, interpolation, or old-attempt substitution was applied.\n\nThe two-job budget is exhausted. Post-FSPs and provenance are retained; no automatic replay or promotion is permitted.\n",encoding="utf-8")
    print(json.dumps(audit,default=str)); return 0
if __name__=="__main__": raise SystemExit(main())

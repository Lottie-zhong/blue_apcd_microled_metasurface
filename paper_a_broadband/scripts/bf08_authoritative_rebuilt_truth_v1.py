from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
AUTHORITY = ROOT / "paper_a_broadband/authority/paper_a_lp_bf08_authoritative_rebuilt_truth_v1.json"
RUNTIME = ROOT / "paper_a_broadband/runtime/bf08_authoritative_rebuilt_truth_v1"
REPORT = ROOT / "paper_a_broadband/reports/lp_bf08_authoritative_rebuilt_truth_v1"
SCHEDULER_PATH = ROOT / "paper_a_broadband/templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
LEGACY = ROOT / "scripts/lp_legacy_h500_sixbin_formal_replay_450_v1.py"
BUILDER_RUNTIME = ROOT / "paper_a_broadband/runtime/bf08_authoritative_builder_reconstruction_v1/cases"
TASK = "PAPER_A_LP_BF08_AUTHORITATIVE_REBUILT_TRUTH_V1"
BRANCH = "work/paper-a-lp-cp-broadband-v1"
FORMAL = np.asarray([435.0 + i for i in range(31)], dtype=float)
PROCESSES, THREADS = 4, 1
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_obj(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def write_json(p: Path, v: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
    t.write_text(json.dumps(v, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(t, p)


def write_csv(p: Path, rows: list[dict[str, Any]]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{path}")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def read_auth() -> dict[str, Any]:
    a = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    if a.get("attempt_id") != "attempt_003" or a.get("physical_budget", {}).get("max_fdtd_jobs") != 2:
        raise RuntimeError("AUTHORITY_BUDGET_CONFLICT")
    return a


def casedir(cid: str) -> Path:
    return RUNTIME / "cases" / cid


def state(cid: str, **update: Any) -> None:
    p = casedir(cid) / "state.json"; old = {}
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
    old.update(update); old["updated_utc"] = now(); write_json(p, old)


def expected(cid: str) -> dict[str, Any]:
    a = read_auth()["physics_contract"]
    return {"source_start_nm": 430.0, "source_stop_nm": 470.0, "pol_deg": 0.0 if cid.endswith("_x") else 90.0,
            "T_points": 81, "field_points": 81, "geometry_nm": a["geometry_nm"], "material": a["material"],
            "sim_time_s": 5e-12, "auto_shutoff_min": 1e-7}


def get(f, obj: str, prop: str) -> Any:
    return f.getnamed(obj, prop)


def readback(f, cid: str) -> dict[str, Any]:
    e = expected(cid); nm = 1e-9
    got = {
        "source_start_nm": float(get(f, "source", "wavelength start")) / nm,
        "source_stop_nm": float(get(f, "source", "wavelength stop")) / nm,
        "pol_deg": float(get(f, "source", "polarization angle")),
        "T_points": int(round(float(get(f, "T", "frequency points")))),
        "field_points": int(round(float(get(f, "field_monitor", "frequency points")))),
        "pillar_1": {"x_nm": float(get(f,"pillar_1","x"))/nm, "y_nm": float(get(f,"pillar_1","y"))/nm, "L_nm": float(get(f,"pillar_1","x span"))/nm, "W_nm": float(get(f,"pillar_1","y span"))/nm, "H_nm": float(get(f,"pillar_1","z span"))/nm, "theta_deg": float(get(f,"pillar_1","rotation 1")), "material": str(get(f,"pillar_1","material"))},
        "pillar_2": {"x_nm": float(get(f,"pillar_2","x"))/nm, "y_nm": float(get(f,"pillar_2","y"))/nm, "L_nm": float(get(f,"pillar_2","x span"))/nm, "W_nm": float(get(f,"pillar_2","y span"))/nm, "H_nm": float(get(f,"pillar_2","z span"))/nm, "theta_deg": float(get(f,"pillar_2","rotation 1")), "material": str(get(f,"pillar_2","material"))},
        "sim_time_s": float(f.getnamed("FDTD", "simulation time")), "auto_shutoff_min": float(f.getnamed("FDTD", "auto shutoff min")),
        "x_span_nm": float(get(f,"FDTD","x span"))/nm, "y_span_nm": float(get(f,"FDTD","y span"))/nm,
        "x_bc": str(get(f,"FDTD","x min bc")), "y_bc": str(get(f,"FDTD","y min bc")), "z_bc": str(get(f,"FDTD","z min bc")),
    }
    g=e["geometry_nm"]
    checks = [abs(got["source_start_nm"]-e["source_start_nm"])<1e-8, abs(got["source_stop_nm"]-e["source_stop_nm"])<1e-8, abs(got["pol_deg"]-e["pol_deg"])<1e-8, got["T_points"]==81, got["field_points"]==81,
              abs(got["pillar_1"]["L_nm"]-g["L1"])<1e-8, abs(got["pillar_1"]["W_nm"]-g["W1"])<1e-8, abs(got["pillar_2"]["L_nm"]-g["L2"])<1e-8, abs(got["pillar_2"]["W_nm"]-g["W2"])<1e-8,
              abs(got["pillar_1"]["theta_deg"]-g["theta1_deg"])<1e-8, abs(got["pillar_2"]["theta_deg"]-g["theta2_deg"])<1e-8,
              abs(got["pillar_1"]["y_nm"]-g["center_1_nm"][1])<1e-8, abs(got["pillar_2"]["y_nm"]-g["center_2_nm"][1])<1e-8,
              got["pillar_1"]["material"]==e["material"], got["pillar_2"]["material"]==e["material"], abs(got["sim_time_s"]-e["sim_time_s"])<1e-15, got["auto_shutoff_min"]<=e["auto_shutoff_min"]]
    return {"pass": bool(all(checks)), "expected": e, "readback": got}


def prepare(cid: str) -> dict[str, Any]:
    import lumapi
    src = BUILDER_RUNTIME / cid / f"{cid}_authoritative_rebuilt_pre.fsp"
    dst = casedir(cid) / f"{cid}_attempt_003_pre.fsp"; dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists(): raise RuntimeError(f"FRESH_BUILDER_PREFSP_MISSING:{src}")
    if dst.exists():
        raise RuntimeError(f"ATTEMPT003_PREEXISTS_NO_OVERWRITE:{dst}")
    shutil.copy2(src, dst)
    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(dst)); gate=readback(f,cid)
    finally: f.close()
    result={"schema":"PAPER_A_LP_BF08_ATTEMPT_003_SETUP_V1","case_id":cid,"attempt_id":"attempt_003","status":"PASS" if gate["pass"] else "HARD_GATE","solver_entered":False,"solver_run_called":False,"fresh_builder_source_fsp":str(src),"fresh_builder_source_sha256":sha_file(src),"attempt_003_pre_fsp":str(dst),"attempt_003_pre_sha256":sha_file(dst),"copy_hash_equal":sha_file(src)==sha_file(dst),"gate":gate,"timestamp_utc":now()}
    if not result["copy_hash_equal"]: result["status"]="HARD_GATE_COPY_HASH"
    write_json(casedir(cid)/"setup_only.json",result); state(cid,case_id=cid,status="SETUP_PASS" if result["status"]=="PASS" else result["status"],solver_entered=False)
    return result


def formal_indices(wl: np.ndarray) -> list[int]:
    out=[]
    for target in FORMAL:
        hit=np.flatnonzero(np.isclose(wl,target,rtol=0,atol=1e-8))
        if len(hit)!=1: raise RuntimeError(f"FORMAL_WAVELENGTH_NOT_EXACT:{target}:{wl.tolist()}")
        out.append(int(hit[0]))
    return out


def extract(f, cid: str) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    low=module(LEGACY,"bf08_attempt003_low")
    freq=np.asarray(f.getdata("T","f")).reshape(-1); wl=299792458.0/freq*1e9
    t=np.real(np.asarray(f.transmission("T")).reshape(-1))
    ff=np.asarray(f.getdata("field_monitor","f")).reshape(-1)
    if len(freq)!=81 or len(t)!=81 or len(ff)!=81: raise RuntimeError(f"NATIVE_MONITOR_LENGTH:{len(freq)}:{len(t)}:{len(ff)}")
    if not np.allclose(ff,freq,rtol=1e-12,atol=1e-3): raise RuntimeError("T_FIELD_FREQUENCY_MISMATCH")
    if not np.all(np.diff(wl)>0): raise RuntimeError("MONITOR_WAVELENGTH_ORDERING_INVALID")
    ind=formal_indices(wl)
    x,y,ex,ey,grid=low.base.b.f1.grid_plane(f,float(t[0])); ex=np.asarray(ex).squeeze(); ey=np.asarray(ey).squeeze()
    if ex.ndim==2: ex=ex[:,:,None]; ey=ey[:,:,None]
    if ex.shape[-1]!=81 or ey.shape[-1]!=81: raise RuntimeError(f"FIELD_SPECTRAL_LENGTH:{ex.shape}:{ey.shape}")
    sp=np.asarray(f.sourcepower(freq)).reshape(-1)
    rows=[]
    for i,target in zip(ind,FORMAL):
        if t[i]<0: raise RuntimeError(f"NEGATIVE_FORMAL_TRANSMISSION:{target}:{t[i]}")
        rawx=low.base.b.f1.periodic_weighted(x,y,ex[:,:,i],grid["x_periodic_duplicate_endpoint"],grid["y_periodic_duplicate_endpoint"])
        rawy=low.base.b.f1.periodic_weighted(x,y,ey[:,:,i],grid["x_periodic_duplicate_endpoint"],grid["y_periodic_duplicate_endpoint"])
        nx,ny=low.base.b.f1.normalize_pair(rawx,rawy,float(t[i]))
        rows.append({"case_id":cid,"attempt_id":"attempt_003","wavelength_nm":float(target),"actual_monitor_wavelength_nm":float(wl[i]),"monitor_index":i,"source_T":float(t[i]),"sourcepower":float(np.real(sp[i])),"raw_weighted_Ex_real":float(rawx.real),"raw_weighted_Ex_imag":float(rawx.imag),"raw_weighted_Ey_real":float(rawy.real),"raw_weighted_Ey_imag":float(rawy.imag),"weighted_Ex_real":float(nx.real),"weighted_Ex_imag":float(nx.imag),"weighted_Ey_real":float(ny.real),"weighted_Ey_imag":float(ny.imag),"selected_power":float(abs(nx)**2+abs(ny)**2),"no_interpolation":True,"no_abs_or_clipping":True})
    diag={"native_points":81,"native_wavelength_start_nm":float(wl[0]),"native_wavelength_stop_nm":float(wl[-1]),"formal_indices":ind,"formal_count":len(rows),"formal_exact_match":True,"sourcepower_abs_min":float(np.min(np.abs(sp[ind]))),"sourcepower_abs_max":float(np.max(np.abs(sp[ind]))),"sourcepower_min_max_ratio":float(np.min(np.abs(sp[ind]))/np.max(np.abs(sp[ind]))) if np.max(np.abs(sp[ind])) else None}
    return rows,diag


def execute(cid: str) -> dict[str,Any]:
    import lumapi
    setup=json.loads((casedir(cid)/"setup_only.json").read_text(encoding="utf-8"))
    if setup.get("status")!="PASS": raise RuntimeError("SETUP_GATE_NOT_PASS")
    pre=Path(setup["attempt_003_pre_fsp"]); prov={"schema":"PAPER_A_LP_BF08_ATTEMPT_003_PROVENANCE_V1","case_id":cid,"attempt_id":"attempt_003","task_id":TASK,"status":"WAITING","solver_entered":False,"solver_run_called":False,"pre_fsp":str(pre),"pre_fsp_sha256":sha_file(pre),"fresh_builder_source_sha256":setup["fresh_builder_source_sha256"],"old_attempts":"PROVENANCE_ONLY_NOT_PHYSICS_TRUTH_NOT_PARENT_FSP","physical_contract_sha256":sha_obj(read_auth()["physics_contract"]),"mpi_processes":PROCESSES,"threads":THREADS,"created_utc":now()}
    pp=casedir(cid)/"attempt_003_provenance.json"; write_json(pp,prov); state(cid,case_id=cid,status="WAITING",solver_entered=False)
    lease=None; f=None
    try:
        sched=module(SCHEDULER_PATH,"bf08_attempt003_scheduler"); scheduler=sched.GlobalSlotScheduler(SLOT_REGISTRY)
        lease=scheduler.acquire_wait(branch=BRANCH,worktree=str(ROOT),task_id=TASK,case_uid=cid,pid=os.getpid(),metadata={"task_class":"PAPER_A_LP_BF08_ATTEMPT003","attempt_id":"attempt_003","fresh_builder_parent":True},timeout_s=21600.0,poll_s=30.0)
        prov.update({"status":"SLOT_ACQUIRED","slot_id":lease.slot_id,"admission_snapshot":lease.record.get("admission_snapshot")}); write_json(pp,prov)
        f=lumapi.FDTD(hide=True); f.load(str(pre)); gate=readback(f,cid); prov["pre_entry_readback"]=gate
        if not gate["pass"]: prov["status"]="HARD_GATE_PREFSP_READBACK"; return prov
        f.setresource("FDTD",1,"processes",str(PROCESSES))
        entered=now(); lease.mark_solver_entered(entered); prov.update({"solver_entered":True,"solver_run_called":True,"entered_utc":entered,"status":"ENTERED"}); write_json(pp,prov); state(cid,status="RUNNING",solver_entered=True,entered_utc=entered,slot_id=lease.slot_id,controller_pid=os.getpid())
        f.run(); returned=now(); post=casedir(cid)/f"{cid}_attempt_003_post.fsp"; f.save(str(post)); prov.update({"status":"RETURNED","returned_utc":returned,"post_fsp":str(post),"post_fsp_sha256":sha_file(post)}); write_json(pp,prov); lease.release("SOLVER_RETURNED",returned); lease=None; state(cid,status="RETURNED",solver_entered=True,returned_utc=returned)
        rows,diag=extract(f,cid); write_csv(casedir(cid)/"formal_spectra.csv",rows)
        checkpoint={"schema":"PAPER_A_LP_BF08_ATTEMPT_003_CHECKPOINT_V1","status":"ACCEPTED","case_id":cid,"attempt_id":"attempt_003","solver_entered":True,"rows":rows,"extraction":diag,"pre_fsp_sha256":prov["pre_fsp_sha256"],"post_fsp_sha256":prov["post_fsp_sha256"]}; cp=casedir(cid)/"checkpoint.json"; write_json(cp,checkpoint)
        prov.update({"status":"ACCEPTED","checkpoint":str(cp),"checkpoint_sha256":sha_file(cp),"rows":len(rows),"extraction":diag}); state(cid,status="COMPLETED",solver_entered=True,checkpoint=str(cp)); return prov
    except Exception as exc:
        prov.update({"status":"FAILED","error":f"{type(exc).__name__}:{exc}","traceback":traceback.format_exc(),"no_auto_replay":bool(prov.get("solver_entered"))}); state(cid,status="FAILED",solver_entered=bool(prov.get("solver_entered")),error=prov["error"]); return prov
    finally:
        if lease is not None:
            try: lease.release("FAILED_ENTERED" if prov.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception as exc: prov["lease_release_error"]=str(exc)
        if f is not None:
            try: f.close()
            except Exception: pass
        write_json(pp,prov)


def postprocess() -> dict[str,Any]:
    cps=[]
    for cid in ("BF08_x","BF08_y"):
        p=casedir(cid)/"checkpoint.json"
        if not p.exists(): raise RuntimeError(f"CHECKPOINT_MISSING:{cid}")
        cp=json.loads(p.read_text(encoding="utf-8"))
        if cp.get("status")!="ACCEPTED" or cp.get("attempt_id")!="attempt_003": raise RuntimeError(f"CHECKPOINT_NOT_AUTHORITATIVE:{cid}")
        cps.append(cp)
    bx={r["wavelength_nm"]:r for r in cps[0]["rows"]}; by={r["wavelength_nm"]:r for r in cps[1]["rows"]}; spec=[]
    for wl in FORMAL:
        x,y=bx[float(wl)],by[float(wl)]; J=np.asarray([[complex(x["weighted_Ex_real"],x["weighted_Ex_imag"]),complex(y["weighted_Ex_real"],y["weighted_Ex_imag"])],[complex(x["weighted_Ey_real"],x["weighted_Ey_imag"]),complex(y["weighted_Ey_real"],y["weighted_Ey_imag"])]])
        C=0.5*J@J.conj().T; s0=float(np.trace(C).real); s1=float((C[0,0]-C[1,1]).real); s2=float(2*C[0,1].real); s3=float(-2*C[0,1].imag); dolp=float(np.hypot(s1,s2)/s0) if s0>0 else float("nan")
        spec.append({"wavelength_nm":float(wl),"S0":s0,"S1":s1,"S2":s2,"S3":s3,"DoLP":dolp,"total_power":0.5*s0,"useful_lp_power":0.5*float(np.hypot(s1,s2))})
    write_csv(REPORT/"bf08_attempt_003_full_jones_spectra.csv",spec)
    summary={"schema":"PAPER_A_LP_BF08_ATTEMPT_003_TRUTH_V1","status":"PASS","verdict":"BF08_AUTHORITATIVE_TRUTH_AVAILABLE_NO_AUTOMATIC_PROMOTION","truth_source":"attempt_003_only","old_attempt_001_002_used_as_physics_truth":False,"formal_points":31,"wavelength_range_nm":[435.0,465.0],"DoLP_mean":float(np.mean([r["DoLP"] for r in spec])),"DoLP_worst":float(np.min([r["DoLP"] for r in spec])),"useful_power_mean":float(np.mean([r["useful_lp_power"] for r in spec])),"useful_power_worst":float(np.min([r["useful_lp_power"] for r in spec])),"anchor_450":next(r for r in spec if r["wavelength_nm"]==450.0),"no_automatic_promotion":True}
    write_json(REPORT/"bf08_attempt_003_truth_summary.json",summary); return summary


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["prepare","run","postprocess"],required=True); ap.add_argument("--case",choices=["BF08_x","BF08_y"]); args=ap.parse_args(); read_auth()
    if args.mode in ("prepare","run") and not args.case: ap.error("--case required")
    if args.mode=="prepare": result=prepare(args.case)
    elif args.mode=="run": result=execute(args.case)
    else: result=postprocess()
    print(json.dumps(result,ensure_ascii=False,default=str)); return 0 if result.get("status") in ("PASS","ACCEPTED") else 2

if __name__=="__main__": raise SystemExit(main())

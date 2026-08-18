from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
REPORT = ROOT / "paper_a_broadband/reports/lp_anisotropy_expanded_search_v1"
RUNTIME = ROOT / "paper_a_broadband/runtime/search_anisotropy_v1"
DOE_PATH = ROOT / "paper_a_broadband/configs/anisotropy_expanded_doe_v1.json"
PARENT_FSP = ROOT / "paper_a_broadband/runtime/reusable_fsp/lp/P1_LP_H1C1B_V2_009_Px_attempt_006_pre.fsp"
PREV_RUNNER = ROOT / "paper_a_broadband/scripts/lp_new_geometry_search_runner_v1.py"
SCHEDULER_PATH = ROOT / "paper_a_broadband/templates/lp_fulljones/apcd_global_fdtd_slot_v1.py"
SLOT_REGISTRY = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
LEGACY_EXTRACTOR = ROOT / "scripts/lp_legacy_h500_sixbin_formal_replay_450_v1.py"
BRANCH = "work/paper-a-lp-cp-broadband-v1"
WORKTREE = str(ROOT)
TASK_ID = "PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_V1"
GRID = [435.0 + i for i in range(31)]
NATIVE_GRID = [430.0 + i for i in range(41)]
SOURCE_START, SOURCE_STOP = 430.0, 470.0
MDC_FWHM = (438.409, 457.191)
MATERIAL = "APCD_TIO2_NATIVE_M1"
PROCESSES, THREADS = 4, 1
PLANNING_ONLY = True

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def write_json(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(x, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, p)
def append_jsonl(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f: f.write(json.dumps(x, ensure_ascii=False, default=str) + "\n")
def write_csv(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    tmp=p.with_suffix(p.suffix+f".{os.getpid()}.tmp")
    with tmp.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields or ["status"],extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    os.replace(tmp,p)


def load_previous():
    spec=importlib.util.spec_from_file_location("lp_new_geometry_search_runner_v1", PREV_RUNNER)
    if spec is None or spec.loader is None: raise RuntimeError("PREVIOUS_RUNNER_IMPORT_FAILED")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.ROOT=ROOT; mod.REPORT=REPORT; mod.RUNTIME=RUNTIME; mod.DOE_PATH=DOE_PATH
    mod.PARENT_FSP=PARENT_FSP; mod.SLOT_REGISTRY=SLOT_REGISTRY; mod.SCHEDULER_PATH=SCHEDULER_PATH
    mod.LEGACY_EXTRACTOR=LEGACY_EXTRACTOR; mod.BRANCH=BRANCH; mod.WORKTREE=WORKTREE; mod.TASK_ID=TASK_ID
    mod.GRID=GRID; mod.NATIVE_GRID=NATIVE_GRID; mod.SOURCE_START=SOURCE_START; mod.SOURCE_STOP=SOURCE_STOP
    mod.MATERIAL=MATERIAL; mod.PROCESSES=PROCESSES; mod.THREADS=THREADS
    return mod


PREV = load_previous()


def load_doe():
    d=json.loads(DOE_PATH.read_text(encoding="utf-8"))
    if d.get("schema") != "PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_DOE_V1": raise RuntimeError("HARD_GATE_DOE_SCHEMA")
    if len(d.get("geometries",[])) != 8 or d.get("solver_calls") != 0: raise RuntimeError("HARD_GATE_DOE_SOLVER_CONTAMINATION")
    return d


PREV.load_doe=load_doe


def case_dir(cid): return RUNTIME / "cases" / cid
def case_state(cid): return case_dir(cid) / "state.json"


def scheduler_snapshot():
    raw=PREV.load_module(SCHEDULER_PATH,"anisotropy_scheduler_snapshot").live_job_snapshot()
    return {"timestamp_utc":raw.get("timestamp_utc"),"global_active_jobs":raw.get("global_active_jobs"),"active_fdtd_jobs":raw.get("active_fdtd_jobs"),"active_rcwa_jobs":raw.get("active_rcwa_jobs"),"unknown_solver_jobs":raw.get("unknown_solver_jobs",[]),"jobs":[{"branch":j.get("branch"),"case_uid":j.get("case_uid"),"solver_type":j.get("solver_type"),"status":j.get("status")} for j in raw.get("jobs",[])]}


def preflight():
    d=load_doe(); parent_ok=PARENT_FSP.exists()
    rot=ROOT/"reports/stage_h1e3a_j1_rotation_audit/h1e3a_route_decision.json"
    audit={"schema":"PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_PREFLIGHT_V1","timestamp_utc":now(),"status":"PASS","solver_entered":False,"solver_run_called":False,"doe_freeze_sha256":d.get("freeze_sha256"),"geometry_count":len(d["geometries"]),"all_geometry_valid":all(g.get("validity",{}).get("geometry_valid") for g in d["geometries"]),"parent_fsp":{"path":str(PARENT_FSP),"exists":parent_ok,"sha256":PREV.sha_file(PARENT_FSP) if parent_ok else None},"rotation_audit":{"path":str(rot),"exists":rot.exists(),"common_phase_lever":False,"treatment":"theta1=0, theta2=delta_theta"},"source_monitor":{"source_span_nm":[430.,470.],"formal_window_nm":[435.,465.],"formal_points":31,"native_monitor_points":41,"spacing_nm":1.0,"no_historical_renormalization":True},"material_contract":{"material":MATERIAL,"native_only":True},"solver_policy":{"global_cap":3,"paper_a_max_active_fdtd":2,"processes":4,"threads":1,"entered_true_no_replay":True},"scheduler_snapshot":scheduler_snapshot()}
    if not parent_ok or not audit["all_geometry_valid"] or not rot.exists(): audit["status"]="HARD_GATE_SETUP_AUTHORITY"
    write_json(REPORT/"preflight.json",audit); return audit


def setup_case(g, pol):
    return PREV.setup_case(g,pol)


def run_case(cid):
    if PLANNING_ONLY:
        case_dir(cid).mkdir(parents=True, exist_ok=True)
        state={"schema":"PAPER_A_LP_ANISOTROPY_PLANNED_CASE_STATE_V1","case_id":cid,"status":"WAIT_BENCHMARK_AUTHORIZATION","solver_entered":False,"solver_run_called":False,"updated_utc":now()}
        write_json(case_state(cid),state)
        return state
    return PREV.run_case(cid)


def mdc_weights():
    p=ROOT/"paper_a_broadband/references/mdc/spectral_profiles_420_480_plot_data.csv"
    vals=[]
    with p.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if r.get("structure_key")=="zl1_alternative": vals.append((float(r["wavelength_nm"]),float(r["r12_normalized_output"])))
    vals.sort(); wl=np.array([x[0] for x in vals]); y=np.array([x[1] for x in vals]); v=np.interp(np.array(GRID),wl,y); w=v/v.sum()
    trap=np.trapezoid if hasattr(np,"trapezoid") else np.trapz
    ov=float(trap(y[(wl>=435)&(wl<=465)],wl[(wl>=435)&(wl<=465)])/trap(y,wl))
    c=float(np.sum(np.array(GRID)*w)); sig=float(np.sqrt(np.sum((np.array(GRID)-c)**2*w)))
    mask=(np.array(GRID)>=MDC_FWHM[0])&(np.array(GRID)<=MDC_FWHM[1]); wf=v[mask]/v[mask].sum()
    out={"schema":"PAPER_A_MDC_ZL1_ALTERNATIVE_WEIGHTING_V1","source_csv":str(p),"structure_key":"zl1_alternative","normalization":"r12_normalized_output relative spectral shape; not absolute emitted power or LEE","source_range_nm":[float(wl.min()),float(wl.max())],"formal_grid_nm":GRID,"normalized_weights_435_465":w.tolist(),"overlap_fraction_435_465":ov,"effective_center_nm":c,"effective_sigma_nm":sig,"fwhm_nm":list(MDC_FWHM),"fwhm_formal_wavelengths_nm":np.array(GRID)[mask].tolist(),"normalized_weights_mdc_fwhm":wf.tolist()}
    write_json(REPORT/"mdc_weighting.json",out); return out


def complex_value(r,prefix): return complex(float(r[prefix+"_real"]),float(r[prefix+"_imag"]))


def stokes(J):
    C=.5*J@J.conj().T; s0=float(np.trace(C).real); s1=float((C[0,0]-C[1,1]).real); s2=float(2*C[0,1].real); s3=float(-2*C[0,1].imag)
    q=math.sqrt(max(0.,s1*s1+s2*s2)); dolp=q/s0 if s0>0 else float("nan"); psi=(math.degrees(.5*math.atan2(s2,s1))%180.) if s0>0 else float("nan")
    ev,vec=np.linalg.eigh(C); v=vec[:,int(np.argmax(ev))]; sv=np.linalg.svd(J,compute_uv=False)
    return {"S0":s0,"S1":s1,"S2":s2,"S3":s3,"DoLP":dolp,"psi_deg":psi,"P_LP_axisfree":.5*(s0+q),"total_power":.5*s0,"circular_contamination":abs(s3)/s0 if s0>0 else float("nan"),"sigma1":float(sv[0]),"sigma2":float(sv[1]),"sigma2_over_sigma1":float(sv[1]/sv[0]) if sv[0]>0 else float("nan"),"dominant_vector_real":v.real.tolist(),"dominant_vector_imag":v.imag.tolist()}


def slope(x,y):
    return float(np.polyfit(np.asarray(x,float),np.asarray(y,float),1)[0]) if len(x)>=2 else float("nan")


def integrated(C, weights):
    Cw=np.sum(np.asarray(C)*np.asarray(weights)[:,None,None],axis=0); s0=float(np.trace(Cw).real); s1=float((Cw[0,0]-Cw[1,1]).real); s2=float(2*Cw[0,1].real); s3=float(-2*Cw[0,1].imag); q=math.sqrt(max(0.,s1*s1+s2*s2))
    return {"S0":s0,"S1":s1,"S2":s2,"S3":s3,"DoLP":q/s0 if s0>0 else float("nan"),"psi_deg":math.degrees(.5*math.atan2(s2,s1))%180. if s0>0 else float("nan"),"P_LP_axisfree":.5*(s0+q),"total_power":.5*s0,"circular_contamination":abs(s3)/s0 if s0>0 else float("nan")}


def postprocess_geometry(gid):
    d=load_doe(); g=next(x for x in d["geometries"] if x["geometry_id"]==gid); cps=[]
    for pol in ("x","y"):
        p=case_dir(f"{gid}_{pol}")/"checkpoint.json"
        if not p.exists(): raise RuntimeError(f"POSTPROCESS_MISSING_CHECKPOINT:{gid}_{pol}")
        cps.append(json.loads(p.read_text(encoding="utf-8"))["rows"])
    by={pol:{float(r["wavelength_nm"]):r for r in rows} for pol,rows in zip(("x","y"),cps)}; spectrum=[]; C=[]; prev_v=None
    for wl in GRID:
        j=np.array([[complex_value(by["x"][wl],"weighted_Ex"),complex_value(by["y"][wl],"weighted_Ex")],[complex_value(by["x"][wl],"weighted_Ey"),complex_value(by["y"][wl],"weighted_Ey")]],complex)
        m=stokes(j); v=np.array(m.pop("dominant_vector_real"))+1j*np.array(m.pop("dominant_vector_imag")); overlap=float(abs(np.vdot(prev_v,v))) if prev_v is not None else float("nan"); angle=math.degrees(math.acos(max(0.,min(1.,overlap)))) if prev_v is not None else float("nan"); prev_v=v
        m.update({"geometry_id":gid,"wavelength_nm":wl,"dominant_vector_overlap_adjacent":overlap,"dominant_vector_drift_angle_deg":angle}); spectrum.append(m); C.append(.5*j@j.conj().T)
    w=mdc_weights(); weights=np.array(w["normalized_weights_435_465"]); fmask=np.array([(MDC_FWHM[0]<=x<=MDC_FWHM[1]) for x in GRID]); fw=weights[fmask]/weights[fmask].sum(); fidx=np.where(fmask)[0]
    psi2=np.unwrap(2*np.radians(np.array([r["psi_deg"] for r in spectrum]))); psi=np.degrees(psi2/2); dolp=np.array([r["DoLP"] for r in spectrum]); power=np.array([r["P_LP_axisfree"] for r in spectrum]); ratio=np.array([r["sigma2_over_sigma1"] for r in spectrum]); ov=np.array([r["dominant_vector_overlap_adjacent"] for r in spectrum[1:]])
    sw=integrated(C,weights.tolist()); sf=integrated(np.array(C)[fidx],fw.tolist());
    rows_state=[]; rows_sing=[]
    for i,r in enumerate(spectrum):
        rows_state.append({"geometry_id":gid,"wavelength_nm":r["wavelength_nm"],"DoLP":r["DoLP"],"psi_deg_mod_pi":r["psi_deg"],"psi_unwrapped_deg":float(psi[i]),"DoLP_slope_local":None,"psi_slope_local":None,"P_LP_axisfree":r["P_LP_axisfree"],"S3_over_S0":r["circular_contamination"]})
        rows_sing.append({"geometry_id":gid,"wavelength_nm":r["wavelength_nm"],"sigma1":r["sigma1"],"sigma2":r["sigma2"],"sigma2_over_sigma1":r["sigma2_over_sigma1"],"adjacent_overlap":r["dominant_vector_overlap_adjacent"],"drift_angle_deg":r["dominant_vector_drift_angle_deg"]})
    summary={"geometry_id":gid,"role":g["role"],"source":g["source"],"anisotropy_ratio_1":g["anisotropy_ratio_1"],"anisotropy_ratio_2":g["anisotropy_ratio_2"],"relative_anisotropy":g["relative_anisotropy"],"MDC_weighted":sw,"MDC_FWHM_weighted":sf,"MDC_FWHM_psi_span_deg":float(max(psi[fidx])-min(psi[fidx])),"MDC_FWHM_DoLP_worst":float(min(dolp[fidx])),"MDC_FWHM_P_LP_axisfree_worst":float(min(power[fidx])),"formal_DoLP_mean":float(np.mean(dolp)),"formal_DoLP_worst":float(min(dolp)),"formal_P_LP_axisfree_mean":float(np.mean(power)),"formal_P_LP_axisfree_worst":float(min(power)),"formal_DoLP_slope_deg_per_nm":slope(GRID,dolp),"formal_psi_slope_deg_per_nm":slope(GRID,psi),"MDC_FWHM_DoLP_slope_deg_per_nm":slope(np.array(GRID)[fidx],dolp[fidx]),"MDC_FWHM_psi_slope_deg_per_nm":slope(np.array(GRID)[fidx],psi[fidx]),"dominant_vector_overlap_worst":float(np.nanmin(ov)) if len(ov) else None,"dominant_vector_overlap_mean":float(np.nanmean(ov)) if len(ov) else None,"dominant_vector_drift_max_deg":float(np.nanmax([r["dominant_vector_drift_angle_deg"] for r in spectrum[1:]])) if len(spectrum)>1 else None,"linear_output_not_S3_dominated":bool(sw["circular_contamination"]<sw["DoLP"]),"single_point_support":False,"final_pass":False,"promising":False}
    summary["final_pass"]=bool(sw["DoLP"]>=.80 and sw["P_LP_axisfree"]>=.35 and summary["MDC_FWHM_psi_span_deg"]<=10.0 and summary["MDC_FWHM_DoLP_worst"]>=.70 and summary["linear_output_not_S3_dominated"])
    summary["promising"]=bool(sw["DoLP"]>=.60 and sw["P_LP_axisfree"]>=.25 and summary["MDC_FWHM_psi_span_deg"]<=30.0 and summary["MDC_FWHM_DoLP_worst"]>=.50 and summary["formal_psi_slope_deg_per_nm"]==summary["formal_psi_slope_deg_per_nm"])
    write_csv(REPORT/"broadband_jones_spectra.csv",_append_csv(REPORT/"broadband_jones_spectra.csv",spectrum)); write_csv(REPORT/"axisfree_stokes_metrics.csv",_append_csv(REPORT/"axisfree_stokes_metrics.csv",spectrum)); write_csv(REPORT/"anisotropy_state_stability.csv",_append_csv(REPORT/"anisotropy_state_stability.csv",rows_state)); write_csv(REPORT/"singular_vector_stability.csv",_append_csv(REPORT/"singular_vector_stability.csv",rows_sing));
    write_csv(REPORT/"mdc_weighted_metrics.csv",_append_csv(REPORT/"mdc_weighted_metrics.csv",[{"geometry_id":gid,"window":"435-465","weighting":"r12_normalized_output","S0":sw["S0"],"S1":sw["S1"],"S2":sw["S2"],"S3":sw["S3"],"DoLP":sw["DoLP"],"psi_deg":sw["psi_deg"],"P_LP_axisfree":sw["P_LP_axisfree"],"circular_contamination":sw["circular_contamination"]},{"geometry_id":gid,"window":"MDC-FWHM","weighting":"r12_normalized_output","S0":sf["S0"],"S1":sf["S1"],"S2":sf["S2"],"S3":sf["S3"],"DoLP":sf["DoLP"],"psi_deg":sf["psi_deg"],"P_LP_axisfree":sf["P_LP_axisfree"],"circular_contamination":sf["circular_contamination"]}]))
    write_json(REPORT/f"{gid}_metrics.json",{"summary":summary,"spectrum":spectrum,"mdc_weighting":w}); append_jsonl(REPORT/"sequential_decisions.jsonl",{"timestamp_utc":now(),"event":"GEOMETRY_COMPLETED","geometry_id":gid,"summary":summary})
    return summary


def _append_csv(p, rows):
    old=[]
    if p.exists():
        with p.open(encoding="utf-8",newline="") as f: old=list(csv.DictReader(f))
    return old+rows


def boundary_check():
    s=scheduler_snapshot(); other=[j for j in s["jobs"] if j.get("branch")!=BRANCH]; out={"snapshot":s,"allow_next_wave":not s["unknown_solver_jobs"] and not other and s["active_fdtd_jobs"]==0,"reason":"NO_OTHER_ACTIVE_SOLVER" if not other else "HIGHER_PRIORITY_OR_EXTERNAL_ACTIVE"}; append_jsonl(REPORT/"boundary_events.jsonl",out); return out


def monitor_loop(stop, wave):
    lock=RUNTIME/"monitor/paper_a_lp_anisotropy_monitor.lock"; lock.parent.mkdir(parents=True,exist_ok=True)
    if lock.exists(): raise RuntimeError("DUPLICATE_MONITOR_GUARD")
    lock.write_text(json.dumps({"pid":os.getpid(),"created_utc":now(),"task":TASK_ID}),encoding="utf-8")
    state_p=RUNTIME/"monitor/paper_a_lp_anisotropy_monitor_state.json"
    try:
        while not stop.wait(600.0):
            states=[]
            for p in RUNTIME.glob("cases/*/state.json"):
                try: states.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception: pass
            snap=scheduler_snapshot(); rec={"timestamp":now(),"task":TASK_ID,"stage":"LP_ANISOTROPY_EXPANDED","completed":sum(x.get("status")=="COMPLETED" for x in states),"total":16,"waiting":sum(x.get("status")=="WAITING" for x in states),"running":sum(x.get("status")=="RUNNING" for x in states),"returned":sum(x.get("status")=="RETURNED" for x in states),"accepted":sum(x.get("status")=="COMPLETED" for x in states),"current_cases":[{"case_id":x.get("case_id"),"status":x.get("status"),"solver_entered":x.get("solver_entered"),"attempt_id":x.get("attempt_id")} for x in states],"scheduler":snap,"progress":None,"active_hard_gate":None}
            append_jsonl(RUNTIME/"monitor/paper_a_lp_anisotropy_progress.jsonl",rec); write_json(state_p,rec)
    finally:
        try: lock.unlink()
        except FileNotFoundError: pass


def run_wave(gid):
    if PLANNING_ONLY:
        return {"geometry_id":gid,"status":"WAIT_BENCHMARK_AUTHORIZATION","solver_entered":False,"solver_run_called":False}
    d=load_doe(); g=next(x for x in d["geometries"] if x["geometry_id"]==gid)
    for pol in ("x","y"):
        if not (case_dir(f"{gid}_{pol}")/"setup_only.json").exists(): setup_case(g,pol)
    procs=[]; logs=[]
    for pol in ("x","y"):
        cid=f"{gid}_{pol}"; fh=(case_dir(cid)/"controller.log").open("a",encoding="utf-8"); logs.append(fh); procs.append((cid,subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"run-case","--case-id",cid],stdout=fh,stderr=fh)))
    while any(p.poll() is None for _,p in procs): time.sleep(5)
    results=[]
    for cid,p in procs:
        st=json.loads(case_state(cid).read_text(encoding="utf-8")) if case_state(cid).exists() else None; results.append({"case_id":cid,"returncode":p.returncode,"state":st})
    for f in logs: f.close()
    if any(x["returncode"]!=0 or not x["state"] or x["state"].get("status")!="COMPLETED" for x in results): return {"geometry_id":gid,"status":"FAILED","cases":results}
    return {"geometry_id":gid,"status":"COMPLETED","cases":results,"summary":postprocess_geometry(gid)}


def midpoint(summaries):
    final=[x for x in summaries if x.get("final_pass")]; promising=[x for x in summaries if x.get("promising")]
    directional=[x for x in summaries if x.get("MDC_weighted",{}).get("DoLP",0)>=.40 or x.get("MDC_FWHM_psi_span_deg",999)<=45.0 or (x.get("dominant_vector_drift_max_deg") is not None and x.get("dominant_vector_drift_max_deg")<90.0)]
    cont=bool(final or promising or directional)
    out={"schema":"PAPER_A_BROADBAND_LP_ANISOTROPY_MIDPOINT_AUDIT_V1","timestamp_utc":now(),"geometries_completed":len(summaries),"final_pass_count":len(final),"promising_count":len(promising),"directional_count":len(directional),"continue_to_A05_A08":cont,"summaries":summaries}
    write_json(REPORT/"midpoint_physics_audit.json",out); return out


def finalise(status,waves,reason=None):
    summaries=[x["summary"] for x in waves if x.get("summary")]; ranked=sorted(summaries,key=lambda x:(bool(x.get("final_pass")),bool(x.get("promising")),x.get("MDC_weighted",{}).get("DoLP",-1),x.get("MDC_weighted",{}).get("P_LP_axisfree",-1),-x.get("MDC_FWHM_psi_span_deg",999)),reverse=True)
    primary=ranked[0]["geometry_id"] if ranked and (ranked[0].get("final_pass") or ranked[0].get("promising")) else None
    decision={"schema":"PAPER_A_BROADBAND_LP_ANISOTROPY_FINAL_DECISION_V1","timestamp_utc":now(),"status":status,"primary":primary,"geometry_count":len(summaries),"solver_entered_cases":sum(1 for g in load_doe()["geometries"] for pol in ("x","y") if (case_state(f"{g['geometry_id']}_{pol}").exists() and json.loads(case_state(f"{g['geometry_id']}_{pol}").read_text(encoding="utf-8")).get("solver_entered"))),"reason":reason,"ranked_geometry_ids":[x["geometry_id"] for x in ranked],"summaries":summaries,"scheduler_snapshot":scheduler_snapshot()}
    write_json(REPORT/"final_candidate.json",{"primary":primary,"ranked":ranked,"status":status}); write_json(REPORT/"final_decision.json",decision); write_json(REPORT/"audit.json",{"schema":"PAPER_A_BROADBAND_LP_ANISOTROPY_AUDIT_V1","timestamp_utc":now(),"solver_budget_max_cases":16,"solver_entered_cases":decision["solver_entered_cases"],"no_rcwa":True,"no_cp_rerun":True,"previous_stage_immutable":True,"rotation_audit_limit":"common rotation not supported; no seventh DOF","decision_status":status,"scheduler":decision["scheduler_snapshot"]})
    report=["# Paper A LP anisotropy-expanded search v1",'',f"Status: `{status}`",'',"Current-Native M1, 430–470 nm source/monitor, 435–465 nm formal window at 1 nm, axis-free full-Jones LP. P_LP_axisfree uses 0.5*(S0+sqrt(S1^2+S2^2)); MDC weighting integrates coherency before metrics.",'',f"Geometries completed: {len(summaries)}; solver-entered cases: {decision['solver_entered_cases']}; no RCWA/CP/new topology.",'',"## Candidate summaries",'',"| geometry | weighted DoLP | weighted P_LP_axisfree | FWHM psi span (deg) | FWHM DoLP worst | pass | promising |", "|---|---:|---:|---:|---:|---|---|"]
    for x in ranked: report.append(f"| {x['geometry_id']} | {x['MDC_weighted']['DoLP']:.4f} | {x['MDC_weighted']['P_LP_axisfree']:.4f} | {x['MDC_FWHM_psi_span_deg']:.2f} | {x['MDC_FWHM_DoLP_worst']:.4f} | {x['final_pass']} | {x['promising']} |")
    (REPORT/"final_report.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    return decision


def run_search():
    if PLANNING_ONLY:
        out={"schema":"PAPER_A_BROADBAND_LP_ANISOTROPY_PLANNING_DECISION_V1","status":"PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_PLANNED_WAIT_BENCHMARK","solver_budget":{"new_fdtd":0,"new_rcwa":0,"ml":0},"solver_entered_cases":0,"active_fdtd":0,"ready_for_auto_admission":0,"hidden_pending_admission":False,"next_authority":"USER_EXPLICIT_BENCHMARK_AUTHORIZATION_REQUIRED"}
        write_json(REPORT/"planning_decision.json",out); return out
    REPORT.mkdir(parents=True,exist_ok=True); pre=preflight()
    if pre["status"]!="PASS": return finalise("HARD_GATE_SETUP_AUTHORITY",[],pre["status"])
    write_json(RUNTIME/"monitor/paper_a_lp_anisotropy_monitor_state.json",{"timestamp":now(),"task":TASK_ID,"stage":"LP_ANISOTROPY_EXPANDED","status":"STARTING","progress":None})
    stop=threading.Event(); mon=threading.Thread(target=monitor_loop,args=(stop,"search"),daemon=True); mon.start(); waves=[]
    try:
        doe=load_doe(); queue=doe["initial_geometry_ids"][:]
        for i,gid in enumerate(queue):
            if not boundary_check()["allow_next_wave"]: return finalise("LOW_PRIORITY_BACKGROUND_WAIT",waves,"HIGHER_PRIORITY_OR_EXTERNAL_ACTIVE")
            result=run_wave(gid); waves.append(result)
            if result.get("status")!="COMPLETED": return finalise("HARD_GATE_CASE_FAILURE",waves,gid)
            if result["summary"].get("final_pass"): return finalise("PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_PASS",waves,"FINAL_PASS_AFTER_INITIAL_DOE")
        mid=midpoint([x["summary"] for x in waves]);
        if not mid["continue_to_A05_A08"]: return finalise("PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_EARLY_STOP_NO_DIRECTION",waves,"MIDPOINT_NO_DIRECTION")
        for gid in doe["conditional_geometry_ids"]:
            if not boundary_check()["allow_next_wave"]: return finalise("LOW_PRIORITY_BACKGROUND_WAIT",waves,"HIGHER_PRIORITY_OR_EXTERNAL_ACTIVE")
            result=run_wave(gid); waves.append(result)
            if result.get("status")!="COMPLETED": return finalise("HARD_GATE_CASE_FAILURE",waves,gid)
            if result["summary"].get("final_pass"): return finalise("PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_PASS",waves,"FINAL_PASS_AFTER_CONDITIONAL_DOE")
        summaries=[x["summary"] for x in waves]; return finalise("PAPER_A_BROADBAND_LP_ANISOTROPY_PROMISING_SEED_FOUND" if any(x.get("promising") for x in summaries) else "PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_FINAL_FAIL",waves,"ALL_EIGHT_GEOMETRIES_COMPLETE")
    finally:
        stop.set(); mon.join(timeout=3)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("mode",choices=["preflight","setup-wave","run-case","run-wave","postprocess","run-search","scheduler"]); ap.add_argument("--geometry-id"); ap.add_argument("--case-id"); a=ap.parse_args()
    if a.mode=="preflight": out=preflight()
    elif a.mode=="setup-wave":
        d=load_doe(); g=next(x for x in d["geometries"] if x["geometry_id"]==(a.geometry_id or "ANISO_A01")); rr=[setup_case(g,p) for p in ("x","y")]; out=rr
    elif a.mode=="run-case": out=run_case(a.case_id)
    elif a.mode=="run-wave": out=run_wave(a.geometry_id or "ANISO_A01")
    elif a.mode=="postprocess": out=postprocess_geometry(a.geometry_id or "ANISO_A01")
    elif a.mode=="scheduler": out=scheduler_snapshot()
    else: out=run_search()
    print(json.dumps(out,indent=2,ensure_ascii=False,default=str)); return 0

if __name__=="__main__": raise SystemExit(main())

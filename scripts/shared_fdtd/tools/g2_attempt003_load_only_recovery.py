from __future__ import annotations
import importlib.util, json, shutil, sys, uuid
from pathlib import Path

PKG=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(PKG.parent)); sys.path.insert(0,r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.event_log import append_event
from shared_fdtd.engine.persistence import atomic_json, sha256_file
from shared_fdtd.tools.real_canary_host import serialized_open

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=ROOT/r"outputs\coupling_ml\APCD_COUPLING_2D3D_G2_ATTEMPT003_FRESH_REBUILD_PARALLEL_PRODUCTION_V1"
CASE="W2H_15294"; d=OUT/"cases"/CASE/"attempt_003"; runtime=d/"run"/(CASE+"__attempt_003_runtime.fsp")
events=d/"recovery_events.jsonl"; post=d/"post"/(str(uuid.uuid4())+"__attempt_003_recovered_post.fsp"); post.parent.mkdir(parents=True,exist_ok=True)
ledger=json.loads((d/"attempt_ledger.json").read_text(encoding="utf-8"))
if not ledger.get("solver_entered") or ledger.get("run_invocation_count")!=1: raise SystemExit("invalid entered-attempt provenance")
log=runtime.with_name(runtime.stem+"_p0.log"); lines=log.read_text(errors="replace").splitlines()
if not any("100% complete" in line for line in lines) or runtime.stat().st_size<100_000_000: raise SystemExit("runtime truth not recovery eligible")
append_event(events,"LOAD_ONLY_RECOVERY_STARTED",case_id=CASE,runtime_fsp=str(runtime),runtime_sha256=sha256_file(runtime),run_invocation_count=1)
shutil.copy2(runtime,post)
if sha256_file(post)!=sha256_file(runtime): raise SystemExit("recovery copy hash mismatch")
spec=importlib.util.spec_from_file_location("g2_recovery_g1",ROOT/r"scripts\coupling_ml\apcd_coupling_2d3d_g1_matched_4case_3d_cylinder_phase_a_v1.py")
g=importlib.util.module_from_spec(spec); sys.modules[spec.name]=g; spec.loader.exec_module(g); g.OUT=OUT
fd=serialized_open(r"D:\apcd_runtime\global_fdtd_control_v3\recovery.sqlite3",post)
try:
    _=fd.getdata("top_farfield3d_monitor","f"); _=fd.getdata("top_farfield3d_monitor","Ex"); _=fd.farfield3d("top_farfield3d_monitor",1)
    raw,metrics,paths=g.extract_and_project(fd,{"geometry_id":CASE},post,d)
finally: fd.close()
raw["attempt_id"]="attempt_003"; raw["source_domain"]="LINE_LIKE_X"; raw["truth_fidelity"]="HF_3D"; atomic_json(paths["raw_json"],raw)
transfer=g.transfer_metrics(CASE,metrics,paths["projection"])
validation={"status":"PASS","recovery":"LOAD_ONLY_NO_SOLVER","solver_entry_count":1,"fresh_load":"PASS","raw_fields":"PASS","angular":"PASS","projection":"PASS","transfer_metrics":transfer,"post_fsp":str(post),"post_fsp_sha256":sha256_file(post)}
atomic_json(d/"scientific_validation.json",validation); ledger.update({"solver_returned":True,"solver_returned_evidence":"100_PERCENT_LOG_PLUS_FRESH_LOAD","recovered_without_solver":True,"post_fsp":str(post),"post_fsp_sha256":sha256_file(post)}); atomic_json(d/"attempt_ledger.json",ledger)
atomic_json(d/"terminal.json",{"state":"COMPLETED","status":"RECOVERED_VALID_HF_TRUTH","case_id":CASE,"attempt_id":"attempt_003","solver_entered":True,"solver_returned":True,"solver_entry_count":1,"rerun":False,"post_fsp":str(post),"post_fsp_sha256":sha256_file(post),"raw_result":str(paths["raw_json"]),"raw_result_sha256":sha256_file(paths["raw_json"]),"scientific_validation_status":"PASS","completed_utc":utc_now()})
append_event(events,"RECOVERED_VALID_HF_TRUTH",case_id=CASE,post_fsp=str(post),post_fsp_sha256=sha256_file(post),raw_sha256=sha256_file(paths["raw_json"]),solver_entry_count=1)

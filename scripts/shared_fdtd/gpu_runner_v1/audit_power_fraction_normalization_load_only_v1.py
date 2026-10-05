# -*- coding: utf-8 -*-
"""Read-only analysis of one already-completed archived FSP; never runs or saves."""
import hashlib
import importlib
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
RUN = pathlib.Path(r"D:\apcd_runtime\gpu_production_runner_v1\runs\K6LDA1_DEV_D1_M05\attempt_001\K6V2_D1M05_20261004T175055Z_449c4f94")
COUPLING_CASE = pathlib.Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6LDA1_DEV_D1_M05\attempt_001")
REPORT = REPO / "reports" / "gpu_runner_v1_power_fraction_normalization_v1" / "LOAD_ONLY_AUDIT.json"
EXPECTED = {
    "run.fsp": "f2258b74d62a1e9d7441cd8214dc371022a8a964df335c7faf6c45d8be4fb2b9",
    "run/run_output.h5": "8aa4ca58d22d9fd6eea4f5e53b557a96e0ec9c273f594c22561788f5af298dcd",
}
def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()
def maxdiff(rows_old,rows_new,key):
    values=[abs(float(a[key])-float(b[key])) for a,b in zip(rows_old,rows_new)]
    i=max(range(len(values)),key=values.__getitem__)
    return {"max_abs":values[i],"wavelength_nm":float(rows_new[i]["wavelength_nm"])}

if not RUN.is_dir() or not COUPLING_CASE.is_dir():
    raise SystemExit("ARCHIVE_OR_CONTRACT_DIRECTORY_MISSING")
fsp=RUN/"run.fsp"
h5=RUN/"run"/"run_output.h5"
hashes=json.loads((RUN/"hashes.json").read_text(encoding="utf-8"))
for rel,expected in EXPECTED.items():
    actual=sha(RUN/rel)
    if actual!=expected:
        raise SystemExit("ARCHIVE_HASH_MISMATCH:"+rel+":"+actual)
recorded={"run.fsp":hashes.get("run_fsp_sha256"),"run/run_output.h5":hashes.get("run_output_h5_sha256")}
if recorded!=EXPECTED:
    raise SystemExit("ARCHIVE_HASH_INDEX_MISMATCH:"+json.dumps(recorded))
contract_path=COUPLING_CASE/"physical_contract.json"
contract=json.loads(contract_path.read_text(encoding="utf-8"))
if sha(contract_path)!="32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5":
    raise SystemExit("PHYSICAL_CONTRACT_HASH_MISMATCH")
old_projection_path=RUN/"projection"/"K6LDA1_DEV_D1_M05__attempt_001_projection.json"
old_orders_path=RUN/"orders"/"K6LDA1_DEV_D1_M05__attempt_001_orders.json"
old_projection=json.loads(old_projection_path.read_text(encoding="utf-8"))
old_orders=json.loads(old_orders_path.read_text(encoding="utf-8"))
before={"run.fsp":sha(fsp),"run/run_output.h5":sha(h5)}
ps=r'''$rows=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like "fdtd-engine*.exe" } | Select-Object Name,ProcessId,ParentProcessId,CreationDate,CommandLine); ConvertTo-Json -InputObject $rows -Compress'''
proc=subprocess.run(["powershell","-NoProfile","-Command",ps],capture_output=True,text=True,timeout=30)
if proc.returncode!=0:
    raise SystemExit("PROCESS_CENSUS_FAILED:"+proc.stderr)
engine_processes=json.loads(proc.stdout.strip() or "[]")
if engine_processes:
    raise SystemExit("ACTIVE_FDTD_ENGINE_PRESENT:"+json.dumps(engine_processes))
sys.path.insert(0,str(REPO/"scripts"/"shared_fdtd"/"gpu_runner_v1"))
import adapter
adapter._prepare_postprocess_import_paths()
launcher=adapter.load_pinned_launcher()
state_module=importlib.import_module("shared_fdtd.tools.pw_complex_floquet_state_v1")
lumapi=importlib.import_module("lumapi")
fd=None
try:
    fd=lumapi.FDTD(hide=True)
    fd.load(str(fsp))
    state=state_module.canonical_state_from_fdtd(fd,contract)
    metrics=launcher.analyze(fd,{"pw_contract":{"contract":contract}},state)
finally:
    if fd is not None:
        try:
            fd.close()
        except Exception:
            pass
after={"run.fsp":sha(fsp),"run/run_output.h5":sha(h5)}
if before!=after:
    raise SystemExit("ARCHIVE_MUTATED_DURING_LOAD_ONLY")
old_rows=old_projection["rows"]
new_rows=metrics["rows"]
if len(old_rows)!=21 or len(new_rows)!=21:
    raise SystemExit("WAVELENGTH_COUNT_NOT_21")
if any(abs(float(a["wavelength_nm"])-float(b["wavelength_nm"]))>1e-7 for a,b in zip(old_rows,new_rows)):
    raise SystemExit("WAVELENGTH_ALIGNMENT_FAILED")
legacy_checks={key:maxdiff(old_rows,new_rows,key) for key in ("R_FDTD","T_FDTD","A_FDTD","closure")}
if any(item["max_abs"]>1e-9 for item in legacy_checks.values()):
    raise SystemExit("LEGACY_RTA_CHANGED:"+json.dumps(legacy_checks))
post_orders=metrics["orders"]["post"]
scales=[float(r["output_P_scale_IN_REF"]) for r in new_rows]
if len(post_orders)!=21 or len(scales)!=21:
    raise SystemExit("POST_ORDER_COUNT_MISMATCH")
order_checks=[]
for i,group in enumerate(post_orders):
    eta_sum=sum(float(row["power_fraction_of_monitor_total"]) for row in group)
    source_sum=sum(float(row["power_fraction_of_source"]) for row in group)
    if abs(eta_sum-1.0)>1e-8 or abs(source_sum-scales[i])>1e-8*max(1.0,abs(scales[i])):
        raise SystemExit("ORDER_POWER_SUM_MISMATCH:"+str(i))
    order_checks.append({
        "wavelength_nm":float(new_rows[i]["wavelength_nm"]),
        "monitor_eta_sum":eta_sum,
        "source_fraction_sum":source_sum,
        "P_scale_IN_REF":scales[i],
        "old_source_fraction_sum":sum(float(x["power_fraction_of_source"]) for x in old_orders["post"][i]),
    })
backend_manifest=adapter.LAUNCHER_PATH.parents[3]/"manifest.json"
report={
    "schema":"APCD_GPU_RUNNER_V1_POWER_FRACTION_NORMALIZATION_LOAD_ONLY_AUDIT_V1",
    "result":"PASS",
    "scientific_entry_performed":False,
    "solver_run_called":False,
    "fsp_save_called":False,
    "analysis_calls":["fd.load","canonical_state_from_fdtd","launcher.analyze"],
    "case_id":"K6LDA1_DEV_D1_M05",
    "attempt_id":"attempt_001",
    "run_id":"K6V2_D1M05_20261004T175055Z_449c4f94",
    "physical_contract_sha256":sha(contract_path),
    "archived_artifacts":{
        "run_fsp":{"path":str(fsp),"sha256_before":before["run.fsp"],"sha256_after":after["run.fsp"]},
        "run_output_h5":{"path":str(h5),"sha256_before":before["run/run_output.h5"],"sha256_after":after["run/run_output.h5"]},
    },
    "backend":{
        "backend_id":adapter.PINNED_BACKEND_ID,
        "launcher_path":str(adapter.LAUNCHER_PATH),
        "launcher_sha256":adapter.LAUNCHER_SHA256,
        "manifest_sha256":sha(backend_manifest),
        "inventory_sha256":json.loads(backend_manifest.read_text(encoding="utf-8"))["inventory_sha256"],
    },
    "wavelength_count":len(new_rows),
    "transmission_api_parity":"PASS",
    "legacy_R_T_A_closure_max_abs_diff":legacy_checks,
    "output_order_conservation_checks":order_checks,
    "scope_note":"Power-fraction normalization implementation/load-only audit only; no Coupling scientific acceptance, HF label acceptance, or ML readiness is implied.",
    "active_fdtd_engine_processes_before_load":engine_processes,
}
REPORT.parent.mkdir(parents=True,exist_ok=True)
REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))

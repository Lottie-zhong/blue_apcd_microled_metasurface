from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter
import runner
import task_scheduler_v1 as scheduler
from postentry_recovery_v1 import recover_postentry_truth_v1

RUNNER_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
COUPLING_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
CASE_ID = "K6GDP2_DEV_G025"
ATTEMPT_ID = "attempt_001"
RUN_ID = "K6V2_G025_20261008T140327Z_454d6858"
REQUEST_ID = "28c992f00bb8b032ecf06f4d8e8dc431"
WORKER_PID = 44352
RECOVERY_PARENT = RUNNER_ROOT / "recovery" / CASE_ID / ATTEMPT_ID / RUN_ID
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
RECOVERY_DIR = RECOVERY_PARENT / ("postentry_truth_recovery_" + STAMP)
REQUEST_DIR = RUNNER_ROOT / "requests" / "scheduled_run_one_v1" / REQUEST_ID
RUN_DIR = RUNNER_ROOT / "runs" / CASE_ID / ATTEMPT_ID / RUN_ID
COUPLING_EVIDENCE = COUPLING_ROOT / "reports" / "coupling" / "COUPLING_K6_V2_G025_ACTUAL_PRODUCTION_RESUME_V1"
CONTROLLER_STATUS = COUPLING_ROOT / "reports" / "coupling" / "COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1" / "CONTROLLER_STATUS_K6V2SERIAL20261008T050430Z_35cd64f3.json"

CONFIG = {
    "runner_root": str(RUNNER_ROOT), "run_dir": str(RUN_DIR),
    "request_dir": str(REQUEST_DIR), "recovery_dir": str(RECOVERY_DIR),
    "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID,
    "request_id": REQUEST_ID, "worker_pid": WORKER_PID,
    "forbidden_case_id": "K6GDP2_DEV_G026",
    "physical_contract_sha256": "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5",
    "pre_fsp_sha256": "e076df25d54a5e455f24f3efdda952d17b8ca332d137f9c68abe296a6ff20646",
    "expected_request_file_sha256": "144d7b77a34efc838d03887573af643869ab3b6b03a92cf746d18caa35476797",
    "expected_request_sha256": "243d4f32f617a85764310fd454c54c8277292cc6063cfb63f14810dc06fa5a62",
    "expected_claim_file_sha256": "6d276e203c16037623d44794d15e923a183a245f248a467d3565cd7b23d10df8",
    "expected_manifest_envelope_sha256": "1a7a43d7f4329e24c02080a27bbde6d95c26395a82148d7676ed7b8297d1b59e",
    "adapter_sha256": "7f28045aa8e0178ce22e44c4377d02515431f4577fb8f1dbd578f58149b50173",
    "worker_module_sha256": "8c078479623aa4250cc01a94c50700018932fd6f60c43a858dcb22641207c9dc",
    "run_manifest_sha256": "00e9d3506ab04cdf44fe2d12376c5d2e56a3695a5fc7a39611801704d62007d2",
    "run_fsp_sha256": "be006f194b07df6d19105812ca49fdce5a8d9660fff983559f91c9d3fc948572",
    "run_output_h5_sha256": "5e00289a1615d1f102cff0b7ce3fda73e00589be78371934c9c935349de3ec9c",
    "run_log_sha256": "c29baae70d6bfc7c69378303eaedfb54b8dc39a11ee37bacc6ca515784be6ce0",
    "status_sha256": "ef48847fa53c0205a9270ee19303981a059bb16e0c73092daf8090e08f98629f",
    "setup_validation_sha256": "3d211227315ab886f7e045c8d22ce5323509391a9832a51db91bcfefc51d8981",
    "pre_entry_revalidation_sha256": "b6c587f163476fcec25a105b8c9c4c27d73f528a4eef6287322676c03e44b51f",
    "marker_sha256": {
        ".runner.lock": "2856d4ab1cc04ac53b8186ce04d420a9ce5ac3b2d69a762925dec3e8e7bfa3cc",
        "active_run.json": "034293528247c55a94b3a80e3c9436e624093f72fac7ec48983619bd432c7068",
        "scheduler_worker_v1.lock": "4f74c327fd6c543aeef5e764ab7fe00c7bd98d65121b76ae59f31e5703ce761d",
    },
    "expected_wavelengths_nm": list(range(440, 461)),
}

def _git_value(*args, cwd):
    result = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                             text=True, encoding="utf-8", errors="replace", check=True)
    return result.stdout.strip()

def _process_census():
    script = r"""
$rows = @(Get-CimInstance Win32_Process -ErrorAction Stop |
  Where-Object { $_.Name -match '^(fdtd-solutions\.exe|fdtd-engine.*\.exe|pythonw?\.exe)$' } |
  Select-Object ProcessId,ParentProcessId,CreationDate,Name,CommandLine)
if ($rows.Count -eq 0) { '[]' } else { ConvertTo-Json -InputObject $rows -Compress -Depth 4 }
"""
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=25, check=True)
    rows = json.loads(result.stdout or "[]")
    if isinstance(rows, dict):
        rows = [rows]
    current_pid = os.getpid()
    blocking, old_target = [], False
    for row in rows:
        pid = int(row.get("ProcessId", 0))
        if pid == current_pid:
            continue
        name = str(row.get("Name", "")).casefold()
        command = str(row.get("CommandLine") or "")
        low = command.casefold()
        if pid in (44352, 45232) and (
                RUN_ID.casefold() in low or REQUEST_ID.casefold() in low
                or "task_scheduler_v1.py" in low or "run_gpu.lsf" in low):
            old_target = True
        if name.startswith("fdtd-engine"):
            blocking.append(row)
        elif name == "fdtd-solutions.exe" and (
                " -run " in low or "run_gpu.lsf" in low or RUN_ID.casefold() in low):
            blocking.append(row)
        elif name in ("python.exe", "pythonw.exe") and (
                "task_scheduler_v1.py" in low or "gpu_runner_v1" in low):
            blocking.append(row)
    return {"captured_utc": datetime.now(timezone.utc).isoformat(),
            "processes": rows, "blocking_processes": blocking,
            "prior_g025_worker_or_child_present": old_target}

def _task_snapshot():
    return {
        "worker": scheduler._task_info(),
        "controller": scheduler._task_info(scheduler.CONTROLLER_TASK_NAME),
    }

def _control_snapshot():
    return adapter.read_global_entry_control()

def _external_snapshot():
    paths = {
        "coupling_resume_continuation": COUPLING_EVIDENCE / "CONTINUATION.md",
        "coupling_resume_evidence": COUPLING_EVIDENCE / "G025_ACTUAL_PRODUCTION_RESUME_EVIDENCE_V1.json",
        "controller_status": CONTROLLER_STATUS,
        "request_manifest_envelope": Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\RUN_ENVELOPE_K6V2_G025_20261008T140327Z_454d6858.json"),
    }
    file_hashes = {
        key: hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        for key, path in paths.items()
    }
    return {
        "coupling_head": _git_value("rev-parse", "HEAD", cwd=COUPLING_ROOT),
        "coupling_status_sha256": hashlib.sha256(
            _git_value("status", "--short", cwd=COUPLING_ROOT).encode("utf-8")).hexdigest(),
        "read_only_file_hashes": file_hashes,
    }

def main():
    CONFIG["runner_head"] = _git_value("rev-parse", "HEAD", cwd=HERE.parents[2])
    source_paths = {
        "runner.py": Path(runner.__file__),
        "adapter.py": Path(adapter.__file__),
        "task_scheduler_v1.py": Path(scheduler.__file__),
        "postentry_recovery_v1.py": HERE / "postentry_recovery_v1.py",
        "recover_g025_postsolver_truth_v1.py": Path(__file__).resolve(),
    }
    CONFIG["runner_source_hashes"] = {
        key: hashlib.sha256(path.read_bytes()).hexdigest()
        for key, path in source_paths.items()
    }
    return recover_postentry_truth_v1(
        config=CONFIG, adapter_module=adapter, runner_module=runner,
        scheduler_module=scheduler, process_census=_process_census,
        task_snapshot=_task_snapshot, control_snapshot=_control_snapshot,
        external_snapshot=_external_snapshot)

if __name__ == "__main__":
    try:
        print(json.dumps(main(), sort_keys=True, ensure_ascii=False, default=str))
    except BaseException as exc:
        print(json.dumps({"result": "BLOCKED", "error_type": type(exc).__name__,
                          "error": str(exc), "traceback": traceback.format_exc(),
                          "solver_invocations_during_recovery": 0,
                          "automatic_replay_count": 0}, sort_keys=True, ensure_ascii=False))
        raise SystemExit(2)

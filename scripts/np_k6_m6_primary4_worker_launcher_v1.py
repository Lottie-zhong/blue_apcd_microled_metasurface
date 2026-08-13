"""Single source of truth for M4 Scheduler worker environment and init smoke.

The init-smoke path creates/loads a disposable FDTD session only.  It never
calls run(), runanalysis(), runjobs(), or save().  The formal path delegates
to the existing one-shot controller only after the deterministic environment
has been installed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m6_primary4_hf_acquisition_v1"
RUNNER = ROOT / r"scripts\np_k6_m6_primary4_runner_v1.py"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
LUM = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical")
LIC = Path(r"N:\Program Files\ANSYS Inc\v251\licensingclient\winx64")
PYTHON_EXE = Path(r"N:\anaconda_envs\RCP_LCP\python.exe")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def build_environment() -> dict[str, str]:
    env = os.environ.copy()
    existing_path = env.get("PATH", "")
    additions = [str(LUM), str(LUM / "bin"), str(API), str(LIC)]
    env["PATH"] = os.pathsep.join([x for x in additions + [existing_path] if x])
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(API), existing_pythonpath] if existing_pythonpath else [str(API)])
    env.setdefault("ANSYSLMD_LICENSE_FILE", "1055@DESKTOP-NNE313K")
    env.setdefault("LM_LICENSE_FILE", env["ANSYSLMD_LICENSE_FILE"])
    env.setdefault("ANSYS_LOCK", "OFF")
    env.setdefault("ANSYS_SYSDIR", "winx64")
    env.setdefault("ANSYS251_DIR", r"N:\\Program Files\\ANSYS Inc\\v251\\ANSYS")
    env.setdefault("ANSYSEM_ROOT251", r"N:\\Program Files\\ANSYS Inc\\v251\\AnsysEM")
    env.setdefault("ANSYS202_DIR", r"N:\\Program Files\\ANSYS Inc\\v202\\ANSYS")
    env.setdefault("LSTC_LICENSE", "ANSYS")
    env.setdefault("LSTC_LICENSE_SERVER", "ANSYS")
    profile = env.get("USERPROFILE") or str(Path.home())
    env.setdefault("USERPROFILE", profile)
    env.setdefault("HOMEDRIVE", Path(profile).drive)
    env.setdefault("HOMEPATH", str(Path(profile).anchor)[2:] if Path(profile).anchor else "")
    env.setdefault("APPDATA", str(Path(profile) / "AppData" / "Roaming"))
    env.setdefault("LOCALAPPDATA", str(Path(profile) / "AppData" / "Local"))
    env.setdefault("TEMP", str(Path(env["LOCALAPPDATA"]) / "Temp"))
    env.setdefault("TMP", env["TEMP"])
    return env


def powershell_path() -> str:
    return shutil.which("powershell") or ""


def environment_snapshot(label: str, env: dict[str, str]) -> dict[str, object]:
    pid = os.getpid()
    parent = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
    )
    session = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object Id,SessionId | ConvertTo-Json -Compress"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
    )
    relevant = [p for p in env.get("PATH", "").split(os.pathsep) if "ANSYS" in p.upper() or "LUMERICAL" in p.upper()]
    filtered_env = {k: v for k, v in env.items() if any(token in k.upper() for token in ("ANSYS", "LUM", "LICENSE", "ACL", "PORT"))}
    return {
        "label": label,
        "timestamp_utc": now(),
        "sys_executable": sys.executable,
        "sys_version": sys.version,
        "pythonpath": sys.path,
        "where_python": shutil.which("python") or "",
        "where_powershell": powershell_path(),
        "lumapi_module": str(getattr(sys.modules.get("lumapi"), "__file__", "")),
        "ansys_paths_in_path": relevant,
        "license_environment": {k: env.get(k, "") for k in ("ANSYSLMD_LICENSE_FILE", "LM_LICENSE_FILE")},
        "filtered_environment": filtered_env,
        "windows_user": env.get("USERNAME", ""),
        "session_id": env.get("SESSIONNAME", ""),
        "userprofile": env.get("USERPROFILE", ""),
        "homedrive": env.get("HOMEDRIVE", ""),
        "homepath": env.get("HOMEPATH", ""),
        "appdata": env.get("APPDATA", ""),
        "localappdata": env.get("LOCALAPPDATA", ""),
        "temp": env.get("TEMP", ""),
        "tmp": env.get("TMP", ""),
        "cwd": os.getcwd(),
        "parent_process_json": parent.stdout.strip(),
        "python_pid": pid,
        "python_session_json": session.stdout.strip(),
        "python_executable_expected": str(PYTHON_EXE),
        "api_path_expected": str(API),
        "lumerical_root_expected": str(LUM),
    }


def init_smoke(case_id: str, smoke_id: str, task_name: str) -> int:
    env = build_environment()
    os.environ.clear()
    os.environ.update(env)
    os.chdir(ROOT)
    started = environment_snapshot("scheduler_worker_before_lumapi", env)
    result: dict[str, object] = {
        "schema_version": "np_k6_m4_scheduler_lumapi_init_smoke_v1",
        "case_id": case_id,
        "task_name": task_name,
        "smoke_id": smoke_id,
        "run_called": False,
        "runanalysis_called": False,
        "runjobs_called": False,
        "save_called": False,
        "solver_run_invocations": 0,
        "started_utc": now(),
        "environment": started,
    }
    try:
        sys.path.insert(0, str(API))
        import lumapi  # type: ignore
        result["lumapi_module"] = str(getattr(lumapi, "__file__", ""))
        run_copy = OUT / "runtime_runs" / case_id / "attempt_001" / f"{case_id}_attempt_001_run.fsp"
        source_fsp = OUT / "runtime_prefsp" / f"{case_id}.fsp"
        contract_path = OUT / "cases" / case_id / "setup_contract.json"
        if run_copy.exists():
            smoke_target = run_copy
            result["smoke_target_kind"] = "existing_run_copy"
        elif source_fsp.exists():
            smoke_target = source_fsp
            result["smoke_target_kind"] = "frozen_source_prefsp"
        elif contract_path.exists():
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            smoke_target = Path(contract["source_prefsp_path"])
            result["smoke_target_kind"] = "contract_source_prefsp"
        else:
            raise FileNotFoundError(f"no constructor smoke target for {case_id}")
        result["run_copy"] = str(run_copy)
        result["run_copy_exists"] = run_copy.exists()
        result["smoke_target"] = str(smoke_target)
        errors = []
        for attempt in range(1, 4):
            result["constructor_attempts"] = attempt
            try:
                fd = lumapi.FDTD(str(smoke_target), hide=True)
                try:
                    result["simulation_time"] = str(fd.getnamed("FDTD", "simulation time"))
                    result["mesh_accuracy"] = str(fd.getnamed("FDTD", "mesh accuracy"))
                finally:
                    fd.close()
                break
            except Exception as exc:
                errors.append({"attempt": attempt, "error": repr(exc), "timestamp_utc": now()})
                if attempt == 3:
                    raise
                time.sleep(20 * attempt)
        if errors:
            result["constructor_retry_errors"] = errors
        result["passed"] = True
    except Exception as exc:
        result["passed"] = False
        result["error"] = repr(exc)
    result["finished_utc"] = now()
    result["environment_after"] = environment_snapshot("scheduler_worker_after_lumapi", env)
    atomic(OUT / f"scheduler_init_smoke_{smoke_id}.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result["passed"] else 1


def formal(case_id: str, task_name: str) -> None:
    env = build_environment()
    os.environ.clear()
    os.environ.update(env)
    os.chdir(ROOT)
    sys.argv = [str(RUNNER), "--case", case_id, "--task-name", task_name]
    runpy.run_path(str(RUNNER), run_name="__main__")


def default_task_name(case_id: str) -> str:
    return rf"\APCD\NP\NP_K6_M6_PRIMARY4_{case_id}_001"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--task-name", default="")
    parser.add_argument("--lumapi-init-smoke-only", action="store_true")
    parser.add_argument("--smoke-id", default="001")
    args = parser.parse_args()
    task_name = args.task_name or default_task_name(args.case)
    if args.lumapi_init_smoke_only:
        return init_smoke(args.case, args.smoke_id, task_name)
    formal(args.case, task_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

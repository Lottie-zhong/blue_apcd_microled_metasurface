from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4fmm2b1_rcwa_api_smoke_test"
RUNTIME = ROOT / "runtime" / "r2_4fmm2b1_rcwa_api_smoke_test_DO_NOT_COMMIT"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
TARGET_WL_M = 453e-9
TARGET_WL_NM = 453.0
SCRIPT_NAME = "stage_r2_4fmm2b1_rcwa_api_smoke_test.py"
GITIGNORE = """*.fsp
*.fspx
*.ldf
*.mat
*.h5
*.hdf5
*.dat
*.raw
*.png
*.jpg
*.jpeg
*.bmp
*.tif
*.tiff
*.gif
*.mp4
*.avi
"""


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def safe_str(value: Any) -> str:
    try:
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (list, tuple, dict)):
            return json.dumps(value)
        return str(value)
    except Exception:
        return repr(value)


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {exc}"


def load_lumapi():
    spec = importlib.util.spec_from_file_location("lumapi", str(LUMAPI))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load lumapi from {LUMAPI}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = module
    spec.loader.exec_module(module)
    return module


def log(rows: list[dict[str, Any]], step: str, status: str, detail: Any = "", object_name: str = "") -> None:
    rows.append({"step": step, "object": object_name, "status": status, "detail": safe_str(detail)[:1500]})


def try_call(rows: list[dict[str, Any]], step: str, func, object_name: str = "") -> tuple[bool, Any]:
    try:
        result = func()
        log(rows, step, "ok", result, object_name)
        return True, result
    except Exception as exc:
        log(rows, step, "failed", f"{type(exc).__name__}: {exc}", object_name)
        return False, None


def try_set(fdtd, rows: list[dict[str, Any]], obj: str, prop: str, value: Any) -> bool:
    ok, _ = try_call(rows, f"set {prop}", lambda: fdtd.setnamed(obj, prop, value), obj)
    return ok


def try_set_current(fdtd, rows: list[dict[str, Any]], prop: str, value: Any, obj: str = "current") -> bool:
    ok, _ = try_call(rows, f"set current {prop}", lambda: fdtd.set(prop, value), obj)
    return ok


def try_get(fdtd, rows: list[dict[str, Any]], obj: str, prop: str) -> str:
    ok, value = try_call(rows, f"get {prop}", lambda: fdtd.getnamed(obj, prop), obj)
    return safe_str(value) if ok else "missing"


def first_success_set(fdtd, rows: list[dict[str, Any]], obj: str, props: list[str], value: Any) -> str:
    used = []
    for prop in props:
        if try_set(fdtd, rows, obj, prop, value):
            return prop
        used.append(prop)
    return "none"


def first_success_get(fdtd, rows: list[dict[str, Any]], obj: str, props: list[str]) -> tuple[str, str]:
    for prop in props:
        value = try_get(fdtd, rows, obj, prop)
        if value != "missing":
            return prop, value
    return "none", "missing"


def try_result(fdtd, rows: list[dict[str, Any]], obj: str, result_name: str) -> str:
    ok, value = try_call(rows, f"getresult {result_name}", lambda: fdtd.getresult(obj, result_name), obj)
    if not ok:
        return "missing"
    return safe_str(value)[:1000]


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}, current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / ".gitignore").write_text(GITIGNORE, encoding="utf-8")

    steps: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    addrcwa_available = False
    rcwa_object_created = False
    tiny_run_completed = False
    run_error = ""
    rcwa_object = "FMM2B1_tiny_rcwa"
    result_fsp = RUNTIME / "fmm2b1_tiny_rcwa_smoke_runtime_DO_NOT_COMMIT.fsp"

    try:
        lumapi = load_lumapi()
        log(steps, "load_lumapi", "ok", str(LUMAPI))
        fdtd = lumapi.FDTD(hide=False)
        log(steps, "open_lumerical_session", "ok", "new blank project; did not open H1J4 FSP")
        try_call(steps, "switch_to_layout", lambda: fdtd.switchtolayout())

        ok, _ = try_call(steps, "addrcwa", lambda: fdtd.addrcwa())
        addrcwa_available = ok
        rcwa_object_created = ok
        if ok:
            try_set_current(fdtd, steps, "name", rcwa_object, rcwa_object)
            # Tiny domain / normal incidence / x polarization / minimal harmonics. Unsupported props are logged.
            for prop, value in [
                ("x", 0), ("y", 0), ("z", 0),
                ("x span", 1e-6), ("y span", 1e-6), ("z span", 0.8e-6),
                ("wavelength", TARGET_WL_M), ("wavelength start", TARGET_WL_M), ("wavelength stop", TARGET_WL_M),
                ("theta", 0), ("phi", 0), ("polarization angle", 0),
                ("incident angle", 0), ("azimuthal angle", 0),
                ("maximum number of k vectors", 3), ("number of k vectors", 3),
                ("max number k vectors", 3), ("harmonics", 1),
            ]:
                try_set(fdtd, steps, rcwa_object, prop, value)

            # Minimal periodic thin-film proxy: one SiO2 slab in air, not H1J4 geometry.
            try_call(steps, "add_minimal_sio2_rect", lambda: fdtd.addrect())
            try_set_current(fdtd, steps, "name", "tiny_sio2_film", "tiny_sio2_film")
            for prop, value in [("material", "sio222"), ("x", 0), ("y", 0), ("z", 0), ("x span", 1e-6), ("y span", 1e-6), ("z span", 100e-9)]:
                try_set(fdtd, steps, "tiny_sio2_film", prop, value)

            # Save only a runtime artifact for reproducibility. It is gitignored and not staged.
            try_call(steps, "save_runtime_tiny_rcwa_fsp", lambda: fdtd.save(str(result_fsp)))
            # This run is intended for the RCWA object only; no FDTD region is created or opened.
            run_ok, _ = try_call(steps, "run_tiny_rcwa_model", lambda: fdtd.run(), rcwa_object)
            tiny_run_completed = run_ok
            if not run_ok:
                run_error = steps[-1]["detail"]

            # Lightweight result extraction attempts. Missing result names are recorded, not fabricated.
            result_summary = {
                "case_id": "tiny_rcwa_453nm_xpol_normal",
                "target_wavelength_nm": TARGET_WL_NM,
                "polarization": "x",
                "incidence": "normal",
                "model": "minimal periodic SiO2 thin-film proxy in air",
                "addrcwa_available": addrcwa_available,
                "rcwa_object_created": rcwa_object_created,
                "tiny_run_completed": tiny_run_completed,
                "run_error": run_error,
                "T_result_preview": try_result(fdtd, steps, rcwa_object, "T"),
                "R_result_preview": try_result(fdtd, steps, rcwa_object, "R"),
                "S_result_preview": try_result(fdtd, steps, rcwa_object, "S"),
                "grating_orders_preview": try_result(fdtd, steps, rcwa_object, "grating_orders"),
                "power_preview": try_result(fdtd, steps, rcwa_object, "power"),
            }
            results.append(result_summary)
        try_call(steps, "close_lumerical_session", lambda: fdtd.close())
    except Exception as exc:
        run_error = f"{type(exc).__name__}: {exc}"
        log(steps, "main_exception", "failed", run_error + "\n" + traceback.format_exc())
        results.append({
            "case_id": "tiny_rcwa_453nm_xpol_normal",
            "target_wavelength_nm": TARGET_WL_NM,
            "polarization": "x",
            "incidence": "normal",
            "model": "minimal periodic SiO2 thin-film proxy in air",
            "addrcwa_available": addrcwa_available,
            "rcwa_object_created": rcwa_object_created,
            "tiny_run_completed": tiny_run_completed,
            "run_error": run_error,
        })

    for p in sorted(RUNTIME.glob("*")):
        artifact_rows.append({
            "path": str(p),
            "name": p.name,
            "suffix": p.suffix,
            "size_bytes": p.stat().st_size if p.exists() else "missing",
            "gitignore_runtime_artifact": True,
            "commit_allowed": p.name == ".gitignore",
        })

    write_csv(OUT / "fmm2b1_rcwa_api_smoke_results.csv", results)
    write_csv(OUT / "fmm2b1_artifact_manifest.csv", artifact_rows)
    write_csv(OUT / "fmm2b1_rcwa_api_smoke_attempt_log.csv", steps)

    summary = {
        "stage": "FMM2B1 tiny Lumerical RCWA/addrcwa API smoke test",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "git_status_short_at_generation": git(["status", "--short"]),
        "addrcwa_available": addrcwa_available,
        "rcwa_solver_object_created": rcwa_object_created,
        "tiny_run_completed": tiny_run_completed,
        "target_wavelength_nm": TARGET_WL_NM,
        "polarization": "x",
        "incidence": "normal",
        "model": "minimal periodic thin-film proxy, not H1J4 FSP",
        "h1j4_fsp_opened_or_modified": False,
        "fdtd_run_performed": False,
        "sweep_performed": False,
        "broadband_performed": False,
        "apcd_coupling_performed": False,
        "push_performed": False,
        "runtime_dir": str(RUNTIME),
        "runtime_fsp": str(result_fsp),
        "runtime_fsp_exists": result_fsp.exists(),
        "run_error": run_error,
        "outputs": [
            "fmm2b1_rcwa_api_smoke_summary.json",
            "fmm2b1_rcwa_api_smoke_results.csv",
            "fmm2b1_rcwa_api_smoke_report.md",
            "fmm2b1_artifact_manifest.csv",
            "fmm2b1_rcwa_api_smoke_attempt_log.csv",
        ],
    }
    (OUT / "fmm2b1_rcwa_api_smoke_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    verdict = "完成" if tiny_run_completed else "未完成"
    write_md(OUT / "fmm2b1_rcwa_api_smoke_report.md", f"""
# FMM2B1 tiny RCWA/addrcwa API smoke test

## 中文报告

1. addrcwa 是否可用：`{addrcwa_available}`
2. RCWA solver object 是否成功创建：`{rcwa_object_created}`
3. tiny run 是否完成：`{tiny_run_completed}` ({verdict})
4. 轻量结果摘要：目标波长 453 nm，x 偏振，法向入射；模型是最小周期 SiO2 薄膜 proxy，不是 H1J4 FSP。结果提取字段见 `fmm2b1_rcwa_api_smoke_results.csv`；若某个 Lumerical result 名称不可用，表中记录为 `missing`，没有伪造数值。
5. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 sweep；没有 broadband；没有 APCD coupling；没有 push。

Runtime artifacts are under `{RUNTIME}` and are gitignored. Heavy runtime files are not staged or committed.
""")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

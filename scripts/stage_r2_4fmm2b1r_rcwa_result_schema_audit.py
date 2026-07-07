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
OUT = ROOT / "outputs" / "r2_4fmm2b1r_rcwa_result_schema_audit"
RUNTIME = ROOT / "runtime" / "r2_4fmm2b1r_rcwa_result_schema_audit_DO_NOT_COMMIT"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
TARGET_WL_NM = 453.0
TARGET_WL_M = 453e-9
PREVIOUS_STAGE_COMMIT = "495fa32"
RCWA_OBJECT = "RCWA"
FORBIDDEN_STATEMENTS = {
    "fdtd_run_performed": False,
    "h1j4_fsp_opened_or_modified": False,
    "sweep_performed": False,
    "broadband_performed": False,
    "apcd_coupling_performed": False,
    "push_performed": False,
}
GITIGNORE = """*.fsp
*.fspx
*.ldf
*.mat
*.h5
*.hdf5
*.npz
*.npy
*.dat
*.raw
*.bin
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
RESULT_NAMES = ["total_energy", "substrate", "simulation_run_time", "index", "grating_power", "grating_orders"]


def safe_str(value: Any, limit: int = 1800) -> str:
    try:
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (dict, list, tuple)):
            text = json.dumps(value, default=str)
        else:
            text = str(value)
    except Exception:
        text = repr(value)
    return text[:limit]


def normalize(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    try:
        # numpy scalar-ish
        if hasattr(value, "item"):
            return value.item()
    except Exception:
        pass
    return value


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
    rows.append({"step": step, "object": object_name, "status": status, "detail": safe_str(detail)})


def try_call(rows: list[dict[str, Any]], step: str, func, object_name: str = "") -> tuple[bool, Any]:
    try:
        result = func()
        log(rows, step, "ok", result, object_name)
        return True, result
    except Exception as exc:
        log(rows, step, "failed", f"{type(exc).__name__}: {exc}", object_name)
        return False, None


def try_set_named(fdtd, rows: list[dict[str, Any]], obj: str, prop: str, value: Any) -> None:
    try_call(rows, f"setnamed {prop}", lambda: fdtd.setnamed(obj, prop, value), obj)


def try_set_current(fdtd, rows: list[dict[str, Any]], prop: str, value: Any, obj: str = "current") -> None:
    try_call(rows, f"set current {prop}", lambda: fdtd.set(prop, value), obj)


def dataset_fields(value: Any) -> dict[str, Any]:
    value = normalize(value)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            if str(key).startswith("Lumerical_dataset"):
                continue
            nval = normalize(val)
            if isinstance(nval, list):
                # Compact scalar/list preview. Most RCWA values are 1-point arrays here.
                if len(nval) == 1:
                    out[str(key)] = nval[0]
                else:
                    out[str(key)] = json.dumps(nval[:8], default=str)
            else:
                out[str(key)] = nval
        return out
    return {"value": safe_str(value)}


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / ".gitignore").write_text(GITIGNORE, encoding="utf-8")

    attempts: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    available_result_names: list[str] = []
    attempted_getresult_names: list[str] = []
    extracted: dict[str, Any] = {}
    summary: dict[str, Any] = {
        "stage": "FMM2B1R",
        "previous_stage_commit": PREVIOUS_STAGE_COMMIT,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "branch": git(["branch", "--show-current"]),
        "addrcwa_available": False,
        "rcwa_solver_object_created": False,
        "tiny_run_completed": False,
        "available_result_names": [],
        "attempted_getresult_names": RESULT_NAMES,
        "total_energy_available": False,
        "substrate_available": False,
        "simulation_run_time_available": False,
        "runtime_seconds": "missing",
        "n_lower": "missing",
        "n_upper": "missing",
        "result_schema_decision": "rcwa_result_schema_fail",
        "target_wavelength_nm": TARGET_WL_NM,
        "polarization_setup": "x-polarized plane wave proxy; normal incidence; do not assume x maps to a fixed s/p channel without convention audit",
        **FORBIDDEN_STATEMENTS,
    }

    try:
        lumapi = load_lumapi()
        log(attempts, "load_lumapi", "ok", str(LUMAPI))
        fdtd = lumapi.FDTD(hide=False)
        log(attempts, "open_lumerical_session", "ok", "new blank project; did not open H1J4 FSP")
        try_call(attempts, "switch_to_layout", lambda: fdtd.switchtolayout())

        ok, _ = try_call(attempts, "addrcwa", lambda: fdtd.addrcwa())
        summary["addrcwa_available"] = ok
        summary["rcwa_solver_object_created"] = ok
        if ok:
            try_set_current(fdtd, attempts, "name", RCWA_OBJECT, RCWA_OBJECT)
            for prop, value in [
                ("x", 0), ("y", 0), ("z", 0), ("x span", 1e-6), ("y span", 1e-6), ("z span", 0.8e-6),
                ("minimum wavelength", TARGET_WL_M), ("maximum wavelength", TARGET_WL_M), ("wavelength center", TARGET_WL_M),
                ("frequency points", 1), ("angle theta", 0), ("angle phi", 0),
                ("polarization angle", 0), ("incident angle", 0), ("azimuthal angle", 0),
                ("maximum number of k vectors", 3), ("max number k vectors", 3), ("harmonics", 1),
            ]:
                try_set_named(fdtd, attempts, RCWA_OBJECT, prop, value)
            try_call(attempts, "add_minimal_sio2_rect", lambda: fdtd.addrect())
            try_set_current(fdtd, attempts, "name", "tiny_sio2_film", "tiny_sio2_film")
            for prop, value in [("material", "sio222"), ("x", 0), ("y", 0), ("z", 0), ("x span", 1e-6), ("y span", 1e-6), ("z span", 100e-9)]:
                try_set_named(fdtd, attempts, "tiny_sio2_film", prop, value)

            run_ok, _ = try_call(attempts, "run_tiny_rcwa_model", lambda: fdtd.run(), RCWA_OBJECT)
            summary["tiny_run_completed"] = run_ok

            # Try result discovery first. API/script support varies; all failures are logged.
            ok_list, value_list = try_call(attempts, "discover_getresult_one_arg", lambda: fdtd.getresult(RCWA_OBJECT), RCWA_OBJECT)
            if ok_list:
                normalized = normalize(value_list)
                if isinstance(normalized, list):
                    available_result_names = [str(x) for x in normalized]
                elif isinstance(normalized, dict):
                    available_result_names = [str(x) for x in normalized.keys()]
                else:
                    available_result_names = [safe_str(normalized)]
            ok_eval, _ = try_call(attempts, "discover_getresult_script", lambda: fdtd.eval(f'__fmm2b1r_results=getresult("{RCWA_OBJECT}");'), RCWA_OBJECT)
            if ok_eval:
                ok_getv, val_getv = try_call(attempts, "discover_getresult_script_getv", lambda: fdtd.getv("__fmm2b1r_results"), RCWA_OBJECT)
                if ok_getv:
                    n = normalize(val_getv)
                    if isinstance(n, list):
                        available_result_names.extend(str(x) for x in n)
                    elif isinstance(n, dict):
                        available_result_names.extend(str(x) for x in n.keys())
                    else:
                        available_result_names.append(safe_str(n))
            expanded_names: list[str] = []
            for item in available_result_names:
                expanded_names.extend(str(item).split())
            available_result_names = sorted(set(x for x in expanded_names if x))
            summary["available_result_names"] = available_result_names

            for name in RESULT_NAMES:
                attempted_getresult_names.append(name)
                ok_res, val_res = try_call(attempts, f"getresult {name}", lambda n=name: fdtd.getresult(RCWA_OBJECT, n), RCWA_OBJECT)
                fields = dataset_fields(val_res) if ok_res else {}
                if ok_res:
                    extracted[name] = fields
                    if name not in available_result_names:
                        available_result_names.append(name)
                row = {
                    "result_name": name,
                    "available": ok_res,
                    "field_names": ";".join(str(k) for k in fields.keys()),
                    "fields_json": json.dumps(fields, default=str),
                    "preview": safe_str(fields),
                }
                # Promote common fields into columns for easy viewing.
                for key in ["Rs", "Ts", "Rp", "Tp", "R", "T", "n_lower", "n_upper", "runtime", "run_time", "simulation_run_time"]:
                    if key in fields:
                        row[key] = fields[key]
                result_rows.append(row)

            summary["total_energy_available"] = "total_energy" in extracted
            summary["substrate_available"] = "substrate" in extracted
            summary["simulation_run_time_available"] = "simulation_run_time" in extracted
            te = extracted.get("total_energy", {})
            for key in ["Rs", "Ts", "Rp", "Tp", "R", "T"]:
                if key in te:
                    summary[key] = te[key]
            sub = extracted.get("substrate", {})
            for key in ["n_lower", "n_upper"]:
                if key in sub:
                    summary[key] = sub[key]
            runtime_fields = extracted.get("simulation_run_time", {})
            for key in ["runtime", "run_time", "simulation_run_time", "value"]:
                if key in runtime_fields:
                    summary["runtime_seconds"] = runtime_fields[key]
                    break
            if summary["total_energy_available"]:
                summary["result_schema_decision"] = "rcwa_result_schema_pass_total_energy_extracted"
            elif summary["tiny_run_completed"]:
                summary["result_schema_decision"] = "rcwa_result_schema_partial_run_ok_total_energy_missing"
            else:
                summary["result_schema_decision"] = "rcwa_result_schema_fail"
        try_call(attempts, "close_lumerical_session", lambda: fdtd.close())
    except Exception as exc:
        log(attempts, "main_exception", "failed", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")

    summary["available_result_names"] = sorted(set(available_result_names))
    summary["attempted_getresult_names"] = sorted(set(attempted_getresult_names))
    summary["extracted_total_energy_fields"] = extracted.get("total_energy", {})
    summary["extracted_substrate_fields"] = extracted.get("substrate", {})
    summary["extracted_simulation_run_time_fields"] = extracted.get("simulation_run_time", {})

    for p in sorted(RUNTIME.glob("*")):
        artifact_rows.append({
            "path": str(p), "name": p.name, "suffix": p.suffix,
            "size_bytes": p.stat().st_size if p.exists() else "missing",
            "runtime_gitignored": True, "commit_allowed": p.name == ".gitignore",
        })

    write_csv(OUT / "fmm2b1r_rcwa_result_schema_results.csv", result_rows)
    write_csv(OUT / "fmm2b1r_rcwa_result_schema_attempt_log.csv", attempts)
    write_csv(OUT / "fmm2b1r_artifact_manifest.csv", artifact_rows)
    (OUT / "fmm2b1r_rcwa_result_schema_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    total_energy_status = "成功" if summary["total_energy_available"] else "未成功"
    total_energy_fields = json.dumps(summary.get("extracted_total_energy_fields", {}), ensure_ascii=False, default=str)
    write_md(OUT / "fmm2b1r_rcwa_result_schema_report.md", f"""
# FMM2B1R RCWA result-schema audit

## 中文报告

1. 本阶段做了 tiny RCWA result-schema follow-up：重新创建最小 SiO2 薄膜 RCWA proxy，453 nm，x 偏振设置，法向入射，只运行一次，不做 sweep。
2. 是否找到了 RCWA solver object 的正确结果名：`total_energy` 提取状态为 `{summary['total_energy_available']}`；可发现结果名记录为 `{summary['available_result_names']}`。
3. total_energy 是否提取成功：{total_energy_status}。
4. total_energy 字段和值：`{total_energy_fields}`。注意：不假定 x 偏振必然对应某个 s/p 通道，需结合 Lumerical 入射轴/角度约定解释 Rs/Ts/Rp/Tp。
5. substrate 可用：`{summary['substrate_available']}`；simulation_run_time 可用：`{summary['simulation_run_time_available']}`；runtime_seconds: `{summary['runtime_seconds']}`。
6. result_schema_decision: `{summary['result_schema_decision']}`。
7. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 sweep；没有 broadband；没有 APCD coupling；没有 push。
""")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

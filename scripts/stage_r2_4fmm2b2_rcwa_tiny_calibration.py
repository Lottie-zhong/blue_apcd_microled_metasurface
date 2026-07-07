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
OUT = ROOT / "outputs" / "r2_4fmm2b2_rcwa_tiny_calibration"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
RCWA_OBJECT = "RCWA"
STAGE = "FMM2B2"
PREVIOUS_SCHEMA_COMMIT = "1ea5369"
WL_NM = 453.0
WL_M = WL_NM * 1e-9
TIO2_N = 2.40
SIO2_N = 1.45
TIO2_THICK_NM = 45.0
SIO2_THICK_NM = 79.0
DBR_PAIRS = 10
ANGLES_DEG = [0.0]
RESULT_NAMES = ["total_energy", "substrate", "simulation_run_time"]
FORBIDDEN = {"fdtd_run_performed": False, "h1j4_fsp_opened_or_modified": False, "sweep_performed": False, "broadband_performed": False, "apcd_coupling_performed": False, "push_performed": False}


def safe_str(value: Any, limit: int = 2000) -> str:
    try:
        if hasattr(value, "tolist"):
            value = value.tolist()
        text = json.dumps(value, default=str) if isinstance(value, (dict, list, tuple)) else str(value)
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
        if hasattr(value, "item"):
            return value.item()
    except Exception:
        pass
    return value


def scalar(value: Any) -> Any:
    value = normalize(value)
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value


def fields(value: Any) -> dict[str, Any]:
    value = normalize(value)
    if not isinstance(value, dict):
        return {"value": scalar(value)}
    return {str(k): scalar(v) for k, v in value.items() if not str(k).startswith("Lumerical_dataset")}


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


def log(rows: list[dict[str, Any]], case_id: str, step: str, status: str, detail: Any = "") -> None:
    rows.append({"case_id": case_id, "step": step, "status": status, "detail": safe_str(detail)})


def try_call(rows: list[dict[str, Any]], case_id: str, step: str, func) -> tuple[bool, Any]:
    try:
        result = func()
        log(rows, case_id, step, "ok", result)
        return True, result
    except Exception as exc:
        log(rows, case_id, step, "failed", f"{type(exc).__name__}: {exc}")
        return False, None


def try_set(fdtd, rows: list[dict[str, Any]], case_id: str, obj: str, prop: str, value: Any) -> bool:
    ok, _ = try_call(rows, case_id, f"set {obj}.{prop}", lambda: fdtd.setnamed(obj, prop, value))
    return ok


def set_layer(fdtd, rows: list[dict[str, Any]], case_id: str, name: str, n_index: float, x_center_m: float, thickness_m: float) -> None:
    ok, _ = try_call(rows, case_id, f"add layer {name}", lambda: fdtd.addrect())
    if not ok:
        return
    try_call(rows, case_id, f"name layer {name}", lambda: fdtd.set("name", name))
    try_set(fdtd, rows, case_id, name, "material", "<Object defined dielectric>")
    try_set(fdtd, rows, case_id, name, "index", n_index)
    for prop, value in [("x", x_center_m), ("y", 0), ("z", 0), ("x span", thickness_m), ("y span", 1e-6), ("z span", 1e-6)]:
        try_set(fdtd, rows, case_id, name, prop, value)


def layers_for(case_id: str) -> list[tuple[str, float, float]]:
    if case_id == "air_reference":
        return []
    if case_id == "single_SiO2_proxy":
        return [("SiO2", SIO2_N, SIO2_THICK_NM)]
    if case_id == "single_TiO2_proxy":
        return [("TiO2", TIO2_N, TIO2_THICK_NM)]
    if case_id == "H1J4_like_bottom_DBR_QWinteger453_10pair_proxy":
        return [(mat, idx, thick) for _ in range(DBR_PAIRS) for mat, idx, thick in (("TiO2", TIO2_N, TIO2_THICK_NM), ("SiO2", SIO2_N, SIO2_THICK_NM))]
    raise ValueError(case_id)


def run_case(lumapi, case_id: str, angle_deg: float, attempts: list[dict[str, Any]]) -> dict[str, Any]:
    fdtd = None
    row: dict[str, Any] = {"stage": STAGE, "case_id": case_id, "wavelength_nm": WL_NM, "theta_deg_requested": angle_deg, "phi_deg_requested": 0.0, "polarization_setup": "x-polarized plane wave proxy; s/p mapping not assumed", "total_energy_available": False, "substrate_available": False, "simulation_run_time_available": False, "status": "failed"}
    try:
        fdtd = lumapi.FDTD(hide=False)
        log(attempts, case_id, "open_lumerical_session", "ok", "blank project; no H1J4 FSP")
        try_call(attempts, case_id, "switch_to_layout", lambda: fdtd.switchtolayout())
        ok, _ = try_call(attempts, case_id, "addrcwa", lambda: fdtd.addrcwa())
        if not ok:
            row["error"] = "addrcwa failed"
            return row
        for prop, value in [("x", 0), ("y", 0), ("z", 0), ("x span", 4e-6), ("y span", 1e-6), ("z span", 1e-6), ("minimum wavelength", WL_M), ("maximum wavelength", WL_M), ("wavelength center", WL_M), ("frequency points", 1), ("angle theta", angle_deg), ("angle phi", 0), ("polarization angle", 0), ("maximum number of k vectors", 3), ("max number k vectors", 3), ("harmonics", 1)]:
            try_set(fdtd, attempts, case_id, RCWA_OBJECT, prop, value)
        stack = layers_for(case_id)
        x_cursor_m = -0.5 * sum(thick for _, _, thick in stack) * 1e-9
        for idx, (material, n_index, thick_nm) in enumerate(stack, 1):
            thick_m = thick_nm * 1e-9
            set_layer(fdtd, attempts, case_id, f"{idx:02d}_{material}", n_index, x_cursor_m + 0.5 * thick_m, thick_m)
            x_cursor_m += thick_m
        run_ok, _ = try_call(attempts, case_id, "run_tiny_rcwa", lambda: fdtd.run())
        if not run_ok:
            row["error"] = "RCWA run failed"
            return row
        extracted: dict[str, dict[str, Any]] = {}
        for result_name in RESULT_NAMES:
            ok_res, val_res = try_call(attempts, case_id, f"getresult {result_name}", lambda rn=result_name: fdtd.getresult(RCWA_OBJECT, rn))
            if ok_res:
                extracted[result_name] = fields(val_res)
        te = extracted.get("total_energy", {})
        row["total_energy_available"] = bool(te)
        for key in ["lambda", "f", "theta", "phi", "Rs", "Ts", "Rp", "Tp"]:
            if key in te:
                row[key] = te[key]
        sub = extracted.get("substrate", {})
        row["substrate_available"] = bool(sub)
        for key in ["n_upper", "n_lower"]:
            if key in sub:
                row[key] = sub[key]
        rt = extracted.get("simulation_run_time", {})
        row["simulation_run_time_available"] = bool(rt)
        if "value" in rt:
            row["simulation_run_time_s"] = rt["value"]
        row["layer_count"] = len(stack)
        row["stack_total_thickness_nm"] = sum(thick for _, _, thick in stack)
        row["status"] = "ok" if te else "missing_total_energy"
        return row
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        log(attempts, case_id, "case_exception", "failed", row["error"] + "\n" + traceback.format_exc())
        return row
    finally:
        if fdtd is not None:
            try_call(attempts, case_id, "close_lumerical_session", lambda: fdtd.close())


def to_float(value: Any) -> float | None:
    try:
        return float(scalar(value))
    except Exception:
        return None


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    lumapi = load_lumapi()
    cases = ["air_reference", "single_SiO2_proxy", "single_TiO2_proxy", "H1J4_like_bottom_DBR_QWinteger453_10pair_proxy"]
    results = [run_case(lumapi, case_id, angle, attempts) for case_id in cases for angle in ANGLES_DEG]
    for row in results:
        for key in ["Rs", "Ts", "Rp", "Tp"]:
            if key in row:
                row[f"{key}_scalar"] = to_float(row[key])
        if row.get("Rs_scalar") is not None and row.get("Rp_scalar") is not None:
            row["R_avg_sp"] = 0.5 * (row["Rs_scalar"] + row["Rp_scalar"])
        if row.get("Ts_scalar") is not None and row.get("Tp_scalar") is not None:
            row["T_avg_sp"] = 0.5 * (row["Ts_scalar"] + row["Tp_scalar"])
    by_case = {r["case_id"]: r for r in results}
    ref_r = float(by_case.get("air_reference", {}).get("R_avg_sp") or 0.0)
    single_r_values = [float(by_case[c].get("R_avg_sp") or 0.0) for c in ["single_SiO2_proxy", "single_TiO2_proxy"] if c in by_case]
    dbr_r = float(by_case.get("H1J4_like_bottom_DBR_QWinteger453_10pair_proxy", {}).get("R_avg_sp") or 0.0)
    total_energy_ok = all(r.get("status") == "ok" for r in results)
    reference_transparent = (float(by_case.get("air_reference", {}).get("T_avg_sp") or 0.0) > 0.99) and abs(ref_r) < 1e-6
    dbr_stronger = dbr_r > max([ref_r, *single_r_values]) + 1e-3
    decision = "rcwa_tiny_calibration_pass" if total_energy_ok and reference_transparent and dbr_stronger else ("rcwa_tiny_calibration_partial" if total_energy_ok else "rcwa_tiny_calibration_fail")
    summary = {"stage": STAGE, "previous_schema_commit": PREVIOUS_SCHEMA_COMMIT, "created_at": datetime.now().isoformat(timespec="seconds"), "branch": git(["branch", "--show-current"]), "cases_actually_run": cases, "wavelength_nm": WL_NM, "angle_list_actually_run": ANGLES_DEG, "material_thickness_assumptions": {"TiO2_index_proxy": TIO2_N, "SiO2_index_proxy": SIO2_N, "TiO2_thickness_nm": TIO2_THICK_NM, "SiO2_thickness_nm": SIO2_THICK_NM, "DBR_pair_count": DBR_PAIRS, "materials_use_object_defined_dielectric": True, "stack_axis": "x (RCWA propagation direction forward)"}, "total_energy_all_cases_ok": total_energy_ok, "reference_transparent_sanity": reference_transparent, "dbr_like_stack_stronger_reflection_than_reference_or_single_layer": dbr_stronger, "air_reference_R_avg_sp": ref_r, "dbr_like_R_avg_sp": dbr_r, "decision": decision, **FORBIDDEN}
    write_csv(OUT / "fmm2b2_rcwa_tiny_calibration_results.csv", results)
    write_csv(OUT / "fmm2b2_rcwa_tiny_calibration_attempt_log.csv", attempts)
    write_csv(OUT / "fmm2b2_artifact_manifest.csv", artifacts)
    (OUT / "fmm2b2_rcwa_tiny_calibration_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    lines = ["# FMM2B2 tiny RCWA calibration", "", "## ????", "", f"stage = `{STAGE}`; previous_schema_commit = `{PREVIOUS_SCHEMA_COMMIT}`.", "", f"?? case: {', '.join(cases)}.", f"??: {WL_NM} nm; ??: {ANGLES_DEG}; x-polarized plane-wave proxy????? x ? s/p ??????", f"??/??: TiO2 {TIO2_THICK_NM} nm (n={TIO2_N}), SiO2 {SIO2_THICK_NM} nm (n={SIO2_N}), DBR pair count={DBR_PAIRS}.", "", "| case | Rs | Ts | Rp | Tp | R_avg | T_avg | status |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in results:
        lines.append(f"| {r['case_id']} | {r.get('Rs_scalar', 'missing')} | {r.get('Ts_scalar', 'missing')} | {r.get('Rp_scalar', 'missing')} | {r.get('Tp_scalar', 'missing')} | {r.get('R_avg_sp', 'missing')} | {r.get('T_avg_sp', 'missing')} | {r.get('status')} |")
    lines.extend(["", "## Sanity notes", "", f"- reference should be near transparent: `{reference_transparent}`.", f"- DBR-like stack should show stronger reflection than empty/single-layer proxy: `{dbr_stronger}`.", f"- decision: `{decision}`.", "- ??????? FDTD???????? H1J4 FSP??? sweep??? broadband??? APCD coupling??? push?"])
    write_md(OUT / "fmm2b2_rcwa_tiny_calibration_report.md", "\n".join(lines))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

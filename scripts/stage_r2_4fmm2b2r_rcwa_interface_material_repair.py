from __future__ import annotations

import csv
import importlib.util
import json
import math
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4fmm2b2r_rcwa_interface_material_repair"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
STAGE = "FMM2B2R"
PREVIOUS_COMMIT = "85aca83"
RCWA_OBJECT = "RCWA"
WL_NM = 453.0
WL_M = WL_NM * 1e-9
N_AIR = 1.0
N_SIO2 = 1.426
N_TIO2 = 2.535
SIO2_NM = 79.0
TIO2_NM = 45.0
DBR_PAIRS = 10
FORBIDDEN = {"fdtd_run_performed": False, "h1j4_fsp_opened_or_modified": False, "sweep_performed": False, "broadband_performed": False, "apcd_coupling_performed": False, "push_performed": False}
CASES = ["air_reference", "single_SiO2_79nm", "single_TiO2_45nm", "TiO2_SiO2_10pair_QWinteger453_proxy"]


def layers_for(case_id: str) -> list[tuple[str, float, float]]:
    if case_id == "air_reference":
        return []
    if case_id == "single_SiO2_79nm":
        return [("SiO2", N_SIO2, SIO2_NM)]
    if case_id == "single_TiO2_45nm":
        return [("TiO2", N_TIO2, TIO2_NM)]
    if case_id == "TiO2_SiO2_10pair_QWinteger453_proxy":
        return [(name, n, d) for _ in range(DBR_PAIRS) for name, n, d in (("TiO2", N_TIO2, TIO2_NM), ("SiO2", N_SIO2, SIO2_NM))]
    raise ValueError(case_id)


def safe_str(value: Any, limit: int = 2500) -> str:
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


def to_float(value: Any) -> float | None:
    try:
        return float(scalar(value))
    except Exception:
        return None


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


def tmm_rt(layers: list[tuple[str, float, float]], n_in: float = N_AIR, n_out: float = N_AIR) -> tuple[float, float]:
    # Normal incidence characteristic matrix, nonabsorbing media.
    m = np.identity(2, dtype=complex)
    for _, n, d_nm in layers:
        delta = 2.0 * math.pi * n * d_nm / WL_NM
        layer = np.array([[math.cos(delta), 1j * math.sin(delta) / n], [1j * n * math.sin(delta), math.cos(delta)]], dtype=complex)
        m = m @ layer
    denom = n_in * m[0, 0] + n_in * n_out * m[0, 1] + m[1, 0] + n_out * m[1, 1]
    r = (n_in * m[0, 0] + n_in * n_out * m[0, 1] - m[1, 0] - n_out * m[1, 1]) / denom
    t = 2.0 * n_in / denom
    R = abs(r) ** 2
    T = (n_out / n_in) * abs(t) ** 2
    return float(R.real), float(T.real)


def interface_positions(layers: list[tuple[str, float, float]]) -> list[float]:
    total_m = sum(d for _, _, d in layers) * 1e-9
    x = -0.5 * total_m
    positions = [x]
    for _, _, d_nm in layers:
        x += d_nm * 1e-9
        positions.append(x)
    return positions


def set_layer(fdtd, rows: list[dict[str, Any]], case_id: str, name: str, n_index: float, x_center_m: float, thickness_m: float) -> dict[str, Any]:
    layer_row = {"case_id": case_id, "object_name": name, "material_mode": "<Object defined dielectric>", "index": n_index, "x_center_m": x_center_m, "x_span_m": thickness_m, "y_span_m": 2e-6, "z_span_m": 2e-6}
    ok, _ = try_call(rows, case_id, f"add layer {name}", lambda: fdtd.addrect())
    if not ok:
        layer_row["status"] = "add_failed"
        return layer_row
    try_call(rows, case_id, f"name layer {name}", lambda: fdtd.set("name", name))
    for prop, value in [("material", "<Object defined dielectric>"), ("index", n_index), ("x", x_center_m), ("x span", thickness_m), ("y", 0), ("y span", 2e-6), ("z", 0), ("z span", 2e-6)]:
        try_set(fdtd, rows, case_id, name, prop, value)
    layer_row["status"] = "created"
    return layer_row


def run_rcwa_case(lumapi, case_id: str, attempts: list[dict[str, Any]], material_rows: list[dict[str, Any]]) -> dict[str, Any]:
    layers = layers_for(case_id)
    fdtd = None
    row: dict[str, Any] = {"stage": STAGE, "case_id": case_id, "wavelength_nm": WL_NM, "theta_deg": 0.0, "phi_deg": 0.0, "status": "failed", "total_energy_available": False, "interface_position_mode": "interface absolute positions", "propagation_axis": "x / RCWA forward", "stacking_axis": "x"}
    try:
        fdtd = lumapi.FDTD(hide=False)
        log(attempts, case_id, "open_lumerical_session", "ok", "blank project; no H1J4 FSP")
        try_call(attempts, case_id, "switch_to_layout", lambda: fdtd.switchtolayout())
        ok, _ = try_call(attempts, case_id, "addrcwa", lambda: fdtd.addrcwa())
        if not ok:
            row["error"] = "addrcwa failed"
            return row
        total_m = sum(d for _, _, d in layers) * 1e-9
        for prop, value in [("x", 0), ("x span", max(4e-6, total_m + 3e-6)), ("y", 0), ("y span", 2e-6), ("z", 0), ("z span", 2e-6), ("minimum wavelength", WL_M), ("maximum wavelength", WL_M), ("wavelength center", WL_M), ("frequency points", 1), ("angle theta", 0), ("angle phi", 0)]:
            try_set(fdtd, attempts, case_id, RCWA_OBJECT, prop, value)
        positions = interface_positions(layers) if layers else []
        if positions:
            arr = np.array(positions, dtype=float).reshape(1, -1)
            ok_if, _ = try_call(attempts, case_id, "set interface absolute positions", lambda: fdtd.setnamed(RCWA_OBJECT, "interface absolute positions", arr))
            row["interface_positions_set_ok"] = ok_if
            row["interface_positions_m"] = json.dumps(positions)
            got_ok, got = try_call(attempts, case_id, "get interface absolute positions", lambda: fdtd.getnamed(RCWA_OBJECT, "interface absolute positions"))
            if got_ok:
                row["interface_positions_readback"] = safe_str(got)
        else:
            row["interface_positions_set_ok"] = True
            row["interface_positions_m"] = "[]"
        x_cursor = -0.5 * total_m
        for idx, (mat, n, d_nm) in enumerate(layers, 1):
            d_m = d_nm * 1e-9
            material_rows.append(set_layer(fdtd, attempts, case_id, f"{idx:02d}_{mat}", n, x_cursor + 0.5 * d_m, d_m))
            x_cursor += d_m
        run_ok, _ = try_call(attempts, case_id, "run_tiny_rcwa", lambda: fdtd.run())
        if not run_ok:
            row["error"] = "RCWA run failed"
            return row
        available_ok, available = try_call(attempts, case_id, "discover getresult names", lambda: fdtd.getresult(RCWA_OBJECT))
        if available_ok:
            row["available_result_names"] = safe_str(str(available).split())
        extracted: dict[str, dict[str, Any]] = {}
        for name in ["total_energy", "substrate", "simulation_run_time"]:
            ok_res, val = try_call(attempts, case_id, f"getresult {name}", lambda n=name: fdtd.getresult(RCWA_OBJECT, n))
            if ok_res:
                extracted[name] = fields(val)
        te = extracted.get("total_energy", {})
        row["total_energy_available"] = bool(te)
        for key in ["lambda", "f", "theta", "phi", "Rs", "Ts", "Rp", "Tp"]:
            if key in te:
                row[key] = te[key]
                if key in ["Rs", "Ts", "Rp", "Tp"]:
                    row[f"{key}_scalar"] = to_float(te[key])
        if row.get("Rs_scalar") is not None and row.get("Rp_scalar") is not None:
            row["R_avg_sp"] = 0.5 * (row["Rs_scalar"] + row["Rp_scalar"])
        if row.get("Ts_scalar") is not None and row.get("Tp_scalar") is not None:
            row["T_avg_sp"] = 0.5 * (row["Ts_scalar"] + row["Tp_scalar"])
        sub = extracted.get("substrate", {})
        for key in ["n_upper", "n_lower"]:
            if key in sub:
                row[key] = sub[key]
        rt = extracted.get("simulation_run_time", {})
        if "value" in rt:
            row["simulation_run_time_s"] = rt["value"]
        row["layer_count"] = len(layers)
        row["stack_total_thickness_nm"] = sum(d for _, _, d in layers)
        row["layer_sequence"] = ";".join(f"{m}:{d}nm:n={n}" for m, n, d in layers)
        row["status"] = "ok" if te else "missing_total_energy"
        return row
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        log(attempts, case_id, "case_exception", "failed", row["error"] + "\n" + traceback.format_exc())
        return row
    finally:
        if fdtd is not None:
            try_call(attempts, case_id, "close_lumerical_session", lambda: fdtd.close())


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    material_rows: list[dict[str, Any]] = []
    lumapi = load_lumapi()

    tmm_rows = []
    for case_id in CASES:
        R, T = tmm_rt(layers_for(case_id))
        tmm_rows.append({"stage": STAGE, "case_id": case_id, "wavelength_nm": WL_NM, "substrate_convention": "air / stack / air", "tmm_R": R, "tmm_T": T, "layer_count": len(layers_for(case_id)), "stack_total_thickness_nm": sum(d for _, _, d in layers_for(case_id))})
    rcwa_rows = [run_rcwa_case(lumapi, case_id, attempts, material_rows) for case_id in CASES]
    by_case = {r["case_id"]: r for r in rcwa_rows}
    rcwa_nontrivial_10pair = float(by_case.get("TiO2_SiO2_10pair_QWinteger453_proxy", {}).get("R_avg_sp") or 0.0) > 1e-3
    rcwa_10pair_r = float(by_case.get("TiO2_SiO2_10pair_QWinteger453_proxy", {}).get("R_avg_sp") or 0.0)
    rcwa_air_r = float(by_case.get("air_reference", {}).get("R_avg_sp") or 0.0)
    rcwa_single_max = max(float(by_case.get(c, {}).get("R_avg_sp") or 0.0) for c in ["single_SiO2_79nm", "single_TiO2_45nm"])
    tmm_10pair_r = next(r["tmm_R"] for r in tmm_rows if r["case_id"] == "TiO2_SiO2_10pair_QWinteger453_proxy")
    tmm_nontrivial_10pair = tmm_10pair_r > 1e-3
    rcwa_10pair_stronger = rcwa_10pair_r > max(rcwa_air_r, rcwa_single_max) + 1e-3
    if tmm_nontrivial_10pair and rcwa_nontrivial_10pair and rcwa_10pair_stronger:
        decision = "rcwa_interface_material_repair_pass"
    elif tmm_nontrivial_10pair and rcwa_nontrivial_10pair:
        decision = "rcwa_interface_material_repair_partial"
    else:
        decision = "rcwa_interface_material_repair_fail"
    summary = {"stage": STAGE, "previous_commit": PREVIOUS_COMMIT, "created_at": datetime.now().isoformat(timespec="seconds"), "branch": git(["branch", "--show-current"]), "root_issue_hypothesis": "FMM2B2 created geometry objects but did not explicitly provide RCWA interface positions, so material interfaces were not represented in total_energy.", "wavelength_nm": WL_NM, "interface_position_mode_used": "interface absolute positions", "propagation_axis": "x / RCWA forward", "stacking_axis": "x", "material_index_assumptions": {"air": N_AIR, "SiO2": N_SIO2, "TiO2": N_TIO2}, "thickness_nm": {"SiO2": SIO2_NM, "TiO2": TIO2_NM}, "dbr_pair_count": DBR_PAIRS, "tmm_oracle_10pair_R": tmm_10pair_r, "rcwa_10pair_R_avg_sp": rcwa_10pair_r, "nontrivial_reflection_recovered": rcwa_nontrivial_10pair, "h1j4_like_10pair_more_reflective_than_air_and_single_layer": rcwa_10pair_stronger, "decision": decision, **FORBIDDEN}
    write_csv(OUT / "fmm2b2r_rcwa_interface_material_repair_results.csv", rcwa_rows)
    write_csv(OUT / "fmm2b2r_rcwa_interface_material_repair_tmm_oracle.csv", tmm_rows)
    write_csv(OUT / "fmm2b2r_rcwa_interface_material_repair_attempt_log.csv", attempts)
    write_csv(OUT / "fmm2b2r_material_index_assignment.csv", material_rows)
    write_csv(OUT / "fmm2b2r_artifact_manifest.csv", [])
    (OUT / "fmm2b2r_rcwa_interface_material_repair_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    lines = ["# FMM2B2R RCWA interface/material inclusion repair", "", "## ????", "", f"stage = `{STAGE}`; previous_commit = `{PREVIOUS_COMMIT}`.", "", f"?????{summary['root_issue_hypothesis']}", "", "## TMM oracle", "", "| case | R | T |", "|---|---:|---:|"]
    for r in tmm_rows:
        lines.append(f"| {r['case_id']} | {r['tmm_R']} | {r['tmm_T']} |")
    lines += ["", "## RCWA repaired total_energy", "", "| case | Rs | Ts | Rp | Tp | R_avg | T_avg | status |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in rcwa_rows:
        lines.append(f"| {r['case_id']} | {r.get('Rs_scalar','missing')} | {r.get('Ts_scalar','missing')} | {r.get('Rp_scalar','missing')} | {r.get('Tp_scalar','missing')} | {r.get('R_avg_sp','missing')} | {r.get('T_avg_sp','missing')} | {r.get('status')} |")
    lines += ["", "## Decision", "", f"- interface_position_mode: `{summary['interface_position_mode_used']}`.", f"- propagation_axis / stacking_axis: `{summary['propagation_axis']}` / `{summary['stacking_axis']}`.", f"- nontrivial_reflection_recovered: `{rcwa_nontrivial_10pair}`.", f"- H1J4-like 10-pair stronger than air/single-layer proxies: `{rcwa_10pair_stronger}`.", f"- decision: `{decision}`.", "- ??????? FDTD???????? H1J4 FSP??? sweep??? broadband??? APCD coupling??? push?"]
    write_md(OUT / "fmm2b2r_rcwa_interface_material_repair_report.md", "\n".join(lines))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

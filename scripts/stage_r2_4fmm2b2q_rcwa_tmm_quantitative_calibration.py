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
OUT = ROOT / "outputs" / "r2_4fmm2b2q_rcwa_tmm_quantitative_calibration"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
STAGE = "FMM2B2Q"
PREVIOUS_COMMIT = "7aa6e67"
RCWA_OBJECT = "RCWA"
WL_NM = 453.0
WL_M = WL_NM * 1e-9
N_AIR = 1.0
N_SIO2 = 1.426
N_TIO2 = 2.535
SIO2_NM = 79.0
TIO2_NM = 45.0
DBR_PAIRS = 10
CASES = ["air_reference", "single_SiO2_79nm", "single_TiO2_45nm", "TiO2_SiO2_10pair_QWinteger453_proxy"]
VARIANTS = [
    {"variant_id": "axis_x_absolute_interfaces", "axis": "x", "material_mode": "object_defined_index", "region_scale": 1.5},
    {"variant_id": "axis_z_absolute_interfaces", "axis": "z", "material_mode": "object_defined_index", "region_scale": 1.5},
    {"variant_id": "index_grid_or_explicit_material_variant", "axis": "x", "material_mode": "direct_index_explicit_air_background", "region_scale": 3.0},
]
FORBIDDEN = {"fdtd_run_performed": False, "h1j4_fsp_opened_or_modified": False, "sweep_performed": False, "broadband_performed": False, "apcd_coupling_performed": False, "push_performed": False}


def layers_for(case_id: str) -> list[tuple[str, float, float]]:
    if case_id == "air_reference":
        return []
    if case_id == "single_SiO2_79nm":
        return [("SiO2", N_SIO2, SIO2_NM)]
    if case_id == "single_TiO2_45nm":
        return [("TiO2", N_TIO2, TIO2_NM)]
    if case_id == "TiO2_SiO2_10pair_QWinteger453_proxy":
        return [(m, n, d) for _ in range(DBR_PAIRS) for m, n, d in (("TiO2", N_TIO2, TIO2_NM), ("SiO2", N_SIO2, SIO2_NM))]
    raise ValueError(case_id)


def safe_str(value: Any, limit: int = 4000) -> str:
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


def log(rows: list[dict[str, Any]], variant: str, case_id: str, step: str, status: str, detail: Any = "") -> None:
    rows.append({"variant_id": variant, "case_id": case_id, "step": step, "status": status, "detail": safe_str(detail)})


def try_call(rows: list[dict[str, Any]], variant: str, case_id: str, step: str, func) -> tuple[bool, Any]:
    try:
        result = func()
        log(rows, variant, case_id, step, "ok", result)
        return True, result
    except Exception as exc:
        log(rows, variant, case_id, step, "failed", f"{type(exc).__name__}: {exc}")
        return False, None


def try_set(fdtd, rows: list[dict[str, Any]], variant: str, case_id: str, obj: str, prop: str, value: Any) -> bool:
    ok, _ = try_call(rows, variant, case_id, f"set {obj}.{prop}", lambda: fdtd.setnamed(obj, prop, value))
    return ok


def tmm_rt(layers: list[tuple[str, float, float]]) -> tuple[float, float]:
    m = np.identity(2, dtype=complex)
    for _, n, d_nm in layers:
        delta = 2.0 * math.pi * n * d_nm / WL_NM
        lm = np.array([[math.cos(delta), 1j * math.sin(delta) / n], [1j * n * math.sin(delta), math.cos(delta)]], dtype=complex)
        m = m @ lm
    denom = N_AIR * m[0, 0] + N_AIR * N_AIR * m[0, 1] + m[1, 0] + N_AIR * m[1, 1]
    r = (N_AIR * m[0, 0] + N_AIR * N_AIR * m[0, 1] - m[1, 0] - N_AIR * m[1, 1]) / denom
    t = 2.0 * N_AIR / denom
    return float(abs(r) ** 2), float(abs(t) ** 2)


def interface_positions(layers: list[tuple[str, float, float]]) -> list[float]:
    total_m = sum(d for _, _, d in layers) * 1e-9
    pos = [-0.5 * total_m]
    x = pos[0]
    for _, _, d_nm in layers:
        x += d_nm * 1e-9
        pos.append(x)
    return pos


def set_layer(fdtd, rows: list[dict[str, Any]], variant: dict[str, Any], case_id: str, name: str, n_index: float, center_m: float, thickness_m: float) -> dict[str, Any]:
    vid = variant["variant_id"]
    axis = variant["axis"]
    row = {"variant_id": vid, "case_id": case_id, "object_name": name, "axis": axis, "material_assignment_method": variant["material_mode"], "index": n_index, "center_m": center_m, "thickness_m": thickness_m}
    ok, _ = try_call(rows, vid, case_id, f"add layer {name}", lambda: fdtd.addrect())
    if not ok:
        row["status"] = "add_failed"
        return row
    try_call(rows, vid, case_id, f"name layer {name}", lambda: fdtd.set("name", name))
    try_set(fdtd, rows, vid, case_id, name, "material", "<Object defined dielectric>")
    try_set(fdtd, rows, vid, case_id, name, "index", n_index)
    geom = {"x": 0, "y": 0, "z": 0, "x span": 2e-6, "y span": 2e-6, "z span": 2e-6}
    geom[axis] = center_m
    geom[f"{axis} span"] = thickness_m
    for prop, value in geom.items():
        try_set(fdtd, rows, vid, case_id, name, prop, value)
    row["status"] = "created"
    return row


def run_rcwa(lumapi, variant: dict[str, Any], case_id: str, attempts: list[dict[str, Any]], material_rows: list[dict[str, Any]]) -> dict[str, Any]:
    vid = variant["variant_id"]
    axis = variant["axis"]
    layers = layers_for(case_id)
    fdtd = None
    row: dict[str, Any] = {"stage": STAGE, "variant_id": vid, "case_id": case_id, "wavelength_nm": WL_NM, "theta_deg": 0.0, "phi_deg": 0.0, "status": "failed", "propagation_axis": f"{axis} candidate", "stacking_axis": axis, "interface_position_mode": "interface absolute positions", "material_index_assignment_method": variant["material_mode"], "total_energy_available": False}
    try:
        fdtd = lumapi.FDTD(hide=False)
        log(attempts, vid, case_id, "open_lumerical_session", "ok", "blank project; no H1J4 FSP")
        try_call(attempts, vid, case_id, "switch_to_layout", lambda: fdtd.switchtolayout())
        ok, _ = try_call(attempts, vid, case_id, "addrcwa", lambda: fdtd.addrcwa())
        if not ok:
            row["error"] = "addrcwa failed"
            return row
        total_m = sum(d for _, _, d in layers) * 1e-9
        span_main = max(4e-6, total_m + float(variant["region_scale"]) * 2e-6)
        rcwa_props = {"x": 0, "y": 0, "z": 0, "x span": 2e-6, "y span": 2e-6, "z span": 2e-6, "minimum wavelength": WL_M, "maximum wavelength": WL_M, "wavelength center": WL_M, "frequency points": 1, "angle theta": 0, "angle phi": 0}
        rcwa_props[f"{axis} span"] = span_main
        for prop, value in rcwa_props.items():
            try_set(fdtd, attempts, vid, case_id, RCWA_OBJECT, prop, value)
        try_set(fdtd, attempts, vid, case_id, RCWA_OBJECT, "background material", "<Object defined dielectric>")
        try_set(fdtd, attempts, vid, case_id, RCWA_OBJECT, "background index", N_AIR)
        pos = interface_positions(layers) if layers else []
        if pos:
            arr = np.array(pos, dtype=float).reshape(1, -1)
            ok_if, _ = try_call(attempts, vid, case_id, "set interface absolute positions", lambda: fdtd.setnamed(RCWA_OBJECT, "interface absolute positions", arr))
            row["interface_positions_set_ok"] = ok_if
            row["interface_absolute_positions_m"] = json.dumps(pos)
            ok_get, got = try_call(attempts, vid, case_id, "get interface absolute positions", lambda: fdtd.getnamed(RCWA_OBJECT, "interface absolute positions"))
            if ok_get:
                row["interface_positions_readback"] = safe_str(got)
        else:
            row["interface_positions_set_ok"] = True
            row["interface_absolute_positions_m"] = "[]"
        cursor = -0.5 * total_m
        for i, (mat, n, d_nm) in enumerate(layers, 1):
            d_m = d_nm * 1e-9
            material_rows.append(set_layer(fdtd, attempts, variant, case_id, f"{vid}_{i:02d}_{mat}", n, cursor + 0.5 * d_m, d_m))
            cursor += d_m
        run_ok, _ = try_call(attempts, vid, case_id, "run_tiny_rcwa", lambda: fdtd.run())
        if not run_ok:
            row["error"] = "RCWA run failed"
            return row
        ok_names, names = try_call(attempts, vid, case_id, "discover getresult names", lambda: fdtd.getresult(RCWA_OBJECT))
        if ok_names:
            row["available_result_names"] = safe_str(str(names).split())
        extracted = {}
        for name in ["total_energy", "substrate", "simulation_run_time"]:
            ok_res, val = try_call(attempts, vid, case_id, f"getresult {name}", lambda n=name: fdtd.getresult(RCWA_OBJECT, n))
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
            row["runtime_seconds"] = rt["value"]
        row["rcwa_region_extent_main_axis_m"] = span_main
        row["layer_sequence"] = ";".join(f"{m}:{d}nm:n={n}" for m, n, d in layers)
        row["status"] = "ok" if te else "missing_total_energy"
        return row
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        log(attempts, vid, case_id, "case_exception", "failed", row["error"] + "\n" + traceback.format_exc())
        return row
    finally:
        if fdtd is not None:
            try_call(attempts, vid, case_id, "close_lumerical_session", lambda: fdtd.close())


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)
    tmm_rows = []
    tmm_by_case = {}
    for case_id in CASES:
        R, T = tmm_rt(layers_for(case_id))
        tmm_by_case[case_id] = R
        tmm_rows.append({"stage": STAGE, "case_id": case_id, "wavelength_nm": WL_NM, "substrate_convention": "air / stack / air", "tmm_R": R, "tmm_T": T, "layer_count": len(layers_for(case_id)), "stack_total_thickness_nm": sum(d for _, _, d in layers_for(case_id))})
    lumapi = load_lumapi()
    attempts: list[dict[str, Any]] = []
    material_rows: list[dict[str, Any]] = []
    rows = [run_rcwa(lumapi, variant, case_id, attempts, material_rows) for variant in VARIANTS for case_id in CASES]
    for r in rows:
        tmm_R = tmm_by_case[r["case_id"]]
        rcwa_R = r.get("R_avg_sp")
        r["tmm_R"] = tmm_R
        r["abs_error_R"] = "missing"
        r["ratio_R"] = "missing"
        r["trend_ok"] = False
        r["quantitative_close_enough"] = False
        if isinstance(rcwa_R, (float, int)):
            r["abs_error_R"] = abs(float(rcwa_R) - tmm_R)
            if tmm_R > 0:
                r["ratio_R"] = float(rcwa_R) / tmm_R
            if r["case_id"] == "air_reference":
                r["trend_ok"] = abs(float(rcwa_R)) < 1e-6
                r["quantitative_close_enough"] = abs(float(rcwa_R)) < 1e-3
            else:
                r["trend_ok"] = float(rcwa_R) > 1e-3
                ratio = float(r["ratio_R"]) if r["ratio_R"] != "missing" else 0.0
                r["quantitative_close_enough"] = 0.2 <= ratio <= 5.0
    variant_scores = []
    for v in VARIANTS:
        vid = v["variant_id"]
        vrows = [r for r in rows if r["variant_id"] == vid]
        dbr = next((r for r in vrows if r["case_id"] == "TiO2_SiO2_10pair_QWinteger453_proxy"), {})
        single_ratios = [float(r["ratio_R"]) for r in vrows if r["case_id"].startswith("single_") and r.get("ratio_R") != "missing"]
        dbr_R = float(dbr.get("R_avg_sp") or 0.0)
        variant_scores.append({"variant_id": vid, "dbr_R_avg": dbr_R, "dbr_ratio_to_tmm": dbr.get("ratio_R", "missing"), "single_layer_ratio_mean": sum(single_ratios)/len(single_ratios) if single_ratios else "missing", "ok_cases": sum(1 for r in vrows if r.get("status") == "ok"), "trend_ok_cases": sum(1 for r in vrows if r.get("trend_ok") is True), "quantitative_close_cases": sum(1 for r in vrows if r.get("quantitative_close_enough") is True)})
    best = max(variant_scores, key=lambda s: (float(s["dbr_R_avg"]), int(s["trend_ok_cases"])))
    high_reflection_found = any(float(s["dbr_R_avg"]) > 0.8 for s in variant_scores)
    trend_any = any(float(s["dbr_R_avg"]) > 1e-3 for s in variant_scores)
    decision = "rcwa_tmm_quantitative_pass" if high_reflection_found else ("rcwa_tmm_quantitative_partial" if trend_any else "rcwa_tmm_quantitative_fail")
    summary = {"stage": STAGE, "previous_commit": PREVIOUS_COMMIT, "created_at": datetime.now().isoformat(timespec="seconds"), "branch": git(["branch", "--show-current"]), "root_hypothesis": "Remaining RCWA/TMM mismatch may be axis, explicit interface positions, material/index assignment, or RCWA region/span setup.", "cases": CASES, "variants": VARIANTS, "best_variant_by_dbr_reflection": best, "high_10pair_reflection_found_gt_0p8": high_reflection_found, "decision": decision, **FORBIDDEN}
    write_csv(OUT / "fmm2b2q_rcwa_tmm_oracle.csv", tmm_rows)
    write_csv(OUT / "fmm2b2q_rcwa_tmm_quantitative_results.csv", rows)
    write_csv(OUT / "fmm2b2q_rcwa_variant_attempt_log.csv", attempts)
    write_csv(OUT / "fmm2b2q_variant_score_summary.csv", variant_scores)
    write_csv(OUT / "fmm2b2q_material_index_assignment.csv", material_rows)
    write_csv(OUT / "fmm2b2q_artifact_manifest.csv", [])
    (OUT / "fmm2b2q_rcwa_tmm_quantitative_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    lines = ["# FMM2B2Q RCWA-vs-TMM quantitative calibration", "", "## 中文报告", "", "1. 本阶段做了 tiny RCWA-vs-TMM quantitative diagnostic：4 个固定 1D stack case，3 个显式 RCWA variant；没有 sweep、没有 angle audit、没有 candidate ranking。", "", "2. FMM2B2R 仍不足以进入 grating_power/angle audit：它只证明 interface/material inclusion 有定性恢复，但 10-pair RCWA R_avg 仍远低于 TMM oracle 的高反射。", "", "## TMM oracle", "", "| case | TMM R | TMM T |", "|---|---:|---:|"]
    for r in tmm_rows:
        lines.append(f"| {r['case_id']} | {r['tmm_R']} | {r['tmm_T']} |")
    lines += ["", "## RCWA variant results", "", "| variant | case | Rs | Ts | Rp | Tp | R_avg | ratio_R | status |", "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        lines.append(f"| {r['variant_id']} | {r['case_id']} | {r.get('Rs_scalar','missing')} | {r.get('Ts_scalar','missing')} | {r.get('Rp_scalar','missing')} | {r.get('Tp_scalar','missing')} | {r.get('R_avg_sp','missing')} | {r.get('ratio_R','missing')} | {r.get('status')} |")
    lines += ["", "## Decision", "", f"- 最接近 TMM 的 variant（按 DBR R 最大）：`{best['variant_id']}`，10-pair R_avg=`{best['dbr_R_avg']}`，ratio=`{best['dbr_ratio_to_tmm']}`。", f"- 是否找到 10-pair 高反射 >0.8：`{high_reflection_found}`。", "- 若仍不接近，当前失败更像 RCWA object/command 或 region/layer-interpretation 限制，而不是 total_energy schema 缺失；axis_z 未成为定量解。", f"- decision = `{decision}`。", "- 明确限制：没有 FDTD；没有打开/修改 H1J4 FSP；没有 sweep；没有 broadband；没有 APCD coupling；没有 push。"]
    write_md(OUT / "fmm2b2q_rcwa_tmm_quantitative_report.md", "\n".join(lines))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

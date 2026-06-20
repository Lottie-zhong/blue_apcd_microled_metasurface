from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

import stage10_cp_route_b4_integer_plane_wave_screen as b4

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b4_3_tolerance_plane_wave_screen"
SAVED_FSP_DIR = OUT_DIR / "_saved_fsp"
NOMINAL_METRICS_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b4_integer_plane_wave_screen" / "route_b4_integer_plane_wave_metrics.csv"
NOMINAL_ID = "TOL_NOMINAL_D194_T90_PSI97"
FROZEN_ID = "B4INT_J1J2_D194_T90_PSI97_H525"
INTEGER_TOL = 1e-8


def nominal_geometry() -> dict[str, float]:
    return {
        "J1_x_nm": 0.0, "J1_y_nm": 97.0, "J2_x_nm": 0.0, "J2_y_nm": -97.0,
        "J1_rotation_deg": -7.0, "J2_rotation_deg": 38.0,
        "J1_L_nm": 230.0, "J1_W_nm": 100.0, "J2_L_nm": 180.0, "J2_W_nm": 90.0,
    }


def tolerance_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(case_id: str, tolerance_type: str, **updates: float) -> None:
        geometry = nominal_geometry()
        geometry.update(updates)
        cases.append({"case_id": case_id, "tolerance_type": tolerance_type, **geometry})

    add("TOL_J1_XP2", "relative_x_offset", J1_x_nm=2.0)
    add("TOL_J1_XM2", "relative_x_offset", J1_x_nm=-2.0)
    add("TOL_J2_XP2", "relative_x_offset", J2_x_nm=2.0)
    add("TOL_J2_XM2", "relative_x_offset", J2_x_nm=-2.0)
    add("TOL_J1_YP2", "relative_y_offset", J1_y_nm=99.0)
    add("TOL_J1_YM2", "relative_y_offset", J1_y_nm=95.0)
    add("TOL_J2_YP2", "relative_y_offset", J2_y_nm=-95.0)
    add("TOL_J2_YM2", "relative_y_offset", J2_y_nm=-99.0)
    add("TOL_J1_ROT_P1", "rotation", J1_rotation_deg=-6.0)
    add("TOL_J1_ROT_M1", "rotation", J1_rotation_deg=-8.0)
    add("TOL_J2_ROT_P1", "rotation", J2_rotation_deg=39.0)
    add("TOL_J2_ROT_M1", "rotation", J2_rotation_deg=37.0)
    add("TOL_SIZE_ALL_P2", "uniform_size", J1_L_nm=232.0, J1_W_nm=102.0, J2_L_nm=182.0, J2_W_nm=92.0)
    add("TOL_SIZE_ALL_M2", "uniform_size", J1_L_nm=228.0, J1_W_nm=98.0, J2_L_nm=178.0, J2_W_nm=88.0)
    return cases


CASES = tolerance_cases()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage10 CP Route B4-3 fabrication tolerance periodic +z plane-wave screen only.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--simulation-time-fs", type=float, default=b4.SIM_TIME_FS)
    parser.add_argument("--mesh-accuracy", type=int, default=3)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def is_integer(value: float) -> bool:
    return abs(value - round(value)) <= INTEGER_TOL


def geometry_audit(case: dict[str, Any]) -> dict[str, Any]:
    dx_j2_minus_j1 = float(case["J2_x_nm"]) - float(case["J1_x_nm"])
    dy_j2_minus_j1 = float(case["J2_y_nm"]) - float(case["J1_y_nm"])
    dx_j1_minus_j2 = -dx_j2_minus_j1
    dy_j1_minus_j2 = -dy_j2_minus_j1
    effective_d = math.hypot(dx_j1_minus_j2, dy_j1_minus_j2)
    effective_theta = math.degrees(math.atan2(dy_j1_minus_j2, dx_j1_minus_j2))
    coords = [float(case[key]) for key in ("J1_x_nm", "J1_y_nm", "J2_x_nm", "J2_y_nm")]
    rotations = [float(case[key]) for key in ("J1_rotation_deg", "J2_rotation_deg")]
    dimensions = [float(case[key]) for key in ("J1_L_nm", "J1_W_nm", "J2_L_nm", "J2_W_nm")]
    coordinate_ready = all(is_integer(value) for value in coords)
    rotation_ready = all(is_integer(value) for value in rotations)
    dimension_ready = all(is_integer(value) for value in dimensions)
    return {
        "case_id": case["case_id"],
        "tolerance_type": case["tolerance_type"],
        **{key: int(round(float(case[key]))) for key in ("J1_x_nm", "J1_y_nm", "J2_x_nm", "J2_y_nm", "J1_rotation_deg", "J2_rotation_deg", "J1_L_nm", "J1_W_nm", "J2_L_nm", "J2_W_nm")},
        "delta_x_nm": b4.fnum(dx_j2_minus_j1),
        "delta_y_nm": b4.fnum(dy_j2_minus_j1),
        "x_bias_abs_nm": b4.fnum(abs(dx_j2_minus_j1)),
        "effective_d_nm": b4.fnum(effective_d),
        "effective_theta_deg": b4.fnum(effective_theta),
        "coordinate_integer_ready": str(coordinate_ready).lower(),
        "rotation_integer_ready": str(rotation_ready).lower(),
        "fabrication_integer_ready": str(coordinate_ready and rotation_ready and dimension_ready).lower(),
        "note": "Integer-valued tolerance variant; effective d/theta are audit quantities, not fabrication instructions.",
    }


def case_table() -> list[dict[str, Any]]:
    nominal = {"case_id": NOMINAL_ID, "tolerance_type": "nominal_reference_reused", **nominal_geometry()}
    rows = [geometry_audit(nominal)]
    rows.extend(geometry_audit(case) for case in CASES)
    return rows


def add_pillars(fdtd: object, case: dict[str, Any]) -> None:
    roles = [
        ("J1", case["J1_x_nm"], case["J1_y_nm"], case["J1_L_nm"], case["J1_W_nm"], case["J1_rotation_deg"]),
        ("J2", case["J2_x_nm"], case["J2_y_nm"], case["J2_L_nm"], case["J2_W_nm"], case["J2_rotation_deg"]),
    ]
    for role, x_nm, y_nm, length_nm, width_nm, rotation_deg in roles:
        fdtd.addrect()
        fdtd.set("name", f"{role}_pillar")
        fdtd.set("x", float(x_nm) * b4.NM)
        fdtd.set("y", float(y_nm) * b4.NM)
        fdtd.set("x span", float(length_nm) * b4.NM)
        fdtd.set("y span", float(width_nm) * b4.NM)
        fdtd.set("z min", 0.0)
        fdtd.set("z max", b4.HEIGHT_NM * b4.NM)
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", float(rotation_deg))
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", b4.MATERIAL_INDEX)


def build_model(fdtd: object, case: dict[str, Any], linear_input: str, sim_time_fs: float, mesh_accuracy: int) -> None:
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z min", b4.Z_MIN_NM * b4.NM)
    fdtd.set("z max", b4.Z_MAX_NM * b4.NM)
    for prop in ("x min bc", "x max bc", "y min bc", "y max bc"):
        fdtd.set(prop, "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", int(mesh_accuracy))
    fdtd.set("simulation time", sim_time_fs * 1e-15)
    add_pillars(fdtd, case)
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z", b4.SOURCE_Z_NM * b4.NM)
    fdtd.set("wavelength start", b4.WAVELENGTH_NM * b4.NM)
    fdtd.set("wavelength stop", b4.WAVELENGTH_NM * b4.NM)
    fdtd.set("polarization angle", 0.0 if linear_input == "x" else 90.0)
    fdtd.addpower()
    fdtd.set("name", b4.POWER_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z", b4.MONITOR_Z_NM * b4.NM)
    fdtd.addprofile()
    fdtd.set("name", b4.FIELD_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", b4.PERIOD_X_NM * b4.NM)
    fdtd.set("y span", b4.PERIOD_Y_NM * b4.NM)
    fdtd.set("z", b4.MONITOR_Z_NM * b4.NM)


def fsp_complete(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 500_000


def run_one(lumapi: Any, runtime: Any, out_dir: Path, case: dict[str, Any], linear_input: str, args: argparse.Namespace) -> dict[str, Any]:
    fsp = out_dir / "_saved_fsp" / f"{case['case_id']}_{linear_input.upper()}IN.fsp"
    if fsp_complete(fsp) and not args.force:
        return {"case_id": case["case_id"], "linear_input": linear_input, "fdtd_status": "reused", "result_fsp": str(fsp), "note": "completed periodic FSP reused"}
    if args.dry_run:
        return {"case_id": case["case_id"], "linear_input": linear_input, "fdtd_status": "not_run", "result_fsp": str(fsp), "note": "dry run"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        build_model(fdtd, case, linear_input, args.simulation_time_fs, args.mesh_accuracy)
        fdtd.save(str(fsp.resolve()))
    finally:
        if fdtd is not None:
            fdtd.close()
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        fdtd.run()
        fdtd.save(str(fsp.resolve()))
        return {"case_id": case["case_id"], "linear_input": linear_input, "fdtd_status": "ok", "result_fsp": str(fsp), "note": "setup/save/load/run/save complete"}
    except Exception as exc:
        return {"case_id": case["case_id"], "linear_input": linear_input, "fdtd_status": "failed", "result_fsp": str(fsp), "note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def extract_metrics(lumapi: Any, runtime: Any, out_dir: Path, case: dict[str, Any], show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    fields: list[tuple[complex | None, complex | None]] = []
    statuses: list[str] = []
    debug: dict[str, Any] = {}
    for linear_input in ("X", "Y"):
        fsp = out_dir / "_saved_fsp" / f"{case['case_id']}_{linear_input}IN.fsp"
        status, ex, ey, meta = b4.extract_linear(None if False else lumapi, runtime, fsp, show_gui)
        statuses.append(status)
        fields.append((ex, ey))
        debug[linear_input] = meta
    if statuses != ["ok", "ok"] or any(value is None for pair in fields for value in pair):
        return {"case_id": case["case_id"], "tolerance_type": case["tolerance_type"], "status": "missing_or_failed", "note": f"X={statuses[0]}; Y={statuses[1]}"}, debug
    exx, eyx = fields[0]
    exy, eyy = fields[1]
    jones = np.array([[exx, exy], [eyx, eyy]], dtype=np.complex128)
    cp = b4.cp_matrix_from_linear(jones)
    ir_r = float(abs(cp[0, 0]) ** 2)
    il_r = float(abs(cp[1, 0]) ** 2)
    ir_l = float(abs(cp[0, 1]) ** 2)
    il_l = float(abs(cp[1, 1]) ** 2)
    total_r = ir_r + il_r
    docp = (ir_r - il_r) / total_r
    l_fraction = il_r / total_r
    target_ratio = il_r / ir_r if ir_r else float("inf")
    strict_ratio = il_r / (ir_r + ir_l + il_l) if (ir_r + ir_l + il_l) else float("inf")
    passed = docp < -0.8 and l_fraction > 0.90 and il_r > 0.3 and target_ratio > 20.0
    audit = geometry_audit(case)
    debug["J_linear"] = [[b4.cstr(value) for value in row] for row in jones]
    debug["J_cp_T_output_input"] = [[b4.cstr(value) for value in row] for row in cp]
    return {
        "case_id": case["case_id"],
        "tolerance_type": case["tolerance_type"],
        "status": "ok",
        "IR_Rin": b4.fnum(ir_r),
        "IL_Rin": b4.fnum(il_r),
        "DoCP_RminusL_for_Rin": b4.fnum(docp),
        "L_fraction_for_Rin": b4.fnum(l_fraction),
        "IR_Lin": b4.fnum(ir_l),
        "IL_Lin": b4.fnum(il_l),
        "target_to_Rin_opposite_ratio": b4.fnum(target_ratio),
        "target_to_all_other_ratio": b4.fnum(strict_ratio),
        "x_bias_abs_nm": audit["x_bias_abs_nm"],
        "fabrication_integer_ready": audit["fabrication_integer_ready"],
        "tolerance_pass": "yes" if passed else "no",
        "note": "Periodic zeroth-order unit-cell complex J_xy converted to calibrated +z R/L basis; T_output,input.",
    }, debug


def nominal_metric_row() -> dict[str, Any]:
    with NOMINAL_METRICS_CSV.open(newline="", encoding="utf-8") as handle:
        row = next(item for item in csv.DictReader(handle) if item["candidate_id"] == FROZEN_ID)
    return {
        "case_id": NOMINAL_ID,
        "tolerance_type": "nominal_reference_reused",
        "status": "reused_b4_1",
        "IR_Rin": row["IR_Rin"], "IL_Rin": row["IL_Rin"],
        "DoCP_RminusL_for_Rin": row["DoCP_RminusL_for_Rin"], "L_fraction_for_Rin": row["L_fraction_for_Rin"],
        "IR_Lin": row["IR_Lin"], "IL_Lin": row["IL_Lin"],
        "target_to_Rin_opposite_ratio": row["target_to_Rin_opposite_ratio"],
        "target_to_all_other_ratio": row["target_to_all_other_ratio"],
        "x_bias_abs_nm": row["x_bias_abs_nm"], "fabrication_integer_ready": "true", "tolerance_pass": "reference",
        "note": "Nominal B4-1 metric reused; nominal FSP not rerun.",
    }


def degradation_rows(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nominal = metrics[0]
    nominal_docp = float(nominal["DoCP_RminusL_for_Rin"])
    nominal_l_fraction = float(nominal["L_fraction_for_Rin"])
    nominal_il = float(nominal["IL_Rin"])
    nominal_ratio = float(nominal["target_to_Rin_opposite_ratio"])
    rows: list[dict[str, Any]] = []
    for metric in metrics[1:]:
        docp = float(metric["DoCP_RminusL_for_Rin"])
        l_fraction = float(metric["L_fraction_for_Rin"])
        il = float(metric["IL_Rin"])
        ratio = float(metric["target_to_Rin_opposite_ratio"])
        rows.append({
            "case_id": metric["case_id"], "tolerance_type": metric["tolerance_type"], "tolerance_pass": metric["tolerance_pass"],
            "delta_DoCP": docp - nominal_docp,
            "delta_L_fraction": l_fraction - nominal_l_fraction,
            "IL_Rin_ratio": il / nominal_il,
            "ratio_relative": ratio / nominal_ratio,
            "x_bias_abs_nm": metric["x_bias_abs_nm"],
            "note": "Positive delta_DoCP means less-negative DoCP and therefore degradation of L-output dominance.",
        })
    return rows


def rank_danger(metrics: list[dict[str, Any]], degradation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    degradation_map = {row["case_id"]: row for row in degradation}
    rows = []
    for metric in metrics[1:]:
        deg = degradation_map[metric["case_id"]]
        rows.append({
            "case_id": metric["case_id"], "tolerance_type": metric["tolerance_type"], "tolerance_pass": metric["tolerance_pass"],
            "DoCP_RminusL_for_Rin": metric["DoCP_RminusL_for_Rin"], "L_fraction_for_Rin": metric["L_fraction_for_Rin"],
            "IL_Rin": metric["IL_Rin"], "IL_Rin_ratio": deg["IL_Rin_ratio"],
            "target_to_Rin_opposite_ratio": metric["target_to_Rin_opposite_ratio"], "ratio_relative": deg["ratio_relative"],
            "x_bias_abs_nm": metric["x_bias_abs_nm"], "danger_reason": "",
        })
    rows.sort(key=lambda row: (
        row["tolerance_pass"] == "yes",
        float(row["L_fraction_for_Rin"]),
        float(row["IL_Rin_ratio"]),
        float(row["target_to_Rin_opposite_ratio"]),
        -float(row["x_bias_abs_nm"]),
    ))
    for rank, row in enumerate(rows, 1):
        row["danger_rank"] = rank
        row["danger_reason"] = "lowest L_fraction / target strength among screened integer tolerances" if rank <= 3 else "passed screen; lower priority"
    return rows


def write_summary(out_dir: Path, metrics: list[dict[str, Any]], ranked: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    tolerance_metrics = metrics[1:]
    passed = [row for row in tolerance_metrics if row["tolerance_pass"] == "yes"]
    failed = [row for row in tolerance_metrics if row["tolerance_pass"] != "yes"]
    worst = ranked[:3]
    worst_position = next(row for row in ranked if "offset" in row["tolerance_type"])
    worst_rotation = next(row for row in ranked if row["tolerance_type"] == "rotation")
    worst_size = next(row for row in ranked if row["tolerance_type"] == "uniform_size")
    nominal = metrics[0]
    lines = [
        "# Stage10 CP Route B4-3 fabrication tolerance periodic plane-wave screen\n\n",
        "## English\n\n",
        "- Route B4-3; CP-APCD J1/J2 dimer branch only.\n",
        "- Finite-patch dipole FDTD: not run. No source-position cases were run.\n",
        "- Tolerance screening follows the integer freeze because quantized coordinates do not guarantee robustness to placement, rotation, or critical-dimension errors. Periodic plane-wave screening limits the later finite-patch tolerance workload.\n",
        f"- Nominal reused from B4-1: DoCP={nominal['DoCP_RminusL_for_Rin']}, L_fraction={nominal['L_fraction_for_Rin']}, IL_Rin={nominal['IL_Rin']}, R-input IL/IR ratio={nominal['target_to_Rin_opposite_ratio']}.\n",
        f"- Tolerance cases tested: {len(tolerance_metrics)}; pass={len(passed)}, fail={len(failed)}.\n",
        "- Included: +/-2 nm individual J1/J2 x/y offsets, +/-1 deg individual rotations, and optional uniform +/-2 nm size tolerance.\n",
        "- CP chain: periodic zeroth-order complex J_xy from x/y inputs, converted to calibrated +z R/L basis; T_output,input.\n\n",
        "### Worst three tolerance cases\n\n",
        "| rank | case | type | DoCP | L fraction | IL/nominal | target/opposite | x-bias nm | pass |\n",
        "|---:|---|---|---:|---:|---:|---:|---:|---|\n",
    ]
    for row in worst:
        lines.append(f"| {row['danger_rank']} | {row['case_id']} | {row['tolerance_type']} | {row['DoCP_RminusL_for_Rin']} | {row['L_fraction_for_Rin']} | {float(row['IL_Rin_ratio']):.6g} | {row['target_to_Rin_opposite_ratio']} | {row['x_bias_abs_nm']} | {row['tolerance_pass']} |\n")
    lines.extend([
        f"\n- +/-2 nm position errors preserve strong plane-wave CP: {'yes' if all(row['tolerance_pass']=='yes' for row in tolerance_metrics if 'offset' in row['tolerance_type']) else 'no'}.\n",
        f"- +/-1 deg rotation errors preserve strong plane-wave CP: {'yes' if all(row['tolerance_pass']=='yes' for row in tolerance_metrics if row['tolerance_type']=='rotation') else 'no'}.\n",
        f"- Uniform size tolerance was included. Worst size case `{worst_size['case_id']}` pass={worst_size['tolerance_pass']}; its low IL_Rin ratio makes it the first B4-4 risk case.\n",
        f"- Route B4-4 recommendation: reuse nominal B4-2, then finite-patch minimal x-line for `{worst_size['case_id']}` (critical size case), `{worst_position['case_id']}` (worst position case), and `{worst_rotation['case_id']}` (worst rotation case). Do not run B4-4 here.\n",
        "\n## 中文\n\n",
        "- 本任务是 Route B4-3，只处理 CP-APCD J1/J2 dimer 支线。\n",
        "- 没有运行 finite-patch dipole FDTD，也没有运行源位置 case。\n",
        "- 整数冻结不等于对放置、旋转和 CD 误差鲁棒，因此需要先做周期平面波容差筛选，以限制后续 finite-patch 容差工作量。\n",
        f"- nominal 复用 B4-1：DoCP={nominal['DoCP_RminusL_for_Rin']}，L_fraction={nominal['L_fraction_for_Rin']}，IL_Rin={nominal['IL_Rin']}，R-input IL/IR ratio={nominal['target_to_Rin_opposite_ratio']}。\n",
        f"- 共测试 {len(tolerance_metrics)} 个容差 case；通过={len(passed)}，失败={len(failed)}。\n",
        "- 已包含：J1/J2 单独 x/y +/-2 nm 偏移、单独旋转 +/-1 deg，以及可选的整体尺寸 +/-2 nm 容差。\n",
        f"- +/-2 nm 位置误差是否保持强平面波 CP：{'是' if all(row['tolerance_pass']=='yes' for row in tolerance_metrics if 'offset' in row['tolerance_type']) else '否'}。\n",
        f"- +/-1 deg 旋转误差是否保持强平面波 CP：{'是' if all(row['tolerance_pass']=='yes' for row in tolerance_metrics if row['tolerance_type']=='rotation') else '否'}。\n",
        f"- Route B4-4 推荐：复用 nominal B4-2，只对最危险位置 case `{worst_position['case_id']}` 和最危险旋转 case `{worst_rotation['case_id']}` 运行最小 x-line。本任务不运行 B4-4。\n",
    ])
    old_cn_recommendation_prefix = "- Route B4-4 \u63a8\u8350"
    lines = [line for line in lines if not line.startswith(old_cn_recommendation_prefix)]
    lines.extend([
        f"- \u5df2\u5305\u542b\u6574\u4f53\u5c3a\u5bf8\u5bb9\u5dee\u3002\u6700\u5371\u9669 size case `{worst_size['case_id']}` \u901a\u8fc7\u72b6\u6001={worst_size['tolerance_pass']}\uff1b\u5176 IL_Rin \u4fdd\u7559\u7387\u4f4e\uff0c\u56e0\u6b64\u662f B4-4 \u9996\u8981\u98ce\u9669 case\u3002\n",
        f"- Route B4-4 \u63a8\u8350\uff1a\u590d\u7528 nominal B4-2\uff0c\u5bf9 `{worst_size['case_id']}`\uff08\u5173\u952e\u5c3a\u5bf8\uff09\u3001`{worst_position['case_id']}`\uff08\u6700\u5371\u9669\u4f4d\u7f6e\uff09\u548c `{worst_rotation['case_id']}`\uff08\u6700\u5371\u9669\u65cb\u8f6c\uff09\u8fd0\u884c\u6700\u5c0f x-line\u3002\u672c\u4efb\u52a1\u4e0d\u8fd0\u884c B4-4\u3002\n",
    ])
    (out_dir / "route_b4_3_tolerance_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    (out_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)
    audit_rows = case_table()
    write_csv(out_dir / "route_b4_3_tolerance_cases.csv", audit_rows)
    write_csv(out_dir / "route_b4_3_tolerance_geometry_audit.csv", audit_rows)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    run_rows: list[dict[str, Any]] = []
    for case in CASES:
        for linear_input in ("x", "y"):
            run_rows.append(run_one(lumapi, runtime, out_dir, case, linear_input, args))
    metrics: list[dict[str, Any]] = [nominal_metric_row()]
    extract_debug: dict[str, Any] = {}
    if args.dry_run:
        for case in CASES:
            metrics.append({"case_id": case["case_id"], "tolerance_type": case["tolerance_type"], "status": "not_run", "tolerance_pass": "no", "note": "dry run"})
    else:
        for case in CASES:
            row, debug = extract_metrics(lumapi, runtime, out_dir, case, args.show_gui)
            metrics.append(row)
            extract_debug[case["case_id"]] = debug
    write_csv(out_dir / "route_b4_3_tolerance_plane_wave_metrics.csv", metrics)
    degradation = degradation_rows(metrics) if not args.dry_run else []
    ranked = rank_danger(metrics, degradation) if degradation else []
    write_csv(out_dir / "route_b4_3_tolerance_degradation.csv", degradation)
    write_csv(out_dir / "route_b4_3_tolerance_ranked_danger.csv", ranked)
    if ranked:
        write_summary(out_dir, metrics, ranked, run_rows)
    debug = {
        "route": "B4-3", "branch": "CP-APCD J1/J2 only", "finite_patch_fdtd_runs": 0,
        "nominal_reference_reused": FROZEN_ID, "nominal_rerun": False,
        "tolerance_case_count": len(CASES), "periodic_linear_runs_planned": len(CASES) * 2,
        "size_tolerance_included": True, "run_rows": run_rows, "extract_debug": extract_debug,
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
        "soft_ratio_definition": "IL_Rin/IR_Rin",
        "worst_position_case": next((row["case_id"] for row in ranked if "offset" in row["tolerance_type"]), None),
        "worst_rotation_case": next((row["case_id"] for row in ranked if row["tolerance_type"] == "rotation"), None),
        "worst_size_case": next((row["case_id"] for row in ranked if row["tolerance_type"] == "uniform_size"), None),
    }
    (out_dir / "route_b4_3_tolerance_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(out_dir), "run_rows": run_rows, "ranked_danger": ranked}, indent=2))
    failed_runs = [row for row in run_rows if row["fdtd_status"] not in {"ok", "reused", "not_run"}]
    failed_extract = [row for row in metrics[1:] if row.get("status") not in {"ok", "not_run"}]
    return 1 if failed_runs or failed_extract else 0


if __name__ == "__main__":
    raise SystemExit(main())

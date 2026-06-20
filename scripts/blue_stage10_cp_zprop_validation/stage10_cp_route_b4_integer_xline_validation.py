from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

import stage10_cp_route_b2_finite_patch_xplus_test as b2

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b4_integer_finite_patch_xline"
SAVED_FSP_DIR = OUT_DIR / "_saved_fsp"
REFERENCE_AVG_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b3_d195t90_xline_validation" / "route_b3_position_averages.csv"

CANDIDATE_ID = "B4INT_J1J2_D194_T90_PSI97_H525"
REFERENCE_ID = "RB1_J1J2_D195_T90_PSI97p5_H525"
D_NM = 194.0
THETA_DEG = 90.0
PSI_DEG = 97.0
J1_ROTATION_DEG = -7.0
J2_ROTATION_DEG = 38.0
GRID_N = 101
CONES_DEG = [5.0, 10.0, 20.0, 30.0]
X_SOURCE = "route_b4_integer_x_dipole_zprop"
Y_SOURCE = "route_b4_integer_y_dipole_zprop"


def make_case(position_id: str, orientation: str, x_nm: float) -> dict[str, Any]:
    upper = orientation.upper()
    return {
        "case_id": f"B4INT_D194_T90_PSI97_{position_id.upper()}_{upper}_T100FS",
        "position_id": position_id,
        "orientation": orientation,
        "x_nm": x_nm,
        "y_nm": 0.0,
        "z_nm": b2.SOURCE_Z_NM,
        "enabled_source": X_SOURCE if orientation == "x" else Y_SOURCE,
        "disabled_source": Y_SOURCE if orientation == "x" else X_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 0.0 if orientation == "x" else 90.0,
    }


CASES = [
    make_case("center", "x", 0.0),
    make_case("center", "y", 0.0),
    make_case("x_plus_qp", "x", b2.Q_NM),
    make_case("x_plus_qp", "y", b2.Q_NM),
    make_case("x_minus_qp", "x", -b2.Q_NM),
    make_case("x_minus_qp", "y", -b2.Q_NM),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage10 CP Route B4-2 D194/T90/PSI97 finite-patch minimal x-line validation.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--simulation-time-fs", type=float, default=b2.SIM_TIME_FS)
    parser.add_argument("--grid-n", type=int, default=GRID_N)
    parser.add_argument("--cone-deg", type=float, nargs="*", default=CONES_DEG)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def integer_roles() -> list[dict[str, Any]]:
    return [
        {"role": "J1", "length_nm": 230.0, "width_nm": 100.0, "height_nm": 525.0, "rotation_deg": J1_ROTATION_DEG, "center_x_nm": 0.0, "center_y_nm": 97.0},
        {"role": "J2", "length_nm": 180.0, "width_nm": 90.0, "height_nm": 525.0, "rotation_deg": J2_ROTATION_DEG, "center_x_nm": 0.0, "center_y_nm": -97.0},
    ]


def add_integer_uniform_patch(fdtd: object) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    parent = "CP_route_b4_D194_T90_PSI97_uniform_patch_7x3_group"
    fdtd.addstructuregroup()
    fdtd.set("name", parent)
    fdtd.groupscope(f"::model::{parent}")
    for ix, x0 in zip(b2.IX_VALUES, b2.X_CENTERS_NM):
        for iy, y0 in zip(b2.IY_VALUES, b2.Y_CENTERS_NM):
            group = f"DIMER_ix{ix}_iy{iy}_J1J2_D194_T90_PSI97"
            fdtd.addstructuregroup()
            fdtd.set("name", group)
            fdtd.groupscope(f"::model::{parent}::{group}")
            for role in integer_roles():
                x_nm = x0 + float(role["center_x_nm"])
                y_nm = y0 + float(role["center_y_nm"])
                fdtd.addrect()
                fdtd.set("name", f"{role['role']}_pillar")
                fdtd.set("x", x_nm * b2.NM)
                fdtd.set("y", y_nm * b2.NM)
                fdtd.set("x span", float(role["length_nm"]) * b2.NM)
                fdtd.set("y span", float(role["width_nm"]) * b2.NM)
                fdtd.set("z min", 0.0)
                fdtd.set("z max", float(role["height_nm"]) * b2.NM)
                fdtd.set("first axis", "z")
                fdtd.set("rotation 1", float(role["rotation_deg"]))
                fdtd.set("material", "<Object defined dielectric>")
                fdtd.set("index", b2.MATERIAL_INDEX)
                inventory.append({
                    "object_name": f"{parent}/{group}/{role['role']}_pillar",
                    "dimer_ix": ix,
                    "dimer_iy": iy,
                    "role": role["role"],
                    "x_center_nm": x_nm,
                    "y_center_nm": y_nm,
                    "z_min_nm": 0.0,
                    "z_max_nm": role["height_nm"],
                    "rotation_deg": role["rotation_deg"],
                })
            fdtd.groupscope(f"::model::{parent}")
    fdtd.groupscope("::model")
    return inventory


def patch_b2_globals() -> None:
    b2.OUT_DIR = OUT_DIR
    b2.CANDIDATE_DIRNAME = "D194_T90_PSI97"
    b2.CANDIDATE_OUT = OUT_DIR
    b2.SAVED_FSP_DIR = SAVED_FSP_DIR
    b2.X_SOURCE = X_SOURCE
    b2.Y_SOURCE = Y_SOURCE
    b2.D_NM = D_NM
    b2.THETA_DEG = THETA_DEG
    b2.PSI_DEG = PSI_DEG
    b2.J1_ROTATION_DEG = J1_ROTATION_DEG
    b2.J2_ROTATION_DEG = J2_ROTATION_DEG
    b2.J_ROLES = integer_roles()
    b2.add_uniform_patch = add_integer_uniform_patch


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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mark_case_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    marked: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["route"] = "B4-2"
        item["candidate_id"] = CANDIDATE_ID
        item["notes"] = "Route B4-2 integer candidate finite-patch x-axis centerline only."
        marked.append(item)
    return marked


def average_by_position(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok = [row for row in case_rows if row.get("extraction_status") == "ok"]
    averages: list[dict[str, Any]] = []
    for position in ("center", "x_plus_qp", "x_minus_qp"):
        position_rows = [row for row in ok if row.get("position_id") == position]
        for cone in sorted({float(row["cone_deg"]) for row in position_rows}):
            pair = [row for row in position_rows if float(row["cone_deg"]) == cone]
            if {row["orientation"] for row in pair} != {"x", "y"}:
                continue
            ir = sum(float(row["IR_cone"]) for row in pair)
            il = sum(float(row["IL_cone"]) for row in pair)
            total = ir + il
            averages.append({
                "route": "B4-2",
                "candidate_id": CANDIDATE_ID,
                "position_id": position,
                "cone_deg": cone,
                "included_cases": ";".join(str(row["case_id"]) for row in pair),
                "IR_total": ir,
                "IL_total": il,
                "P_total": total,
                "DoCP_RminusL": (ir - il) / total if total else float("nan"),
                "DoCP_LminusR": (il - ir) / total if total else float("nan"),
                "L_fraction": il / total if total else float("nan"),
                "R_fraction": ir / total if total else float("nan"),
                "notes": "Incoherent x/y dipole power sum only; no coherent field addition.",
            })
    return averages


def reference_map() -> dict[tuple[str, float], dict[str, str]]:
    return {(row["position_id"], float(row["cone_deg"])): row for row in read_csv(REFERENCE_AVG_CSV)}


def comparison_rows(averages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reference = reference_map()
    rows: list[dict[str, Any]] = []
    for row in averages:
        key = (str(row["position_id"]), float(row["cone_deg"]))
        ref = reference[key]
        candidate_power = float(row["P_total"])
        reference_power = float(ref["P_total"])
        ratio = candidate_power / reference_power if reference_power else float("nan")
        rows.append({
            "position_id": key[0],
            "cone_deg": key[1],
            "reference_candidate_id": REFERENCE_ID,
            "reference_fabrication_integer_ready": "false",
            "reference_DoCP_RminusL": ref["DoCP_RminusL"],
            "reference_L_fraction": ref["L_fraction"],
            "reference_total_cone_power": reference_power,
            "integer_candidate_id": CANDIDATE_ID,
            "integer_candidate_fabrication_ready": "true",
            "integer_DoCP_RminusL": row["DoCP_RminusL"],
            "integer_L_fraction": row["L_fraction"],
            "integer_total_cone_power": candidate_power,
            "power_ratio_integer_over_reference": ratio,
            "power_not_catastrophic": "yes" if ratio >= 0.25 else "no",
            "notes": "D195/T90/PSI97p5 reference reused from Route B3; no reference rerun.",
        })
    return rows


def score_rows(averages: list[dict[str, Any]], comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for cone in sorted({float(row["cone_deg"]) for row in averages}):
        subset = [row for row in averages if float(row["cone_deg"]) == cone]
        if len(subset) != 3:
            continue
        l_values = [float(row["L_fraction"]) for row in subset]
        d_values = [float(row["DoCP_RminusL"]) for row in subset]
        powers = [float(row["P_total"]) for row in subset]
        comp = [row for row in comparisons if float(row["cone_deg"]) == cone]
        power_guard = all(row["power_not_catastrophic"] == "yes" for row in comp)
        passes = min(l_values) > 0.60 and all(value < -0.2 for value in d_values) and power_guard
        scores.append({
            "candidate_id": CANDIDATE_ID,
            "fabrication_integer_ready": "true",
            "cone_deg": cone,
            "positions_included": "center;x_plus_qp;x_minus_qp",
            "min_L_fraction": min(l_values),
            "avg_L_fraction": mean(l_values),
            "std_L_fraction": pstdev(l_values),
            "avg_DoCP_RminusL": mean(d_values),
            "avg_total_cone_power": mean(powers),
            "all_positions_power_not_catastrophic": "yes" if power_guard else "no",
            "minimal_xline_pass": "yes" if passes else "no",
            "notes": "Operational catastrophic-power guard is integer/reference power ratio >=0.25 at each position.",
        })
    return scores


def fmt_average(averages: list[dict[str, Any]], position: str, cone: float) -> str:
    row = next((r for r in averages if r["position_id"] == position and float(r["cone_deg"]) == cone), None)
    if not row:
        return "not available"
    return f"DoCP={float(row['DoCP_RminusL']):.6g}, L_fraction={float(row['L_fraction']):.6g}, P={float(row['P_total']):.6g}"


def write_summary(averages: list[dict[str, Any]], comparisons: list[dict[str, Any]], scores: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    score20 = next((row for row in scores if float(row["cone_deg"]) == 20.0), None)
    passed = bool(score20 and score20["minimal_xline_pass"] == "yes")
    min_l = float(score20["min_L_fraction"]) if score20 else float("nan")
    completed = sum(row["fdtd_status"] in {"ok", "reused"} for row in run_rows)
    lines = [
        "# Stage10 CP Route B4-2 integer finite-patch minimal x-line validation\n\n",
        "## English\n\n",
        f"- Route B4-2; CP-APCD J1/J2 branch only. Candidate: `{CANDIDATE_ID}` only.\n",
        f"- Exactly six finite-patch cases were requested and completed/reused: {completed}/6: center_x/y, x_plus_qp_x/y, x_minus_qp_x/y.\n",
        "- No y-offset, no 41-position or full-plane sweep, no bare reference, no x_plus/minus_2qp.\n",
        "- Geometry: J1 center=(0,97) nm, rotation=-7 deg; J2 center=(0,-97) nm, rotation=38 deg; fabrication_integer_ready=true.\n",
        "- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant. x/y dipoles are combined by incoherent power sums only.\n\n",
        "### Position averages\n\n",
    ]
    for position in ("center", "x_plus_qp", "x_minus_qp"):
        lines.append(f"- {position}: +/-5 deg {fmt_average(averages, position, 5.0)}; +/-10 deg {fmt_average(averages, position, 10.0)}; +/-20 deg {fmt_average(averages, position, 20.0)}.\n")
    lines.extend(["\n### D195 physical-reference comparison at +/-20 deg\n\n"])
    for position in ("center", "x_plus_qp", "x_minus_qp"):
        row = next(r for r in comparisons if r["position_id"] == position and float(r["cone_deg"]) == 20.0)
        lines.append(f"- {position}: reference DoCP={float(row['reference_DoCP_RminusL']):.6g}, L_fraction={float(row['reference_L_fraction']):.6g}, P={float(row['reference_total_cone_power']):.6g}; integer DoCP={float(row['integer_DoCP_RminusL']):.6g}, L_fraction={float(row['integer_L_fraction']):.6g}, P={float(row['integer_total_cone_power']):.6g}; power ratio={float(row['power_ratio_integer_over_reference']):.6g}.\n")
    lines.extend([
        f"- Route B4-2 minimal x-line result at +/-20 deg: {'PASS' if passed else 'FAIL'}; min L_fraction={min_l:.6g}.\n",
        f"- Decision: {'freeze D194_T90_PSI97 as the fabrication-aware CP candidate and move to tolerance tests, not more ideal optimization' if passed else 'test the next integer candidate from the Route B4-1 ranking'}.\n",
        "- Cone powers are API-normalized extraction metrics, not independently validated absolute LEE.\n",
        "\n## 中文\n\n",
        f"- 本任务是 Route B4-2，只处理 CP-APCD J1/J2 支线，只测试 `{CANDIDATE_ID}`。\n",
        f"- 严格请求并完成/复用 6 个有限阵列 case：{completed}/6，即 center_x/y、x_plus_qp_x/y、x_minus_qp_x/y。\n",
        "- 没有 y-offset、41 点或完整平面扫描、bare reference、x_plus/minus_2qp。\n",
        "- 整数几何：J1 中心=(0,97) nm、旋转=-7 deg；J2 中心=(0,-97) nm、旋转=38 deg；fabrication_integer_ready=true。\n",
        "- x/y 偶极只做功率非相干相加。负 DoCP_RminusL 表示 L 输出占优。\n\n",
        "### 位置平均\n\n",
    ])
    for position in ("center", "x_plus_qp", "x_minus_qp"):
        lines.append(f"- {position}: +/-5 deg {fmt_average(averages, position, 5.0)}；+/-10 deg {fmt_average(averages, position, 10.0)}；+/-20 deg {fmt_average(averages, position, 20.0)}。\n")
    lines.extend([
        f"- +/-20 deg 最小 x-line 鲁棒性：{'通过' if passed else '未通过'}；min L_fraction={min_l:.6g}。\n",
        f"- 决策：{'冻结 D194_T90_PSI97 为加工友好 CP 候选，下一步进入容差测试，不继续理想参数优化' if passed else '测试 Route B4-1 排名中的下一个整数候选'}。\n",
        "- cone power 是 API-normalized extraction metric，不是独立验证的绝对 LEE。\n",
    ])
    (OUT_DIR / "route_b4_integer_xline_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SAVED_FSP_DIR.mkdir(parents=True, exist_ok=True)
    patch_b2_globals()
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    setup_fsp = OUT_DIR / "route_b4_D194_T90_PSI97_xline_setup.fsp"
    setup_status = "ok"
    setup_warnings: list[str] = []
    inventory: list[dict[str, Any]] = []
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        setup_warnings, inventory = b2.build_setup(fdtd, args.simulation_time_fs)
        fdtd.save(str(setup_fsp.resolve()))
    except Exception as exc:
        setup_status = f"failed: {type(exc).__name__}: {exc}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass

    run_rows: list[dict[str, Any]] = []
    if setup_status == "ok" and not args.dry_run:
        for case in CASES:
            run_rows.append(b2.run_case(lumapi, runtime, setup_fsp, case, args.simulation_time_fs, args.show_gui, args.force))
    else:
        for case in CASES:
            run_rows.append({"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "not_run" if args.dry_run else setup_status, "result_fsp": str(SAVED_FSP_DIR / f"{case['case_id']}.fsp"), "notes": "dry run" if args.dry_run else setup_status})

    case_rows: list[dict[str, Any]] = []
    extract_debug: list[dict[str, Any]] = []
    if not args.dry_run:
        for case in CASES:
            rows, debug = b2.extract_case(lumapi, runtime, case, args.grid_n, args.cone_deg, args.show_gui)
            case_rows.extend(mark_case_rows(rows))
            extract_debug.append(debug)
    averages = average_by_position(case_rows)
    comparisons = comparison_rows(averages) if averages else []
    scores = score_rows(averages, comparisons) if comparisons else []
    write_csv(OUT_DIR / "route_b4_integer_xline_case_metrics.csv", case_rows)
    write_csv(OUT_DIR / "route_b4_integer_xline_position_averages.csv", averages)
    write_csv(OUT_DIR / "route_b4_integer_xline_vs_d195_reference.csv", comparisons)
    write_csv(OUT_DIR / "route_b4_integer_xline_score.csv", scores)
    if scores:
        write_summary(averages, comparisons, scores, run_rows)
    debug = {
        "route": "B4-2",
        "branch": "CP-APCD J1/J2 only",
        "candidate_id": CANDIDATE_ID,
        "fabrication_integer_ready": True,
        "candidate_geometry": {"d_nm": 194, "theta_deg": 90, "psi_deg": 97, "J1_center_nm": [0, 97], "J2_center_nm": [0, -97], "J1_rotation_deg": -7, "J2_rotation_deg": 38},
        "exact_cases_requested": [case["case_id"] for case in CASES],
        "no_y_offset": True,
        "no_41_position_sweep": True,
        "no_full_plane_sweep": True,
        "setup_status": setup_status,
        "setup_fsp": str(setup_fsp),
        "setup_warnings": setup_warnings,
        "run_rows": run_rows,
        "extract_debug": extract_debug,
        "patch_inventory_count": len(inventory),
        "reference_candidate": REFERENCE_ID,
        "reference_reused_not_rerun": True,
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
    }
    (OUT_DIR / "route_b4_integer_xline_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    print(json.dumps({"setup_status": setup_status, "run_rows": run_rows, "position_averages": averages, "scores": scores}, indent=2))
    failed_runs = [row for row in run_rows if row["fdtd_status"] not in {"ok", "reused", "not_run"}]
    failed_extract = [row for row in extract_debug if row.get("status") != "ok"]
    return 1 if setup_status != "ok" or failed_runs or failed_extract else 0


if __name__ == "__main__":
    raise SystemExit(main())

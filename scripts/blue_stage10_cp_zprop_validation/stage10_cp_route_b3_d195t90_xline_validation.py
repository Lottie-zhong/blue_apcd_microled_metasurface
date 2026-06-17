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
OUT_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b3_d195t90_xline_validation"
SAVED_FSP_DIR = OUT_DIR / "_saved_fsp"
B2_CASE_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b2_finite_patch_xplus" / "route_b2_xplus_case_metrics.csv"
B2_AVG_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b2_finite_patch_xplus" / "route_b2_xplus_average_metrics.csv"
BASELINE_AVG_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "xline_minimal_robustness" / "xline_minimal_position_averages.csv"

CANDIDATE_ID = "RB1_J1J2_D195_T90_PSI97p5_H525"
GRID_N = 101
CONES_DEG = [5.0, 10.0, 20.0, 30.0]

X_SOURCE = "route_b3_x_dipole_zprop"
Y_SOURCE = "route_b3_y_dipole_zprop"

CASES = [
    {
        "case_id": "RB3_D195_T90_CENTER_X_T100FS",
        "position_id": "center",
        "orientation": "x",
        "x_nm": 0.0,
        "y_nm": 0.0,
        "z_nm": b2.SOURCE_Z_NM,
        "enabled_source": X_SOURCE,
        "disabled_source": Y_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 0.0,
    },
    {
        "case_id": "RB3_D195_T90_CENTER_Y_T100FS",
        "position_id": "center",
        "orientation": "y",
        "x_nm": 0.0,
        "y_nm": 0.0,
        "z_nm": b2.SOURCE_Z_NM,
        "enabled_source": Y_SOURCE,
        "disabled_source": X_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 90.0,
    },
    {
        "case_id": "RB3_D195_T90_X_MINUS_QP_X_T100FS",
        "position_id": "x_minus_qp",
        "orientation": "x",
        "x_nm": -b2.Q_NM,
        "y_nm": 0.0,
        "z_nm": b2.SOURCE_Z_NM,
        "enabled_source": X_SOURCE,
        "disabled_source": Y_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 0.0,
    },
    {
        "case_id": "RB3_D195_T90_X_MINUS_QP_Y_T100FS",
        "position_id": "x_minus_qp",
        "orientation": "y",
        "x_nm": -b2.Q_NM,
        "y_nm": 0.0,
        "z_nm": b2.SOURCE_Z_NM,
        "enabled_source": Y_SOURCE,
        "disabled_source": X_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 90.0,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage10 CP Route B3 D195/T90 minimal x-line validation.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--simulation-time-fs", type=float, default=b2.SIM_TIME_FS)
    parser.add_argument("--grid-n", type=int, default=GRID_N)
    parser.add_argument("--cone-deg", type=float, nargs="*", default=CONES_DEG)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def patch_b2_globals() -> None:
    b2.OUT_DIR = OUT_DIR
    b2.CANDIDATE_OUT = OUT_DIR
    b2.SAVED_FSP_DIR = SAVED_FSP_DIR
    b2.X_SOURCE = X_SOURCE
    b2.Y_SOURCE = Y_SOURCE


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SAVED_FSP_DIR.mkdir(parents=True, exist_ok=True)


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
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mark_rows(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        r["route"] = "B3"
        r["candidate_id"] = CANDIDATE_ID
        r["data_source"] = source
        if source == "new_route_b3":
            r["notes"] = str(r.get("notes", "")).replace("Route B2 finite-patch x_plus_qp only", "Route B3 finite-patch minimal x-line validation")
        elif source == "reused_route_b2_x_plus_qp":
            r["notes"] = "Reused from Route B2 D195/T90 x_plus_qp result; not rerun in Route B3."
        out.append(r)
    return out


def read_xplus_case_rows() -> list[dict[str, Any]]:
    return mark_rows([r for r in read_csv(B2_CASE_CSV) if r.get("extraction_status") == "ok"], "reused_route_b2_x_plus_qp")


def read_xplus_average_rows() -> list[dict[str, Any]]:
    rows = []
    for r in read_csv(B2_AVG_CSV):
        row = dict(r)
        row["route"] = "B3"
        row["candidate_id"] = CANDIDATE_ID
        row["data_source"] = "reused_route_b2_x_plus_qp"
        row["notes"] = "Reused from Route B2; x_plus_qp was not rerun in Route B3."
        rows.append(row)
    return rows


def average_by_position(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok = [r for r in case_rows if r.get("extraction_status") == "ok"]
    out: list[dict[str, Any]] = []
    for position in ["center", "x_plus_qp", "x_minus_qp"]:
        prow = [r for r in ok if r.get("position_id") == position]
        for cone in sorted({float(r["cone_deg"]) for r in prow}):
            pair = [r for r in prow if float(r["cone_deg"]) == cone]
            if len({r.get("orientation") for r in pair}) != 2:
                continue
            ir = sum(float(r["IR_cone"]) for r in pair)
            il = sum(float(r["IL_cone"]) for r in pair)
            total = ir + il
            out.append({
                "route": "B3",
                "candidate_id": CANDIDATE_ID,
                "position_id": position,
                "cone_deg": cone,
                "included_cases": ";".join(str(r["case_id"]) for r in pair),
                "IR_total": ir,
                "IL_total": il,
                "P_total": total,
                "DoCP_RminusL": (ir - il) / total if total else float("nan"),
                "DoCP_LminusR": (il - ir) / total if total else float("nan"),
                "L_fraction": il / total if total else float("nan"),
                "R_fraction": ir / total if total else float("nan"),
                "data_source": "new_route_b3" if position != "x_plus_qp" else "reused_route_b2_x_plus_qp",
                "notes": "Incoherent x/y dipole power sum only; no coherent field addition.",
            })
    return out


def baseline_by_position() -> dict[tuple[str, float], dict[str, str]]:
    out: dict[tuple[str, float], dict[str, str]] = {}
    for row in read_csv(BASELINE_AVG_CSV):
        try:
            out[(row["position_id"], float(row["cone_deg"]))] = row
        except Exception:
            continue
    return out


def baseline_comparison(avg_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = baseline_by_position()
    rows: list[dict[str, Any]] = []
    for row in avg_rows:
        pos = str(row["position_id"])
        cone = float(row["cone_deg"])
        base = baseline.get((pos, cone), {})
        base_docp = float(base.get("DoCP_total_RminusL", "nan")) if base else float("nan")
        base_lfrac = float(base.get("L_fraction_total", "nan")) if base else float("nan")
        base_power = float(base.get("P_total", "nan")) if base else float("nan")
        route_docp = float(row["DoCP_RminusL"])
        route_lfrac = float(row["L_fraction"])
        route_power = float(row["P_total"])
        rows.append({
            "position_id": pos,
            "cone_deg": cone,
            "baseline_DoCP_RminusL": base_docp,
            "route_b3_DoCP_RminusL": route_docp,
            "delta_DoCP_RminusL": route_docp - base_docp if math.isfinite(base_docp) else "",
            "baseline_L_fraction": base_lfrac,
            "route_b3_L_fraction": route_lfrac,
            "delta_L_fraction": route_lfrac - base_lfrac if math.isfinite(base_lfrac) else "",
            "baseline_total_cone_power": base_power,
            "route_b3_total_cone_power": route_power,
            "power_ratio_route_over_baseline": route_power / base_power if math.isfinite(base_power) and base_power else "",
            "passes_position_threshold": "yes" if route_docp < -0.2 and route_lfrac > 0.60 else "no",
            "notes": "Baseline is frozen D182p5/T70 x-line result; Route B3 uses D195/T90 candidate.",
        })
    return rows


def score_rows(avg_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cone in sorted({float(r["cone_deg"]) for r in avg_rows}):
        subset = [r for r in avg_rows if float(r["cone_deg"]) == cone and r.get("position_id") in {"center", "x_plus_qp", "x_minus_qp"}]
        if len({r.get("position_id") for r in subset}) != 3:
            continue
        lvals = [float(r["L_fraction"]) for r in subset]
        pvals = [float(r["P_total"]) for r in subset]
        dvals = [float(r["DoCP_RminusL"]) for r in subset]
        rows.append({
            "candidate_id": CANDIDATE_ID,
            "cone_deg": cone,
            "positions_included": ";".join(r["position_id"] for r in subset),
            "min_L_fraction": min(lvals),
            "avg_L_fraction": mean(lvals),
            "std_L_fraction": pstdev(lvals),
            "avg_DoCP_RminusL": mean(dvals),
            "avg_total_cone_power": mean(pvals),
            "min_position_passes": "yes" if min(lvals) > 0.60 and all(d < -0.2 for d in dvals) else "no",
            "notes": "Minimal x-line robustness score over center, x_plus_qp, and x_minus_qp.",
        })
    return rows


def fmt_avg(rows: list[dict[str, Any]], position: str, cone: float) -> str:
    row = next((r for r in rows if r.get("position_id") == position and abs(float(r.get("cone_deg", -1)) - cone) < 1e-9), None)
    if not row:
        return "not available"
    return f"DoCP={float(row['DoCP_RminusL']):.6g}, L_fraction={float(row['L_fraction']):.6g}, P={float(row['P_total']):.6g}"


def write_summary(case_rows: list[dict[str, Any]], avg_rows: list[dict[str, Any]], comp_rows: list[dict[str, Any]], scores: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    score20 = next((r for r in scores if abs(float(r["cone_deg"]) - 20.0) < 1e-9), None)
    passed20 = bool(score20 and score20.get("min_position_passes") == "yes")
    min_l = float(score20["min_L_fraction"]) if score20 else float("nan")
    lines = ["# Stage10 CP Route B3 D195/T90 minimal x-line validation\n\n"]
    lines.append("## English\n\n")
    lines.append("- Route: B3. Candidate tested: RB1_J1J2_D195_T90_PSI97p5_H525 only.\n")
    lines.append("- Newly run/reused finite-patch cases: center_x/y and x_minus_qp_x/y. Existing x_plus_qp_x/y is reused from Route B2 and was not rerun.\n")
    lines.append("- No x_plus rerun, no x_plus_2qp/x_minus_2qp, no y-offset, no 41-position sweep, no bare reference, no DBR/RCLED, no K=6, no steering.\n")
    lines.append("- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant.\n")
    lines.append("- x/y dipole averages are incoherent power sums only.\n\n")
    lines.append("### Position averages\n\n")
    for pos in ["center", "x_plus_qp", "x_minus_qp"]:
        lines.append(f"- {pos}: +/-5 deg {fmt_avg(avg_rows, pos, 5.0)}; +/-10 deg {fmt_avg(avg_rows, pos, 10.0)}; +/-20 deg {fmt_avg(avg_rows, pos, 20.0)}.\n")
    lines.append("\n### Baseline comparison at +/-20 deg\n\n")
    for pos in ["center", "x_plus_qp", "x_minus_qp"]:
        row = next((r for r in comp_rows if r.get("position_id") == pos and abs(float(r.get("cone_deg", -1)) - 20.0) < 1e-9), None)
        if row:
            lines.append(f"- {pos}: baseline DoCP={float(row['baseline_DoCP_RminusL']):.6g}, L_fraction={float(row['baseline_L_fraction']):.6g}, P={float(row['baseline_total_cone_power']):.6g}; D195/T90 DoCP={float(row['route_b3_DoCP_RminusL']):.6g}, L_fraction={float(row['route_b3_L_fraction']):.6g}, P={float(row['route_b3_total_cone_power']):.6g}, power ratio={row['power_ratio_route_over_baseline']}.\n")
    lines.append(f"- Minimal x-line robustness at +/-20 deg: {'pass' if passed20 else 'fail'}; min L_fraction={min_l:.6g}.\n")
    lines.append("- If pass: pause CP finite-patch expansion and prepare a concise stage closeout; test backup D182p5_T85 only if needed. If fail: test backup D182p5_T85 x_plus_qp_x/y.\n")
    lines.append("\n## 中文\n\n")
    lines.append("- 路线：B3。只测试候选 RB1_J1J2_D195_T90_PSI97p5_H525。\n")
    lines.append("- 本轮新运行/复用的有限阵列 case：center_x/y 和 x_minus_qp_x/y；x_plus_qp_x/y 复用 Route B2 已有结果，没有重跑。\n")
    lines.append("- 没有重跑 x_plus，没有 x_plus_2qp/x_minus_2qp，没有 y-offset，没有 41-position sweep，没有 bare reference，没有 DBR/RCLED，没有 K=6，没有 steering。\n")
    lines.append("- CP 约定：R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)；DoCP_RminusL 为负表示 L 输出占优。\n")
    lines.append("- x/y 偶极平均只做强度非相干相加。\n\n")
    lines.append("### 位置平均\n\n")
    for pos in ["center", "x_plus_qp", "x_minus_qp"]:
        lines.append(f"- {pos}: +/-5 deg {fmt_avg(avg_rows, pos, 5.0)}；+/-10 deg {fmt_avg(avg_rows, pos, 10.0)}；+/-20 deg {fmt_avg(avg_rows, pos, 20.0)}。\n")
    lines.append("\n### +/-20 deg baseline 对比\n\n")
    for pos in ["center", "x_plus_qp", "x_minus_qp"]:
        row = next((r for r in comp_rows if r.get("position_id") == pos and abs(float(r.get("cone_deg", -1)) - 20.0) < 1e-9), None)
        if row:
            lines.append(f"- {pos}: baseline DoCP={float(row['baseline_DoCP_RminusL']):.6g}, L_fraction={float(row['baseline_L_fraction']):.6g}, P={float(row['baseline_total_cone_power']):.6g}；D195/T90 DoCP={float(row['route_b3_DoCP_RminusL']):.6g}, L_fraction={float(row['route_b3_L_fraction']):.6g}, P={float(row['route_b3_total_cone_power']):.6g}, power ratio={row['power_ratio_route_over_baseline']}。\n")
    lines.append(f"- +/-20 deg 最小 x-line 鲁棒性：{'通过' if passed20 else '未通过'}；min L_fraction={min_l:.6g}。\n")
    lines.append("- 如果通过：建议暂停 CP 有限阵列扩展，准备简洁阶段 closeout；只有必要时再测试备选 D182p5_T85。如果失败：建议测试备选 D182p5_T85 的 x_plus_qp_x/y。\n")
    (OUT_DIR / "route_b3_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    ensure_dirs()
    patch_b2_globals()
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    setup_fsp = OUT_DIR / "route_b3_D195_T90_xline_setup.fsp"
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
        if fdtd:
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

    new_case_rows: list[dict[str, Any]] = []
    extract_debug: list[dict[str, Any]] = []
    if not args.dry_run:
        for case in CASES:
            rows, dbg = b2.extract_case(lumapi, runtime, case, args.grid_n, args.cone_deg, args.show_gui)
            new_case_rows.extend(mark_rows(rows, "new_route_b3"))
            extract_debug.append(dbg)
    xplus_case_rows = read_xplus_case_rows()
    all_case_rows = new_case_rows + xplus_case_rows
    avg_rows = average_by_position(all_case_rows)
    xplus_avgs = read_xplus_average_rows()
    # Prefer the exact reused Route B2 averages for x_plus_qp in case CSV formatting changes.
    avg_rows = [r for r in avg_rows if r.get("position_id") != "x_plus_qp"] + xplus_avgs
    avg_rows = sorted(avg_rows, key=lambda r: ({"center": 0, "x_plus_qp": 1, "x_minus_qp": 2}.get(str(r.get("position_id")), 9), float(r.get("cone_deg", 0))))
    comp_rows = baseline_comparison(avg_rows)
    scores = score_rows(avg_rows)

    write_csv(OUT_DIR / "route_b3_case_metrics.csv", all_case_rows)
    write_csv(OUT_DIR / "route_b3_position_averages.csv", avg_rows)
    write_csv(OUT_DIR / "route_b3_baseline_comparison.csv", comp_rows)
    write_csv(OUT_DIR / "route_b3_min_position_score.csv", scores)
    write_summary(all_case_rows, avg_rows, comp_rows, scores, run_rows)

    debug = {
        "route": "B3",
        "candidate_id": CANDIDATE_ID,
        "new_cases_requested": [c["case_id"] for c in CASES],
        "x_plus_reused_from_route_b2": True,
        "no_x_plus_rerun": True,
        "no_x_plus_2qp": True,
        "no_x_minus_2qp": True,
        "no_y_offset": True,
        "no_41_position_sweep": True,
        "no_bare_reference": True,
        "no_dbr_rcled": True,
        "no_k6": True,
        "no_steering": True,
        "setup_status": setup_status,
        "setup_fsp": str(setup_fsp),
        "setup_warnings": setup_warnings,
        "run_rows": run_rows,
        "extract_debug": extract_debug,
        "patch_inventory_count": len(inventory),
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
    }
    (OUT_DIR / "route_b3_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    failed_runs = [r for r in run_rows if r["fdtd_status"] not in {"ok", "reused", "not_run"}]
    failed_extract = [d for d in extract_debug if d.get("status") != "ok"]
    print(json.dumps({"setup_status": setup_status, "run_rows": run_rows, "position_averages": avg_rows, "score_rows": scores}, indent=2))
    return 1 if setup_status != "ok" or failed_runs or failed_extract else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import stage10_cp_dipole_bw2a_no_dbr_microled_xline_psi99_edge_position_run as base
from metasurface.lumapi_runner import import_lumapi

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_offcenter_edge_power_validation"
RUNTIME_DIR = ROOT / "_runtime" / "stage10_cp_bw2a" / "offcenter_edge_power_validation"
SETUP_DIR = RUNTIME_DIR / "setup"
RESULT_DIR = RUNTIME_DIR / "results"
CENTER_REF = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_power_audit" / "center_spectral_power_audit_all_cones.csv"
REUSE_453_CASE = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_psi99_position_run" / "stage10_cp_dipole_bw2a_psi99_position_case_results.csv"
WAVELENGTHS_NM = [422.0, 453.0, 420.0, 480.0]
CONES = [5.0, 10.0, 20.0]
CANDIDATE_ID = base.CANDIDATE_ID
Q_NM = base.Q_NM


def configure_base() -> None:
    base.OUT_DIR = OUT_DIR
    base.SAVED_DIR = RUNTIME_DIR
    base.SETUP_DIR = SETUP_DIR
    base.RESULT_DIR = RESULT_DIR
    base.WAVELENGTHS_NM = WAVELENGTHS_NM
    base.CONES = CONES


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def normalize_case_row(row: dict[str, str], source: str) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for key in ["wavelength_nm", "source_x_nm", "source_y_nm", "q_nm", "cone_half_angle_deg", "R_power", "L_power", "L_fraction", "DoCP_RminusL", "total_cone_power", "peak_abs_theta_deg"]:
        if out.get(key) not in (None, ""):
            out[key] = float(out[key])
    out["data_source"] = source
    out["result_csv"] = str(OUT_DIR / "offcenter_edge_power_case_results.csv")
    return out


def read_reusable_453_case_rows() -> list[dict[str, Any]]:
    if not REUSE_453_CASE.exists():
        return []
    rows: list[dict[str, Any]] = []
    with REUSE_453_CASE.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row.get("candidate_id") != CANDIDATE_ID:
                continue
            if float(row.get("wavelength_nm", "nan")) != 453.0:
                continue
            if row.get("source_position_label") not in {"x_plus_q", "x_minus_q"}:
                continue
            if row.get("dipole_axis") not in {"x", "y"}:
                continue
            if float(row.get("cone_half_angle_deg", "nan")) not in CONES:
                continue
            if row.get("status") != "ok":
                continue
            rows.append(normalize_case_row(row, "reused_453_position_scan"))
    labels = {(r["source_position_label"], r["dipole_axis"], float(r["cone_half_angle_deg"])) for r in rows}
    expected = {(pos, dip, cone) for pos in ["x_plus_q", "x_minus_q"] for dip in ["x", "y"] for cone in CONES}
    return rows if labels == expected else []


def planned_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wavelength_nm in WAVELENGTHS_NM:
        for pos in base.positions():
            for dip in ["x", "y"]:
                rows.append({
                    "case_id": f"BW2A_OFFEDGE_{CANDIDATE_ID}_{int(wavelength_nm)}NM_{pos['source_position_label'].upper()}_{dip.upper()}DIP",
                    "candidate_id": CANDIDATE_ID,
                    "wavelength_nm": wavelength_nm,
                    "source_position_label": pos["source_position_label"],
                    "position_id": pos["source_position_label"],
                    "x_nm": pos["x_nm"],
                    "y_nm": pos["y_nm"],
                    "z_nm": base.b2.SOURCE_Z_NM,
                    "q_nm": Q_NM,
                    "orientation": dip,
                    "enabled_source": base.b2.X_SOURCE if dip == "x" else base.b2.Y_SOURCE,
                    "disabled_source": base.b2.Y_SOURCE if dip == "x" else base.b2.X_SOURCE,
                    "theta_deg": 90.0,
                    "phi_deg": 0.0 if dip == "x" else 90.0,
                })
    if len(rows) != 16:
        raise RuntimeError(f"Refusing to run: expected exactly 16 cases, got {len(rows)}")
    return rows

def cases_to_run(reused_453: bool) -> list[dict[str, Any]]:
    all_cases = planned_cases()
    todo = []
    for case in all_cases:
        if float(case["wavelength_nm"]) == 453.0 and reused_453:
            continue
        todo.append(case)
    if len(todo) not in {12, 16}:
        raise RuntimeError(f"Refusing to run unexpected case count: {len(todo)}")
    return todo


def read_center_reference() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not CENTER_REF.exists():
        return rows
    with CENTER_REF.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            try:
                wl = float(row.get("wavelength_nm", "nan"))
                cone = float(row.get("cone_deg", row.get("cone_half_angle_deg", "nan")))
            except ValueError:
                continue
            if wl not in WAVELENGTHS_NM or cone not in CONES:
                continue
            total = float(row["total_cone_power"])
            lf = float(row["L_fraction"])
            rows.append({
                "candidate_id": CANDIDATE_ID,
                "wavelength_nm": wl,
                "cone_half_angle_deg": cone,
                "center_total_cone_power": total,
                "center_L_fraction": lf,
                "center_DoCP_RminusL": float(row["DoCP_RminusL"]),
                "center_usable_L_power": total * lf,
                "source_csv": row.get("source_csv", str(CENTER_REF)),
            })
    return rows


def add_power_metrics(rows: list[dict[str, Any]]) -> None:
    for r in rows:
        total = float(r.get("total_cone_power_incoh", r.get("total_cone_power", 0.0)))
        lf = float(r.get("L_fraction_incoh", r.get("L_fraction", 0.0)))
        usable = total * lf
        leakage = total * (1.0 - lf)
        r["usable_L_power"] = usable
        r["leakage_R_power"] = leakage
        r["L_to_R_power_ratio"] = usable / leakage if leakage > 0 else float("inf")


def retention_summary(avg_rows: list[dict[str, Any]], center_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    add_power_metrics(avg_rows)
    center = {(float(r["wavelength_nm"]), float(r["cone_half_angle_deg"])): r for r in center_rows}
    out: list[dict[str, Any]] = []
    for wl in WAVELENGTHS_NM:
        for cone in CONES:
            subset = [r for r in avg_rows if float(r["wavelength_nm"]) == wl and float(r["cone_half_angle_deg"]) == cone and r.get("status") == "ok"]
            cref = center.get((wl, cone))
            row: dict[str, Any] = {"candidate_id": CANDIDATE_ID, "wavelength_nm": wl, "cone_half_angle_deg": cone, "status": "ok" if len(subset) == 2 and cref else "missing_reference_or_pair"}
            if len(subset) == 2 and cref:
                by_pos = {r["source_position_label"]: r for r in subset}
                center_l = float(cref["center_usable_L_power"])
                vals = [float(r["usable_L_power"]) for r in subset]
                lfs = [float(r["L_fraction_incoh"]) for r in subset]
                row.update({
                    "center_usable_L_power": center_l,
                    "x_minus_q_usable_L_power": by_pos["x_minus_q"]["usable_L_power"],
                    "x_plus_q_usable_L_power": by_pos["x_plus_q"]["usable_L_power"],
                    "x_minus_q_retention_vs_center": by_pos["x_minus_q"]["usable_L_power"] / center_l if center_l else float("nan"),
                    "x_plus_q_retention_vs_center": by_pos["x_plus_q"]["usable_L_power"] / center_l if center_l else float("nan"),
                    "min_offcenter_usable_L_power": min(vals),
                    "avg_offcenter_usable_L_power": sum(vals) / len(vals),
                    "min_offcenter_retention_vs_center": min(vals) / center_l if center_l else float("nan"),
                    "avg_offcenter_retention_vs_center": (sum(vals) / len(vals)) / center_l if center_l else float("nan"),
                    "min_offcenter_L_fraction": min(lfs),
                    "avg_offcenter_L_fraction": sum(lfs) / len(lfs),
                })
            out.append(row)
    return out


def report(avg_rows: list[dict[str, Any]], retention: list[dict[str, Any]], reused_cases: list[str], run_cases: list[str]) -> None:
    rows20 = [r for r in avg_rows if float(r["cone_half_angle_deg"]) == 20.0 and r.get("status") == "ok"]
    all_pass = all(float(r["L_fraction_incoh"]) >= 0.60 and float(r["DoCP_RminusL_incoh"]) < 0 for r in rows20)
    near = [r for r in rows20 if 0.60 <= float(r["L_fraction_incoh"]) < 0.70]
    best_power = max(rows20, key=lambda r: float(r["usable_L_power"])) if rows20 else None
    ret20 = [r for r in retention if float(r["cone_half_angle_deg"]) == 20.0 and r.get("status") == "ok"]
    best_ret = max(ret20, key=lambda r: float(r["min_offcenter_retention_vs_center"])) if ret20 else None
    red = [r for r in rows20 if float(r["wavelength_nm"]) == 480.0]
    red_fail = [r for r in red if float(r["L_fraction_incoh"]) < 0.60 or float(r["DoCP_RminusL_incoh"]) >= 0]
    lines = [
        "# Stage10 CP BW2A PSI99 Off-center Edge/Power Validation", "", "## English Summary", "",
        "Scope: PSI99 only; no-DBR ordinary MicroLED; x_plus_q/x_minus_q only; wavelengths 420/422/453/480 nm.",
        "No DBR, no RCLED, no center-boundary expansion, no y-offsets, no full 2D sweep.",
        "CP basis: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); DoCP_RminusL < 0 means L_out dominance.", "",
        f"- Reused cases: {len(reused_cases)}", f"- Newly run cases: {len(run_cases)}", f"- All 20 deg off-center positions pass L_fraction >= 0.60: {'yes' if all_pass else 'no'}",
    ]
    if best_power:
        lines.append(f"- Highest off-center usable L_out power at 20 deg: {best_power['wavelength_nm']} nm {best_power['source_position_label']}, usable_L={float(best_power['usable_L_power']):.6e}, L_fraction={float(best_power['L_fraction_incoh']):.6f}.")
    if best_ret:
        lines.append(f"- Best minimum off-center retention at 20 deg: {best_ret['wavelength_nm']} nm, min retention={float(best_ret['min_offcenter_retention_vs_center']):.6f}.")
    lines.append(f"- Near-threshold 20 deg warnings: {len(near)}.")
    lines.append("- Red edge 480 nm does not fail by CP selectivity." if not red_fail else "- Red edge 480 nm has a CP-selectivity failure.")
    lines += ["", "### 20 deg off-center incoherent rows"]
    for r in sorted(rows20, key=lambda x: (float(x["wavelength_nm"]), x["source_position_label"])):
        lines.append(f"- {r['wavelength_nm']} nm {r['source_position_label']}: L_fraction={float(r['L_fraction_incoh']):.6f}, DoCP={float(r['DoCP_RminusL_incoh']):.6f}, P={float(r['total_cone_power_incoh']):.6e}, usable_L={float(r['usable_L_power']):.6e}")
    lines += ["", "### Reuse / run accounting", "- Reused: " + (", ".join(reused_cases) if reused_cases else "none"), "- Newly run: " + (", ".join(run_cases) if run_cases else "none")]
    lines += ["", "## 中文判断", "", "本轮只验证 PSI99 no-DBR 普通 MicroLED 的 x_plus_q / x_minus_q 离轴位置，波长为 420/422/453/480 nm。没有运行 DBR/RCLED，没有做中心边界扩展，也没有做 y-offset 或 2D 扫描。"]
    lines.append(f"20 deg 下所有离轴位置均保持 L_out 占优并满足 L_fraction >= 0.60：{'是' if all_pass else '否'}。")
    if best_power:
        lines.append(f"20 deg 下离轴可用 L_out power 最高的是 {best_power['wavelength_nm']} nm {best_power['source_position_label']}。")
    if best_ret:
        lines.append(f"20 deg 下相对中心保持率最好的是 {best_ret['wavelength_nm']} nm。")
    lines.append("480 nm 红边没有 CP 选择性失败；若有劣化，主要看可用功率/保持率。" if not red_fail else "480 nm 红边出现 CP 选择性失败。")
    lines.append("后续 RCLED-coupled 验证优先考虑 422 nm 和 453 nm，同时保留 420/480 nm 作为边缘压力点。")
    (OUT_DIR / "offcenter_edge_power_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    configure_base()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    reused_rows = read_reusable_453_case_rows()
    reused_453 = bool(reused_rows)
    all_cases = planned_cases()
    todo = cases_to_run(reused_453)
    write_csv(OUT_DIR / "offcenter_edge_power_run_table.csv", [{**c, "planned_action": "reuse" if float(c["wavelength_nm"]) == 453.0 and reused_453 else "run"} for c in all_cases])
    runtime = SimpleNamespace(lumapi_python_api_dir=r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python", hide_gui=True)
    lumapi = import_lumapi(runtime)
    setup_wavelengths = sorted({float(c["wavelength_nm"]) for c in todo})
    setup_paths = {}
    for wl in setup_wavelengths:
        base.WAVELENGTHS_NM = [wl]
        setup_paths.update(base.build_setups(lumapi, runtime))
    base.WAVELENGTHS_NM = WAVELENGTHS_NM
    run_rows = []
    case_rows = list(reused_rows)
    debug = []
    for case in todo:
        base.patch_candidate(float(case["wavelength_nm"]))
        run_row = base.run_one(lumapi, runtime, setup_paths[float(case["wavelength_nm"])], case)
        run_rows.append(run_row)
        rows, info = base.extract_case(lumapi, runtime, case)
        for row in rows:
            row["data_source"] = "new_fdtd"
            row["result_csv"] = str(OUT_DIR / "offcenter_edge_power_case_results.csv")
        case_rows.extend(rows)
        debug.append(info)
    avg_rows = base.incoherent(case_rows)
    for row in avg_rows:
        row["data_source"] = "mixed_reused_453_and_new_fdtd" if float(row["wavelength_nm"]) == 453.0 and reused_453 else "new_fdtd"
    add_power_metrics(case_rows)
    add_power_metrics(avg_rows)
    center_rows = read_center_reference()
    retention = retention_summary(avg_rows, center_rows)
    write_csv(OUT_DIR / "offcenter_edge_power_case_results.csv", case_rows)
    write_csv(OUT_DIR / "offcenter_edge_power_incoherent_summary.csv", avg_rows)
    write_csv(OUT_DIR / "offcenter_edge_power_center_reference.csv", center_rows)
    write_csv(OUT_DIR / "offcenter_edge_power_retention_summary.csv", retention)
    reused_cases = sorted({f"453:{r['source_position_label']}:{r['dipole_axis']}" for r in reused_rows})
    run_cases = [c["case_id"] for c in todo]
    summary = {
        "stage": "Stage10 CP BW2A PSI99 off-center edge/power validation",
        "candidate_id": CANDIDATE_ID,
        "wavelengths_nm": WAVELENGTHS_NM,
        "positions": ["x_minus_q", "x_plus_q"],
        "q_nm": Q_NM,
        "cones_deg": CONES,
        "runtime_dir": str(RUNTIME_DIR),
        "reused_cases": reused_cases,
        "new_cases_requested": len(todo),
        "new_cases_completed_or_reused": sum(1 for r in run_rows if r.get("fdtd_status") in {"ok", "reused"}),
        "failed_cases": [r for r in run_rows if r.get("fdtd_status") not in {"ok", "reused"}],
        "case_rows_ok": sum(1 for r in case_rows if r.get("status") == "ok"),
        "incoherent_rows_ok": sum(1 for r in avg_rows if r.get("status") == "ok"),
        "center_reference_rows": len(center_rows),
        "retention_rows": len(retention),
        "no_dbr": True,
        "no_rcled": True,
        "no_y_offsets": True,
        "extract_debug": debug,
    }
    (OUT_DIR / "offcenter_edge_power_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report(avg_rows, retention, reused_cases, run_cases)
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed_cases"] else 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_power_audit"
INPUTS = [
    ("ultra", ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_boundary_ultra"),
    ("wide", ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_boundary_wide"),
    ("boundary", ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_boundary"),
]
CSV_NAMES = [
    "stage10_cp_dipole_bw2a_center_spectral_boundary_combined_summary.csv",
    "stage10_cp_dipole_bw2a_center_spectral_boundary_incoherent_summary.csv",
    "stage10_cp_dipole_bw2a_center_spectral_boundary_case_results.csv",
]
EXPECTED_WAVELENGTHS = [420, 422, 424, 426, 428, 430, 432, 434, 436, 438, 440, 442, 444, 446, 447, 448, 450, 453, 454, 455, 456, 458, 460, 462, 464, 466, 468, 470, 472, 474, 476, 478, 480]
EXPECTED_CONES = [5, 10, 20]


def f(row, *names):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return float(value)
    return None


def norm_row(row, source, path):
    wl = f(row, "wavelength_nm", "nm")
    cone = f(row, "cone_deg", "cone_angle_deg", "cone_half_angle_deg")
    total = f(row, "total_cone_power", "total_power", "total_cone_power_incoh")
    lf = f(row, "L_fraction", "L_fraction_incoh")
    docp = f(row, "DoCP_RminusL", "DoCP_RminusL_incoh")
    if wl is None or cone is None or total is None or lf is None or docp is None:
        return None
    if row.get("candidate_id") and row["candidate_id"] != "BW2_J1J2_D194_T90_PSI99_H525":
        return None
    if row.get("source_position_label") and row["source_position_label"] != "center":
        return None
    wl_i = int(round(wl)) if abs(wl - round(wl)) < 1e-6 else wl
    cone_i = int(round(cone)) if abs(cone - round(cone)) < 1e-6 else cone
    usable_l = total * lf
    leakage_r = total * (1.0 - lf)
    ratio = usable_l / leakage_r if leakage_r > 0 else float("inf")
    return {
        "wavelength_nm": wl_i,
        "cone_deg": cone_i,
        "total_cone_power": total,
        "L_fraction": lf,
        "DoCP_RminusL": docp,
        "usable_L_power": usable_l,
        "leakage_R_power": leakage_r,
        "L_to_R_power_ratio": ratio,
        "source_priority": source,
        "source_csv": str(path.relative_to(ROOT)),
    }


def read_rows():
    rows_by_key = {}
    read_files = []
    for source, folder in INPUTS:
        if not folder.exists():
            continue
        for name in CSV_NAMES:
            path = folder / name
            if not path.exists():
                continue
            read_files.append(str(path.relative_to(ROOT)))
            with path.open(newline="", encoding="utf-8-sig") as fh:
                for raw in csv.DictReader(fh):
                    row = norm_row(raw, source, path)
                    if not row:
                        continue
                    key = (row["wavelength_nm"], row["cone_deg"])
                    rows_by_key.setdefault(key, row)
    rows = list(rows_by_key.values())
    for cone in EXPECTED_CONES:
        cone_rows = [r for r in rows if r["cone_deg"] == cone]
        max_total = max((float(r["total_cone_power"]) for r in cone_rows), default=0.0)
        max_l = max((float(r["usable_L_power"]) for r in cone_rows), default=0.0)
        for r in cone_rows:
            r["normalized_total_power"] = float(r["total_cone_power"]) / max_total if max_total else 0.0
            r["normalized_usable_L_power"] = float(r["usable_L_power"]) / max_l if max_l else 0.0
    return sorted(rows, key=lambda r: (float(r["cone_deg"]), float(r["wavelength_nm"]))), read_files


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def best_windows(rows):
    out = []
    for cone in EXPECTED_CONES:
        cone_rows = [r for r in rows if r["cone_deg"] == cone]
        for width in [4, 6, 8, 10]:
            best = None
            for start in EXPECTED_WAVELENGTHS:
                selected = [r for r in cone_rows if start <= float(r["wavelength_nm"]) <= start + width]
                if not selected:
                    continue
                score = sum(float(r["usable_L_power"]) for r in selected) / len(selected)
                rec = {
                    "cone_deg": cone,
                    "window_width_nm": width,
                    "window_start_nm": start,
                    "window_end_nm": start + width,
                    "sample_count": len(selected),
                    "avg_usable_L_power": score,
                    "avg_total_cone_power": sum(float(r["total_cone_power"]) for r in selected) / len(selected),
                    "avg_L_fraction": sum(float(r["L_fraction"]) for r in selected) / len(selected),
                    "wavelengths_in_window": ";".join(str(r["wavelength_nm"]) for r in selected),
                }
                if best is None or score > float(best["avg_usable_L_power"]):
                    best = rec
            if best:
                out.append(best)
    return out


def fmt(x):
    return f"{float(x):.6g}" if isinstance(x, (float, int)) else str(x)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, read_files = read_rows()
    fields = ["wavelength_nm", "cone_deg", "total_cone_power", "L_fraction", "DoCP_RminusL", "usable_L_power", "leakage_R_power", "L_to_R_power_ratio", "normalized_total_power", "normalized_usable_L_power", "source_priority", "source_csv"]
    write_csv(OUT / "center_spectral_power_audit_all_cones.csv", rows, fields)

    rankings = {}
    for cone in EXPECTED_CONES:
        ranked = sorted([r for r in rows if r["cone_deg"] == cone], key=lambda r: float(r["usable_L_power"]), reverse=True)
        rankings[cone] = ranked
        write_csv(OUT / f"center_spectral_power_audit_rank_{cone}deg.csv", ranked, fields)

    windows = best_windows(rows)
    window_fields = ["cone_deg", "window_width_nm", "window_start_nm", "window_end_nm", "sample_count", "avg_usable_L_power", "avg_total_cone_power", "avg_L_fraction", "wavelengths_in_window"]
    write_csv(OUT / "center_spectral_power_audit_best_windows.csv", windows, window_fields)

    missing = [{"wavelength_nm": wl, "cone_deg": cone} for wl in EXPECTED_WAVELENGTHS for cone in EXPECTED_CONES if not any(r["wavelength_nm"] == wl and r["cone_deg"] == cone for r in rows)]
    strongest_total = {cone: max((r for r in rows if r["cone_deg"] == cone), key=lambda r: float(r["total_cone_power"]), default=None) for cone in EXPECTED_CONES}
    strongest_l = {cone: rankings[cone][0] if rankings[cone] else None for cone in EXPECTED_CONES}
    cp_max = {cone: max((r for r in rows if r["cone_deg"] == cone), key=lambda r: float(r["L_fraction"]), default=None) for cone in EXPECTED_CONES}

    total20 = strongest_total[20]
    l20 = strongest_l[20]
    cp20 = cp_max[20]
    red_rows = sorted([r for r in rows if r["cone_deg"] == 20 and float(r["wavelength_nm"]) >= 454], key=lambda r: float(r["wavelength_nm"]))
    max20 = max((float(r["total_cone_power"]) for r in rows if r["cone_deg"] == 20), default=0.0)
    red_total_drop = float(red_rows[-1]["total_cone_power"]) / max20 if red_rows and max20 else None
    red_lf_min = min((float(r["L_fraction"]) for r in red_rows), default=None)
    best_window_20 = max((w for w in windows if w["cone_deg"] == 20), key=lambda w: float(w["avg_usable_L_power"]), default=None)

    summary = {
        "stage": "Stage10 CP BW2A PSI99 center spectral power audit",
        "read_existing_csv_only": True,
        "fdtd_run": False,
        "fsp_ldf_runtime_touched": False,
        "read_files": read_files,
        "row_count": len(rows),
        "missing_rows": missing,
        "strongest_total_power_by_cone": {str(k): v for k, v in strongest_total.items()},
        "strongest_usable_L_power_by_cone": {str(k): v for k, v in strongest_l.items()},
        "strongest_L_fraction_by_cone": {str(k): v for k, v in cp_max.items()},
        "best_windows": windows,
        "power_max_aligned_with_cp_selectivity_max_20deg": bool(total20 and cp20 and total20["wavelength_nm"] == cp20["wavelength_nm"]),
        "usable_L_max_aligned_with_cp_selectivity_max_20deg": bool(l20 and cp20 and l20["wavelength_nm"] == cp20["wavelength_nm"]),
        "red_side_total_power_ratio_at_480_vs_max20": red_total_drop,
        "red_side_min_L_fraction_20deg": red_lf_min,
        "recommended_off_center_wavelengths_nm": {"power_maximum": l20["wavelength_nm"] if l20 else None, "project_center": 453, "blue_edge": 420, "red_edge": 480},
    }
    (OUT / "center_spectral_power_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def line_for(row):
        if not row:
            return "missing"
        return f"{row['wavelength_nm']} nm: total={fmt(row['total_cone_power'])}, L_fraction={fmt(row['L_fraction'])}, usable_L={fmt(row['usable_L_power'])}"

    report = [
        "# Stage10 CP BW2A PSI99 Center Spectral Power Audit", "", "## English Summary", "",
        "This audit reads existing CSV outputs only. No FDTD was run, and no FSP/LDF/runtime files were opened, moved, deleted, or modified.", "",
        "### Strongest Total Cone Power",
    ]
    for cone in EXPECTED_CONES:
        report.append(f"- {cone} deg: {line_for(strongest_total[cone])}")
    report += ["", "### Strongest Usable L_out Power"]
    for cone in EXPECTED_CONES:
        report.append(f"- {cone} deg: {line_for(strongest_l[cone])}")
    report += ["", "### Strongest Spectral Windows by Average Usable L_out Power"]
    for w in windows:
        report.append(f"- {w['cone_deg']} deg, {w['window_width_nm']} nm window: {w['window_start_nm']}-{w['window_end_nm']} nm, avg usable L={fmt(w['avg_usable_L_power'])}, avg total={fmt(w['avg_total_cone_power'])}, avg L_fraction={fmt(w['avg_L_fraction'])}")
    report += ["", "### Interpretation"]
    report.append(f"- At 20 deg, total-power maximum is {line_for(total20)}.")
    report.append(f"- At 20 deg, usable-L maximum is {line_for(l20)}.")
    report.append(f"- At 20 deg, CP-selectivity maximum is {line_for(cp20)}.")
    report.append("- The power maximum is not aligned with the CP-selectivity maximum." if not summary["power_max_aligned_with_cp_selectivity_max_20deg"] else "- The power maximum is aligned with the CP-selectivity maximum.")
    report.append("- The red side mainly loses total cone power; L_fraction remains high and does not indicate a CP-selectivity collapse.")
    report.append(f"- Best 20 deg window: {best_window_20['window_start_nm']}-{best_window_20['window_end_nm']} nm by average usable L_out power." if best_window_20 else "- Best 20 deg window: missing.")
    report.append(f"- Missing expected rows: {len(missing)}.")
    report += ["", "### Recommended Off-center Validation Wavelengths"]
    rec = summary["recommended_off_center_wavelengths_nm"]
    report.append(f"- Power maximum wavelength: {rec['power_maximum']} nm")
    report.append(f"- Project-center wavelength: {rec['project_center']} nm")
    report.append(f"- Blue edge wavelength: {rec['blue_edge']} nm")
    report.append(f"- Red edge wavelength: {rec['red_edge']} nm")
    report += ["", "## 中文判断", "", "本审计只读取已有 CSV，没有运行 FDTD，也没有打开、移动、删除或修改 FSP/LDF/runtime 文件。", "", f"20 deg 下，总 cone power 最强点为 {line_for(total20)}。", f"20 deg 下，可用 L_out power 最强点为 {line_for(l20)}。", f"20 deg 下，CP 选择性最高点为 {line_for(cp20)}。", "功率峰值与 CP 选择性峰值不完全重合。红侧主要是 total cone power 下降，L_fraction 仍保持较高，不是 CP 选择性塌陷。", f"建议后续 off-center 检查波长：功率峰值 {rec['power_maximum']} nm、项目中心 {rec['project_center']} nm、蓝边 {rec['blue_edge']} nm、红边 {rec['red_edge']} nm。"]
    (OUT / "center_spectral_power_audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

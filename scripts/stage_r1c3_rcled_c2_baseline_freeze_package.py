from __future__ import annotations
import csv, json
from pathlib import Path
ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r1c3_rcled_c2_baseline_freeze_package"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"
PRIMARY_ROWS = [
    {"wavelength_nm": 450, "eta10": 0.398, "eta20": 0.587, "eta30": 0.856, "peak_abs_angle_deg": 9.30, "dominant_zone": "abs_5_10"},
    {"wavelength_nm": 453, "eta10": 0.461, "eta20": 0.682, "eta30": 0.856, "peak_abs_angle_deg": 9.01, "dominant_zone": "abs_5_10"},
    {"wavelength_nm": 456, "eta10": 0.494, "eta20": 0.719, "eta30": 0.861, "peak_abs_angle_deg": 6.81, "dominant_zone": "abs_5_10"},
]
BACKUP_ROWS = [
    {"wavelength_nm": 450, "eta20": 0.634, "peak_abs_angle_deg": 9.18},
    {"wavelength_nm": 453, "eta20": 0.690, "peak_abs_angle_deg": 6.92},
    {"wavelength_nm": 456, "eta20": 0.655, "peak_abs_angle_deg": 7.27},
]

def write_csv(path, rows):
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    primary = {
        "candidate_id": "R1C2_C2_cav230", "role": "primary", "top_pair_count": 6,
        "bottom_pair_count": 0, "cavity_span_nm": 230, "termination": "TiO2_50nm",
        "validated_wavelengths": "450,453,456", "avg_eta20": sum(r["eta20"] for r in PRIMARY_ROWS)/3,
        "min_eta20": min(r["eta20"] for r in PRIMARY_ROWS),
        "max_peak_abs_angle_deg": max(r["peak_abs_angle_deg"] for r in PRIMARY_ROWS),
    }
    backup = {
        "candidate_id": "R1C2_C2_base", "role": "backup", "top_pair_count": 6,
        "bottom_pair_count": 0, "cavity_span_nm": 220, "termination": "TiO2_50nm",
        "validated_wavelengths": "450,453,456", "avg_eta20": sum(r["eta20"] for r in BACKUP_ROWS)/3,
        "min_eta20": min(r["eta20"] for r in BACKUP_ROWS),
        "max_peak_abs_angle_deg": max(r["peak_abs_angle_deg"] for r in BACKUP_ROWS),
    }
    package = {
        "stage": "R1C3_RCLED_C2_baseline_freeze_package",
        "primary_frozen_baseline": primary,
        "primary_wavelength_results": PRIMARY_ROWS,
        "backup_candidate": backup,
        "backup_wavelength_results": BACKUP_ROWS,
        "old_route_rejected": "m8 + bottomDBR99 / R1B route produced symmetric off-normal 20-30 degree lobes",
        "r1c0": "TMM redesign found top=6 bottom=0 family",
        "r1c1": "validated top3 and selected C2",
        "r1c2": "refined C2 and selected C2_cav230",
        "source_y_sweep": "allowed as robustness test, not rescue",
        "apcd_integration": "not yet run",
    }
    (OUT / "r1c3_frozen_baseline.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    write_csv(OUT / "r1c3_frozen_baseline.csv", [primary] + PRIMARY_ROWS)
    write_csv(OUT / "r1c3_backup_candidate.csv", [backup] + BACKUP_ROWS)
    summary = [
        "# R1C3 RCLED C2 baseline freeze package", "",
        "Old m8 + bottomDBR99 / R1B route was rejected because it produced symmetric off-normal 20-30 degree lobes.",
        "R1C0 TMM redesign found the top=6 bottom=0 family.",
        "R1C1 validated top3 and selected C2.",
        "R1C2 refined C2 and selected C2_cav230.", "",
        "Primary baseline = R1C2_C2_cav230: top_pair_count=6, bottom_pair_count=0, cavity_span_nm=230, termination=TiO2_50nm.",
        "Backup = R1C2_C2_base: top_pair_count=6, bottom_pair_count=0, cavity_span_nm=220, termination=TiO2_50nm.", "",
        "| wl nm | eta10 | eta20 | eta30 | peak_abs deg | dominant zone |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for r in PRIMARY_ROWS:
        summary.append(f"| {r['wavelength_nm']} | {r['eta10']:.3f} | {r['eta20']:.3f} | {r['eta30']:.3f} | {r['peak_abs_angle_deg']:.2f} | {r['dominant_zone']} |")
    summary += ["", "Source-y sweep is now allowed as a robustness test, not rescue. APCD integration has not yet run."]
    (OUT / "r1c3_stage_history_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    next_steps = [
        "# R1C3 next steps", "",
        "1. Freeze R1C2_C2_cav230 as the RCLED/MDC source-module baseline.",
        "2. Keep R1C2_C2_base as backup.",
        "3. Run a small source-y robustness test around the frozen baseline.",
        "4. Review before any APCD integration.",
    ]
    (OUT / "r1c3_next_steps.md").write_text("\n".join(next_steps) + "\n", encoding="utf-8")
    text = INDEX.read_text(encoding="utf-8")
    if "## R1C3 freeze status" not in text:
        text = text.rstrip() + "\n\n## R1C3 freeze status\n\n- frozen primary baseline: R1C2_C2_cav230\n- backup: R1C2_C2_base\n- next stage: source-y robustness test around frozen baseline\n- APCD integration: not yet run\n"
    INDEX.write_text(text, encoding="utf-8")
if __name__ == "__main__":
    main()

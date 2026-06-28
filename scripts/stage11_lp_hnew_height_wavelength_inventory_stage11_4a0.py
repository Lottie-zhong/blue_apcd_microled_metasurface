from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

HEIGHTS = [500, 550, 600, 650, 700, 750]
SCOUT_WAVELENGTHS = [451, 452, 453]
PRIMARY_HEIGHTS = [600, 650]
SECONDARY_HEIGHTS = [700]
DEFERRED_HEIGHTS = [550, 750]
PRIORITY_BINS = [240, 300]
COVERAGE_BINS = [0, 60, 120, 180]
ALL_BINS = COVERAGE_BINS + PRIORITY_BINS


def semis(values: list[int]) -> str:
    return ";".join(str(v) for v in values)


def existing_data_rows() -> list[dict[str, str]]:
    return [
        {
            "height_nm": "500",
            "data_status": "existing_historical_lp_data",
            "source_scope": "tracked_reports_scripts",
            "notes": "H500 has extensive Stage11-3 data but failed narrowband robust six-bin rescue",
        },
        {
            "height_nm": "550",
            "data_status": "no_confirmed_multiwavelength_lp_dimer_data",
            "source_scope": "tracked_reports_scripts",
            "notes": "H550 deferred",
        },
        {
            "height_nm": "600",
            "data_status": "no_confirmed_multiwavelength_lp_dimer_data",
            "source_scope": "tracked_reports_scripts",
            "notes": "H600 primary new-height scout",
        },
        {
            "height_nm": "650",
            "data_status": "no_confirmed_multiwavelength_lp_dimer_data",
            "source_scope": "tracked_reports_scripts",
            "notes": "H650 primary new-height scout",
        },
        {
            "height_nm": "700",
            "data_status": "no_confirmed_multiwavelength_lp_dimer_data",
            "source_scope": "tracked_reports_scripts",
            "notes": "H700 priority-bin-only scout",
        },
        {
            "height_nm": "750",
            "data_status": "no_confirmed_multiwavelength_lp_dimer_data",
            "source_scope": "tracked_reports_scripts",
            "notes": "H750 deferred simulation-only extension",
        },
    ]


def candidate_space_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for height in PRIMARY_HEIGHTS:
        for bin_deg in ALL_BINS:
            rows.append(
                {
                    "height_nm": str(height),
                    "phase_bin_hint_deg": str(bin_deg),
                    "candidate_family": "Hnew_template_from_H500_geometry",
                    "priority_for_stage11_4a1": "highest_priority_bin"
                    if bin_deg in PRIORITY_BINS
                    else "coverage_bin",
                    "planned_status": "included",
                    "reason": f"H{height} primary fixed-height scout",
                }
            )
    for bin_deg in PRIORITY_BINS:
        rows.append(
            {
                "height_nm": "700",
                "phase_bin_hint_deg": str(bin_deg),
                "candidate_family": "Hnew_template_from_H500_geometry",
                "priority_for_stage11_4a1": "medium_high_priority_bin",
                "planned_status": "included",
                "reason": "H700 priority-bin-only scout",
            }
        )
    for height in DEFERRED_HEIGHTS:
        rows.append(
            {
                "height_nm": str(height),
                "phase_bin_hint_deg": "all",
                "candidate_family": "Hnew_template_from_H500_geometry",
                "priority_for_stage11_4a1": "deferred",
                "planned_status": "deferred",
                "reason": f"H{height} deferred",
            }
        )
    return rows


def planned_case_rows() -> list[dict[str, str]]:
    wavelengths = semis(SCOUT_WAVELENGTHS)
    all_bins = semis(ALL_BINS)
    return [
        {
            "case_group_id": "S11_4A1_H600_ALL",
            "height_nm": "600",
            "wavelengths_nm": wavelengths,
            "phase_bins_deg": all_bins,
            "priority": "highest",
            "planned_action": "periodic_single_dimer_jones_extraction",
            "reason": "H600 primary fixed-height scout",
            "estimated_stage": "Stage11-4A1",
        },
        {
            "case_group_id": "S11_4A1_H650_ALL",
            "height_nm": "650",
            "wavelengths_nm": wavelengths,
            "phase_bins_deg": all_bins,
            "priority": "highest",
            "planned_action": "periodic_single_dimer_jones_extraction",
            "reason": "H650 primary fixed-height scout",
            "estimated_stage": "Stage11-4A1",
        },
        {
            "case_group_id": "S11_4A1_H700_240_300",
            "height_nm": "700",
            "wavelengths_nm": wavelengths,
            "phase_bins_deg": semis(PRIORITY_BINS),
            "priority": "medium_high",
            "planned_action": "periodic_single_dimer_jones_extraction",
            "reason": "H700 priority-bin-only scout",
            "estimated_stage": "Stage11-4A1",
        },
        {
            "case_group_id": "DEFER_H550",
            "height_nm": "550",
            "wavelengths_nm": wavelengths,
            "phase_bins_deg": all_bins,
            "priority": "deferred",
            "planned_action": "no_run",
            "reason": "H550 deferred unless H600/H650 fail",
            "estimated_stage": "Stage11-4A1_deferred",
        },
        {
            "case_group_id": "DEFER_H750",
            "height_nm": "750",
            "wavelengths_nm": wavelengths,
            "phase_bins_deg": all_bins,
            "priority": "deferred",
            "planned_action": "no_run",
            "reason": "H750 deferred as simulation-only extension",
            "estimated_stage": "Stage11-4A1_deferred",
        },
    ]


def manifest() -> dict[str, object]:
    cases = planned_case_rows()
    return {
        "stage": "Stage11-4A0",
        "created_by": "stage11_lp_hnew_height_wavelength_inventory_stage11_4a0.py",
        "no_fdtd_run_in_stage11_4a0": True,
        "hard_case_cap": 180,
        "primary_heights": PRIMARY_HEIGHTS,
        "secondary_heights": SECONDARY_HEIGHTS,
        "deferred_heights": DEFERRED_HEIGHTS,
        "scout_wavelengths_nm": SCOUT_WAVELENGTHS,
        "priority_bins_deg": PRIORITY_BINS,
        "coverage_bins_deg": COVERAGE_BINS,
        "fixed_height_rule": True,
        "mixed_height_tuple_allowed": False,
        "included_case_groups": [c for c in cases if c["planned_action"] != "no_run"],
        "deferred_case_groups": [c for c in cases if c["planned_action"] == "no_run"],
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_reports(root: Path = ROOT) -> dict[str, Path]:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    paths = {
        "existing": reports / "stage11_4a0_lp_hnew_existing_data_inventory.csv",
        "candidate_space": reports / "stage11_4a0_lp_hnew_candidate_space_inventory.csv",
        "planned_cases": reports / "stage11_4a0_lp_hnew_planned_cases_stage11_4a1.csv",
        "manifest": reports / "stage11_4a0_lp_hnew_case_manifest_stage11_4a1.json",
        "heights": reports / "stage11_4a0_lp_hnew_recommended_heights.md",
        "summary": reports / "stage11_4a0_lp_hnew_summary.md",
    }

    write_csv(paths["existing"], existing_data_rows())
    write_csv(paths["candidate_space"], candidate_space_rows())
    write_csv(paths["planned_cases"], planned_case_rows())
    paths["manifest"].write_text(json.dumps(manifest(), indent=2) + "\n", encoding="utf-8")
    paths["heights"].write_text(recommended_heights_md(), encoding="utf-8")
    paths["summary"].write_text(summary_md(), encoding="utf-8")
    return paths


def recommended_heights_md() -> str:
    return """# Stage11-4A0 Recommended Heights

| Height | Recommendation | Reason |
| --- | --- | --- |
| H500 | closed control | Keep as 450 nm single-point proof-of-concept; small-range robust rescue failed. |
| H550 | defer | Do not spend cases before H600/H650 evidence. |
| H600 | run first | Primary Stage11-4A1 fixed-height scout. |
| H650 | run first | Primary Stage11-4A1 fixed-height scout. |
| H700 | 240/300 only | Secondary priority-bin scout. |
| H750 | defer | Simulation-only extension after lower heights fail. |
"""


def summary_md() -> str:
    return """# Stage11-4A0 LP-Hnew Fixed-Height Planning Summary

Stage11-3B4 closes the H500 small-range LP rescue path for a robust 449/450/451 nm six-bin library.
H500 remains useful as a 450 nm single-point proof-of-concept, not as the robust spectral library.

Stage11 continues as Stage11-4: LP-Hnew fixed-height spectral robust phase-library reconstruction.
Stage11-4A1 should run a bounded Hnew scout:

- H600 and H650: all six bins at 451/452/453 nm.
- H700: 240/300 priority bins at 451/452/453 nm.
- H550 and H750: deferred.

Future six-bin libraries must be H600-only, H650-only, or H700-only. Mixed-height tuples are not allowed.
No K=6 work should start until a fixed-height robust six-bin tuple exists.

Stage11-4A0 is analysis-only. It generated planning tables and did not run simulations.
"""


if __name__ == "__main__":
    for label, path in write_reports().items():
        print(f"{label}: {path}")

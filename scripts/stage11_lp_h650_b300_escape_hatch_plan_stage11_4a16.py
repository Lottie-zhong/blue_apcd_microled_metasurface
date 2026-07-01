from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PLAN_MD = REPORTS / "stage11_4a16_h650_b300_escape_hatch_plan.md"
SPACE_CSV = REPORTS / "stage11_4a16_h650_b300_escape_hatch_candidate_space.csv"
MANIFEST_JSON = REPORTS / "stage11_4a16_h650_b300_escape_hatch_manifest.json"
SUMMARY_JSON = REPORTS / "stage11_4a16_h650_b300_escape_hatch_summary.json"

REQUIRED_INPUTS = [
    "reports/stage11_4a13_h600_true_b300_evidence_table.csv",
    "reports/stage11_4a14_h600_b300_mechanism_summary.json",
    "reports/stage11_4a15_h600_b300_selectivity_phase_hybrid_report.md",
    "reports/stage11_4a15_h600_b300_selectivity_phase_hybrid_summary.json",
    "reports/stage11_4a1_lp_hnew_results.csv",
    "reports/stage11_4a1_lp_hnew_candidate_ranking.csv",
]

GROUPS = [
    {
        "group_id": "S11_4A16_G1_H650_B300_DIRECT_ESCAPE",
        "future_case_count": 12,
        "height_nm": 650,
        "target_bin_deg": 300,
        "wavelengths_nm": "451;452;453",
        "purpose": "test whether H650 shifts selected-channel phase away from the H600 0/60 attractor while preserving LP projection",
        "distinct_from_h600_failure": "new fixed height; excludes H600 B60-donor forcing and does not reuse H600 true-B300 blind search groups",
        "priority": "highest",
    },
    {
        "group_id": "S11_4A16_G2_H650_B300_MINI_REPAIR",
        "future_case_count": 6,
        "height_nm": 650,
        "target_bin_deg": 300,
        "wavelengths_nm": "451;452;453",
        "purpose": "small repair set only if G1 has near-300 phase or near-miss projection evidence",
        "distinct_from_h600_failure": "H650 matrix/phase repair, not H600 rerun; stops if G1 shows the same 0/60 attractor",
        "priority": "conditional",
    },
]
FIELDS = ["group_id", "future_case_count", "height_nm", "target_bin_deg", "wavelengths_nm", "purpose", "distinct_from_h600_failure", "priority"]
DECISION = "H650 B300 escape hatch is distinct from H600 failures because it changes fixed height instead of forcing H600 families that repeatedly landed near 0/60 or collapsed projection near 300."


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    missing_inputs = [p for p in REQUIRED_INPUTS if not (ROOT / p).exists()]
    total_cases = sum(g["future_case_count"] for g in GROUPS)
    with SPACE_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(GROUPS)
    manifest = {
        "stage": "Stage11-4A16",
        "planning_only": True,
        "no_fdtd": True,
        "height_nm": 650,
        "target_bin_deg": 300,
        "wavelengths_nm": [451, 452, 453],
        "max_future_cases": 18,
        "total_future_cases": total_cases,
        "exclude_h600_b60_donor_forcing": True,
        "bounded_escape_hatch_plan_exists": total_cases <= 18 and not missing_inputs,
        "groups": GROUPS,
        "decision_after_future_run": [
            "if H650 B300 loose/strict -> plan coverage 0/120/180 with B60/B240 kept",
            "if high-selectivity but wrong bin -> reassign donor, do not force",
            "if no near-miss -> stop LP-Hnew six-bin attempt and write LP route-positioning audit",
        ],
        "do_not_run": ["FDTD", "coverage", "H600 rerun", "H700", "K=6", "dipole", "DBR", "RCLED"],
    }
    summary = {
        "stage": "Stage11-4A16",
        "missing_inputs": missing_inputs,
        "bounded_escape_hatch_plan_exists": manifest["bounded_escape_hatch_plan_exists"],
        "total_future_cases": total_cases,
        "groups": [g["group_id"] for g in GROUPS],
        "decision": DECISION,
        "recommended_next_run_group": "S11_4A16_G1_H650_B300_DIRECT_ESCAPE",
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Stage11-4A16 H650 B300 Escape-Hatch Plan",
        "",
        "Planning only. No FDTD, coverage, H600 rerun, H700, K=6, dipole, DBR/RCLED, or H500 rescue was run.",
        "",
        "## Context",
        "",
        "H600 B300 is stopped for now: A10/A12/A15 selectivity candidates landed near 0/60, while A11 landed near 300 with collapsed projection/matrix behavior.",
        "A15 best had ratio 11.589234, Tx 0.979696, matrix 0.293775, phase_error 105.037257, nearest 0/60.",
        "",
        "## Decision",
        "",
        DECISION,
        "",
        "## Planned Groups",
        "",
        "| group | cases | purpose | distinctness |",
        "|---|---:|---|---|",
    ]
    for g in GROUPS:
        lines.append(f"| {g['group_id']} | {g['future_case_count']} | {g['purpose']} | {g['distinct_from_h600_failure']} |")
    lines += [
        "",
        "Total future cases: 18. This does not exceed the A16 cap.",
        "",
        "## Boundary",
        "",
        "Do not run coverage, H600 B300 reruns, H700, or K=6 before evaluating H650 B300 G1.",
        "",
    ]
    PLAN_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

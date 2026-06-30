from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PLAN_MD = REPORTS / "stage11_4a14_h600_b300_mechanism_redesign_plan.md"
SPACE_CSV = REPORTS / "stage11_4a14_h600_b300_mechanism_candidate_space.csv"
MANIFEST_JSON = REPORTS / "stage11_4a14_h600_b300_mechanism_manifest.json"
SUMMARY_JSON = REPORTS / "stage11_4a14_h600_b300_mechanism_summary.json"

REQUIRED_INPUTS = [
    "reports/stage11_4a13_h600_true_b300_decision_audit.md",
    "reports/stage11_4a13_h600_true_b300_evidence_table.csv",
    "reports/stage11_4a13_h600_true_b300_summary.json",
    "reports/stage11_4a13_h600_true_b300_recommended_next.md",
    "reports/stage11_4a8_phase_bin_reassignment_summary.json",
    "reports/stage11_4a5_h600_b240_mechanism_expansion_ranking.csv",
]
EXCLUDED_FAMILIES = [
    "B300_x_pair_swap_G80_O-30", "B300_x_pair_swap_G80_O-40", "B300_x_pair_swap_G80_O-20",
    "B300_x_pair_noswap_G80_O-30", "B300_x_pair_swap_G90_O-30", "B300_x_pair_noswap_G100_O-24",
]
GROUPS = [
    {"group_id":"S11_4A14_G1_B300_SELECTIVITY_WITH_300_PHASE_HYBRID","future_case_count":12,"height_nm":600,"target_bin_deg":300,"wavelengths_nm":"451;452;453","mechanism":"hybridize A10 moderate-selectivity geometry with A11 near-300 phase anchors","distinct_from_prior":"combines A10 selectivity source and A11 phase source instead of rerunning either family","purpose":"recover projection selectivity while keeping selected phase near 300","priority":"highest"},
    {"group_id":"S11_4A14_G2_B300_MATRIX_REPAIR_NEAR_300","future_case_count":6,"height_nm":600,"target_bin_deg":300,"wavelengths_nm":"451;452;453","mechanism":"small-gap and orientation repair around A11 near-300 but leaky family","distinct_from_prior":"uses A11 only as a phase-local anchor and changes matrix-repair knobs","purpose":"keep near-300 phase while reducing blocked-y leakage","priority":"high"},
    {"group_id":"S11_4A14_G3_B300_NON_B60_ANCHOR_MICRO_ESCAPE","future_case_count":6,"height_nm":600,"target_bin_deg":300,"wavelengths_nm":"451;452;453","mechanism":"non-B60 anchor micro-escape using diagonal/noswap candidates not in A8 donor family","distinct_from_prior":"excludes A8 B60 donor family and avoids A12 mini-escape geometries","purpose":"last bounded H600-only escape before H650 planning","priority":"medium"},
]
FIELDS = ["group_id","future_case_count","height_nm","target_bin_deg","wavelengths_nm","mechanism","distinct_from_prior","purpose","priority"]
DECISION = "A bounded distinct H600 B300 mechanism plan exists, but it is the last H600 true-B300 attempt before H650 escape-hatch planning."


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    missing_inputs = [p for p in REQUIRED_INPUTS if not (ROOT / p).exists()]
    total_cases = sum(g["future_case_count"] for g in GROUPS)
    with SPACE_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(GROUPS)
    manifest = {
        "stage":"Stage11-4A14", "planning_only":True, "no_fdtd":True,
        "height_nm":600, "target_bin_deg":300, "wavelengths_nm":[451,452,453],
        "max_future_cases":24, "total_future_cases":total_cases,
        "bounded_distinct_plan_exists": total_cases <= 24 and not missing_inputs,
        "excluded_b60_donor_families":EXCLUDED_FAMILIES, "groups":GROUPS,
        "decision_after_future_run":[
            "if B300 loose/strict -> run coverage 0/120/180",
            "if phase near 300 but selectivity weak -> one matrix-repair refinement only",
            "if selectivity good but phase not 300 -> reassign donor, do not force",
            "if no near-miss -> stop H600 B300 and plan H650 escape hatch",
        ],
        "do_not_run":["FDTD","coverage","H650","K=6","finite patch","dipole","DBR","RCLED"],
    }
    summary = {"stage":"Stage11-4A14","missing_inputs":missing_inputs,"bounded_distinct_plan_exists":manifest["bounded_distinct_plan_exists"],"total_future_cases":total_cases,"groups":[g["group_id"] for g in GROUPS],"decision":DECISION,"recommended_next_route":"Run A14 G1 only if continuing H600; otherwise plan H650 B300 escape hatch."}
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = ["# Stage11-4A14 H600 B300 Mechanism Redesign Plan","","Planning only. No FDTD, coverage, H650, K=6, finite patch, dipole, DBR/RCLED, or H500 rescue was run.","","## Why Previous B300 Searches Failed","","- A10 G1: moderate selectivity, but selected phase landed near 0 rather than 300.","- A11 G2: selected phase landed near 300, but projection selectivity collapsed.","- A12 G3: no useful result; best case still failed ratio, matrix, and phase gates.","- A8 high-selectivity B300-labeled family is a B60 donor and is excluded from B300 forcing.","","## Decision","",DECISION,"","## Planned Groups","","| group | cases | purpose | distinctness |","|---|---:|---|---|"]
    for g in GROUPS:
        lines.append(f"| {g['group_id']} | {g['future_case_count']} | {g['purpose']} | {g['distinct_from_prior']} |")
    lines += ["","Total future cases: 24. This does not exceed the A14 cap.","","## Boundary","","Do not run H600 coverage, H650, or K=6 until true B300 has loose/strict evidence or H600 is formally stopped.",""]
    PLAN_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

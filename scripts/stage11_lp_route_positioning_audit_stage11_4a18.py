from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
AUDIT_MD = REPORTS / "stage11_4a18_lp_route_positioning_audit.md"
EVIDENCE_CSV = REPORTS / "stage11_4a18_lp_route_positioning_evidence_table.csv"
SUMMARY_JSON = REPORTS / "stage11_4a18_lp_route_positioning_summary.json"
NEXT_MD = REPORTS / "stage11_4a18_lp_route_positioning_recommended_next.md"

REQUIRED_INPUTS = [
    "reports/stage11_4a5_h600_b240_mechanism_expansion_ranking.csv",
    "reports/stage11_4a8_phase_bin_reassignment_report.md",
    "reports/stage11_4a13_h600_true_b300_decision_audit.md",
    "reports/stage11_4a15_h600_b300_selectivity_phase_hybrid_report.md",
    "reports/stage11_4a16_h650_b300_escape_hatch_plan.md",
    "reports/stage11_4a17_h650_b300_direct_escape_report.md",
    "reports/stage11_4a17_h650_b300_direct_escape_recommended_next.md",
]

FIELDS = ["evidence_id", "role", "height_nm", "candidate_id", "ratio", "Tx", "matrix_error", "phase_error_deg", "nearest_actual_bins", "pass_level", "decision_use", "notes"]
EVIDENCE = [
    {"evidence_id":"A8_B60_DONOR","role":"partial LP evidence: B60 strict donor","height_nm":"600","candidate_id":"H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40","ratio":"11.278722","Tx":"0.752180","matrix_error":"0.297811","phase_error_deg":"24.596581","nearest_actual_bins":"60","pass_level":"strict","decision_use":"keep_as_partial_evidence","notes":"B300-labeled family is useful as actual B60, not true B300."},
    {"evidence_id":"A5_B240_LOOSE","role":"partial LP evidence: B240 loose mechanism","height_nm":"600","candidate_id":"H600B240MECH_009_diag_pair_J1J2_G40","ratio":"5.157216","Tx":"0.835876","matrix_error":"0.481903","phase_error_deg":"25.892659","nearest_actual_bins":"240","pass_level":"loose","decision_use":"keep_as_partial_evidence","notes":"B240 has mechanism value but not enough for six-bin LP route."},
    {"evidence_id":"A15_H600_B300_FAIL","role":"H600 B300 failure evidence","height_nm":"600","candidate_id":"H600B300HYBRID_001_x_pair_J2J1_G90","ratio":"11.589234","Tx":"0.979696","matrix_error":"0.293775","phase_error_deg":"105.037257","nearest_actual_bins":"0;60","pass_level":"fail_phase","decision_use":"stop_manual_H600_B300_rescue","notes":"Selectivity is strong but phase is locked to 0/60, not B300."},
    {"evidence_id":"A17_H650_B300_FAIL","role":"H650 B300 failure evidence","height_nm":"650","candidate_id":"H650B300ESCAPE_001_x_pair_J2J1_G90","ratio":"0.986137","Tx":"0.928105","matrix_error":"1.007004","phase_error_deg":"158.473359","nearest_actual_bins":"120;60","pass_level":"fail_ratio_matrix_phase","decision_use":"stop_LP_Hnew_sixbin_attempt","notes":"H650 escape hatch did not create true-B300 evidence or near-miss."},
]
DECISION = "Stop LP-Hnew six-bin fixed-height attempt for now. Do not run coverage or K=6 from current LP-Hnew data."
NEXT = "Return priority to CP/RCLED mainline; keep LP results as partial phase-library/mechanism evidence. Revisit LP only with a new mechanism or ML/global search, not manual local B300 rescue."


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    missing_inputs = [p for p in REQUIRED_INPUTS if not (ROOT / p).exists()]
    with EVIDENCE_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(EVIDENCE)
    summary = {
        "stage": "Stage11-4A18",
        "audit_type": "route_positioning_only_no_fdtd",
        "missing_inputs": missing_inputs,
        "decision": DECISION,
        "recommended_next_project_priority": "CP/RCLED mainline",
        "keep_lp_as": "partial phase-library/mechanism evidence",
        "do_not_enter": ["LP K=6", "coverage", "A16 G2", "H600 rerun", "H650 rerun"],
        "future_lp_condition": "new mechanism or ML/global search only",
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Stage11-4A18 LP Route-Positioning Audit",
        "",
        "This is a route-positioning audit only. No FDTD, A16 G2, coverage, H600/H650 rerun, K=6, or heavy output was run.",
        "",
        "## Core Decision",
        "",
        DECISION,
        "",
        "## Evidence Table",
        "",
        "| evidence | role | h | ratio | Tx | matrix | phase error | nearest bins | status | use |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in EVIDENCE:
        lines.append(f"| {r['evidence_id']} | {r['role']} | {r['height_nm']} | {r['ratio']} | {r['Tx']} | {r['matrix_error']} | {r['phase_error_deg']} | {r['nearest_actual_bins']} | {r['pass_level']} | {r['decision_use']} |")
    lines += [
        "",
        "## Route Options",
        "",
        "A. Pause LP-Hnew six-bin and return priority to CP/RCLED mainline.",
        "B. Keep LP results as partial phase-library/mechanism evidence for thesis or paper background.",
        "C. Revisit LP later only with a new mechanism or ML/global search, not manual local B300 rescue.",
        "D. Do not enter K=6 from current LP-Hnew data.",
        "",
        "## Recommended Next",
        "",
        NEXT,
        "",
    ]
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")
    NEXT_MD.write_text("# Stage11-4A18 Recommended Next\n\n" + NEXT + "\n\nDo not run LP coverage, A16 G2, or LP K=6 from the current evidence.\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

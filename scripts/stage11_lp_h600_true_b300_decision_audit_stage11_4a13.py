from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
EVIDENCE_CSV = REPORTS / "stage11_4a13_h600_true_b300_evidence_table.csv"
SUMMARY_JSON = REPORTS / "stage11_4a13_h600_true_b300_summary.json"
AUDIT_MD = REPORTS / "stage11_4a13_h600_true_b300_decision_audit.md"
NEXT_MD = REPORTS / "stage11_4a13_h600_true_b300_recommended_next.md"

FIELDS = ["evidence_id", "stage", "role", "candidate_id", "actual_bin_deg", "nearest_bin_deg", "ratio", "Tx", "matrix_error", "phase_error_deg", "pass_level", "decision_use", "notes"]
EVIDENCE = [
    {"evidence_id":"A8_B60_DONOR","stage":"Stage11-4A8","role":"B60 donor","candidate_id":"H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40","actual_bin_deg":"60","nearest_bin_deg":"60","ratio":"11.278722","Tx":"0.752180","matrix_error":"0.297811","phase_error_deg":"24.596581","pass_level":"strict","decision_use":"keep_as_B60_donor","notes":"High-selectivity B300-labeled family reassigned to actual B60; do not force as B300."},
    {"evidence_id":"A5_B240_LOOSE","stage":"Stage11-4A5","role":"B240 partial library evidence","candidate_id":"H600B240MECH_009_diag_pair_J1J2_G40","actual_bin_deg":"240","nearest_bin_deg":"240","ratio":"5.157216","Tx":"0.835876","matrix_error":"0.481903","phase_error_deg":"25.892659","pass_level":"loose","decision_use":"keep_as_B240_loose_evidence","notes":"B240 mechanism expansion produced loose evidence but not a robust six-bin basis."},
    {"evidence_id":"A10_G1_B300_FAIL","stage":"Stage11-4A10","role":"true B300 G1 failed","candidate_id":"A10_G1_best","actual_bin_deg":"0","nearest_bin_deg":"0","ratio":"4.458043","Tx":"","matrix_error":"0.475631","phase_error_deg":"89.940554","pass_level":"fail","decision_use":"do_not_continue_this_family","notes":"Different-anchor family did not land near true B300; nearest actual bin was 0."},
    {"evidence_id":"A11_G2_B300_FAIL","stage":"Stage11-4A11","role":"true B300 G2 failed","candidate_id":"A11_G2_best","actual_bin_deg":"300","nearest_bin_deg":"300","ratio":"1.010146","Tx":"","matrix_error":"0.994965","phase_error_deg":"26.072770","pass_level":"fail","decision_use":"do_not_continue_this_family","notes":"Phase-opposite family landed near 300 but projection/selectivity collapsed."},
    {"evidence_id":"A12_G3_B300_FAIL","stage":"Stage11-4A12","role":"true B300 G3 failed","candidate_id":"H600TRUEB300G3_002_diag_pair_J1J2_G100","actual_bin_deg":"0","nearest_bin_deg":"0","ratio":"2.357350","Tx":"0.947046","matrix_error":"0.651573","phase_error_deg":"88.009657","pass_level":"fail","decision_use":"stop_H600_true_B300_blind_search","notes":"Mini escape preserved Tx but failed ratio, matrix, and phase gates."},
]
DECISION = "Stop H600 true-B300 blind search for now; do not run H600 coverage yet."
RECOMMENDED_ROUTE = "Stage11-4A13 recommends route A first: H600 B300 mechanism redesign planning only. Route B H650 B300 escape hatch is next if A cannot produce a bounded, physically distinct search plan."


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    write_csv(EVIDENCE_CSV, EVIDENCE)
    summary = {"stage":"Stage11-4A13","audit_type":"decision_only_no_fdtd","decision":DECISION,"keep_partial_evidence":["A8 B60 donor","A5 B240 loose"],"true_b300_failed_groups":["A10 G1","A11 G2","A12 G3"],"recommended_next_route":RECOMMENDED_ROUTE,"do_not_run":["FDTD","coverage","H650","K=6","finite patch","dipole","DBR","RCLED"]}
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = ["# Stage11-4A13 H600 True-B300 Decision Audit", "", "This is a decision audit only. No FDTD, coverage, H650, K=6, finite patch, dipole, DBR, RCLED, or H500 rescue was run.", "", "## Decision", "", DECISION, "", "Keep the A8 B60 donor and A5 B240 loose case as useful partial LP-H600 library evidence. Do not run H600 coverage because true B300 remains unresolved.", "", "## Evidence Summary", "", "| evidence | role | candidate | ratio | Tx | matrix | phase error | status | use |", "|---|---|---|---:|---:|---:|---:|---|---|"]
    for r in EVIDENCE:
        lines.append(f"| {r['evidence_id']} | {r['role']} | {r['candidate_id']} | {r['ratio']} | {r['Tx'] or 'n/a'} | {r['matrix_error']} | {r['phase_error_deg']} | {r['pass_level']} | {r['decision_use']} |")
    lines += ["", "## Route Recommendation", "", RECOMMENDED_ROUTE, "", "Alternatives kept open: route B H650 B300 escape hatch, route C partial phase-library/mechanism positioning, or route D return to CP/RCLED mainline if paper timeline dominates.", "", "## Boundary", "", "No K=6 work is justified until a fixed-height LP library has a credible true-B300 route.", ""]
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")
    NEXT_MD.write_text("# Stage11-4A13 Recommended Next\n\n" + RECOMMENDED_ROUTE + "\n\nDo not run coverage 0/60/120/180, H650, or K=6 before deciding whether B300 mechanism redesign is worth one more bounded planning pass.\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

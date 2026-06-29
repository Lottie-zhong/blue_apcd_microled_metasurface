from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"
A1_RESULTS = REPORT_DIR / "stage11_4a1_lp_hnew_results.csv"
A1_RANKING = REPORT_DIR / "stage11_4a1_lp_hnew_candidate_ranking.csv"
A1_BOTTLENECK = REPORT_DIR / "stage11_4a1_lp_hnew_bottleneck_summary.md"
A2_PLAN = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_plan.md"
A2_SPACE = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_candidate_space.csv"
A2_MANIFEST = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_manifest.json"
A3_RESULTS = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_results.csv"
A3_RANKING = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_ranking.csv"
A3_REPORT = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_report.md"
A3_NEXT = REPORT_DIR / "stage11_4a3_h600_b240_role_recombination_recommended_next.md"

PLAN_MD = REPORT_DIR / "stage11_4a4_b240_search_space_redesign_plan.md"
SPACE_CSV = REPORT_DIR / "stage11_4a4_b240_search_space_redesign_candidate_space.csv"
MANIFEST_JSON = REPORT_DIR / "stage11_4a4_b240_search_space_redesign_manifest.json"
SUMMARY_JSON = REPORT_DIR / "stage11_4a4_b240_search_space_redesign_summary.json"

WAVELENGTHS = [451, 452, 453]
PASS_THRESHOLDS = {
    "strict": {"ratio_min": 6.0, "Tx_min": 0.45, "matrix_error_max": 0.50, "phase_error_max_deg": 25.0},
    "loose": {"ratio_min": 3.0, "Tx_min": 0.10, "matrix_error_max": 1.00, "phase_error_max_deg": 35.0},
    "near_miss": {"ratio_min": 2.0, "Tx_min": 0.10, "matrix_error_max": 1.50, "phase_error_max_deg": 45.0},
}
FIELDS = [
    "group_id", "height_nm", "target_bin_deg", "wavelengths_nm", "planned_cases", "priority",
    "candidate_family", "mechanism_change_from_a3", "geometry_knobs", "purpose", "trigger",
    "early_stop_rule", "decision_after_group",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def flt(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, "") or default)
    except ValueError:
        return default


def required_inputs() -> list[Path]:
    return [A1_RESULTS, A1_RANKING, A1_BOTTLENECK, A2_PLAN, A2_SPACE, A2_MANIFEST, A3_RESULTS, A3_RANKING, A3_REPORT, A3_NEXT]


def diagnose_a3() -> dict[str, object]:
    for path in required_inputs():
        if not path.exists():
            raise FileNotFoundError(path)
    rows = read_csv(A3_RESULTS)
    ranking = read_csv(A3_RANKING)
    ok = [r for r in rows if r.get("status") == "ok"]
    tx_good = [r for r in ok if flt(r, "target_Tx") >= 0.45]
    ratio_fail = [r for r in ok if flt(r, "conversion_to_leakage_ratio") < 3.0]
    matrix_fail = [r for r in ok if flt(r, "matrix_error") > 0.50]
    phase_fail = [r for r in ok if flt(r, "phase_error_deg") > 25.0]
    best = ranking[0] if ranking else {}
    wls = sorted({int(float(r["wavelength_nm"])) for r in ok})
    return {
        "ok_rows": len(ok),
        "tx_good_rows": len(tx_good),
        "tx_good_but_selectivity_bad_rows": len([r for r in tx_good if flt(r, "conversion_to_leakage_ratio") < 3.0]),
        "ratio_failure_rows": len(ratio_fail),
        "matrix_failure_rows": len(matrix_fail),
        "phase_failure_rows": len(phase_fail),
        "wavelengths_present_nm": wls,
        "complete_451_452_453": wls == WAVELENGTHS,
        "strict_candidates": len([r for r in ranking if r.get("best_pass_level") == "strict"]),
        "loose_candidates": len([r for r in ranking if r.get("best_pass_level") == "loose"]),
        "near_miss_candidates": len([r for r in ranking if r.get("near_miss") == "true"]),
        "best_candidate": best,
        "a1_baseline": {"worst_ratio": 1.003135, "phase_error_deg": 40.346637, "failure": "ratio/matrix/phase"},
    }


def plan_rows() -> list[dict[str, str]]:
    wl = ";".join(str(w) for w in WAVELENGTHS)
    return [
        {
            "group_id": "S11_4A4_H600_B240_MECHANISM_EXPANSION",
            "height_nm": "600", "target_bin_deg": "240", "wavelengths_nm": wl, "planned_cases": "36",
            "priority": "primary", "candidate_family": "expanded_gap_orientation_family",
            "mechanism_change_from_a3": "leaves the local B240 x_pair swap G80-100 O-nearby family; adds larger separations and orientation families",
            "geometry_knobs": "gap/center separation 120-220 nm; y_pair and diag_pair; swap and noswap; J1/J2 order; wider clearance",
            "purpose": "recover LP projection selectivity before phase tuning",
            "trigger": "always first",
            "early_stop_rule": "stop only after 36 cases or after a strict/loose candidate is confirmed across 451/452/453",
            "decision_after_group": "if loose or near-miss appears, focus B240 refinement; otherwise run group 2",
        },
        {
            "group_id": "S11_4A4_H600_B240_ADJACENT_ANCHOR_RESCUE",
            "height_nm": "600", "target_bin_deg": "240", "wavelengths_nm": wl, "planned_cases": "18",
            "priority": "secondary", "candidate_family": "adjacent_bin_phase_anchor_with_selectivity_filter",
            "mechanism_change_from_a3": "uses adjacent-bin phase anchors only when selectivity is better, not B240 label inheritance",
            "geometry_knobs": "source anchors near 180/300; require ratio-filtered donors; phase pull by gap/orientation/order",
            "purpose": "find a 240 common-phase candidate by relabeling a more selective projection family",
            "trigger": "run after group 1 if B240 is still below near-miss",
            "early_stop_rule": "stop after any complete near-miss or loose candidate; reject phase-only hits with ratio below 2",
            "decision_after_group": "if near-miss appears, focused B240 refinement; if not, run escape hatch",
        },
        {
            "group_id": "S11_4A4_H650_B240_ESCAPE_HATCH",
            "height_nm": "650", "target_bin_deg": "240", "wavelengths_nm": wl, "planned_cases": "18",
            "priority": "conditional", "candidate_family": "small_H650_mechanism_probe",
            "mechanism_change_from_a3": "changes fixed height after H600 mechanism families fail; still B240-only",
            "geometry_knobs": "limited H650 versions of the best H600 mechanism families; no full six-bin or H700 sweep",
            "purpose": "determine whether H600 is the blocker rather than the LP dimer concept",
            "trigger": "run only if H600 groups 1 and 2 have no near-miss",
            "early_stop_rule": "stop after 18 cases or earlier only on system error; do not expand H650 without evidence",
            "decision_after_group": "if no near-miss, stop LP-Hnew B240 path and reconsider LP paper positioning",
        },
    ]


def total_cases(rows: list[dict[str, str]]) -> int:
    return sum(int(r["planned_cases"]) for r in rows)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_manifest(rows: list[dict[str, str]], diagnosis: dict[str, object]) -> dict[str, object]:
    return {
        "stage": "Stage11-4A4",
        "task": "H600 B240 search-space redesign planning",
        "planning_only": True,
        "no_fdtd_run": True,
        "no_lumerical_run": True,
        "no_b300_phase_pull": True,
        "no_k6_metagrating": True,
        "no_h500_rescue": True,
        "wavelengths_nm": WAVELENGTHS,
        "target_bin_deg": 240,
        "hard_future_case_budget": 72,
        "planned_future_cases": total_cases(rows),
        "thresholds": PASS_THRESHOLDS,
        "a3_failure_diagnosis": diagnosis,
        "b300_blocked_reason": "A3 produced no B240 loose candidate and no near-miss; B300 phase pull would not repair the missing 240 projection-phase anchor.",
        "decision_tree": {
            "no_near_miss": "stop LP-Hnew B240 path and reconsider LP paper positioning",
            "near_miss": "run focused B240 refinement",
            "loose_or_strict": "resume B300 phase pull",
        },
        "run_groups": rows,
    }


def write_md(rows: list[dict[str, str]], manifest: dict[str, object]) -> None:
    d = manifest["a3_failure_diagnosis"]
    best = d.get("best_candidate", {})
    lines = [
        "# Stage11-4A4 B240 Search-Space Redesign Plan",
        "",
        "Planning only: no FDTD, no Lumerical, no B300, no coverage bins, no H650 full sweep, no K=6, no H500 rescue.",
        "",
        "## A3 Failure Diagnosis",
        "",
        f"- ok_rows: {d['ok_rows']}",
        f"- Tx-good rows: {d['tx_good_rows']}",
        f"- Tx-good but selectivity-bad rows: {d['tx_good_but_selectivity_bad_rows']}",
        f"- ratio failure rows: {d['ratio_failure_rows']}",
        f"- matrix failure rows: {d['matrix_failure_rows']}",
        f"- phase failure rows: {d['phase_failure_rows']}",
        f"- complete wavelengths: {d['complete_451_452_453']}",
        f"- strict/loose/near-miss: {d['strict_candidates']}/{d['loose_candidates']}/{d['near_miss_candidates']}",
        "",
        "Best A3 candidate:",
        "",
        "```json",
        json.dumps(best, indent=2),
        "```",
        "",
        "A3 mainly proved that height-scaled B240 templates keep Tx high but do not restore LP projection selectivity or phase. The next plan changes the mechanism rather than continuing local B240 recombination.",
        "",
        "## Why B300 Remains Blocked",
        "",
        "B300 phase pull is blocked because B240 has no loose candidate and no near-miss. Without a viable 240 projection-phase anchor, B300 improvement cannot produce a six-bin library.",
        "",
        "## Future A4 Groups",
        "",
        "| group | height | cases | purpose |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['group_id']} | {row['height_nm']} | {row['planned_cases']} | {row['purpose']} |")
    lines += [
        "",
        f"Total future cases: {manifest['planned_future_cases']} / {manifest['hard_future_case_budget']}.",
        "",
        "## Decision Tree",
        "",
        "- no near-miss: stop LP-Hnew B240 path and reconsider LP paper positioning",
        "- near-miss: run focused B240 refinement",
        "- loose/strict: resume B300 phase pull",
        "",
        "## Thresholds",
        "",
        "- strict: ratio >= 6, Tx >= 0.45, matrix_error <= 0.50, phase_error <= 25 deg",
        "- loose: ratio >= 3, Tx >= 0.10, matrix_error <= 1.00, phase_error <= 35 deg",
        "- near-miss: ratio >= 2, Tx >= 0.10, matrix_error <= 1.50, phase_error <= 45 deg",
        "",
    ]
    PLAN_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    diagnosis = diagnose_a3()
    rows = plan_rows()
    if total_cases(rows) > 72:
        raise RuntimeError("A4 future plan exceeds 72 cases")
    write_csv(SPACE_CSV, rows)
    manifest = build_manifest(rows, diagnosis)
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps({
        "stage": "Stage11-4A4",
        "planning_only": True,
        "planned_groups": len(rows),
        "planned_future_cases": total_cases(rows),
        "b300_blocked": True,
        "recommended_first_group": rows[0]["group_id"],
        "a3_best_candidate": diagnosis["best_candidate"],
        "a3_tx_good_but_selectivity_bad_rows": diagnosis["tx_good_but_selectivity_bad_rows"],
        "a3_near_miss_candidates": diagnosis["near_miss_candidates"],
    }, indent=2), encoding="utf-8")
    write_md(rows, manifest)
    print(f"planned_future_cases={total_cases(rows)}")


if __name__ == "__main__":
    main()

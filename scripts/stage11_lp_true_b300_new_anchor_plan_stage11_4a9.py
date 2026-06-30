from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"
A8_AUDIT = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_audit.csv"
A8_SUMMARY = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_summary.json"
A8_REPORT = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_report.md"
A8_NEXT = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_recommended_next.md"
A5_RANKING = REPORT_DIR / "stage11_4a5_h600_b240_mechanism_expansion_ranking.csv"
A6_RESULTS = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_results.csv"
A7_SPACE = REPORT_DIR / "stage11_4a7_b300_phase_anchor_candidate_space.csv"
SPACE_CSV = REPORT_DIR / "stage11_4a9_true_b300_new_anchor_candidate_space.csv"
MANIFEST_JSON = REPORT_DIR / "stage11_4a9_true_b300_new_anchor_manifest.json"
PLAN_MD = REPORT_DIR / "stage11_4a9_true_b300_new_anchor_plan.md"
SUMMARY_JSON = REPORT_DIR / "stage11_4a9_true_b300_new_anchor_summary.json"
WAVELENGTHS = [451, 452, 453]
TARGET_BIN = 300
MAX_CASES = 36
FIELDS = ["group_id", "height_nm", "target_actual_bin_deg", "wavelengths_nm", "planned_geometries", "planned_cases", "anchor_family", "seed_policy", "excluded_family", "purpose", "priority"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_inputs() -> tuple[list[dict[str, str]], dict]:
    for path in [A8_AUDIT, A8_SUMMARY, A8_REPORT, A8_NEXT, A5_RANKING, A6_RESULTS, A7_SPACE]:
        if not path.exists():
            raise FileNotFoundError(path)
    return read_csv(A8_AUDIT), json.loads(A8_SUMMARY.read_text(encoding="utf-8"))


def excluded_b60_family(audit_rows: list[dict[str, str]]) -> dict[str, object]:
    promoted = [r for r in audit_rows if r["reassignment_recommendation"] == "candidate_for_B60"]
    ids = sorted({r["candidate_id"] for r in promoted})
    source_ids = sorted({cid.split("_FROM_", 1)[-1] for cid in ids})
    families = sorted({"_".join(src.split("_")[2:]) if src.startswith("H500DIMER") else src for src in source_ids})
    return {"candidate_ids": ids, "source_candidate_ids": source_ids, "families": families}


def plan_groups(excluded_family: str) -> list[dict[str, object]]:
    return [
        {
            "group_id": "S11_4A9_G1_TRUE_B300_DIFFERENT_ANCHOR_FAMILY",
            "height_nm": 600,
            "target_actual_bin_deg": TARGET_BIN,
            "wavelengths_nm": "451;452;453",
            "planned_geometries": 6,
            "planned_cases": 18,
            "anchor_family": "non_x_pair_swap_G80_O40; prefer y_pair/diag_pair or different B240/B0 donors with actual phase closer to 300",
            "seed_policy": "exclude A8 B60-promoted family except as negative reference",
            "excluded_family": excluded_family,
            "purpose": "find a true B300 phase anchor without rediscovering B60",
            "priority": "highest",
        },
        {
            "group_id": "S11_4A9_G2_TRUE_B300_PHASE_OPPOSITE_FAMILY",
            "height_nm": 600,
            "target_actual_bin_deg": TARGET_BIN,
            "wavelengths_nm": "451;452;453",
            "planned_geometries": 4,
            "planned_cases": 12,
            "anchor_family": "phase-opposite candidates whose 450 nm selected phase is near 240/300, not 0/60",
            "seed_policy": "prefer sources not promoted by A8; reject if nearest actual bin is 0 or 60 at first wavelength",
            "excluded_family": excluded_family,
            "purpose": "test whether a different resonance branch can land near actual B300",
            "priority": "secondary",
        },
        {
            "group_id": "S11_4A9_G3_TRUE_B300_MINI_ESCAPE",
            "height_nm": 600,
            "target_actual_bin_deg": TARGET_BIN,
            "wavelengths_nm": "451;452;453",
            "planned_geometries": 2,
            "planned_cases": 6,
            "anchor_family": "minimal escape: one y_pair and one diag_pair control from non-promoted sources",
            "seed_policy": "negative-reference A8 family only in analysis, not as refinement target",
            "excluded_family": excluded_family,
            "purpose": "cheap sanity check before broader H600 redesign or stopping LP-Hnew path",
            "priority": "fallback",
        },
    ]


def write_outputs() -> dict[str, object]:
    audit_rows, a8_summary = load_inputs()
    excluded = excluded_b60_family(audit_rows)
    excluded_family = ";".join(excluded["families"]) or "A8_B60_promoted_family"
    groups = plan_groups(excluded_family)
    total = sum(int(g["planned_cases"]) for g in groups)
    if total > MAX_CASES:
        raise RuntimeError(f"A9 exceeds case cap: {total}")
    write_csv(SPACE_CSV, groups, FIELDS)
    manifest = {
        "stage": "Stage11-4A9",
        "planning_only": True,
        "no_fdtd_lumerical": True,
        "height_nm": 600,
        "target_actual_bin_deg": TARGET_BIN,
        "wavelengths_nm": WAVELENGTHS,
        "max_future_cases": MAX_CASES,
        "future_total_cases": total,
        "excluded_b60_donor_family": excluded,
        "run_groups": groups,
        "excluded_scope": ["B60 donor refinement", "coverage 0/60/120/180", "H650", "K=6", "finite patch", "dipole", "DBR/RCLED"],
        "decision_after_future_run": [
            "if B300 loose/strict -> run coverage 0/120/180 next, keeping B60 donor and B240 loose evidence",
            "if B300 high-selectivity but lands in another bin -> reassign again",
            "if no selectivity -> redesign or stop H600 LP-Hnew six-bin path",
        ],
    }
    summary = {
        **manifest,
        "a8_best_reassigned_candidate": a8_summary.get("best_reassigned_candidate"),
        "b300_still_unsolved": True,
        "recommended_next_run_group": groups[0]["group_id"],
        "avoid_rediscovering_b60_rule": "exclude A8-promoted B60 donor family from true-B300 refinement; use it only as negative reference",
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    PLAN_MD.write_text("\n".join([
        "# Stage11-4A9 True B300 New-Anchor Plan",
        "",
        "Planning only. No FDTD/Lumerical was run.",
        "",
        "## Why A9 Exists",
        "",
        "A8 showed the best A6 B300-labeled high-selectivity family is actually a stable B60 donor. It should be kept as B60 evidence, not forced as B300.",
        "",
        "## Excluded B60 Donor Family",
        "",
        json.dumps(excluded, indent=2),
        "",
        "## Future Groups",
        "",
        *[f"- {g['group_id']}: {g['planned_cases']} cases, {g['purpose']}" for g in groups],
        "",
        f"Total future cases: {total} / {MAX_CASES}.",
        "",
        "## Recommended Next Run Group",
        "",
        groups[0]["group_id"],
        "",
        "Do not include B60 donor refinement, coverage, H650, K=6, finite patch, dipole, or DBR/RCLED.",
        "",
    ]), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(write_outputs(), indent=2))

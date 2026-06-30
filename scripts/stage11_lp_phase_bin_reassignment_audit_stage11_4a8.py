from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"
A6_RESULTS = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_results.csv"
A6_RANKING = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_ranking.csv"
A7_SUMMARY = REPORT_DIR / "stage11_4a7_b300_phase_anchor_summary.json"
A7_PLAN = REPORT_DIR / "stage11_4a7_b300_phase_anchor_diagnostic_plan.md"
A5_RANKING = REPORT_DIR / "stage11_4a5_h600_b240_mechanism_expansion_ranking.csv"
AUDIT_CSV = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_audit.csv"
SUMMARY_JSON = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_summary.json"
REPORT_MD = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_report.md"
NEXT_MD = REPORT_DIR / "stage11_4a8_phase_bin_reassignment_recommended_next.md"
BINS = [0, 60, 120, 180, 240, 300]
ORIGINAL_TARGET = 300
FIELDS = [
    "candidate_id", "original_target_bin_deg", "wavelength_nm", "selected_phase_deg",
    "nearest_actual_bin_deg", "phase_error_to_actual_bin_deg", "target_Tx", "y_leakage",
    "conversion_to_leakage_ratio", "matrix_error", "pass_level_as_original",
    "pass_level_as_reassigned", "reassignment_recommendation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def circ_diff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def nearest_bin(phase: float) -> int:
    return min(BINS, key=lambda b: abs(circ_diff(phase, b)))


def pass_level(ratio: float, tx: float, matrix: float, phase_error: float) -> str:
    if ratio >= 6 and tx >= 0.45 and matrix <= 0.50 and phase_error <= 25:
        return "strict"
    if ratio >= 3 and tx >= 0.10 and matrix <= 1.00 and phase_error <= 35:
        return "loose"
    if ratio >= 6 and tx >= 0.45 and matrix <= 0.50 and phase_error <= 45:
        return "near_miss"
    return "fail"


def row_audit(row: dict[str, str]) -> dict[str, object]:
    phase = flt(row["selected_phase_deg"]) % 360.0
    actual = nearest_bin(phase)
    actual_err = abs(circ_diff(phase, actual))
    original_err = abs(circ_diff(phase, ORIGINAL_TARGET))
    tx = flt(row["target_Tx"], 0.0)
    ratio = flt(row["conversion_to_leakage_ratio"], 0.0)
    matrix = flt(row["matrix_error"], 999.0)
    original_level = pass_level(ratio, tx, matrix, original_err)
    reassigned_level = pass_level(ratio, tx, matrix, actual_err)
    if actual == ORIGINAL_TARGET:
        rec = "already_b300"
    elif reassigned_level in {"strict", "loose", "near_miss"}:
        rec = f"candidate_for_B{actual}"
    else:
        rec = "do_not_promote"
    return {
        "candidate_id": row["candidate_id"],
        "original_target_bin_deg": ORIGINAL_TARGET,
        "wavelength_nm": row["wavelength_nm"],
        "selected_phase_deg": f"{phase:.6f}",
        "nearest_actual_bin_deg": actual,
        "phase_error_to_actual_bin_deg": f"{actual_err:.6f}",
        "target_Tx": row["target_Tx"],
        "y_leakage": row["y_leakage"],
        "conversion_to_leakage_ratio": row["conversion_to_leakage_ratio"],
        "matrix_error": row["matrix_error"],
        "pass_level_as_original": original_level,
        "pass_level_as_reassigned": reassigned_level,
        "reassignment_recommendation": rec,
    }


def stable_reassignment(rows: list[dict[str, object]]) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["candidate_id"])].append(row)
    promoted = []
    unstable = []
    for cid, members in groups.items():
        bins = {int(m["nearest_actual_bin_deg"]) for m in members}
        levels = {str(m["pass_level_as_reassigned"]) for m in members}
        worst_ratio = min(flt(m["conversion_to_leakage_ratio"], 0.0) for m in members)
        worst_tx = min(flt(m["target_Tx"], 0.0) for m in members)
        worst_matrix = max(flt(m["matrix_error"], 999.0) for m in members)
        max_phase_err = max(flt(m["phase_error_to_actual_bin_deg"], 999.0) for m in members)
        record = {
            "candidate_id": cid,
            "bins": sorted(bins),
            "worst_ratio": worst_ratio,
            "worst_Tx": worst_tx,
            "worst_matrix_error": worst_matrix,
            "max_phase_error_to_actual_bin_deg": max_phase_err,
            "levels": sorted(levels),
        }
        if len(bins) == 1 and (levels <= {"strict"} or levels <= {"strict", "loose"} or levels <= {"strict", "loose", "near_miss"}):
            record["promoted_bin"] = next(iter(bins))
            promoted.append(record)
        else:
            unstable.append(record)
    promoted.sort(key=lambda r: (r["promoted_bin"], -r["worst_ratio"], r["max_phase_error_to_actual_bin_deg"]))
    unstable.sort(key=lambda r: (-r["worst_ratio"], r["max_phase_error_to_actual_bin_deg"]))
    return {"promoted": promoted, "unstable": unstable}


def write_outputs() -> dict[str, object]:
    for path in [A6_RESULTS, A6_RANKING, A7_SUMMARY, A7_PLAN, A5_RANKING]:
        if not path.exists():
            raise FileNotFoundError(path)
    raw = [r for r in read_csv(A6_RESULTS) if r.get("status") == "ok"]
    audits = [row_audit(r) for r in raw]
    write_csv(AUDIT_CSV, audits, FIELDS)
    reassignment = stable_reassignment(audits)
    promoted = reassignment["promoted"]
    best = promoted[0] if promoted else None
    promoted_bins = sorted({int(p["promoted_bin"]) for p in promoted})
    remaining_missing = [b for b in BINS if b not in promoted_bins and b not in [240]]
    # B240 has loose evidence from A5, but B300 remains unsolved by reassignment.
    remaining_weak = sorted(set(remaining_missing + [300]))
    recommendation = "Use the A6 high-selectivity family as B0/B60 donor evidence only if stable; do not force it as B300. Future B300 should use a different anchor family."
    summary = {
        "stage": "Stage11-4A8",
        "planning_only": True,
        "no_fdtd_lumerical": True,
        "rows_audited": len(audits),
        "promoted_candidate_count": len(promoted),
        "unstable_candidate_count": len(reassignment["unstable"]),
        "promoted_bins": promoted_bins,
        "best_reassigned_candidate": best,
        "remaining_missing_or_weak_bins": remaining_weak,
        "b300_solved": False,
        "recommendation": recommendation,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    REPORT_MD.write_text("\n".join([
        "# Stage11-4A8 Phase-Bin Reassignment Audit",
        "",
        "Planning/audit only. No FDTD/Lumerical was run.",
        "",
        "## Result",
        "",
        f"Rows audited: {len(audits)}.",
        f"Stable promoted candidates: {len(promoted)}.",
        f"Promoted bins: {promoted_bins}.",
        "B300 is not solved unless selected phase is near 300; no A6 high-selectivity donor solved B300.",
        "",
        "## Best Reassigned Candidate",
        "",
        "```json", json.dumps(best, indent=2), "```",
        "",
        "## Remaining Missing/Weak Bins",
        "",
        ";".join(map(str, remaining_weak)),
        "",
        "## Recommended Next",
        "",
        recommendation,
        "",
    ]), encoding="utf-8")
    NEXT_MD.write_text("# Stage11-4A8 Recommended Next\n\n" + recommendation + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(write_outputs(), indent=2))

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"
A1_RESULTS = REPORT_DIR / "stage11_4a1_lp_hnew_results.csv"
A1_RANKING = REPORT_DIR / "stage11_4a1_lp_hnew_candidate_ranking.csv"
A5_RANKING = REPORT_DIR / "stage11_4a5_h600_b240_mechanism_expansion_ranking.csv"
A5_REPORT = REPORT_DIR / "stage11_4a5_h600_b240_mechanism_expansion_report.md"
A6_RESULTS = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_results.csv"
A6_RANKING = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_ranking.csv"
A6_REPORT = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_report.md"
A6_NEXT = REPORT_DIR / "stage11_4a6_h600_b300_phase_pull_recommended_next.md"
PLAN_MD = REPORT_DIR / "stage11_4a7_b300_phase_anchor_diagnostic_plan.md"
CANDIDATE_CSV = REPORT_DIR / "stage11_4a7_b300_phase_anchor_candidate_space.csv"
MANIFEST_JSON = REPORT_DIR / "stage11_4a7_b300_phase_anchor_manifest.json"
SUMMARY_JSON = REPORT_DIR / "stage11_4a7_b300_phase_anchor_summary.json"
BINS = [0, 60, 120, 180, 240, 300]
WAVELENGTHS = [451, 452, 453]
TARGET_BIN = 300
MAX_FUTURE_CASES = 36


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


def infer_family(candidate_id: str) -> str:
    tail = candidate_id.split("_FROM_", 1)[-1]
    bits = []
    for key in ("x_pair", "y_pair", "diag_pair", "swap", "noswap"):
        if key in tail:
            bits.append(key)
    for part in tail.split("_"):
        if part.startswith("G") or part.startswith("O-") or part.startswith("O"):
            bits.append(part)
    return "_".join(bits) if bits else tail


def candidate_stats(results: list[dict[str, str]], ranking: list[dict[str, str]]) -> list[dict[str, object]]:
    ranking_by_id = {r["candidate_id"]: r for r in ranking}
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in results:
        groups[row["candidate_id"]].append(row)
    out = []
    for cid, rows in groups.items():
        phases = [flt(r["selected_phase_deg"]) % 360.0 for r in rows if r.get("status") == "ok"]
        ratios = [flt(r["conversion_to_leakage_ratio"], 0.0) for r in rows if r.get("status") == "ok"]
        txs = [flt(r["target_Tx"], 0.0) for r in rows if r.get("status") == "ok"]
        matrices = [flt(r["matrix_error"], 999.0) for r in rows if r.get("status") == "ok"]
        phase_errors = [abs(circ_diff(p, TARGET_BIN)) for p in phases]
        nearest = [nearest_bin(p) for p in phases]
        by_wl = ";".join(f"{r['wavelength_nm']}:{flt(r['selected_phase_deg']) % 360.0:.3f}->{nearest_bin(flt(r['selected_phase_deg']))}" for r in rows if r.get("status") == "ok")
        rrank = ranking_by_id.get(cid, {})
        out.append({
            "candidate_id": cid,
            "source_candidate_id": rrank.get("source_candidate_id", cid.split("_FROM_", 1)[-1]),
            "geometry_family": infer_family(cid),
            "min_phase_deg": min(phases) if phases else math.nan,
            "max_phase_deg": max(phases) if phases else math.nan,
            "phase_span_deg": max(phases) - min(phases) if phases else math.nan,
            "nearest_bins": ";".join(map(str, sorted(set(nearest)))) if nearest else "",
            "phase_by_wavelength": by_wl,
            "worst_ratio": min(ratios) if ratios else 0.0,
            "worst_Tx": min(txs) if txs else 0.0,
            "worst_matrix_error": max(matrices) if matrices else 999.0,
            "max_phase_error_to_300_deg": max(phase_errors) if phase_errors else 999.0,
            "best_pass_level": rrank.get("best_pass_level", "fail"),
            "near_miss": rrank.get("near_miss", "false"),
            "failure_mode": "phase_only" if min(ratios or [0]) >= 6 and max(matrices or [999]) <= 0.5 else "mixed",
        })
    out.sort(key=lambda r: (-float(r["worst_ratio"]), float(r["worst_matrix_error"]), float(r["max_phase_error_to_300_deg"])))
    return out


def high_selectivity_cluster(stats: list[dict[str, object]]) -> dict[str, object]:
    high = [s for s in stats if float(s["worst_ratio"]) >= 6 and float(s["worst_matrix_error"]) <= 0.5]
    bins: dict[str, int] = defaultdict(int)
    for s in high:
        for b in str(s["nearest_bins"]).split(";"):
            if b:
                bins[b] += 1
    return {
        "high_selectivity_candidate_count": len(high),
        "nearest_bin_histogram": dict(sorted(bins.items())),
        "cluster_statement": "High-selectivity B300 candidates cluster away from 300 deg; phase anchor is wrong." if high and ("300" not in bins or bins.get("300", 0) < len(high)) else "No strong wrong-bin cluster detected.",
    }


def planned_groups(stats: list[dict[str, object]]) -> list[dict[str, object]]:
    best = stats[0]
    donor = best["source_candidate_id"]
    return [
        {
            "group_id": "S11_4A7_G1_B300_PHASE_ANCHOR_SHIFT",
            "height_nm": 600,
            "target_bin_deg": 300,
            "wavelengths_nm": "451;452;453",
            "planned_geometries": 6,
            "planned_cases": 18,
            "seed_candidate": donor,
            "geometry_knobs": "same high-selectivity x_pair family; gap/offset phase-anchor shift; keep projection matrix intact",
            "purpose": "pull selected-channel phase toward 300 without sacrificing ratio/matrix",
            "priority": "highest",
        },
        {
            "group_id": "S11_4A7_G2_B300_ADJACENT_BIN_ANCHOR_RESCUE",
            "height_nm": 600,
            "target_bin_deg": 300,
            "wavelengths_nm": "451;452;453",
            "planned_geometries": 4,
            "planned_cases": 12,
            "seed_candidate": "nearby 240/0 actual-phase donors from tracked B300/B240 families",
            "geometry_knobs": "adjacent-bin donor relabel check; swap/no-swap; small gap changes",
            "purpose": "find a better phase anchor if direct B300 pull remains offset",
            "priority": "secondary",
        },
        {
            "group_id": "S11_4A7_G3_B300_ORIENTATION_GAP_FALLBACK",
            "height_nm": 600,
            "target_bin_deg": 300,
            "wavelengths_nm": "451;452;453",
            "planned_geometries": 2,
            "planned_cases": 6,
            "seed_candidate": donor,
            "geometry_knobs": "diag_pair fallback; one wider gap and one swapped control",
            "purpose": "minimal check that orientation/gap can move phase without killing selectivity",
            "priority": "fallback",
        },
    ]


def write_outputs() -> dict[str, object]:
    for path in [A1_RESULTS, A1_RANKING, A5_RANKING, A5_REPORT, A6_RESULTS, A6_RANKING, A6_REPORT, A6_NEXT]:
        if not path.exists():
            raise FileNotFoundError(path)
    stats = candidate_stats(read_csv(A6_RESULTS), read_csv(A6_RANKING))
    cluster = high_selectivity_cluster(stats)
    groups = planned_groups(stats)
    total = sum(int(g["planned_cases"]) for g in groups)
    if total > MAX_FUTURE_CASES:
        raise RuntimeError(f"A7 plan exceeds {MAX_FUTURE_CASES}: {total}")
    candidate_fields = [
        "candidate_id", "source_candidate_id", "geometry_family", "min_phase_deg", "max_phase_deg",
        "phase_span_deg", "nearest_bins", "phase_by_wavelength", "worst_ratio", "worst_Tx",
        "worst_matrix_error", "max_phase_error_to_300_deg", "best_pass_level", "near_miss", "failure_mode",
    ]
    write_csv(CANDIDATE_CSV, stats, candidate_fields)
    summary = {
        "stage": "Stage11-4A7",
        "planning_only": True,
        "no_fdtd_lumerical": True,
        "target": "H600 B300 phase-anchor diagnostic/refinement",
        "a6_completed_cases": len(read_csv(A6_RESULTS)),
        "b300_strict_loose_after_a6": False,
        "b300_near_miss_count_after_a6": sum(1 for s in stats if s["near_miss"] == "true"),
        "best_a6_candidate": stats[0],
        "phase_cluster": cluster,
        "future_groups": groups,
        "future_total_cases": total,
        "coverage_blocked_reason": "B300 has good selectivity but wrong selected-channel phase anchor; coverage 0/60/120/180 should wait until B300 reaches loose/strict or systematic phase-offset correction is proven.",
        "decision_tree": [
            "if B300 becomes loose/strict and B240 loose exists -> run H600 coverage 0/60/120/180 next",
            "if B300 remains phase-only fail but phase offset becomes systematic -> run one focused phase-offset correction",
            "if B300 loses selectivity -> redesign B300 search space",
            "if no improvement -> reconsider LP-Hnew six-bin feasibility",
        ],
        "excluded": ["B240 rerun", "H650", "coverage", "K=6", "finite patch", "dipole", "DBR/RCLED", "H500 rescue"],
    }
    MANIFEST_JSON.write_text(json.dumps({"stage": "Stage11-4A7", "max_future_cases": MAX_FUTURE_CASES, "wavelengths_nm": WAVELENGTHS, "run_groups": groups, "excluded": summary["excluded"]}, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    PLAN_MD.write_text("\n".join([
        "# Stage11-4A7 B300 Phase-Anchor Diagnostic Plan",
        "",
        "Planning only. No FDTD/Lumerical was run. Scope is H600 B300 only.",
        "",
        "## Diagnosis",
        "",
        f"A6 produced {summary['a6_completed_cases']} completed B300 rows, with 0 strict, 0 loose, and {summary['b300_near_miss_count_after_a6']} near-miss candidates.",
        f"Best A6 candidate: `{stats[0]['candidate_id']}`.",
        f"Worst ratio: {float(stats[0]['worst_ratio']):.6f}; worst Tx: {float(stats[0]['worst_Tx']):.6f}; worst matrix error: {float(stats[0]['worst_matrix_error']):.6f}; max phase error: {float(stats[0]['max_phase_error_to_300_deg']):.6f} deg.",
        cluster["cluster_statement"],
        "",
        "## Why Coverage Remains Blocked",
        "",
        summary["coverage_blocked_reason"],
        "",
        "## Future A7 Groups",
        "",
        *[f"- {g['group_id']}: {g['planned_cases']} cases, {g['purpose']}" for g in groups],
        "",
        f"Total future cases: {total} / {MAX_FUTURE_CASES}.",
        "",
        "## Decision Tree",
        "",
        *[f"- {line}" for line in summary["decision_tree"]],
        "",
        "Excluded: B240 rerun, H650, coverage, K=6, finite patch, dipole, DBR/RCLED, H500 rescue.",
        "",
    ]), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(write_outputs(), indent=2))

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BATCH_PLAN = ROOT / "outputs" / "lp_ml1b2a_36case_pilot_plan" / "lp_ml1b2a_batch_plan.csv"
RESULTS = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_01" / "lp_ml1b2b_batch01_results.csv"
RANKING = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_01" / "lp_ml1b2b_batch01_candidate_ranking.csv"
SUMMARY_IN = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_01" / "lp_ml1b2b_batch01_summary.json"
QUEUE = ROOT / "outputs" / "lp_ml1b0_runner_planning" / "lp_ml1b0_pilot_queue.csv"
MANIFEST = ROOT / "outputs" / "lp_ml1a4_explicit_geometry_seed_generator" / "lp_ml1a4_explicit_seed_manifest.csv"
OUT_DIR = ROOT / "outputs" / "lp_ml1b2b_36case_pilot"
GEOM_JOIN = OUT_DIR / "batch_01" / "lp_ml1b2b_batch01_geometry_response_join.csv"
REMAINING = OUT_DIR / "lp_ml1b2b_remaining_batch_composition.csv"
RECOMMEND = OUT_DIR / "lp_ml1b2b_next_batch_recommendation.json"
REPORT = ROOT / "reports" / "lp_ml1b2b_batch01_diagnostic_and_next_batch_audit.md"
GEOM_FIELDS = ["L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "H_nm"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def ff(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def split_dist(text: str) -> dict[str, int]:
    out = {}
    for part in (text or "").split(";"):
        if not part or ":" not in part:
            continue
        key, value = part.split(":", 1)
        out[key] = int(float(value))
    return out


def is_diverse(row: dict[str, str]) -> tuple[str, int]:
    targets = split_dist(row.get("target_bin_distribution", ""))
    groups = split_dist(row.get("sampling_group_distribution", ""))
    heights = split_dist(row.get("H_nm_distribution", ""))
    score = len(targets) * 3 + len(groups) * 2 + len(heights)
    label = "diverse" if len(targets) >= 2 or len(groups) >= 2 else "mostly_one_exploration_group"
    return label, score


def main() -> None:
    missing = [p for p in [BATCH_PLAN, RESULTS, RANKING, SUMMARY_IN, QUEUE, MANIFEST] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing input(s): " + ", ".join(str(p) for p in missing))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    ranking = read_csv(RANKING)
    results = read_csv(RESULTS)
    batches = read_csv(BATCH_PLAN)
    queue = {r["candidate_id"]: r for r in read_csv(QUEUE)}
    manifest = {r["candidate_id"]: r for r in read_csv(MANIFEST)}
    summary = json.loads(SUMMARY_IN.read_text(encoding="utf-8"))

    nearest_counts = Counter(r["nearest_bin_mode"] for r in ranking)
    status_counts = Counter(r["preliminary_status"] for r in ranking)
    txs = [ff(r["Tx_mean"]) for r in ranking]
    ratios = [ff(r["ratio_median"]) for r in ranking]
    phase452 = [ff(r["phase_err_at_452nm"]) for r in ranking]
    high_tx_poor_ratio = [r for r in ranking if ff(r["Tx_mean"]) >= 0.45 and ff(r["ratio_median"]) < 3]
    phase_near_poor_ratio = [r for r in ranking if ff(r["phase_err_at_452nm"]) <= 30 and ff(r["ratio_median"]) < 3]
    drift = [r for r in ranking if r["nearest_bin_mode"] != r["target_bin"]]

    geom_rows = []
    for r in ranking:
        cid = r["candidate_id"]
        src = manifest.get(cid) or queue.get(cid) or {}
        row = {"candidate_id": cid, "target_bin": r.get("target_bin", ""), "sampling_group": src.get("sampling_group", ""), "nearest_bin_mode": r.get("nearest_bin_mode", ""), "Tx_mean": r.get("Tx_mean", ""), "ratio_median": r.get("ratio_median", ""), "phase_err_at_452nm": r.get("phase_err_at_452nm", "")}
        for field in GEOM_FIELDS:
            row[field] = src.get(field, "")
        geom_rows.append(row)

    remaining_rows = []
    for b in batches:
        if b.get("batch_id") == "LPML1B2A_BATCH_01":
            continue
        label, score = is_diverse(b)
        groups = split_dist(b.get("sampling_group_distribution", ""))
        targets = split_dist(b.get("target_bin_distribution", ""))
        remaining_rows.append({
            "batch_id": b.get("batch_id", ""),
            "candidate_count": b.get("candidate_count", ""),
            "target_bin_distribution": b.get("target_bin_distribution", ""),
            "sampling_group_distribution": b.get("sampling_group_distribution", ""),
            "H_nm_distribution": b.get("H_nm_distribution", ""),
            "expected_subrun_count": b.get("planned_subruns", ""),
            "composition_label": label,
            "diversity_score": score,
            "contains_B240": str("240" in targets).lower(),
            "contains_global_escape_lhs": str("global_escape_lhs" in groups).lower(),
            "contains_sixbin_balance": str("sixbin_balance" in groups).lower(),
            "note": "B300 continuation / statistical failure mapping" if b.get("batch_id") == "LPML1B2A_BATCH_02" and set(targets) == {"300"} else "diverse next batch candidate" if ("240" in targets and ("global_escape_lhs" in groups or "sixbin_balance" in groups)) else "remaining planned batch",
        })
    candidates = [r for r in remaining_rows if r["note"] == "diverse next batch candidate"]
    if candidates:
        recommended = sorted(candidates, key=lambda r: (-int(r["diversity_score"]), r["batch_id"]))[0]
        rationale = "batch-01 and batch-02 are B300-heavy; this batch adds B240 plus global/sixbin diversity."
    else:
        recommended = remaining_rows[0]
        rationale = "no diverse B240/global/sixbin alternative found; fall back to next planned batch."

    write_csv(GEOM_JOIN, geom_rows, ["candidate_id", "target_bin", "sampling_group", *GEOM_FIELDS, "nearest_bin_mode", "Tx_mean", "ratio_median", "phase_err_at_452nm"])
    write_csv(REMAINING, remaining_rows, ["batch_id", "candidate_count", "target_bin_distribution", "sampling_group_distribution", "H_nm_distribution", "expected_subrun_count", "composition_label", "diversity_score", "contains_B240", "contains_global_escape_lhs", "contains_sixbin_balance", "note"])
    rec = {"recommended_next_batch_id": recommended["batch_id"], "recommendation": "authorize_this_batch_next_but_do_not_run_now", "rationale": rationale, "batch_02_label": next((r["note"] for r in remaining_rows if r["batch_id"] == "LPML1B2A_BATCH_02"), ""), "no_fdtd_run": True, "no_k6_readiness_claim": True, "batch01_summary": {"nearest_bin_counts": dict(nearest_counts), "status_counts": dict(status_counts), "high_tx_poor_ratio_count": len(high_tx_poor_ratio), "phase_near_poor_ratio_count": len(phase_near_poor_ratio), "drift_count": len(drift)}}
    RECOMMEND.write_text(json.dumps(rec, indent=2), encoding="utf-8")

    def bullet(rows: list[dict[str, str]]) -> list[str]:
        return [f"- {r['candidate_id']}: nearest={r['nearest_bin_mode']}, Tx_mean={r['Tx_mean']}, ratio_median={r['ratio_median']}, phase_err_452={r['phase_err_at_452nm']}" for r in rows]
    comp_table = ["| batch | targets | groups | H | label | note |", "|---|---|---|---|---|---|"]
    for r in remaining_rows:
        comp_table.append(f"| {r['batch_id']} | {r['target_bin_distribution']} | {r['sampling_group_distribution']} | {r['H_nm_distribution']} | {r['composition_label']} | {r['note']} |")
    report = [
        "# LP-ML1B2B batch-01 diagnostic and next-batch audit", "",
        "This is analysis only. No FDTD was run. No GUI, FMM, ML training, K=6, or coverage was run.", "",
        "## Batch-01 technical result", f"- candidates: {summary.get('candidate_count')}", f"- subruns: {summary.get('actual_subrun_records')} / {summary.get('expected_subruns')}", f"- merged Jones rows: {summary.get('merged_row_count')} / {summary.get('expected_merged_rows')}", f"- failures: {summary.get('failure_count')}", f"- anomalies: {summary.get('anomaly_count')}", "",
        "## Batch-01 performance interpretation", "- Technical PASS: runner/schema/resume/reporting produced complete finite data with no failures or anomaly flags.", "- Physical weak: no strong/usable B300 candidate appeared; phase targeting is scattered and selectivity is generally poor.", "", f"- nearest_bin_mode counts: {dict(nearest_counts)}", f"- preliminary_status counts: {dict(status_counts)}", f"- Tx_mean range/median: {min(txs):.6f}..{max(txs):.6f} / {median(txs):.6f}", f"- ratio_median range/median: {min(ratios):.6f}..{max(ratios):.6f} / {median(ratios):.6f}", f"- phase_err_at_452nm range/median: {min(phase452):.6f}..{max(phase452):.6f} / {median(phase452):.6f}", "",
        "## High-Tx but poor-ratio candidates", *bullet(high_tx_poor_ratio), "",
        "## Phase-near-target but poor-ratio candidates", *bullet(phase_near_poor_ratio), "",
        "## Drifted candidates", *bullet(drift), "",
        "## Remaining batch composition", *comp_table, "",
        "## Recommendation", f"Authorize next: **{recommended['batch_id']}**.", f"Rationale: {rationale}", "Do not declare K=6 readiness.", "Do not execute anything from this diagnostic step.", ""]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()

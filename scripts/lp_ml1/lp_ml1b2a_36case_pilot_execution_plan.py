from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
B0 = ROOT / "outputs" / "lp_ml1b0_runner_planning"
B1A = ROOT / "outputs" / "lp_ml1b1a_smoke_result_sanity_audit"
OUT = ROOT / "outputs" / "lp_ml1b2a_36case_pilot_plan"
REPORTS = ROOT / "reports"
QUEUE_IN = B0 / "lp_ml1b0_pilot_queue.csv"
SMOKE_IN = B0 / "lp_ml1b0_smoke_test_recommendation.csv"
B1A_SUMMARY = B1A / "lp_ml1b1a_summary.json"
B1A_CANDIDATES = B1A / "lp_ml1b1a_candidate_summary.csv"
QUEUE_AUDIT = OUT / "lp_ml1b2a_pilot_queue_audit.csv"
BATCH_PLAN = OUT / "lp_ml1b2a_batch_plan.csv"
SUMMARY = OUT / "lp_ml1b2a_summary.json"
PLAN_MD = REPORTS / "lp_ml1b2a_36case_pilot_execution_plan.md"
EXPECTED_COUNT = 36
BATCH_SIZE = 6
WAVELENGTHS = [450, 450.5, 451, 451.5, 452, 452.5, 453, 453.5, 454]
POLARIZATIONS = ["x", "y"]
SMOKE_RUNTIME_SECONDS = {
    "LPML1A4_0028_B300_exploration_B300_H600": 340.82,
    "LPML1A4_0234_B240_exploration_B240_H600": 296.46,
}
GEOMETRY_FIELDS = ["H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm"]
AUDIT_FIELDS = ["queue_id", "candidate_id", "target_bin_deg", "sampling_group", "sampling_family", "H_nm", "geometry_complete", "missing_geometry_fields", "planned_wavelength_count", "planned_polarization_count", "planned_subruns", "estimated_runtime_sec", "estimated_runtime_min", "resume_key_policy", "failure_log_policy", "ready_for_b2b"]
BATCH_FIELDS = ["batch_id", "candidate_count", "candidate_ids", "target_bin_distribution", "H_nm_distribution", "sampling_group_distribution", "planned_subruns", "estimated_runtime_sec", "estimated_runtime_min", "recommended_order", "resume_rule"]
RESULT_SCHEMA = ["candidate_id", "target_bin_deg", "wavelength_nm", "txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im", "selected_Tx", "leakage_xin_to_yout", "leakage_yin_to_xout", "y_direct_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "nearest_bin_deg", "phase_error_deg", "matrix_error", "spectral_pass", "result_status", "error_message", "result_csv", "fsp_path_untracked"]


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


def to_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def count_str(rows: list[dict[str, Any]], key: str) -> str:
    return ";".join(f"{k}:{v}" for k, v in sorted(Counter(str(r.get(key, "")) for r in rows).items()))


def validate_inputs() -> None:
    missing = [p for p in [QUEUE_IN, SMOKE_IN, B1A_SUMMARY, B1A_CANDIDATES] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing LP-ML1B2A input(s): " + ", ".join(str(p) for p in missing))


def geometry_complete(row: dict[str, str]) -> tuple[bool, list[str]]:
    missing = []
    for field in GEOMETRY_FIELDS:
        value = row.get(field, "")
        if value == "" or not math.isfinite(to_float(value)):
            missing.append(field)
    return not missing, missing


def make_audit(queue: list[dict[str, str]], runtime_per_candidate: float) -> list[dict[str, Any]]:
    rows = []
    for row in queue:
        ok, missing = geometry_complete(row)
        rows.append({
            "queue_id": row.get("queue_id", ""),
            "candidate_id": row["candidate_id"],
            "target_bin_deg": row["target_bin_deg"],
            "sampling_group": row.get("sampling_group", ""),
            "sampling_family": row.get("sampling_family", ""),
            "H_nm": row.get("H_nm", ""),
            "geometry_complete": str(ok).lower(),
            "missing_geometry_fields": ";".join(missing),
            "planned_wavelength_count": len(WAVELENGTHS),
            "planned_polarization_count": len(POLARIZATIONS),
            "planned_subruns": len(WAVELENGTHS) * len(POLARIZATIONS),
            "estimated_runtime_sec": f"{runtime_per_candidate:.2f}",
            "estimated_runtime_min": f"{runtime_per_candidate / 60:.2f}",
            "resume_key_policy": "skip_existing_candidate_wavelength_polarization_rows",
            "failure_log_policy": "append_case_level_error_to_failure_log_and_continue",
            "ready_for_b2b": str(ok).lower(),
        })
    return rows


def make_batches(audit_rows: list[dict[str, Any]], runtime_per_candidate: float) -> list[dict[str, Any]]:
    batches = []
    for i in range(0, len(audit_rows), BATCH_SIZE):
        chunk = audit_rows[i:i + BATCH_SIZE]
        batch_id = f"LPML1B2A_BATCH_{len(batches) + 1:02d}"
        batches.append({
            "batch_id": batch_id,
            "candidate_count": len(chunk),
            "candidate_ids": ";".join(str(r["candidate_id"]) for r in chunk),
            "target_bin_distribution": count_str(chunk, "target_bin_deg"),
            "H_nm_distribution": count_str(chunk, "H_nm"),
            "sampling_group_distribution": count_str(chunk, "sampling_group"),
            "planned_subruns": len(chunk) * len(WAVELENGTHS) * len(POLARIZATIONS),
            "estimated_runtime_sec": f"{len(chunk) * runtime_per_candidate:.2f}",
            "estimated_runtime_min": f"{len(chunk) * runtime_per_candidate / 60:.2f}",
            "recommended_order": len(batches) + 1,
            "resume_rule": "before_each_subrun_check_result_status_for_candidate_wavelength_polarization",
        })
    return batches


def main() -> None:
    validate_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    queue = read_csv(QUEUE_IN)
    if len(queue) != EXPECTED_COUNT:
        raise ValueError(f"Expected {EXPECTED_COUNT} pilot candidates, got {len(queue)}")
    with B1A_SUMMARY.open(encoding="utf-8") as f:
        b1a_summary = json.load(f)
    b1a_candidates = read_csv(B1A_CANDIDATES)
    runtime_per_candidate = mean(SMOKE_RUNTIME_SECONDS.values())
    audit_rows = make_audit(queue, runtime_per_candidate)
    batches = make_batches(audit_rows, runtime_per_candidate)
    missing_geometry_count = sum(1 for r in audit_rows if r["geometry_complete"] != "true")
    target_counts = Counter(row["target_bin_deg"] for row in queue)
    group_counts = Counter(row.get("sampling_group", "") for row in queue)
    h_counts = Counter(row.get("H_nm", "") for row in queue)
    total_runtime = len(queue) * runtime_per_candidate
    summary = {
        "stage": "LP-ML1B2A",
        "planning_only_no_fdtd": True,
        "pilot_candidate_count": len(queue),
        "geometry_complete_count": len(queue) - missing_geometry_count,
        "missing_geometry_count": missing_geometry_count,
        "target_bin_distribution": dict(sorted(target_counts.items(), key=lambda kv: int(kv[0]))),
        "sampling_group_distribution": dict(sorted(group_counts.items())),
        "H_nm_distribution": dict(sorted(h_counts.items(), key=lambda kv: int(kv[0]))),
        "wavelengths_nm": WAVELENGTHS,
        "polarizations": POLARIZATIONS,
        "planned_subruns": len(queue) * len(WAVELENGTHS) * len(POLARIZATIONS),
        "batch_size_candidates": BATCH_SIZE,
        "batch_count": len(batches),
        "runtime_basis_seconds": SMOKE_RUNTIME_SECONDS,
        "estimated_runtime_per_candidate_sec": round(runtime_per_candidate, 2),
        "estimated_total_runtime_sec": round(total_runtime, 2),
        "estimated_total_runtime_hours": round(total_runtime / 3600, 2),
        "b1a_decision": b1a_summary.get("decision", ""),
        "b1a_go_no_go": b1a_summary.get("go_no_go", ""),
        "performance_caution": "B300 smoke had low Tx/ratio; B240 smoke shifted toward bin 120 and was phase-wrong; B2 is statistical exploration and seed filtering, not K=6 readiness.",
        "result_schema_columns": RESULT_SCHEMA,
    }
    write_csv(QUEUE_AUDIT, audit_rows, AUDIT_FIELDS)
    write_csv(BATCH_PLAN, batches, BATCH_FIELDS)
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    b1a_lines = [f"- {r['candidate_id']}: Tx_mean={r['selected_Tx_mean']}, phase_err_452={r['phase_error_deg_at_452nm']}, nearest_bin_mode={r['nearest_bin_mode']}, ratio_median={r['conversion_to_leakage_ratio_median']}" for r in b1a_candidates]
    md = [
        "# LP-ML1B2A 36-case pilot execution plan",
        "",
        "Purpose: plan the frozen LP-ML1B 36-case pilot execution without running FDTD.",
        "",
        "## Inputs",
        f"- {QUEUE_IN}",
        f"- {B1A_SUMMARY}",
        f"- {B1A_CANDIDATES}",
        "",
        "## Frozen queue audit",
        f"- frozen candidate count: {len(queue)}",
        f"- geometry complete: {len(queue) - missing_geometry_count}",
        f"- missing geometry: {missing_geometry_count}",
        f"- target_bin distribution: {dict(sorted(target_counts.items(), key=lambda kv: int(kv[0])))}",
        f"- sampling_group distribution: {dict(sorted(group_counts.items()))}",
        f"- H_nm distribution: {dict(sorted(h_counts.items(), key=lambda kv: int(kv[0])))}",
        "",
        "## Runtime estimate",
        "- LPML1A4_0028_B300_exploration_B300_H600: 340.82 s",
        "- LPML1A4_0234_B240_exploration_B240_H600: 296.46 s",
        f"- estimated per candidate: {runtime_per_candidate:.2f} s",
        f"- estimated 36-candidate pilot: {total_runtime:.2f} s = {total_runtime / 3600:.2f} h plus overhead",
        "",
        "## Batching",
        f"- recommended batch size: {BATCH_SIZE} candidates",
        f"- batch count: {len(batches)}",
        "- reason: small enough to inspect failures between batches while avoiding one-candidate overhead.",
        "",
        "## Resume logic",
        "- Before each candidate/wavelength/polarization subrun, check whether a successful row already exists in the result CSV.",
        "- Resume key: candidate_id + wavelength_nm + input_polarization.",
        "- Skip successful rows; retry missing or failed rows only when explicitly requested.",
        "",
        "## Failure logging",
        "- Write a failure row with candidate_id, wavelength_nm, polarization, status, exception type, message, traceback head, fsp path, and runtime seconds.",
        "- Continue to the next subrun unless Lumerical startup itself fails repeatedly.",
        "",
        "## LP-ML1B2B output schema",
        "- " + ", ".join(RESULT_SCHEMA),
        "",
        "## LP-ML1B2C sanity/ranking criteria",
        "- Verify finite complex Jones entries and recomputed metrics as in LP-ML1B1A.",
        "- Rank seeds by spectral median ratio, Tx floor, matrix_error ceiling, bin consistency, and phase error stability.",
        "- Treat the pilot as seed filtering only; do not claim K=6 readiness.",
        "",
        "## Performance caution from LP-ML1B1A",
        *b1a_lines,
        "- B300 smoke: low Tx and ratio < 1.",
        "- B240 smoke: nearest bin shifted toward 120 and phase-wrong.",
        "- LP-ML1B2 is for statistical exploration and seed filtering, not immediate K=6 use.",
        "",
        "No FDTD was run.",
        "No Lumerical GUI was opened.",
        "No FMM solve was executed.",
        "No model training was run.",
        "No K=6 was started.",
    ]
    PLAN_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

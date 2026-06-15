from __future__ import annotations

import csv
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/stage11_2h_h500_120_y_pair_micro_rescue"
RESULT = OUT_DIR / "h500_120_y_pair_micro_rescue_fdtd_results_stage11_2h.csv"
SUMMARY_CSV = OUT_DIR / "h500_120_y_pair_micro_rescue_result_summary_stage11_2h.csv"
BEST_CSV = OUT_DIR / "best_120_strict_or_loose_stage11_2h.csv"
BEFORE_AFTER_CSV = OUT_DIR / "before_after_120_stage11_2h.csv"
SUMMARY_MD = OUT_DIR / "h500_120_y_pair_micro_rescue_summary_stage11_2h.md"

PHASE_BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12

BEFORE = {
    "candidate_id": "H500DIMER2C_004_B120_x_pair_swap_G60_O-20",
    "actual_common_phase_deg": 123.736197,
    "nearest_bin_deg": 120,
    "phase_err_to_120_deg": 3.736197,
    "selected_x_power": 0.505731,
    "blocked_y_leakage": 0.112372,
    "conversion_to_leakage_ratio": 4.500509,
    "matrix_error": 0.471387,
    "status": "loose",
}

SUMMARY_FIELDS = [
    "candidate_id",
    "actual_common_phase_deg",
    "nearest_bin_deg",
    "phase_err_to_120_deg",
    "selected_x_power",
    "blocked_y_leakage",
    "conversion_to_leakage_ratio",
    "matrix_error",
    "leakage_budget_for_ratio6",
    "leakage_excess",
    "strict_status",
    "loose_status",
    "fdtd_status",
    "source_pair_id",
    "base_donor_case_id",
    "placement_type",
    "swap_order",
    "gap_nm",
    "local_offset_nm",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def nearest_bin(phase: float) -> tuple[int, float]:
    nearest = min(PHASE_BINS, key=lambda b: abs(wrap180(phase - b)))
    return nearest, abs(wrap180(phase - nearest))


def metric(row: dict[str, str]) -> dict[str, object]:
    t_xx = flt(row.get("t_xx_amp"))
    t_yx = flt(row.get("t_yx_amp"))
    t_xy = flt(row.get("t_xy_amp"))
    t_yy = flt(row.get("t_yy_amp"))
    phase = flt(row.get("t_xx_phase_deg", row.get("dimer_output_phase_deg")))
    selected = t_xx * t_xx
    leakage = t_xy * t_xy + t_yy * t_yy
    ratio = selected / max(leakage, EPS)
    matrix_error = math.sqrt(t_yx * t_yx + leakage) / max(t_xx, EPS)
    nearest, phase_err = nearest_bin(phase)
    budget = selected / 6.0
    strict = nearest == 120 and ratio >= 6 and phase_err <= 10 and selected >= 0.45 and matrix_error <= BEFORE["matrix_error"]
    loose = nearest == 120 and ratio >= 3 and phase_err <= 15 and selected >= 0.10
    return {
        "candidate_id": row.get("dimer_case_id", ""),
        "actual_common_phase_deg": fmt(phase),
        "nearest_bin_deg": str(nearest),
        "phase_err_to_120_deg": fmt(phase_err),
        "selected_x_power": fmt(selected),
        "blocked_y_leakage": fmt(leakage),
        "conversion_to_leakage_ratio": fmt(ratio),
        "matrix_error": fmt(matrix_error),
        "leakage_budget_for_ratio6": fmt(budget),
        "leakage_excess": fmt(leakage - budget),
        "strict_status": str(strict).lower(),
        "loose_status": str(loose).lower(),
        "fdtd_status": row.get("fdtd_status", ""),
        "source_pair_id": row.get("source_pair_id", ""),
        "base_donor_case_id": row.get("base_donor_case_id", ""),
        "placement_type": row.get("placement_type", ""),
        "swap_order": row.get("swap_order", ""),
        "gap_nm": row.get("gap_nm", ""),
        "local_offset_nm": row.get("local_offset_nm", ""),
    }


def best_key(row: dict[str, object]) -> tuple[float, float, float, float]:
    strict_rank = 0 if row["strict_status"] == "true" else 1
    return (
        strict_rank,
        -flt(row["conversion_to_leakage_ratio"], 0),
        flt(row["phase_err_to_120_deg"], 999),
        flt(row["matrix_error"], 999),
    )


def before_row() -> dict[str, object]:
    selected = BEFORE["selected_x_power"]
    leakage = BEFORE["blocked_y_leakage"]
    budget = selected / 6.0
    return {
        **BEFORE,
        "leakage_budget_for_ratio6": fmt(budget),
        "leakage_excess": fmt(leakage - budget),
        "strict_status": "false",
        "loose_status": "true",
        "fdtd_status": "prior_best",
        "source_pair_id": "",
        "base_donor_case_id": "",
        "placement_type": "x_pair",
        "swap_order": "J2-J1",
        "gap_nm": "60",
        "local_offset_nm": "-20",
    }


def main() -> None:
    if not RESULT.exists():
        raise SystemExit(f"missing required input: {RESULT}")
    rows = [metric(row) for row in read_csv(RESULT)]
    rows = sorted(rows, key=best_key)
    write_csv(SUMMARY_CSV, rows, SUMMARY_FIELDS)
    best_rows = rows[: min(10, len(rows))]
    write_csv(BEST_CSV, best_rows, SUMMARY_FIELDS)
    before = before_row()
    after = best_rows[0] if best_rows else before
    write_csv(BEFORE_AFTER_CSV, [{"stage": "before", **before}, {"stage": "after", **after}], ["stage"] + SUMMARY_FIELDS)
    strict_reached = after.get("strict_status") == "true"
    before_leak = flt(before["blocked_y_leakage"])
    after_leak = flt(after["blocked_y_leakage"])
    lines = [
        "# Stage11-2H H500 120 y-pair micro-rescue summary",
        "",
        "Only H500 120-only y-pair dimer FDTD was run. No K=6, no metagrating, no H600/H700.",
        "",
        f"run_case_count = {len(rows)}",
        f"strict_120_reached = {strict_reached}",
        "",
        "## Before",
        f"- case = {before['candidate_id']}",
        f"- ratio = {before['conversion_to_leakage_ratio']}",
        f"- Tx = {before['selected_x_power']}",
        f"- leakage = {before['blocked_y_leakage']}",
        f"- phase_err = {before['phase_err_to_120_deg']}",
        f"- matrix_error = {before['matrix_error']}",
        "",
        "## Best After",
        f"- case = {after['candidate_id']}",
        f"- ratio = {after['conversion_to_leakage_ratio']}",
        f"- Tx = {after['selected_x_power']}",
        f"- leakage = {after['blocked_y_leakage']}",
        f"- leakage_delta_vs_before = {fmt(after_leak - before_leak)}",
        f"- phase_err = {after['phase_err_to_120_deg']}",
        f"- matrix_error = {after['matrix_error']}",
        f"- strict_status = {after['strict_status']}",
        "",
        "Success target is ratio >= 6, nearest bin 120, preferably phase_err <= 10 deg, Tx >= 0.45, and matrix_error not worse than current best.",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"run_case_count={len(rows)}")
    print(f"strict_120_reached={strict_reached}")
    print(f"best_case={after['candidate_id']}")
    print(f"best_ratio={after['conversion_to_leakage_ratio']}")
    print(f"best_leakage_delta={fmt(after_leak - before_leak)}")


if __name__ == "__main__":
    main()

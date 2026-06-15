from __future__ import annotations

import csv
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull"

IN_FILES = [
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2a_h500_dimer_validation/h500_dimer_fdtd_results_stage11_2a.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin/h500_dimer_placement_patch_fdtd_results_stage11_2b.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_alt_patch_fdtd_results_stage11_2c.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/h500_dimer_final_gap_fdtd_results_stage11_2d.csv",
    OUT_DIR / "h500_dimer_240_fine_pull_fdtd_results_stage11_2e.csv",
]

SUMMARY_MD = OUT_DIR / "h500_dimer_actual_6bin_summary_stage11_2e.md"
BEST_CSV = OUT_DIR / "h500_dimer_best_actual_6bin_library_stage11_2e.csv"
GAP_MD = OUT_DIR / "h500_dimer_240_remaining_gap_diagnosis_stage11_2e.md"
PROJ_MD = OUT_DIR / "h500_dimer_240_projection_matrix_diagnosis_stage11_2e.md"

PHASE_BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12
BEFORE_240_CASE = "H500DIMER2D_018_B240_x_pair_swap_G80_O-30"

BEST_FIELDS = [
    "bin_deg",
    "candidate_count",
    "best_case_id",
    "source_file",
    "projection_selectivity_ratio",
    "selected_power",
    "blocked_input_total_power",
    "selected_polarization_purity",
    "matrix_projection_error_norm",
    "actual_common_phase_deg",
    "actual_common_phase_error_deg",
    "usable_status",
    "failure_mode",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {str(k): "" if v is None else str(v) for k, v in row.items()}
            for row in csv.DictReader(handle)
        ]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: object, default: float = math.nan) -> float:
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


def nearest_bin(phase_deg: float) -> tuple[int, float]:
    bin_deg = min(PHASE_BINS, key=lambda candidate: abs(wrap180(phase_deg - candidate)))
    return bin_deg, abs(wrap180(phase_deg - bin_deg))


def metric(row: dict[str, str]) -> dict[str, str]:
    t_xx_amp = as_float(row.get("t_xx_amp"))
    t_yx_amp = as_float(row.get("t_yx_amp"))
    t_xy_amp = as_float(row.get("t_xy_amp"))
    t_yy_amp = as_float(row.get("t_yy_amp"))
    phase = as_float(row.get("t_xx_phase_deg", row.get("dimer_output_phase_deg")))

    selected_power = t_xx_amp * t_xx_amp
    x_input_cross = t_yx_amp * t_yx_amp
    blocked_power = t_xy_amp * t_xy_amp + t_yy_amp * t_yy_amp
    ratio = selected_power / max(blocked_power, EPS)
    purity = selected_power / max(selected_power + x_input_cross, EPS)
    matrix_error = math.sqrt(x_input_cross + blocked_power) / max(t_xx_amp, EPS)
    actual_bin, actual_error = nearest_bin(phase)

    if selected_power < 0.10:
        status = "low_selected_power"
        failure = "selected_power_too_low"
    elif purity < 0.80:
        status = "cross_polarization_leakage"
        failure = "cross_polarization_leakage"
    elif ratio < 3.0:
        status = "leaky_projection_broken"
        failure = "projection_matrix_broken_y_leakage"
    elif actual_error <= 8.0 and ratio >= 6.0 and matrix_error <= 0.60:
        status = "actual_dimer_usable_strict"
        failure = "projection_matrix_usable_phase_hit"
    elif actual_error <= 15.0 and ratio >= 3.0 and matrix_error <= 1.00:
        status = "actual_dimer_usable_loose"
        failure = "projection_matrix_usable_phase_hit"
    elif ratio >= 6.0 and selected_power >= 0.10 and purity >= 0.80:
        status = "high_selectivity_common_phase_missed"
        failure = "common_phase_missed"
    else:
        status = "projection_matrix_or_phase_not_usable"
        failure = "projection_matrix_or_phase_not_usable"

    return {
        **row,
        "actual_nearest_bin_deg": str(actual_bin),
        "actual_common_phase_deg": fmt(phase),
        "actual_common_phase_error_deg": fmt(actual_error),
        "selected_power": fmt(selected_power),
        "x_input_cross_leak_power": fmt(x_input_cross),
        "blocked_input_total_power": fmt(blocked_power),
        "projection_selectivity_ratio": fmt(ratio),
        "selected_polarization_purity": fmt(purity),
        "matrix_projection_error_norm": fmt(matrix_error),
        "usable_status": status,
        "failure_mode": failure,
    }


def rank_key(row: dict[str, str]) -> tuple[float, float, float, float]:
    status_rank = {
        "actual_dimer_usable_strict": 0,
        "actual_dimer_usable_loose": 1,
        "high_selectivity_common_phase_missed": 2,
    }.get(row["usable_status"], 3)
    return (
        status_rank,
        as_float(row["actual_common_phase_error_deg"], 999.0),
        -as_float(row["projection_selectivity_ratio"], 0.0),
        as_float(row["matrix_projection_error_norm"], 999.0),
    )


def load_all_rows() -> list[dict[str, str]]:
    missing = [path for path in IN_FILES if not path.exists()]
    if missing:
        raise SystemExit("missing required input: " + ", ".join(str(path) for path in missing))
    rows: list[dict[str, str]] = []
    for path in IN_FILES:
        for row in read_csv(path):
            rows.append(metric({**row, "source_file": path.name}))
    return rows


def best_by_bin(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    best_rows: list[dict[str, str]] = []
    for bin_deg in PHASE_BINS:
        subset = [
            row for row in rows
            if int(as_float(row["actual_nearest_bin_deg"], -999.0)) == bin_deg
        ]
        subset.sort(key=rank_key)
        if not subset:
            best_rows.append({
                "bin_deg": str(bin_deg),
                "candidate_count": "0",
                "best_case_id": "",
                "source_file": "",
                "projection_selectivity_ratio": "",
                "selected_power": "",
                "blocked_input_total_power": "",
                "selected_polarization_purity": "",
                "matrix_projection_error_norm": "",
                "actual_common_phase_deg": "",
                "actual_common_phase_error_deg": "",
                "usable_status": "missing_dimer",
                "failure_mode": "missing_dimer",
                "notes": "no real H500 dimer in this actual common-phase bin",
            })
            continue
        best = subset[0]
        best_rows.append({
            "bin_deg": str(bin_deg),
            "candidate_count": str(len(subset)),
            "best_case_id": best.get("dimer_case_id", ""),
            "source_file": best.get("source_file", ""),
            "projection_selectivity_ratio": best["projection_selectivity_ratio"],
            "selected_power": best["selected_power"],
            "blocked_input_total_power": best["blocked_input_total_power"],
            "selected_polarization_purity": best["selected_polarization_purity"],
            "matrix_projection_error_norm": best["matrix_projection_error_norm"],
            "actual_common_phase_deg": best["actual_common_phase_deg"],
            "actual_common_phase_error_deg": best["actual_common_phase_error_deg"],
            "usable_status": best["usable_status"],
            "failure_mode": best["failure_mode"],
            "notes": "selected-channel actual common phase bin; real H500 dimer only",
        })
    return best_rows


def write_summary(best_rows: list[dict[str, str]]) -> None:
    lines = [
        "# Stage11-2E H500 Actual Dimer Projection-Phase 6-bin Summary",
        "",
        "Merged Stage11-2A + 2B + 2C + 2D + 2E real H500 dimer FDTD.",
        "Bins are assigned by selected-channel actual common phase angle(t_xx), not by single-pillar static phase.",
        "",
        "| bin_deg | candidate_count | best_case_id | ratio | Tx | blocked_y_power | purity | matrix_error | common_phase | phase_error | usable_status | failure_mode |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in best_rows:
        lines.append(
            f"| {row['bin_deg']} | {row['candidate_count']} | {row['best_case_id']} | "
            f"{row['projection_selectivity_ratio']} | {row['selected_power']} | "
            f"{row['blocked_input_total_power']} | {row['selected_polarization_purity']} | "
            f"{row['matrix_projection_error_norm']} | {row['actual_common_phase_deg']} | "
            f"{row['actual_common_phase_error_deg']} | {row['usable_status']} | {row['failure_mode']} |"
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_diagnostics(rows: list[dict[str, str]], best_rows: list[dict[str, str]]) -> None:
    before = next((row for row in rows if row.get("dimer_case_id") == BEFORE_240_CASE), None)
    best_240 = next(row for row in best_rows if row["bin_deg"] == "240")
    usable_loose = sum(
        row["usable_status"] in {"actual_dimer_usable_loose", "actual_dimer_usable_strict"}
        for row in rows
    )
    usable_strict = sum(row["usable_status"] == "actual_dimer_usable_strict" for row in rows)
    failure_counts: dict[str, int] = {}
    for row in rows:
        failure_counts[row["failure_mode"]] = failure_counts.get(row["failure_mode"], 0) + 1

    proj_lines = [
        "# Stage11-2E Projection Matrix Diagnosis",
        "",
        "This audit tests whether each real H500 dimer remains close to t*exp(i*phi)*|x><x|.",
        "It does not claim K=6 steering or phase-gradient supercell validation.",
        "",
        f"total_real_h500_dimer_cases = {len(rows)}",
        f"actual_dimer_usable_loose_or_strict = {usable_loose}",
        f"actual_dimer_usable_strict = {usable_strict}",
        "",
        "## Failure Mode Counts",
    ]
    proj_lines.extend(f"- {key}: {value}" for key, value in sorted(failure_counts.items()))
    proj_lines.extend([
        "",
        "## 240 Before/After",
    ])
    if before:
        proj_lines.append(
            "- before_2E: "
            f"{BEFORE_240_CASE}, ratio={before['projection_selectivity_ratio']}, "
            f"Tx={before['selected_power']}, phase_error={before['actual_common_phase_error_deg']}, "
            f"matrix_error={before['matrix_projection_error_norm']}, status={before['usable_status']}."
        )
    else:
        proj_lines.append(f"- before_2E: {BEFORE_240_CASE} not found in merged inputs.")
    proj_lines.append(
        "- after_2E_best_240: "
        f"{best_240['best_case_id']}, ratio={best_240['projection_selectivity_ratio']}, "
        f"Tx={best_240['selected_power']}, phase_error={best_240['actual_common_phase_error_deg']}, "
        f"matrix_error={best_240['matrix_projection_error_norm']}, status={best_240['usable_status']}."
    )
    PROJ_MD.write_text("\n".join(proj_lines) + "\n", encoding="utf-8")

    formed = all(
        row["usable_status"] in {"actual_dimer_usable_loose", "actual_dimer_usable_strict"}
        for row in best_rows
    )
    gap_lines = [
        "# Stage11-2E H500 240 Remaining Gap Diagnosis",
        "",
        f"H500 real-dimer projection-phase 6-bin library candidate formed = {formed}",
        "",
    ]
    for row in best_rows:
        if row["usable_status"] in {"actual_dimer_usable_loose", "actual_dimer_usable_strict"}:
            gap_lines.append(
                f"- {row['bin_deg']} deg: usable via {row['best_case_id']}; "
                f"ratio={row['projection_selectivity_ratio']}, Tx={row['selected_power']}, "
                f"phase_error={row['actual_common_phase_error_deg']}, "
                f"matrix_error={row['matrix_projection_error_norm']}."
            )
        else:
            gap_lines.append(
                f"- {row['bin_deg']} deg: gap remains; best={row['best_case_id']}; "
                f"failure={row['failure_mode']}; phase_error={row['actual_common_phase_error_deg']}."
            )
    gap_lines.extend([
        "",
        "Boundary: this is a real-dimer actual common-phase library audit only.",
        "It is not K=6 full FDTD, not a phase-gradient supercell result, and not LP steering completion.",
    ])
    GAP_MD.write_text("\n".join(gap_lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_all_rows()
    best_rows = best_by_bin(rows)
    write_csv(BEST_CSV, best_rows, BEST_FIELDS)
    write_summary(best_rows)
    write_diagnostics(rows, best_rows)

    print(f"total_cases={len(rows)}")
    print(
        "actual_dimer_usable_loose="
        f"{sum(row['usable_status'] in {'actual_dimer_usable_loose', 'actual_dimer_usable_strict'} for row in rows)}"
    )
    print(f"actual_dimer_usable_strict={sum(row['usable_status'] == 'actual_dimer_usable_strict' for row in rows)}")
    best_240 = next(row for row in best_rows if row["bin_deg"] == "240")
    print(
        "best_240="
        f"{best_240['best_case_id']},ratio={best_240['projection_selectivity_ratio']},"
        f"phase_error={best_240['actual_common_phase_error_deg']},status={best_240['usable_status']}"
    )


if __name__ == "__main__":
    main()

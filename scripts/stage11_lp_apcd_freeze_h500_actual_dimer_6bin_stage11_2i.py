from __future__ import annotations

import csv
import math
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze"
PHASE_BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12

INPUT_PATTERNS = [
    "outputs/blue10k6_lp_apcd_stage11_2a_h500_dimer_validation/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine/*fdtd_results*.csv",
    "outputs/stage11_2h_h500_120_y_pair_micro_rescue/*fdtd_results*.csv",
    "outputs/stage11_2h_h500_120_y_pair_micro_rescue/*result_summary*.csv",
]

FINAL_FIELDS = [
    "bin_deg",
    "candidate_id",
    "source_stage",
    "source_file",
    "geometry_family",
    "actual_common_phase_deg",
    "phase_err_deg",
    "selected_x_power",
    "blocked_y_leakage",
    "conversion_to_leakage_ratio",
    "matrix_error",
    "strict",
    "notes",
]

STRICT_FIELDS = FINAL_FIELDS + [
    "nearest_bin_deg",
    "leakage_budget_for_ratio6",
    "leakage_excess",
]

HANDOFF_FIELDS = [
    "phase_bin_deg",
    "candidate_id",
    "actual_common_phase_deg",
    "phase_err_deg",
    "selected_x_power",
    "blocked_y_leakage",
    "conversion_to_leakage_ratio",
    "matrix_error",
    "geometry_family",
    "source_stage",
    "source_file",
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


def nearest_bin(phase_deg: float) -> tuple[int, float]:
    bin_deg = min(PHASE_BINS, key=lambda candidate: abs(wrap180(phase_deg - candidate)))
    return bin_deg, abs(wrap180(phase_deg - bin_deg))


def source_stage(path: Path) -> str:
    text = path.as_posix().lower()
    for stage in ["2a", "2b", "2c", "2d", "2e", "2f", "2g", "2h"]:
        if f"stage11_{stage}" in text or f"stage11-{stage}" in text or f"stage11_2{stage[-1]}" in text:
            return f"Stage11-{stage.upper()}"
    if "stage11_2h" in text:
        return "Stage11-2H"
    return "unknown"


def geometry_family(candidate_id: str, row: dict[str, str]) -> str:
    placement = row.get("placement_type", "")
    if not placement:
        if "diag_pair" in candidate_id:
            placement = "diag_pair"
        elif "x_pair" in candidate_id:
            placement = "x_pair"
        elif "y_pair" in candidate_id:
            placement = "y_pair"
        else:
            placement = "unknown"
    swap = row.get("swap_order", "")
    if not swap:
        if "_noswap_" in candidate_id:
            swap = "J1-J2"
        elif "_swap_" in candidate_id:
            swap = "J2-J1"
        else:
            swap = "unknown"
    suffix = "swap" if swap == "J2-J1" else "noswap" if swap == "J1-J2" else "unknown"
    return f"{placement}_{suffix}"


def normalize_row(row: dict[str, str], path: Path) -> dict[str, object] | None:
    candidate_id = row.get("dimer_case_id") or row.get("candidate_id") or ""
    if not candidate_id:
        return None
    phase = flt(row.get("actual_common_phase_deg"))
    if math.isnan(phase):
        phase = flt(row.get("t_xx_phase_deg", row.get("dimer_output_phase_deg")))
    if math.isnan(phase):
        return None
    nearest, phase_err = nearest_bin(phase)
    t_xx = flt(row.get("t_xx_amp"))
    t_yx = flt(row.get("t_yx_amp"))
    t_xy = flt(row.get("t_xy_amp"))
    t_yy = flt(row.get("t_yy_amp"))
    selected = flt(row.get("selected_x_power", row.get("selected_power", row.get("target_x_power"))))
    if math.isnan(selected):
        selected = t_xx * t_xx
    leakage = flt(row.get("blocked_y_leakage", row.get("blocked_input_total_power", row.get("y_input_total_leak_power"))))
    if math.isnan(leakage):
        leakage = t_xy * t_xy + t_yy * t_yy
    ratio = flt(row.get("conversion_to_leakage_ratio", row.get("projection_selectivity_ratio", row.get("dimer_selectivity_ratio"))))
    if math.isnan(ratio):
        ratio = selected / max(leakage, EPS)
    matrix_error = flt(row.get("matrix_error", row.get("matrix_projection_error_norm")))
    if math.isnan(matrix_error):
        matrix_error = math.sqrt(max(t_yx * t_yx, 0.0) + max(leakage, 0.0)) / max(t_xx, EPS)
    strict = is_strict(
        {
            "nearest_bin_deg": nearest,
            "phase_err_deg": phase_err,
            "conversion_to_leakage_ratio": ratio,
            "selected_x_power": selected,
            "matrix_error": matrix_error,
        },
        nearest,
    )
    budget = selected / 6.0
    return {
        "candidate_id": candidate_id,
        "source_stage": source_stage(path),
        "source_file": path.name,
        "geometry_family": geometry_family(candidate_id, row),
        "actual_common_phase_deg": phase,
        "nearest_bin_deg": nearest,
        "phase_err_deg": phase_err,
        "selected_x_power": selected,
        "blocked_y_leakage": leakage,
        "conversion_to_leakage_ratio": ratio,
        "matrix_error": matrix_error,
        "strict": strict,
        "leakage_budget_for_ratio6": budget,
        "leakage_excess": leakage - budget,
        "notes": "H500 real-dimer selected-channel actual common-phase candidate",
    }


def is_strict(row: dict[str, object], target_bin: int) -> bool:
    return (
        int(row["nearest_bin_deg"]) == target_bin
        and float(row["phase_err_deg"]) <= 10.0
        and float(row["conversion_to_leakage_ratio"]) >= 6.0
        and float(row["selected_x_power"]) >= 0.10
        and float(row["matrix_error"]) <= 0.60
    )


def rank_key(row: dict[str, object], target_bin: int) -> tuple[object, ...]:
    return (
        0 if is_strict(row, target_bin) else 1,
        0 if int(row["nearest_bin_deg"]) == target_bin else 1,
        float(row["phase_err_deg"]),
        -float(row["conversion_to_leakage_ratio"]),
        -float(row["selected_x_power"]),
        float(row["blocked_y_leakage"]),
        float(row["matrix_error"]),
        str(row["candidate_id"]),
    )


def discover_files() -> list[Path]:
    files: list[Path] = []
    for pattern in INPUT_PATTERNS:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted(set(files))


def load_candidates() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for path in discover_files():
        for raw in read_csv(path):
            norm = normalize_row(raw, path)
            if not norm:
                continue
            key = (str(norm["candidate_id"]), str(path.name))
            if key in seen:
                continue
            seen.add(key)
            rows.append(norm)
    return rows


def format_row(row: dict[str, object], bin_deg: int | None = None) -> dict[str, object]:
    out = dict(row)
    if bin_deg is not None:
        out["bin_deg"] = str(bin_deg)
    for key in [
        "actual_common_phase_deg",
        "phase_err_deg",
        "selected_x_power",
        "blocked_y_leakage",
        "conversion_to_leakage_ratio",
        "matrix_error",
        "leakage_budget_for_ratio6",
        "leakage_excess",
    ]:
        if key in out:
            out[key] = fmt(float(out[key]))
    out["strict"] = str(bool(out["strict"])).lower()
    return out


def choose_by_bin(rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    final_rows: list[dict[str, object]] = []
    strict_rows: list[dict[str, object]] = []
    rejected_rows: list[dict[str, object]] = []
    for bin_deg in PHASE_BINS:
        bin_candidates = [row for row in rows if int(row["nearest_bin_deg"]) == bin_deg]
        bin_candidates.sort(key=lambda row: rank_key(row, bin_deg))
        strict_candidates = [row for row in bin_candidates if is_strict(row, bin_deg)]
        strict_rows.extend(format_row(row, bin_deg) for row in strict_candidates)
        if bin_candidates:
            best = bin_candidates[0]
            final_rows.append(format_row(best, bin_deg))
            loose_or_rejected = [row for row in bin_candidates if not is_strict(row, bin_deg)]
            if loose_or_rejected:
                rejected_rows.append(format_row(sorted(loose_or_rejected, key=lambda row: rank_key(row, bin_deg))[0], bin_deg))
    return final_rows, strict_rows, rejected_rows


def handoff_rows(final_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in final_rows:
        out.append({
            "phase_bin_deg": row["bin_deg"],
            "candidate_id": row["candidate_id"],
            "actual_common_phase_deg": row["actual_common_phase_deg"],
            "phase_err_deg": row["phase_err_deg"],
            "selected_x_power": row["selected_x_power"],
            "blocked_y_leakage": row["blocked_y_leakage"],
            "conversion_to_leakage_ratio": row["conversion_to_leakage_ratio"],
            "matrix_error": row["matrix_error"],
            "geometry_family": row["geometry_family"],
            "source_stage": row["source_stage"],
            "source_file": row["source_file"],
        })
    return out


def write_markdown(final_rows: list[dict[str, object]]) -> None:
    all_strict = len(final_rows) == 6 and all(str(row["strict"]) == "true" for row in final_rows)
    weakest_ratio = min(final_rows, key=lambda row: float(row["conversion_to_leakage_ratio"]))
    weakest_tx = min(final_rows, key=lambda row: float(row["selected_x_power"]))
    largest_phase = max(final_rows, key=lambda row: float(row["phase_err_deg"]))
    largest_matrix = max(final_rows, key=lambda row: float(row["matrix_error"]))
    lines = [
        "# Stage11-2I Final H500 LP-APCD Actual Dimer 6-bin Freeze",
        "",
        "This freeze is read-only over existing Stage11-2A through 2H H500 dimer result CSVs.",
        "No FDTD was run, no .fsp was generated, and no K=6 full supercell simulation has been run.",
        "",
        f"all_6_bins_strict = {all_strict}",
        "",
        "| bin | candidate_id | phase | phase_err | Tx | leakage | ratio | matrix_error | strict |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in final_rows:
        lines.append(
            f"| {row['bin_deg']} | {row['candidate_id']} | {row['actual_common_phase_deg']} | "
            f"{row['phase_err_deg']} | {row['selected_x_power']} | {row['blocked_y_leakage']} | "
            f"{row['conversion_to_leakage_ratio']} | {row['matrix_error']} | {row['strict']} |"
        )
    lines.extend([
        "",
        "## Weakest Final Bins",
        "",
        f"- weakest by ratio: {weakest_ratio['bin_deg']} deg, {weakest_ratio['candidate_id']}, ratio={weakest_ratio['conversion_to_leakage_ratio']}.",
        f"- weakest by Tx: {weakest_tx['bin_deg']} deg, {weakest_tx['candidate_id']}, Tx={weakest_tx['selected_x_power']}.",
        f"- largest phase error: {largest_phase['bin_deg']} deg, {largest_phase['candidate_id']}, phase_err={largest_phase['phase_err_deg']}.",
        f"- largest matrix_error: {largest_matrix['bin_deg']} deg, {largest_matrix['candidate_id']}, matrix_error={largest_matrix['matrix_error']}.",
        "",
        "## Stage12 Handoff",
        "",
        f"Ready for Stage12 K=6 analytic/layout/supercell design = {all_strict}.",
        "Boundary: this does not mean K=6 FDTD, phase-gradient supercell FDTD, or LP steering has been completed.",
    ])
    (OUT_DIR / "final_h500_lp_apcd_6bin_library.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates()
    if not candidates:
        raise SystemExit("No H500 dimer candidates found in Stage11-2A through 2H outputs.")
    final_rows, strict_rows, rejected_rows = choose_by_bin(candidates)
    if len(final_rows) != 6:
        raise SystemExit(f"Expected 6 final bins, got {len(final_rows)}.")
    write_csv(OUT_DIR / "final_h500_lp_apcd_6bin_library.csv", final_rows, FINAL_FIELDS)
    write_csv(OUT_DIR / "stage12_handoff_phase_library.csv", handoff_rows(final_rows), HANDOFF_FIELDS)
    write_csv(OUT_DIR / "all_strict_candidates_by_bin.csv", strict_rows, STRICT_FIELDS)
    write_csv(OUT_DIR / "rejected_or_loose_best_by_bin.csv", rejected_rows, STRICT_FIELDS)
    write_markdown(final_rows)
    all_strict = all(row["strict"] == "true" for row in final_rows)
    print(f"candidate_count={len(candidates)}")
    print(f"strict_candidate_count={len(strict_rows)}")
    print(f"all_6_bins_strict={all_strict}")
    print(f"out_dir={OUT_DIR}")
    for row in final_rows:
        print(
            f"bin={row['bin_deg']} case={row['candidate_id']} "
            f"ratio={row['conversion_to_leakage_ratio']} Tx={row['selected_x_power']} "
            f"phase_err={row['phase_err_deg']} strict={row['strict']}"
        )


if __name__ == "__main__":
    main()

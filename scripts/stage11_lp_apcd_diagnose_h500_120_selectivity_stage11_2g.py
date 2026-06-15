from __future__ import annotations

import csv
import math
import re
import statistics
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/stage11_2g_h500_120_selectivity_readonly"

PHASE_BINS = [0, 60, 120, 180, 240, 300]
TARGET_BIN = 120
EPS = 1e-12
CURRENT_120_CASE = "H500DIMER2C_004_B120_x_pair_swap_G60_O-20"

INPUT_PATTERNS = [
    "outputs/blue10k6_lp_apcd_stage11_2a_h500_dimer_validation/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/*fdtd_results*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine/*fdtd_results*.csv",
]

ALL_FIELDS = [
    "candidate_id",
    "source_stage",
    "source_file",
    "geometry_family",
    "placement_type",
    "swap_order",
    "gap_nm",
    "local_offset_nm",
    "source_pair_id",
    "j1_candidate_id",
    "j2_candidate_id",
    "actual_common_phase_deg",
    "nearest_bin_deg",
    "phase_err_to_120_deg",
    "selected_x_power",
    "leakage",
    "ratio",
    "matrix_error",
    "strict_margin_ratio",
    "leakage_budget_for_ratio6",
    "leakage_excess",
    "status",
]

GROUP_FIELDS = [
    "geometry_family",
    "count",
    "best_ratio",
    "median_ratio",
    "best_leakage_excess",
    "best_matrix_error",
    "best_phase_err",
]

RECOMMEND_FIELDS = [
    "rank",
    "candidate_id",
    "source_stage",
    "source_pair_id",
    "geometry_family",
    "actual_common_phase_deg",
    "phase_err_to_120_deg",
    "selected_x_power",
    "leakage",
    "ratio",
    "matrix_error",
    "recommended_patch",
    "reason",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
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


def nearest_phase_bin(phase_deg: float) -> tuple[int, float]:
    nearest = min(PHASE_BINS, key=lambda bin_deg: abs(wrap180(phase_deg - bin_deg)))
    return nearest, abs(wrap180(phase_deg - nearest))


def infer_source_stage(path: Path) -> str:
    text = path.as_posix().lower()
    for stage in ["2a", "2b", "2c", "2d", "2e", "2f"]:
        if f"stage11_{stage}" in text or f"stage11-{stage}" in text:
            return f"Stage11-{stage.upper()}"
    return "unknown"


def infer_geometry(case_id: str, row: dict[str, str]) -> dict[str, str]:
    placement = row.get("placement_type", "")
    if not placement:
        if "diag_pair" in case_id:
            placement = "diag_pair"
        elif "x_pair" in case_id:
            placement = "x_pair"
        elif "y_pair" in case_id:
            placement = "y_pair"
        else:
            placement = "unknown"
    swap = row.get("swap_order", "")
    if not swap:
        if "_noswap_" in case_id:
            swap = "J1-J2"
        elif "_swap_" in case_id:
            swap = "J2-J1"
        else:
            swap = "unknown"
    gap = row.get("gap_nm", "")
    offset = row.get("local_offset_nm", "")
    gap_match = re.search(r"_G(-?\d+(?:p\d+)?)", case_id)
    off_match = re.search(r"_O(-?\d+(?:p\d+)?)", case_id)
    if not gap and gap_match:
        gap = gap_match.group(1).replace("p", ".")
    if not offset and off_match:
        offset = off_match.group(1).replace("p", ".")
    return {
        "placement_type": placement,
        "swap_order": swap,
        "gap_nm": gap,
        "local_offset_nm": offset,
        "geometry_family": f"{placement}_{'swap' if swap == 'J2-J1' else 'noswap' if swap == 'J1-J2' else 'unknown'}",
    }


def normalize_row(row: dict[str, str], path: Path) -> dict[str, object]:
    case_id = row.get("dimer_case_id") or row.get("candidate_id") or row.get("pair_id") or ""
    phase = as_float(row.get("actual_common_phase_deg"))
    if math.isnan(phase):
        phase = as_float(row.get("t_xx_phase_deg", row.get("dimer_output_phase_deg")))
    t_xx = as_float(row.get("t_xx_amp"))
    t_yx = as_float(row.get("t_yx_amp"))
    t_xy = as_float(row.get("t_xy_amp"))
    t_yy = as_float(row.get("t_yy_amp"))
    selected = as_float(row.get("selected_power", row.get("target_x_power")))
    if math.isnan(selected):
        selected = t_xx * t_xx
    leakage = as_float(row.get("blocked_input_total_power", row.get("y_input_total_leak_power")))
    if math.isnan(leakage):
        leakage = t_xy * t_xy + t_yy * t_yy
    ratio = as_float(row.get("projection_selectivity_ratio", row.get("dimer_selectivity_ratio")))
    if math.isnan(ratio):
        ratio = selected / max(leakage, EPS)
    matrix_error = as_float(row.get("matrix_projection_error_norm"))
    if math.isnan(matrix_error):
        cross = t_yx * t_yx
        matrix_error = math.sqrt(max(cross, 0.0) + max(leakage, 0.0)) / max(t_xx, EPS)
    nearest, _ = nearest_phase_bin(phase)
    phase_err_120 = abs(wrap180(phase - TARGET_BIN))
    budget = selected / 6.0
    geom = infer_geometry(case_id, row)
    status = row.get("usable_status") or row.get("actual_dimer_status") or row.get("fdtd_status") or ""
    return {
        "candidate_id": case_id,
        "source_stage": infer_source_stage(path),
        "source_file": path.name,
        **geom,
        "source_pair_id": row.get("source_pair_id", ""),
        "j1_candidate_id": row.get("j1_candidate_id", ""),
        "j2_candidate_id": row.get("j2_candidate_id", ""),
        "actual_common_phase_deg": phase,
        "nearest_bin_deg": nearest,
        "phase_err_to_120_deg": phase_err_120,
        "selected_x_power": selected,
        "leakage": leakage,
        "ratio": ratio,
        "matrix_error": matrix_error,
        "strict_margin_ratio": ratio - 6.0,
        "leakage_budget_for_ratio6": budget,
        "leakage_excess": leakage - budget,
        "status": status,
    }


def formatted(row: dict[str, object]) -> dict[str, object]:
    out = dict(row)
    for key in [
        "actual_common_phase_deg",
        "phase_err_to_120_deg",
        "selected_x_power",
        "leakage",
        "ratio",
        "matrix_error",
        "strict_margin_ratio",
        "leakage_budget_for_ratio6",
        "leakage_excess",
    ]:
        out[key] = fmt(float(out[key]))
    return out


def discover_input_files() -> list[Path]:
    files: list[Path] = []
    for pattern in INPUT_PATTERNS:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted(set(files))


def load_candidates() -> tuple[list[Path], list[dict[str, object]]]:
    files = discover_input_files()
    rows: list[dict[str, object]] = []
    for path in files:
        for row in read_csv(path):
            norm = normalize_row(row, path)
            if int(norm["nearest_bin_deg"]) == TARGET_BIN or float(norm["phase_err_to_120_deg"]) <= 30.0:
                rows.append(norm)
    return files, rows


def sorted_tables(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    return {
        "top_120_by_ratio": sorted(rows, key=lambda r: (-float(r["ratio"]), float(r["phase_err_to_120_deg"]), float(r["matrix_error"])))[:25],
        "top_120_by_low_leakage_excess": sorted(rows, key=lambda r: (float(r["leakage_excess"]), float(r["phase_err_to_120_deg"]), -float(r["selected_x_power"])))[:25],
        "top_120_by_matrix_error": sorted(rows, key=lambda r: (float(r["matrix_error"]), float(r["phase_err_to_120_deg"]), -float(r["ratio"])))[:25],
        "near_120_high_Tx_low_leakage": sorted(
            rows,
            key=lambda r: (
                float(r["leakage_excess"]),
                -float(r["selected_x_power"]),
                float(r["phase_err_to_120_deg"]),
                -float(r["ratio"]),
            ),
        )[:25],
    }


def grouped_stats(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(str(row["geometry_family"]), []).append(row)
    out: list[dict[str, object]] = []
    for family, members in sorted(groups.items()):
        ratios = [float(row["ratio"]) for row in members]
        out.append({
            "geometry_family": family,
            "count": len(members),
            "best_ratio": fmt(max(ratios)),
            "median_ratio": fmt(statistics.median(ratios)),
            "best_leakage_excess": fmt(min(float(row["leakage_excess"]) for row in members)),
            "best_matrix_error": fmt(min(float(row["matrix_error"]) for row in members)),
            "best_phase_err": fmt(min(float(row["phase_err_to_120_deg"]) for row in members)),
        })
    return out


def recommendations(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    current = next((row for row in rows if row["candidate_id"] == CURRENT_120_CASE), None)
    current_excess = float(current["leakage_excess"]) if current else math.inf
    donor_pool = [
        row for row in rows
        if row["candidate_id"] != CURRENT_120_CASE
        and float(row["leakage_excess"]) < current_excess
        and float(row["selected_x_power"]) >= 0.10
        and float(row["phase_err_to_120_deg"]) <= 30.0
    ]
    if len(donor_pool) < 12:
        donor_pool.extend(
            row for row in rows
            if row["candidate_id"] != CURRENT_120_CASE and row not in donor_pool
        )
    ranked = sorted(
        donor_pool,
        key=lambda r: (
            float(r["leakage_excess"]),
            float(r["matrix_error"]),
            float(r["phase_err_to_120_deg"]),
            -float(r["selected_x_power"]),
        ),
    )
    recs: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in ranked:
        key = (str(row["candidate_id"]), str(row["geometry_family"]))
        if key in seen:
            continue
        seen.add(key)
        patch = "120-only micro-rescue: derive new H500 dimer variants around this donor; vary gap +/-10 nm and offset +/-10 nm, no K=6."
        reason = "lower leakage budget pressure" if float(row["leakage_excess"]) < 0 else "best available near-120 donor, but leakage still above ratio-6 budget"
        recs.append({
            "rank": len(recs) + 1,
            "candidate_id": row["candidate_id"],
            "source_stage": row["source_stage"],
            "source_pair_id": row["source_pair_id"],
            "geometry_family": row["geometry_family"],
            "actual_common_phase_deg": fmt(float(row["actual_common_phase_deg"])),
            "phase_err_to_120_deg": fmt(float(row["phase_err_to_120_deg"])),
            "selected_x_power": fmt(float(row["selected_x_power"])),
            "leakage": fmt(float(row["leakage"])),
            "ratio": fmt(float(row["ratio"])),
            "matrix_error": fmt(float(row["matrix_error"])),
            "recommended_patch": patch,
            "reason": reason,
        })
        if len(recs) >= 12:
            break
    return recs


def answer_bottleneck(current: dict[str, object] | None) -> str:
    if not current:
        return "Current 120 best case was not found in the mined rows."
    selected = float(current["selected_x_power"])
    leakage = float(current["leakage"])
    budget = float(current["leakage_budget_for_ratio6"])
    excess = float(current["leakage_excess"])
    if excess > 0:
        return (
            f"The current 120 best is limited more by high blocked-y leakage than by low Tx: "
            f"Tx={selected:.6f}, leakage={leakage:.6f}, ratio-6 leakage budget={budget:.6f}, "
            f"excess={excess:.6f}."
        )
    return (
        f"The current 120 best already meets the ratio-6 leakage budget; any remaining limitation is not leakage dominated. "
        f"Tx={selected:.6f}, leakage={leakage:.6f}, budget={budget:.6f}."
    )


def write_markdown(files: list[Path], rows: list[dict[str, object]], tables: dict[str, list[dict[str, object]]], groups: list[dict[str, object]], recs: list[dict[str, object]]) -> None:
    current = next((row for row in rows if row["candidate_id"] == CURRENT_120_CASE), None)
    better_leak = [
        row for row in rows
        if current and float(row["leakage_excess"]) < float(current["leakage_excess"])
        and float(row["phase_err_to_120_deg"]) > float(current["phase_err_to_120_deg"])
    ]
    best_group = sorted(groups, key=lambda g: (float(g["best_leakage_excess"]), -float(g["best_ratio"])))[0] if groups else None
    lines = [
        "# Stage11-2G H500 120 Selectivity Read-only Diagnostic",
        "",
        "This is a read-only diagnostic over existing H500 dimer FDTD result CSVs. No FDTD was run, no .fsp was generated, and no K=6/metagrating tools were touched.",
        "",
        "## Inputs",
    ]
    lines.extend(f"- {path.relative_to(REPO_ROOT).as_posix()}" for path in files)
    lines.extend([
        "",
        "## Bottleneck Answer",
        "",
        answer_bottleneck(current),
        "",
        f"Cases mined near 120 deg = {len(rows)}.",
        f"Donor cases with lower leakage_excess than current 120 but worse phase = {len(better_leak)}.",
        "",
        "## Geometry Family Recommendation",
        "",
    ])
    if best_group:
        lines.append(
            f"Refine `{best_group['geometry_family']}` first for a later 120-only micro-rescue: "
            f"it has best leakage_excess={best_group['best_leakage_excess']}, best ratio={best_group['best_ratio']}, "
            f"best matrix_error={best_group['best_matrix_error']}."
        )
    else:
        lines.append("No geometry family could be recommended because no near-120 rows were found.")
    lines.extend([
        "",
        "## Top Recommendations For Later FDTD, Not Run Here",
        "",
        "| rank | candidate_id | family | phase_err | Tx | leakage | ratio | matrix_error | reason |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ])
    for rec in recs:
        lines.append(
            f"| {rec['rank']} | {rec['candidate_id']} | {rec['geometry_family']} | {rec['phase_err_to_120_deg']} | "
            f"{rec['selected_x_power']} | {rec['leakage']} | {rec['ratio']} | {rec['matrix_error']} | {rec['reason']} |"
        )
    lines.extend([
        "",
        "## Tables Written",
    ])
    for name in tables:
        lines.append(f"- {name}.csv")
    lines.extend([
        "- all_near_120_candidates.csv",
        "- grouped_by_geometry_family.csv",
        "- recommended_next_120_micro_rescue_candidates.csv",
        "",
        "Boundary: recommendations are for a later 120-only micro-rescue. They are not executed in Stage11-2G.",
    ])
    (OUT_DIR / "h500_120_selectivity_readonly_summary_stage11_2g.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files, rows = load_candidates()
    if not files:
        raise SystemExit("No Stage11-2A through 2F H500 dimer result CSV files were found.")
    rows_fmt = [formatted(row) for row in sorted(rows, key=lambda r: (float(r["phase_err_to_120_deg"]), -float(r["ratio"])))]
    write_csv(OUT_DIR / "all_near_120_candidates.csv", rows_fmt, ALL_FIELDS)
    tables = sorted_tables(rows)
    for name, table_rows in tables.items():
        write_csv(OUT_DIR / f"{name}.csv", [formatted(row) for row in table_rows], ALL_FIELDS)
    groups = grouped_stats(rows)
    write_csv(OUT_DIR / "grouped_by_geometry_family.csv", groups, GROUP_FIELDS)
    recs = recommendations(rows)
    write_csv(OUT_DIR / "recommended_next_120_micro_rescue_candidates.csv", recs, RECOMMEND_FIELDS)
    write_markdown(files, rows, tables, groups, recs)
    current = next((row for row in rows if row["candidate_id"] == CURRENT_120_CASE), None)
    print(f"input_file_count={len(files)}")
    print(f"near_120_candidate_count={len(rows)}")
    if current:
        print(f"current_120_leakage_excess={fmt(float(current['leakage_excess']))}")
        print(f"current_120_ratio={fmt(float(current['ratio']))}")
    print(f"recommendation_count={len(recs)}")
    print(f"out_dir={OUT_DIR}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import math
import re
import statistics
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/stage11_3a_h500_lp_spectral_robust_phase_library_audit"
PHASE_BINS = [0, 60, 120, 180, 240, 300]
WAVELENGTHS = [447, 448, 449, 450, 451, 452, 453]
EPS = 1e-12

CANDIDATE_PATTERNS = [
    "outputs/blue10k6_lp_apcd_stage11_2a_h500_dimer_validation/*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2b_h500_dimer_rebin/*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/*.csv",
    "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine/*.csv",
    "outputs/stage11_2g_h500_120_selectivity_readonly/*.csv",
    "outputs/stage11_2h_h500_120_y_pair_micro_rescue/*.csv",
    "outputs/stage11_2i_h500_lp_actual_dimer_6bin_freeze/*.csv",
    "outputs/stage12_10a_h500_lp_240bin_single_dimer_refinement/*.csv",
    "outputs/stage12_10b_h500_lp_240bin_broad_family_scout/*.csv",
    "outputs/stage12_10c_h500_lp_180bin_single_dimer_refinement/*.csv",
    "outputs/stage12_10d_h500_lp_300bin_single_dimer_refinement/*.csv",
    "outputs/stage12_11a_h500_lp_k6_phase_origin_search/*.csv",
]

SPECTRAL_RESULTS = REPO_ROOT / "outputs/stage12_12a_h500_lp_6bin_spectral_audit/stage12_12a_6bin_spectral_results.csv"
WEIGHTED_RESULTS = REPO_ROOT / "outputs/stage12_12a_h500_lp_6bin_spectral_audit/stage12_12a_weighted_6bin_metrics.csv"
WINDOW_RESULTS = REPO_ROOT / "outputs/stage12_12a2_h500_lp_6bin_narrow_window_acceptance/stage12_12a2_window_acceptance_metrics.csv"
LONG_WL_RESULTS = REPO_ROOT / "outputs/stage12_12a2_h500_lp_6bin_narrow_window_acceptance/stage12_12a2_240bin_long_wavelength_failure.csv"

POOL_FIELDS = [
    "candidate_id", "source_stage", "geometry_family", "intended_bin_deg", "actual_phase_450_deg",
    "nearest_bin_450_deg", "Tx_450", "leakage_450", "ratio_450", "matrix_error_450",
    "geometry_legal", "minimum_clearance_nm", "result_csv", "source_file",
]
for metric in ["ratio", "Tx", "leakage", "phase"]:
    POOL_FIELDS.extend(f"{metric}_{wl}" for wl in WAVELENGTHS)
POOL_FIELDS.extend([
    "min_ratio_449_451", "min_ratio_447_453", "weighted_ratio_FWHM_2nm", "weighted_ratio_FWHM_3nm",
    "weighted_ratio_FWHM_6nm", "phase_slope_449_451", "phase_slope_447_453",
    "long_wavelength_collapse_flag", "robust_score", "rescue_priority",
])

SUMMARY_FIELDS = [
    "bin_deg", "candidate_count", "spectral_candidate_count", "best_ratio_450", "best_min_ratio_449_451",
    "best_min_ratio_447_453", "collapse_count", "best_robust_score", "notes",
]




def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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
        if value is None or str(value).strip() == "" or str(value).lower() == "nan":
            return default
        return float(value)
    except Exception:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def nearest_bin(phase_deg: float) -> tuple[int, float]:
    nearest = min(PHASE_BINS, key=lambda b: abs(wrap180(phase_deg - b)))
    return nearest, abs(wrap180(phase_deg - nearest))


def infer_stage(path: Path) -> str:
    text = path.as_posix().lower()
    for stage in ["stage11_2i", "stage12_10a", "stage12_10b", "stage12_10c", "stage12_10d", "stage12_11a", "stage12_12a", "stage12_12a2"]:
        if stage in text:
            return stage.replace("_", "-").upper()
    return "unknown"


def infer_geometry(candidate_id: str, row: dict[str, str]) -> str:
    if row.get("geometry_family"):
        return row["geometry_family"]
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
    if "noswap" in candidate_id:
        swap = "noswap"
    elif "swap" in candidate_id:
        swap = "swap"
    else:
        swap = "unknown"
    return f"{placement}_{swap}"


def candidate_id(row: dict[str, str]) -> str:
    return row.get("candidate_id") or row.get("dimer_case_id") or row.get("source_pair_id") or ""


def first_float(row: dict[str, str], names: list[str]) -> float:
    for name in names:
        value = flt(row.get(name))
        if not math.isnan(value):
            return value
    return math.nan


def normalize_candidate(row: dict[str, str], path: Path) -> dict[str, object] | None:
    cid = candidate_id(row)
    if not cid or cid.lower() in {"candidate_id", "dimer_case_id"}:
        return None
    phase = first_float(row, ["actual_common_phase_deg", "phase_deg", "phase_mod_360_deg", "selected_channel_phase_deg", "t_xx_phase_deg", "dimer_output_phase_deg"])
    nearest_450 = first_float(row, ["nearest_bin_deg", "nearest_60bin_deg"])
    if math.isnan(nearest_450) and not math.isnan(phase):
        nearest_450, _ = nearest_bin(phase)
    intended = first_float(row, ["bin_deg", "phase_bin_deg", "target_actual_bin_deg", "static_original_bin_deg"])
    tx = first_float(row, ["Tx", "selected_x_power", "target_x_power", "target_conversion"])
    leakage = first_float(row, ["blocked_y_leakage", "leakage", "opposite_spin_or_yLP_leakage", "estimated_leakage", "blocked_y_total_leakage", "y_input_total_leak_power"])
    ratio = first_float(row, ["conversion_to_leakage_ratio", "ratio", "dimer_selectivity_ratio", "projection_selectivity_ratio"])
    matrix = first_float(row, ["matrix_error", "matrix_projection_error_norm"])
    return {
        "candidate_id": cid,
        "source_stage": row.get("source_stage") or infer_stage(path),
        "geometry_family": infer_geometry(cid, row),
        "intended_bin_deg": int(intended) if not math.isnan(intended) else "",
        "actual_phase_450_deg": phase,
        "nearest_bin_450_deg": int(nearest_450) if not math.isnan(nearest_450) else "",
        "Tx_450": tx,
        "leakage_450": leakage,
        "ratio_450": ratio,
        "matrix_error_450": matrix,
        "geometry_legal": row.get("geometry_legal", ""),
        "minimum_clearance_nm": row.get("minimum_clearance_nm", ""),
        "result_csv": row.get("result_csv", ""),
        "source_file": relpath(path),
    }


def discover_candidate_files() -> list[Path]:
    files: list[Path] = []
    for pattern in CANDIDATE_PATTERNS:
        files.extend(REPO_ROOT.glob(pattern))
    keep = []
    for path in sorted(set(files)):
        name = path.name.lower()
        if any(token in name for token in ["plan", "geometry", "failed", "cluster", "comparison", "origin_scan", "coverage_map"]):
            continue
        keep.append(path)
    return keep


def aggregate_base_pool() -> dict[str, dict[str, object]]:
    pool: dict[str, dict[str, object]] = {}
    for path in discover_candidate_files():
        for row in read_csv(path):
            norm = normalize_candidate(row, path)
            if not norm:
                continue
            cid = str(norm["candidate_id"])
            old = pool.get(cid)
            old_score = -1 if old is None else sum(str(old.get(k, "")) != "" for k in POOL_FIELDS[:14])
            new_score = sum(str(norm.get(k, "")) != "" for k in POOL_FIELDS[:14])
            if old is None or new_score >= old_score:
                pool[cid] = norm
    return pool


def load_spectral_metrics() -> dict[str, dict[str, object]]:
    spectral: dict[str, dict[str, object]] = {}
    for row in read_csv(SPECTRAL_RESULTS):
        cid = row.get("candidate_id", "")
        wl = int(flt(row.get("wavelength_nm"), -1))
        if not cid or wl not in WAVELENGTHS:
            continue
        slot = spectral.setdefault(cid, {})
        slot[f"ratio_{wl}"] = first_float(row, ["conversion_to_leakage_ratio", "ratio"])
        slot[f"Tx_{wl}"] = first_float(row, ["Tx", "target_conversion", "selected_x_power", "target_x_power"])
        slot[f"leakage_{wl}"] = first_float(row, ["blocked_y_total_leakage", "blocked_y_leakage", "leakage", "y_input_total_leak_power"])
        slot[f"phase_{wl}"] = first_float(row, ["selected_channel_phase_deg", "actual_common_phase_deg", "t_xx_phase_deg", "phase_deg"])
    return spectral


def values(metrics: dict[str, object], prefix: str, wavelengths: list[int]) -> list[float]:
    return [flt(metrics.get(f"{prefix}_{wl}")) for wl in wavelengths if not math.isnan(flt(metrics.get(f"{prefix}_{wl}")))]


def weighted_average(metrics: dict[str, object], prefix: str, fwhm_nm: float) -> float:
    sigma = fwhm_nm / 2.354820045
    pairs = []
    for wl in WAVELENGTHS:
        val = flt(metrics.get(f"{prefix}_{wl}"))
        if math.isnan(val):
            continue
        weight = math.exp(-0.5 * ((wl - 450.0) / sigma) ** 2)
        pairs.append((weight, val))
    if not pairs:
        return math.nan
    return sum(w * v for w, v in pairs) / sum(w for w, _ in pairs)


def phase_slope(metrics: dict[str, object], low: int, high: int) -> float:
    lo = flt(metrics.get(f"phase_{low}"))
    hi = flt(metrics.get(f"phase_{high}"))
    if math.isnan(lo) or math.isnan(hi):
        return math.nan
    return wrap180(hi - lo) / (high - low)


def long_wavelength_collapse(metrics: dict[str, object]) -> bool:
    r450 = flt(metrics.get("ratio_450"))
    r451 = flt(metrics.get("ratio_451"))
    r452 = flt(metrics.get("ratio_452"))
    r453 = flt(metrics.get("ratio_453"))
    if not math.isnan(r451) and r451 < 6:
        return True
    if not math.isnan(r452) and r452 < 3:
        return True
    if not math.isnan(r453) and r453 < 1:
        return True
    if not math.isnan(r450) and not math.isnan(r452) and r450 > 0 and r452 / r450 < 0.25:
        return True
    return False


def robust_score_fields(metrics: dict[str, object]) -> dict[str, object]:
    m449 = values(metrics, "ratio", [449, 450, 451])
    mall = values(metrics, "ratio", WAVELENGTHS)
    out = {
        "min_ratio_449_451": min(m449) if m449 else math.nan,
        "min_ratio_447_453": min(mall) if mall else math.nan,
        "weighted_ratio_FWHM_2nm": weighted_average(metrics, "ratio", 2),
        "weighted_ratio_FWHM_3nm": weighted_average(metrics, "ratio", 3),
        "weighted_ratio_FWHM_6nm": weighted_average(metrics, "ratio", 6),
        "phase_slope_449_451": phase_slope(metrics, 449, 451),
        "phase_slope_447_453": phase_slope(metrics, 447, 453),
        "long_wavelength_collapse_flag": long_wavelength_collapse(metrics),
    }
    min_ratio = flt(out["min_ratio_449_451"], 0)
    w2 = flt(out["weighted_ratio_FWHM_2nm"], 0)
    w3 = flt(out["weighted_ratio_FWHM_3nm"], 0)
    phase_penalty = min(abs(flt(out["phase_slope_449_451"], 0)) / 30.0, 2.0)
    tail_penalty = 3.0 if out["long_wavelength_collapse_flag"] else 0.0
    out["robust_score"] = min(min_ratio, w2, w3) - phase_penalty - tail_penalty
    return out


def classify_rescue_priority(row: dict[str, object]) -> str:
    intended = row.get("intended_bin_deg")
    nearest = row.get("nearest_bin_450_deg")
    collapse = bool(row.get("long_wavelength_collapse_flag"))
    min_ratio = flt(row.get("min_ratio_449_451"))
    if collapse and (intended == 240 or nearest == 240):
        return "priority_1_240_long_wavelength_collapse"
    if intended == 120 or nearest == 120:
        if not math.isnan(min_ratio) and min_ratio < 10:
            return "priority_2_120_secondary_risk"
        return "monitor_120_secondary_risk"
    if collapse:
        return "spectral_collapse_watch"
    if not math.isnan(min_ratio) and min_ratio >= 6:
        return "robust_seed_candidate"
    return "center_only_or_unsampled"


def classify_ml_readiness(spectral_count: int) -> tuple[str, str]:
    if spectral_count < 200:
        return "not_ready", "Spectral samples are below 200; use rule-based audit and targeted FDTD first."
    if spectral_count < 500:
        return "ml_lite_pilot_possible", "Gaussian process, random forest, or XGBoost may help triage targeted candidates."
    return "ml_lite_ready", "ML-lite is reasonable; full DenseNet/GAN/VAE still needs a larger curated dataset."


def build_pool() -> list[dict[str, object]]:
    pool = aggregate_base_pool()
    spectral = load_spectral_metrics()
    for cid, metrics in spectral.items():
        base = pool.setdefault(cid, {"candidate_id": cid, "source_stage": "STAGE12-12A", "geometry_family": infer_geometry(cid, {}), "source_file": relpath(SPECTRAL_RESULTS)})
        base.update(metrics)
        if base.get("actual_phase_450_deg", "") in ["", None] and not math.isnan(flt(metrics.get("phase_450"))):
            base["actual_phase_450_deg"] = metrics["phase_450"]
        if base.get("nearest_bin_450_deg", "") in ["", None] and not math.isnan(flt(metrics.get("phase_450"))):
            base["nearest_bin_450_deg"] = nearest_bin(float(metrics["phase_450"]))[0]
        for old, new in [("Tx_450", "Tx_450"), ("leakage_450", "leakage_450"), ("ratio_450", "ratio_450")]:
            if base.get(old, "") in ["", None] and new in metrics:
                base[old] = metrics[new]
        base.update(robust_score_fields(metrics))
    for row in pool.values():
        row.setdefault("geometry_legal", "")
        row.setdefault("minimum_clearance_nm", "")
        row.setdefault("result_csv", "")
        row.setdefault("source_file", "")
        for field in POOL_FIELDS:
            row.setdefault(field, "")
        row["rescue_priority"] = classify_rescue_priority(row)
    return list(pool.values())


def format_pool_row(row: dict[str, object]) -> dict[str, object]:
    out = dict(row)
    for field in POOL_FIELDS:
        if isinstance(out.get(field), float):
            out[field] = fmt(float(out[field]))
    return out


def spectral_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for b in PHASE_BINS:
        members = [r for r in rows if r.get("nearest_bin_450_deg") == b or r.get("intended_bin_deg") == b]
        spectral = [r for r in members if r.get("ratio_449") not in ["", None]]
        ratios450 = values_from_rows(members, "ratio_450")
        min449 = values_from_rows(spectral, "min_ratio_449_451")
        minall = values_from_rows(spectral, "min_ratio_447_453")
        scores = values_from_rows(spectral, "robust_score")
        collapse_count = sum(1 for r in spectral if bool(r.get("long_wavelength_collapse_flag")))
        notes = "dominant failure bin" if b == 240 and collapse_count else "secondary risk watch" if b == 120 else ""
        out.append({
            "bin_deg": b,
            "candidate_count": len(members),
            "spectral_candidate_count": len(spectral),
            "best_ratio_450": fmt(max(ratios450) if ratios450 else math.nan),
            "best_min_ratio_449_451": fmt(max(min449) if min449 else math.nan),
            "best_min_ratio_447_453": fmt(max(minall) if minall else math.nan),
            "collapse_count": collapse_count,
            "best_robust_score": fmt(max(scores) if scores else math.nan),
            "notes": notes,
        })
    return out


def values_from_rows(rows: list[dict[str, object]], field: str) -> list[float]:
    return [flt(r.get(field)) for r in rows if not math.isnan(flt(r.get(field)))]


def read_window_rows() -> list[dict[str, str]]:
    return read_csv(WINDOW_RESULTS)


def diagnose_failure(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> dict[str, object]:
    windows = read_window_rows()
    weakest = next((r for r in windows if r.get("window_nm") == "449-451"), windows[0] if windows else {})
    bin240 = next((r for r in summary if r["bin_deg"] == 240), {})
    bin120 = next((r for r in summary if r["bin_deg"] == 120), {})
    return {
        "dominant_failure_bin": weakest.get("weakest_bin", "240"),
        "bin240_min_ratio_449_451": weakest.get("bin240_min_ratio", ""),
        "bin120_min_ratio_449_451": weakest.get("bin120_min_ratio", ""),
        "bin240_collapse_count": bin240.get("collapse_count", 0),
        "bin120_secondary_risk": str(weakest.get("bin120_stable", "")).lower() != "true" or flt(weakest.get("bin120_min_ratio"), math.inf) < 10,
    }


def write_md_files(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    diag = diagnose_failure(rows, summary)
    spectral_count = sum(1 for r in rows if r.get("ratio_449") not in ["", None])
    ml_status, ml_note = classify_ml_readiness(spectral_count)
    window_lines = read_window_rows()
    failure = [
        "# Stage11-3A Current Library Failure Diagnosis",
        "",
        "Stage11 is the correct place for phase-library repair. Stage12-12A/A2 are spectral diagnostics feeding back into Stage11, not permission to continue K=6 FDTD.",
        "",
        "The current H500 LP-K6 library is 450-nm center-wavelength optimized. It is not 6-7 nm blue spectral tolerant.",
        "",
        f"Dominant failure bin: {diag['dominant_failure_bin']} deg.",
        f"240 deg 449-451 min ratio: {diag['bin240_min_ratio_449_451']}.",
        f"120 deg secondary risk: {diag['bin120_secondary_risk']}.",
        "Weak bins from existing spectral evidence: 240 deg is dominant; 300 deg and 180 deg also show low 447-453 ratio floors and should be watched during tuple search.",
        "",
        "Observed failure is driven by individual-bin collapse, especially the 240 deg long-wavelength tail, with phase-step errors following the weakened bin rather than a purely uniform group-phase drift. K=6 FDTD should wait until robust single-dimer candidates or robust tuples are identified.",
        "",
        "Window evidence:",
    ]
    failure.extend(f"- {r.get('window_nm')}: acceptable={r.get('acceptable')}, weakest_bin={r.get('weakest_bin')}, bin240_min_ratio={r.get('bin240_min_ratio')}, bin120_min_ratio={r.get('bin120_min_ratio')}" for r in window_lines)
    (OUT_DIR / "stage11_3a_current_library_failure_diagnosis.md").write_text("\n".join(failure) + "\n", encoding="utf-8")

    score = [
        "# Stage11-3A Robust Score Definition",
        "",
        "This is a scoring proposal only; Stage11-3A does not optimize geometry.",
        "",
        "robust_score = min(min_ratio_449_451, weighted_ratio_FWHM_2nm, weighted_ratio_FWHM_3nm) - phase_stability_penalty - long_wavelength_tail_penalty.",
        "",
        "Components:",
        "- min_ratio over 449/450/451 nm: primary narrow blue tolerance floor.",
        "- weighted_ratio_FWHM_2nm and 3nm: narrow spectral source proxies.",
        "- leakage penalty at 451/452/453: captured by long_wavelength_collapse_flag and future leakage terms.",
        "- phase stability penalty: abs(phase_slope_449_451)/30, capped in implementation.",
        "- phase-step compatibility penalty: evaluated in Stage11-3C tuple search, not single-candidate ranking.",
        "- Tx, matrix_error, and clearance/fabrication penalties: included as tie-breakers/rescue filters in later stages.",
    ]
    (OUT_DIR / "stage11_3a_robust_score_definition.md").write_text("\n".join(score) + "\n", encoding="utf-8")

    plan = [
        "# Stage11-3A Rescue Priority Plan",
        "",
        "Next goal is not to rescue the old 240 deg label only. Search for a spectral-robust six-phase dimer library [phi0, phi0+60, ...] mod 360 with stable LP-APCD projection behavior.",
        "",
        "1. Stage11-3B: targeted 240/120 spectral rescue over 449/450/451 nm.",
        "2. Stage11-3C: global phase-offset robust six-bin tuple search.",
        "3. Stage11-3D: freeze a new spectral-robust H500 LP-APCD 6-bin library.",
        "4. Then return to Stage12 for K=6 spectral validation using the new Stage11-3D library.",
        "",
        "K6 FDTD should wait until robust single-dimer candidates or robust tuples are identified.",
        "DBR/dipole Stage13 should wait unless we deliberately proceed under an ultra-narrowband 450-nm RCLED assumption.",
    ]
    (OUT_DIR / "stage11_3a_rescue_priority_plan.md").write_text("\n".join(plan) + "\n", encoding="utf-8")

    ml = [
        "# Stage11-3A ML-lite Readiness Assessment",
        "",
        f"spectral_candidate_count = {spectral_count}",
        f"readiness = {ml_status}",
        ml_note,
        "",
        "ML-lite active learning is not the immediate next step unless enough spectral samples exist. Full DenseNet / GAN / VAE / generative inverse design is premature now.",
        "A Gaussian process, random forest, or XGBoost surrogate may become useful after at least 200-500 single-dimer spectral samples.",
    ]
    (OUT_DIR / "stage11_3a_ml_lite_readiness_assessment.md").write_text("\n".join(ml) + "\n", encoding="utf-8")

    next_rec = [
        "# Stage11-3A Next Recommendation",
        "",
        "Recommended next stage: Stage11-3B targeted 240/120 spectral rescue over 449/450/451 nm.",
        "",
        "Boundaries: read-only/planning only in Stage11-3A; no FDTD, no K6, no DBR, no RCLED, no dipoles, no finite patch, and no optimization were performed.",
    ]
    (OUT_DIR / "stage11_3a_next_recommendation.md").write_text("\n".join(next_rec) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_pool()
    rows.sort(key=lambda r: (str(r.get("rescue_priority", "")), -flt(r.get("robust_score"), -1e9), str(r.get("candidate_id", ""))))
    formatted = [format_pool_row(r) for r in rows]
    write_csv(OUT_DIR / "stage11_3a_candidate_pool.csv", formatted, POOL_FIELDS)
    summary = spectral_summary(rows)
    write_csv(OUT_DIR / "stage11_3a_existing_spectral_candidate_summary.csv", summary, SUMMARY_FIELDS)
    write_md_files(rows, summary)
    diag = diagnose_failure(rows, summary)
    spectral_count = sum(1 for r in rows if r.get("ratio_449") not in ["", None])
    ml_status, _ = classify_ml_readiness(spectral_count)
    print(f"candidate_pool_size={len(rows)}")
    print(f"spectral_candidate_count={spectral_count}")
    print(f"dominant_failure_bin={diag['dominant_failure_bin']}")
    print(f"bin120_secondary_risk={diag['bin120_secondary_risk']}")
    print(f"ml_lite_readiness={ml_status}")
    print(f"out_dir={OUT_DIR}")
    print("boundary=read_only_planning_only_no_fdtd_no_k6_no_dbr_no_rcled_no_dipoles_no_finite_patch_no_optimization")


if __name__ == "__main__":
    main()

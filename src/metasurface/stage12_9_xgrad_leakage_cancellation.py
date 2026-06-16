from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from metasurface.stage12_8_xgrad_refinement import (
    EPS,
    FORWARD_BINS,
    GEOM_FIELDS,
    REJECT_FIELDS,
    RESULT_FIELDS,
    RUN_FIELDS,
    SHIFT_VALUES_NM,
    VARIANT_FIELDS,
    audit_variant,
    bool_from,
    classify_pass,
    clone_rows,
    find_source_plan_rows,
    flt,
    metric_ratio,
    order_contrast,
    read_csv_rows,
    run_one,
    shift_row_x,
    source_to_layout_row,
    top_same_bin_candidates,
    validate_same_bin_substitution,
    variant_score,
    write_csv_rows,
)

OUTPUT_DIR_NAME = "stage12_9_h500_lp_k6_xgrad_leakage_cancellation"
MAX_NEW_VARIANTS = 10
TARGET_ORDER = 1
BASELINE = {
    "variant_id": "variant_000_baseline",
    "variant_type": "official_baseline_reference",
    "x_LP_target_plus1_power": 0.35782382585849376,
    "y_LP_target_plus1_leakage": 0.03070098955871727,
    "target_order_selectivity_ratio": 11.655123531902342,
    "steering_angle_deg": 10.0000000055,
    "x_LP_dominant_order": "+1",
    "y_LP_dominant_leakage_order": "+2",
    "x_LP_order_contrast": 4.4245556829,
    "total_transmission_selectivity_ratio": "not_validated",
    "y_leakage_fraction_in_target_order": "not_available",
    "minimum_clearance_nm": 20.0,
    "geometry_legal": True,
}
STAGE12_8_BEST = {
    "variant_id": "variant_001_sub_bin240_stage12_8_seed",
    "variant_type": "stage12_8_best_reference",
    "x_LP_target_plus1_power": 0.3649581358292434,
    "y_LP_target_plus1_leakage": 0.029614335772574624,
    "target_order_selectivity_ratio": 12.323698178880834,
    "steering_angle_deg": 10.000000005514977,
    "x_LP_dominant_order": "+1",
    "y_LP_dominant_leakage_order": "+2",
    "x_LP_order_contrast": 4.376639428165978,
    "total_transmission_selectivity_ratio": 1.0443087870626842,
    "y_leakage_fraction_in_target_order": "not_available",
    "minimum_clearance_nm": 20.0,
    "geometry_legal": True,
}
RANK_FIELDS = [
    "rank", "variant_id", "variant_type", "x_LP_target_plus1_power", "y_LP_target_plus1_leakage",
    "target_order_selectivity_ratio", "steering_angle_deg", "x_LP_dominant_order",
    "y_LP_dominant_leakage_order", "x_LP_order_contrast", "total_transmission_selectivity_ratio",
    "y_leakage_fraction_in_target_order", "minimum_clearance_nm", "geometry_legal", "hard_pass",
    "preferred_pass", "stretch_pass", "improves_over_baseline", "improves_over_stage12_8_best", "score",
]
COMPARE_FIELDS = [
    "source", "variant_id", "x_LP_target_plus1_power", "y_LP_target_plus1_leakage",
    "target_order_selectivity_ratio", "steering_angle_deg", "hard_pass", "preferred_pass", "stretch_pass",
]

@dataclass(frozen=True)
class Stage12_9Paths:
    strict_pool_csv: Path
    baseline_layout_csv: Path
    stage12_8_ranked_csv: Path
    output_dir: Path
    fdtd_work_dir: Path


def enforce_candidate_limit(variants: list[dict], max_new: int = MAX_NEW_VARIANTS) -> list[dict]:
    refs = [v for v in variants if v.get("status") == "reference"]
    new = [v for v in variants if v.get("status") != "reference"]
    return refs + new[:max_new]


def clearance_rule_ok(audit: dict, min_clearance_nm: float = 15.0) -> bool:
    return bool_from(audit.get("geometry_legal")) and flt(audit.get("minimum_clearance_nm")) >= min_clearance_nm and flt(audit.get("minimum_neighbor_clearance_nm")) >= min_clearance_nm


def leakage_thresholds(x_power: float) -> dict[str, float]:
    return {"ratio20": x_power / 20.0, "ratio30": x_power / 30.0, "ratio50": x_power / 50.0}


def _candidate_by_bin(pool: list[dict], baseline: list[dict], bin_deg: int) -> dict | None:
    base_row = next(r for r in baseline if int(float(r["phase_bin_deg"])) == bin_deg)
    cands = top_same_bin_candidates(pool, bin_deg, base_row["candidate_id"], 1)
    return cands[0] if cands else None


def _substitute_bins(repo_root: Path, baseline: list[dict], pool: list[dict], bins: Iterable[int]) -> list[dict] | None:
    layout = clone_rows(baseline)
    selected = []
    for bin_deg in bins:
        cand = _candidate_by_bin(pool, baseline, bin_deg)
        if not cand or not validate_same_bin_substitution(bin_deg, cand):
            return None
        selected.append((bin_deg, cand))
    sources = find_source_plan_rows(repo_root, [cand["candidate_id"] for _, cand in selected])
    for bin_deg, cand in selected:
        idx = next(i for i, r in enumerate(layout) if int(float(r["phase_bin_deg"])) == bin_deg)
        layout[idx] = source_to_layout_row(layout[idx], cand, sources[cand["candidate_id"]])
    return layout


def _variant_row(variant_id: str, variant_type: str, description: str, layout: list[dict], changed_bins: str, changed_indices: str, shifts: str, notes: str) -> dict:
    return {
        "variant_id": variant_id,
        "variant_type": variant_type,
        "description": description,
        "layout_rows": layout,
        "changed_bins": changed_bins,
        "changed_indices": changed_indices,
        "candidate_ids_by_bin": ";".join(f"{r['phase_bin_deg']}:{r['candidate_id']}" for r in layout),
        "shift_nm_by_index": shifts,
        "planned_fdtd_runs": 2,
        "status": "planned",
        "notes": notes,
    }


def _seed_layout(repo_root: Path, baseline: list[dict], pool: list[dict]) -> list[dict]:
    return _substitute_bins(repo_root, baseline, pool, [240]) or clone_rows(baseline)


def generate_variants(paths: Stage12_9Paths, repo_root: Path | None = None) -> tuple[list[dict], list[dict]]:
    repo_root = repo_root or Path.cwd()
    baseline = read_csv_rows(paths.baseline_layout_csv)
    pool = read_csv_rows(paths.strict_pool_csv)
    rejected: list[dict] = []
    variants: list[dict] = [
        {
            "variant_id": "variant_000_baseline",
            "variant_type": "official_baseline_reference",
            "description": "official Stage12-2 x-gradient baseline reference; no FDTD re-run",
            "layout_rows": clone_rows(baseline),
            "changed_bins": "",
            "changed_indices": "",
            "candidate_ids_by_bin": ";".join(f"{r['phase_bin_deg']}:{r['candidate_id']}" for r in baseline),
            "shift_nm_by_index": "",
            "planned_fdtd_runs": 0,
            "status": "reference",
            "notes": "baseline metrics loaded from Stage12-2",
        }
    ]
    seed = _seed_layout(repo_root, baseline, pool)
    variants.append(
        {
            "variant_id": "variant_001_sub_bin240_stage12_8_seed",
            "variant_type": "stage12_8_best_reference",
            "description": "Stage12-8 best same-bin bin240 substitution seed; no FDTD re-run",
            "layout_rows": seed,
            "changed_bins": "240",
            "changed_indices": "4",
            "candidate_ids_by_bin": ";".join(f"{r['phase_bin_deg']}:{r['candidate_id']}" for r in seed),
            "shift_nm_by_index": "",
            "planned_fdtd_runs": 0,
            "status": "reference",
            "notes": "reference metrics loaded from Stage12-8",
        }
    )

    next_id = 1
    specs = [([240, 180], "multi_sub_240_180"), ([240, 300], "multi_sub_240_300"), ([240, 180, 300], "multi_sub_240_180_300"), ([240, 120], "multi_sub_240_120")]
    for bins, label in specs:
        vid = f"variant_{next_id:03d}_{label}"
        next_id += 1
        try:
            layout = _substitute_bins(repo_root, baseline, pool, bins)
            if layout is None:
                rejected.append({"variant_id": vid, "variant_type": "multi_bin_substitution", "reason": "candidate_missing", "notes": str(bins)})
                continue
            _, audit = audit_variant(layout)
            if clearance_rule_ok(audit):
                indices = ";".join(str(i) for i, r in enumerate(layout) if int(float(r["phase_bin_deg"])) in bins)
                variants.append(_variant_row(vid, "multi_bin_substitution", f"same-bin substitutions for bins {bins}", layout, ";".join(map(str, bins)), indices, "", audit["audit_notes"]))
            else:
                rejected.append({"variant_id": vid, "variant_type": "multi_bin_substitution", "reason": "geometry_illegal_or_clearance_below_15nm", "notes": audit["audit_notes"]})
        except Exception as exc:
            rejected.append({"variant_id": vid, "variant_type": "multi_bin_substitution", "reason": "build_failed", "notes": str(exc)[:500]})

    for dx in [-5.0, 5.0, -10.0, 10.0]:
        layout = clone_rows(seed)
        shift_row_x(layout[4], dx)
        _, audit = audit_variant(layout)
        vid = f"variant_{next_id:03d}_seed_shift_bin240_{dx:+.0f}nm"
        next_id += 1
        if clearance_rule_ok(audit):
            variants.append(_variant_row(vid, "seed_x_micro_shift", f"Stage12-8 seed with bin240 shifted {dx:+.0f} nm along x", layout, "240", "4", f"4:{dx:+.0f}", audit["audit_notes"]))
        else:
            rejected.append({"variant_id": vid, "variant_type": "seed_x_micro_shift", "reason": "geometry_illegal_or_clearance_below_15nm", "notes": audit["audit_notes"]})

    shift_specs = [
        (clone_rows(baseline), [(3, -5.0), (5, 5.0)], "baseline_spread_180_300", "spread 180/240/300 risk region"),
        (clone_rows(baseline), [(3, 5.0), (5, -5.0)], "baseline_compress_180_300", "compress 180/240/300 risk region"),
        (clone_rows(seed), [(3, -5.0), (5, 5.0)], "seed_spread_180_300", "Stage12-8 seed plus spread 180/240/300 risk region"),
    ]
    for layout, moves, label, description in shift_specs:
        vid = f"variant_{next_id:03d}_{label}"
        next_id += 1
        for index, dx in moves:
            shift_row_x(layout[index], dx)
        _, audit = audit_variant(layout)
        if clearance_rule_ok(audit):
            variants.append(_variant_row(vid, "regional_x_micro_shift", description, layout, "180;300" if "seed" not in label else "180;240;300", "3;5", ";".join(f"{i}:{dx:+.0f}" for i, dx in moves), audit["audit_notes"]))
        else:
            rejected.append({"variant_id": vid, "variant_type": "regional_x_micro_shift", "reason": "geometry_illegal_or_clearance_below_15nm", "notes": audit["audit_notes"]})

    return enforce_candidate_limit(variants, MAX_NEW_VARIANTS), rejected


def build_run_matrix(variants: list[dict]) -> list[dict]:
    rows = []
    for variant in variants:
        if variant.get("status") == "reference":
            continue
        for pol in ["x", "y"]:
            rows.append({
                "run_id": f"{variant['variant_id']}_{pol}",
                "variant_id": variant["variant_id"],
                "polarization": pol,
                "run_required": True,
                "gradient_axis": "x",
                "target_order": "x-order +1",
                "status": "planned",
                "notes": "official x-gradient leakage-cancellation plane-wave scout",
            })
    return rows


def reference_rank_row(reference: dict, source_type: str) -> dict:
    row = dict(reference)
    row["score"] = variant_score(row["x_LP_target_plus1_power"], row["y_LP_target_plus1_leakage"], row["target_order_selectivity_ratio"])
    row.update(classify_pass(row))
    row["improves_over_baseline"] = row["target_order_selectivity_ratio"] > BASELINE["target_order_selectivity_ratio"] and row["y_LP_target_plus1_leakage"] < BASELINE["y_LP_target_plus1_leakage"]
    row["improves_over_stage12_8_best"] = row["target_order_selectivity_ratio"] > STAGE12_8_BEST["target_order_selectivity_ratio"] and row["y_LP_target_plus1_leakage"] < STAGE12_8_BEST["y_LP_target_plus1_leakage"]
    row["variant_type"] = source_type
    return row


def summarize_variant(variant: dict, geom_audit: dict, xres: dict, yres: dict) -> dict:
    x = flt(xres.get("target_plus1_power"))
    y = flt(yres.get("target_plus1_power"))
    total_y = flt(yres.get("total_transmission"))
    total_ratio = flt(xres.get("total_transmission")) / max(total_y, EPS)
    y_fraction = y / max(total_y, EPS)
    row = {
        "variant_id": variant["variant_id"],
        "variant_type": variant["variant_type"],
        "x_LP_target_plus1_power": x,
        "y_LP_target_plus1_leakage": y,
        "target_order_selectivity_ratio": metric_ratio(x, y),
        "steering_angle_deg": flt(xres.get("dominant_theta_deg")),
        "x_LP_dominant_order": f"{int(float(xres.get('dominant_order_n', 999))):+d}" if str(xres.get("fdtd_status")) == "ok" else "failed",
        "y_LP_dominant_leakage_order": f"{int(float(yres.get('dominant_order_n', 999))):+d}" if str(yres.get("fdtd_status")) == "ok" else "failed",
        "x_LP_order_contrast": flt(xres.get("order_contrast_plus1_vs_next")),
        "total_transmission_selectivity_ratio": total_ratio,
        "y_leakage_fraction_in_target_order": y_fraction,
        "minimum_clearance_nm": geom_audit["minimum_clearance_nm"],
        "geometry_legal": geom_audit["geometry_legal"],
    }
    row["score"] = variant_score(x, y, row["target_order_selectivity_ratio"])
    row.update(classify_pass(row))
    row["improves_over_baseline"] = row["target_order_selectivity_ratio"] > BASELINE["target_order_selectivity_ratio"] and y < BASELINE["y_LP_target_plus1_leakage"]
    row["improves_over_stage12_8_best"] = row["target_order_selectivity_ratio"] > STAGE12_8_BEST["target_order_selectivity_ratio"] and y < STAGE12_8_BEST["y_LP_target_plus1_leakage"]
    return row


def _best_stage12_9(ranked: list[dict]) -> dict:
    new_rows = [r for r in ranked if r.get("variant_type") not in {"official_baseline_reference", "stage12_8_best_reference"}]
    return new_rows[0] if new_rows else ranked[0]


def rank_stage12_9_rows(rows: list[dict]) -> list[dict]:
    """Rank for leakage cancellation, not just ratio gain from higher x power."""
    ranked = sorted(
        rows,
        key=lambda r: (
            not bool_from(r.get("hard_pass")),
            not bool_from(r.get("improves_over_stage12_8_best")),
            flt(r.get("y_LP_target_plus1_leakage")),
            -flt(r.get("target_order_selectivity_ratio")),
            -flt(r.get("x_LP_target_plus1_power")),
        ),
    )
    for idx, row in enumerate(ranked, 1):
        row["rank"] = idx
    return ranked


def write_summaries(paths: Stage12_9Paths, ranked: list[dict]) -> None:
    best = _best_stage12_9(ranked)
    baseline = next(r for r in ranked if r["variant_id"] == "variant_000_baseline")
    stage12_8 = next(r for r in ranked if r["variant_id"] == "variant_001_sub_bin240_stage12_8_seed")
    hard = bool_from(best.get("hard_pass"))
    preferred = bool_from(best.get("preferred_pass"))
    stretch = bool_from(best.get("stretch_pass"))
    cmp_rows = []
    for source, row in [("Stage12-2 official baseline", baseline), ("Stage12-8 best", stage12_8), ("Stage12-9 best", best)]:
        cmp_rows.append({"source": source, **{k: row.get(k, "") for k in COMPARE_FIELDS if k != "source"}})
    write_csv_rows(cmp_rows, paths.output_dir / "stage12_9_baseline_stage12_8_best_stage12_9_best_comparison.csv", COMPARE_FIELDS)
    summary = [
        "# Stage12-9 Best Variant Summary",
        "",
        f"- Stage12-9 improves over official baseline: {bool_from(best.get('improves_over_baseline'))}.",
        f"- Stage12-9 improves over Stage12-8 best: {bool_from(best.get('improves_over_stage12_8_best'))}.",
        f"- Best variant ID: {best['variant_id']}.",
        f"- Best x-LP +1 power: {best['x_LP_target_plus1_power']}.",
        f"- Best y-LP +1 leakage: {best['y_LP_target_plus1_leakage']}.",
        f"- Best target_order_selectivity_ratio: {best['target_order_selectivity_ratio']}.",
        f"- Hard pass: {hard}.",
        f"- Preferred pass: {preferred}.",
        f"- Stretch pass: {stretch}.",
        f"- Replace official baseline in a later Stage12-10 freeze: {hard}.",
        f"- Another scout justified: {not preferred}.",
        "- Boundary: plane-wave x-gradient only; not dipole-source validation.",
        "- Boundary: no dipoles, no CP, no y-gradient, no H600/H700, no reverse layout.",
    ]
    (paths.output_dir / "stage12_9_best_variant_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    thresholds = leakage_thresholds(max(flt(best["x_LP_target_plus1_power"]), flt(stage12_8["x_LP_target_plus1_power"]), flt(baseline["x_LP_target_plus1_power"])))
    interp = [
        "# Stage12-9 Leakage Cancellation Interpretation",
        "",
        "Stage12-9 moved from single-bin substitution to supercell-level same-bin substitutions and local x-position micro-shifts around the 180/240/300 risk region.",
        f"For the best observed x power, approximate y-LP target-order leakage thresholds are: ratio >=20 needs <= {thresholds['ratio20']}, ratio >=30 needs <= {thresholds['ratio30']}, ratio >=50 needs <= {thresholds['ratio50']}.",
        f"Best y-LP target x-order +1 leakage is {best['y_LP_target_plus1_leakage']}.",
        "If no large jump is found, the bottleneck likely requires a new higher-margin phase library or supercell-level co-design, not small local tuning.",
    ]
    (paths.output_dir / "stage12_9_leakage_cancellation_interpretation.md").write_text("\n".join(interp) + "\n", encoding="utf-8")
    rec = [
        "# Stage12-9 Next Recommendation",
        "",
        "Do not replace the official Stage12 baseline unless a Stage12-9/Stage12-10 candidate satisfies the hard pass criteria.",
        "If stronger suppression is still required before Stage13, prioritize a higher-margin six-bin phase library or explicit supercell-level co-design.",
        "Keep Stage13 reserved for dipole-source / MicroLED coupling after the plane-wave convention is frozen.",
    ]
    (paths.output_dir / "stage12_9_next_recommendation.md").write_text("\n".join(rec) + "\n", encoding="utf-8")


def run_stage12_9(paths: Stage12_9Paths, lumapi, runtime, repo_root: Path | None = None) -> dict:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    variants, rejected = generate_variants(paths, repo_root)
    plan_rows = [{k: variant.get(k, "") for k in VARIANT_FIELDS} for variant in variants]
    write_csv_rows(plan_rows, paths.output_dir / "stage12_9_candidate_variant_plan.csv", VARIANT_FIELDS)
    geom_rows = []
    geom_by_id = {}
    for variant in variants:
        _, geom_audit = audit_variant(variant["layout_rows"])
        geom_by_id[variant["variant_id"]] = geom_audit
        geom_rows.append({"variant_id": variant["variant_id"], **geom_audit})
    write_csv_rows(geom_rows, paths.output_dir / "stage12_9_candidate_geometry_audit.csv", GEOM_FIELDS)
    run_matrix = build_run_matrix(variants)
    write_csv_rows(run_matrix, paths.output_dir / "stage12_9_fdtd_run_matrix.csv", RUN_FIELDS)
    results = []
    ranked = [reference_rank_row(BASELINE, "official_baseline_reference"), reference_rank_row(STAGE12_8_BEST, "stage12_8_best_reference")]
    for variant in [v for v in variants if v.get("status") != "reference"]:
        xres = run_one(lumapi, runtime, variant, "x", paths)
        results.append(xres)
        write_csv_rows(results, paths.output_dir / "stage12_9_fdtd_results.csv", RESULT_FIELDS)
        yres = run_one(lumapi, runtime, variant, "y", paths)
        results.append(yres)
        write_csv_rows(results, paths.output_dir / "stage12_9_fdtd_results.csv", RESULT_FIELDS)
        if xres.get("fdtd_status") == "ok" and yres.get("fdtd_status") == "ok":
            ranked.append(summarize_variant(variant, geom_by_id[variant["variant_id"]], xres, yres))
        else:
            rejected.append({"variant_id": variant["variant_id"], "variant_type": variant["variant_type"], "reason": "fdtd_failed", "notes": (str(xres.get("notes", "")) + str(yres.get("notes", "")))[:600]})
    ranked = rank_stage12_9_rows(ranked)
    write_csv_rows(ranked, paths.output_dir / "stage12_9_ranked_variants.csv", RANK_FIELDS)
    write_csv_rows(rejected, paths.output_dir / "stage12_9_failed_or_rejected_variants.csv", REJECT_FIELDS)
    write_summaries(paths, ranked)
    best = _best_stage12_9(ranked)
    return {
        "output_dir": str(paths.output_dir),
        "new_candidate_variants": len([v for v in variants if v.get("status") != "reference"]),
        "new_fdtd_runs": len(run_matrix),
        "best_variant_id": best["variant_id"],
        "baseline_ratio": BASELINE["target_order_selectivity_ratio"],
        "stage12_8_best_ratio": STAGE12_8_BEST["target_order_selectivity_ratio"],
        "best_ratio": best["target_order_selectivity_ratio"],
        "baseline_y_leakage": BASELINE["y_LP_target_plus1_leakage"],
        "stage12_8_best_y_leakage": STAGE12_8_BEST["y_LP_target_plus1_leakage"],
        "best_y_leakage": best["y_LP_target_plus1_leakage"],
        "baseline_x_power": BASELINE["x_LP_target_plus1_power"],
        "stage12_8_best_x_power": STAGE12_8_BEST["x_LP_target_plus1_power"],
        "best_x_power": best["x_LP_target_plus1_power"],
        "hard_pass": best["hard_pass"],
        "preferred_pass": best["preferred_pass"],
        "stretch_pass": best["stretch_pass"],
        "best_gui_fsp_generated": False,
    }


def summarize_existing_results(paths: Stage12_9Paths, repo_root: Path | None = None) -> dict:
    """Rebuild ranking and summaries from completed FDTD CSVs without new simulations."""
    variants, rejected = generate_variants(paths, repo_root)
    geom_by_id = {}
    for variant in variants:
        _, geom_audit = audit_variant(variant["layout_rows"])
        geom_by_id[variant["variant_id"]] = geom_audit
    result_rows = read_csv_rows(paths.output_dir / "stage12_9_fdtd_results.csv")
    by_run = {(row.get("variant_id"), row.get("polarization")): row for row in result_rows}
    ranked = [reference_rank_row(BASELINE, "official_baseline_reference"), reference_rank_row(STAGE12_8_BEST, "stage12_8_best_reference")]
    for variant in [v for v in variants if v.get("status") != "reference"]:
        xres = by_run.get((variant["variant_id"], "x"))
        yres = by_run.get((variant["variant_id"], "y"))
        if xres and yres and xres.get("fdtd_status") == "ok" and yres.get("fdtd_status") == "ok":
            ranked.append(summarize_variant(variant, geom_by_id[variant["variant_id"]], xres, yres))
        else:
            rejected.append({"variant_id": variant["variant_id"], "variant_type": variant["variant_type"], "reason": "missing_existing_fdtd_result", "notes": "summarize_existing_results did not rerun FDTD"})
    ranked = rank_stage12_9_rows(ranked)
    write_csv_rows(ranked, paths.output_dir / "stage12_9_ranked_variants.csv", RANK_FIELDS)
    write_csv_rows(rejected, paths.output_dir / "stage12_9_failed_or_rejected_variants.csv", REJECT_FIELDS)
    write_summaries(paths, ranked)
    best = _best_stage12_9(ranked)
    return {
        "output_dir": str(paths.output_dir),
        "new_candidate_variants": len([v for v in variants if v.get("status") != "reference"]),
        "new_fdtd_runs": 0,
        "best_variant_id": best["variant_id"],
        "baseline_ratio": BASELINE["target_order_selectivity_ratio"],
        "stage12_8_best_ratio": STAGE12_8_BEST["target_order_selectivity_ratio"],
        "best_ratio": best["target_order_selectivity_ratio"],
        "baseline_y_leakage": BASELINE["y_LP_target_plus1_leakage"],
        "stage12_8_best_y_leakage": STAGE12_8_BEST["y_LP_target_plus1_leakage"],
        "best_y_leakage": best["y_LP_target_plus1_leakage"],
        "baseline_x_power": BASELINE["x_LP_target_plus1_power"],
        "stage12_8_best_x_power": STAGE12_8_BEST["x_LP_target_plus1_power"],
        "best_x_power": best["x_LP_target_plus1_power"],
        "hard_pass": best["hard_pass"],
        "preferred_pass": best["preferred_pass"],
        "stretch_pass": best["stretch_pass"],
        "best_gui_fsp_generated": False,
    }

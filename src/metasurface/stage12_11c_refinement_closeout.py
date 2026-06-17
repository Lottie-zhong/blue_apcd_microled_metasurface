from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_k6_fdtd import flt, read_csv_rows, write_csv_rows

OUTPUT_DIR_NAME = "stage12_11c_h500_lp_k6_refinement_closeout"

BASELINE_METRICS = {"stage": "Stage12-2", "label": "official_x_gradient_baseline", "x_LP_target_plus1_power": 0.35782382585849376, "y_LP_target_plus1_leakage": 0.03070098955871727, "target_order_selectivity_ratio": 11.655123531902342, "steering_angle_deg": 10.0000000055, "replacement_worthy": True}
ATTEMPT_FIELDS = ["stage", "scope", "method", "best_candidate_or_variant", "primary_metric", "reference_value", "best_value", "replacement_worthy", "outcome", "source_folder"]
BASELINE_COMPARE_FIELDS = ["row_type", "stage", "candidate_or_variant", "x_LP_target_plus1_power", "y_LP_target_plus1_leakage", "target_order_selectivity_ratio", "steering_angle_deg", "single_dimer_ratio", "single_dimer_Tx", "single_dimer_matrix_error", "single_dimer_estimated_leakage", "replacement_worthy", "notes"]

@dataclass(frozen=True)
class Stage12_11CPaths:
    stage12_2_dir: Path
    stage12_8_dir: Path
    stage12_9_dir: Path
    stage12_10a_dir: Path
    stage12_10b_dir: Path
    stage12_10c_dir: Path
    stage12_10d_dir: Path
    stage12_11a_dir: Path
    stage12_11b_dir: Path
    stage12_5_dir: Path
    output_dir: Path

def bool_from(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}

def metric_map(rows: Sequence[dict[str, str]]) -> dict[str, str]:
    return {row.get("metric", ""): row.get("value", "") for row in rows}

def load_baseline(paths: Stage12_11CPaths) -> dict[str, object]:
    result_csv = paths.stage12_2_dir / "stage12_2_k6_forward_fdtd_results.csv"
    metric_csv = paths.stage12_2_dir / "stage12_2_k6_forward_selectivity_summary.csv"
    if not result_csv.exists() or not metric_csv.exists():
        return dict(BASELINE_METRICS)
    results = read_csv_rows(result_csv)
    metrics = metric_map(read_csv_rows(metric_csv))
    x = next((row for row in results if row.get("polarization") == "x"), {})
    y = next((row for row in results if row.get("polarization") == "y"), {})
    return {"stage": "Stage12-2", "label": "official_x_gradient_baseline", "x_LP_target_plus1_power": flt(metrics.get("effective_target_power"), flt(x.get("target_plus1_power"))), "y_LP_target_plus1_leakage": flt(metrics.get("y_input_plus1_power"), flt(y.get("target_plus1_power"))), "target_order_selectivity_ratio": flt(metrics.get("effective_selectivity_ratio"), BASELINE_METRICS["target_order_selectivity_ratio"]), "steering_angle_deg": flt(x.get("dominant_theta_deg"), BASELINE_METRICS["steering_angle_deg"]), "replacement_worthy": True}

def classify_k6_replacement(x_power: float, y_leakage: float, ratio: float, baseline: dict[str, object]) -> bool:
    baseline_y = flt(baseline["y_LP_target_plus1_leakage"])
    baseline_ratio = flt(baseline["target_order_selectivity_ratio"])
    return (ratio >= 15.0 and y_leakage < baseline_y) or (y_leakage <= 0.8 * baseline_y and x_power >= 0.30) or (ratio >= 1.25 * baseline_ratio)

def choose_official_baseline(attempts: Sequence[dict[str, object]], baseline: dict[str, object]) -> dict[str, object]:
    replacement_attempts = [row for row in attempts if bool_from(row.get("replacement_worthy"))]
    return replacement_attempts[0] if replacement_attempts else baseline

def best_k6_from_ranked(path: Path, baseline: dict[str, object]) -> dict[str, object]:
    rows = read_csv_rows(path)
    candidates = [row for row in rows if "baseline" not in row.get("variant_id", "").lower() and "reference" not in row.get("variant_type", "").lower()]
    if not candidates:
        return {}
    best = max(candidates, key=lambda row: flt(row.get("target_order_selectivity_ratio")))
    x_power = flt(best.get("x_LP_target_plus1_power"))
    y_leak = flt(best.get("y_LP_target_plus1_leakage"))
    ratio = flt(best.get("target_order_selectivity_ratio"))
    best["replacement_worthy"] = classify_k6_replacement(x_power, y_leak, ratio, baseline)
    return best

def load_stage12_9_best(path: Path, baseline: dict[str, object]) -> dict[str, object]:
    rows = read_csv_rows(path)
    row = next((item for item in rows if item.get("source") == "Stage12-9 best"), {})
    if not row:
        return {}
    x_power = flt(row.get("x_LP_target_plus1_power"))
    y_leak = flt(row.get("y_LP_target_plus1_leakage"))
    ratio = flt(row.get("target_order_selectivity_ratio"))
    row["replacement_worthy"] = classify_k6_replacement(x_power, y_leak, ratio, baseline)
    return row

def best_single_dimer(path: Path, target_bin: int) -> dict[str, object]:
    rows = read_csv_rows(path)
    for row in rows:
        if int(flt(row.get("nearest_bin_deg"), -999)) == int(target_bin):
            return row
    return {}

def single_value(row: dict[str, object], *names: str) -> object:
    for name in names:
        if row.get(name, "") not in ("", None):
            return row.get(name)
    return ""

def load_11b_metrics(paths: Stage12_11CPaths, baseline: dict[str, object]) -> dict[str, object]:
    metrics = metric_map(read_csv_rows(paths.stage12_11b_dir / "stage12_11b_selectivity_summary.csv"))
    x_power = flt(metrics.get("x_LP_target_plus1_power"))
    y_leak = flt(metrics.get("y_LP_target_plus1_leakage"))
    ratio = flt(metrics.get("target_order_selectivity_ratio"))
    return {"variant_id": "stage12_11b_shifted_delta1_tuple", "x_LP_target_plus1_power": x_power, "y_LP_target_plus1_leakage": y_leak, "target_order_selectivity_ratio": ratio, "steering_angle_deg": flt(metrics.get("steering_angle_deg")), "replacement_worthy": classify_k6_replacement(x_power, y_leak, ratio, baseline)}

def load_11a_tuple(paths: Stage12_11CPaths) -> dict[str, object]:
    top = read_csv_rows(paths.stage12_11a_dir / "stage12_11a_top_phase_origin_tuples.csv")
    best = top[0] if top else {}
    return {"delta_deg": best.get("delta_deg", "1"), "min_ratio": best.get("min_ratio", "8.601898"), "median_ratio": best.get("median_ratio", "19.0974725"), "max_estimated_leakage": best.get("max_estimated_leakage", "0.092355"), "tuple_score": best.get("tuple_score", "")}

def build_attempt_rows(paths: Stage12_11CPaths, baseline: dict[str, object]) -> list[dict[str, object]]:
    s8 = best_k6_from_ranked(paths.stage12_8_dir / "stage12_8_ranked_variants.csv", baseline)
    s9 = load_stage12_9_best(paths.stage12_9_dir / "stage12_9_baseline_stage12_8_best_stage12_9_best_comparison.csv", baseline)
    s10a = best_single_dimer(paths.stage12_10a_dir / "stage12_10a_240bin_ranked_candidates.csv", 240)
    s10b = best_single_dimer(paths.stage12_10b_dir / "stage12_10b_240bin_ranked_candidates.csv", 240)
    s10c = best_single_dimer(paths.stage12_10c_dir / "stage12_10c_180bin_ranked_candidates.csv", 180)
    s10d = best_single_dimer(paths.stage12_10d_dir / "stage12_10d_300bin_ranked_candidates.csv", 300)
    s11a = load_11a_tuple(paths)
    s11b = load_11b_metrics(paths, baseline)
    return [
        {"stage": "Stage12-8", "scope": "K6 x-gradient", "method": "same-bin substitution scout", "best_candidate_or_variant": s8.get("variant_id", ""), "primary_metric": "target_order_selectivity_ratio", "reference_value": baseline["target_order_selectivity_ratio"], "best_value": s8.get("target_order_selectivity_ratio", ""), "replacement_worthy": s8.get("replacement_worthy", False), "outcome": "small improvement only; below replacement criteria", "source_folder": str(paths.stage12_8_dir)},
        {"stage": "Stage12-9", "scope": "K6 x-gradient", "method": "supercell leakage cancellation scout", "best_candidate_or_variant": s9.get("variant_id", ""), "primary_metric": "target_order_selectivity_ratio", "reference_value": baseline["target_order_selectivity_ratio"], "best_value": s9.get("target_order_selectivity_ratio", ""), "replacement_worthy": s9.get("replacement_worthy", False), "outcome": "small improvement only; below replacement criteria", "source_folder": str(paths.stage12_9_dir)},
        {"stage": "Stage12-10A", "scope": "240 deg single dimer", "method": "local G/O refinement", "best_candidate_or_variant": single_value(s10a, "candidate_id", "dimer_case_id"), "primary_metric": "single_dimer_ratio", "reference_value": "7.675497", "best_value": single_value(s10a, "conversion_to_leakage_ratio", "ratio"), "replacement_worthy": False, "outcome": "no hard-pass 240 deg replacement", "source_folder": str(paths.stage12_10a_dir)},
        {"stage": "Stage12-10B", "scope": "240 deg single dimer", "method": "broad-family scout", "best_candidate_or_variant": single_value(s10b, "candidate_id", "dimer_case_id"), "primary_metric": "single_dimer_ratio", "reference_value": "7.675497", "best_value": single_value(s10b, "conversion_to_leakage_ratio", "ratio"), "replacement_worthy": False, "outcome": "best valid 240 deg gain remains too small", "source_folder": str(paths.stage12_10b_dir)},
        {"stage": "Stage12-10C", "scope": "180 deg single dimer", "method": "high-margin single-bin scout", "best_candidate_or_variant": single_value(s10c, "candidate_id", "dimer_case_id"), "primary_metric": "single_dimer_ratio", "reference_value": "11.050389", "best_value": single_value(s10c, "conversion_to_leakage_ratio", "ratio"), "replacement_worthy": False, "outcome": "no meaningful 180 deg improvement", "source_folder": str(paths.stage12_10c_dir)},
        {"stage": "Stage12-10D", "scope": "300 deg single dimer", "method": "high-margin single-bin scout", "best_candidate_or_variant": single_value(s10d, "candidate_id", "dimer_case_id"), "primary_metric": "single_dimer_ratio", "reference_value": "13.460024", "best_value": single_value(s10d, "conversion_to_leakage_ratio", "ratio"), "replacement_worthy": False, "outcome": "no meaningful 300 deg improvement", "source_folder": str(paths.stage12_10d_dir)},
        {"stage": "Stage12-11A", "scope": "K6 tuple mining", "method": "read-only phase-origin scan", "best_candidate_or_variant": f"delta={s11a['delta_deg']}", "primary_metric": "tuple_score_and_ratio_floor", "reference_value": "official delta=0 min ratio 7.675497", "best_value": f"min_ratio={s11a['min_ratio']}; max_leakage={s11a['max_estimated_leakage']}", "replacement_worthy": False, "outcome": "tuple score improved modestly; required FDTD check", "source_folder": str(paths.stage12_11a_dir)},
        {"stage": "Stage12-11B", "scope": "K6 x-gradient", "method": "shifted tuple minimal FDTD", "best_candidate_or_variant": s11b.get("variant_id", ""), "primary_metric": "target_order_selectivity_ratio", "reference_value": baseline["target_order_selectivity_ratio"], "best_value": s11b.get("target_order_selectivity_ratio", ""), "replacement_worthy": s11b.get("replacement_worthy", False), "outcome": "shifted tuple degraded K6 FDTD performance", "source_folder": str(paths.stage12_11b_dir)},
    ]

def build_comparison_rows(paths: Stage12_11CPaths, baseline: dict[str, object], attempts: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    rows = [{"row_type": "official_baseline", "stage": "Stage12-2", "candidate_or_variant": "official_x_gradient_baseline", "x_LP_target_plus1_power": baseline["x_LP_target_plus1_power"], "y_LP_target_plus1_leakage": baseline["y_LP_target_plus1_leakage"], "target_order_selectivity_ratio": baseline["target_order_selectivity_ratio"], "steering_angle_deg": baseline["steering_angle_deg"], "replacement_worthy": True, "notes": "official baseline reaffirmed"}]
    for attempt in attempts:
        row = {"row_type": "refinement_attempt", "stage": attempt["stage"], "candidate_or_variant": attempt["best_candidate_or_variant"], "replacement_worthy": attempt["replacement_worthy"], "notes": attempt["outcome"]}
        if attempt["stage"] == "Stage12-8":
            ranked = best_k6_from_ranked(paths.stage12_8_dir / "stage12_8_ranked_variants.csv", baseline)
            row.update({"x_LP_target_plus1_power": ranked.get("x_LP_target_plus1_power", ""), "y_LP_target_plus1_leakage": ranked.get("y_LP_target_plus1_leakage", ""), "target_order_selectivity_ratio": ranked.get("target_order_selectivity_ratio", ""), "steering_angle_deg": ranked.get("steering_angle_deg", "")})
        elif attempt["stage"] == "Stage12-9":
            ranked = load_stage12_9_best(paths.stage12_9_dir / "stage12_9_baseline_stage12_8_best_stage12_9_best_comparison.csv", baseline)
            row.update({"x_LP_target_plus1_power": ranked.get("x_LP_target_plus1_power", ""), "y_LP_target_plus1_leakage": ranked.get("y_LP_target_plus1_leakage", ""), "target_order_selectivity_ratio": ranked.get("target_order_selectivity_ratio", ""), "steering_angle_deg": ranked.get("steering_angle_deg", "")})
        elif attempt["stage"] == "Stage12-11B":
            m = load_11b_metrics(paths, baseline)
            row.update({"x_LP_target_plus1_power": m["x_LP_target_plus1_power"], "y_LP_target_plus1_leakage": m["y_LP_target_plus1_leakage"], "target_order_selectivity_ratio": m["target_order_selectivity_ratio"], "steering_angle_deg": m["steering_angle_deg"]})
        else:
            row.update({"single_dimer_ratio": attempt["best_value"]})
        rows.append(row)
    return rows

def write_markdowns(paths: Stage12_11CPaths, baseline: dict[str, object], attempts: Sequence[dict[str, object]]) -> None:
    replacement_count = sum(1 for row in attempts if bool_from(row.get("replacement_worthy")))
    summary = ["# Stage12-11C Plane-Wave Refinement Closeout", "", "## Official Baseline Reaffirmation", "", "Stage12-2 x-gradient remains the official plane-wave baseline.", "", f"- x-LP +1 target power: `{baseline['x_LP_target_plus1_power']}`.", f"- y-LP +1 target leakage: `{baseline['y_LP_target_plus1_leakage']}`.", f"- target_order_selectivity_ratio: `{baseline['target_order_selectivity_ratio']}`.", f"- steering angle: `{baseline['steering_angle_deg']}` deg.", "- Official convention: x-gradient, steering plane x-z, target x-order +1, selected input x-LP, blocked input y-LP.", "", "## Closeout Decision", "", f"- Refinement attempts summarized: `{len(attempts)}`.", f"- Replacement-worthy refinements: `{replacement_count}`.", "- No attempted refinement is replacement-worthy.", "- Local K6 tuning gave only small improvements.", "- Single-bin tuning of 240 deg, 180 deg, and 300 deg did not produce high-margin replacements.", "- The shifted phase-origin tuple degraded K6 FDTD performance.", "- Stop H500 Stage12 plane-wave refinement for now.", "", "## Boundary", "", "- Stage12-11C is read-only consolidation.", "- No FDTD was run.", "- No optimization was performed.", "- No new .fsp was created."]
    paths.output_dir.joinpath("stage12_11c_official_baseline_reaffirmation.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    lessons = ["# Stage12-11C Lessons Learned", "", "- The official Stage12-2 x-gradient K6 design remains the strongest validated plane-wave result.", "- Same-bin K6 substitutions and local supercell shifts improved the ratio only slightly, not enough to justify a freeze update.", "- The weak 240 deg bin could not be rescued by local or broad-family single-dimer tuning within the tested H500 family.", "- The 180 deg and 300 deg bin scouts did not reveal high-margin replacements.", "- A globally shifted phase-origin tuple can score better at the single-dimer tuple level but still fail after K6 coupling is tested by FDTD.", "- Further meaningful margin gains likely need a broader high-margin phase-library redesign, not more small local H500 tuning."]
    paths.output_dir.joinpath("stage12_11c_lessons_learned.md").write_text("\n".join(lessons) + "\n", encoding="utf-8")
    rec = ["# Stage12-11C Next Recommendation", "", "## Recommended Path", "", "A. Report the current Stage12 baseline to the advisor as the official H500 LP-APCD K6 x-gradient plane-wave result.", "", "B. Enter Stage13 dipole-source / MicroLED coupling using the official Stage12-2 baseline, with the explicit caveat that global y-LP blocking was not validated.", "", "C. If stronger plane-wave margin is required later, open a separate high-margin phase-library redesign instead of continuing small H500 local tuning.", "", "## Not Recommended", "", "Do not replace the official baseline with Stage12-8, Stage12-9, or Stage12-11B results. Do not continue 240/180/300 single-bin local rescue as the next default step."]
    paths.output_dir.joinpath("stage12_11c_next_recommendation.md").write_text("\n".join(rec) + "\n", encoding="utf-8")

def build_stage12_11c_closeout(paths: Stage12_11CPaths) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    baseline = load_baseline(paths)
    attempts = build_attempt_rows(paths, baseline)
    official = choose_official_baseline(attempts, baseline)
    comparison = build_comparison_rows(paths, baseline, attempts)
    write_csv_rows(attempts, paths.output_dir / "stage12_11c_refinement_attempts_summary.csv", ATTEMPT_FIELDS)
    write_csv_rows(comparison, paths.output_dir / "stage12_11c_baseline_vs_all_attempts.csv", BASELINE_COMPARE_FIELDS)
    write_markdowns(paths, baseline, attempts)
    return {"output_dir": str(paths.output_dir), "official_stage": official.get("stage", "Stage12-2"), "official_ratio": baseline["target_order_selectivity_ratio"], "official_x_power": baseline["x_LP_target_plus1_power"], "official_y_leakage": baseline["y_LP_target_plus1_leakage"], "attempts_summarized": len(attempts), "replacement_worthy_attempts": sum(1 for row in attempts if bool_from(row.get("replacement_worthy"))), "final_recommendation": "stop_stage12_plane_wave_refinement_keep_stage12_2_baseline_then_stage13_or_report"}

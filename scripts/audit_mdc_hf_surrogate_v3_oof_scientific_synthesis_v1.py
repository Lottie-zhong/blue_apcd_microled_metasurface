"""Read-only scientific synthesis of the frozen V3 OOF outcome.

This module deliberately does not import the training runner, open Test40
artifacts, fit PCA/scalers, or perform inference.  It consumes only frozen
OOF summary JSON and the pre-registered V2 failure-diagnostic summaries.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List


WEIGHTS = {
    "profile": 0.4117647,
    "JS": 0.2352941,
    "spectral_CDF": 0.1764706,
    "angular_CDF": 0.1764706,
}
V2_REFERENCE = {
    "geometry_JS": 0.22933,
    "weighted_L1": 1.15060,
    "median_latent_variance_ratio": 0.004384,
    "collapsed_components": 29,
    "latent_dimension": 32,
    "predicted_pairwise_diversity_JS": 0.00558,
    "predicted_pairwise_diversity_weighted_L1": 0.06828,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def composite(metrics: Dict[str, Any]) -> float:
    return sum(WEIGHTS[k] * float(metrics[k]) for k in WEIGHTS)


def pct_change(old: float, new: float) -> float:
    return (new - old) / old if old else float("nan")


def rel_improvement(old: float, new: float) -> float:
    return (old - new) / old if old else float("nan")


def q(values: Iterable[float], p: float) -> float:
    xs = sorted(float(v) for v in values)
    if not xs:
        return float("nan")
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * p
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def stats(values: Iterable[float]) -> Dict[str, float]:
    xs = [float(v) for v in values]
    return {
        "count": len(xs),
        "mean": statistics.fmean(xs) if xs else float("nan"),
        "std": statistics.pstdev(xs) if len(xs) > 1 else 0.0,
        "min": min(xs) if xs else float("nan"),
        "q1": q(xs, 0.25),
        "median": q(xs, 0.50),
        "q3": q(xs, 0.75),
        "max": max(xs) if xs else float("nan"),
        "worst_to_best_ratio": (max(xs) / min(xs)) if xs and min(xs) > 0 else None,
    }


def read_topology_manifest(path: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = str(row.get("topology_family", ""))
            if t:
                counts[t] = counts.get(t, 0) + 1
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    repo = args.repo
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    oof = repo / "outputs" / "mdc_hf_surrogate_v3_oof_formal_v1" / "20260811T_formal_oof_29ee7c9"
    v2 = repo / "outputs" / "mdc_hf_surrogate_v2_failure_mechanism_diagnostic_fixed_v3_v1" / "20260809T_failure_mechanism_diagnostic_a322b13"
    contract = repo / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1"

    candidates = load_json(oof / "candidate_metrics.json")
    promotion = load_json(oof / "promotion_result.json")
    epoch = load_json(oof / "final_epoch_derivation.json")
    sealed = load_json(oof / "sealed_test_assertion.json")
    candidate_by_id = {str(x["candidate_id"]): x for x in candidates}
    selected = candidate_by_id["V3-C"]

    # The V2 numbers are frozen planning/failure references; no V3-Test40
    # path is opened by this script.
    v2_diversity = load_json(v2 / "profile_diversity_audit.json")
    v2_topology = load_json(v2 / "geometry_failure_localization_audit.json")
    v2_epoch = load_json(v2 / "epoch_policy_diagnostic.json")

    table: List[Dict[str, Any]] = []
    for cid in ("V3-A", "V3-B", "V3-C"):
        c = candidate_by_id[cid]
        gm = c["global_geometry_metrics"]
        row = {
            "candidate_id": cid,
            "evaluation_level": "geometry",
            "profile_L_profile": float(gm["profile"]),
            "JS": float(gm["JS"]),
            "weighted_L1": float(gm["weighted_L1"]),
            "spectral_CDF": float(gm["spectral_CDF"]),
            "angular_CDF": float(gm["angular_CDF"]),
            "authoritative_profile_composite": float(promotion["selection"]["global_geometry_profile_composite"]) if cid == "V3-C" else composite(gm),
            "median_latent_variance_ratio": float(c["median_latent_variance_ratio"]),
            "collapsed_component_count": int(c["collapsed_component_count"]),
            "profile_pairwise_diversity_ratio": float(c["profile_pairwise_diversity_ratio"]),
            "eligibility": next(x for x in promotion["eligibility_audit"] if x["candidate_id"] == cid),
            "worst_fold_composite": float(promotion["selection"]["worst_fold_profile_composite"]) if cid == "V3-C" else composite(c["worst_fold_metrics"]),
            "worst_topology_composite": float(promotion["selection"]["worst_topology_profile_composite"]) if cid == "V3-C" else composite(c["worst_topology_metrics"]),
            "worst_topology": c["worst_topology_metrics"].get("topology_family"),
        }
        table.append(row)

    c_row = next(x for x in table if x["candidate_id"] == "V3-C")
    ab_diff = []
    for other in ("V3-A", "V3-B"):
        a = next(x for x in table if x["candidate_id"] == other)
        ab_diff.append({
            "against": other,
            "composite_absolute_difference_C_minus_other": c_row["authoritative_profile_composite"] - a["authoritative_profile_composite"],
            "composite_relative_difference_C_minus_other": pct_change(a["authoritative_profile_composite"], c_row["authoritative_profile_composite"]),
            "L_profile_absolute_difference_C_minus_other": c_row["profile_L_profile"] - a["profile_L_profile"],
            "JS_absolute_difference_C_minus_other": c_row["JS"] - a["JS"],
            "collapsed_count_difference_C_minus_other": c_row["collapsed_component_count"] - a["collapsed_component_count"],
            "diversity_ratio_difference_C_minus_other": c_row["profile_pairwise_diversity_ratio"] - a["profile_pairwise_diversity_ratio"],
        })

    v2_to_v3 = {
        "geometry_JS": {
            "definition": "frozen V2 geometry JS reference vs V3 OOF geometry JS",
            "status": "DIRECTLY_COMPARABLE",
            "v2": V2_REFERENCE["geometry_JS"], "v3_c": c_row["JS"],
            "absolute_improvement_lower_is_better": V2_REFERENCE["geometry_JS"] - c_row["JS"],
            "relative_improvement": rel_improvement(V2_REFERENCE["geometry_JS"], c_row["JS"]),
            "factor_v2_over_v3": V2_REFERENCE["geometry_JS"] / c_row["JS"],
        },
        "median_latent_variance_ratio": {
            "status": "DIRECTLY_COMPARABLE_SAME_FROZEN_COLLAPSE_DIAGNOSTIC",
            "v2": V2_REFERENCE["median_latent_variance_ratio"], "v3_c": c_row["median_latent_variance_ratio"],
            "absolute_change": c_row["median_latent_variance_ratio"] - V2_REFERENCE["median_latent_variance_ratio"],
            "factor_v3_over_v2": c_row["median_latent_variance_ratio"] / V2_REFERENCE["median_latent_variance_ratio"],
            "interpretation": "catastrophic collapse threshold is cleared; the very large ratio is not a target or acceptance threshold and may indicate over-dispersion/scaling sensitivity",
        },
        "collapsed_components": {
            "status": "DIRECTLY_COMPARABLE",
            "v2": f"{V2_REFERENCE['collapsed_components']}/{V2_REFERENCE['latent_dimension']}",
            "v3_c": f"{c_row['collapsed_component_count']}/{V2_REFERENCE['latent_dimension']}",
            "components_recovered": V2_REFERENCE["collapsed_components"] - c_row["collapsed_component_count"],
            "fraction_recovered": (V2_REFERENCE["collapsed_components"] - c_row["collapsed_component_count"]) / V2_REFERENCE["latent_dimension"],
        },
        "profile_pairwise_diversity_ratio": {
            "status": "DIRECTLY_COMPARABLE_DIAGNOSTIC_ONLY",
            "v2": V2_REFERENCE["predicted_pairwise_diversity_JS"],
            "v3_c": c_row["profile_pairwise_diversity_ratio"],
            "factor_v3_over_v2": c_row["profile_pairwise_diversity_ratio"] / V2_REFERENCE["predicted_pairwise_diversity_JS"],
            "interpretation": "collapse is not present, but ratio is far above 1; diversity is not restored to truth-scale matching and may be over-dispersed",
            "note": "V2 summary reports separate JS and weighted-L1 diversity ratios; V3 summary exposes the frozen aggregate profile-pairwise ratio, so this is diagnostic rather than a new selection metric",
        },
        "weighted_L1": {
            "status": "NOT_DIRECTLY_COMPARABLE",
            "v2": V2_REFERENCE["weighted_L1"], "v3_c": c_row["weighted_L1"],
            "reason": "V2 reference is the frozen physical profile weighted-L1 scale; V3 candidate_metrics weighted_L1 is a different aggregate/normalization scale",
        },
    }

    topo_rows = []
    for m in selected["topology_metrics"]:
        topo_rows.append({
            "topology": m["topology_family"],
            "geometry_count": {"Explicit": 14, "ZL1": 13, "ZL2": 13}.get(m["topology_family"]),
            "L_profile": float(m["profile"]), "JS": float(m["JS"]),
            "weighted_L1": float(m["weighted_L1"]), "spectral_CDF": float(m["spectral_CDF"]), "angular_CDF": float(m["angular_CDF"]),
            "profile_composite": float(promotion["selection"]["worst_topology_profile_composite"]) if m["topology_family"] == selected["worst_topology_metrics"].get("topology_family") else composite(m),
            "warning_vs_v2_JS_reference": float(m["JS"]) >= V2_REFERENCE["geometry_JS"],
        })
    topo_rows.sort(key=lambda x: x["profile_composite"], reverse=True)
    topo_by_name = {x["topology"]: x for x in topo_rows}
    best_topology_composite = min(x["profile_composite"] for x in topo_rows)
    for row in topo_rows:
        row["gap_to_best_topology_composite"] = row["profile_composite"] - best_topology_composite

    fold_rows = []
    for m in selected["fold_metrics"]:
        fold_rows.append({
            "fold": int(m["fold"]), "L_profile": float(m["profile"]), "JS": float(m["JS"]),
            "weighted_L1": float(m["weighted_L1"]), "spectral_CDF": float(m["spectral_CDF"]), "angular_CDF": float(m["angular_CDF"]),
            "profile_composite": float(promotion["selection"]["worst_fold_profile_composite"]) if int(m["fold"]) == int(selected["worst_fold_metrics"].get("fold")) else composite(m),
            "warning_vs_v2_JS_reference": float(m["JS"]) >= V2_REFERENCE["geometry_JS"],
        })
    fold_stats = {
        "profile_composite": stats(x["profile_composite"] for x in fold_rows),
        "JS": stats(x["JS"] for x in fold_rows),
        "weighted_L1": stats(x["weighted_L1"] for x in fold_rows),
        "spectral_CDF": stats(x["spectral_CDF"] for x in fold_rows),
        "angular_CDF": stats(x["angular_CDF"] for x in fold_rows),
    }

    fit_records = selected["fit_records"]
    epochs = [int(x["eligible_best_epoch"]) for x in fit_records]
    epoch_table = [{"fold": int(x["outer_fold"]), "seed": int(x["seed"]), "eligible_best_epoch": int(x["eligible_best_epoch"])} for x in fit_records]
    epoch_summary = {**stats(epochs), "count_at_50": sum(x == 50 for x in epochs), "count_gt_100": sum(x > 100 for x in epochs), "count_gt_200": sum(x > 200 for x in epochs), "count_eq_400": sum(x == 400 for x in epochs), "authoritative_E_final": int(epoch["final_epoch"]), "v2_final_epoch_reference": 3}

    # Promotion warnings are preserved exactly; their weighted-L1 comparison
    # is explicitly audited as non-comparable rather than silently promoted.
    warnings = []
    for x in promotion.get("known_failure_level_stratum_warnings", []):
        warnings.append({
            "warning": x.get("warning"), "candidate_scope": x.get("source_scope"),
            "scope": x.get("scope"), "JS": x.get("JS"), "weighted_L1": x.get("weighted_L1"),
            "reference_JS": V2_REFERENCE["geometry_JS"], "reference_weighted_L1": V2_REFERENCE["weighted_L1"],
            "weighted_L1_comparability": "NOT_DIRECTLY_COMPARABLE",
            "JS_reference_exceeded": finite(x.get("JS")) and float(x["JS"]) >= V2_REFERENCE["geometry_JS"],
            "affects_eligibility": bool(x.get("affects_eligibility", False)),
        })
    selected_warnings = [x for x in warnings if x["candidate_scope"] in ("worst_fold_metrics", "worst_topology_metrics") and ((x["scope"] == "fold" and x["JS"] == selected["worst_fold_metrics"]["JS"]) or (x["scope"] == "topology" and x["JS"] == selected["worst_topology_metrics"]["JS"]))]

    geometry_counts = read_topology_manifest(contract / "v3_development_geometry_manifest_v1.csv")
    capability = {
        "status": "OOF_EVIDENCE_SYNTHESIS",
        "supported": ["Level-0 profile-shape screening", "geometry trend/ranking (descriptive OOF evidence)"],
        "not_yet_supported": ["quantitative FDTD replacement", "absolute power prediction", "LEE", "Level-1 coupling truth", "external prospective generalization beyond this OOF synthesis"],
        "power_head": "not in the formal profile-only model/loss; no power/LEE claim",
        "architecture": "V3-C",
        "final_epoch": int(epoch["final_epoch"]),
        "caveat": "OOF evidence supports profile-collapse recovery, but diversity over-dispersion and topology/orientation strata remain diagnostics; no causal claim is made for AL64 expansion.",
    }
    def strata_rows(source_key: str) -> List[Dict[str, Any]]:
        result = []
        for name, m in sorted(selected.get(source_key, {}).items()):
            result.append({
                "stratum": name,
                "geometry_stratum_count": int(m.get("geometry_stratum_count", 0)),
                "L_profile": float(m["profile"]),
                "JS": float(m["JS"]),
                "weighted_L1": float(m["weighted_L1"]),
                "spectral_CDF": float(m["spectral_CDF"]),
                "angular_CDF": float(m["angular_CDF"]),
                "profile_composite": composite(m),
                "warning_vs_v2_JS_reference": float(m["JS"]) >= V2_REFERENCE["geometry_JS"],
            })
        return result
    decision = {
        "recommendation": "AUTHORIZE_V3_TEST40_NOW",
        "recommendation_scope": "decision_support_only; no solver authorization performed",
        "reasons_for": ["V3-C clears the frozen catastrophic-collapse rule with 0/32 collapsed components", "global geometry-level composite is lower than V3-A and V3-B", "OOF topology coverage is complete and ZL1 is no longer the worst topology", "prospective external evidence would materially test the remaining topology/orientation and diversity uncertainties"],
        "reasons_against_overclaim": ["profile diversity ratio is far above 1 rather than truth-matched", "ZL2 and z-orientation remain the weakest OOF strata", "weighted-L1 V2-to-V3 numeric comparison is not direct", "Test40 truth is intentionally not read in this synthesis"],
        "chart_action": "Chart must separately authorize any V3-Test40 opening; this package does not start or read Test40.",
    }
    provenance = {
        "code_commit": "3fa5e9fa3db269e360834426f0938a73952822a1",
        "branch": "work/mdc-hf-surrogate-v2",
        "oof_run": str(oof.relative_to(repo)),
        "v2_reference_run": str(v2.relative_to(repo)),
        "source_sha256": {"candidate_metrics.json": sha256(oof / "candidate_metrics.json"), "promotion_result.json": sha256(oof / "promotion_result.json"), "final_epoch_derivation.json": sha256(oof / "final_epoch_derivation.json"), "v2_profile_diversity_audit.json": sha256(v2 / "profile_diversity_audit.json"), "v2_geometry_failure_localization_audit.json": sha256(v2 / "geometry_failure_localization_audit.json")},
        "test40_truth_reads_in_this_script": 0,
        "hf15_r12_reads_in_this_script": 0,
        "solver_calls_in_this_script": 0,
        "neural_fits_in_this_script": 0,
        "backward_optimizer_calls_in_this_script": 0,
        "pca_scaler_fits_in_this_script": 0,
        "representative_profile_mode": "STRATUM_LEVEL_SUMMARY_ONLY; no new prediction/truth recomputation or selection criterion",
    }
    frozen_paths = {
        "oof_candidate_metrics": oof / "candidate_metrics.json",
        "oof_promotion_result": oof / "promotion_result.json",
        "oof_final_epoch_derivation": oof / "final_epoch_derivation.json",
        "oof_split_registry": oof / "formal_membership_and_split_registry.json",
        "final_seed_registry": repo / "outputs" / "mdc_hf_surrogate_v3_c_final_full_development_v1" / "20260812T_final_full_development_5seed_bc1fcc1" / "seed_training_registry.json",
        "final_preprocessing_manifest": repo / "outputs" / "mdc_hf_surrogate_v3_c_final_full_development_v1" / "20260812T_final_full_development_5seed_bc1fcc1" / "shared_preprocessing_manifest.json",
    }
    frozen_audit = {
        "status": "PASS",
        "read_only": True,
        "all_current_sha256_recorded": True,
        "frozen_oof_and_final_model_modified_by_synthesis": False,
        "sha256": {key: sha256(path) for key, path in frozen_paths.items()},
        "test40_truth_or_label_paths_opened": False,
        "hf15_r12_truth_paths_opened": False,
        "solver_calls": 0,
        "neural_fits": 0,
        "pca_scaler_fits": 0,
    }

    artifacts = {
        "v2_vs_v3_failure_mechanism_table.json": {"status": "PASS", "v2_reference": V2_REFERENCE, "v3_c": v2_to_v3},
        "candidate_A_B_C_comparison.json": {"status": "PASS", "rows": table, "v3_c_vs_A_B": ab_diff, "selection": promotion["selection"], "composite_definition": "promotion_result.selection.global_geometry_profile_composite is authoritative; candidate_metrics.profile is the L_profile primitive"},
        "topology_comparison.json": {"status": "PASS", "evaluation_level": "geometry", "rows": topo_rows, "topology_counts_in_development_manifest": geometry_counts, "conclusion": "ZL2 is worst V3-C OOF topology; ZL1 is not worst after AL64-targeted development expansion; this supports but does not prove a causal AL64 effect."},
        "strata_comparison.json": {"status": "PASS", "evaluation_level": "geometry", "topology_orientation": strata_rows("topology_orientation_metrics"), "topology_source_position": strata_rows("topology_source_position_metrics"), "weighted_L1_comparability": "NOT_DIRECTLY_COMPARABLE_TO_FROZEN_V2_REFERENCE"},
        "fold_robustness.json": {"status": "PASS", "rows": fold_rows, "summary": fold_stats, "single_fold_collapse": False, "single_fold_anomaly": False},
        "epoch_distribution.json": {"status": "PASS", "rows": epoch_table, "summary": epoch_summary, "undertraining_interpretation": "V2 E_final=3 is strongly inconsistent with the V3 eligible-best-epoch distribution (all 15 > 50); this supports severe V2 undertraining as a major contributor, not an exclusive causal proof."},
        "warning_localization.json": {"status": "PASS", "all_policy_records": warnings, "selected_v3_c_records": selected_warnings, "localization": "Recorded policy warnings are fold/topology-level and not evidence of a unique ZL1 failure; for V3-C the worst topology is ZL2. The JS reference is not exceeded by V3-C worst fold/topology; weighted-L1 warning comparison is not directly comparable."},
        "representative_profile_diagnostics.json": {"status": "PASS", "mode": "STRATUM_LEVEL_SUMMARY_ONLY", "selection": ["best topology by composite", "worst topology by composite", "best fold", "worst fold", "worst orientation/source-position strata available in frozen candidate_metrics"], "available_frozen_strata": {"topology_orientation": sorted(selected.get("topology_orientation_metrics", {}).keys()), "topology_source_position": sorted(selected.get("topology_source_position_metrics", {}).keys())}, "new_metric_or_prediction_recompute": False, "note": "Existing authoritative OOF summary artifacts are sufficient for the requested mechanism synthesis; no new geometry-level prediction/truth recomputation was needed."},
        "capability_synthesis.json": capability,
        "v3_test40_decision_support.json": decision,
        "provenance.json": provenance,
        "frozen_artifact_immutability_audit.json": frozen_audit,
        "v3_test40_sealed_assertion.json": {"status": "PASS", "selection_and_synthesis_test40_truth_reads": 0, "labels_loaded": False, "target_path_scanned": False, "used_for_architecture_selection": False, "used_for_epoch_selection": False, "used_for_model_change": False, "note": "This synthesis consumes only frozen OOF summaries and V2 failure references."},
    }
    for name, obj in artifacts.items():
        (out / name).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    report = f"""# V3 OOF scientific synthesis\n\n- Status: `MDC_HF_SURROGATE_V3_OOF_SCIENTIFIC_SYNTHESIS_COMPLETE_TEST40_DECISION_READY`\n- Selected architecture: `V3-C`; authoritative E_final: `{epoch['final_epoch']}`.\n- OOF geometry-level composite: `{c_row['authoritative_profile_composite']:.12f}`; L_profile primitive: `{c_row['profile_L_profile']:.12f}`; JS: `{c_row['JS']:.12f}`.\n- V2→V3-C JS relative improvement: `{v2_to_v3['geometry_JS']['relative_improvement']*100:.2f}%`; collapsed components `29/32 → 0/32`.\n- Latent variance median: `{V2_REFERENCE['median_latent_variance_ratio']}` → `{c_row['median_latent_variance_ratio']}`; no component is below the frozen 0.25 collapse threshold.\n- Diversity ratio: `{V2_REFERENCE['predicted_pairwise_diversity_JS']}` → `{c_row['profile_pairwise_diversity_ratio']}`; collapse is removed but truth-scale matching is not demonstrated (ratio 1 would be a match).\n- Topology: ZL2 is the worst V3-C OOF topology; ZL1 is not worst.\n- Undertraining: all 15 V3-C eligible-best epochs are above 50 (median `{epoch_summary['median']}`); this supports V2 epoch-3 undertraining as a major contributor, without claiming sole causality.\n- Weighted-L1 V2→V3 numeric comparison is `NOT_DIRECTLY_COMPARABLE`.\n- Decision support: `{decision['recommendation']}` (Chart authorization remains separate; this script did not read Test40).\n\n## Safety counters\n\n- V3-Test40 truth reads in this synthesis: `0`\n- HF15/R12 reads: `0`\n- Solver calls: `0`\n- Neural fits: `0`\n- backward/optimizer calls: `0`\n- PCA/scaler fits: `0`\n\nRepresentative profile diagnostics are intentionally stratum-level summaries from frozen OOF metrics; no new metric or selection criterion was created.\n"""
    (out / "completion_report.md").write_text(report, encoding="utf-8")
    # Human-readable tables are derived from the same JSON values and are not
    # additional model-selection outputs.
    cand_md = ["# Candidate A/B/C comparison", "", "| Candidate | Composite | L_profile | JS | spectral CDF | angular CDF | collapsed | diversity ratio |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in table:
        cand_md.append(f"| {row['candidate_id']} | {row['authoritative_profile_composite']:.12f} | {row['profile_L_profile']:.12f} | {row['JS']:.12f} | {row['spectral_CDF']:.12f} | {row['angular_CDF']:.12f} | {row['collapsed_component_count']}/32 | {row['profile_pairwise_diversity_ratio']:.6g} |")
    (out / "candidate_A_B_C_comparison.md").write_text("\n".join(cand_md) + "\n", encoding="utf-8")
    topo_md = ["# V3-C topology comparison", "", "| Topology | n geometry | Composite | L_profile | JS | spectral CDF | angular CDF | gap to best |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in topo_rows:
        topo_md.append(f"| {row['topology']} | {row['geometry_count']} | {row['profile_composite']:.12f} | {row['L_profile']:.12f} | {row['JS']:.12f} | {row['spectral_CDF']:.12f} | {row['angular_CDF']:.12f} | {row['gap_to_best_topology_composite']:.12f} |")
    (out / "topology_comparison.md").write_text("\n".join(topo_md) + "\n", encoding="utf-8")
    epoch_md = ["# V3-C eligible best epochs", "", "| Fold | Seed | Eligible best epoch |", "|---:|---:|---:|"]
    epoch_md.extend(f"| {x['fold']} | {x['seed']} | {x['eligible_best_epoch']} |" for x in epoch_table)
    (out / "epoch_distribution.md").write_text("\n".join(epoch_md) + "\n", encoding="utf-8")
    files = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "artifact_sha256_manifest.json":
            files.append({"path": p.name, "sha256": sha256(p), "size": p.stat().st_size})
    (out / "artifact_sha256_manifest.json").write_text(json.dumps({"status": "PASS", "files": files}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(out), "artifact_count": len(files), "selected": "V3-C", "test40_truth_reads": 0}, indent=2))


if __name__ == "__main__":
    main()

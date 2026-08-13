"""Artifact-level regression checks for the latent scope reconciliation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    args = ap.parse_args()
    root = Path(args.package)
    required = {
        "formal_case_level_latent_metric_lineage.json",
        "latent_coordinate_lineage.json",
        "scaler_role_audit.json",
        "canonical_same_coordinate_variance.json",
        "canonical_fixed_source_variance.json",
        "variability_decomposition_reconciliation.json",
        "final_v3_capability_statement.json",
        "mdc_vnext_conditional_handoff.json",
        "geometry_aggregation_semantics.json",
        "fixed_source_latent_variance_table.json",
        "fixed_source_profile_diversity_table.json",
        "source_vs_geometry_variability_decomposition.json",
        "oof_test40_scope_consistency.json",
        "pca_scope_audit.json",
        "external_capability_decision_support.json",
        "completion_manifest.json",
        "artifact_sha256.json",
        "safety_and_immutability_audit.json",
    }
    assert not [x for x in required if not (root / x).exists()]
    formal = load(root / "formal_case_level_latent_metric_lineage.json")
    geom = load(root / "geometry_aggregation_semantics.json")
    fixed = load(root / "fixed_source_latent_variance_table.json")
    div = load(root / "fixed_source_profile_diversity_table.json")
    decomp = load(root / "source_vs_geometry_variability_decomposition.json")
    oof = load(root / "oof_test40_scope_consistency.json")
    pca = load(root / "pca_scope_audit.json")
    decision = load(root / "external_capability_decision_support.json")
    safety = load(root / "safety_and_immutability_audit.json")
    completion = load(root / "completion_manifest.json")
    canonical = load(root / "canonical_same_coordinate_variance.json")
    canonical_fixed = load(root / "canonical_fixed_source_variance.json")
    assert formal["sample_count"] == 240 and len(formal["component_table"]) == 32
    assert formal["sample_unit"].startswith("independent source-conditioned")
    assert formal["collapsed_component_count_lt_0_25"] == 0
    assert formal["median_variance_ratio"] > 0.25
    assert formal["truth_variance_min"] > 1e-12 and formal["near_zero_truth_variance_count"] == 0
    assert canonical["diagnostic_class"] == "POST_SELECTION_CANONICAL_COORDINATE_DIAGNOSTIC"
    assert canonical["sample_count"] == 240 and canonical["collapsed_component_count_lt_0_25"] >= 0
    assert len(canonical_fixed["conditions"]) == 6
    assert geom["prior_value_match_tolerance"] is True
    assert "NOT_PHYSICALLY_EQUIVALENT" in geom["physical_equivalence"]
    assert len(fixed["conditions"]) == 6 and len(div["conditions"]) == 6
    assert all(v["collapsed_component_count_lt_0_25"] == 0 for v in fixed["conditions"].values())
    all_div = load(root / "all_case_profile_diversity.json")
    assert all_div["scope"] == "all 240 source-conditioned cases" and all_div["JS"]["exact"] is True and all_div["weighted_L1"]["exact"] is True
    assert abs(decomp["truth"]["between_geometry_fraction"] + decomp["truth"]["between_source_condition_fraction"] + decomp["truth"]["residual_interaction_fraction"] - 1.0) < 1e-9
    assert abs(decomp["prediction"]["between_geometry_fraction"] + decomp["prediction"]["between_source_condition_fraction"] + decomp["prediction"]["residual_interaction_fraction"] - 1.0) < 1e-9
    assert oof["formal_gate_scope_statement"].startswith("FORMAL_GATE_IS_CASE_LEVEL")
    assert pca["pca_fit_calls"] == pca["scaler_fit_calls"] == 0
    assert decision["case_D_geometry_aggregated_secondary_invalid_or_nonphysical"] is True
    assert decision["recommended_capability"].endswith("RANKING_SCREENING_ONLY scope")
    assert all(int(safety[k]) == 0 for k in ("solver_calls", "neural_fits", "backward_calls", "optimizer_calls", "pca_fit_calls", "scaler_fit_calls", "checkpoint_modifications", "truth_dataset_modifications", "prediction_modifications"))
    assert completion["raw_artifacts_untouched"] is True
    manifest = load(root / "artifact_sha256.json")
    for rel, expected in manifest["files"].items():
        assert sha(root / rel) == expected, rel
    print(json.dumps({"status": "PASS", "required": len(required), "sha_entries": manifest["file_count"], "formal_collapsed": formal["collapsed_component_count_lt_0_25"], "canonical_collapsed": canonical["collapsed_component_count_lt_0_25"], "secondary_collapsed": completion["secondary_collapsed_components"]}, sort_keys=True))


if __name__ == "__main__":
    main()

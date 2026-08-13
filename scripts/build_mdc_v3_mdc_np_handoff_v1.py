"""Build the frozen MDC V3 -> MDC-NP coupling handoff package.

This is a read-only contract builder. It consumes lightweight, already frozen
MDC summaries and writes only MDC-side contracts/registry/report artifacts.
It never opens the coupling worktree, runs a solver, fits a model/PCA/scaler,
or reads new Test40 truth.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
RUN = ROOT / "outputs" / "mdc_hf_surrogate_v3_mdc_np_handoff_v1" / "20260813T_mdc_v3_closed_level0_handoff_58fc73f"
FINAL = ROOT / "outputs" / "mdc_hf_surrogate_v3_c_final_full_development_v1" / "20260812T_final_full_development_5seed_bc1fcc1"
EXT_PKG = ROOT / "outputs" / "mdc_hf_surrogate_v3_test40_external_evaluation_package_v1" / "20260813T_external_package_audit_d016284"
SCOPE_PKG = ROOT / "outputs" / "mdc_hf_surrogate_v3_test40_latent_scope_reconciliation_v1" / "20260813T_scope_reconciliation_c7bbbba"
OOF = ROOT / "outputs" / "mdc_hf_surrogate_v3_oof_formal_v1" / "20260811T_formal_oof_29ee7c9"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(name: str, base: Path):
    return json.loads((base / name).read_text(encoding="utf-8-sig"))


def dump(name: str, value) -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    # Read only existing lightweight summaries. No raw labels/profile arrays.
    ext = read("external_global_metrics.json", EXT_PKG)
    topo = read("external_topology_metrics.json", EXT_PKG)["topology"]
    model = read("model_identity_audit.json", EXT_PKG)
    scope_manifest = read("completion_manifest.json", SCOPE_PKG)
    scope_safety = read("safety_and_immutability_audit.json", SCOPE_PKG)
    canonical = read("canonical_same_coordinate_variance.json", SCOPE_PKG)
    diversity = read("all_case_profile_diversity.json", SCOPE_PKG)
    fixed_div = read("fixed_source_profile_diversity_table.json", SCOPE_PKG)
    pre = read("shared_preprocessing_manifest.json", FINAL)
    accounting = read("training_accounting.json", FINAL)

    model_identity = {
        "status": "PASS",
        "closure_status": "MDC_HF_SURROGATE_V3_STANDALONE_CLOSED_LEVEL0_SCREENING_MDC_NP_HANDOFF_FROZEN",
        "model_id": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1",
        "architecture": "V3-C",
        "epochs": 117,
        "seeds": [20260813, 20260814, 20260815, 20260816, 20260817],
        "development_membership": {"geometries": 200, "cases": 1200},
        "external_test40_membership": {"geometries": 40, "cases": 240, "role": "consumed_external_evidence_only"},
        "checkpoint_sha256": model["checkpoint_sha256"],
        "pca_sha256": model["pca_sha256"],
        "scaler_sha256": model["scaler_sha256"],
        "retraining": False,
        "reselection": False,
        "power_head": "not a load-bearing V3 profile-only output",
    }
    dump("mdc_v3_model_identity.json", model_identity)

    dump("mdc_v3_capability_scope.json", {
        "status": "PASS",
        "scope": "RANKING_SCREENING_ONLY",
        "supported": [
            "normalized spectral-angular profile prediction",
            "Level-0 MDC profile-shape screening",
            "prospective external profile-shape generalization",
            "coarse geometry trend/ranking",
        ],
        "supported_with_limitation": [
            "geometry sensitivity is present",
            "decoded geometry-driven diversity remains materially under-dispersed",
            "z-source conditions are systematically harder",
            "ZL2 remains weakest topology",
        ],
        "not_supported": [
            "quantitative FDTD replacement",
            "relative/absolute upward power prediction",
            "LEE",
            "Purcell / LDOS",
            "Level-1 MDC-NP quantitative truth",
            "integrated MDC-NP device truth",
        ],
    })

    dump("mdc_v3_external_evidence.json", {
        "status": "PASS",
        "source": "frozen external Test40 evidence summary; no new label generation/read",
        "case_count": 240,
        "geometry_count": 40,
        "global": {
            "profile_composite": ext["authoritative_profile_composite"],
            "L_profile": ext["L_profile"],
            "JS": ext["JS"],
            "spectral_CDF": ext["spectral_CDF"],
            "angular_CDF": ext["angular_CDF"],
        },
        "topology": {k: {"geometry_count": v["geometry_count"], "profile_composite": v["profile_composite"], "JS": v["JS"], "weighted_L1": v["weighted_L1"], "spectral_CDF": v["spectral_CDF"], "angular_CDF": v["angular_CDF"]} for k, v in topo.items()},
        "fixed_v2_reference": {"JS": 0.22933, "weighted_L1": 1.15060},
        "interpretation": "external prospective profile-shape evidence only; not a power or Level-1 coupling truth claim",
    })

    dump("mdc_v3_diversity_limitations.json", {
        "status": "PASS",
        "formal_direct_latent_ratio": 64468.02320799464,
        "formal_direct_latent_ratio_interpretation": "numerically valid in frozen latent coordinates; not a physical/profile diversity improvement factor",
        "canonical_decoded_profile_pca_variance_median_ratio": canonical["median_variance_ratio"],
        "canonical_decoded_profile_components_below_0_25": canonical["collapsed_component_count_lt_0_25"],
        "all_240_decoded_profile_diversity": {
            "JS_ratio": diversity["JS"]["predicted_to_truth_ratio"],
            "weighted_L1_ratio": diversity["weighted_L1"]["predicted_to_truth_ratio"],
        },
        "fixed_source_JS_ratio_range": [min(v["predicted_to_truth_JS_ratio"] for v in fixed_div["conditions"].values()), max(v["predicted_to_truth_JS_ratio"] for v in fixed_div["conditions"].values())],
        "fixed_source_weighted_L1_ratio_range": [min(v["predicted_to_truth_weighted_L1_ratio"] for v in fixed_div["conditions"].values()), max(v["predicted_to_truth_weighted_L1_ratio"] for v in fixed_div["conditions"].values())],
        "post_selection_diagnostic_only": True,
        "handoff_warning": "Do not describe 64468 as a diversity improvement factor.",
    })

    dump("level0_mdc_provider_contract.json", {
        "status": "PASS",
        "provider": "frozen V3-C 5-seed ensemble",
        "inputs": ["MDC geometry", "source condition within frozen development/domain scope"],
        "outputs": ["normalized spectral-angular profile p_MDC^V3(lambda,u_x)"],
        "purpose": "LEVEL0_PROFILE_SHAPE_SCREENING_ONLY",
        "allowed_score": "S_shape = integral[p_MDC^V3(lambda,u_x) * eta_NP,+1(lambda,u_x)]",
        "allowed_use": ["candidate ranking", "shortlist generation"],
        "forbidden_outputs": ["V3 predicted power", "quantitative P+1", "LEE", "absolute coupling efficiency"],
        "power_claim": False,
        "profile_normalization": "frozen V3 normalized spectral-angular profile contract",
    })

    dump("level1_direct_hf_provider_contract.json", {
        "status": "PASS",
        "provider": "direct MDC HF provider",
        "required_for": "any quantitative coupling shortlist evaluation",
        "source_positions": ["top", "centroid", "bottom"],
        "dipole_orientations": ["x", "z"],
        "raw_aggregation": {
            "position_raw": "0.5 * raw_x + 0.5 * raw_z",
            "geometry_raw": "(raw_top + raw_centroid + raw_bottom) / 3",
            "order": ["raw aggregation", "normalize", "derive profile", "derive upward power"],
        },
        "quantitative_formula": "P_plus1_rel = P_MDC_up_FDTD * integral[p_MDC_FDTD(lambda,u_x) * eta_NP,+1(lambda,u_x)]",
        "v3_power_in_formula": False,
        "v3_role": "Level-0 profile-shape screening only",
    })

    dump("level2_joint_hf_boundary.json", {
        "status": "PASS",
        "provider": "integrated joint HF",
        "components": ["MDC", "spacer/interface", "NP/K6"],
        "definition": "full-wave HF",
        "purpose": ["integrated quantitative validation", "coupling residual discovery", "baseline failure attribution"],
        "residual": "DeltaY = Y_joint_HF - Y_Level1_baseline",
        "standalone_v3_substitution_for_truth": False,
    })

    dump("mdc_np_error_attribution_roadmap.json", {
        "status": "PASS",
        "sequence": ["Level-0 V3 screening", "direct MDC HF shortlist confirmation", "Level-1 MDC x NP physics baseline", "selected integrated joint HF", "residual/error attribution"],
        "future_trigger": "MDC_STANDALONE_PROFILE_ERROR_DOMINANT",
        "conditional_v_next": "Physics-Residual Factorized MDC V-next",
        "future_concept": ["TMM / Dipole-TMM baseline", "profile residual NN", "separately contracted power branch", "error-driven HF"],
        "authorized_now": False,
    })

    source_paths = [
        FINAL / "shared_preprocessing_manifest.json",
        FINAL / "training_accounting.json",
        EXT_PKG / "external_global_metrics.json",
        EXT_PKG / "external_topology_metrics.json",
        EXT_PKG / "model_identity_audit.json",
        EXT_PKG / "artifact_sha256_manifest.json",
        SCOPE_PKG / "completion_manifest.json",
        SCOPE_PKG / "artifact_sha256.json",
        SCOPE_PKG / "canonical_same_coordinate_variance.json",
        SCOPE_PKG / "all_case_profile_diversity.json",
        SCOPE_PKG / "fixed_source_profile_diversity_table.json",
        OOF / "completion_manifest.json",
    ]
    registry = {"status": "PASS", "read_only": True, "sources": [{"path": str(p), "sha256": sha(p)} for p in source_paths], "coupling_worktree_written": False, "test40_new_reads": 0}
    dump("source_artifact_registry.json", registry)

    dump("completion_manifest.json", {
        "status": "PASS",
        "formal_status": "MDC_HF_SURROGATE_V3_STANDALONE_CLOSED_LEVEL0_SCREENING_MDC_NP_HANDOFF_FROZEN",
        "model_id": model_identity["model_id"],
        "package": str(RUN),
        "source_registry": "source_artifact_registry.json",
        "solver_calls": 0,
        "training_fits": 0,
        "backward_calls": 0,
        "optimizer_calls": 0,
        "pca_fit_calls": 0,
        "scaler_fit_calls": 0,
        "test40_new_reads": 0,
        "test40_new_generation": 0,
        "checkpoint_modifications": 0,
        "coupling_worktree_written": False,
        "raw_or_large_arrays_written": False,
    })
    files = {str(p.relative_to(RUN)): sha(p) for p in sorted(RUN.glob("*.json")) if p.name != "artifact_sha256.json"}
    dump("artifact_sha256.json", {"status": "PASS", "file_count": len(files), "files": files})
    print(json.dumps({"status": "PASS", "package": str(RUN), "files": len(files), "external_composite": ext["authoritative_profile_composite"], "canonical_median": canonical["median_variance_ratio"]}, sort_keys=True))


if __name__ == "__main__":
    main()

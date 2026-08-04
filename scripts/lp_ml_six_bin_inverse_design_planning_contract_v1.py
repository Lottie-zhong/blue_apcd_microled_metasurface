import hashlib
import json
import subprocess
import csv
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
C = O / "clean_v2"
A = O / "analysis"
P = O / "plans/lp_ml_six_bin_inverse_design_planning_v1"
REPORT = ROOT / "reports/lp_ml_six_bin_inverse_design_planning_contract_v1.md"
QID = "LPML_R1_GLOBAL_SOBOL_054"
SEEDS = [11, 22, 33, 44, 55]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write(name, payload):
    path = P / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def git(args):
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True, capture_output=True, check=True).stdout.strip()


def main():
    P.mkdir(parents=True, exist_ok=True)
    merged = C / "lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv"
    split = C / "split_clean_v2.csv"
    norm = C / "normalization_clean_v2.json"
    checksums = json.loads((C / "clean_dataset_checksums_v2.json").read_text(encoding="utf-8"))
    expected = {
        "merged": "ca2fd154eed8e9b2f41b92c2f2aaa95f77d451c7047e4056f84a430c56e67336",
        "split": "2a4223f802204e870cc7d28d956f5c705f9442ccdbad2ad9bd10fecab07ce661",
        "normalization": "13c7855b48d8c34e674ea67cb343df9414306cf43a943efdec6bba001f864167",
    }
    actual = {"merged": sha(merged), "split": sha(split), "normalization": sha(norm)}
    assert actual == expected
    with merged.open(encoding="utf-8-sig", newline="") as f:
        clean_rows = list(csv.DictReader(f))
    assert len(clean_rows) == 2871
    assert not any(row.get("candidate_id") == QID for row in clean_rows)
    assert len({(row["candidate_id"], row["wavelength_nm"]) for row in clean_rows}) == 2871
    manifest = {
        "contract_version": "LP_ML_SIX_BIN_INVERSE_DESIGN_PLANNING_MANIFEST_V1",
        "status": "LP_ML_INVERSE_PLANNING_CONTRACT_READY",
        "planning_only": True,
        "solver_calls": 0,
        "candidate_generation_executed": False,
        "candidate_list_present": False,
        "runnable_solver_package_present": False,
        "geometry_054_admitted_rows": 0,
        "clean_source_hashes": actual,
        "creation_commit": git(["rev-parse", "HEAD"]),
        "upstream": git(["rev-parse", "--verify", "@{u}"]),
        "protected_reports_sha256": {
            "reports/lp_ml1a3_git_history_geometry_reconstruction.md": "9e46a7bd1927d65adc3a9cf9192040e7d239b839ed516adcd96870bf64bfcd02",
            "reports/stage11_4a20_legacy_fsp_object_inventory.md": "ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708",
        },
    }
    target = {
        "contract_version": "LP_ML_SIX_BIN_INVERSE_PHYSICAL_TARGET_V1",
        "status": "FROZEN_PLANNING_CONTRACT_ONLY",
        "target_type": "COMPLETE_COMPLEX_JONES",
        "explicitly_not": ["PHASE_ONLY", "TXX_ONLY", "CONSTITUENT_ADDITIVE_K6", "RECIPROCITY_ASSUMPTION"],
        "projector": {
            "symbol": "P_APCD",
            "source_contract": "outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_projector_guard_metric_definition_contract_v1.json",
            "source_sha256": "bb575391319f97e417ccac16be95c3e1d3569dece2363a9d1d338d2d7c1e74e5",
            "resolution_rule": "Use the frozen APCD projector definition without redefining absolute PASS/FAIL thresholds; no numerical projector is invented here.",
            "shape_error": "min_c ||J-c*P_APCD||_F / (||J||_F + epsilon)",
        },
        "jones_convention": "J=[[txx,txy],[tyx,tyy]]; x-input Ex=txx/Ey=tyx; y-input Ex=txy/Ey=tyy",
        "observable": "transmission-side coordinate-weighted full-period complex-field G0 with duplicate endpoint removal/reclosure and sqrt(T)/norm(weighted Ex,Ey)",
        "material": "APCD_TIO2_NATIVE_M1",
        "reference_plane": "field_monitor_z_1000_nm",
        "background": "air_n=1",
        "boundary": "x/y_periodic_z_PML_normal_incidence",
        "normalization": "sqrt(T)/norm(weighted Ex,weighted Ey)",
        "target_jones": "J_target,k = complex_scalar_k * P_APCD",
        "scalar_definition": "complex_scalar_k = rho_k * exp(i*(phi_offset + 60*k degrees)), rho_k > 0",
        "solver_calls": 0,
    }
    convention = {
        "contract_version": "LP_ML_SIX_BIN_TARGET_CONVENTION_V1",
        "bin_indices": list(range(6)),
        "phase_step_deg": 60.0,
        "phi_offset": {"kind": "free_common_offset", "domain_deg": [-30.0, 30.0], "periodic_equivalence_deg": 60.0},
        "complex_scalar": "rho_k*exp(i*(phi_offset + k*60deg))",
        "closure": {"adjacent_phase_error": "circular_distance(delta_phi,60deg)", "six_bin_closure": "circular_distance(sum(delta_phi),360deg)"},
        "offset_invariance": "subtract one common fitted phi_offset before phase-closure scoring",
        "amplitude_policy": "rho_k is continuous and scored for uniformity; no fixed amplitude is assumed",
        "projector_policy": "one frozen P_APCD shape for all bins; no per-bin projector redefinition",
        "solver_calls": 0,
    }
    checkpoint_hashes = {"C0": {}, "C1": {}, "C2": {}, "C3": {}, "C4": {}}
    c0 = O / "model_runtime_round1_frozen_v1"
    for seed in SEEDS:
        checkpoint_hashes["C0"][str(seed)] = sha(c0 / f"residual_mlp_seed_{seed}.pt")
    for kind in ["C1", "C2", "C3", "C4"]:
        for seed in SEEDS:
            checkpoint_hashes[kind][str(seed)] = sha(C / "model_runtime_recompetition_v2" / kind / f"residual_mlp_seed_{seed}.pt")
    consensus = {
        "contract_version": "LP_ML_SIX_BIN_MODEL_ROLE_AND_CONSENSUS_V1",
        "dataset_sha256": actual["merged"],
        "roles": {
            "C0": "CURRENT_CHAMPION_GLOBAL_DOMAIN_GUARD",
            "selected_blend": "PRIMARY_CONTINUOUS_GRADIENT_SCORER_ALPHA_0P95_C0_PLUS_0P05_C1",
            "C1_to_C4": "ENSEMBLE_DISPERSION_AND_ALTERNATIVE_MODEL_SENSITIVITY_ONLY",
            "ensemble_dispersion": "EPISTEMIC_UNCERTAINTY_PROXY_NOT_A_CONFIDENCE_INTERVAL",
            "C0_blend_disagreement": "EXTRAPOLATION_RISK_SIGNAL",
        },
        "checkpoint_sha256": checkpoint_hashes,
        "risk_classes": {
            "CONSENSUS_LOW_RISK": "all required models finite and disagreement <= validation-derived q50 scale",
            "CONSENSUS_MODERATE_RISK": "disagreement above validation q50 and <= validation q90 scale",
            "MODEL_DISAGREEMENT_HIGH_RISK": "disagreement > validation q90, outside clean training hull, or any model non-finite",
        },
        "threshold_source": "clean Round-1 and Round-2 train/validation residual distributions only",
        "test_guided_selection": False,
        "high_risk_policy": "high-risk candidates cannot be sole representative of a phase bin",
        "solver_calls": 0,
    }
    objective = {
        "contract_version": "LP_ML_SIX_BIN_INVERSE_OBJECTIVE_V1",
        "variables": ["J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"],
        "bounds_source": "outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_5d_design_space_contract_v1.json",
        "bounds": {"J1_side_nm": [108, 112], "J2_length_nm": [106, 110], "J2_width_nm": [98, 102], "D_nm": [196, 204], "Psi_deg": [-1.2, 1.2]},
        "fixed": {"H_nm": 500.0, "period_nm": [432.0, 432.0], "material": "APCD_TIO2_NATIVE_M1", "wavelength_nm": [450.0, 450.5, 451.0, 451.5, 452.0, 452.5, 453.0, 453.5, 454.0]},
        "terms": {
            "phase_target_error": "circular_distance(arg(<P_APCD,J>_F), arg(complex_scalar_target))",
            "projector_shape_error": "min_c ||J-c*P_APCD||_F/(||J||_F+epsilon)",
            "rank": "sigma2/sigma1 from complete raw complex J",
            "leakage": "Tyy+Txy+Tyx from complete raw complex J",
            "throughput_penalty": "normalized shortfall of selected-channel Txx against clean-training reference",
            "spectral_instability": "endpoint phase drift + phase slope + phase curvature + bin-order instability + throughput variation",
            "uncertainty": "ensemble dispersion proxy",
            "consensus": "C0 versus selected-blend disagreement",
            "manufacturing": "hard infeasibility gate; not a soft optical score",
        },
        "normalization": "each continuous term divided by max(pooled R1/R2 validation median absolute residual, validation IQR, epsilon); tests excluded",
        "recommended_initial_weights": {"phase": 1.0, "projector": 1.0, "rank": 1.0, "leakage": 1.0, "throughput": 0.5, "spectral": 1.0, "uncertainty": 0.5, "consensus": 1.0},
        "allowed_validation_only_adjustment": "each soft weight 0.5x to 2.0x; manufacturing remains hard; no adjustment from frozen tests",
        "forbidden": ["projector_BCE", "ambiguous_projection_error_apcd_v1_alias", "txy_equals_tyx", "test_guided_weight_selection", "D9_label"],
        "solver_calls": 0,
    }
    tuple_objective = {
        "contract_version": "LP_ML_SIX_BIN_TUPLE_OBJECTIVE_V1",
        "scope": "PLANNING_AND_RANKING_ONLY",
        "components": ["adjacent_phase_step_errors", "six_bin_phase_closure", "projector_shape_consistency", "amplitude_uniformity", "leakage_uniformity", "sigma_ratio_uniformity", "spectral_ordering_stability", "manufacturing_diversity", "model_uncertainty", "C0_blend_consensus"],
        "pareto_axes": ["phase_accuracy", "projector_shape", "throughput", "leakage", "sigma_ratio", "spectral_stability", "consensus", "uncertainty", "manufacturing_margin", "geometric_diversity"],
        "offset_invariance": True,
        "selection_policy": "retain a Pareto set per bin; no single weighted champion is authoritative",
        "forbidden": ["all_bins_same_geometry_family", "one_champion_only", "phase_proximity_only", "uncertainty_coverage_by_high_risk_only", "geometry_054", "constituent_additive_K6"],
        "solver_calls": 0,
    }
    optimization = {
        "contract_version": "LP_ML_SIX_BIN_OPTIMIZATION_METHOD_PLAN_V1",
        "status": "PLANNED_NOT_RUN",
        "method_1": {"name": "differentiable_multistart", "model": "selected_blend", "trajectories_per_bin_min": 100, "quantize_then_rescore": True, "candidate_generation_executed": False},
        "method_2": {"name": "bounded_derivative_free", "algorithm": "CMA-ES_or_equivalent_bounded_method", "role": "local-gradient miss and sensitivity diagnostic", "candidate_generation_executed": False},
        "retention_proposal": {"raw_candidates_per_bin_min": 20, "pareto_shortlist_per_bin": [10, 20]},
        "no_direct_target_to_geometry_network": True,
        "no_runnable_solver_package": True,
        "solver_calls": 0,
    }
    pareto = {
        "contract_version": "LP_ML_SIX_BIN_PARETO_SELECTION_V1",
        "per_bin": True,
        "objectives": tuple_objective["pareto_axes"],
        "hard_gates": ["manufacturing_valid", "gap_valid", "within_clean_design_bounds", "finite_complete_Jones_prediction", "not_geometry_054", "not_duplicate_training_geometry"],
        "risk_policy": "high-risk model-disagreement candidates may remain diagnostic but cannot be sole bin representative",
        "diversity_policy": "retain multiple geometry families and non-dominated manufacturing margins where available",
        "selection_data": "training/validation only; frozen tests are one-time post-selection evaluation",
        "candidate_list": "ABSENT_BY_CONTRACT",
        "solver_calls": 0,
    }
    budget = {
        "contract_version": "LP_ML_SIX_BIN_PROSPECTIVE_FDTD_BUDGET_PROPOSAL_V1",
        "authorization": "NOT_AUTHORIZED_BY_THIS_TASK",
        "proposed_scope": "single-dimer prospective formal weighted-G0 physics only",
        "proposed_geometry_count": "6_to_10_per_bin; 36_to_60 total across six bins",
        "proposed_subruns": "x_and_y_per_geometry; 72_to_120 total if both inputs are used",
        "wavelength_nm": 450.0,
        "required_contract": "separate future authorization, checkpoint-first, exact geometry/provenance, no dynamic replacement",
        "forbidden_now": ["solver", "FDTD", "inverse_FDTD", "Round-3", "new_geometry_execution", "six-bin_promotion", "K6"],
        "solver_calls": 0,
    }
    hierarchy = {
        "contract_version": "LP_ML_SIX_BIN_K6_VALIDATION_HIERARCHY_V1",
        "levels": [
            "LEVEL_1_SURROGATE_ONLY_OPTIMIZATION_AND_PARETO_FILTERING",
            "LEVEL_2_C0_BLEND_SEED_CONSENSUS_AUDIT",
            "LEVEL_3_SINGLE_DIMER_PROSPECTIVE_FDTD_SEPARATELY_AUTHORIZED",
            "LEVEL_4_FDTD_ASSIMILATION_AND_REQUIRED_RETRAINING",
            "LEVEL_5_SIX_BIN_TUPLE_SELECTION",
            "LEVEL_6_FULL_K6_SUPERCELL_FULL_WAVE",
            "LEVEL_7_BROADBAND_TOLERANCE_SOURCE_WEIGHTED_INTEGRATION",
        ],
        "constituent_additive_substitution": False,
        "promotion_now": False,
        "solver_calls": 0,
    }
    readiness = {
        "contract_version": "LP_ML_SIX_BIN_INVERSE_READINESS_GATE_V1",
        "outcome": "LP_ML_INVERSE_PLANNING_CONTRACT_READY",
        "pre_candidate_gates": [
            "clean_v2_hashes_unchanged",
            "C0_and_selected_blend_checkpoint_hashes_frozen",
            "P_APCD_source_contract_hash_resolved_before_candidate_generation",
            "single_phase_convention_and_60_degree_closure_frozen",
            "wavelength_weighting_frozen",
            "objective_normalization_from_train_validation_only",
            "manufacturing_bounds_frozen",
            "no_test_guided_weight_selection",
            "geometry_054_zero_rows",
            "protected_report_hashes_stable",
        ],
        "pre_future_fdtd_gates": [
            "multiple_manufacturable_candidates_per_bin",
            "low_or_moderate_consensus_support_per_bin",
            "at_least_one_feasible_tuple",
            "separate_solver_budget_authorization",
            "entered_failure_and_quarantine_policy_frozen",
        ],
        "no_candidate_generation": True,
        "no_solver_authorization": True,
    }
    artifacts = [
        ("lp_ml_six_bin_inverse_physical_target_contract_v1.json", target),
        ("lp_ml_six_bin_target_convention_v1.json", convention),
        ("lp_ml_six_bin_model_consensus_contract_v1.json", consensus),
        ("lp_ml_six_bin_inverse_objective_contract_v1.json", objective),
        ("lp_ml_six_bin_tuple_objective_contract_v1.json", tuple_objective),
        ("lp_ml_six_bin_optimization_method_plan_v1.json", optimization),
        ("lp_ml_six_bin_pareto_selection_contract_v1.json", pareto),
        ("lp_ml_six_bin_prospective_fdtd_budget_v1.json", budget),
        ("lp_ml_six_bin_k6_validation_hierarchy_v1.json", hierarchy),
        ("lp_ml_six_bin_inverse_readiness_gate_v1.json", readiness),
    ]
    written = {name: write(name, payload) for name, payload in artifacts}
    report = """# LP-ML Six-Bin Inverse-Design Planning Contract v1\n\n## Status\n\n`LP_ML_INVERSE_PLANNING_CONTRACT_READY`\n\nThis is an offline planning freeze only. No candidate geometry was generated, no runnable solver package was created, and solver/FDTD calls = 0.\n\n## Frozen inputs and model roles\n\nClean v2 remains 255 Round-1 geometries / 2295 rows, 64 Round-2 geometries / 576 rows, and 319 merged geometries / 2871 rows. Geometry 054 is quarantined with zero admitted rows. C0 remains the current champion/global guard; the C0/C1 alpha=0.95 blend is the primary planning challenger; C1-C4 seed ensembles provide dispersion and model-disagreement diagnostics, not confidence intervals.\n\n## Target Jones and six-bin convention\n\nEach target is a complete complex Jones matrix `J_target,k = complex_scalar_k * P_APCD`, with `complex_scalar_k = rho_k exp(i(phi_offset + 60 k degrees))`. The common phase offset is free and scored modulo the 60-degree equivalence. The projector shape is scalar-invariant and uses `min_c ||J-cP_APCD||_F / ||J||_F`; ambiguous legacy projection-error aliases are not used.\n\n## Inverse objective\n\nThe objective combines circular phase error, scalar-invariant projector shape error, sigma2/sigma1, raw-Jones leakage, throughput, spectral endpoint/slope/curvature/order stability, ensemble uncertainty, C0/blend disagreement, and a hard manufacturing gate. Normalization is from clean train/validation residual distributions only; frozen tests cannot tune weights.\n\n## Tuple and Pareto policy\n\nSix-bin selection is Pareto-based across phase, projector, throughput, leakage, rank, spectral stability, consensus, uncertainty, manufacturing margin and geometric diversity. No bin has a single authoritative champion; high-disagreement candidates cannot be sole representatives.\n\n## Future validation hierarchy\n\nSurrogate-only Pareto filtering precedes C0/blend consensus, separately authorized single-dimer FDTD, assimilation, tuple selection, full-K6 full-wave validation, and finally broadband/tolerance/source-weighted integration. Constituent-additive predictions cannot substitute for K6 full-wave validation.\n\n## Future budget proposal\n\nPlanning envelope only: 6-10 geometries per bin (36-60 total), x/y subruns if authorized (72-120 total), 450 nm only. This task authorizes none of those solver calls.\n\n## Hard gates\n\nClean hashes, protected reports, model checkpoint hashes and quarantine boundary must remain unchanged before any future candidate generation. No Round-3, inverse FDTD, six-bin promotion, K6 execution, geometry 054 use, or test-guided weighting is permitted here.\n"""
    REPORT.write_text(report, encoding="utf-8")
    manifest["artifact_sha256"] = {name: sha(path) for name, path in written.items()}
    manifest["artifact_sha256"][str(REPORT.relative_to(ROOT)).replace("\\", "/")] = sha(REPORT)
    write("lp_ml_six_bin_inverse_planning_manifest_v1.json", manifest)
    print(json.dumps({"status": manifest["status"], "output_dir": str(P), "artifact_count": len(written), "solver_calls": 0, "candidate_generation": False}, indent=2))


if __name__ == "__main__":
    main()

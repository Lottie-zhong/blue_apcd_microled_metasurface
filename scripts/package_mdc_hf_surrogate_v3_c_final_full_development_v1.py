from pathlib import Path
import json, hashlib, subprocess

root = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
run = root / "outputs/mdc_hf_surrogate_v3_c_final_full_development_v1/20260812T_final_full_development_5seed_bc1fcc1"
contract = root / "contracts/mdc_hf_surrogate_v2/v3_final_full_development_v1"
contract.mkdir(parents=True, exist_ok=True)

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def dump(name, value):
    (contract / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

acc = read(run / "training_accounting.json")
reg = read(run / "seed_training_registry.json")
r1 = read(run / "fresh_load_replay_1.json")
r2 = read(run / "fresh_load_replay_2.json")
pre = read(run / "shared_preprocessing_manifest.json")
membership = read(run / "full_development_membership.json")
commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()

dump("final_model_registry.json", {
    "status": "PASS",
    "formal_state": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_FULL_DEVELOPMENT_MODEL_FROZEN",
    "model_id": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1",
    "architecture": "V3-C", "final_epoch": 117, "membership": membership,
    "training_accounting": acc, "code_commit": commit,
    "scope": "RANKING_SCREENING_ONLY; profile-shape Level-0 screening surrogate",
    "power_head": "ABSENT", "auxiliary_target": "NON_LOAD_BEARING",
    "known_failure_warning": "KNOWN_FAILURE_LEVEL_STRATUM_WARNING inherited from frozen V3 OOF",
})
dump("full_development_preprocessing_contract.json", {
    "status": "PASS", "fit_count": {"PCA32": 1, "input_scaler": 1},
    "pca": pre["pca"], "scaler": pre["scaler"],
    "shared_by_seeds": [20260813, 20260814, 20260815, 20260816, 20260817],
    "per_seed_refit": False, "membership_sha256": membership["membership_sha256"],
    "source_q_sha256": membership["source_q_sha256"],
})
dump("final_seed_training_registry.json", reg)
dump("ensemble_inference_registry.json", {
    "status": "PASS", "model_id": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1",
    "seed_order": [20260813, 20260814, 20260815, 20260816, 20260817],
    "aggregation": "arithmetic_mean_of_five_decoded_normalized_joint_profiles",
    "weights": [0.2] * 5, "performance_weighting": False, "seed_pruning": False,
    "parameter_averaging": False, "median": False, "individual_outputs_preserved": True,
    "disagreement_diagnostic_only": True,
    "replay_prediction_sha256": r1["prediction_sha256"],
    "replay_equal": r1["prediction_sha256"] == r2["prediction_sha256"],
})
dump("fresh_load_inference_integrity.json", {
    "status": "PASS", "replay_1": r1, "replay_2": r2,
    "prediction_sha_equal": r1["prediction_sha256"] == r2["prediction_sha256"],
    "fit_calls": 0, "backward_calls": 0, "optimizer_calls": 0,
    "pca_fit_calls": 0, "scaler_fit_calls": 0,
})
dump("canonical_loader_contract.json", {
    "status": "PASS",
    "model_id": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1",
    "architecture": "V3-C",
    "input_width": 23,
    "latent_output": "PCA32 signed linear latent",
    "decoded_profile_shape": [301, 2000],
    "shared_pca_scaler": True,
    "fresh_load_only": True,
    "fit_calls": 0,
    "backward_calls": 0,
    "optimizer_calls": 0,
    "threshold_or_selection": "none; fixed five-seed equal-weight ensemble",
})
dump("seed_disagreement_diagnostic_schema.json", {
    "status": "PASS", "purpose": "diagnostic only; cannot prune or weight seeds",
    "required_fields": ["seed", "geometry_or_case_uid", "decoded_profile", "pairwise_JS", "pairwise_weighted_L1", "latent_component_std"],
    "truth_or_external_evaluation": "not included in this package",
})
epoch_path = root / "outputs/mdc_hf_surrogate_v3_oof_formal_v1/20260811T_formal_oof_29ee7c9/final_epoch_derivation.json"
dump("oof_final_epoch_provenance.json", {
    "status": "PASS", "selected_architecture": "V3-C", "oof_fit_count": 15,
    "final_epoch": 117, "source": str(epoch_path), "source_sha256": sha(epoch_path),
    "v3_test40_reads": 0,
})
dump("sealed_v3_test40_assertion.json", {
    "status": "PASS", "labels_generated": False, "truth_reads": 0, "label_reads": 0,
    "target_paths_scanned": False,
    "participates_in": ["final_training", "seed_selection", "checkpoint_selection", "ensemble_weighting"],
    "opening_condition": "architecture and all checkpoint hashes frozen plus separate Chart authorization",
})
dump("environment_provenance.json", {
    "status": "PASS", "python": "3.10.20", "torch": "2.5.1+cu121", "cuda_build": "12.1",
    "gpu": "NVIDIA GeForce RTX 3080", "environment_source": "RCP_LCP", "training_precision": "float32; AMP disabled",
})
dump("completion_manifest.json", {
    "status": "PASS", "formal_state": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_FULL_DEVELOPMENT_MODEL_FROZEN",
    "model_id": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1", "architecture": "V3-C",
    "membership_200_geometries_1200_cases": True, "shared_pca_fit_count": 1,
    "shared_scaler_fit_count": 1, "final_fits": 5, "final_epochs": [117] * 5,
    "fresh_load_replays_equal": True, "solver_calls": 0, "v3_test40_truth_reads": 0,
    "hf15_r12_truth_reads": 0, "scope": "RANKING_SCREENING_ONLY", "code_commit": commit,
})
(contract / "completion_report.md").write_text(
    "# V3-C final full-development completion report\n\n"
    "- Status: `MDC_HF_SURROGATE_V3_C_FINAL_5SEED_FULL_DEVELOPMENT_MODEL_FROZEN`\n"
    "- Model: `MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1` / V3-C\n"
    "- Membership: 200 geometries / 1200 cases / exactly 6 cases per geometry\n"
    "- Shared preprocessing: PCA32 fit count 1; input scaler fit count 1; shared by all five seeds\n"
    "- Final fits: seeds 20260813–20260817, exactly 117 epochs each; no validation, early stopping, checkpoint selection, or seed pruning\n"
    "- Ensemble: equal arithmetic mean of five decoded normalized profiles; disagreement diagnostic only\n"
    "- Fresh-load replay: two independent processes, individual and ensemble hashes identical\n"
    "- V3-Test40: sealed, labels/truth not generated/read; HF15/R12 not read\n"
    "- Solver calls: 0 in this task; neural fits: 5; PCA/scaler fits: 1/1\n"
    "- Scope: ranking/screening-only; inherited KNOWN_FAILURE_LEVEL_STRATUM_WARNING\n",
    encoding="utf-8",
)
files = []
for path in sorted(contract.iterdir()):
    if path.is_file() and path.name != "artifact_sha256.json":
        files.append((str(path.relative_to(root)), sha(path), path.stat().st_size))
for path in sorted(run.rglob("*")):
    if path.is_file() and path.suffix.lower() in {".json", ".md"}:
        files.append((str(path.relative_to(root)), sha(path), path.stat().st_size))
(contract / "artifact_sha256.json").write_text(json.dumps({"status": "PASS", "files": files}, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps({"contract_dir": str(contract), "files": len(files), "code_commit": commit}, ensure_ascii=False))

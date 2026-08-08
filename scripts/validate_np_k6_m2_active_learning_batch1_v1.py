"""Standalone validator for NP K6 M2 active-learning Batch1 selection."""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m2_active_learning_batch1_selection_v1"
DATASET = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
M1 = ROOT / "outputs" / "np_k6_m1_pilot_training_v1"
GEOM = ROOT / "outputs" / "np_k6_ml_d0_database_foundation_v1" / "k6_hf_pilot_geometry_manifest.json"
SPLIT = ROOT / "outputs" / "np_k6_ml_d0_database_foundation_v1" / "k6_split_manifest.json"
WAVELENGTHS = list(range(445, 456))
SEEDS = [17, 29, 43]
GENERATOR = "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2"
STACK = "NP_K6_INDEPENDENT_STACK_PILOT_V1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate() -> dict:
    checks = {}
    errors = []
    def check(name, condition, detail=None):
        checks[name] = bool(condition)
        if not condition:
            errors.append({"check": name, "detail": detail})
    state = json.loads((OUT / "state_reconciliation.json").read_text(encoding="utf-8"))
    p0 = json.loads((DATASET / "pilot_training_state.json").read_text(encoding="utf-8"))
    m1gate = json.loads((M1 / "training_gate_summary.json").read_text(encoding="utf-8"))
    check("head_reconciled", state["P0_REVALIDATED_AT_HEAD_35B7BFE"] is True)
    check("p0_stage_local_status", state["P0_STAGE_LOCAL_STATUS"] == "NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY")
    check("m1_stage_status", state["M1_STAGE_LOCAL_STATUS"] == "NP_K6_M1_PILOT_SURROGATE_SMOKE_TRAINING_COMPLETE_ACTIVE_LEARNING_READY")
    check("global_pending_state", state["global_authoritative_state"] == "NP_K6_M2_ACTIVE_LEARNING_BATCH1_SELECTED_FDTD_AUTHORIZATION_PENDING")
    check("p0_formal_observations", state["P0_FORMAL_HF_OBSERVATIONS"] == 66 and p0["formal_observation_count"] == 66)
    check("p0_validator_pass", p0["status"] == "NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY" and p0["pilot_training_authorized"] is True)
    check("m1_gate_status", m1gate["status"] == "NP_K6_M1_PILOT_SURROGATE_SMOKE_TRAINING_COMPLETE_ACTIVE_LEARNING_READY")
    check("m1_local_training_state_preserved", state["M1_real_training_started"] is True and m1gate["real_training_started"] is True)
    check("m1_no_solver", state["M1_solver_calls"] == 0 and m1gate["solver_calls"] == 0)
    check("sealed_access_zero", state["M1_sealed_access"] == 0 and state["M2_sealed_access"] == 0 and m1gate["sealed_test_untouched"] is True)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    geom = json.loads(GEOM.read_text(encoding="utf-8"))
    pool = json.loads((OUT / "candidate_pool_audit.json").read_text(encoding="utf-8"))
    check("candidate_split_authority", pool["geometry_manifest_sha256"] == sha256(GEOM) and pool["split_manifest_sha256"] == sha256(SPLIT))
    check("candidate_pool_counts", pool["development_total"] == 48 and pool["sealed_total"] == 12 and pool["already_formal_hf_labeled"] == 3 and pool["eligible_unlabeled_development"] == 45)
    check("sealed_excluded", pool["sealed_excluded_count"] == 12 and pool["sealed_access"] == 0)
    features = read_csv(OUT / "candidate_acquisition_features.csv")
    selected = read_csv(OUT / "batch1_selected_geometries.csv")
    novelty = read_csv(OUT / "geometry_novelty_metrics.csv")
    check("candidate_feature_count", len(features) == 45)
    check("novelty_count", len(novelty) == 45)
    check("selected_exactly_six", len(selected) == 6)
    check("selected_unique_hashes", len({r["geometry_hash"] for r in selected}) == 6)
    check("slot_order", [r["slot"] for r in selected] == ["U1", "U2", "D1", "D2", "X1", "P1"])
    feature_hashes = {r["geometry_hash"] for r in features}
    formal_hashes = {r["geometry_hash"] for r in csv_rows(DATASET / "hf_observations_long.csv")}
    sealed_hashes = {r["geometry_hash"] for r in geom["rows"] if r["pilot_role"] == "sealed_test_pilot"}
    check("selected_in_eligible_pool", all(r["geometry_hash"] in feature_hashes and r["geometry_hash"] not in formal_hashes and r["geometry_hash"] not in sealed_hashes for r in selected))
    check("lf_authority_fields", all(r.get("lf_passing_status") and r.get("lf_pareto_status") for r in features + selected))
    check("prediction_shape", count_gzip(OUT / "cnn_ensemble_predictions.csv.gz") == 45 * 22)
    norm = json.loads((OUT / "acquisition_normalization.json").read_text(encoding="utf-8"))
    check("eligible_only_normalization", norm["fit_scope"] == "eligible_development_pool_only" and norm["sealed_stats_used"] is False and norm["formal_hf_targets_used"] is False)
    dist = json.loads((OUT / "geometry_distance_matrix_summary.json").read_text(encoding="utf-8"))
    check("distance_threshold_empirical_25th", dist["pairwise_count"] == 990 and dist["near_duplicate_threshold_25th_percentile"] > 0)
    mlp = json.loads((OUT / "mlp_ensemble_manifest.json").read_text(encoding="utf-8"))
    check("mlp_committee_provenance", mlp["purpose"] == "ACQUISITION_ONLY" and mlp["seed_count"] == 3 and mlp["checkpoint_count"] == 3 and sorted(x["seed"] for x in mlp["models"]) == SEEDS and all(x["training_rows"] == 66 and x["sealed_access"] == 0 and x["solver_calls"] == 0 and sha256(Path(x["checkpoint_path"])) == x["checkpoint_sha256"] for x in mlp["models"]))
    cnn = json.loads((OUT / "cnn_ensemble_provenance.json").read_text(encoding="utf-8"))
    check("cnn_checkpoint_provenance", cnn["purpose"] == "ACQUISITION_ONLY" and cnn["checkpoint_count"] == 3 and all(Path(x["checkpoint_path"]).exists() and sha256(Path(x["checkpoint_path"])) == x["checkpoint_sha256"] for x in cnn["models"]))
    task = json.loads((OUT / "batch1_task_manifest.json").read_text(encoding="utf-8"))
    tasks = task["tasks"]
    check("exactly_twelve_tasks", len(tasks) == 12 and task["task_count"] == 12)
    check("tasks_two_polarizations", sorted({t["polarization"] for t in tasks}) == ["p", "s"])
    check("tasks_geometry_count", len({t["geometry_hash"] for t in tasks}) == 6)
    check("tasks_entered_run_zero", all(t["entered"] is False and t["solver_entered"] is False and t["run_invocation_count"] == 0 for t in tasks))
    check("tasks_solver_and_label_flags", all(t["solver_authorized"] is False and t["training_label"] is False and t["candidate_performance_label"] is False and t["development"] is True and t["sealed"] is False for t in tasks))
    check("tasks_context_contract", all(t["wavelengths_nm"] == WAVELENGTHS and t["wavelength_count"] == 11 and t["u_x"] == 0.0 and t["k_y"] == 0.0 and t["generator_id"] == GENERATOR and t["interface_stack_id"] == STACK and t["maximum_simulation_time_s"] == 3e-12 and t["auto_shutoff_threshold"] == 1e-5 for t in tasks))
    check("task_observation_projection", task["current_formal_observations"] == 66 and task["expected_new_observations"] == 132 and task["expected_after_success"] == 198)
    rationale = json.loads((OUT / "batch1_selection_rationale.json").read_text(encoding="utf-8"))
    check("selection_representation_gate", rationale["selection_order"] == ["U1","U2","D1","D2","X1","P1"] and rationale["representation_gate"] == {"uncertainty_slots":2,"diversity_slots":2,"disagreement_slots":1,"performance_slots":1})
    check("selection_no_single_score", rationale["no_top6_single_score"] is True and rationale["no_all_lf_passing_or_pareto_only"] is True)
    check("no_p0_rerun_or_m1_retrain", pool["no_p0_rerun"] is True and pool["no_m1_retraining"] is True and cnn["m1_retrained"] is False)
    checksum = json.loads((OUT / "checksum_manifest.json").read_text(encoding="utf-8"))
    checksum_ok = all((OUT / x["path"]).exists() and sha256(OUT / x["path"]) == x["sha256"] for x in checksum["files"])
    check("lightweight_checksum_manifest", checksum_ok)
    check("runtime_checkpoints_excluded", checksum["runtime_checkpoints_excluded_from_git"] is True)
    return {"status": "PASS" if not errors else "FAIL", "checks": checks, "errors": errors, "candidate_count": len(features), "selected_count": len(selected), "task_count": len(tasks), "prediction_rows": 45 * 22, "solver_calls": 0, "sealed_access": 0}


def csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def count_gzip(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)

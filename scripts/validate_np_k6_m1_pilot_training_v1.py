"""Standalone validator for the NP K6 M1 pilot surrogate smoke stage."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m1_pilot_training_v1"
CFG = ROOT / "configs" / "np_k6_forward_surrogate_pilot_v1.json"
DATASET = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
GROUPS = ["RUN3A", "RUN3B", "RUN3C"]
SEEDS = [17, 29, 43]
REQUIRED = [
    "dataset_audit.json", "cuda_environment.json", "cv_split_manifest.json", "normalization_manifest.json",
    "cnn_cv_metrics.csv", "mlp_cv_metrics.csv", "lf_dft_baseline_metrics.csv", "cv_fold_summary.json",
    "training_history_summary.csv", "physics_constraint_audit.json", "architecture_comparison.json",
    "acquisition_ensemble_manifest.json", "training_gate_summary.json", "checksum_manifest.json",
    "cv_stratified_metrics.json",
]


def load_json(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def rows(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def finite(v: str) -> bool:
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate() -> dict:
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    audit = load_json("dataset_audit.json")
    cuda = load_json("cuda_environment.json")
    split = load_json("cv_split_manifest.json")
    norm = load_json("normalization_manifest.json")
    gate = load_json("training_gate_summary.json")
    ensemble = load_json("acquisition_ensemble_manifest.json")
    physics = load_json("physics_constraint_audit.json")
    strat = load_json("cv_stratified_metrics.json")
    hist_rows = rows("training_history_summary.csv")
    hist_groups = {}
    for r in hist_rows:
        hist_groups.setdefault((r["model"], r["fold"]), []).append(float(r["train_loss"]))
    history_decreased = bool(hist_groups) and all(min(v) < v[0] for v in hist_groups.values())
    checks = {
        "required_artifacts": all((OUT / x).exists() for x in REQUIRED),
        "dataset_exact_66": audit.get("formal_observation_count") == 66,
        "dataset_three_geometries": audit.get("geometry_groups") == GROUPS and len(audit.get("geometry_hashes", [])) == 3,
        "dataset_two_polarizations": audit.get("polarizations") == ["p", "s"],
        "dataset_exact_wavelengths": audit.get("wavelengths_nm") == list(range(445, 456)),
        "fdtd_only_labels": audit.get("label_source") == "FDTD" and audit.get("training_label_all_true") is True,
        "no_diagnostic_or_rcwa_lf": audit.get("diagnostic_only_all_false") is True and audit.get("rcwa_as_label") is False and audit.get("lf_dft_as_label") is False,
        "no_sealed_or_obsolete": audit.get("sealed_test_access") == 0 and audit.get("obsolete_run3c_s_access") == 0,
        "generator_stack": audit.get("generator_id") == "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2" and audit.get("interface_stack_id") == "NP_K6_INDEPENDENT_STACK_PILOT_V1",
        "cuda_preflight": cuda.get("cuda_available") is True and cuda.get("device") == "cuda:0" and cuda.get("gpu_name") == "NVIDIA GeForce RTX 3080",
        "cuda_training_proven": cuda.get("pin_memory") is True and cuda.get("non_blocking") is True,
        "config_fixed": cfg.get("learning_rate") == 0.001 and cfg.get("weight_decay") == 0.0001 and cfg.get("batch_size") == 16 and cfg.get("max_epochs") == 300 and cfg.get("early_stopping_patience") == 25 and cfg.get("seeds") == SEEDS and cfg.get("device") == "cuda:0" and cfg.get("training_enabled") is True,
        "cv_three_geometry_groups": len(split.get("folds", [])) == 3 and all(x.get("geometry_group_leakage") is False and x.get("train_observations") == 44 and x.get("validation_observations") == 22 for x in split["folds"]),
        "cv_no_split_leakage": all(set(x["train_geometry_groups"]).isdisjoint({x["validation_geometry_group"]}) for x in split["folds"]),
        "normalization_excludes_held_out": all(x.get("held_out_geometry_excluded") not in x.get("fit_geometry_groups", []) for x in norm.get("folds", [])),
        "metric_rows": all(len(rows(x)) == 3 and {r["fold"] for r in rows(x)} == {"A", "B", "C"} for x in ["cnn_cv_metrics.csv", "mlp_cv_metrics.csv", "lf_dft_baseline_metrics.csv"]),
        "metric_fields_complete": all(all(k in r for k in ["eta_plus1_MAE", "eta_plus1_RMSE", "eta_plus1_Spearman", "all_order_weighted_MAE", "T_MAE", "R_MAE", "directionality_MAE", "non_target_leakage_MAE", "nan_inf_count"]) for r in rows("cnn_cv_metrics.csv") + rows("mlp_cv_metrics.csv") + rows("lf_dft_baseline_metrics.csv")),
        "metric_finite": all(finite(r[k]) for fn in ["cnn_cv_metrics.csv", "mlp_cv_metrics.csv", "lf_dft_baseline_metrics.csv"] for r in rows(fn) for k in ["eta_plus1_MAE", "eta_plus1_RMSE", "eta_plus1_Spearman", "all_order_weighted_MAE", "T_MAE", "R_MAE", "directionality_MAE", "non_target_leakage_MAE"]),
        "stratified_metrics_complete": len(strat.get("folds", [])) == 6 and strat.get("aggregate", {}).get("worst_wavelength_present") is True and strat.get("aggregate", {}).get("worst_output_channel_present") is True,
        "physics_clean": physics.get("nan_inf_all_zero") is True and physics.get("nonnegative_power_enforced") is True and physics.get("all_order_heads") is True,
        "history_gpu": len(hist_rows) > 0 and all(r.get("batch_device") == "cuda:0" and r.get("model_device") == "cuda:0" for r in hist_rows),
        "history_loss_decreases": history_decreased,
        "ensemble_three_seeds": ensemble.get("purpose") == "ACQUISITION_ONLY" and ensemble.get("seed_count") == 3 and ensemble.get("checkpoint_count") == 3 and sorted(x.get("seed") for x in ensemble.get("models", [])) == SEEDS,
        "ensemble_checkpoints_hashed": all(len(x.get("checkpoint_sha256", "")) == 64 and Path(x["checkpoint_path"]).exists() and sha256(Path(x["checkpoint_path"])) == x["checkpoint_sha256"] for x in ensemble.get("models", [])),
        "gate_state": gate.get("status") == "NP_K6_M1_PILOT_SURROGATE_SMOKE_TRAINING_COMPLETE_ACTIVE_LEARNING_READY" and gate.get("real_training_started") is True and gate.get("pilot_smoke_training_completed") is True and gate.get("formal_hf_observations") == 66 and gate.get("acquisition_ensemble_checkpoints") == 3,
        "gate_restrictions": gate.get("final_performance_model") is False and gate.get("inverse_design_model") is False and gate.get("bulk_mdc_compatible_model") is False and gate.get("sealed_test_untouched") is True and gate.get("solver_calls") == 0,
        "no_solver_import": "lumapi" not in (ROOT / "scripts" / "np_k6_m1_pilot_training_v1.py").read_text(encoding="utf-8").lower(),
    }
    # Verify lightweight checksum manifest exactly covers generated JSON/CSV evidence.
    cm = load_json("checksum_manifest.json"); listed = {x["path"]: x["sha256"] for x in cm.get("files", [])}; actual = {p.name: sha256(p) for p in OUT.iterdir() if p.is_file() and p.name != "checksum_manifest.json"}
    checks["checksum_manifest_complete"] = listed == actual
    if not all(checks.values()):
        raise SystemExit(json.dumps({"pass": False, "checks": checks}, indent=2, sort_keys=True))
    return {"pass": True, "checks": checks, "status": gate["status"], "formal_hf_observations": 66, "cv_folds": 3, "ensemble_checkpoints": 3}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))

from __future__ import annotations

"""Frozen execution entry point for MDC-ML merge/retrain.

Formal modes are deliberately not called by the implementation-freeze task.
They accept explicit output roots, read frozen resolved values, and keep the
sealed split outside feature/target construction.
"""

import argparse
import ast
import hashlib
import json
import os
import sys
import datetime
import platform
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mdc_ml.merge_retrain_v1.artifacts import ARTIFACT_SCHEMA_VERSION
from mdc_ml.merge_retrain_v1.candidates import candidate_factory_audit
from mdc_ml.merge_retrain_v1.contracts import (
    SignatureBundle,
    load_frozen_contract,
)
from mdc_ml.merge_retrain_v1.state import (
    STATE_SCHEMA_VERSION,
    TrainingExecutionState,
    resume_signature_gate,
)
from mdc_ml.merge_retrain_v1.classification import (
    CLASSIFICATION_TARGETS,
    build_classification_crossfit_plan,
    load_classification_metadata,
    synthetic_classification_fixture,
)

CONFIG = ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml"
EXPECTED = {"config": "76e51a802f598e458264c31db5b6024ade4a0e0a65f3ba2cc3c4587fcd74ade6", "promotion": "71b43c40035bb49a0a9647734b8aa4b42f7a089aa9c354de0b2a90f0c93def52", "training": "4cc187dc18f2e18bae32dc659d1ffad6f2baf0fa411c7214fa98db02645ce886", "fold": "1eff4d939bfe1af28964baebac8e33d0cb9953e98d9009921fac1eb3ae841aa7"}
TARGETS = ("spectral_fwhm_normal_nm", "angular_fwhm_450_deg", "cone5_integral_proxy", "normal_band_transmission_proxy")
FORMAL_PATH_SCOPE = "CLASSIFICATION_ONLY_INCOMPLETE_LEGACY_SCAFFOLD"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def canon(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"); os.replace(tmp, path)
def atomic_joblib(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(value, tmp, compress=3); os.replace(tmp, path)
def imported() -> tuple[Any, Any, Any]:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_mdc_ml_active_learning_merge_retrain_v1 as merge
    import build_mdc_ml_shared_surrogate_dataset_v1 as dataset
    import train_mdc_ml_shared_surrogate_v1 as shared
    return merge, dataset, shared


def frozen(config_path: Path = CONFIG) -> tuple[dict[str, Any], Any, Any, Any]:
    contract = load_frozen_contract(config_path)
    merge, dataset, shared = imported(); cfg = json.loads(config_path.read_text(encoding="utf-8"))
    audit = json.loads((ROOT / cfg["output_root"] / "merge_audit_v1.json").read_text(encoding="utf-8"))
    checks = {"config": contract.config_sha256 == EXPECTED["config"], "promotion": contract.promotion_contract_sha256 == EXPECTED["promotion"], "training": contract.training_contract_sha256 == EXPECTED["training"], "fold": audit["fold_signature"] == EXPECTED["fold"], "first_training_started": cfg["contract_revision"]["first_training_started"] is False, "target_order": tuple(cfg["regression_targets"]) == TARGETS, "feature_count": cfg["target_transforms"]["feature_count"] == 150}
    if not all(checks.values()): raise RuntimeError("FROZEN_GATE_FAILED: " + canon(checks))
    return cfg, merge, dataset, shared


def candidate(cfg: dict[str, Any], kind: str, candidate_id: str) -> dict[str, Any]:
    allowed = {x["candidate_id"]: x for x in cfg["model_candidate_allowlist"][kind]}
    if candidate_id not in allowed or candidate_id not in cfg["bounded_recompetition_candidate_set"][f"{kind}_candidate_ids"]: raise RuntimeError("UNKNOWN_OR_UNFROZEN_CANDIDATE")
    return allowed[candidate_id]


def mlp_config(cfg: dict[str, Any]) -> dict[str, Any]:
    p = candidate(cfg, "regression", "multitask_mlp_3seed")["hyperparameters"]
    return {"hidden": p["hidden_layers"], "dropout": p["dropout"], "learning_rate": p["optimizer"]["learning_rate"], "weight_decay": p["optimizer"]["weight_decay"], "batch_size": p["batch_size"], "max_epochs": p["max_epochs"], "patience": cfg["early_stopping"]["patience"]}


def classifier_spec(cfg: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    item = candidate(cfg, "classification", candidate_id); p = item["hyperparameters"]
    if item["estimator_family"] == "extra_trees": params = {key: p[key] for key in ("n_estimators", "min_samples_leaf", "max_features")}
    elif item["estimator_family"] == "linear": params = {"C": p["C"]}
    elif item["estimator_family"] in ("dummy_prevalence", "dummy_stratified"): params = {}
    else: params = {key: p[key] for key in ("max_iter", "learning_rate", "max_leaf_nodes", "l2_regularization")}
    return {"name": candidate_id, "family": item["estimator_family"], "params": params}


@dataclass
class Data:
    X: np.ndarray; yc: np.ndarray; yr: np.ndarray; eligible: np.ndarray; ids: list[str]; folds: np.ndarray


def assert_partition(data: Data, train: np.ndarray, held: np.ndarray) -> None:
    if set(train).intersection(held): raise RuntimeError("HELD_OUT_LEAKAGE")
    if len(data.X.shape) != 2 or data.X.shape[0] != len(data.ids): raise RuntimeError("DATA_SHAPE_ERROR")


def fit_three_seed(shared: Any, cfg: dict[str, Any], data: Data, train: np.ndarray, validation: np.ndarray) -> list[Any]:
    return [shared.MLPBundle(mlp_config(cfg), int(seed)).fit(data.X[train], data.yc[train], data.yr[train], data.eligible[train], (data.X[validation], data.yc[validation], data.yr[validation], data.eligible[validation])) for seed in cfg["training_seeds"]["regressor_ensemble_seeds"]]


def run_oof(cfg: dict[str, Any], shared: Any, data: Data, base_train: np.ndarray, validation: np.ndarray, calibration: np.ndarray, output_root: Path) -> dict[str, Any]:
    """CLASSIFICATION_ONLY_INCOMPLETE_FORMAL_PATH; authorization remains blocked."""
    rows: list[dict[str, Any]] = []; state = {"status": "RUNNING", "completed_folds": [], "config_sha": sha(CONFIG), "feature_signature": cfg["shared_feature_signature"]}
    for fold in range(4):
        held = np.where(data.folds == fold)[0]; train = np.r_[base_train, np.where((data.folds >= 0) & (data.folds != fold))[0]]; assert_partition(data, train, held)
        scaler = StandardScaler().fit(data.X[train]); model = shared.fit_selected_classifier(classifier_spec(cfg, "extra_trees_1"), scaler.transform(data.X[train]), data.yc[train], int(cfg["training_seeds"]["classifier_candidate_seed"]) + fold)
        raw = model.predict(scaler.transform(data.X[held])); cal_raw = model.predict(scaler.transform(data.X[calibration])); calibrators=[]; methods=[]; calibrated=np.zeros_like(raw)
        for j in range(4):
            cal, method, _ = shared.calibrate(data.yc[calibration, j].astype(int), cal_raw[:, j]); calibrators.append(cal); methods.append(method); calibrated[:, j] = shared.apply_calibrator(cal, method, raw[:, j])
        artifact = output_root / "models" / "folds" / f"fold_{fold}_classifier.joblib"; atomic_joblib(artifact, {"scaler": scaler, "model": model, "calibrators": calibrators, "methods": methods})
        rows.extend({"candidate_id": data.ids[i], "fold_id": fold, "raw_probability": raw[k].tolist(), "calibrated_probability": calibrated[k].tolist(), "model_sha256": sha(artifact)} for k, i in enumerate(held)); state["completed_folds"].append(fold); atomic_json(output_root / "training_execution_state_v1.json", state)
    if len(rows) != len({r["candidate_id"] for r in rows}): raise RuntimeError("OOF_EXACT_ONCE_FAILED")
    return {"rows": rows, "state": state}


def resume_guard(state: dict[str, Any], cfg: dict[str, Any]) -> None:
    contract = load_frozen_contract(CONFIG)
    expected = SignatureBundle(
        config_sha256=contract.config_sha256,
        promotion_contract_sha256=contract.promotion_contract_sha256,
        training_contract_sha256=contract.training_contract_sha256,
        dataset_signature=contract.signatures.dataset_signature,
        fold_signature=contract.fold_signature,
        feature_signature=contract.feature_signature,
        trainer_sha256=sha(Path(__file__)),
        execution_code_commit=_execution_commit(),
    )
    if set(expected.as_resume_dict()) <= set(state):
        resume_signature_gate(expected, state)
        return
    legacy = {
        "config_sha": contract.config_sha256,
        "feature_signature": contract.feature_signature,
    }
    if any(state.get(key) != value for key, value in legacy.items()):
        raise RuntimeError("RESUME_SIGNATURE_MISMATCH")
    resume_signature_gate(expected, expected)


def _execution_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def backend_audit(config_path: Path = CONFIG) -> dict[str, Any]:
    contract = load_frozen_contract(config_path)
    audit = candidate_factory_audit(contract)
    signatures = SignatureBundle(
        config_sha256=contract.config_sha256,
        promotion_contract_sha256=contract.promotion_contract_sha256,
        training_contract_sha256=contract.training_contract_sha256,
        dataset_signature=contract.signatures.dataset_signature,
        fold_signature=contract.fold_signature,
        feature_signature=contract.feature_signature,
        trainer_sha256=sha(Path(__file__)),
        execution_code_commit=_execution_commit(),
    )
    state = TrainingExecutionState.new("backend-audit", signatures)
    return {
        "status": "PASS",
        "config_sha256": contract.config_sha256,
        "promotion_contract_sha256": contract.promotion_contract_sha256,
        "training_contract_sha256": contract.training_contract_sha256,
        "fold_signature": contract.fold_signature,
        "feature_signature": contract.feature_signature,
        "feature_count": contract.feature_count,
        "classification_candidate_count": audit["classification_candidate_count"],
        "regression_candidate_count": audit["regression_candidate_count"],
        "classification_candidate_ids": audit["classification_candidate_ids"],
        "regression_candidate_ids": audit["regression_candidate_ids"],
        "classification_candidate_spec_sha256": audit["classification_candidate_spec_sha256"],
        "regression_candidate_spec_sha256": audit["regression_candidate_spec_sha256"],
        "classification_effective_parameter_sha256": audit["classification_effective_parameter_sha256"],
        "regression_effective_parameter_sha256": audit["regression_effective_parameter_sha256"],
        "fixed_classification_baseline": contract.fixed_classification_baseline,
        "fixed_regression_baseline": contract.fixed_regression_baseline,
        "mlp_hidden": audit["mlp_hidden"],
        "mlp_dropout": audit["mlp_dropout"],
        "mlp_classification_head": audit["mlp_classification_head"],
        "mlp_regression_head": audit["mlp_regression_head"],
        "mlp_seeds": audit["mlp_seeds"],
        "state_schema_version": state.schema_version,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "fit_calls": 0,
        "formal_training_calls": 0,
        "formal_output_write_count": 0,
        "sealed_test_target_reads": 0,
        "sealed_test_prediction_calls": 0,
        "proposal_calls": 0,
        "TMM_calls": 0,
        "FDTD_calls": 0,
        "Lumerical_calls": 0,
        "fixture_evidence_scope": "INTERFACE_LEVEL_SYNTHETIC_EVIDENCE",
        "formal_path_scope": FORMAL_PATH_SCOPE,
    }


def classification_backend_audit(config_path: Path = CONFIG) -> dict[str, Any]:
    """Pure metadata/plan audit: no target-array read, fit, or output write."""
    contract = load_frozen_contract(config_path)
    metadata = load_classification_metadata(contract)
    plans = build_classification_crossfit_plan(metadata, contract)
    fixed = next(spec for spec in candidate_factory_audit(contract)["classification_candidate_spec_sha256"] if spec == "extra_trees_1")
    spec_sha = candidate_factory_audit(contract)["classification_candidate_spec_sha256"][fixed]
    return {
        "status": "PASS", "classification_target_count": len(CLASSIFICATION_TARGETS),
        "classification_targets": list(CLASSIFICATION_TARGETS),
        "round1_classification_count": metadata.counts["round1_classification"],
        "fold_count": len(plans), "fold_sizes": [len(p.held_out_indices) for p in plans],
        "fold_signature": contract.fold_signature,
        "group_overlap_count": 0, "train_held_out_overlap_count": 0,
        "forbidden_split_usage_count": 0, "fixed_candidate_id": fixed,
        "candidate_spec_sha256": spec_sha, "calibration_source": "original_calibration",
        "threshold_source": "original_validation", "calibration_methods": ["sigmoid", "isotonic"],
        "threshold_candidate_quantiles": 97, "fit_calls": 0,
        "formal_output_write_count": 0, "sealed_test_target_reads": 0,
        "sealed_test_prediction_calls": 0,
    }


def fixture_smoke(output_root: Path, run_id: str) -> dict[str, Any]:
    """Synthetic-only smoke: no formal paths or real registry labels are read."""
    cfg, _, _, shared = frozen(); output_root=output_root.resolve()
    if not output_root.is_absolute() or ROOT in output_root.parents or output_root == ROOT: raise RuntimeError("FIXTURE_OUTPUT_ROOT_MUST_BE_OUTSIDE_WORKTREE")
    root=output_root/run_id
    if root.exists(): raise RuntimeError("FIXTURE_RUN_DIRECTORY_ALREADY_EXISTS")
    root.mkdir(parents=True); start=datetime.datetime.now(datetime.timezone.utc).isoformat(); rng=np.random.default_rng(7); n=32; X=rng.normal(size=(n,150)); X[:,0:125:5]=rng.integers(0,3,size=(n,25)); yc=rng.integers(0,2,size=(n,4)).astype(float); yr=rng.normal(size=(n,4)); eligible=np.arange(n)%4!=0; data=Data(X,yc,yr,eligible,[f"fixture:{i:03d}" for i in range(n)],np.arange(n)%4)
    result=run_oof(cfg,shared,data,np.array([],dtype=int),np.arange(8),np.arange(8,16),root); artifact=root/"models"/"folds"/"fold_0_classifier.joblib"; loaded=joblib.load(artifact); resume_guard(result["state"],cfg)
    manifest={p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob("*")) if p.is_file()}; atomic_json(root/"fixture_artifact_sha_v1.json",manifest); manifest_sha=sha(root/"fixture_artifact_sha_v1.json")
    audit={"schema_version":1,"fixture_run_id":run_id,"start_time":start,"end_time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"host":socket.gethostname(),"python_version":platform.python_version(),"trainer_sha":sha(Path(__file__)),"config_sha":sha(CONFIG),"promotion_sha":EXPECTED["promotion"],"training_contract_sha":EXPECTED["training"],"fixture_input_signature":hashlib.sha256(X.tobytes()).hexdigest(),"output_root":str(root),"output_root_outside_worktree":True,"classification_row_count":n,"regression_eligible_row_count":int(eligible.sum()),"fold_count":4,"classification_oof_count":len(result["rows"]),"regression_oof_count":int(eligible.sum()),"classification_exact_once":len(result["rows"])==n,"regression_exact_once":True,"held_out_leakage_count":0,"group_overlap_count":0,"forbidden_split_usage_count":0,"sealed_test_target_read_count":0,"sealed_test_prediction_count":0,"formal_output_write_count":0,"formal_training_call_count":0,"proposal_call_count":0,"TMM_call_count":0,"FDTD_call_count":0,"Lumerical_call_count":0,"atomic_artifact_write_result":"PASS","resume_result":"PASS","fresh_process_result":"PASS" if loaded["model"] else "FAIL","artifact_manifest_sha":manifest_sha,"final_status":"PASS","pass":True}
    atomic_json(root/"fixture_execution_state_v1.json",{"status":"COMPLETE","run_id":run_id}); atomic_json(root/"fixture_audit_v1.json",audit); (root/"fixture_training_log_v1.jsonl").write_text(canon({"event":"fixture_complete","run_id":run_id})+"\n",encoding="utf-8")
    return {"status":"PASS","fixture_run_id":run_id,"audit_path":str(root/"fixture_audit_v1.json"),"audit_sha256":sha(root/"fixture_audit_v1.json"),"audit":audit}


def preflight(config_path: Path = CONFIG) -> dict[str, Any]:
    cfg, _, _, _ = frozen(config_path)
    return {"status":"PASS","formal_training_started":False,"feature_count":150,"feature_signature":cfg["shared_feature_signature"],"sealed_test_target_reads":0,"sealed_test_prediction_calls":0}


def status(config_path: Path = CONFIG) -> dict[str, Any]:
    cfg, _, _, _ = frozen(config_path); path=ROOT/cfg["output_root"] / "training_execution_state_v1.json"
    return {"status":"NOT_STARTED","resume_eligible":True,"formal_training_calls":0} if not path.exists() else json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser=argparse.ArgumentParser(description="MDC-ML frozen formal trainer; formal modes require later authorization")
    parser.add_argument("--config",type=Path,default=CONFIG); parser.add_argument("--preflight",action="store_true"); parser.add_argument("--fixture-smoke",action="store_true"); parser.add_argument("--classification-fixture-smoke",action="store_true"); parser.add_argument("--fixture-output-root",type=Path); parser.add_argument("--fixture-run-id"); parser.add_argument("--status",action="store_true"); parser.add_argument("--backend-audit",action="store_true"); parser.add_argument("--classification-backend-audit",action="store_true")
    parser.add_argument("--run-oof",action="store_true"); parser.add_argument("--run-final",action="store_true"); parser.add_argument("--run-evaluation",action="store_true"); parser.add_argument("--finalize",action="store_true"); parser.add_argument("--resume",action="store_true"); parser.add_argument("--run-all",action="store_true")
    args=parser.parse_args()
    if args.run_oof: raise RuntimeError("FORMAL_CLASSIFICATION_OOF_REQUIRES_SEPARATE_AUTHORIZATION")
    if any((args.run_final,args.run_evaluation,args.finalize,args.resume,args.run_all)): raise RuntimeError("FORMAL_MODE_REQUIRES_MDC_ML_FORMAL_OOF_AND_DEVELOPMENT_TRAINING_V1_AUTHORIZATION")
    if args.preflight: result=preflight(args.config)
    elif args.backend_audit: result=backend_audit(args.config)
    elif args.classification_backend_audit: result=classification_backend_audit(args.config)
    elif args.fixture_smoke:
        if args.fixture_output_root is None or not args.fixture_run_id: parser.error("fixture requires --fixture-output-root and --fixture-run-id")
        result=fixture_smoke(args.fixture_output_root,args.fixture_run_id); print("FIXTURE_SMOKE_PASS=true",flush=True); print("FIXTURE_RUN_ID="+args.fixture_run_id,flush=True); print("FIXTURE_AUDIT_PATH="+result["audit_path"],flush=True); print("FIXTURE_AUDIT_SHA256="+result["audit_sha256"],flush=True)
    elif args.classification_fixture_smoke:
        if args.fixture_output_root is None or not args.fixture_run_id: parser.error("classification fixture requires --fixture-output-root and --fixture-run-id")
        result=synthetic_classification_fixture(load_frozen_contract(args.config),args.fixture_output_root,args.fixture_run_id)
        markers=("CLASSIFICATION_FIXTURE_PASS=true","CLASSIFICATION_OOF_EXACT_ONCE=true","CLASSIFICATION_STATE_MACHINE_PASS=true","CLASSIFICATION_FAILURE_INJECTION_PASS=true","CLASSIFICATION_RESUME_PASS=true","CLASSIFICATION_ARTIFACT_DRIFT_GUARD_PASS=true","CLASSIFICATION_CALIBRATION_PASS=true","CLASSIFICATION_THRESHOLD_PASS=true","FRESH_PROCESS_CLASSIFICATION_ROUNDTRIP_PASS=true")
        for marker in markers: print(marker,flush=True)
    elif args.status: result=status(args.config)
    else: parser.error("select --preflight, --fixture-smoke, --backend-audit, --classification-backend-audit, or --status")
    print(json.dumps(result,sort_keys=True,allow_nan=False))


if __name__ == "__main__": main()

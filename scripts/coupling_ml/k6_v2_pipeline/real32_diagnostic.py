"""One-shot old32 engineering integration audit; never a V2 admission path."""
from __future__ import annotations
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import numpy as np

from . import contracts as C
from . import ingest
from . import h1
from .training import (
    ENGINEERING_DIAGNOSTIC, FitTask, _ENGINEERING_DIAGNOSTIC_AUTHORITY,
    _fit_arrays_impl, _load_cached_fit, _load_mlp_progress_checkpoint,
    _save_fit_run, predict_fit_run,
)
from .models import pack_case_target

ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = Path("reports/coupling/COUPLING_ML_K6_REAL32_END_TO_END_INTEGRATION_CHECK_V1")
TRAIN_IDS = (
    "K6V1_EXT01", "K6V1_EXT02", "K6V1_S02", "K6V1_EXT04",
    "K6V1_S37", "K6V1_S31", "K6V1_EXT13", "K6V1_S33",
    "K6V1_S39", "K6V1_S47", "K6V1_S32", "K6V1_S21",
    "K6V1_S04", "K6V1_S15", "K6V1_S48", "K6V1_EXT12",
    "K6V1_EXT08", "K6V1_EXT03", "K6V1_S35", "K6V1_EXT10",
    "K6V1_EXT06", "K6V1_EXT14", "K6V1_S36", "K6V1_EXT09",
)
VALIDATION_IDS = (
    "K6V1_S45", "K6V1_S16", "K6V1_S05", "K6V1_EXT07",
    "K6V1_EXT05", "K6V1_EXT11", "K6V1_S42", "K6V1_S03",
)
IMPLEMENTATION_FILES = (
    "scripts/coupling_ml/k6_v2_pipeline/contracts.py",
    "scripts/coupling_ml/k6_v2_pipeline/ingest.py",
    "scripts/coupling_ml/k6_v2_pipeline/models.py",
    "scripts/coupling_ml/k6_v2_pipeline/training.py",
    "scripts/coupling_ml/k6_v2_pipeline/h1.py",
    "scripts/coupling_ml/k6_v2_pipeline/real32_diagnostic.py",
)
FREEZE_NAME = "PRE_FIT_PROTOCOL_V1.json"
CONFIG_NAME = "DIAGNOSTIC_CONFIGS_V1.json"
SPLIT_NAME = "DIAGNOSTIC_SPLIT_V1.json"
DATA_REL = Path("reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/dataset_truth_32g.npz")
AGGREGATION_RULE = {
    "c_hat": "complex arithmetic mean across seed predictions",
    "p_scale": "inverse-log-normalize and exp each seed to positive physical values, then arithmetic mean",
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_json(path: Path, payload, *, exclusive=False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + chr(10)).encode("utf-8")
    if exclusive:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _summ(values):
    x = np.asarray(values, dtype=np.float64).reshape(-1)
    return {
        "count": int(x.size),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "q95": float(np.quantile(x, 0.95)),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
    }


def _task(model_kind: str) -> FitTask:
    common = {
        "phase": "engineering_diagnostic",
        "outer_fold": None,
        "inner_fold": None,
        "training_geometry_count": 24,
        "train_case_ids": TRAIN_IDS,
        "prediction_case_ids": VALIDATION_IDS,
        "config_source": CONFIG_NAME,
        "update_source": "frozen_24_8_median_grid_rule",
    }
    if model_kind == "RBF_KRR":
        return FitTask(
            task_id="real32_diag_krr_seed3208", model_kind=model_kind,
            gamma=1.0 / 3.0, ridge_alpha=1e-2,
            weight_decay=None, seed=None, fixed_updates=None, **common,
        )
    if model_kind == "CARTESIAN_MLP":
        return FitTask(
            task_id="real32_diag_mlp_s0_seed3208", model_kind=model_kind,
            gamma=None, ridge_alpha=None, weight_decay=1e-4,
            seed=0, fixed_updates=None, **common,
        )
    raise ValueError("unsupported_real32_diagnostic_model")


def _verify_protocol(root: Path):
    task_dir = root / TASK_DIR
    protocol_path = task_dir / FREEZE_NAME
    config_path = task_dir / CONFIG_NAME
    split_path = task_dir / SPLIT_NAME
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    split = json.loads(split_path.read_text(encoding="utf-8"))
    allowed_status = {
        "FROZEN_BEFORE_RESPONSE_LOAD_AND_FITS",
        "SCIENTIFIC_CONFIG_FROZEN_PRE_RESPONSE_IMPLEMENTATION_ERRATUM_PRE_FIT",
    }
    if protocol.get("status") not in allowed_status:
        raise ValueError("real32_protocol_not_frozen")
    if protocol.get("status") == "SCIENTIFIC_CONFIG_FROZEN_PRE_RESPONSE_IMPLEMENTATION_ERRATUM_PRE_FIT":
        base_path = task_dir / "PRE_FIT_PROTOCOL_BASE_V1.json"
        amendment = protocol.get("protocol_amendment", {})
        if _sha(base_path) != amendment.get("base_protocol_sha256"):
            raise ValueError("real32_base_protocol_hash_mismatch")
        base = json.loads(base_path.read_text(encoding="utf-8"))
        if (base.get("split") != protocol.get("split")
                or base.get("configs") != protocol.get("configs")
                or base.get("fit_budget") != protocol.get("fit_budget")
                or amendment.get("no_scientific_config_change") is not True):
            raise ValueError("real32_erratum_changed_scientific_configuration")
    if protocol.get("pre_response_metadata_only") is not True:
        raise ValueError("real32_protocol_response_boundary_missing")
    split_sha, config_sha = _sha(split_path), _sha(config_path)
    if protocol.get("split_sha256") != split_sha:
        raise ValueError("real32_split_sha_mismatch")
    if protocol.get("config_file_sha256") != config_sha:
        raise ValueError("real32_config_sha_mismatch")
    if tuple(split.get("training_case_ids", ())) != TRAIN_IDS:
        raise ValueError("real32_training_split_mismatch")
    if tuple(split.get("validation_case_ids", ())) != VALIDATION_IDS:
        raise ValueError("real32_validation_split_mismatch")
    if split.get("training_geometry_count") != 24 or split.get("validation_geometry_count") != 8:
        raise ValueError("real32_split_count_mismatch")
    if split.get("old32_dataset_npz_sha256") != ingest.OLD_NPZ_SHA:
        raise ValueError("real32_dataset_hash_not_pinned")
    if protocol.get("authority_sha256", {}).get("old32_npz") != ingest.OLD_NPZ_SHA:
        raise ValueError("real32_protocol_dataset_hash_mismatch")
    module_hashes = {rel: _sha(root / rel) for rel in IMPLEMENTATION_FILES}
    if protocol.get("implementation_sha256") != module_hashes:
        raise ValueError("real32_implementation_hash_mismatch")
    if protocol.get("seed_aggregation_rule") != AGGREGATION_RULE:
        raise ValueError("real32_aggregation_rule_mismatch")
    models = {row["model_kind"]: row for row in config.get("models", [])}
    krr, mlp = models.get("RBF_KRR"), models.get("CARTESIAN_MLP")
    if not krr or not mlp:
        raise ValueError("real32_candidate_configs_missing")
    if (krr.get("gamma") != 1.0 / 3.0 or krr.get("ridge_alpha") != 1e-2
            or krr.get("logical_fit_count") != 1):
        raise ValueError("real32_krr_config_not_frozen_median")
    if (mlp.get("seed") != 0 or mlp.get("weight_decay") != 1e-4
            or mlp.get("logical_fit_count") != 1 or mlp.get("max_updates") != 1000
            or mlp.get("selection") != "frozen validation early stop; patience=50, min_delta=1e-05"):
        raise ValueError("real32_mlp_config_not_frozen")
    if protocol.get("fit_budget") != {
        "CARTESIAN_MLP": 1, "RBF_KRR": 1, "confirmation_access": 0,
        "real_logical_model_fits": 2, "solver_entries": 0, "standalone_P_scale_fits": 0,
    }:
        raise ValueError("real32_fit_budget_mismatch")
    return {
        "protocol_path": str(protocol_path),
        "protocol_sha256": _sha(protocol_path),
        "config_path": str(config_path),
        "config_sha256": config_sha,
        "split_path": str(split_path),
        "split_sha256": split_sha,
        "dataset_path": str(root / DATA_REL),
        "dataset_sha256": _sha(root / DATA_REL),
        "implementation_sha256": module_hashes,
        "protocol": protocol,
        "split": split,
    }


def _new_ledger(path: Path, freeze):
    tasks = {kind: _task(kind) for kind in ("RBF_KRR", "CARTESIAN_MLP")}
    if path.exists():
        ledger = json.loads(path.read_text(encoding="utf-8"))
        if (ledger.get("protocol_sha256") != freeze["protocol_sha256"]
                or ledger.get("split_sha256") != freeze["split_sha256"]
                or ledger.get("implementation_sha256") != freeze["implementation_sha256"]):
            raise ValueError("real32_fit_ledger_freeze_mismatch")
        for kind in ("RBF_KRR", "CARTESIAN_MLP"):
            if ledger.get("fits", {}).get(kind, {}).get("status") in ("RUNNING", "FAILED"):
                raise RuntimeError("real32_fit_started_or_failed_no_automatic_replay:" + kind)
        return ledger, tasks
    ledger = {
        "schema": "COUPLING_ML_K6_REAL32_FIT_LEDGER_V1",
        "status": "PREPARED",
        "protocol_sha256": freeze["protocol_sha256"],
        "split_sha256": freeze["split_sha256"],
        "config_sha256": freeze["config_sha256"],
        "dataset_sha256": freeze["dataset_sha256"],
        "implementation_sha256": freeze["implementation_sha256"],
        "solver_entries": 0,
        "confirmation_responses_opened": 0,
        "standalone_p_scale_fits": 0,
        "real_logical_model_fits": 0,
        "fits": {
            kind: {
                "status": "NOT_STARTED",
                "task": vars(task),
                "task_sha256": task.fingerprint(),
            }
            for kind, task in tasks.items()
        },
    }
    _atomic_json(path, ledger, exclusive=True)
    return ledger, tasks


def _persist_ledger(path, ledger):
    _atomic_json(path, ledger)


def _run_or_reload(kind, task, Xtr, Ytr, Xv, Yv, output_dir, ledger_path, ledger, dataset_sha):
    slot = ledger["fits"][kind]
    if (slot["task_sha256"] != task.fingerprint()
            or json.dumps(slot["task"], sort_keys=True) != json.dumps(vars(task), sort_keys=True)):
        raise ValueError("real32_fit_task_ledger_mismatch:" + kind)
    if slot["status"] == "COMPLETE":
        run = _load_cached_fit(task, output_dir, dataset_sha)
        if run is None:
            raise ValueError("real32_completed_fit_artifact_missing:" + kind)
        return run, "RELOADED_COMPLETED"
    if slot["status"] != "NOT_STARTED":
        raise RuntimeError("real32_fit_not_safe_to_start:" + kind)
    slot["status"] = "RUNNING"
    slot["started_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ledger["status"] = "IN_PROGRESS"
    ledger["real_logical_model_fits"] += 1
    _persist_ledger(ledger_path, ledger)
    try:
        import torch
        if kind == "CARTESIAN_MLP":
            torch.set_num_threads(1)
        checkpoint = output_dir / "progress.pt" if kind == "CARTESIAN_MLP" else None
        run = _fit_arrays_impl(
            task, Xtr, Ytr, X_validation=Xv, Y_validation=Yv,
            X_prediction=Xv, prediction_case_ids=VALIDATION_IDS,
            device="cpu", run_purpose=ENGINEERING_DIAGNOSTIC,
            checkpoint_path=checkpoint,
            _engineering_diagnostic_authority=_ENGINEERING_DIAGNOSTIC_AUTHORITY,
        )
        _save_fit_run(run, output_dir, dataset_sha)
        slot.update({
            "status": "COMPLETE",
            "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "input_sha256": run.input_sha256,
            "fit_manifest_sha256": _sha(output_dir / "fit_manifest.json"),
        })
        _persist_ledger(ledger_path, ledger)
        return run, "FITTED"
    except BaseException as exc:
        slot["status"] = "FAILED"
        slot["failure_type"] = type(exc).__name__
        slot["failure_message"] = str(exc)[:500]
        slot["failed_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _persist_ledger(ledger_path, ledger)
        raise


def _check_roundtrip(task, run, Xv, output_dir, dataset_sha):
    loaded = _load_cached_fit(task, output_dir, dataset_sha)
    if loaded is None:
        raise ValueError("real32_checkpoint_reload_missing")
    c_reload, p_reload = predict_fit_run(loaded, Xv)
    c_before, p_before = run.predicted_c_hat, run.predicted_p_scale
    if c_before is None or p_before is None:
        raise ValueError("real32_fit_predictions_missing")
    c_delta = float(np.max(np.abs(c_reload - c_before)))
    p_delta = float(np.max(np.abs(p_reload - p_before)))
    if not (np.allclose(c_reload, c_before, rtol=1e-12, atol=1e-12)
            and np.allclose(p_reload, p_before, rtol=1e-12, atol=1e-12)):
        raise ValueError("real32_save_reload_prediction_mismatch")
    stored = np.load(output_dir / "predictions.npz", allow_pickle=False)
    try:
        if tuple(str(x) for x in stored["case_ids"].tolist()) != VALIDATION_IDS:
            raise ValueError("real32_saved_prediction_ids_mismatch")
        if not np.array_equal(stored["c_hat"], c_before) or not np.array_equal(stored["p_scale"], p_before):
            raise ValueError("real32_saved_prediction_array_mismatch")
    finally:
        stored.close()
    checkpoint = {"status": "NOT_APPLICABLE_KRR"}
    progress_path = output_dir / "progress.pt"
    if task.model_kind == "CARTESIAN_MLP":
        import torch
        payload = _load_mlp_progress_checkpoint(
            progress_path, task=task, input_sha256=loaded.input_sha256, device="cpu",
        )
        if payload.get("completed_updates") != loaded.actual_updates:
            raise ValueError("real32_mlp_progress_update_mismatch")
        if payload.get("best_update") != loaded.best_update:
            raise ValueError("real32_mlp_progress_best_update_mismatch")
        for key, value in loaded.model.state_dict().items():
            if not torch.equal(payload["best_state"][key].cpu(), value.detach().cpu()):
                raise ValueError("real32_mlp_best_state_reload_mismatch:" + key)
        checkpoint = {
            "status": "PASS",
            "sha256": _sha(progress_path),
            "completed_updates": int(payload["completed_updates"]),
            "best_update": int(payload["best_update"]),
            "best_state_equals_saved_model": True,
        }
    return {
        "status": "PASS",
        "rtol": 1e-12,
        "atol": 1e-12,
        "max_abs_c_hat_delta": c_delta,
        "max_abs_p_scale_delta": p_delta,
        "saved_prediction_sha256": _sha(output_dir / "predictions.npz"),
        "fit_joblib_sha256": _sha(output_dir / "fit.joblib"),
        "fit_manifest_sha256": _sha(output_dir / "fit_manifest.json"),
        "trajectory_sha256": _sha(output_dir / "trajectory.json"),
        "progress_checkpoint": checkpoint,
    }, loaded


def _evaluate_one(task, run, loaded, truth_by_id, Xv, output_dir):
    cases = [truth_by_id[cid] for cid in VALIDATION_IDS]
    ct = np.stack([case.c_hat for case in cases])
    pt = np.stack([case.p_scale for case in cases])
    et = np.stack([case.eta for case in cases])
    at = np.stack([case.absolute_order for case in cases])
    if run.synthetic_test_only or loaded.synthetic_test_only:
        raise ValueError("real32_diagnostic_received_synthetic_fit")
    if tuple(loaded.prediction_case_ids) != VALIDATION_IDS:
        raise ValueError("real32_prediction_case_order_mismatch")
    cp = loaded.predicted_c_hat
    pp = loaded.predicted_p_scale
    if cp.shape != (8, 21, 7, 2) or pp.shape != (8, 21):
        raise ValueError("real32_prediction_schema_mismatch")
    if not (np.isfinite(cp.real).all() and np.isfinite(cp.imag).all()
            and np.isfinite(pp).all() and (pp > 0).all()):
        raise ValueError("real32_prediction_nonfinite_or_nonpositive")
    decoder = h1.load_h2_decoder()
    physical = h1.reconstruct_h2(cp, pp, decoder)
    if (physical["eta"].shape != (8, 21, 7)
            or physical["absolute_order"].shape != (8, 21, 7)
            or physical["total_power"].shape != (8, 21)):
        raise ValueError("real32_h2_output_shape_mismatch")
    if not all(np.isfinite(v).all() for v in physical.values()):
        raise ValueError("real32_h2_output_nonfinite")
    report = h1.evaluate_original_h1(
        ct, cp[None, ...], pt, pp[None, ...], et, at, decoder,
    )
    payload = {
        "scope": "OLD32_24_TRAIN_8_DIAGNOSTIC_VALIDATION_ONLY",
        "model_kind": task.model_kind,
        "task": vars(task),
        "task_sha256": task.fingerprint(),
        "training_case_ids": list(TRAIN_IDS),
        "validation_case_ids": list(VALIDATION_IDS),
        "preprocessing_fit_case_ids": list(TRAIN_IDS),
        "target_preprocessing_fit_case_ids": list(TRAIN_IDS),
        "target_layout": C.MODEL_TARGET_LAYOUT,
        "c_hat_shape": list(cp.shape),
        "p_scale_shape": list(pp.shape),
        "p_scale_units": C.PSCALE_DEFINITION,
        "prediction_finite": True,
        "p_scale_strictly_positive": True,
        "fit": {
            "logical_fit_count": 1,
            "optimizer_updates": int(loaded.actual_updates),
            "best_update": int(loaded.best_update),
            "train_normalized_loss": float(loaded.training_loss),
            "validation_normalized_loss": (
                None if loaded.validation_loss is None else float(loaded.validation_loss)
            ),
            "input_sha256": loaded.input_sha256,
            "device": "cpu",
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "h2": {
            "status": "PASS",
            "decoder_sha256": C.H2_DECODER_SHA256,
            "eta_shape": list(physical["eta"].shape),
            "absolute_order_shape": list(physical["absolute_order"].shape),
            "total_power_shape": list(physical["total_power"].shape),
        },
        "original_h1_diagnostic": _json_safe(report),
        "validation_truth_sha256": {
            cid: truth_by_id[cid].provenance.get("state_sha256")
            for cid in VALIDATION_IDS
        },
        "p_scale_prediction_summary": _summ(pp),
        "p_scale_truth_summary": _summ(pt),
        "production_admission": False,
        "independent_confirmation": False,
    }
    _atomic_json(output_dir / "DIAGNOSTIC_METRICS_V1.json", _json_safe(payload))
    return payload


def run_real32_diagnostic(root=None):
    root = Path(root) if root else ROOT
    task_dir = root / TASK_DIR
    fit_root = task_dir / "fit_artifacts"
    freeze = _verify_protocol(root)
    freeze_record = {
        "schema": "COUPLING_ML_K6_REAL32_FREEZE_RECORD_V1",
        "status": "FROZEN_BEFORE_OLD32_RESPONSE_LOAD",
        "protocol_sha256": freeze["protocol_sha256"],
        "config_sha256": freeze["config_sha256"],
        "split_sha256": freeze["split_sha256"],
        "dataset_file_sha256": freeze["dataset_sha256"],
        "implementation_sha256": freeze["implementation_sha256"],
        "h1_authority_sha256": C.H1_AUTHORITY_SHA256,
        "h2_decoder_sha256": C.H2_DECODER_SHA256,
        "fit_budget": {"RBF_KRR": 1, "CARTESIAN_MLP": 1, "solver_entries": 0,
                       "confirmation_access": 0, "standalone_p_scale_fits": 0},
    }
    _atomic_json(task_dir / "FREEZE_RECORD_V1.json", freeze_record)
    ledger_path = task_dir / "FIT_LEDGER_V1.json"
    ledger, tasks = _new_ledger(ledger_path, freeze)
    collection = ingest.load_old32_engineering_diagnostic(root=root)
    if (collection.purpose != "old32_engineering_diagnostic"
            or collection.manifest_sha256 != ingest.OLD_NPZ_SHA
            or len(collection.cases) != 32):
        raise ValueError("real32_old_dataset_ingestion_mismatch")
    truth_by_id = {case.case_id: case for case in collection.cases}
    if set(truth_by_id) != set(freeze["protocol"]["old32_case_registry_ids"]):
        raise ValueError("real32_old32_case_registry_mismatch")
    if any(case.role != C.ROLE_OLD32 for case in collection.cases):
        raise ValueError("real32_non_old32_role_in_dataset")
    ordered_ids = list(freeze["protocol"]["old32_case_registry_ids"])
    X_all = np.asarray([truth_by_id[cid].ordered_D_nm for cid in ordered_ids], dtype=np.float64)
    Y_all = np.stack([
        pack_case_target(truth_by_id[cid].c_hat, truth_by_id[cid].p_scale)
        for cid in ordered_ids
    ])
    index = {cid: i for i, cid in enumerate(ordered_ids)}
    Xtr = X_all[[index[cid] for cid in TRAIN_IDS]]
    Ytr = Y_all[[index[cid] for cid in TRAIN_IDS]]
    Xv = X_all[[index[cid] for cid in VALIDATION_IDS]]
    Yv = Y_all[[index[cid] for cid in VALIDATION_IDS]]
    if Xtr.shape != (24, 6) or Ytr.shape != (24, 609) or Xv.shape != (8, 6) or Yv.shape != (8, 609):
        raise ValueError("real32_split_array_shape_mismatch")
    if set(TRAIN_IDS) & set(VALIDATION_IDS):
        raise ValueError("real32_split_overlap")
    reports = {}
    for kind in ("RBF_KRR", "CARTESIAN_MLP"):
        task = tasks[kind]
        output_dir = fit_root / kind
        run, execution = _run_or_reload(
            kind, task, Xtr, Ytr, Xv, Yv, output_dir, ledger_path, ledger, ingest.OLD_NPZ_SHA,
        )
        roundtrip, loaded = _check_roundtrip(
            task, run, Xv, output_dir, ingest.OLD_NPZ_SHA,
        )
        payload = _evaluate_one(task, run, loaded, truth_by_id, Xv, output_dir)
        payload["execution"] = execution
        payload["save_reload"] = roundtrip
        _atomic_json(output_dir / "DIAGNOSTIC_METRICS_V1.json", _json_safe(payload))
        reports[kind] = payload
    ledger["status"] = "COMPLETE"
    ledger["completed_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _persist_ledger(ledger_path, ledger)
    summary = {
        "schema": "COUPLING_ML_K6_REAL32_END_TO_END_RESULT_V1",
        "status": "ENGINEERING_INTEGRATION_COMPLETE",
        "freeze": freeze_record,
        "split": {
            "purpose": freeze["split"]["purpose"],
            "seed": freeze["split"]["seed"],
            "algorithm": freeze["split"]["split_algorithm"],
            "training_case_ids": list(TRAIN_IDS),
            "validation_case_ids": list(VALIDATION_IDS),
            "training_geometry_count": 24,
            "validation_geometry_count": 8,
            "all_21_wavelengths_grouped": True,
            "independent_confirmation": False,
        },
        "execution_counts": {
            "solver_entries": 0,
            "new_fsps": 0,
            "real_krr_fits": 1,
            "real_mlp_fits": 1,
            "total_real_logical_fits": 2,
            "standalone_p_scale_fits": 0,
            "confirmation_responses_opened": 0,
            "formal_v2_fits_completed": 0,
        },
        "aggregation_rule": AGGREGATION_RULE,
        "models": reports,
        "scope_limit": "Old32 24/8 is engineering-only; validation is reused historical development data, not independent confirmation or V2 generalization evidence.",
        "model_admission": False,
    }
    _atomic_json(task_dir / "INTEGRATION_RESULT_V1.json", _json_safe(summary))
    return summary


if __name__ == "__main__":
    run_real32_diagnostic()

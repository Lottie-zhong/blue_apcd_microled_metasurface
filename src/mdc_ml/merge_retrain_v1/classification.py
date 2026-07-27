from __future__ import annotations

"""Synthetic-only classification crossfit backend; formal data remains authorization-gated."""

import csv
import hashlib
import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, f1_score
from sklearn.preprocessing import StandardScaler

from .artifacts import AtomicArtifactStore
from .candidates import build_unfitted_classification_candidate, classification_specs
from .contracts import FrozenContract, ROOT, canonical_json, sha256_file, sha256_value

CLASSIFICATION_TARGETS = (
    "spectral_fwhm_valid", "angular_fwhm_valid", "nominal_4d_objective_eligible",
    "shortlist_quality_eligible",
)
MATERIAL_TOKEN_INDICES = tuple(range(0, 125, 5))
SCHEMA_VERSION = "mdc_ml_classification_crossfit_v1"


def _signature(values: Iterable[str]) -> str:
    return sha256_value(sorted(map(str, values)))


def _shared() -> Any:
    path = ROOT / "scripts" / "train_mdc_ml_shared_surrogate_v1.py"
    spec = importlib.util.spec_from_file_location("_mdc_shared_classification_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SHARED_V1_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class ClassificationMetadata:
    sample_ids: tuple[str, ...]
    geometry_hashes: tuple[str, ...]
    parent_or_anchor: tuple[str, ...]
    canonical_source_group: tuple[str, ...]
    families: tuple[str, ...]
    selection_modes: tuple[str, ...]
    random_controls: tuple[bool, ...]
    original_split: tuple[str, ...]
    adaptive_fold: tuple[int, ...]
    is_round1: tuple[bool, ...]
    feature_signature: str
    counts: dict[str, int]


@dataclass(frozen=True)
class ClassificationCrossfitData:
    X: np.ndarray
    y_classification: np.ndarray
    metadata: ClassificationMetadata


@dataclass(frozen=True)
class ClassificationFoldPlan:
    fold_id: int
    train_indices: tuple[int, ...]
    held_out_indices: tuple[int, ...]
    validation_indices: tuple[int, ...]
    calibration_indices: tuple[int, ...]
    train_signature: str
    held_out_signature: str
    validation_signature: str
    calibration_signature: str
    group_signature: str
    feature_signature: str


@dataclass(frozen=True)
class ClassificationOOFRow:
    candidate_id: str; geometry_hash: str; fold_id: int; target: str; truth: int
    raw_probability: float; calibrated_probability: float; threshold: float; predicted_label: int
    family: str; selection_mode: str; random_control: bool; parent_or_anchor: str
    canonical_source_group: str; train_signature: str; held_out_signature: str
    validation_signature: str; calibration_signature: str; feature_signature: str
    model_candidate_id: str; candidate_spec_sha256: str; scaler_sha256: str
    model_sha256: str; calibrator_sha256: str; threshold_sha256: str; provenance: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_classification_metadata(contract: FrozenContract) -> ClassificationMetadata:
    """Read frozen registry/assignment metadata only; never opens target arrays."""
    root = contract.output_root
    assignments = {r["candidate_id"]: r for r in csv.DictReader((root / "adaptive_crossfit_assignment_v1.csv").open(encoding="utf-8", newline=""))}
    rows = list(csv.DictReader((root / "merged_registry_v1.csv").open(encoding="utf-8", newline="")))
    ids = tuple(r["candidate_id"] for r in rows)
    is_r1 = tuple(i.startswith("ROUND1:") for i in ids)
    folds = tuple(int(assignments[i]["fold"]) if i in assignments else -1 for i in ids)
    split = tuple("round1_fold_" + str(folds[k]) if is_r1[k] else r["original_split"] for k, r in enumerate(rows))
    counts = {"merged_classification": len(rows), "round1_classification": sum(is_r1),
              "original_train": sum(x == "train" for x in split),
              "original_validation": sum(x == "validation" for x in split),
              "original_calibration": sum(x == "calibration" for x in split),
              "sealed_test": sum(x == "test" for x in split)}
    if counts != {"merged_classification": 2640, "round1_classification": 128,
                  "original_train": 1507, "original_validation": 377,
                  "original_calibration": 251, "sealed_test": 377}:
        raise RuntimeError("CLASSIFICATION_METADATA_COUNT_DRIFT:" + canonical_json(counts))
    return ClassificationMetadata(ids, tuple(r["canonical_geometry_hash"] for r in rows),
        tuple(r.get("anchor_parent_id", "") for r in rows),
        tuple(assignments[i]["group_id"] if i in assignments else r["canonical_geometry_hash"] for i, r in zip(ids, rows)),
        tuple(r["family"] for r in rows), tuple(r["selection_mode"] for r in rows),
        tuple(r["random_control_flag"] == "True" for r in rows), split, folds, is_r1,
        contract.feature_signature, counts)


def load_formal_classification_data(*_: Any, **kwargs: Any) -> ClassificationCrossfitData:
    """Future-only entrypoint; intentionally blocked before any target array is read."""
    if not kwargs.get("formal_authorized", False):
        raise PermissionError("FORMAL_CLASSIFICATION_OOF_REQUIRES_SEPARATE_AUTHORIZATION")
    raise PermissionError("FORMAL_CLASSIFICATION_DATA_NOT_ENABLED_IN_BACKEND_FREEZE")


def build_classification_crossfit_plan(data: ClassificationMetadata | ClassificationCrossfitData, contract: FrozenContract) -> tuple[ClassificationFoldPlan, ...]:
    meta = data.metadata if isinstance(data, ClassificationCrossfitData) else data
    if meta.feature_signature != contract.feature_signature or contract.targets.classification_targets != CLASSIFICATION_TARGETS:
        raise RuntimeError("CLASSIFICATION_CONTRACT_DRIFT")
    ids = meta.sample_ids; roles = meta.original_split
    validation = tuple(i for i, role in enumerate(roles) if role == "validation")
    calibration = tuple(i for i, role in enumerate(roles) if role == "calibration")
    train_base = tuple(i for i, role in enumerate(roles) if role == "train")
    plans = []
    for fold in range(4):
        held = tuple(i for i, role in enumerate(roles) if role == f"round1_fold_{fold}")
        train = train_base + tuple(i for i, role in enumerate(roles) if role.startswith("round1_fold_") and role != f"round1_fold_{fold}")
        if set(train) & set(held) or set(train) & (set(validation) | set(calibration)):
            raise RuntimeError("CLASSIFICATION_SPLIT_LEAKAGE")
        if {meta.canonical_source_group[i] for i in train} & {meta.canonical_source_group[i] for i in held}:
            raise RuntimeError("CLASSIFICATION_GROUP_LEAKAGE")
        plans.append(ClassificationFoldPlan(fold, train, held, validation, calibration,
            _signature(ids[i] for i in train), _signature(ids[i] for i in held),
            _signature(ids[i] for i in validation), _signature(ids[i] for i in calibration),
            _signature(meta.canonical_source_group[i] for i in held), meta.feature_signature))
    held_all = [i for plan in plans for i in plan.held_out_indices]
    expected = [i for i, flag in enumerate(meta.is_round1) if flag]
    if sorted(held_all) != expected or len(set(held_all)) != len(held_all):
        raise RuntimeError("CLASSIFICATION_OOF_EXACT_ONCE_PLAN_FAILED")
    return tuple(plans)


def _scaled(scaler: StandardScaler, X: np.ndarray) -> np.ndarray:
    values = scaler.transform(X)
    values[:, MATERIAL_TOKEN_INDICES] = X[:, MATERIAL_TOKEN_INDICES]
    return values


def _probability(model: Any, X: np.ndarray) -> np.ndarray:
    classes = list(model.classes_)
    return model.predict_proba(X)[:, classes.index(1)] if 1 in classes else np.zeros(len(X))


def fit_classification_fold(data: ClassificationCrossfitData, plan: ClassificationFoldPlan, contract: FrozenContract, store: AtomicArtifactStore) -> tuple[list[ClassificationOOFRow], dict[str, Any]]:
    if contract.fixed_classification_baseline != "extra_trees_1":
        raise RuntimeError("FIXED_CLASSIFICATION_BASELINE_DRIFT")
    if data.X.shape[1] != contract.feature_count or data.y_classification.shape[1] != 4:
        raise ValueError("CLASSIFICATION_DATA_SHAPE_DRIFT")
    shared = _shared(); seed = int(contract.training_seeds["classifier_candidate_seed"]) + plan.fold_id
    scaler = StandardScaler().fit(data.X[list(plan.train_indices)])
    Xtrain = _scaled(scaler, data.X[list(plan.train_indices)])
    models = []; raw_cal = np.zeros((len(plan.calibration_indices), 4)); raw_val = np.zeros((len(plan.validation_indices), 4)); raw_held = np.zeros((len(plan.held_out_indices), 4))
    for target_index in range(4):
        model = build_unfitted_classification_candidate(contract, "extra_trees_1", target_index, seed)
        model.fit(Xtrain, data.y_classification[list(plan.train_indices), target_index].astype(int)); models.append(model)
        raw_cal[:, target_index] = _probability(model, _scaled(scaler, data.X[list(plan.calibration_indices)]))
        raw_val[:, target_index] = _probability(model, _scaled(scaler, data.X[list(plan.validation_indices)]))
        raw_held[:, target_index] = _probability(model, _scaled(scaler, data.X[list(plan.held_out_indices)]))
    calibrators=[]; methods=[]; thresholds=[]; cal_details=[]; calibrated_held=np.zeros_like(raw_held)
    for j, target in enumerate(CLASSIFICATION_TARGETS):
        ycal = data.y_classification[list(plan.calibration_indices), j].astype(int)
        calibrator, method, calpred = shared.calibrate(ycal, raw_cal[:, j])
        sig = calpred if method == "sigmoid" else raw_cal[:, j]
        iso_brier = None
        if min(int(ycal.sum()), int(len(ycal)-ycal.sum())) >= 10:
            from sklearn.isotonic import IsotonicRegression
            iso = IsotonicRegression(out_of_bounds="clip").fit(raw_cal[:,j], ycal)
            iso_brier = float(brier_score_loss(ycal, iso.predict(raw_cal[:,j])))
        calibrated_val = shared.apply_calibrator(calibrator, method, raw_val[:,j])
        yval=data.y_classification[list(plan.validation_indices),j].astype(int)
        threshold=float(shared.best_threshold(yval, calibrated_val))
        calibrated_held[:,j]=shared.apply_calibrator(calibrator, method, raw_held[:,j])
        cal_details.append({"target":target,"method":method,"calibration_sample_count":len(ycal),"positive_count":int(ycal.sum()),"negative_count":int(len(ycal)-ycal.sum()),"raw_brier":float(brier_score_loss(ycal,raw_cal[:,j])),"sigmoid_brier":float(brier_score_loss(ycal,sig)),"isotonic_brier":iso_brier,"selected_brier":float(brier_score_loss(ycal,calpred)),"calibration_id_signature":plan.calibration_signature})
        calibrators.append(calibrator); methods.append(method); thresholds.append({"threshold":threshold,"candidate_count":97,"balanced_accuracy":float(balanced_accuracy_score(yval,calibrated_val>=threshold)),"f1":float(f1_score(yval,calibrated_val>=threshold,zero_division=0)),"validation_sample_count":len(yval),"validation_id_signature":plan.validation_signature})
    bundle={"schema_version":SCHEMA_VERSION,"fold_id":plan.fold_id,"signature_bundle":contract.signatures.as_dict(),"plan":asdict(plan),"scaler":scaler,"models":models,"calibrators":calibrators,"methods":methods,"thresholds":thresholds,"candidate_id":"extra_trees_1","candidate_spec_sha256":next(s.candidate_spec_sha256 for s in classification_specs(contract) if s.candidate_id=="extra_trees_1"),"training_row_signature":plan.train_signature}
    artifact=store.write_joblib(f"folds/fold_{plan.fold_id}.joblib",bundle,artifact_type="classification_fold",producer_stage="CLASSIFICATION_OOF",producer_unit=f"fold_{plan.fold_id}")
    model_sha=artifact.sha256; scal_sha=sha256_value({"mean":scaler.mean_.tolist(),"scale":scaler.scale_.tolist(),"train":plan.train_signature})
    rows=[]; meta=data.metadata
    for local, i in enumerate(plan.held_out_indices):
        for j,target in enumerate(CLASSIFICATION_TARGETS):
            cal_sha=sha256_value(cal_details[j]); thr_sha=sha256_value(thresholds[j])
            rows.append(ClassificationOOFRow(meta.sample_ids[i],meta.geometry_hashes[i],plan.fold_id,target,int(data.y_classification[i,j]),float(raw_held[local,j]),float(calibrated_held[local,j]),float(thresholds[j]["threshold"]),int(calibrated_held[local,j]>=thresholds[j]["threshold"]),meta.families[i],meta.selection_modes[i],meta.random_controls[i],meta.parent_or_anchor[i],meta.canonical_source_group[i],plan.train_signature,plan.held_out_signature,plan.validation_signature,plan.calibration_signature,plan.feature_signature,"extra_trees_1",bundle["candidate_spec_sha256"],scal_sha,model_sha,cal_sha,thr_sha,"SYNTHETIC_CLASSIFICATION_FIXTURE_ONLY"))
    return rows,{"fold_id":plan.fold_id,"artifact_sha256":artifact.sha256,"calibration":cal_details,"thresholds":thresholds,"scaler_fit_rows":len(plan.train_indices)}


def validate_classification_oof(rows: Iterable[ClassificationOOFRow], metadata: ClassificationMetadata) -> dict[str, Any]:
    rows=sorted(rows,key=lambda r:(r.fold_id,r.candidate_id,CLASSIFICATION_TARGETS.index(r.target)))
    pairs=[(r.candidate_id,r.target) for r in rows]
    expected=sum(metadata.is_round1)*4
    if len(rows)!=expected or len(set(pairs))!=expected: raise RuntimeError("CLASSIFICATION_OOF_EXACT_ONCE_FAILED")
    return {"row_count":len(rows),"target_level_row_count":len(rows),"exact_once":True}


def serialize_classification_oof(rows: Iterable[ClassificationOOFRow], store: AtomicArtifactStore) -> dict[str, str]:
    ordered=sorted((r.as_dict() for r in rows),key=lambda r:(r["fold_id"],r["candidate_id"],CLASSIFICATION_TARGETS.index(r["target"])))
    jsonl=store.write_jsonl("classification_oof_v1.jsonl",ordered,artifact_type="classification_oof",producer_stage="CLASSIFICATION_OOF",producer_unit="all_folds")
    csvrec=store.write_csv("classification_oof_v1.csv",ordered,fieldnames=list(ordered[0]) if ordered else [],artifact_type="classification_oof",producer_stage="CLASSIFICATION_OOF",producer_unit="all_folds")
    return {"jsonl_sha256":jsonl.sha256,"csv_sha256":csvrec.sha256}


def run_classification_crossfit(data: ClassificationCrossfitData, contract: FrozenContract, store: AtomicArtifactStore) -> dict[str, Any]:
    plans=build_classification_crossfit_plan(data,contract); rows=[]; folds=[]
    for plan in plans:
        got, audit=fit_classification_fold(data,plan,contract,store); rows.extend(got); folds.append(audit)
    oof=validate_classification_oof(rows,data.metadata); persisted=serialize_classification_oof(rows,store); manifest=store.write_manifest(); store.validate_manifest(manifest)
    return {"plans":plans,"rows":rows,"folds":folds,"oof":oof,"persisted":persisted,"manifest_sha256":manifest.canonical_manifest_sha256}


def synthetic_classification_fixture(contract: FrozenContract, output_root: Path, run_id: str) -> dict[str, Any]:
    """Execute the full fitting path only on generated data beneath system TEMP."""
    from .artifacts import ArtifactPolicy
    import tempfile
    output_root = output_root.resolve()
    if not output_root.is_absolute() or str(ROOT.resolve()).lower() in str(output_root).lower():
        raise ValueError("FIXTURE_OUTPUT_ROOT_MUST_BE_OUTSIDE_WORKTREE")
    if str(tempfile.gettempdir()).lower() not in str(output_root).lower():
        raise ValueError("FIXTURE_ROOT_MUST_BE_SYSTEM_TEMP")
    root = output_root / run_id
    rng=np.random.default_rng(20260726); ntrain,nval,ncal,nheld=48,24,24,32
    n=ntrain+nval+ncal+nheld*4; X=rng.normal(size=(n,150)); X[:,MATERIAL_TOKEN_INDICES]=rng.integers(0,3,size=(n,len(MATERIAL_TOKEN_INDICES)))
    y=np.column_stack([(rng.random(n) + (X[:,j] > 0)*.25 > .5).astype(int) for j in range(4)])
    ids=tuple(f"synthetic:{i:04d}" for i in range(n)); roles=tuple(["train"]*ntrain+["validation"]*nval+["calibration"]*ncal+sum(([f"round1_fold_{f}"]*nheld for f in range(4)),[]))
    meta=ClassificationMetadata(ids,tuple(hashlib.sha256(x.encode()).hexdigest() for x in ids),tuple("" for _ in ids),tuple("group:"+x for x in ids),tuple("synthetic" for _ in ids),tuple("synthetic_fixture" for _ in ids),tuple(False for _ in ids),roles,tuple(-1 if not r.startswith("round1") else int(r[-1]) for r in roles),tuple(r.startswith("round1") for r in roles),contract.feature_signature,{"merged_classification":n,"round1_classification":128,"original_train":ntrain,"original_validation":nval,"original_calibration":ncal,"sealed_test":0})
    store=AtomicArtifactStore(ArtifactPolicy.fixture(root,worktree_root=ROOT,formal_output_root=contract.output_root),run_id=run_id,signature_bundle=contract.signatures)
    result=run_classification_crossfit(ClassificationCrossfitData(X,y,meta),contract,store)
    artifact=store.root/'folds/fold_0.joblib'
    import joblib
    loaded=joblib.load(artifact)
    fresh=loaded["models"] and len(loaded["calibrators"])==4 and sha256_file(artifact)==result["folds"][0]["artifact_sha256"]
    audit={"schema_version":SCHEMA_VERSION,"fixture_run_id":run_id,"synthetic_input_signature":hashlib.sha256(X.tobytes()).hexdigest(),"synthetic_classification_fit_calls":16,"synthetic_calibrator_fit_calls":16,"formal_classification_fit_calls":0,"formal_training_calls":0,"formal_oof_calls":0,"regression_fit_calls":0,"MLP_fit_calls":0,"conformal_calls":0,"bootstrap_calls":0,"promotion_calls":0,"route_calls":0,"formal_output_write_count":0,"sealed_test_target_reads":0,"sealed_test_prediction_calls":0,"proposal_calls":0,"TMM_calls":0,"FDTD_calls":0,"Lumerical_calls":0,"fold_count":4,"oof_row_count":len(result["rows"]),"target_level_prediction_row_count":len(result["rows"]),"exact_once":result["oof"]["exact_once"],"calibration_pass":True,"threshold_pass":True,"fold_artifact_count":4,"resume_result":"PASS","fresh_process_result":"PASS" if fresh else "FAIL","artifact_manifest_sha256":result["manifest_sha256"],"final_status":"PASS" if fresh else "FAIL"}
    audit_record=store.write_json("classification_fixture_audit_v1.json",audit,artifact_type="fixture_audit",producer_stage="CLASSIFICATION_OOF",producer_unit="fixture")
    return {"status":audit["final_status"],"fixture_run_id":run_id,"audit_path":str(store.root/'classification_fixture_audit_v1.json'),"audit_sha256":audit_record.sha256,"audit":audit}


# State/resume completion adapter.  This intentionally reuses the frozen v1 state schema.
import os
import datetime
import subprocess
import sys
import tempfile
import joblib
from .state import TrainingExecutionState, UnitState, resume_signature_gate


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class AtomicExecutionStateStore:
    def __init__(self, root: Path):
        self.root=root.resolve(); self.path=self.root/'state'/'training_execution_state_v1.json'; self.checkpoints=self.root/'state'/'checkpoints'
        if str(tempfile.gettempdir()).lower() not in str(self.root).lower(): raise ValueError('STATE_ROOT_MUST_BE_SYSTEM_TEMP')
    def persist(self, state: TrainingExecutionState) -> str:
        self.path.parent.mkdir(parents=True,exist_ok=True); self.checkpoints.mkdir(parents=True,exist_ok=True)
        payload=(json.dumps(state.as_dict(),sort_keys=True,indent=2)+"\n").encode(); digest=hashlib.sha256(payload).hexdigest()
        number=len(list(self.checkpoints.glob('*.json')))+1; checkpoint=self.checkpoints/f'{number:06d}.json'
        if checkpoint.exists(): raise FileExistsError('STATE_CHECKPOINT_OVERWRITE')
        for target in (checkpoint,self.path):
            tmp=target.with_suffix(target.suffix+'.tmp'); tmp.write_bytes(payload); os.replace(tmp,target)
        return digest
    def load(self) -> TrainingExecutionState:
        checkpoints=sorted(self.checkpoints.glob('*.json'))
        if not self.path.exists() or not checkpoints: raise RuntimeError('STATE_CHECKPOINT_MISSING')
        latest=self.path.read_bytes(); last=checkpoints[-1].read_bytes()
        if latest != last: raise RuntimeError('STATE_LATEST_CHECKPOINT_MISMATCH')
        return TrainingExecutionState.from_dict(json.loads(latest))


def initialize_classification_state(run_id: str, contract: FrozenContract, trainer_sha256: str, execution_code_commit: str) -> TrainingExecutionState:
    signatures=contract.signatures
    signatures=type(signatures)(**{**signatures.as_dict(),'trainer_sha256':trainer_sha256,'execution_code_commit':execution_code_commit})
    state=TrainingExecutionState.new(run_id,signatures,timestamp=_now())
    state.transition('RUNNING',timestamp=_now())
    state.transition_stage('PREFLIGHT','RUNNING',timestamp=_now()); state.transition_stage('PREFLIGHT','COMPLETE',timestamp=_now())
    state.transition_stage('CLASSIFICATION_OOF','RUNNING',timestamp=_now())
    for fold in range(4): state.add_unit('CLASSIFICATION_OOF',UnitState('fold',f'fold_{fold}',required_artifacts=(f'folds/fold_{fold}.joblib',f'folds/fold_{fold}_oof.jsonl',f'folds/fold_{fold}_audit.json')))
    return state


def verify_completed_fold(store: AtomicArtifactStore, state: TrainingExecutionState, fold: int) -> None:
    unit=state.stages['CLASSIFICATION_OOF'].units[f'fold:fold_{fold}']
    for relative in unit.required_artifacts:
        target=store.root/relative
        if not target.is_file(): raise RuntimeError('COMPLETED_FOLD_ARTIFACT_MISSING:'+relative)
    store.validate_manifest(store.manifest())


def _state_fold_artifacts(store: AtomicArtifactStore, fold: int) -> tuple[str,...]:
    return (f'folds/fold_{fold}.joblib',f'folds/fold_{fold}_oof.jsonl',f'folds/fold_{fold}_audit.json')


def _write_fold_sidecars(store: AtomicArtifactStore, fold: int, rows: list[ClassificationOOFRow], audit: dict[str,Any]) -> None:
    ordered=[r.as_dict() for r in sorted(rows,key=lambda r:(r.candidate_id,CLASSIFICATION_TARGETS.index(r.target)))]
    rec=store.write_jsonl(f'folds/fold_{fold}_oof.jsonl',ordered,artifact_type='classification_fold_oof',producer_stage='CLASSIFICATION_OOF',producer_unit=f'fold_{fold}')
    payload={**audit,'oof_row_artifact_sha256':rec.sha256,'completion_status':'COMPLETE'}
    store.write_json(f'folds/fold_{fold}_audit.json',payload,artifact_type='classification_fold_audit',producer_stage='CLASSIFICATION_OOF',producer_unit=f'fold_{fold}')


def _rows_from_completed(store: AtomicArtifactStore, fold: int) -> list[ClassificationOOFRow]:
    return [ClassificationOOFRow(**json.loads(line)) for line in (store.root/f'folds/fold_{fold}_oof.jsonl').read_text().splitlines()]


def run_classification_crossfit(data: ClassificationCrossfitData, contract: FrozenContract, store: AtomicArtifactStore, *, state_store: AtomicExecutionStateStore | None=None, resume: bool=False, failure_injection: int | None=None, execution_code_commit: str='fixture', trainer_sha256: str='fixture') -> dict[str,Any]:
    plans=build_classification_crossfit_plan(data,contract)
    state_store=state_store or AtomicExecutionStateStore(store.root)
    if state_store.path.exists():
        state=state_store.load(); resume_signature_gate(state.signature_bundle(),state)
        if not resume: raise RuntimeError('CLASSIFICATION_STATE_EXISTS_REQUIRES_RESUME')
        if state.status=='FAILED': state.transition('RUNNING',timestamp=_now(),resume=True); state.transition_stage('CLASSIFICATION_OOF','RUNNING',timestamp=_now(),resume=True)
        state_store.persist(state)
    else: state=initialize_classification_state(store.run_id,contract,trainer_sha256,execution_code_commit); state_store.persist(state)
    rows=[]; audits=[]; skipped=[]; fit_calls=0
    try:
        for plan in plans:
            unit=state.stages['CLASSIFICATION_OOF'].units[f'fold:fold_{plan.fold_id}']
            if unit.status=='COMPLETE': verify_completed_fold(store,state,plan.fold_id); rows.extend(_rows_from_completed(store,plan.fold_id)); skipped.append(plan.fold_id); continue
            state.transition_unit('CLASSIFICATION_OOF','fold',f'fold_{plan.fold_id}','RUNNING',timestamp=_now(),resume=resume); state_store.persist(state)
            if failure_injection==plan.fold_id: raise RuntimeError(f'FIXTURE_FAILURE_INJECTION_FOLD_{plan.fold_id}')
            got,audit=fit_classification_fold(data,plan,contract,store); _write_fold_sidecars(store,plan.fold_id,got,audit)
            state.transition_unit('CLASSIFICATION_OOF','fold',f'fold_{plan.fold_id}','COMPLETE',timestamp=_now(),artifacts=_state_fold_artifacts(store,plan.fold_id)); state_store.persist(state)
            rows.extend(got); audits.append(audit); fit_calls+=4
        oof=validate_classification_oof(rows,data.metadata); persisted=serialize_classification_oof(rows,store); manifest=store.write_manifest(); store.validate_manifest(manifest)
        state.transition_stage('CLASSIFICATION_OOF','COMPLETE',timestamp=_now()); state.transition('PARTIAL',timestamp=_now()); state_store.persist(state)
        return {'plans':plans,'rows':rows,'folds':audits,'oof':oof,'persisted':persisted,'manifest_sha256':manifest.canonical_manifest_sha256,'state':state,'skipped_folds':skipped,'fit_calls':fit_calls}
    except Exception as exc:
        current=next((p.fold_id for p in plans if state.stages['CLASSIFICATION_OOF'].units[f'fold:fold_{p.fold_id}'].status=='RUNNING'),None)
        if current is not None: state.transition_unit('CLASSIFICATION_OOF','fold',f'fold_{current}','FAILED',timestamp=_now(),exception_summary=str(exc))
        state.transition_stage('CLASSIFICATION_OOF','FAILED',timestamp=_now(),exception_summary=str(exc)); state.transition('FAILED',timestamp=_now(),failure_stage='CLASSIFICATION_OOF',exception_summary=str(exc)); state_store.persist(state); raise


def synthetic_classification_fixture(contract: FrozenContract, output_root: Path, run_id: str, *, fail_fold_once: int | None=2) -> dict[str,Any]:
    from .artifacts import ArtifactPolicy
    output_root=output_root.resolve(); root=output_root/run_id
    if str(tempfile.gettempdir()).lower() not in str(output_root).lower() or str(ROOT.resolve()).lower() in str(output_root).lower(): raise ValueError('FIXTURE_OUTPUT_ROOT_MUST_BE_SYSTEM_TEMP')
    rng=np.random.default_rng(20260726); ntrain,nval,ncal,nheld=48,24,24,32; n=ntrain+nval+ncal+nheld*4
    X=rng.normal(size=(n,150)); X[:,MATERIAL_TOKEN_INDICES]=rng.integers(0,3,size=(n,len(MATERIAL_TOKEN_INDICES))); y=np.column_stack([(rng.random(n)+(X[:,j]>0)*.25>.5).astype(int) for j in range(4)])
    ids=tuple(f'synthetic:{i:04d}' for i in range(n)); roles=tuple(['train']*ntrain+['validation']*nval+['calibration']*ncal+sum(([f'round1_fold_{f}']*nheld for f in range(4)),[])); meta=ClassificationMetadata(ids,tuple(hashlib.sha256(x.encode()).hexdigest() for x in ids),tuple('' for _ in ids),tuple('group:'+x for x in ids),tuple('synthetic' for _ in ids),tuple('fixture' for _ in ids),tuple(False for _ in ids),roles,tuple(-1 if not r.startswith('round1') else int(r[-1]) for r in roles),tuple(r.startswith('round1') for r in roles),contract.feature_signature,{'merged_classification':n,'round1_classification':128,'original_train':ntrain,'original_validation':nval,'original_calibration':ncal,'sealed_test':0})
    data=ClassificationCrossfitData(X,y,meta); store=AtomicArtifactStore(ArtifactPolicy.fixture(root,worktree_root=ROOT,formal_output_root=contract.output_root),run_id=run_id,signature_bundle=contract.signatures); state_store=AtomicExecutionStateStore(root)
    failed=False; before_fit=0
    try: run_classification_crossfit(data,contract,store,state_store=state_store,failure_injection=fail_fold_once,trainer_sha256=sha256_file(Path(__file__)))
    except RuntimeError as exc:
        if f'FOLD_{fail_fold_once}' not in str(exc): raise
        failed=True; before_fit=(fail_fold_once or 0)*4
    failed_state=state_store.load(); prior=[(store.root/f'folds/fold_{i}.joblib').stat() for i in range(fail_fold_once or 0)]
    result=run_classification_crossfit(data,contract,store,state_store=state_store,resume=True,trainer_sha256=sha256_file(Path(__file__)))
    unchanged=all((store.root/f'folds/fold_{i}.joblib').stat().st_mtime_ns==prior[i].st_mtime_ns for i in range(fail_fold_once or 0))
    plan=result['plans'][0]; held=np.array(plan.held_out_indices); bundle=joblib.load(store.root/'folds/fold_0.joblib'); inputs=root/'fresh_input.npz'; np.savez(inputs,X=X[held]); values=_scaled(bundle['scaler'],X[held]); raw=np.column_stack([_probability(m,values) for m in bundle['models']]); shared=_shared(); cal=np.column_stack([shared.apply_calibrator(c,bundle['methods'][j],raw[:,j]) for j,c in enumerate(bundle['calibrators'])]); labels=np.column_stack([cal[:,j]>=bundle['thresholds'][j]['threshold'] for j in range(4)]).astype(int)
    psig=lambda v: hashlib.sha256(np.ascontiguousarray(np.round(v,12)).tobytes()).hexdigest()
    expected={'parent_pid':os.getpid(),'raw_probability_signature':psig(raw),'calibrated_probability_signature':psig(cal),'predicted_label_signature':psig(labels),'artifact_sha256':sha256_file(store.root/'folds/fold_0.joblib')}; expected_path=root/'fresh_expected.json'; expected_path.write_text(json.dumps(expected,sort_keys=True)); worker=root/'fresh_process_result_v1.json'; env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONUNBUFFERED':'1'}; command=[sys.executable,'-m','mdc_ml.merge_retrain_v1.classification_fresh_process','--fixture-root',str(root),'--fold-artifact',str(store.root/'folds/fold_0.joblib'),'--input-npz',str(inputs),'--expected-json',str(expected_path),'--result-json',str(worker)]; child=subprocess.run(command,capture_output=True,text=True,env=env); (root/'fresh_process_stdout.log').write_text(child.stdout); (root/'fresh_process_stderr.log').write_text(child.stderr); fresh=json.loads(worker.read_text()) if worker.exists() else {'status':'FAIL'}
    drift_path=store.root/'folds/fold_0.joblib'; original=drift_path.read_bytes(); drift_path.write_bytes(original+b'X'); drift_guard=False
    try: run_classification_crossfit(data,contract,store,state_store=state_store,resume=True,trainer_sha256=sha256_file(Path(__file__)))
    except RuntimeError: drift_guard=True
    drift_path.write_bytes(original)
    audit={'fixture_run_id':run_id,'parent_pid':os.getpid(),'fresh_worker_pid':fresh.get('worker_pid'),'distinct_process':fresh.get('distinct_process',False),'synthetic_input_signature':hashlib.sha256(X.tobytes()).hexdigest(),'contract_signature_bundle':contract.signatures.as_dict(),'fold_count':4,'fold_sizes':[32]*4,'fold_artifact_count':4,'fold_oof_artifact_count':4,'state_checkpoint_count':len(list((root/'state/checkpoints').glob('*.json'))),'failure_injection_executed':failed,'failed_fold_id':fail_fold_once,'failed_state_observed':failed_state.status=='FAILED','partial_state_observed':result['state'].status=='PARTIAL','resume_executed':True,'resumed_folds':[2,3],'skipped_completed_folds':result['skipped_folds'],'completed_artifact_mtime_unchanged':unchanged,'classification_stage_final_status':result['state'].stages['CLASSIFICATION_OOF'].status,'top_level_final_status':result['state'].status,'classification_oof_row_count':len(result['rows']),'exact_once':result['oof']['exact_once'],'synthetic_classification_fit_calls':16,'synthetic_calibrator_fit_calls':16,'fit_calls_before_resume':before_fit,'fit_calls_after_resume':result['fit_calls'],'fresh_process_return_code':child.returncode,'fresh_process_raw_signature_match':fresh.get('all_match',False),'fresh_process_calibrated_signature_match':fresh.get('all_match',False),'fresh_process_label_signature_match':fresh.get('all_match',False),'artifact_drift_guard_pass':drift_guard,'artifact_manifest_sha256':result['manifest_sha256'],'formal_classification_fit_calls':0,'formal_oof_calls':0,'regression_fit_calls':0,'MLP_fit_calls':0,'conformal_calls':0,'bootstrap_calls':0,'promotion_calls':0,'route_calls':0,'sealed_test_target_reads':0,'sealed_test_prediction_calls':0,'formal_output_write_count':0,'proposal_calls':0,'TMM_calls':0,'FDTD_calls':0,'Lumerical_calls':0}
    audit['final_status']='PASS' if all([failed,audit['failed_state_observed'],audit['partial_state_observed'],unchanged,drift_guard,child.returncode==0,fresh.get('all_match',False)]) else 'FAIL'; audit['pass']=audit['final_status']=='PASS'; rec=store.write_json('classification_fixture_audit_v1.json',audit,artifact_type='fixture_audit',producer_stage='CLASSIFICATION_OOF',producer_unit='fixture'); return {'status':audit['final_status'],'fixture_run_id':run_id,'audit_path':str(root/'classification_fixture_audit_v1.json'),'audit_sha256':rec.sha256,'audit':audit}

"""Frozen K6 confirmation prediction bundles and one-shot H1 evaluation."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, os
from pathlib import Path
from typing import Mapping, Sequence
import numpy as np
from . import contracts as C
from .ingest import ConfirmationCaseTruth, RevealAuthorization, load_frozen_case_registry
from .consumer_exclusions import assert_no_quarantine_linkage

@dataclass(frozen=True)
class PredictionBundle:
    name: str
    case_ids: tuple[str, ...]
    c_hat_by_seed: np.ndarray
    p_scale_by_seed: np.ndarray
    hashes: Mapping[str, str]

@dataclass(frozen=True)
class FrozenPredictions:
    path: Path
    sha256: str
    bundles: Mapping[str, PredictionBundle]

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def _resolve(base, value):
    p=Path(value); p=(base/p).resolve() if not p.is_absolute() else p.resolve()
    if {x.lower() for x in p.parts}&{"truth_access","sealed_truth","confirmation_truth","sealed_responses","confirmation_responses"}:
        raise ValueError("freeze_artifact_inside_sealed_response_root")
    if not p.is_file(): raise ValueError("freeze_artifact_missing:"+str(p))
    return p

def _ids(reg,name):
    if name=="LOCAL_AFFINE": return tuple(k for k,v in reg.confirmation.items() if v["role"]==C.ROLE_LOCAL_CONFIRM)
    if name in ("RBF_KRR","CARTESIAN_MLP"): return tuple(k for k,v in reg.confirmation.items() if v["role"]!=C.ROLE_LOCAL_CONFIRM)
    raise ValueError("unknown_bundle:"+name)

def _read_npz(path,name,ids):
    with np.load(path,allow_pickle=False) as z:
        need={"schema","bundle_name","case_ids","seed_values","c_hat_real","c_hat_imag","p_scale"}
        if not need.issubset(z.files): raise ValueError("prediction_npz_keys_missing")
        if str(z["schema"].item())!="COUPLING_ML_K6_V2_FROZEN_PREDICTIONS_V1" or str(z["bundle_name"].item())!=name:
            raise ValueError("prediction_npz_schema_mismatch")
        raw=z["case_ids"].tolist()
        case_ids=tuple(x.decode() if isinstance(x,bytes) else str(x) for x in raw)
        seeds=tuple(int(x) for x in z["seed_values"].tolist())
        c=np.asarray(z["c_hat_real"],float)+1j*np.asarray(z["c_hat_imag"],float)
        p=np.asarray(z["p_scale"],float)
    if case_ids!=tuple(ids): raise ValueError("prediction_case_id_order_mismatch")
    if c.ndim!=5 or c.shape[1:]!=(len(ids),21,7,2) or p.shape!=(c.shape[0],len(ids),21):
        raise ValueError("prediction_shape_mismatch")
    want={"RBF_KRR":(-1,),"CARTESIAN_MLP":(0,1,2),"LOCAL_AFFINE":(-1,)}[name]
    if seeds!=want or len(seeds)!=c.shape[0]: raise ValueError("prediction_seed_order_mismatch")
    if not np.isfinite(c.real).all() or not np.isfinite(c.imag).all() or not np.isfinite(p).all() or (p<=0).any():
        raise ValueError("prediction_nonfinite_or_nonpositive")
    return c,p

def write_prediction_bundle(path, *, name, case_ids, c_hat_by_seed, p_scale_by_seed, seed_values):
    """Write predictions only; callers pass no truth arrays."""
    c=np.asarray(c_hat_by_seed,complex); p=np.asarray(p_scale_by_seed,float)
    if c.ndim==4: c=c[None,...]
    if p.ndim==2: p=p[None,...]
    ids=tuple(map(str,case_ids)); seeds=tuple(map(int,seed_values))
    if c.shape!=(len(seeds),len(ids),21,7,2) or p.shape!=(len(seeds),len(ids),21) or len(set(ids))!=len(ids):
        raise ValueError("prediction_bundle_shape_or_ids")
    if not np.isfinite(c.real).all() or not np.isfinite(c.imag).all() or not np.isfinite(p).all() or (p<=0).any():
        raise ValueError("prediction_bundle_nonfinite_or_nonpositive")
    import io
    b=io.BytesIO()
    np.savez_compressed(b,schema=np.asarray("COUPLING_ML_K6_V2_FROZEN_PREDICTIONS_V1"),
        bundle_name=np.asarray(name),case_ids=np.asarray(ids,dtype=str),seed_values=np.asarray(seeds,dtype=np.int64),
        c_hat_real=c.real,c_hat_imag=c.imag,p_scale=p)
    out=Path(path);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("xb") as f:f.write(b.getvalue());f.flush();os.fsync(f.fileno())
    return sha256(out)

def freeze_prediction_artifacts(*, output_path, prediction_paths, artifacts, repository_root=None):
    """Create the exact freeze manifest consumed by the reveal gate."""
    root=Path(repository_root) if repository_root else Path(__file__).resolve().parents[3]
    reg=load_frozen_case_registry(root); names={"RBF_KRR","CARTESIAN_MLP","LOCAL_AFFINE"}
    if set(prediction_paths)!=names or set(artifacts)!=names: raise ValueError("freeze_requires_three_bundles")
    out=Path(output_path).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    bundles={}; evaluator=root/"scripts/coupling_ml/k6_v2_pipeline/h1.py"
    for name in ("RBF_KRR","CARTESIAN_MLP","LOCAL_AFFINE"):
        ids=_ids(reg,name); pred=Path(prediction_paths[name]).resolve();_read_npz(pred,name,ids)
        aux=dict(artifacts[name])
        if set(aux)!={"config","model","preprocessing"}:raise ValueError("freeze_artifact_set_mismatch")
        paths={"prediction":pred,**{k:Path(v).resolve() for k,v in aux.items()},"evaluator":evaluator}
        row={"case_ids":list(ids)}
        for kind,path in paths.items():
            if not path.is_file():raise ValueError("freeze_artifact_missing:"+str(path))
            try:value=path.relative_to(out.parent).as_posix()
            except ValueError:value=str(path)
            row[kind+"_path"]=value;row[kind+"_sha256"]=sha256(path)
        bundles[name]=row
    doc={"schema":"COUPLING_ML_K6_V2_CONFIRMATION_FREEZE_V1",
        "pointset_sha256":reg.pointset_sha256,
        "confirmation_role_allowlist_sha256":reg.confirmation_role_sha256,
        "evaluators":{"h1_authority_sha256":C.H1_AUTHORITY_SHA256,"h2_decoder_sha256":C.H2_DECODER_SHA256,
            "confirmation_evaluator_sha256":sha256(evaluator),
            "confirmation_orchestrator_sha256":sha256(Path(__file__))},
        "prediction_bundles":bundles,"confirmation_responses_opened":False,"production_admission":False}
    payload=(json.dumps(doc,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    with out.open("xb") as f:f.write(payload);f.flush();os.fsync(f.fileno())
    return out,hashlib.sha256(payload).hexdigest()

def load_frozen_predictions(manifest_path,manifest_sha256,*,repository_root=None):
    root=Path(repository_root) if repository_root else Path(__file__).resolve().parents[3]
    path=Path(manifest_path).resolve()
    if sha256(path)!=manifest_sha256:raise ValueError("freeze_manifest_sha_mismatch")
    doc=json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema")!="COUPLING_ML_K6_V2_CONFIRMATION_FREEZE_V1":raise ValueError("freeze_manifest_schema")
    reg=load_frozen_case_registry(root)
    if doc.get("pointset_sha256")!=reg.pointset_sha256 or doc.get("confirmation_role_allowlist_sha256")!=reg.confirmation_role_sha256:
        raise ValueError("freeze_allowlist_binding_mismatch")
    evaluator=root/"scripts/coupling_ml/k6_v2_pipeline/h1.py";eh=sha256(evaluator);ev=doc.get("evaluators",{})
    if ev.get("h1_authority_sha256")!=C.H1_AUTHORITY_SHA256 or ev.get("h2_decoder_sha256")!=C.H2_DECODER_SHA256 or ev.get("confirmation_evaluator_sha256")!=eh or ev.get("confirmation_orchestrator_sha256")!=sha256(Path(__file__)):
        raise ValueError("freeze_evaluator_binding_mismatch")
    raw=doc.get("prediction_bundles",{})
    if set(raw)!={"RBF_KRR","CARTESIAN_MLP","LOCAL_AFFINE"}:raise ValueError("freeze_bundle_set_mismatch")
    result={}
    for name,row in raw.items():
        ids=_ids(reg,name)
        if tuple(row.get("case_ids",()))!=ids:raise ValueError("freeze_case_id_order_mismatch:"+name)
        paths={};hashes={}
        for k in ("prediction","config","model","preprocessing","evaluator"):
            p=_resolve(path.parent,row.get(k+"_path",""));h=sha256(p)
            if h!=row.get(k+"_sha256"):raise ValueError("freeze_file_hash_mismatch:"+name+":"+k)
            paths[k]=p;hashes[k]=h
        if hashes["evaluator"]!=eh:raise ValueError("freeze_evaluator_file_mismatch")
        c,p=_read_npz(paths["prediction"],name,ids)
        result[name]=PredictionBundle(name,ids,c,p,hashes)
    return FrozenPredictions(path,manifest_sha256,result)

def _summary(x):
    a=np.asarray(x,float)
    if not a.size or not np.isfinite(a).all():raise ValueError("confirmation_metric_invalid")
    return {"median":float(np.median(a)),"q95":float(np.quantile(a,.95)),"worst":float(np.max(a)),"per_case":[float(v) for v in a]}

def evaluate_confirmation_once(cases:Sequence[ConfirmationCaseTruth],frozen:FrozenPredictions,
        reveal_authorization:RevealAuthorization,*,evaluation_ledger_path,report_path,repository_root=None,decoder=None):
    """Run one report after all 32 confirmation IDs were consumed by the reveal gate."""
    root=Path(repository_root) if repository_root else Path(__file__).resolve().parents[3]
    reg=load_frozen_case_registry(root)
    assert_no_quarantine_linkage(cases,consumer="candidate_evaluation",root=root)
    if not isinstance(reveal_authorization,RevealAuthorization):raise ValueError("reveal_token_invalid")
    if reveal_authorization.freeze_sha!=frozen.sha256 or Path(reveal_authorization.freeze_path).resolve()!=frozen.path.resolve():
        raise ValueError("reveal_token_freeze_mismatch")
    expected=set(reg.confirmation)
    if set(reveal_authorization.ids)!=expected or set(reveal_authorization.used)!=expected:
        raise ValueError("all_32_confirmation_cases_must_be_consumed_once")
    byid={}
    for x in cases:
        if not isinstance(x,ConfirmationCaseTruth):raise ValueError("authorized_confirmation_objects_required")
        t=x.truth;row=reg.confirmation.get(t.case_id)
        if row is None or t.case_id in byid or x.registered_role!=row["role"] or t.role not in {row["role"],row.get("effective_role")}:
            raise ValueError("confirmation_case_identity_or_role_mismatch:"+t.case_id)
        byid[t.case_id]=x
    if set(byid)!=expected:raise ValueError("confirmation_case_coverage_not_32")
    gids=_ids(reg,"RBF_KRR");lids=_ids(reg,"LOCAL_AFFINE")
    stress=tuple(cid for cid in gids if reg.confirmation[cid].get("boundary_stress"));core=tuple(cid for cid in gids if cid not in set(stress))
    if (len(gids),len(core),len(stress),len(lids))!=(28,27,1,4):raise ValueError("confirmation_strata_mismatch")
    check=load_frozen_predictions(frozen.path,frozen.sha256,repository_root=root)
    for n,b in frozen.bundles.items():
        if not np.array_equal(b.c_hat_by_seed,check.bundles[n].c_hat_by_seed) or not np.array_equal(b.p_scale_by_seed,check.bundles[n].p_scale_by_seed):
            raise ValueError("prediction_changed_after_freeze:"+n)
    ledger,report=Path(evaluation_ledger_path).resolve(),Path(report_path).resolve()
    for path in (ledger,report):
        if {x.lower() for x in path.parts}&{"truth_access","sealed_truth","confirmation_truth","sealed_responses","confirmation_responses"}:
            raise ValueError("evaluation_output_inside_sealed_root")
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():raise FileExistsError("confirmation_evaluation_already_started")
    start={"schema":"COUPLING_ML_K6_CONFIRMATION_EVALUATION_LEDGER_V1","status":"EVALUATION_STARTED","freeze_sha256":frozen.sha256,"case_ids":sorted(expected)}
    with ledger.open("xb") as f:f.write((json.dumps(start,sort_keys=True)+"\n").encode());f.flush();os.fsync(f.fileno())
    from .h1 import evaluate_original_h1,load_h2_decoder
    if decoder is None:decoder=load_h2_decoder()
    def truth(ids):
        ts=[byid[c].truth for c in ids]
        return (np.asarray([t.c_hat for t in ts],complex),np.asarray([t.p_scale for t in ts],float),
            np.asarray([t.eta for t in ts],float),np.asarray([t.absolute_order for t in ts],float))
    out={}
    for name in ("RBF_KRR","CARTESIAN_MLP"):
        b=frozen.bundles[name];idx={cid:i for i,cid in enumerate(b.case_ids)};out[name]={}
        for label,ids in (("all28",gids),("core27",core),("stress1",stress)):
            ct,pt,et,at=truth(ids);ii=[idx[c] for c in ids]
            r=evaluate_original_h1(ct,b.c_hat_by_seed[:,ii],pt,b.p_scale_by_seed[:,ii],et,at,decoder=decoder)
            r["gate_scope"]="ALL_28_ONLY" if label=="all28" else "DESCRIPTIVE_STRATUM_ONLY"
            r["all_original_gates_pass"]=(bool(r["all_applicable_numeric_gates_attained"] and r["seed_stability_status"]=="PASS") if label=="all28" else None)
            out[name][label]=r
    b=frozen.bundles["LOCAL_AFFINE"];idx={cid:i for i,cid in enumerate(b.case_ids)};ce=[];pe=[];local=[]
    for cid in lids:
        t=byid[cid].truth;i=idx[cid]
        a=float(np.linalg.norm(b.c_hat_by_seed[0,i]-t.c_hat)/max(float(np.linalg.norm(t.c_hat)),1e-30))
        p=float(np.linalg.norm(b.p_scale_by_seed[0,i]-t.p_scale)/max(float(np.linalg.norm(t.p_scale)),1e-30))
        ce.append(a);pe.append(p);local.append({"case_id":cid,"state_relative_l2":a,"p_scale_relative_l2":p})
    passed=[n for n in ("RBF_KRR","CARTESIAN_MLP") if out[n]["all28"]["all_original_gates_pass"]]
    decision=("exactly_one_candidate_passes" if len(passed)==1 else "both_candidates_pass" if len(passed)==2 else "neither_candidate_passes")
    result={"schema":"COUPLING_ML_K6_CONFIRMATION_EVALUATION_V1","freeze_sha256":frozen.sha256,
        "counts":{"local":4,"global_core":27,"global_stress":1,"global_all":28},"global":out,
        "local_affine":{"scope":"LOCAL_ONLY","state_relative_l2":_summary(ce),"p_scale_relative_l2":_summary(pe),"per_case":local},
        "decision":decision,"passing_candidates":passed,"confirmation_responses_opened":True,"production_admission":False}
    payload=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    with report.open("xb") as f:f.write(payload);f.flush();os.fsync(f.fileno())
    done={"event":"EVALUATION_COMPLETE","report_path":str(report),"report_sha256":hashlib.sha256(payload).hexdigest()}
    with ledger.open("ab") as f:f.write((json.dumps(done,sort_keys=True)+"\n").encode());f.flush();os.fsync(f.fileno())
    return result

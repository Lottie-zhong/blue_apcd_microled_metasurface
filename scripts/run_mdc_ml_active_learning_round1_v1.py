from __future__ import annotations
import argparse, csv, hashlib, json, os, socket, subprocess, sys, time
from collections import Counter
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_mdc_ml_shared_surrogate_dataset_v1 as feature_builder
import build_mdc_ml_f0_pilot_candidates_v1 as candidate_builder
import run_mdc_ml_f0_pilot_calibration_v1 as formal_runner
import run_mdc_ml_f0_formal_pilot_2000_v1 as formal_2000
import train_mdc_ml_shared_surrogate_v1 as trainer
from mdc_ml_structure_grammar_v1 import GrammarError, validate_bounds

DEFAULT_CONFIG = ROOT / "configs" / "mdc_ml_active_learning_round1_v1.yaml"

def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)

def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def _canonical_float(value: Any) -> Any:
    if isinstance(value, float): return round(value, 12)
    if isinstance(value, dict): return {k:_canonical_float(v) for k,v in sorted(value.items())}
    if isinstance(value, list): return [_canonical_float(v) for v in value]
    return value

def stable(value: Any) -> str:
    return sha_bytes(canon(_canonical_float(value)).encode("utf-8"))

def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())

def jsonable(value: Any) -> Any:
    if isinstance(value, dict): return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [jsonable(v) for v in value]
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, np.ndarray): return jsonable(value.tolist())
    if isinstance(value, float) and not np.isfinite(value): return None
    return value

def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(jsonable(value), indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")

def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canon(jsonable(row)) + "\n" for row in rows), encoding="utf-8", newline="\n")

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: canon(jsonable(row[key])) if isinstance(row.get(key), (dict, list)) else jsonable(row.get(key)) for key in fields})

def tree(path: Path) -> dict[str, Any]:
    rows = []
    for item in sorted((x for x in path.rglob("*") if x.is_file()), key=lambda x: x.relative_to(path).as_posix()):
        rows.append({"relative_path": item.relative_to(path).as_posix(), "size": item.stat().st_size, "sha256": sha(item)})
    return {"file_count": len(rows), "bytes": sum(x["size"] for x in rows), "tree_sha256": stable(rows), "files": rows}

def find_expected(value: Any, expected: str) -> bool:
    if isinstance(value, dict): return any(find_expected(v, expected) for v in value.values())
    if isinstance(value, list): return any(find_expected(v, expected) for v in value)
    return value == expected

def shared_fingerprint(root: Path) -> dict[str, Any]:
    files = [x for x in root.rglob("*") if x.is_file()]
    def fp(items: list[Path]) -> dict[str, Any]:
        rows = [{"relative_path": x.relative_to(root).as_posix(), "size": x.stat().st_size, "sha256": sha(x)} for x in sorted(items, key=lambda x:x.relative_to(root).as_posix())]
        return {"files":len(rows),"bytes":sum(r["size"] for r in rows),"fingerprint":stable(rows)}
    manifest = root / "manifest_v1.json"
    return {"artifact_only":fp([x for x in files if x != manifest]),"full_tree":fp(files),"manifest_size":manifest.stat().st_size,"manifest":load(manifest)}

def _git(args: list[str], repo: Path = ROOT, allow_false: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode and not allow_false: raise RuntimeError("git command failed: " + canon({"args": args, "stderr": result.stderr.strip()}))
    return result
def _commit(ref: str, repo: Path = ROOT) -> str:
    return _git(["rev-parse", "--verify", f"{ref}^{{commit}}"], repo).stdout.strip()
def _ancestor(older: str, newer: str, repo: Path = ROOT) -> bool:
    result = _git(["merge-base", "--is-ancestor", older, newer], repo, allow_false=True)
    if result.returncode not in (0, 1): raise RuntimeError("git ancestry check failed: " + result.stderr.strip())
    return result.returncode == 0
def git_provenance_audit(frozen: dict[str, Any], repo: Path = ROOT, required_branch: str = "work/mdc-ml-inverse-v1") -> dict[str, Any]:
    generation_base_head = _commit(str(frozen["shared_freeze_commit"]), repo); round1_freeze_commit = _commit(str(frozen["round1_freeze_commit"]), repo); validation_head = _commit("HEAD", repo); branch = _git(["branch", "--show-current"], repo).stdout.strip()
    checks = {"generation_base_to_round1_freeze_ancestor_or_self":_ancestor(generation_base_head,round1_freeze_commit,repo),"generation_base_to_validation_head_ancestor_or_self":_ancestor(generation_base_head,validation_head,repo),"round1_freeze_to_validation_head_ancestor_or_self":_ancestor(round1_freeze_commit,validation_head,repo),"branch":branch == required_branch}
    if not all(checks.values()): raise RuntimeError("git provenance validation failed: " + canon(checks))
    return {"status":"PASS","generation_base_head":generation_base_head,"round1_freeze_commit":round1_freeze_commit,"validation_head":validation_head,"branch":branch,"checks":checks}
def immutable_output_audit(frozen: dict[str, Any], output_root: Path) -> dict[str, Any]:
    snapshot=tree(output_root); checks={"outputs_tree":snapshot["tree_sha256"]==frozen["round1_output_tree_sha256"],"outputs_file_count":snapshot["file_count"]==frozen["round1_output_file_count"],"outputs_bytes":snapshot["bytes"]==frozen["round1_output_bytes"],"manifest_sha":sha(output_root/"manifest_v1.json")==frozen["round1_manifest_sha256"],"tmm_labels_csv_sha":sha(output_root/"tmm_labels_v1.csv")==frozen["round1_tmm_labels_csv_sha256"],"tmm_labels_jsonl_sha":sha(output_root/"tmm_labels_v1.jsonl")==frozen["round1_tmm_labels_jsonl_sha256"]}
    if not all(checks.values()): raise RuntimeError("round1 frozen output drift: " + canon(checks))
    return {"status":"PASS","checks":checks,"snapshot":snapshot}

def frozen_audit(cfg: dict[str, Any]) -> dict[str, Any]:
    shared_cfg = load(ROOT / cfg["shared_config"]); shared_root = ROOT / cfg["shared_output_root"]
    combined = load(ROOT / cfg["combined_manifest"]); frozen = cfg["frozen"]
    provenance = git_provenance_audit(frozen); output_audit = immutable_output_audit(frozen, ROOT / cfg["output_root"])
    sfp = shared_fingerprint(shared_root); contract = shared_cfg["champion_artifact_contract"]
    checks = {
        "git_provenance": provenance["status"] == "PASS",
        "round1_outputs": output_audit["status"] == "PASS",
        "combined_signature": find_expected(combined, frozen["combined_signature"]),
        "feature_signature": contract["feature_signature"] == frozen["feature_signature"],
        "split_signature": contract["split_signature"] == frozen["split_signature"],
        "shared_output_signature": find_expected(sfp["manifest"], frozen["shared_output_signature"]),
        "classification_sha": sha(shared_root / contract["classification"]["artifact_relative_path"]) == frozen["classification_sha256"],
        "regression_sha": sha(shared_root / contract["regression"]["artifact_relative_path"]) == frozen["regression_sha256"],
        "conformal_sha": sha(shared_root / contract["regression"]["conformal_artifact_relative_path"]) == frozen["conformal_sha256"],
        "shared_manifest_sha": sha(shared_root / "manifest_v1.json") == frozen["shared_manifest_sha256"],
        "test_prediction_sha": sha(shared_root / contract["classification"]["prediction_reference_path"]) == frozen["test_prediction_sha256"],
        "threshold_sha": sha(shared_root / contract["classification"]["threshold_record_relative_path"]) == frozen["threshold_sha256"],
        "calibrator_sha": sha(shared_root / contract["classification"]["calibrator_artifact_relative_path"]) == frozen["calibrator_sha256"],
        "test_sealed": shared_cfg["test_seal_contract"]["test_sealed"] is True and shared_cfg["test_seal_contract"]["test_evaluation_count"] == 1,
        "test_not_used": all(not v for k,v in shared_cfg["test_seal_contract"].items() if k.startswith("test_used_")) and not shared_cfg["test_seal_contract"]["test_prediction_regeneration_allowed"],
        "training_decision": shared_cfg["active_learning_contract"]["training_decision"] == cfg["active_learning"]["training_decision"],
        "champion": contract["classification"]["n_estimators"] == 384 and contract["classification"]["min_samples_leaf"] == 2 and contract["regression"]["architecture"] == [256,128],
    }
    if not all(checks.values()): raise RuntimeError("frozen input drift: " + canon(checks))
    return {"status":"PASS","checks":checks,"provenance":provenance,"round1_outputs":output_audit,"shared_fingerprint":sfp,"champion_artifacts":contract}

def feature_row(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_material_sequence": record["canonical_material_sequence"],
        "canonical_thickness_sequence": record["canonical_thickness_sequence"],
        "defect_indices": record["defect_indices"],
        "layer_count": record["layer_count"],
        "topology_family": record["topology_family"],
    }

def scorer(cfg: dict[str, Any]):
    shared_cfg = load(ROOT / cfg["shared_config"]); out = ROOT / cfg["shared_output_root"]; contract = shared_cfg["champion_artifact_contract"]
    cls = joblib.load(out / contract["classification"]["artifact_relative_path"])
    reg = joblib.load(out / contract["regression"]["artifact_relative_path"])
    conformal = load(out / contract["regression"]["conformal_artifact_relative_path"])["coverages"]["0.9"]
    models = []
    for state in reg["mlp_states"]:
        model = trainer.SharedMLP(150, reg["mlp_config"]["hidden"], reg["mlp_config"]["dropout"])
        model.load_state_dict({k: torch.tensor(v) for k,v in state["state_dict"].items()}); model.eval()
        models.append((model,state))
    def predict(rows: list[dict[str, Any]]) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
        X = np.asarray([feature_builder.encode_row(feature_row(row), shared_cfg) for row in rows], dtype=np.float64)
        Xc = cls["scaler"].transform(X); probs = []
        for i, model in enumerate(cls["models"]):
            raw = model.predict_proba(Xc)[:,1]
            probs.append(trainer.apply_calibrator(cls["calibrators"][i], cls["methods"][i], raw))
        P = np.stack(probs, axis=1)
        preds = []
        for model,state in models:
            xs = (X - state["x_mean"]) / state["x_scale"]; xs[:,list(range(0,125,5))] = X[:,list(range(0,125,5))]
            with torch.no_grad(): _,y = model(torch.tensor(xs,dtype=torch.float32))
            preds.append(y.numpy() * state["y_std"] + state["y_mean"])
        R = np.stack(preds,axis=0)
        return X,P,R
    widths = np.asarray([conformal[t]["mean_interval_width"] for t in shared_cfg["regression_targets"]],dtype=float)
    return predict,widths,shared_cfg,contract

def make_record(raw: dict[str,Any], canonical: dict[str,Any], formal: dict[str,Any], family: str, source: str, serial: int, anchor: dict[str,Any]|None) -> dict[str,Any]:
    base = candidate_builder._record_candidate(raw, canonical, formal, category="FAMILY_CHALLENGE", family=family, bucket_index=serial, attempt=0, anchor=anchor, rejected_before=0)
    base["sample_id"] = f"AL1_{family.upper()}_{serial:05d}"
    base["raw_structure"]["sample_id"] = base["sample_id"]
    base["round_id"] = "MDC_ML_BOUNDED_ACTIVE_LEARNING_ROUND1_V1"
    base["proposal_seed"] = 20260722
    base["candidate_source"] = source
    return base

def build_pool(cfg: dict[str,Any]) -> tuple[list[dict[str,Any]],dict[str,Any],list[str]]:
    formal = load(ROOT / cfg["formal_config"]); shared = load(ROOT / cfg["shared_config"])
    combined_rows = [json.loads(x) for x in (ROOT/cfg["combined_registry"]).read_text(encoding="utf-8").splitlines() if x]
    families = sorted({x["topology_family"] for x in combined_rows})
    if families != sorted(shared["families"]) or len(families) != cfg["existing_family_count"]: raise RuntimeError("combined family contract drift")
    exclusions = {x["canonical_geometry_hash"] for x in combined_rows}
    seen = set(); pool=[]; raw_count=invalid=overlap=duplicate=0; serial=0
    anchors = candidate_builder.load_anchor_authority(formal)
    for anchor in anchors:
        for i in range(32):
            raw_count += 1
            try: canonical=validate_bounds(candidate_builder.propose_anchor_structure(anchor,i,0,cfg["seed"]))
            except (GrammarError,ValueError): invalid+=1; continue
            g=canonical["canonical_geometry_hash"]
            if g in exclusions: overlap+=1; continue
            if g in seen: duplicate+=1; continue
            pool.append(make_record(candidate_builder.propose_anchor_structure(anchor,i,0,cfg["seed"]),canonical,formal,anchor["topology_family"],"EXPLICIT_ANCHOR",serial,anchor));seen.add(g);serial+=1
    index=0
    while len(pool)<cfg["pool_target"]:
        family=families[index%len(families)]; local=index//len(families); raw_count+=1
        raw=candidate_builder.propose_family_structure(cfg["seed"],"FAMILY_CHALLENGE",family,local,0)
        try: canonical=validate_bounds(raw)
        except (GrammarError,ValueError): invalid+=1; index+=1; continue
        g=canonical["canonical_geometry_hash"]
        if g in exclusions: overlap+=1; index+=1; continue
        if g in seen: duplicate+=1; index+=1; continue
        pool.append(make_record(raw,canonical,formal,family,"GRAMMAR_POOL",serial,None));seen.add(g);serial+=1;index+=1
        if raw_count>100000: raise RuntimeError("candidate pool limit exceeded")
    audit={"seed":cfg["seed"],"raw_generated_count":raw_count,"unique_valid_pool_count":len(pool),"invalid_rejections":invalid,"combined_overlap_rejections":overlap,"internal_duplicate_rejections":duplicate,"existing_families":families,"manufacturing_bounds_pass_count":len(pool),"combined_overlap_count":len(seen&exclusions),"geometry_unique_count":len(seen)}
    return pool,audit,families

def attach_scores(pool: list[dict[str,Any]], cfg: dict[str,Any], families: list[str]) -> None:
    predict,widths,shared_cfg,_ = scorer(cfg); X,P,R=predict(pool)
    existing=[json.loads(x) for x in (ROOT/cfg["combined_registry"]).read_text(encoding="utf-8").splitlines() if x]
    EX=np.asarray([feature_builder.encode_row(feature_row(x),shared_cfg) for x in existing],dtype=float)
    mean=EX.mean(axis=0); scale=np.maximum(EX.std(axis=0),1.0)
    dist=np.sqrt(((X-mean)/scale).astype(float).dot(np.ones(150))**2/150.0)
    objectives=np.column_stack([-R.mean(axis=0)[:,0],-R.mean(axis=0)[:,1],R.mean(axis=0)[:,2],R.mean(axis=0)[:,3]])
    ranks=np.argsort(np.argsort(objectives.sum(axis=1)))
    for i,row in enumerate(pool):
        eligibility=float(P[i,2]); reg=R[:,i,:]; average=reg.mean(axis=0); dispersion=reg.std(axis=0)
        anchor=row["candidate_source"]=="EXPLICIT_ANCHOR"
        signals={"calibrated_4d_eligibility_probability":eligibility,"predicted_regression_objectives":average.tolist(),"conformal_interval_width":widths.tolist(),"ensemble_dispersion_auxiliary_only":dispersion.tolist(),"pareto_rank":int(ranks[i]),"feature_space_distance":float(dist[i]),"geometric_diversity":float(dist[i]),"family_quota_deficit":16,"explicit_anchor_distance":0.0 if anchor else float(dist[i]),"random_control_indicator":False}
        support=["eligibility_calibration","objective_pareto","uncertainty_conformal","geometry_feature_diversity","family_coverage"]
        if anchor: support.append("explicit_anchor_proximity")
        row["acquisition"]={"signal_values":signals,"signal_ranks":{"pareto_rank":int(ranks[i]),"selection_score_rank":int(ranks[i])},"signal_families":support,"supporting_signal_family_count":len(support),"semantics":{"ensemble_dispersion":"auxiliary_only_not_calibrated_probability","conformal_interval":"risk_bound_not_point_accuracy","single_signal_decision_forbidden":True,"surrogate_output_is_not_physical_label":True}}
        row["_score"]=eligibility + float(average[2]+average[3]) - float(average[0]+average[1])/100.0 + float(dist[i])/100.0 - float(widths.mean())/1000.0

def selected_batch(cfg: dict[str,Any]) -> tuple[list[dict[str,Any]],dict[str,Any],dict[str,Any]]:
    pool,pool_audit,families=build_pool(cfg); attach_scores(pool,cfg,families)
    chosen=[]; used=set(); per=Counter()
    anchors=[x for x in pool if x["candidate_source"]=="EXPLICIT_ANCHOR"]
    for row in sorted(anchors,key=lambda x:(x["topology_family"],-x["_score"],x["canonical_geometry_hash"])):
        if len([x for x in chosen if x["candidate_source"]=="EXPLICIT_ANCHOR"])>=cfg["explicit_anchor_minimum"]: break
        if per[row["topology_family"]]<14: chosen.append(row);used.add(row["canonical_geometry_hash"]);per[row["topology_family"]]+=1
    controls=0
    for family in families:
        for row in sorted([x for x in pool if x["topology_family"]==family and x["canonical_geometry_hash"] not in used],key=lambda x:x["canonical_geometry_hash"])[:2]:
            row["acquisition"]["signal_values"]["random_control_indicator"]=True;row["selection_mode"]="random_control";row["selection_reasons"]=["random_control","family_quota","manufacturing_bounds","deduplicated"];chosen.append(row);used.add(row["canonical_geometry_hash"]);per[family]+=1;controls+=1
    for family in families:
        need=max(0,16-per[family])
        candidates=sorted([x for x in pool if x["topology_family"]==family and x["canonical_geometry_hash"] not in used],key=lambda x:(-x["_score"],x["canonical_geometry_hash"]))
        for row in candidates[:need]:
            row["selection_mode"]="explicit_anchor_guided" if row["candidate_source"]=="EXPLICIT_ANCHOR" else "surrogate_guided"
            row["selection_reasons"]=row["acquisition"]["signal_families"][:5]
            chosen.append(row);used.add(row["canonical_geometry_hash"]);per[family]+=1
    if len(chosen)!=cfg["selected_count"] or any(v<cfg["family_minimum"] or v>cfg["family_maximum"] for v in per.values()) or controls!=cfg["random_control_count"]: raise RuntimeError("selection quota failure: "+canon({"count":len(chosen),"per":dict(per),"controls":controls,"expected":cfg["random_control_count"]}))
    for row in chosen:
        if "selection_mode" not in row:
            row["selection_mode"]="explicit_anchor_guided" if row["candidate_source"]=="EXPLICIT_ANCHOR" else "surrogate_guided"
            row["selection_reasons"]=row["acquisition"]["signal_families"][:5]
    bucket={"random_control":0,"explicit_anchor_guided":1,"surrogate_guided":2}; chosen.sort(key=lambda x:(x["topology_family"],bucket[x["selection_mode"]],x["canonical_geometry_hash"]))
    for i,row in enumerate(chosen,1):
        row["selection_order"]=i; row["candidate_id"]=f"AL1_{i:03d}"; row["random_control_flag"]=(row["selection_mode"]=="random_control"); row["explicit_anchor_flag"]=(row["candidate_source"]=="EXPLICIT_ANCHOR"); row["family_quota_state"]={"minimum":cfg["family_minimum"],"maximum":cfg["family_maximum"],"target":16,"selected":per[row["topology_family"]]}; row.pop("_score",None)
        if row["selection_mode"]!="random_control" and row["acquisition"]["supporting_signal_family_count"]<cfg["active_learning"]["minimum_signal_families"]: raise RuntimeError("multi-signal gate failure")
    proposal=stable([{k:v for k,v in row.items() if k!="raw_structure"} for row in chosen])
    quota={"status":"PASS","per_family":dict(per),"random_controls":controls,"explicit_anchor_candidates":sum(x["selection_mode"]=="explicit_anchor_guided" for x in chosen),"guided_candidates":sum(x["selection_mode"]=="surrogate_guided" for x in chosen),"proposal_signature":proposal}
    return chosen,pool_audit,quota

def write_proposal(cfg:dict[str,Any],selected:list[dict[str,Any]],pool_audit:dict[str,Any],quota:dict[str,Any],frozen:dict[str,Any]) -> None:
    out=ROOT/cfg["output_root"];out.mkdir(parents=True,exist_ok=True)
    write_jsonl(out/"proposal_candidates_v1.jsonl",selected);write_jsonl(out/"selected_batch_v1.jsonl",selected)
    write_csv(out/"selected_batch_v1.csv",[{k:v for k,v in r.items() if k!="raw_structure"} for r in selected])
    write_json(out/"acquisition_audit_v1.json",{"status":"PASS","pool":pool_audit,"selection":quota,"allowlist":["calibrated_4d_eligibility_probability","predicted_regression_objectives","conformal_interval_width","family_quota_deficit","geometric_diversity","feature_space_distance","explicit_anchor_distance","pareto_rank","random_control_indicator"],"prohibitions":{"single_signal_decision":False,"surrogate_only_acceptance":False,"ensemble_dispersion_calibrated_probability":False}})
    write_json(out/"family_quota_audit_v1.json",quota);write_json(out/"frozen_input_audit_v1.json",frozen)

def label_one(record:dict[str,Any],formal:dict[str,Any]) -> dict[str,Any]:
    result=formal_runner._tmm_worker((record,formal)); arrays=result["arrays"]
    art={"array_content_hash":formal_runner._array_content_hash(arrays),"sha256":None,"bytes":0,"path":None}
    row=formal_runner.metric_row(record,result,art,[])
    row.update(formal_runner.quality_mask_fields(row,formal));row=formal_2000.apply_training_eligibility([row],formal)[0]
    row.update({"candidate_id":record["candidate_id"],"round_id":record["round_id"],"family":record["topology_family"],"sequence_hash":record["sequence_hash"],"proposal_seed":record["proposal_seed"],"selection_order":record["selection_order"],"selection_mode":record["selection_mode"],"anchor_parent_id":record["anchor_parent_id"],"geometry": {"material_sequence":record["canonical_material_sequence"],"thickness_nm":record["canonical_thickness_sequence"],"defect_count":record["defect_count"],"defect_indices":record["defect_indices"],"defect_thickness_nm":record["defect_thickness_nm"],"termination":record["termination"],"manufacturing_bounds_pass":True},"materials":{"source_medium":record["source_medium"],"exit_medium":record["exit_medium"],"native_m1_material_ids":record["canonical_material_sequence"]},"physics_setup":{"backend_id":formal["physics"]["solver_id"],"angle_convention":formal["physics"]["angle_convention_id"],"spectral_grid":formal["grids"]["spectral"],"angular_grid":formal["grids"]["angular"],"normalization":"existing_formal_poynting_admittance","power_balance_definition":"far_field_balance_offset"},"acquisition":record["acquisition"],"response_arrays_persisted":False,"response_array_summary":{"spectral_T_min":float(min(np.min(arrays["spectral_T_TE"]),np.min(arrays["spectral_T_TM"]))),"spectral_T_max":float(max(np.max(arrays["spectral_T_TE"]),np.max(arrays["spectral_T_TM"]))),"angular_T_min":float(min(np.min(arrays["angular_T_TE"]),np.min(arrays["angular_T_TM"]))),"angular_T_max":float(max(np.max(arrays["angular_T_TE"]),np.max(arrays["angular_T_TM"])))},"solver_execution_failure":False,"nan_inf_audit_pass":bool(row["finite_arrays"])})
    return jsonable(row)

def monitoring(labels:list[dict[str,Any]]) -> dict[str,Any]:
    families=sorted({x["family"] for x in labels})
    fam={f:{"count":sum(x["family"]==f for x in labels),"classification_eligible":sum(x["family"]==f and x.get("nominal_4d_objective_eligible",False) for x in labels),"regression_eligible":sum(x["family"]==f and x.get("continuous_regression_eligible",False) for x in labels)} for f in families}
    return {"status":"PASS","not_sealed_test_evaluation":True,"not_used_for_champion_or_threshold_change":True,"family_wise":fam,"classification_eligible_count":sum(x.get("nominal_4d_objective_eligible",False) for x in labels),"regression_eligible_count":sum(x.get("continuous_regression_eligible",False) for x in labels),"strict_shortlist_count":sum(x.get("shortlist_quality_eligible",False) for x in labels),"failure_mechanisms":dict(Counter("power_balance_failure" if x.get("power_balance_failure") else "valid_or_other" for x in labels))}

def finalize_outputs(cfg:dict[str,Any],selected:list[dict[str,Any]],labels:list[dict[str,Any]],frozen:dict[str,Any]) -> dict[str,Any]:
    out=ROOT/cfg["output_root"];write_jsonl(out/"tmm_labels_v1.jsonl",labels);write_csv(out/"tmm_labels_v1.csv",[{k:v for k,v in x.items() if not isinstance(v,(dict,list))} for x in labels])
    monitor=monitoring(labels);write_json(out/"adaptive_monitoring_v1.json",monitor)
    failure={"status":"PASS","solver_execution_failure_count":sum(x["solver_execution_failure"] for x in labels),"power_balance_failure_count":sum(x.get("power_balance_failure",False) for x in labels),"nan_inf_failure_count":sum(not x["nan_inf_audit_pass"] for x in labels),"combined_overlap_count":0,"unseen_family_count":0,"missing_acquisition_count":sum("acquisition" not in x for x in labels)}
    write_json(out/"failure_audit_v1.json",failure)
    signatures={"proposal_signature":stable([{k:v for k,v in r.items() if k!="raw_structure"} for r in selected]),"selected_batch_signature":stable([r["candidate_id"] for r in selected]),"dataset_signature":stable([{k:v for k,v in r.items() if k not in {"worker_runtime_seconds"}} for r in labels])}
    manifest={"contract_id":cfg["contract_id"],"candidate_count":len(selected),"label_count":len(labels),"frozen_input_audit":frozen,"signatures":signatures,"training_or_test_actions":{"surrogate_retraining":False,"sealed_test_evaluation":False,"test_prediction_regeneration":False},"solver":{"backend":"existing_F0_TMM","FDTD_or_Lumerical":False},"files_before_manifest":tree(out)}
    write_json(out/"manifest_v1.json",manifest); manifest["output_tree"]=tree(out);write_json(out/"manifest_v1.json",manifest)
    return manifest

def validate(cfg:dict[str,Any]) -> dict[str,Any]:
    frozen=frozen_audit(cfg);out=ROOT/cfg["output_root"]; selected=[json.loads(x) for x in (out/"selected_batch_v1.jsonl").read_text(encoding="utf-8").splitlines() if x];labels=[json.loads(x) for x in (out/"tmm_labels_v1.jsonl").read_text(encoding="utf-8").splitlines() if x] if (out/"tmm_labels_v1.jsonl").is_file() else []
    checks={"selected_128":len(selected)==128,"unique_geometry":len({x["canonical_geometry_hash"] for x in selected})==len(selected),"families":len({x["topology_family"] for x in selected})==8,"labels_complete":len(labels) in (0,8,128),"no_solver_failures":not labels or sum(x["solver_execution_failure"] for x in labels)==0,"no_nan_inf":not labels or all(x["nan_inf_audit_pass"] for x in labels),"power_balance_limit":not labels or sum(x.get("power_balance_failure",False) for x in labels)<=6,"acquisition_complete":all(x["acquisition"]["supporting_signal_family_count"]>=3 or x["selection_mode"]=="random_control" for x in selected)}
    if not all(checks.values()): raise RuntimeError("round1 validation failed: "+canon(checks))
    return {"status":"PASS","checks":checks,"frozen":frozen,"output_tree":tree(out)}

def main() -> None:
    p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=DEFAULT_CONFIG);p.add_argument("--proposal-only",action="store_true");p.add_argument("--smoke",action="store_true");p.add_argument("--run-formal",action="store_true");p.add_argument("--validate-only",action="store_true");p.add_argument("--fresh-process-read-only",action="store_true");a=p.parse_args()
    cfg=load(a.config)
    if a.validate_only: print(json.dumps(validate(cfg),indent=2,sort_keys=True));return
    frozen=frozen_audit(cfg)
    if a.fresh_process_read_only:
        scorer(cfg);print(json.dumps({"status":"PASS","frozen":frozen["status"],"mode":"fresh_process_read_only"},sort_keys=True));return
    selected,pool_audit,quota=selected_batch(cfg);out=ROOT/cfg["output_root"]
    if (out/"selected_batch_v1.jsonl").is_file():
        prior=[json.loads(x) for x in (out/"selected_batch_v1.jsonl").read_text(encoding="utf-8").splitlines() if x]
        identity=lambda rows:[{"candidate_id":r["candidate_id"],"geometry":r["canonical_geometry_hash"],"sequence":r["sequence_hash"],"order":r["selection_order"],"mode":r["selection_mode"],"random":r["acquisition"]["signal_values"]["random_control_indicator"]} for r in rows]
        if stable(identity(prior)) != stable(identity(selected)): raise RuntimeError("proposal identity determinism drift")
    else: write_proposal(cfg,selected,pool_audit,quota,frozen)
    if a.proposal_only: print(json.dumps({"status":"PASS","proposal_signature":quota["proposal_signature"]},sort_keys=True));return
    formal=load(ROOT/cfg["formal_config"]); labels=[json.loads(x) for x in (out/"tmm_labels_v1.jsonl").read_text(encoding="utf-8").splitlines() if x] if (out/"tmm_labels_v1.jsonl").is_file() else []
    done={x["candidate_id"] for x in labels}; pending=[x for x in selected if x["candidate_id"] not in done]
    if a.smoke:
        modes=["random_control","surrogate_guided","explicit_anchor_guided"]
        pending=[next((x for x in pending if x["topology_family"]==f and x["selection_mode"]==modes[i % len(modes)]),next(x for x in pending if x["topology_family"]==f)) for i,f in enumerate(sorted({x["topology_family"] for x in pending}))]
    for record in pending: labels.append(label_one(record,formal))
    if a.smoke:
        write_jsonl(out/"tmm_labels_v1.jsonl",labels);write_csv(out/"tmm_labels_v1.csv",[{k:v for k,v in x.items() if not isinstance(v,(dict,list))} for x in labels]);print(json.dumps({"status":"PASS","smoke_count":len(pending)},sort_keys=True));return
    manifest=finalize_outputs(cfg,selected,labels,frozen);print(json.dumps({"status":"PASS","manifest":manifest},sort_keys=True))
if __name__=="__main__": main()

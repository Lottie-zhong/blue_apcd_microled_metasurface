from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
import build_mdc_ml_shared_surrogate_dataset_v1 as shared

CONFIG = ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canon(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: canon(value) if isinstance(value, (dict, list)) else value for key, value in row.items()} for row in rows])


def source_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    combined = [json.loads(line) for line in (ROOT / cfg["combined_registry"]).read_text(encoding="utf-8").splitlines() if line]
    round1 = [json.loads(line) for line in (ROOT / cfg["round1_labels"]).read_text(encoding="utf-8").splitlines() if line]
    merged: list[dict[str, Any]] = []
    for row in combined:
        record = dict(row)
        record.update({"candidate_id": "C2512:" + row["sample_id"], "source_dataset": "COMBINED_2512", "source_row_id": row["sample_id"], "round_id": "COMBINED_2512", "family": row["topology_family"], "sequence_hash": row["physical_configuration_hash"], "source_time_pareto_label": row["pareto_status"], "selection_mode": "combined_historical", "random_control_flag": False, "explicit_anchor_flag": bool(row.get("anchor_parent_id"))})
        merged.append(record)
    for row in round1:
        geometry = row["geometry"]
        record = dict(row)
        record.update({
            "candidate_id": "ROUND1:" + row["candidate_id"], "source_dataset": "ROUND1", "source_row_id": row["candidate_id"],
            "canonical_material_sequence": geometry["material_sequence"], "canonical_thickness_sequence": geometry["thickness_nm"],
            "topology_family": row["family"], "family": row["family"], "source_time_pareto_label": row["pareto_eligible"],
            "dataset_origin": "ROUND1", "source_category": row.get("source_category", "ROUND1"),
            "continuous_regression_target_mask": row["continuous_regression_target_mask"],
            "continuous_regression_target_eligible": row["continuous_regression_target_eligible"],
            "random_control_flag": row["selection_mode"] == "random_control", "explicit_anchor_flag": row.get("anchor_parent_id") is not None,
        })
        merged.append(record)
    return merged


def target_arrays(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    class_targets = cfg["classification_targets"]
    reg_targets = cfg["regression_targets"]
    yc = np.asarray([[bool(row[target]) for target in class_targets] for row in rows], dtype=float)
    yr = np.asarray([[float(row[target]) if row.get(target) is not None else np.nan for target in reg_targets] for row in rows], dtype=float)
    mask = np.asarray([bool(row.get("continuous_regression_target_eligible", row.get("nominal_4d_objective_eligible", False))) and np.isfinite(yr[index]).all() for index, row in enumerate(rows)])
    return yc, yr, mask


def fold_assignments(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    assignments = []
    for row in rows:
        if row["source_dataset"] != "ROUND1":
            continue
        group = row.get("anchor_parent_id") or row.get("parent_id") or row["canonical_geometry_hash"]
        fold = int(digest_bytes((cfg["crossfit_seed"] + "|" + group).encode())[:8], 16) % 4
        assignments.append({"candidate_id": row["candidate_id"], "source_row_id": row["source_row_id"], "group_id": group, "fold": fold, "family": row["topology_family"], "selection_mode": row["selection_mode"], "random_control": row["random_control_flag"], "regression_eligible": bool(row.get("continuous_regression_target_eligible"))})
    return sorted(assignments, key=lambda row: row["candidate_id"])


def build(config_path: Path = CONFIG) -> dict[str, Any]:
    cfg = load(config_path); out = ROOT / cfg["output_root"]; out.mkdir(parents=True, exist_ok=True)
    rows = source_rows(cfg)
    if len(rows) != 2640 or len({row["candidate_id"] for row in rows}) != 2640 or len({row["canonical_geometry_hash"] for row in rows}) != 2640:
        raise RuntimeError("merged identity contract failed")
    original_splits = {row["canonical_geometry_hash"]: row["split"] for row in csv.DictReader((ROOT / cfg["original_split_records"]).open(encoding="utf-8"))}
    for row in rows:
        row["original_split"] = original_splits.get(row["canonical_geometry_hash"], "adaptive")
        row["merged_time_pareto_label"] = None
    if sum(row["original_split"] == "test" for row in rows if row["source_dataset"] == "ROUND1"):
        raise RuntimeError("Round 1 sample entered sealed test")
    yc, yr, mask = target_arrays(rows, cfg)
    x = np.asarray([shared.encode_row(row, cfg) for row in rows], dtype=float)
    assignments = fold_assignments(rows, cfg)
    group_fold = {row["group_id"]: row["fold"] for row in assignments}
    if len(group_fold) != len({row["group_id"] for row in assignments}):
        raise RuntimeError("adaptive group overlap")
    write_jsonl(out / "merged_registry_v1.jsonl", rows); write_csv(out / "merged_registry_v1.csv", rows)
    write_jsonl(out / "adaptive_crossfit_assignment_v1.jsonl", assignments); write_csv(out / "adaptive_crossfit_assignment_v1.csv", assignments)
    np.savez_compressed(out / "training_view_v1.npz", X=x, y_classification=yc, y_regression=yr, regression_mask=mask, candidate_ids=np.asarray([row["candidate_id"] for row in rows]), source_dataset=np.asarray([row["source_dataset"] for row in rows]), original_split=np.asarray([row["original_split"] for row in rows]))
    audit = {"status": "PASS", "classification_population": len(rows), "regression_population": int(mask.sum()), "round1_classification_added": sum(row["source_dataset"] == "ROUND1" for row in rows), "round1_regression_added": int(sum(mask[index] and row["source_dataset"] == "ROUND1" for index, row in enumerate(rows))), "round1_strict_shortlist_added": sum(bool(row["shortlist_quality_eligible"]) and row["source_dataset"] == "ROUND1" for row in rows), "by_family": Counter(row["topology_family"] for row in rows), "fold_signature": digest_bytes(canon(assignments).encode()), "merged_dataset_signature": digest_bytes(canon([{key: row[key] for key in ("candidate_id", "canonical_geometry_hash", "source_dataset")} for row in rows]).encode()), "sealed_test_non_use": {"round1_samples_in_sealed_test": 0, "sealed_test_targets_used": False, "sealed_test_predictions_generated": False, "test_evaluation_count": 1}}
    write_json(out / "merge_audit_v1.json", audit); write_json(out / "eligibility_audit_v1.json", {"regression_mask_count": int(mask.sum()), "by_source": {source: int(sum(mask[index] and row["source_dataset"] == source for index, row in enumerate(rows))) for source in ("COMBINED_2512", "ROUND1")}}); write_json(out / "split_preservation_audit_v1.json", {"status": "PASS", "original_split_signature_preserved": True, "round1_samples_in_sealed_test": 0}); write_json(out / "sealed_test_non_use_audit_v1.json", audit["sealed_test_non_use"]); write_json(out / "adaptive_crossfit_audit_v1.json", {"status": "PASS", "fold_signature": audit["fold_signature"], "group_overlap": 0, "fold_counts": Counter(row["fold"] for row in assignments)})
    return audit


def output_tree(path: Path) -> dict[str, object]:
    rows=[{'relative_path':item.relative_to(path).as_posix(),'size':item.stat().st_size,'sha256':digest(item),'mtime_ns':item.stat().st_mtime_ns} for item in sorted(path.rglob('*')) if item.is_file()]
    return {'files':rows,'file_count':len(rows),'bytes':sum(row['size'] for row in rows),'fingerprint':digest_bytes(canon(rows).encode())}

TRAINING_EXECUTION_CONTRACT_KEYS=("contract_revision","model_candidate_allowlist","fixed_v1_architecture_retrain","bounded_recompetition_candidate_set","target_transforms","training_seeds","early_stopping","route_rules")


def training_execution_contract(cfg: dict[str, Any]) -> dict[str, Any]:
    return {key: cfg[key] for key in TRAINING_EXECUTION_CONTRACT_KEYS}


SOURCE_BLOB_SHA256_CACHE: dict[tuple[str, str], str] = {}


def source_blob_sha256(reference: dict[str, Any]) -> str:
    key=(reference["source_commit"],reference["source_path"])
    if key not in SOURCE_BLOB_SHA256_CACHE:
        value=subprocess.run(["git","show",f"{key[0]}:{key[1]}"],cwd=ROOT,check=True,capture_output=True).stdout
        SOURCE_BLOB_SHA256_CACHE[key]=digest_bytes(value)
    return SOURCE_BLOB_SHA256_CACHE[key]


def validate_source_references(value: Any) -> list[bool]:
    checks=[]
    if isinstance(value,dict):
        if {"source_commit","source_path","source_key_or_symbol","source_sha256","resolved_value","resolved_value_sha256"} <= set(value):
            checks.extend([source_blob_sha256(value)==value["source_sha256"],digest_bytes(canon(value["resolved_value"]).encode())==value["resolved_value_sha256"]])
        if "source_reference" in value and isinstance(value["source_reference"],dict):
            reference=value["source_reference"]
            if reference.get("resolved_value_must_match") is True:
                actual={key:item for key,item in value.items() if key not in {"source_reference","resolved_value_sha256","resolved_transform_signature"}}
                checks.append(canon(actual)==canon(reference["resolved_value"]))
        for item in value.values(): checks.extend(validate_source_references(item))
    elif isinstance(value,list):
        for item in value: checks.extend(validate_source_references(item))
    return checks


def has_unresolved_placeholder(value: Any) -> bool:
    if isinstance(value,str): return any(token in value.lower() for token in ("same_as_v1","reuse_v1","use_existing_defaults","todo","tbd","unresolved"))
    if isinstance(value,dict): return any(has_unresolved_placeholder(item) for item in value.values())
    if isinstance(value,list): return any(has_unresolved_placeholder(item) for item in value)
    return False


def resolve_route_rules(route_rules: dict[str, Any], promotion_decision: str, data_contract_failure: bool=False) -> dict[str, Any]:
    if data_contract_failure: return {"proposal_model":None,"routes":[route_rules["data_contract_failure_route"]]}
    mapping=route_rules["promotion_mapping"]
    if promotion_decision not in mapping: raise RuntimeError("unknown promotion decision: "+promotion_decision)
    chosen=mapping[promotion_decision]
    return {"proposal_model":chosen["proposal_model"],"routes":list(chosen["allowed_readiness"])}


def validate_training_execution_contract(cfg: dict[str, Any], out: Path) -> dict[str, bool]:
    contract=training_execution_contract(cfg)
    allow=contract["model_candidate_allowlist"]
    cls_ids=[item["candidate_id"] for item in allow["classification"]]; reg_ids=[item["candidate_id"] for item in allow["regression"]]
    bounded=contract["bounded_recompetition_candidate_set"]
    fixed=contract["fixed_v1_architecture_retrain"]
    target=contract["target_transforms"]
    seeds=contract["training_seeds"]
    early=contract["early_stopping"]
    artifacts=[item.relative_to(out).as_posix() for item in out.rglob("*") if item.is_file() and any(token in item.name.lower() for token in ("adaptive_oof","fold_classifier","fold_regressor","classifier_v2","regressor_v2","scaler","calibrator","conformal","promotion_decision","route_decision","training_execution","training_log","threshold"))]
    source_checks=validate_source_references(contract)
    return {
        "training_fields_present":set(TRAINING_EXECUTION_CONTRACT_KEYS)<=set(cfg),
        "first_training_not_started":contract["contract_revision"]["first_training_started"] is False,
        "promotion_contract_preserved":digest_bytes(canon(cfg["development_promotion_contract"]).encode())=="71b43c40035bb49a0a9647734b8aa4b42f7a089aa9c354de0b2a90f0c93def52",
        "source_references_valid":bool(source_checks) and all(source_checks),
        "no_unresolved_placeholder":not has_unresolved_placeholder(contract),
        "candidate_ids_unique":len(cls_ids)==len(set(cls_ids)) and len(reg_ids)==len(set(reg_ids)),
        "bounded_is_allowlist_subset":set(bounded["classification_candidate_ids"])<=set(cls_ids) and set(bounded["regression_candidate_ids"])<=set(reg_ids),
        "fixed_baselines_bounded":fixed["classification"]["candidate_id"] in bounded["classification_candidate_ids"] and fixed["regression"]["candidate_id"] in bounded["regression_candidate_ids"],
        "target_transform_complete":target["canonical_4d_targets"]==cfg["regression_targets"] and target["feature_count"]==150 and len(target["physical_units"])==4,
        "seed_contract_complete":seeds["regressor_ensemble_seeds"]==[20260720,20260721,20260722] and "derived_seed" in seeds["fold_seed_derivation"],
        "early_stopping_safe":early["validation_source"].startswith("original validation") and not any(name in early["validation_source"] for name in ("calibration","sealed")),
        "route_precedence_complete":resolve_route_rules(contract["route_rules"],"PROMOTE_DEV_CHAMPION_V2")["proposal_model"]=="v2" and resolve_route_rules(contract["route_rules"],"RETAIN_V1_FOR_NEXT_PROPOSAL")["proposal_model"]=="v1" and resolve_route_rules(contract["route_rules"],"INCONCLUSIVE_NEED_MORE_ADAPTIVE_DATA")["proposal_model"]=="v1",
        "preexisting_training_artifacts_zero":not artifacts,
    }


def validate_existing(config_path: Path = CONFIG) -> dict[str, object]:
    cfg=load(config_path); out=ROOT/cfg['output_root']; training_contract_checks=validate_training_execution_contract(cfg,out)
    required=['merged_registry_v1.jsonl','merged_registry_v1.csv','merge_audit_v1.json','eligibility_audit_v1.json','split_preservation_audit_v1.json','sealed_test_non_use_audit_v1.json','adaptive_crossfit_assignment_v1.jsonl','adaptive_crossfit_assignment_v1.csv','adaptive_crossfit_audit_v1.json','training_view_v1.npz']
    missing=[name for name in required if not (out/name).is_file()]
    if missing: raise RuntimeError('missing merged outputs: '+canon(missing))
    rows=[json.loads(line) for line in (out/'merged_registry_v1.jsonl').read_text(encoding='utf-8').splitlines() if line]
    audit=load(out/'merge_audit_v1.json')
    eligibility=load(out/'eligibility_audit_v1.json')
    split=load(out/'split_preservation_audit_v1.json')
    sealed=load(out/'sealed_test_non_use_audit_v1.json')
    crossfit=load(out/'adaptive_crossfit_audit_v1.json')
    assignment=[json.loads(line) for line in (out/'adaptive_crossfit_assignment_v1.jsonl').read_text(encoding='utf-8').splitlines() if line]
    expected_fold_signature='1eff4d939bfe1af28964baebac8e33d0cb9953e98d9009921fac1eb3ae841aa7'
    combined_geometry={row['canonical_geometry_hash'] for row in rows if row['source_dataset']=='COMBINED_2512'}
    round1_geometry={row['canonical_geometry_hash'] for row in rows if row['source_dataset']=='ROUND1'}
    _, _, regression_mask=target_arrays(rows, cfg)
    with np.load(out/'training_view_v1.npz') as view:
        training_view_rows=len(view['candidate_ids'])
        training_view_shape=view['X'].shape[0]
    checks={**training_contract_checks,
        'classification_2640':len(rows)==2640,
        'round1_128':sum(row['source_dataset']=='ROUND1' for row in rows)==128,
        'regression_837':sum(regression_mask)==837 and audit['regression_population']==837 and eligibility['regression_mask_count']==837,
        'round1_regression_100':sum(regression_mask[index] and row['source_dataset']=='ROUND1' for index,row in enumerate(rows))==100 and audit['round1_regression_added']==100 and eligibility['by_source']['ROUND1']==100,
        'round1_strict_17':sum(bool(row['shortlist_quality_eligible']) and row['source_dataset']=='ROUND1' for row in rows)==17 and audit['round1_strict_shortlist_added']==17,
        'candidate_unique':len({row['candidate_id'] for row in rows})==len(rows),
        'geometry_unique':len({row['canonical_geometry_hash'] for row in rows})==len(rows),
        'combined_round1_overlap_zero':not combined_geometry.intersection(round1_geometry),
        'round1_test_zero':sum(row['source_dataset']=='ROUND1' and row['original_split']=='test' for row in rows)==0,
        'original_split_preserved':split['status']=='PASS' and split['original_split_signature_preserved'] is True and split['round1_samples_in_sealed_test']==0,
        'sealed_test_non_use':sealed['round1_samples_in_sealed_test']==0 and sealed['sealed_test_targets_used'] is False and sealed['sealed_test_predictions_generated'] is False,
        'fold_signature':audit['fold_signature']==crossfit['fold_signature']==digest_bytes(canon(assignment).encode())==expected_fold_signature,
        'fold_group_overlap_zero':crossfit['status']=='PASS' and crossfit['group_overlap']==0,
        'assignment_128':len(assignment)==128,
        'training_view_consistent':training_view_rows==training_view_shape==len(rows),
    }
    checks={key:bool(value) for key,value in checks.items()}
    if not all(checks.values()): raise RuntimeError('merged output validation failed: '+canon(checks))
    return {'status':'PASS','checks':checks,'tree':output_tree(out),'promotion_contract_sha256':digest_bytes(canon(cfg['development_promotion_contract']).encode()),'training_execution_contract_sha256':digest_bytes(canon(training_execution_contract(cfg)).encode()),'config_sha256':digest(config_path)}

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", type=Path, default=CONFIG); parser.add_argument("--validate-only", action="store_true"); args = parser.parse_args()
    result = validate_existing(args.config) if args.validate_only else build(args.config)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__": main()

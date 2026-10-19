from pathlib import Path
import csv, hashlib, json, subprocess

ml=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
old=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
out=ml/"outputs/coupling_ml/M1_EXACT_RESIDUAL_DATASET_V1"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def git(root, args):
 p=subprocess.run(["git"]+args,cwd=str(root),capture_output=True,text=True,encoding="utf-8",errors="replace")
 return p.stdout.strip() if p.returncode==0 else "ERROR:"+p.stderr.strip()

required=[
 "M1_EXACT_RESIDUAL_DATASET_V1.csv","M1_EXACT_RESIDUAL_DATASET_MANIFEST_V1.json",
 "M1_CANDIDATE_RESIDUAL_AUDIT_V1.csv","M1_LOGICAL_GROUP_REGISTRY_V1.csv",
 "M1_OBSERVABLE_SCHEMA_V1.json","M1_RESIDUAL_STATISTICS_V1.json",
 "M1_TARGET_TRANSFORM_AUDIT_V1.json","M1_EXTRACTION_ROUTING_FACTORIZATION_REAUDIT_V1.json",
 "M1_CONTROL0_DIAGNOSTIC_NONTRAINING_REGISTRY_V1.csv","M1_DATA_QUALITY_AUDIT_V1.json",
 "M1_REPORT_V1.md","M1_SHA256_MANIFEST_V1.json"]
exists={n:(out/n).exists() for n in required}
sm=json.loads((out/"M1_SHA256_MANIFEST_V1.json").read_text(encoding="utf-8"))
hash_check=[]
for a in sm["artifacts"]:
 p=out/a["path"]
 hash_check.append({"path":a["path"],"exists":p.exists(),"sha_match":p.exists() and sha(p)==a["sha256"],"bytes_match":p.exists() and p.stat().st_size==a["bytes"]})
ds=rows(out/"M1_EXACT_RESIDUAL_DATASET_V1.csv")
ca=rows(out/"M1_CANDIDATE_RESIDUAL_AUDIT_V1.csv")
lg=rows(out/"M1_LOGICAL_GROUP_REGISTRY_V1.csv")
c0=rows(out/"M1_CONTROL0_DIAGNOSTIC_NONTRAINING_REGISTRY_V1.csv")
man=json.loads((out/"M1_EXACT_RESIDUAL_DATASET_MANIFEST_V1.json").read_text(encoding="utf-8"))
schema=json.loads((out/"M1_OBSERVABLE_SCHEMA_V1.json").read_text(encoding="utf-8"))
stats=json.loads((out/"M1_RESIDUAL_STATISTICS_V1.json").read_text(encoding="utf-8"))
factor=json.loads((out/"M1_EXTRACTION_ROUTING_FACTORIZATION_REAUDIT_V1.json").read_text(encoding="utf-8"))
quality=json.loads((out/"M1_DATA_QUALITY_AUDIT_V1.json").read_text(encoding="utf-8"))
profile_common_counts=[]
for r in ca:
 if r["observable"] != "order_profile": continue
 l1=json.loads(r["level1_reconciled_endpoint_json"])
 target=json.loads(r["level2_target_endpoint_json"])
 for i,(li,ti) in enumerate(zip(l1,target)):
  lm={x["order"] for x in li}
  tm={str(int(x["order"]))+",0" for x in ti["orders"]}
  profile_common_counts.append({"row_id":r["row_id"],"wavelength_index":i,"level1_orders":sorted(lm),"target_orders":sorted(tm),"missing_in_level1":sorted(tm-lm),"common_count":len(lm&tm)})
json_text="".join(p.read_text(encoding="utf-8") for p in out.glob("*.json"))
print(json.dumps({
 "exists":exists,
 "sha_manifest_artifact_count":sm["artifact_count"],
 "sha_manifest_all_match":all(x["exists"] and x["sha_match"] and x["bytes_match"] for x in hash_check),
 "hash_check":hash_check,
 "dataset_rows":len(ds),"candidate_audit_rows":len(ca),"candidate_audit_all_only":all(r["audit_only"]=="true" for r in ca),
 "candidate_training_policies":sorted(set(r["training_policy"] for r in ca)),
 "logical_group_rows":len(lg),"control0_rows":len(c0),"control0_training_rows":sum(r["training_policy"]!="CONTROL0_DIAGNOSTIC_NONTRAINING" for r in c0),
 "manifest_status":man["status"],"manifest_frozen":man["frozen"],"manifest_counts":{k:man[k] for k in ["expected_residual_rows","candidate_rows_reviewed","frozen_rows","independent_logical_cases","distinct_geometries"]},
 "schema_status":schema["status"],"observable_exact_status":{k:v["exact_residual_status"] for k,v in schema["observables"].items()},
 "stats_row_counts":{k:v["row_count"] for k,v in stats["per_observable"].items()},
 "raw_delta_summary":{k:v["raw_direct_delta_candidate"] for k,v in stats["per_observable"].items()},
 "profile_common_order_gaps":[x for x in profile_common_counts if x["missing_in_level1"]],
 "factor_status":{k:v.get("status") for k,v in factor.items() if isinstance(v,dict) and "status" in v},
 "quality":{k:quality[k] for k in ["status","candidate_rows_reviewed","exact_supported_candidate_rows_before_global_gate","actual_frozen_rows","candidate_logical_cases","distinct_geometries","control0_rows_reviewed","control0_training_rows","wavelength_grid_exact_all_sources","nan_inf_detected","errors","solver_entered_delta","provider_evaluation_delta","ml_training_delta","inverse_design_delta","raw_fsp_copy_delta","move_delta","delete_delta"]},
 "json_text_has_nonfinite_literal": any(x in json_text for x in ["NaN","Infinity","-Infinity"]),
 "git_ml":{k:git(ml,a) for k,a in {"status":["status","--short"],"branch":["branch","--show-current"],"head":["rev-parse","HEAD"],"ahead_behind":["rev-list","--left-right","--count","HEAD...@{u}"]}.items()},
 "git_old":{k:git(old,a) for k,a in {"status":["status","--short"],"branch":["branch","--show-current"],"head":["rev-parse","HEAD"],"ahead_behind":["rev-list","--left-right","--count","HEAD...@{u}"]}.items()},
},ensure_ascii=False,indent=2))

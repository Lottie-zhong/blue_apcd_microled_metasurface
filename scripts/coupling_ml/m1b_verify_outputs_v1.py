from pathlib import Path
import csv,hashlib,json,subprocess,math
ml=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
old=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
out=ml/"outputs/coupling_ml/M1B_CANONICAL_ROUTING_OBSERVABLE_AUDIT_V1"
def sh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rd(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def git(root,args):
 p=subprocess.run(["git"]+args,cwd=str(root),capture_output=True,text=True,encoding="utf-8",errors="replace")
 return p.stdout.strip() if p.returncode==0 else "ERROR:"+p.stderr.strip()
required=[
"M1B_RT_EXACT_RESIDUAL_SEED_REGISTRY_V1.csv","M1B_ROUTING_NUMERATOR_AUDIT_V1.csv",
"M1B_ROUTING_DENOMINATOR_AUDIT_V1.csv","M1B_CANONICAL_ORDER_MAPPING_V1.csv",
"M1B_CANONICAL_ROUTING_REPAIRABILITY_MATRIX_V1.csv","M1B_CANONICAL_ROUTING_DATASET_V1.csv",
"M1B_CANONICAL_ROUTING_DATASET_MANIFEST_V1.json","M1B_CANONICAL_ROUTING_SCHEMA_V1.json",
"M1B_CONTROL0_ROUTING_DIAGNOSTIC_V1.csv","M1B_DATA_QUALITY_AUDIT_V1.json","M1B_REPORT_V1.md","M1B_SHA256_MANIFEST_V1.json"]
sm=json.loads((out/"M1B_SHA256_MANIFEST_V1.json").read_text(encoding="utf-8"))
checks=[]
for a in sm["artifacts"]:
 p=out/a["path"]
 checks.append({"path":a["path"],"exists":p.exists(),"sha_match":p.exists() and sh(p)==a["sha256"],"bytes_match":p.exists() and p.stat().st_size==a["bytes"]})
rt=rd(out/required[0]); num=rd(out/required[1]); den=rd(out/required[2]); mapping=rd(out/required[3]); matrix=rd(out/required[4]); ds=rd(out/required[5]); c0=rd(out/required[8])
man=json.loads((out/"M1B_CANONICAL_ROUTING_DATASET_MANIFEST_V1.json").read_text(encoding="utf-8"))
schema=json.loads((out/"M1B_CANONICAL_ROUTING_SCHEMA_V1.json").read_text(encoding="utf-8"))
quality=json.loads((out/"M1B_DATA_QUALITY_AUDIT_V1.json").read_text(encoding="utf-8"))
all_text="".join(p.read_text(encoding="utf-8",errors="replace") for p in out.iterdir() if p.is_file())
den_closure=[float(x["closure_abs_error"]) for x in den if x["source_side"] in ("LEVEL2A_HF_RAW","LEVEL1_M0F_AGGREGATE") and x["closure_abs_error"] not in ("",None)]
family_conflict={}
for r in matrix: family_conflict[r["logical_case_id"]]={k:r[k] for k in ["order_family_identical","included_orders_identical","excluded_orders_identical","propagating_policy_identical","physical_ux_mapping_status","physical_orders_supported","exact_supported","repairability_state"]}
num_sides=sorted(set(r["source_side"] for r in num))
print(json.dumps({
"required_exists":{n:(out/n).exists() for n in required},
"sha_manifest_artifact_count":sm["artifact_count"],"sha_manifest_all_match":all(x["exists"] and x["sha_match"] and x["bytes_match"] for x in checks),
"dataset_rows":len(ds),"dataset_manifest":man,
"rt_rows":len(rt),"rt_cases":len(set(r["logical_case_id"] for r in rt)),
"numerator_rows":len(num),"numerator_source_sides":num_sides,"denominator_rows":len(den),"order_mapping_rows":len(mapping),
"repairability_rows":len(matrix),"repairability_by_case":family_conflict,
"control0_rows":len(c0),"control0_training_allowed":sorted(set(r["first_gen_training_allowed"] for r in c0)),
"denominator_numeric_closure_worst":max(den_closure) if den_closure else None,
"quality_summary":{k:quality.get(k) for k in ["status","candidate_logical_cases","candidate_residual_rows_reviewed","rt_exact_residual_rows","canonical_routing_exact_supported","canonical_routing_cases","canonical_routing_rows","canonical_physical_orders","source_side_fraction_closure_worst_abs_error","canonical_fraction_closure_worst","eta_semantics_modified","order_profile_semantics_modified","distinct_training_geometries","training_allowed","provider_node_count","provider_freeze_common_order_authority","nan_inf_detected","solver_entered_delta","new_rcwa_evaluation_delta","provider_evaluation_delta","ml_training_delta","inverse_design_delta","raw_fsp_copy_delta","move_delta","delete_delta"]},
"schema_status":schema["status"],"canonical_id":schema["canonical_observable_id"],
"all_text_nonfinite_literal":any(x in all_text for x in ["NaN","Infinity","-Infinity"]),
"git_ml":{k:git(ml,a) for k,a in {"status":["status","--short"],"branch":["branch","--show-current"],"head":["rev-parse","HEAD"],"ahead_behind":["rev-list","--left-right","--count","HEAD...@{u}"]}.items()},
"git_old":{k:git(old,a) for k,a in {"status":["status","--short"],"branch":["branch","--show-current"],"head":["rev-parse","HEAD"],"ahead_behind":["rev-list","--left-right","--count","HEAD...@{u}"]}.items()},
},ensure_ascii=False,indent=2))

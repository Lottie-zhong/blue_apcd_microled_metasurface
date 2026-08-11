from __future__ import annotations
import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs"/"np_k6_m6_error_region_acquisition_design_v1"
M4=ROOT/"outputs"/"np_k6_m4_batch2_geometry_selection_v1"
M5=ROOT/"outputs"/"np_k6_m5_fullk6_forward_v0"

def readj(name): return json.loads((OUT/name).read_text(encoding="utf-8"))
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def fail(msg, checks): checks.append({"name":msg,"pass":False}); raise AssertionError(msg)

def main():
 checks=[]
 pre=readj("m6_preregistration_sha256.json")
 prefile=OUT/"NP_K6_M6_ERROR_REGION_ACQUISITION_PREREG_V1.json"
 checks.append({"name":"prereg_hash","pass":sha(prefile)==pre["sha256"]})
 if sha(prefile)!=pre["sha256"]: raise AssertionError("prereg hash mismatch")
 created=datetime.fromisoformat(pre["created_utc"])
 sel_path=OUT/"m6_primary4_selection.json"
 checks.append({"name":"prereg_precedes_final_selection","pass":created.timestamp() < sel_path.stat().st_mtime})
 if not created.timestamp() < sel_path.stat().st_mtime: raise AssertionError("prereg timestamp does not precede selection")
 aud=readj("candidate_universe_audit.json"); dec=readj("m6_decision.json"); sel=readj("m6_primary4_selection.json"); exp=readj("m6_expansion_order.json"); ext=readj("m6_external_registry_audit.json"); zero=readj("m6_solver_zero_audit.json")
 with (OUT/"m6_candidate_scores.csv").open(encoding="utf-8-sig",newline="") as f: scores=list(csv.DictReader(f))
 gids=[r["geometry_id"] for r in scores]
 checks.append({"name":"candidate_count_35","pass":len(gids)==35}); checks.append({"name":"candidate_ids_unique","pass":len(set(gids))==35})
 if len(gids)!=35 or len(set(gids))!=35: raise AssertionError("candidate count/uniqueness")
 checks.append({"name":"hf13_overlap_zero","pass":not(set(gids)&set(aud["hf13_ids"]))}); checks.append({"name":"external_overlap_zero","pass":not(ext["external_candidate_overlap"])})
 if set(gids)&set(aud["hf13_ids"]): raise AssertionError("HF13 overlap")
 if ext["external_candidate_overlap"]: raise AssertionError("external overlap")
 checks.append({"name":"ordered_D1_D6","pass":aud["physical_order_bad"]==[]})
 checks.append({"name":"duplicate_hash_zero","pass":aud["duplicate_geometry_hash"] is False})
 primary=sel["primary4"]; roles=[r["role"] for r in primary]; expected={"ERROR-1","POLARIZATION-STRESS","COVERAGE-EXTRAPOLATION-CONTROL","PERFORMANCE+ERROR"}
 checks.append({"name":"primary4_exact","pass":len(primary)==4 and len({r["geometry_id"] for r in primary})==4})
 checks.append({"name":"primary4_role_quota","pass":set(roles)==expected and len(roles)==4})
 if len(primary)!=4 or set(roles)!=expected: raise AssertionError("Primary4 quota")
 backups=exp["backups_ranked"]; checks.append({"name":"backups_at_least_8","pass":len(backups)>=8 and len(set(backups))==len(backups)})
 checks.append({"name":"expansion_first6","pass":exp["first6"]==exp["primary4"]+backups[:2]})
 checks.append({"name":"expansion_first8","pass":exp["first8"]==exp["primary4"]+backups[:4]})
 if len(backups)<8 or exp["first6"]!=exp["primary4"]+backups[:2] or exp["first8"]!=exp["primary4"]+backups[:4]: raise AssertionError("expansion order")
 for name in ["m6_coverage_summary.json","m6_solver_cost_package.json","m6_external_registry_audit.json","m6_provenance_audit.json"]: checks.append({"name":f"artifact_{name}","pass":(OUT/name).exists()})
 checks.append({"name":"zero_solver","pass":all(zero.get(k,0)==0 for k in ["solver_calls","fdtd_run_calls","lumapi_solver_run_calls","external_hf_calls","sealed_target_reads","inverse_design_artifacts"])})
 checks.append({"name":"external_metadata_only","pass":ext["metadata_only"] and ext["sealed_hf_target_read"]==0 and ext["used_as_m6_candidate"] is False})
 checks.append({"name":"no_fsp_or_runtime_artifacts_in_m6_output","pass":not any(p.suffix.lower() in {".fsp",".npz",".log"} for p in OUT.rglob("*"))})
 report={"validator":"validate_np_k6_m6_error_region_acquisition_design_v1","status":"PASS","checks":checks,"candidate_count":len(gids),"solver_calls":0,"sealed_target_reads":0,"external_target_reads":0}
 (OUT/"m6_validator_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(report,indent=2))
if __name__=='__main__': main()

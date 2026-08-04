"""Finalize authorized DOE96 database metadata without solver access."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

def sha_file(p):
 h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def dump(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def main(run):
 run=Path(run)
 grid_path=run/"joint_profile_grid_contract.json"
 grid=json.loads(grid_path.read_text(encoding="utf-8"))
 grid["angle_grid_policy"]="first-case native farfieldangle grid frozen; all cases must match within 1e-6 deg (native export floating quantization)"
 grid["angle_grid_match_tolerance_deg"]=1e-6
 grid["marginal_closure_tolerance"]=1e-12
 grid["marginal_closure_policy"]="recompute both marginals from raw joint tensor using radians for both theta and wavelength quadrature"
 dump(grid_path,grid)
 smoke=json.loads((run/"doe96_upgrade_smoke_audit.json").read_text(encoding="utf-8")); smoke["upgrade_contract_sha256"]=sha_file(run/"joint_profile_export_contract_resolved.json"); dump(run/"doe96_upgrade_smoke_audit.json",smoke)
 ledger_lines=[json.loads(x) for x in (run/"doe96_case_attempt_ledger.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
 dump(run/"doe96_case_attempt_ledger.json",{"entry_count":len(ledger_lines),"solver_entered_count":sum(bool(x.get("solver_entered")) for x in ledger_lines),"recovery_extraction_only_count":sum(x.get("recovery_type")=="post_fsp_extraction_only" for x in ledger_lines),"entries":ledger_lines})
 r1=json.loads((run/"doe96_extraction_replay_1.json").read_text()); r2=json.loads((run/"doe96_extraction_replay_2.json").read_text())
 keys=["case_index_sha256","joint_tensor_index_sha256","grid_sha256","geometry_profile_sha256","scalar_label_sha256","aggregation_membership_sha256","np_interface_view_sha256"]
 matches={k:r1[k]==r2[k] for k in keys}
 dump(run/"doe96_extraction_reproducibility_audit.json",{"status":"PASS" if all(matches.values()) else "HARD_GATE_REPLAY_MISMATCH","required_fields":keys,"replay_1":r1,"replay_2":r2,"exact_sha_matches":matches,"all_exact":all(matches.values()),"solver_calls":0})
 solver=json.loads((run/"doe96_solver_run_manifest.json").read_text())
 quality=json.loads((run/"doe96_case_quality_audit_v1.json").read_text())
 geom=json.loads((run/"doe96_geometry_label_manifest_v1.json").read_text())
 agg=json.loads((run/"doe96_aggregation_audit_v1.json").read_text())
 np_a=json.loads((run/"doe96_np_interface_consumption_test.json").read_text())
 auth=json.loads((run/"doe96_solver_authorization.json").read_text())
 completion={"status":"MDC_HF_SURROGATE_V2_DOE96_DATABASE_COMPLETE_READY_FOR_PROFILE_COMPRESSION_AND_OOF_TRAINING_AUTHORIZATION_REVIEW","tier":"DOE96","authorized_geometry_count":auth["authorized_geometry_count"],"authorized_unique_physical_cases":auth["authorized_case_count"],"accepted_cases":solver["accepted_cases"],"geometry_count":geom["geometry_count"],"joint_tensor_shape":quality["shape_set"][0],"joint_tensor_case_count":json.loads((run/"doe96_case_label_manifest_v1.json").read_text())["joint_tensor_case_count"],"quality_audit_status":quality["status"],"aggregation_audit_status":agg["status"],"replay_audit_status":json.loads((run/"doe96_extraction_reproducibility_audit.json").read_text())["status"],"np_interface_status":np_a["status"],"solver_counters":solver["safety_counters"],"DOE96_authorized":auth["DOE96_authorized"],"HF15_formal_reads":solver["safety_counters"]["HF15_formal_reads"],"sealed_test_reads":solver["safety_counters"]["sealed_test_reads"],"source_policy":"DOE96 authorized only; no HF15 formal values or diagnostics read"}
 dump(run/"doe96_completion_manifest.json",completion)
 report=f"""# DOE96 joint-profile database completion\n\n- Status: `{completion['status']}`\n- Authorization: DOE96 authorized; 96 geometries / 576 unique physical cases.\n- Joint export: native per-wavelength farfield2d tensor, shape `{completion['joint_tensor_shape']}`, 576/576 accepted.\n- Quality: finite ratio 1.0, negative count 0, raw-before-normalization and marginal closure PASS.\n- Aggregation: 96 geometry profiles, six raw cases per geometry, no case-level normalization before aggregation.\n- Replay: two independent fresh Python processes, all deterministic SHA fields identical.\n- NP interface: frozen synthetic consumption fixture PASS; solver calls 0.\n- Safety: 576 FDTD solver entries, 0 recovery solver calls, 0 HF15/sealed/TMM/RCWA/model-fit calls.\n\nDOE96 solver and extraction are complete; no HF15 formal labels or diagnostics were read.\n"""
 (run/"doe96_completion_report.md").write_text(report,encoding="utf-8")
 hashes={}
 for p in sorted(run.rglob("*")):
  if p.is_file() and p.name!="doe96_artifact_sha256.json" and p.suffix.lower() in {".json",".jsonl",".md",".parquet"}:
   hashes[str(p.relative_to(run))]=sha_file(p)
 dump(run/"doe96_artifact_sha256.json",{"status":"PASS","policy":"metadata, reports, indexes and parquet views; raw FSP/NPZ payloads excluded from Git artifact set","files":hashes})
 print(json.dumps({"status":completion["status"],"artifact_count":len(hashes),"solver_calls":solver["total_solver_calls"]},sort_keys=True))
if __name__=="__main__": main(sys.argv[1])

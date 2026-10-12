from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=ROOT/"reports/coupling/APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1"
INV=ROOT/"reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/science_admission_setup_review_v1/V3_SOURCE_SETUP_INVENTORY.json"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()
inv=json.loads(INV.read_text(encoding="utf-8-sig")); results=[]
rows=[("A1","K6V3_TIME_DIAG2_A1_5NM_6PS","K6V3_NUM_REPEAT_A1","0e6e522141ddbd0f9a4323cdc470293fd485af9493257a4ccd166383f6a62bb2","528d8b156a18cea2db65a094678a3df14003fd70f939998590b96f17250caa95",[120,160,165,175,160,195],"K6GDP2_DEV_G001"),("A2","K6V3_TIME_DIAG2_A2_5NM_6PS","K6V3_NUM_REPEAT_A2","540ec80315bcec60619afb85f60dc894d46e40bffd87d5f8c6fb38b48a2651d1","715c2c77208ef2de2af34bd0da72aae68878a1f8a1d99b5ddbc2bef57c751ac5",[210,115,175,115,180,125],"K6GDP2_DEV_G004")]
for tag,cid,srcid,srcsha,proofsha,geom,anchor in rows:
 p=OUT/f"{tag}_SETUP_LOAD_PROOF.json"; x=json.loads(p.read_text(encoding="utf-8-sig")); c=x["fresh_readback"]
 record=next(y for y in inv["cases"] if y["case_id"]==srcid and y["attempt_id"]=="attempt_001")
 source_fsp=Path(record["artifacts"]["pre_fsp"]["path"]); source_proof=Path(record["artifacts"]["load_proof"]["path"]); b=json.loads(source_proof.read_text(encoding="utf-8-sig"))["canonical_readback"]
 assert sha(source_fsp)==srcsha and sha(source_proof)==proofsha
 assert record["artifacts"]["pre_fsp"]["sha256"]==srcsha and record["artifacts"]["load_proof"]["sha256"]==proofsha
 target=Path(x["candidate_fsp_path"]); assert sha(target)==x["candidate_fsp_sha256"]
 assert x["case_id"]==cid and x["source_case_id"]==srcid and x["ordered_D_nm"]==geom and x["anchor_case_id"]==anchor
 assert x["fresh_native_load"] and x["solver_api_run_called"] is False and x["scientific_entry_count"]==0 and x["replay_count"]==0
 assert c["run_called"] is False and c["save_called_by_validator"] is False
 assert c["fdtd"]["simulation_time_s"]==6e-12 and c["fdtd"]["auto_shutoff_min"]==1e-6
 assert c["meshes"]["NP_DERIVED_BASELINE_N2"]["step_nm"]==[5.0,5.0,5.0]
 diffs={}
 for k in sorted(set(b["fdtd"])|set(c["fdtd"])):
  if b["fdtd"].get(k)!=c["fdtd"].get(k): diffs["fdtd/"+k]={"source":b["fdtd"].get(k),"candidate":c["fdtd"].get(k)}
 assert list(diffs)==["fdtd/simulation_time_s"],(cid,diffs)
 same=[]
 for k in ["ordered_D_nm","geometry_hash_sha256","object_names","object_types","geometry","stack","source_names","sources","monitor_names","monitors","wavelengths_nm","sample_reference_planes","mesh_names","meshes","materials","mesh_coverage"]:
  assert b.get(k)==c.get(k),cid+" readback changed: "+k
  same.append(k)
 results.append({"case_id":cid,"source_case_id":srcid,"anchor_case_id":anchor,"ordered_D_nm":geom,"source_fsp_sha256":sha(source_fsp),"source_load_proof_sha256":sha(source_proof),"candidate_fsp_path":str(target),"candidate_fsp_sha256":sha(target),"candidate_proof_path":str(p),"candidate_proof_sha256":sha(p),"only_readback_difference":diffs,"unchanged_readback_sections":same,"auto_shutoff_min":c["fdtd"]["auto_shutoff_min"],"core_mesh_override_nm":c["meshes"]["NP_DERIVED_BASELINE_N2"]["step_nm"],"solver_entry_count":0,"replay_count":0})
result={"schema":"APCD_COUPLING_DIAG2_SETUP_READBACK_AUDIT_V1","status":"PASS_SETUP_ONLY","cases":results,"statement":"This verifies setup FSP readback only. It does not verify engine-generated mesh, solver output, time convergence, scientific truth, or GPU admission."}
(OUT/"SETUP_READBACK_AUDIT.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2,ensure_ascii=False))

import json,sys
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts"/"coupling_ml"))
from k6_v2_pipeline import contracts as C
from k6_v2_pipeline.ingest import (
 DataAccessError,load_frozen_case_registry,load_development_collection,
 load_diagnostic_case,issue_reveal_authorization
)
from k6_v2_pipeline.splits import fit_geometry_scaler,load_geometry_fold_plan

def test_frozen_registry_counts_and_role_hash():
 r=load_frozen_case_registry(ROOT)
 assert len(r.development)==128 and len(r.confirmation)==32
 assert sum(bool(x.get("boundary_stress")) for x in r.confirmation.values())==1

def test_training_rejects_confirmation_before_artifact_access():
 r=load_frozen_case_registry(ROOT); cid=next(iter(r.confirmation.values()))["case_id"]
 record={"case_id":cid,"role":C.ROLE_GLOBAL_CORE_CONFIRM,"state_npz":{"path":"missing","sha256":"0"*64}}
 with pytest.raises(DataAccessError,match="rejected_before_response_access"):
  load_development_collection(new_case_records=[record],root=ROOT,registry=r)

def test_training_rejects_diagnostic_before_artifact_access():
 record={"case_id":C.TWO_PLANE_CASE_ID,"role":C.ROLE_DIAGNOSTIC,"state_npz":{"path":"missing","sha256":"0"*64}}
 with pytest.raises(DataAccessError,match="rejected_before_response_access"):
  load_development_collection(new_case_records=[record],root=ROOT)

def test_diagnostic_descriptor_does_not_open_response_files():
 x=load_diagnostic_case({"case_id":C.TWO_PLANE_CASE_ID,"attempt_id":C.TWO_PLANE_ATTEMPT_ID,
  "role":C.ROLE_DIAGNOSTIC,"protocol_sha256":C.TWO_PLANE_PROTOCOL_SHA256,
  "ordered_D_nm":[220,120,155,100,105,110],"artifacts":{"raw_npz":{"path":"missing"}}})
 assert x.role==C.ROLE_DIAGNOSTIC and x.artifact_descriptors["raw_npz"]["path"]=="missing"

def _freeze_fixture(tmp_path,registry,*,incomplete=False,sealed_path=False):
 from k6_v2_pipeline.ingest import sha256_file
 tmp_path.mkdir(parents=True,exist_ok=True)
 h1=ROOT/"scripts/coupling_ml/k6_v2_pipeline/h1.py"
 eh=sha256_file(h1)
 bundles={}
 global_ids=sorted(k for k,v in registry.confirmation.items() if v["role"]=="SEALED_CONFIRMATION_GLOBAL")
 local_ids=sorted(k for k,v in registry.confirmation.items() if v["role"]==C.ROLE_LOCAL_CONFIRM)
 for name,ids in (("RBF_KRR",global_ids),("CARTESIAN_MLP",global_ids),("LOCAL_AFFINE",local_ids)):
  b={"case_ids":ids.copy()}
  for key in ("prediction","config","model","preprocessing"):
   path=tmp_path/f"{name}_{key}.bin"
   if sealed_path and name=="RBF_KRR" and key=="prediction":
    path=tmp_path/"truth_access"/"confirmation.npz";path.parent.mkdir(parents=True,exist_ok=True)
   else: path.parent.mkdir(parents=True,exist_ok=True)
   path.write_bytes((name+key).encode())
   b[key+"_path"]=str(path);b[key+"_sha256"]=sha256_file(path)
  b["evaluator_path"]=str(h1);b["evaluator_sha256"]=eh
  bundles[name]=b
 if incomplete: bundles["CARTESIAN_MLP"]["case_ids"].pop()
 m={"schema":"COUPLING_ML_K6_V2_CONFIRMATION_FREEZE_V1","pointset_sha256":registry.pointset_sha256,
    "confirmation_role_allowlist_sha256":registry.confirmation_role_sha256,
    "evaluators":{"h1_authority_sha256":C.H1_AUTHORITY_SHA256,"h2_decoder_sha256":C.H2_DECODER_SHA256,"confirmation_evaluator_sha256":eh,"confirmation_orchestrator_sha256":sha256_file(ROOT/"scripts/coupling_ml/k6_v2_pipeline/confirmation.py")},
    "prediction_bundles":bundles}
 path=tmp_path/"freeze.json";path.write_text(json.dumps(m),encoding="utf-8")
 return path,sha256_file(path)

def test_reveal_token_binds_and_persistently_starts_once(tmp_path):
 r=load_frozen_case_registry(ROOT); manifest,msha=_freeze_fixture(tmp_path,r); ledger=tmp_path/"ledger.jsonl"
 t=issue_reveal_authorization(freeze_manifest_path=manifest,freeze_manifest_sha256=msha,
  pointset_sha256=r.pointset_sha256,role_allowlist_sha256=r.confirmation_role_sha256,
  reveal_ledger_path=ledger,root=ROOT)
 cid=next(iter(r.confirmation));t.consume(cid)
 row=json.loads(ledger.read_text().splitlines()[0])
 assert row["status"]=="REVEAL_STARTED" and row["first_case_id"]==cid and row["freeze_manifest_sha256"]==msha
 with pytest.raises(DataAccessError,match="reuse"): t.consume(cid)
 with pytest.raises(DataAccessError,match="already_started"):
  issue_reveal_authorization(freeze_manifest_path=manifest,freeze_manifest_sha256=msha,
   pointset_sha256=r.pointset_sha256,role_allowlist_sha256=r.confirmation_role_sha256,
   reveal_ledger_path=ledger,root=ROOT)

def test_freeze_gate_rejects_missing_hash_incomplete_coverage_and_sealed_paths(tmp_path):
 r=load_frozen_case_registry(ROOT); manifest,msha=_freeze_fixture(tmp_path,r,incomplete=True)
 with pytest.raises(DataAccessError,match="coverage"): issue_reveal_authorization(
  freeze_manifest_path=manifest,freeze_manifest_sha256=msha,pointset_sha256=r.pointset_sha256,
  role_allowlist_sha256=r.confirmation_role_sha256,reveal_ledger_path=tmp_path/"ledger1",root=ROOT)
 manifest_bad,msha_bad=_freeze_fixture(tmp_path/"missing_hash",r)
 mb=json.loads(manifest_bad.read_text()); del mb["prediction_bundles"]["RBF_KRR"]["model_sha256"]
 manifest_bad.write_text(json.dumps(mb)); msha_bad=__import__("hashlib").sha256(manifest_bad.read_bytes()).hexdigest()
 with pytest.raises(DataAccessError,match="schema_incomplete"): issue_reveal_authorization(
  freeze_manifest_path=manifest_bad,freeze_manifest_sha256=msha_bad,pointset_sha256=r.pointset_sha256,
  role_allowlist_sha256=r.confirmation_role_sha256,reveal_ledger_path=tmp_path/"ledger_missing",root=ROOT)
 manifest2,msha2=_freeze_fixture(tmp_path/"other",r,sealed_path=True)
 with pytest.raises(DataAccessError,match="sealed_response"): issue_reveal_authorization(
  freeze_manifest_path=manifest2,freeze_manifest_sha256=msha2,pointset_sha256=r.pointset_sha256,
  role_allowlist_sha256=r.confirmation_role_sha256,reveal_ledger_path=tmp_path/"ledger2",root=ROOT)
 with pytest.raises(DataAccessError,match="sha_mismatch"): issue_reveal_authorization(
  freeze_manifest_path=manifest,freeze_manifest_sha256="0"*64,pointset_sha256=r.pointset_sha256,
  role_allowlist_sha256=r.confirmation_role_sha256,reveal_ledger_path=tmp_path/"ledger3",root=ROOT)

def test_geometry_scaler_fits_only_supplied_train_indices():
 x=np.array([[0]*6,[2]*6,[1000]*6],float)
 s=fit_geometry_scaler(x,[0,1],["a","b","held"])
 assert np.allclose(s.mean,1) and np.allclose(s.scale,1)
 assert s.fit_case_ids==("a","b") and np.allclose(s.transform(x)[2],999)
 with pytest.raises(DataAccessError): fit_geometry_scaler(x,[0,0])
 assert fit_geometry_scaler(x,[0,1,2]).scale[0] > s.scale[0]


def _synthetic_runner_record(tmp_path,registry,*,bad_wavelength=False,bad_source_fraction=False,case_id="K6LDA1_DEV_D1_M05"):
 from k6_v2_pipeline.ingest import sha256_file
 import importlib.util
 tmp_path.mkdir(parents=True,exist_ok=True)
 cid=case_id; reg=registry.development[cid]; D=reg["ordered_D_nm"]
 source=ROOT/"scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py"
 spec=importlib.util.spec_from_file_location("synthetic_truth_source",source)
 mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod);dec=mod
 wls=np.asarray(C.WAVELENGTHS_NM,dtype=float)
 state_wls=wls.copy()
 if bad_wavelength: state_wls[0]=441
 orders=np.array([(m,n) for n in range(-4,5) for m in range(-4,5)],dtype=int)
 oi={tuple(x):i for i,x in enumerate(orders)}
 cr=np.zeros((3,21,81,2,2)); ci=np.zeros_like(cr); kz=np.zeros((3,21,81)); mask=np.zeros((3,21,81),bool)
 for j,wl in enumerate(wls):
  for m in range(-3,4):
   q=oi[(m,0)]; kz[2,j,q]=dec._mode(m,0,float(wl),1.0,1,"TE")["kz_rad_m"].real
   mask[2,j,q]=True;cr[2,j,q,0,:]=1.0
 state=tmp_path/"state.npz"
 np.savez(state,coefficients_real=cr,coefficients_imag=ci,wavelengths_nm=state_wls,
  orders=orders,propagating_mask=mask,mode_kz_real=kz)
 sh=sha256_file(state)
 sm=tmp_path/"state.json";sm.write_text(json.dumps({"sha256":sh,"schema_version":"PW_COMPLEX_FLOQUET_STATE_V1",
  "planes":["IN","PRENP","POSTNP"],"directions":["+z","-z"],"polarizations":["TE","TM"]}))
 raw=tmp_path/"raw.npz"; shape=(2,2,1,21)
 ex=np.full(shape,2.0);ey=np.zeros(shape);hx=np.zeros(shape);hy=np.full(shape,2.0)
 np.savez(raw,POSTNP_f=299792458.0/(wls*1e-9),POSTNP_x=np.array([0,1.74e-6]),
  POSTNP_y=np.array([0,290e-9]),POSTNP_Ex=ex,POSTNP_Ey=ey,POSTNP_Hx=hx,POSTNP_Hy=hy)
 rh=sha256_file(raw)
 rm=tmp_path/"raw.json"
 pc_path=Path(r"D:\\apcd_runtime\\gpu_production_runner_v1\\contracts\\pw_contract_32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.json")
 pc=json.loads(pc_path.read_text(encoding="utf-8-sig"))
 raw_desc={"schema":"APCD_PW_RAW_COMPLEX_FIELDS_V1","sha256":rh,"path":str(raw)}
 norm={"incident_power_per_area":[2.0]*21,"gauge_phase_rad":[0.0]*21,
  "gauge":"single_global_phase_per_wavelength_from_IN_REF_+z_(0,0)_TM"}
 rm.write_text(json.dumps({"case_id":cid,"attempt_id":"attempt_001","contract":pc,"raw_complex_fields":raw_desc,
  "canonical_state":{"axis_order":["plane","wavelength","order","direction","polarization"],
  "directions":["+z","-z"],"polarizations":["TE","TM"],"normalization":norm}}))
 order_rows=[]
 for wl in C.WAVELENGTHS_NM:
  order_rows.append([{"order_x":m,"order_y":0,"power_fraction_of_monitor_total":1/7,
   "power_fraction_of_source":(0.05 if bad_source_fraction else 1/7)} for m in range(-3,4)])
 op=tmp_path/"orders.json";op.write_text(json.dumps({"schema":"APCD_PW_PERIODIC_DIFFRACTION_ORDERS_V1",
  "wavelengths_nm":list(C.WAVELENGTHS_NM),"post":order_rows}))
 manifest=tmp_path/"manifest.json";manifest.write_text(json.dumps({"case_id":cid,"attempt_id":"attempt_001",
  "geometry":list(D),"physical_contract_sha256":C.PHYSICAL_CONTRACT_SHA256,"pre_fsp_sha256":"a"*64}))
 def a(path): return {"path":str(path),"sha256":sha256_file(path)}
 return {"case_id":cid,"attempt_id":"attempt_001","role":reg["role"],"ordered_D_nm":list(D),
  "physical_contract_sha256":C.PHYSICAL_CONTRACT_SHA256,"status":"DONE","solver_invocations":1,"replay_count":0,
  "source_manifest":a(manifest),"state_npz":a(state),"state_metadata":a(sm),"raw_npz":a(raw),"raw_metadata":a(rm),"orders_json":a(op)}

def test_verified_runner_ingest_uses_frozen_extractor_and_preserves_axes(tmp_path):
 from k6_v2_pipeline.ingest import load_verified_runner_case
 r=load_frozen_case_registry(ROOT); rec=_synthetic_runner_record(tmp_path,r)
 t=load_verified_runner_case(rec,expected_role=rec["role"],root=ROOT,registry=r)
 assert t.c_hat.shape==(21,7,2) and t.p_scale.shape==(21,) and t.eta.shape==(21,7)
 assert np.isfinite(t.c_hat.real).all() and np.allclose(t.p_scale,1.0)
 assert t.provenance["truth_extractor_sha256"]==C.H1_EVALUATOR_SOURCE_SHA256
 assert t.provenance["reference_plane_nm"]==1722.0

def test_verified_runner_ingest_rejects_wavelength_schema_error(tmp_path):
 from k6_v2_pipeline.ingest import load_verified_runner_case
 r=load_frozen_case_registry(ROOT); rec=_synthetic_runner_record(tmp_path,r,bad_wavelength=True)
 with pytest.raises(Exception,match="state_shape_or_wavelength_mismatch"):
  load_verified_runner_case(rec,expected_role=rec["role"],root=ROOT,registry=r)

def _synthetic_power_mapping_supplement(tmp_path,record):
 from k6_v2_pipeline import ingest
 tmp_path.mkdir(parents=True,exist_ok=True)
 from k6_v2_pipeline.ingest import sha256_file,geometry_sha
 import json
 artifacts={k:record[k]["sha256"] for k in
  ("source_manifest","state_npz","state_metadata","raw_npz","raw_metadata","orders_json")}
 mapping=dict(ingest._POWER_MAPPING)
 p_scale=np.ones(21); eta=np.ones((21,7))/7
 numeric={"p_scale":ingest._float_array_sha256(p_scale),
  "eta":ingest._float_array_sha256(eta),
  "source_fraction":ingest._float_array_sha256(p_scale[:,None]*eta)}
 audit={"schema":ingest._POWER_AUDIT_SCHEMA,"status":"PASS",
  "training_label_eligible":True,
  "case_id":record["case_id"],"attempt_id":record["attempt_id"],
  "ordered_geometry_sha256":geometry_sha(record["ordered_D_nm"]),
  "physical_contract_sha256":C.PHYSICAL_CONTRACT_SHA256,
  "artifact_sha256":artifacts,"numeric_sha256":numeric,"mapping":mapping,
  "audit_kind":"synthetic_fixture_only"}
 audit_path=tmp_path/"power_audit.json"
 audit_path.write_text(json.dumps(audit,sort_keys=True),encoding="utf-8")
 supplement={"schema":ingest._POWER_SUPPLEMENT_SCHEMA,"status":"PASS",
  "training_label_eligible":True,
  "case_id":record["case_id"],"attempt_id":record["attempt_id"],"role":record["role"],
  "ordered_D_nm":record["ordered_D_nm"],
  "ordered_geometry_sha256":geometry_sha(record["ordered_D_nm"]),
  "physical_contract_sha256":C.PHYSICAL_CONTRACT_SHA256,
  "artifact_sha256":artifacts,"numeric_sha256":numeric,"mapping":mapping,
  "independent_audit":{"path":str(audit_path),"sha256":sha256_file(audit_path)}}
 path=tmp_path/"power_mapping_supplement.json"
 path.write_text(json.dumps(supplement,sort_keys=True),encoding="utf-8")
 return {"path":str(path),"sha256":sha256_file(path)}

def test_bad_runner_source_power_mapping_remains_fail_closed_by_default(tmp_path):
 from k6_v2_pipeline.ingest import load_verified_runner_case
 r=load_frozen_case_registry(ROOT)
 rec=_synthetic_runner_record(tmp_path,r,bad_source_fraction=True)
 with pytest.raises(DataAccessError,match="source_normalized_order_power_mismatch"):
  load_verified_runner_case(rec,expected_role=rec["role"],root=ROOT,registry=r)

def test_case_scoped_power_mapping_supplement_is_explicit_and_artifact_bound(tmp_path):
 from k6_v2_pipeline.ingest import load_verified_runner_case
 r=load_frozen_case_registry(ROOT)
 rec=_synthetic_runner_record(tmp_path,r,bad_source_fraction=True)
 supplement=_synthetic_power_mapping_supplement(tmp_path,rec)
 truth=load_verified_runner_case(rec,expected_role=rec["role"],root=ROOT,
  registry=r,power_supplement=supplement)
 assert truth.case_id=="K6LDA1_DEV_D1_M05"
 assert truth.provenance["power_mapping_source"]=="case_scoped_audited_p_scale_times_eta"
 assert truth.provenance["power_mapping_supplement_sha256"]==supplement["sha256"]
 assert np.allclose(truth.absolute_order,truth.p_scale[:,None]*truth.eta)

 import json
 from k6_v2_pipeline.ingest import sha256_file
 sp=Path(supplement["path"])
 altered=json.loads(sp.read_text(encoding="utf-8"))
 altered["artifact_sha256"]["raw_npz"]="0"*64
 sp.write_text(json.dumps(altered,sort_keys=True),encoding="utf-8")
 bad_supplement={"path":str(sp),"sha256":sha256_file(sp)}
 with pytest.raises(DataAccessError,match="power_mapping_supplement_artifact_binding_mismatch"):
  load_verified_runner_case(rec,expected_role=rec["role"],root=ROOT,registry=r,
   power_supplement=bad_supplement)

 other_case=next(cid for cid in r.development if cid!=rec["case_id"])
 rec2=_synthetic_runner_record(tmp_path/"other",r,bad_source_fraction=True,
  case_id=other_case)
 supplement2=_synthetic_power_mapping_supplement(tmp_path/"other_supplement",rec2)
 with pytest.raises(DataAccessError,match="power_mapping_supplement_scope_forbidden"):
  load_verified_runner_case(rec2,expected_role=rec2["role"],root=ROOT,registry=r,
   power_supplement=supplement2)

def test_confirmation_loader_requires_freeze_authorization_before_artifacts(tmp_path):
 from k6_v2_pipeline.ingest import load_confirmation_case
 r=load_frozen_case_registry(ROOT); cid,item=next(iter(r.confirmation.items()))
 rec={"case_id":cid,"attempt_id":"attempt_001","role":item["role"],
  "ordered_D_nm":list(item["ordered_D_nm"]),"physical_contract_sha256":C.PHYSICAL_CONTRACT_SHA256,
  "state_npz":{"path":"must_not_open","sha256":"0"*64}}
 with pytest.raises(DataAccessError,match="token_invalid"):
  load_confirmation_case(rec,reveal_authorization=None,root=ROOT,registry=r)

def test_frozen_geometry_folds_keep_cases_grouped():
 r=load_frozen_case_registry(ROOT)
 # Metadata-only synthetic CaseTruths; response arrays are not loaded for this split audit.
 cases=[]
 for i,(cid,row) in enumerate({**r.old32,**r.development}.items()):
  pass
 oldp=ROOT/"reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json"
 old=json.loads(oldp.read_text(encoding="utf-8-sig"))
 prov={x["case_id"]:x for x in old["case_provenance"]}
 from k6_v2_pipeline.contracts import CaseTruth,CaseCollection
 for cid in json.loads((ROOT/"reports/coupling/COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1/DEVELOPMENT_CASE_ALLOWLIST_V1.json").read_text(encoding="utf-8-sig"))["old32_case_ids"]:
  cases.append(CaseTruth(cid,"attempt_001",C.ROLE_OLD32,tuple(prov[cid]["ordered_D_nm"]),np.zeros((21,7,2),complex),np.ones(21),np.ones((21,7))/7,np.ones((21,7))/7,{}))
 cand={cid:v for cid,v in r.development.items()}
 for cid,v in cand.items():
  cases.append(CaseTruth(cid,"attempt_001",v["role"],v["ordered_D_nm"],np.zeros((21,7,2),complex),np.ones(21),np.ones((21,7))/7,np.ones((21,7))/7,{}))
 col=CaseCollection("development",tuple(cases),"synthetic",{})
 p=load_geometry_fold_plan(col,ROOT)
 assert len(p.outer_folds)==4
 for f in p.outer_folds.values():
  assert len(f.train_indices)==128 and len(f.validation_indices)==32
  assert tuple(map(len,f.learning_curve.values()))==(32,64,128)

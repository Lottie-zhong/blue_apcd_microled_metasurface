from __future__ import annotations
import argparse, datetime as dt, hashlib, importlib.metadata as md, json, os, platform, sys
from pathlib import Path

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TASK_REL=Path("reports/coupling/COUPLING_ML_PARTIAL_DEVELOPMENT_DIAG_33G_2FITS_V1")
TASK=ROOT/TASK_REL
AUDIT=TASK/"DATASET_AUDIT_33G.json"
DATASET=TASK/"DATASET_SHA256_MANIFEST_V1.json"
SPLIT=TASK/"DIAGNOSTIC_SPLIT_V1.json"
CONFIG=TASK/"PARTIAL_DIAGNOSTIC_CONFIG_V1.json"
PROTOCOL=TASK/"PREFIT_PROTOCOL_V1.json"
LEDGER=TASK/"FIT_LEDGER_V1.json"
ENVFILE=TASK/"ENVIRONMENT_INVENTORY_V1.json"
EXE=r"N:\anaconda_envs\RCP_LCP\python.exe"
SEED=3208
IMPL=[
 "scripts/coupling_ml/k6_v2_pipeline/contracts.py",
 "scripts/coupling_ml/k6_v2_pipeline/ingest.py",
 "scripts/coupling_ml/k6_v2_pipeline/models.py",
 "scripts/coupling_ml/k6_v2_pipeline/training.py",
 "scripts/coupling_ml/k6_v2_pipeline/h1.py",
 "scripts/coupling_ml/k6_v2_pipeline/real32_diagnostic.py",
]

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha_file(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
def readj(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def writej(p,v,exclusive=False):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
 b=(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+"\n").encode()
 if exclusive:
  with p.open("xb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
 else:
  t=p.with_name(p.name+"."+str(os.getpid())+".tmp")
  with t.open("xb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
  os.replace(t,p)
def safe(v):
 import numpy as np
 if isinstance(v,dict): return {str(k):safe(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)): return [safe(x) for x in v]
 if isinstance(v,np.ndarray): return safe(v.tolist())
 if isinstance(v,np.generic):
  x=v.item()
  return x if not isinstance(x,float) or np.isfinite(x) else None
 if isinstance(v,float) and not __import__("math").isfinite(v): return None
 return v
def env():
 import numpy as np, scipy, sklearn, torch
 return {"python_executable":str(Path(sys.executable).resolve()),"python_version":platform.python_version(),
  "environment_name":"RCP_LCP","numpy":np.__version__,"scipy":scipy.__version__,
  "scikit_learn":sklearn.__version__,"torch":torch.__version__,"torch_cuda_runtime":torch.version.cuda,
  "cuda_available":bool(torch.cuda.is_available()),
  "cuda_devices":[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
  "fit_device":"cpu"}
def impl_hashes():
 return {x:sha_file(ROOT/x) for x in IMPL+[str(TASK_REL/"RUN_PARTIAL_DIAGNOSTIC_V1.py")]}
def tasks(train,val):
 from scripts.coupling_ml.k6_v2_pipeline.training import FitTask
 common={"phase":"engineering_diagnostic","outer_fold":None,"inner_fold":None,
  "training_geometry_count":52,"train_case_ids":tuple(train),"prediction_case_ids":tuple(val),
  "config_source":CONFIG.name,"update_source":"frozen_grid_midpoint_lowest_seed"}
 return {
 "RBF_KRR":FitTask(task_id="partial65_krr",model_kind="RBF_KRR",gamma=1/3,ridge_alpha=1e-2,
  weight_decay=None,seed=None,fixed_updates=None,**common),
 "CARTESIAN_MLP":FitTask(task_id="partial65_mlp_s0",model_kind="CARTESIAN_MLP",gamma=None,
  ridge_alpha=None,weight_decay=1e-4,seed=0,fixed_updates=None,**common)}

_ARTIFACT_KEYS=("source_manifest","state_metadata","raw_metadata","orders_json","state_npz","raw_npz","truth_h5")

def build_record(ingest_result,row):
 cid=row["case_id"]
 if ingest_result.get("schema") not in ("COUPLING_K6_V2_DEVELOPMENT_CASE_INGEST_RESULT_V1",
                                          "COUPLING_K6_V2_FIRST_CASE_INGEST_RESULT_V1"):
  raise ValueError("ingest_result_schema_unrecognized:"+cid)
 if row.get("runner_status",{}).get("value")!="DONE":
  raise ValueError("runner_status_not_done:"+cid)
 for key,expected in (("case_id",cid),("attempt_id",row["attempt_id"]),("role",row["role"]),
                      ("ordered_D_nm",row["ordered_D_nm"]),
                      ("physical_contract_sha256",row["physical_contract_sha256"])):
  if key in ingest_result and ingest_result[key]!=expected:
   raise ValueError("ingest_result_identity_mismatch:"+cid+":"+key)
 if "status" in ingest_result and ingest_result["status"]!="PASS":
  raise ValueError("ingest_result_not_pass:"+cid)
 run_id=ingest_result.get("run_id")
 if not isinstance(run_id,str) or not run_id:
  raise ValueError("ingest_result_run_id_missing:"+cid)
 status_desc=row["runner_status"]
 status_path=Path(status_desc["path"])
 if not status_path.is_file() or sha_file(status_path)!=status_desc["sha256"]:
  raise ValueError("runner_status_sha_mismatch:"+cid)
 status_doc=readj(status_path)
 if (status_doc.get("case_id")!=cid or status_doc.get("attempt_id")!=row["attempt_id"]
     or status_doc.get("run_id")!=run_id or status_doc.get("state")!="DONE"
     or status_doc.get("solver_entered") is not True
     or int(status_doc.get("solver_invocations",-1))!=1
     or status_doc.get("truth_h5_sha256")!=row["truth_h5"]["sha256"]):
  raise ValueError("runner_status_identity_or_entry_mismatch:"+cid)
 if Path(row["truth_h5"]["path"]).parent.name!=run_id:
  raise ValueError("truth_run_path_mismatch:"+cid)
 for key in ("case_id","attempt_id","role","ordered_D_nm","physical_contract_sha256"):
  if key in status_doc and key in row and status_doc[key]!=row[key]:
   raise ValueError("runner_status_row_binding_mismatch:"+cid+":"+key)
 access=ingest_result.get("access",{}) or {}
 access_counts=ingest_result.get("access_counts",{}) or {}
 invocations=ingest_result.get("solver_invocations",
     access.get("first_case_historical_solver_entries",access_counts.get("solver_invocations",-1)))
 replay=ingest_result.get("replay_count",access.get("post_entry_replay",access_counts.get("replay_count",-1)))
 if (ingest_result.get("solver_entered",True) is not True or int(invocations)!=1 or int(replay)!=0):
  raise ValueError("ingest_result_entry_or_replay_mismatch:"+cid)
 supplied=ingest_result.get("input_artifacts")
 if supplied is not None:
  if not isinstance(supplied,dict):
   raise ValueError("input_artifacts_not_mapping:"+cid)
  for key,expected in (("case_id",cid),("attempt_id",row["attempt_id"]),("role",row["role"]),
                       ("ordered_D_nm",row["ordered_D_nm"]),
                       ("physical_contract_sha256",row["physical_contract_sha256"]),
                       ("status","DONE"),("solver_invocations",1),("replay_count",0)):
   if key in supplied and supplied[key]!=expected:
    raise ValueError("input_artifacts_identity_mismatch:"+cid+":"+key)
  for key in _ARTIFACT_KEYS:
   if key not in supplied:
    raise ValueError("input_artifacts_descriptor_missing:"+cid+":"+key)
   got=supplied[key]; expected=row[key]
   if not isinstance(got,dict) or got.get("path")!=expected.get("path") or got.get("sha256")!=expected.get("sha256"):
    raise ValueError("input_artifacts_descriptor_mismatch:"+cid+":"+key)
 rec={"case_id":cid,"attempt_id":row["attempt_id"],"role":row["role"],
      "ordered_D_nm":row["ordered_D_nm"],"physical_contract_sha256":row["physical_contract_sha256"],
      "status":"DONE","solver_invocations":1,"replay_count":0,"run_id":run_id}
 for key in _ARTIFACT_KEYS:
  rec[key]=row[key]
 return rec

def schema_adapter_test():
 audit=readj(AUDIT)
 selected=["K6GDP2_DEV_G001","K6LDA1_DEV_D1_M05","K6LDA1_DEV_D2_M05"]
 results=[]
 for cid in selected:
  row=next(x for x in audit["cases"] if x["case_id"]==cid)
  result=readj(row["ingest_result"]["path"])
  rec=build_record(result,row)
  results.append({"case_id":cid,"ingest_schema":result["schema"],
   "input_artifact_block_present":"input_artifacts" in result,
   "input_artifact_shape":("full_identity_plus_descriptors" if isinstance(result.get("input_artifacts"),dict) and "case_id" in result["input_artifacts"] else
      "descriptors_only" if isinstance(result.get("input_artifacts"),dict) else "legacy_no_block"),
   "record_binding":"PASS",
   "source_manifest_sha256":rec["source_manifest"]["sha256"],
   "truth_h5_sha256":rec["truth_h5"]["sha256"],"solver_invocations":rec["solver_invocations"],
   "replay_count":rec["replay_count"]})
 payload={"schema":"COUPLING_ML_PARTIAL_DIAG_INGEST_SCHEMA_ADAPTER_TEST_V2",
  "status":"PASS","purpose":"metadata-only adapter check; no fit and no response-array access",
  "cases":results,"real_model_fits":0,"solver_entries":0,"confirmation_response_access":0}
 writej(TASK/"SCHEMA_ADAPTER_TEST_V2.json",payload)
 return payload

def prepare():
 import numpy as np
 os.chdir(ROOT)
 if Path(sys.executable).resolve().as_posix().lower()!=Path(EXE).resolve().as_posix().lower():
  raise RuntimeError("wrong_interpreter:"+sys.executable)
 audit=readj(AUDIT); ds=readj(DATASET)
 if audit.get("case_count")!=33 or audit.get("official_loader_audit",{}).get("pass_count")!=33 or audit.get("official_loader_audit",{}).get("failed_count")!=0:
  raise ValueError("new33_audit_not_pass")
 ids=sorted(map(str,ds["combined_ordered_case_ids"]))
 if len(ids)!=65 or len(set(ids))!=65 or ds.get("unique_ordered_geometry_count")!=65:
  raise ValueError("combined_65_geometry_integrity")
 role={x["case_id"]:x["role"] for x in ds["new33"]["cases"]}
 role.update({x:"OLD32_DEVELOPMENT_REUSED" for x in ds["old32"]["case_ids"]})
 rng=np.random.Generator(np.random.PCG64(SEED))
 perm=list(map(str,rng.permutation(np.asarray(ids,dtype=object)).tolist()))
 val,train=perm[:13],perm[13:]
 if len(train)!=52 or len(val)!=13 or set(train)&set(val): raise ValueError("split_invalid")
 t=tasks(train,val); e=env()
 if e["python_version"]!="3.10.20": raise ValueError("historical_python_version_mismatch")
 names=[SPLIT,CONFIG,PROTOCOL,LEDGER,ENVFILE,TASK/"CONTINUATION.md"]
 if any(p.exists() for p in names): raise FileExistsError("prefit artifacts already exist; refusing overwrite/reset")
 split={"schema":"COUPLING_ML_PARTIAL_DEVELOPMENT_DIAG_SPLIT_V1",
  "purpose":"response-blind engineering diagnostic only; not independent confirmation",
  "seed":SEED,"algorithm":"sort case IDs; numpy Generator(PCG64(3208)).permutation; first 13 validation, remaining 52 training",
  "sorted_case_ids":ids,"training_case_ids":train,"validation_case_ids":val,
  "training_geometry_count":52,"validation_geometry_count":13,"all_21_wavelengths_grouped":True,
  "response_values_read":False,"role_counts":{r:sum(role[x]==r for x in ids) for r in sorted(set(role.values()))},
  "train_role_counts":{r:sum(role[x]==r for x in train) for r in sorted(set(role.values()))},
  "validation_role_counts":{r:sum(role[x]==r for x in val) for r in sorted(set(role.values()))},
  "old32_prior_exposure":ds["old32"]["prior_exposure_note"],
  "dataset_manifest_sha256":sha_file(DATASET),"dataset_audit_sha256":sha_file(AUDIT)}
 writej(SPLIT,split,True)
 config={"schema":"COUPLING_ML_PARTIAL_DIAGNOSTIC_CONFIG_V1",
  "selection":"one fixed config per candidate; midpoint frozen KRR grid and midpoint MLP decay, lowest frozen seed; no search",
  "models":{
   "RBF_KRR":{"task_id":t["RBF_KRR"].task_id,"gamma":1/3,"ridge_alpha":1e-2,"fits":1,"task_sha256":t["RBF_KRR"].fingerprint()},
   "CARTESIAN_MLP":{"task_id":t["CARTESIAN_MLP"].task_id,"architecture":"6-32-32-609; GELU; Cartesian C_hat head 588 and log-P_scale head 21",
    "parameters":21377,"seed":0,"optimizer":"AdamW","learning_rate":1e-3,"weight_decay":1e-4,
    "batch":"full batch","max_updates":1000,"early_stop":{"patience":50,"min_delta":1e-5},
    "fits":1,"task_sha256":t["CARTESIAN_MLP"].fingerprint()}},
  "target":{"C_hat":"full 21x7xTE/TM Cartesian complex state; 588 reals","P_scale":"separate log target; exp inverse; strict finite and positive; no epsilon/clipping",
    "compression":"none","scalers":"fit on the 52 training geometries only","loss_source":"frozen k6_v2_pipeline models/training implementations"}}
 config["split_sha256"]=sha_file(SPLIT); writej(CONFIG,config,True)
 response_sha=hashlib.sha256(canon({"old32_npz_sha256":ds["old32"]["dataset_sha256"],
  "new33_label_hashes":{x["case_id"]:x["label_npz_sha256"] for x in ds["new33"]["cases"]},
  "combined_snapshot_sha256":ds["combined_snapshot_sha256"]})).hexdigest()
 protocol={"schema":"COUPLING_ML_PARTIAL_DEVELOPMENT_DIAG_PREFIT_PROTOCOL_V1",
  "status":"FROZEN_BEFORE_RESPONSE_VALUE_ACCESS_AND_FITS","frozen_at_utc":utc(),
  "scope":"old32 reused development plus 33 newly audited development geometries; fixed 52/13 split; one KRR and one MLP fit",
  "authority":{"physical_contract_sha256":ds["frozen_physical_contract_sha256"],
   "h1_sha256":ds["h1_authority_sha256"],"h2_sha256":ds["h2_decoder_sha256"],
   "old32_authority_sha256":ds["old32"]["authority_sha256"],"old32_npz_sha256":ds["old32"]["dataset_sha256"]},
  "response_blind_inputs":{"dataset_audit_sha256":sha_file(AUDIT),"dataset_sha_manifest_sha256":sha_file(DATASET),
   "response_values_read_before_freeze":False},
  "split_sha256":sha_file(SPLIT),"config_sha256":sha_file(CONFIG),
  "implementation_sha256":impl_hashes(),"runtime":e,"fit_device":"cpu",
  "response_bundle_sha256":response_sha,
  "fit_budget":{"current_task_max":2,"krr":1,"mlp":1,"current_task_started_at_freeze":0,
   "prior_real32_fits_preserved":2,"solver":0,"confirmation_access":0,"p_scale_only":0,"replay":0},
  "checkpoint_rule":"frozen validation loss, patience=50, min_delta=1e-5, max 1000 MLP updates",
  "scope_limit":"diagnostic only; no production admission or independent confirmation"}
 writej(PROTOCOL,protocol,True)
 envrec={"schema":"COUPLING_ML_PARTIAL_DIAGNOSTIC_ENVIRONMENT_V1","before_fit":e,
  "after_fit":None,"environment_mutated":False,"dependency_installations":0,
  "historical":{"real32_python":"3.10.20","real32_device":"cpu","python_version_match":True,
   "historical_executable_path_recorded":False}}
 writej(ENVFILE,envrec,True)
 ledger={"schema":"COUPLING_ML_PARTIAL_DEVELOPMENT_DIAG_FIT_LEDGER_V1","status":"PREPARED",
  "protocol_sha256":sha_file(PROTOCOL),"split_sha256":sha_file(SPLIT),"config_sha256":sha_file(CONFIG),
  "dataset_manifest_sha256":sha_file(DATASET),"implementation_sha256":protocol["implementation_sha256"],
  "max_current_task_fits":2,"current_task_real_fits_started":0,"current_task_real_fits_completed":0,
  "current_task_krr_fits_started":0,"current_task_mlp_fits_started":0,"prior_real32_fits_preserved":2,
  "solver_entries":0,"p_scale_only_fits":0,"confirmation_response_access":0,"automatic_replay":0,
  "fits":{k:{"status":"NOT_STARTED","task":vars(v),"task_sha256":v.fingerprint()} for k,v in t.items()}}
 writej(LEDGER,ledger,True)
 (TASK/"CONTINUATION.md").write_text(
  "# CONTINUATION - PARTIAL DEVELOPMENT DIAGNOSTIC 33G 2 FITS\n\n"
  f"Updated UTC: {utc()}\n\nHost: DESKTOP-NNE313K, user dell. Worktree: {ROOT}. Branch: work/mdc-np-coupling-ml-v1.\n"
  f"Interpreter: {e['python_executable']} (RCP_LCP), Python {e['python_version']}; NumPy {e['numpy']}; SciPy {e['scipy']}; "
  f"scikit-learn {e['scikit_learn']}; PyTorch {e['torch']}; CUDA {e['torch_cuda_runtime']}; selected fit device CPU.\n"
  "Read this file and PREFIT_PROTOCOL_V1.json, DIAGNOSTIC_SPLIT_V1.json, PARTIAL_DIAGNOSTIC_CONFIG_V1.json, "
  "FIT_LEDGER_V1.json, and ENVIRONMENT_INVENTORY_V1.json before resuming.\n\n"
  "Prefit freeze completed before response values were read. Exactly one KRR and one MLP fit are authorized for this task; "
  "current fit count is zero. The prior two REAL32 fits remain in separate preserved accounting. No solver, confirmation response, "
  "diagnostic EXT02 truth, standalone P_scale fit, or automatic replay.\n",encoding="utf-8")
 for p in [SPLIT,CONFIG,PROTOCOL,LEDGER,ENVFILE,TASK/"CONTINUATION.md"]:
  print("FROZEN",p.name,sha_file(p),p.stat().st_size)
 print("VALIDATION_IDS",json.dumps(val,ensure_ascii=True))
 print("COUNTS",json.dumps(ledger["current_task_real_fits_started"]))

def load_data(split):
 import numpy as np
 from scripts.coupling_ml.k6_v2_pipeline import ingest,models,contracts as C
 audit=readj(AUDIT);ds=readj(DATASET);reg=ingest.load_frozen_case_registry(root=ROOT)
 old=ingest.load_old32_engineering_diagnostic(root=ROOT,registry=reg)
 by={x.case_id:x for x in old.cases}; ar={x["case_id"]:x for x in audit["cases"]}
 mr={x["case_id"]:x for x in ds["new33"]["cases"]}
 if set(ar)!=set(mr) or len(mr)!=33: raise ValueError("new33_id_mismatch")
 for cid in sorted(mr):
  row=ar[cid]; meta=mr[cid]
  if row["ingest_status"]!="PASS" or row["official_loader_reextraction"]["status"]!="PASS":raise ValueError("ingest_audit_fail:"+cid)
  if row["label_npz"]["sha256"]!=meta["label_npz_sha256"] or sha_file(row["label_npz"]["path"])!=meta["label_npz_sha256"]:raise ValueError("label_sha_mismatch:"+cid)
  rp=row["ingest_result"]["path"]
  if sha_file(rp)!=meta["ingest_result_sha256"]:raise ValueError("ingest_result_sha_mismatch:"+cid)
  ingest_result=readj(rp)
  rec=build_record(ingest_result,row)
  truth=ingest.load_verified_runner_case(rec,expected_role=meta["role"],root=ROOT,registry=reg,
    power_supplement=row.get("power_mapping_supplement"))
  if truth.case_id!=cid or tuple(truth.ordered_D_nm)!=tuple(meta["ordered_D_nm"]):raise ValueError("case_geometry_mismatch:"+cid)
  by[cid]=truth
 if set(by)!=set(split["sorted_case_ids"]) or len(by)!=65:raise ValueError("training_allowlist_mismatch")
 ids=split["sorted_case_ids"]
 if any(x.role not in C.DEVELOPMENT_ROLES for x in by.values()):raise ValueError("nondevelopment_role")
 x=np.asarray([by[c].ordered_D_nm for c in ids],dtype=np.float64)
 y=np.stack([models.pack_case_target(by[c].c_hat,by[c].p_scale) for c in ids])
 if x.shape!=(65,6) or y.shape!=(65,609) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError("training_array_shape_or_finiteness")
 ix={c:i for i,c in enumerate(ids)}
 tr=[ix[c] for c in split["training_case_ids"]];va=[ix[c] for c in split["validation_case_ids"]]
 return by,x[tr],y[tr],x[va],y[va]

def run():
 import numpy as np
 os.chdir(ROOT)
 if Path(sys.executable).resolve().as_posix().lower()!=Path(EXE).resolve().as_posix().lower():raise RuntimeError("wrong_interpreter")
 protocol=readj(PROTOCOL);split=readj(SPLIT);readj(CONFIG);ledger=readj(LEDGER)
 if protocol.get("status")!="FROZEN_BEFORE_RESPONSE_VALUE_ACCESS_AND_FITS":raise ValueError("protocol_not_frozen")
 if sha_file(SPLIT)!=protocol["split_sha256"] or sha_file(CONFIG)!=protocol["config_sha256"]:raise ValueError("split_or_config_sha")
 if sha_file(PROTOCOL)!=ledger["protocol_sha256"]:raise ValueError("ledger_protocol_sha")
 if sha_file(AUDIT)!=protocol["response_blind_inputs"]["dataset_audit_sha256"] or sha_file(DATASET)!=protocol["response_blind_inputs"]["dataset_sha_manifest_sha256"]:raise ValueError("dataset_metadata_changed")
 current_impl=impl_hashes()
 amendment_path=TASK/"IMPLEMENTATION_ERRATUM_V3.json"
 amendment=readj(amendment_path)
 executor_key=str(TASK_REL/"RUN_PARTIAL_DIAGNOSTIC_V1.py")
 base_impl=protocol["implementation_sha256"]
 if ({k:v for k,v in current_impl.items() if k!=executor_key} !=
     {k:v for k,v in base_impl.items() if k!=executor_key}):raise ValueError("non_executor_implementation_sha_changed")
 if current_impl.get(executor_key)!=amendment.get("updated_executor_sha256"):raise ValueError("executor_amendment_sha_mismatch")
 if amendment.get("base_protocol_sha256")!=sha_file(PROTOCOL):raise ValueError("amendment_base_protocol_sha_mismatch")
 if amendment.get("effective_implementation_sha256")!=current_impl:raise ValueError("effective_implementation_sha_mismatch")
 if ledger.get("implementation_amendment_sha256")!=sha_file(amendment_path):raise ValueError("ledger_amendment_sha_mismatch")
 if ledger.get("implementation_sha256")!=current_impl:raise ValueError("ledger_implementation_sha_mismatch")
 e=env()
 if e!=protocol["runtime"]:raise ValueError("environment_changed_after_freeze")
 for k in ("RBF_KRR","CARTESIAN_MLP"):
  if ledger["fits"][k]["status"] in ("RUNNING","FAILED"):raise RuntimeError("no_automatic_replay:"+k)
 if ledger["current_task_real_fits_started"]>2:raise ValueError("fit_budget_exceeded")
 if ledger["status"]=="COMPLETE":print("COMPLETE_NO_REFIT");return
 schema_result=schema_adapter_test()
 print("SCHEMA_ADAPTER_TEST",json.dumps(schema_result,sort_keys=True))
 by,xtr,ytr,xv,yv=load_data(split)
 if (xtr.shape,ytr.shape,xv.shape,yv.shape)!=((52,6),(52,609),(13,6),(13,609)):raise ValueError("split_shapes")
 ds=readj(DATASET)
 rb=hashlib.sha256(canon({"old32_npz_sha256":ds["old32"]["dataset_sha256"],
  "new33_label_hashes":{x["case_id"]:x["label_npz_sha256"] for x in ds["new33"]["cases"]},
  "combined_snapshot_sha256":ds["combined_snapshot_sha256"]})).hexdigest()
 if rb!=protocol["response_bundle_sha256"]:raise ValueError("response_bundle_sha")
 from scripts.coupling_ml.k6_v2_pipeline import training as T,h1
 ts=tasks(split["training_case_ids"],split["validation_case_ids"]);runs={}
 for kind in ("RBF_KRR","CARTESIAN_MLP"):
  task=ts[kind];slot=ledger["fits"][kind]
  if task.fingerprint()!=slot["task_sha256"]:raise ValueError("task_sha:"+kind)
  if slot["status"]=="COMPLETE":
   fit=T._load_cached_fit(task,TASK/"fit_artifacts"/kind,rb)
   if fit is None:raise RuntimeError("completed_fit_missing:"+kind)
   runs[kind]=fit;continue
  if slot["status"]!="NOT_STARTED" or ledger["current_task_real_fits_started"]>=2:raise RuntimeError("fit_slot_not_startable:"+kind)
  ledger["status"]="IN_PROGRESS";ledger["current_task_real_fits_started"]+=1
  if kind=="RBF_KRR":ledger["current_task_krr_fits_started"]+=1
  else:ledger["current_task_mlp_fits_started"]+=1
  slot["status"]="RUNNING";slot["started_at_utc"]=utc();writej(LEDGER,ledger)
  out=TASK/"fit_artifacts"/kind;checkpoint=out/"progress.pt" if kind=="CARTESIAN_MLP" else None
  try:
   if kind=="CARTESIAN_MLP":
    import torch;torch.set_num_threads(1)
   fit=T._fit_arrays_impl(task,xtr,ytr,X_validation=xv,Y_validation=yv,X_prediction=xv,
    prediction_case_ids=split["validation_case_ids"],device="cpu",
    run_purpose=T.PARTIAL_DEVELOPMENT_DIAGNOSTIC,checkpoint_path=checkpoint,
    _partial_development_diagnostic_authority=T._PARTIAL_DEVELOPMENT_DIAGNOSTIC_AUTHORITY)
   T._save_fit_run(fit,out,rb)
   loaded=T._load_cached_fit(task,out,rb)
   if loaded is None:raise RuntimeError("reload_missing:"+kind)
   c2,p2=T.predict_fit_run(loaded,xv)
   if not(np.allclose(c2,fit.predicted_c_hat,rtol=1e-12,atol=1e-12) and np.allclose(p2,fit.predicted_p_scale,rtol=1e-12,atol=1e-12)):raise RuntimeError("reload_parity:"+kind)
   slot.update({"status":"COMPLETE","completed_at_utc":utc(),"input_sha256":fit.input_sha256,
    "fit_manifest_sha256":sha_file(out/"fit_manifest.json"),"fit_joblib_sha256":sha_file(out/"fit.joblib"),
    "prediction_sha256":sha_file(out/"predictions.npz"),"actual_updates":fit.actual_updates,
    "best_update":fit.best_update,"training_loss":fit.training_loss,"validation_loss":fit.validation_loss,
    "reload_max_abs_c_hat_delta":float(np.max(np.abs(c2-fit.predicted_c_hat))),
    "reload_max_abs_p_scale_delta":float(np.max(np.abs(p2-fit.predicted_p_scale))),"device":"cpu"})
   ledger["current_task_real_fits_completed"]+=1;writej(LEDGER,ledger);runs[kind]=fit
   print("FIT_DONE",kind,"updates",fit.actual_updates,"best",fit.best_update,"train",fit.training_loss,"val",fit.validation_loss)
  except BaseException as ex:
   slot.update({"status":"FAILED","failed_at_utc":utc(),"failure_type":type(ex).__name__,"failure_message":str(ex)[:1000]})
   ledger["status"]="FAILED_NO_REPLAY";writej(LEDGER,ledger);raise
 ctrue=np.stack([by[c].c_hat for c in split["validation_case_ids"]])
 ptrue=np.stack([by[c].p_scale for c in split["validation_case_ids"]])
 etrue=np.stack([by[c].eta for c in split["validation_case_ids"]])
 atrue=np.stack([by[c].absolute_order for c in split["validation_case_ids"]])
 decoder=h1.load_h2_decoder();metrics={}
 for kind,fit in runs.items():
  m=safe(h1.evaluate_original_h1(ctrue,fit.predicted_c_hat[None,...],ptrue,fit.predicted_p_scale[None,...],etrue,atrue,decoder))
  metrics[kind]=m
  writej(TASK/"fit_artifacts"/kind/"H1_DIAGNOSTIC_V1.json",{"schema":"COUPLING_ML_PARTIAL_DIAGNOSTIC_H1_V1",
   "scope":"development-only 13-geometry validation; not confirmation or admission",
   "case_ids":split["validation_case_ids"],"seed_stability":"not_estimable","original_h1":m})
 result={"schema":"COUPLING_ML_PARTIAL_DEVELOPMENT_DIAG_RESULT_V1","status":"COMPLETE_ENGINEERING_DIAGNOSTIC",
  "protocol_sha256":sha_file(PROTOCOL),"split_sha256":sha_file(SPLIT),"config_sha256":sha_file(CONFIG),
  "dataset_manifest_sha256":sha_file(DATASET),"response_bundle_sha256":rb,"runtime":env(),
  "training_geometry_count":52,"validation_geometry_count":13,"all_21_wavelengths_grouped":True,
  "training_case_ids":split["training_case_ids"],"validation_case_ids":split["validation_case_ids"],
  "solver_entries":0,"new_fsps":0,"confirmation_response_access":0,"standalone_p_scale_fits":0,
  "automatic_replay":0,"prior_real32_diagnostic_fits_preserved":2,"current_task_real_fits":2,
  "models":{k:{"task_id":r.task.task_id,"input_sha256":r.input_sha256,"training_loss":r.training_loss,
   "validation_loss":r.validation_loss,"actual_updates":r.actual_updates,"best_update":r.best_update,
   "C_hat_shape":list(r.predicted_c_hat.shape),"P_scale_shape":list(r.predicted_p_scale.shape),
   "P_scale_strictly_positive_finite":bool(np.isfinite(r.predicted_p_scale).all() and (r.predicted_p_scale>0).all()),
   "original_h1_diagnostic":metrics[k]} for k,r in runs.items()},
  "production_admission":False,"independent_confirmation":False}
 writej(TASK/"RESULT_V1.json",safe(result))
 ledger["status"]="COMPLETE";ledger["completed_at_utc"]=utc();writej(LEDGER,ledger)
 envrec=readj(ENVFILE);envrec["after_fit"]=env();envrec["environment_mutated"]=False
 envrec["dependency_installations"]=0;writej(ENVFILE,envrec)
 p=TASK/"CONTINUATION.md";p.write_text(p.read_text(encoding="utf-8")+
  "\n\n## Completed diagnostic fits\nCompleted UTC: "+utc()+
  "\nKRR=1 and MLP=1; current task total=2/2. Prior REAL32 fits=2 remain separately recorded. "
  "Solver=0; confirmation access=0; standalone P_scale fits=0; automatic replay=0. "
  "See RESULT_V1.json, FIT_LEDGER_V1.json, and fit_artifacts. Development-only, no admission.\n",encoding="utf-8")
 print("RESULT_SHA256",sha_file(TASK/"RESULT_V1.json"))
 print("LEDGER",json.dumps({k:ledger[k] for k in ["status","current_task_real_fits_started","current_task_real_fits_completed","solver_entries","p_scale_only_fits","confirmation_response_access","automatic_replay"]},sort_keys=True))

if __name__=="__main__":
 os.chdir(ROOT)
 sys.path.insert(0,str(ROOT))
 parser=argparse.ArgumentParser()
 parser.add_argument("--prepare",action="store_true")
 parser.add_argument("--run",action="store_true")
 args=parser.parse_args()
 if args.prepare==args.run: raise SystemExit("choose exactly one of --prepare or --run")
 prepare() if args.prepare else run()


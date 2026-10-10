"""Read-only first-entry scientific audit. Never launches or recovers a solver."""
import hashlib,json,pathlib,sqlite3,sys,time
import numpy as np
import h5py

RUNTIME=pathlib.Path(r"D:\apcd_runtime\gpu_platform_v2_serial_production_v1")
ROOT=pathlib.Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
BINDING=RUNTIME/"science_releases/G027_attempt001_20261010_recovery1/BINDING.json"
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open("rb") as f:
  for v in iter(lambda:f.read(1<<20),b""):h.update(v)
 return h.hexdigest()
def audit():
 b=json.loads(BINDING.read_text(encoding="utf-8"))
 sys.path.insert(0,str(RUNTIME/"releases"/b["code_head"]/"platform_v2"))
 from apcd_gpu_v2.artifacts import bundle_inventory
 from apcd_gpu_v2.serial import SerialConfig,SerialRequest
 cfg=SerialConfig.model_validate_json(pathlib.Path(b["configuration_path"]).read_text(encoding="utf-8"))
 request=SerialRequest.model_validate_json(json.dumps(json.loads(pathlib.Path(b["requests_path"]).read_text(encoding="utf-8"))[0]))
 db=sqlite3.connect("file:"+str(RUNTIME/"ledger.sqlite3")+"?mode=ro",uri=True);db.row_factory=sqlite3.Row
 tasks=[dict(x) for x in db.execute("select * from tasks")]
 slot=dict(db.execute("select * from slot").fetchone())
 events=[dict(x) for x in db.execute("select * from events where kind!='HEARTBEAT' order by seq")];db.close()
 assert len(tasks)==1 and tasks[0]["case_id"]==request.case_id
 task=tasks[0]
 ledgerpath=pathlib.Path(cfg.coupling_ledger)
 l=json.loads(ledgerpath.read_text(encoding="utf-8"));rec=l["case_records"][request.case_id]
 counts={k:l[k] for k in ["entered_count","truth_valid_count","labels_valid_count","remaining_unentered_count","training_fits","p_scale_fits","confirmation_response_access_count","automatic_replay_count"]}
 engines={}
 for e in events:
  if e["kind"]=="ENGINE_PROCESS":
   p=json.loads(e["payload"]);engines[(p["pid"],p["creation_time"])]=dict(pid=p["pid"],creation_time=p["creation_time"],executable=p["executable"],ppid=p["ppid"],working_directory=p["working_directory"],command_sha256=hashlib.sha256(json.dumps(p["command"]).encode()).hexdigest(),gpu_argument_present="-gpu" in p["command"])
 result=dict(schema="APCD_COUPLING_G027_FIRST_ENTRY_AUDIT_V1",observed_unix=time.time(),case_id=request.case_id,attempt_id=request.attempt_id,code_head=b["code_head"],binding_sha256=sha(BINDING),release_sha256=b["release_sha256"],request_digest=request.request_sha256,admission_digest=request.admission_sha256,counts=counts,sqlite_state=task["state"],coupling_phase=rec["phase"],entered=task["entered"],slot_clear=slot["token"] is None,engines=list(engines.values()),g028_unentered="K6GDP2_DEV_G028" in l["remaining_unentered_case_ids"],event_index=[dict(seq=e["seq"],time=e["utc_unix"],kind=e["kind"],payload_sha256=hashlib.sha256(e["payload"].encode()).hexdigest()) for e in events],ledger_sha256=sha(ledgerpath),no_replay=counts["automatic_replay_count"]==0,no_training=counts["training_fits"]==counts["p_scale_fits"]==0,no_confirmation_access=counts["confirmation_response_access_count"]==0)
 if task["state"]!="TRUTH_VALID":
  result.update(status="PARTIAL",error=task["error"]);return result
 assert task["entered"]==1 and rec["phase"]=="V2_TRUTH_VALID" and engines and result["slot_clear"]
 evidence=json.loads(task["bundle"]);assert rec["evidence"]["bundle"]==evidence["bundle"]
 bundle=evidence["bundle"];p=pathlib.Path(bundle["path"])
 assert bundle_inventory(p/"run.fsp",cfg.native_h5_name)==bundle["files"]
 assert sha(p/"bundle_receipt.json")==bundle["receipt_sha256"]
 validation=evidence["validation"];assert validation["verdict"]=="PASS" and validation["outputs"]==609 and validation["fresh_load_verified"] and validation["actual_importer"]=="load_verified_runner_case"
 for d in validation["record"].values():
  if isinstance(d,dict) and "path" in d and "sha256" in d:assert sha(d["path"])==d["sha256"]
 assert sha(validation["labels_artifact"]["path"])==validation["labels_artifact"]["sha256"]
 with h5py.File(p/"run"/cfg.native_h5_name,"r") as h:
  native={g:{n:dict(shape=list(h[g][n].shape),dtype=str(h[g][n].dtype)) for n in ["Ex","Ey","Ez","Hx","Hy","Hz"]} for g in h if g.startswith("Monitor") and isinstance(h[g],h5py.Group)}
 label=pathlib.Path(cfg.coupling_ledger).parent/("INGESTED_TRUTH_"+request.case_id+"_V1.npz")
 with np.load(label,allow_pickle=False) as v:
  c=v["C_hat_real"]+1j*v["C_hat_imag"];ps=v["P_scale"];eta=v["eta"];power=v["absolute_order"]
  assert c.shape==(21,7,2) and ps.shape==(21,) and np.isfinite(c).all() and np.isfinite(ps).all() and (ps>0).all()
  assert np.array_equal(v["wavelengths_nm"],np.arange(440,461)) and np.array_equal(v["order_m"],np.arange(-3,4))
  assert np.array_equal(v["polarization"],np.array(["TE","TM"]))
  labelcheck=dict(outputs=int(c.size*2+ps.size),shape=list(c.shape),p_scale_min=float(ps.min()),p_scale_max=float(ps.max()),eta_sum_max_error=float(np.abs(eta.sum(axis=1)-1).max()),absolute_power_closure_max_error=float(np.abs(power.sum(axis=1)-ps).max()))
 assert l["truth_valid_case_ids"]==l["labels_valid_case_ids"] or set(l["truth_valid_case_ids"])==set(l["labels_valid_case_ids"])
 returns=[e for e in events if e["request_sha"]==request.request_sha256 and e["kind"]=="PROCESS_RETURNED"];assert len(returns)==1
 launch=[e for e in events if e["request_sha"]==request.request_sha256 and e["kind"]=="LAUNCHER_PROCESS"];assert len(launch)==1
 finish=[e for e in events if e["request_sha"]==request.request_sha256 and e["kind"]=="TRUTH_VALID"];assert len(finish)==1
 returned=json.loads(returns[0]["payload"]);assert returned["returncode"]==0
 result.update(status="PASS",native_bundle=bundle,native_eh=native,labelcheck=labelcheck,labels=dict(path=str(label),sha256=sha(label)),validation=validation,launcher_wall_seconds=returns[0]["utc_unix"]-launch[0]["utc_unix"],engine_to_process_return_seconds=returns[0]["utc_unix"]-min(e["utc_unix"] for e in events if e["request_sha"]==request.request_sha256 and e["kind"]=="ENGINE_PROCESS"),end_to_end_seconds=finish[0]["utc_unix"]-next(e["utc_unix"] for e in events if e["request_sha"]==request.request_sha256 and e["kind"]=="CLAIMED"),one_launch=True)
 return result
if __name__=="__main__":
 print(json.dumps(audit(),sort_keys=True,indent=2))

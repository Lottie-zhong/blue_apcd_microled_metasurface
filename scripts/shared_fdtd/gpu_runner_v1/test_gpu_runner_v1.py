# -*- coding: utf-8 -*-
"""Offline tests: injected callbacks only, no Lumerical or solver process."""
import hashlib,json,sys,tempfile,unittest,unittest.mock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runner import CONTRACT_SHA256,EXPANSION_SHA256,RunnerError,atomic_json,run_one

# Historical-case values are fixtures only; production geometry comes from Coupling authority.
GEOMETRIES = {"K6V1_S35": [110,145,225,105,185,215],
              "K6V1_S39": [175,100,125,120,100,230]}
from adapter import NativeAdapter
import runner as runner_module

class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name)
  self.pre=self.base/"approved.fsp"; self.pre.write_bytes(b"fixture FSP")
  self.m={"case_id":"K6V1_S35","attempt_id":"attempt_001","run_id":"run-s35-001",
   "geometry":GEOMETRIES["K6V1_S35"],"physical_contract_sha256":CONTRACT_SHA256,
   "expansion_manifest_sha256":EXPANSION_SHA256,"pre_fsp_path":str(self.pre),
   "pre_fsp_sha256":hashlib.sha256(b"fixture FSP").hexdigest()}
  self.root=self.base/"runner"; self.gpu=lambda:{"free_mib":8192,"processes":[]}
  self.owner=lambda _r:False
  self.truth=lambda _m,_d:{"fresh_load_verified":True,"monitors_valid":True,
   "state_valid":True,"scientific_valid":True}
 def tearDown(self): self.tmp.cleanup()

 def _seed_s35_predecessor(self,root,with_recovery=True):
  run_id=runner_module.S35_RECOVERY_RUN_ID
  run_dir=root/"runs/K6V1_S35/attempt_001"/run_id
  run_dir.mkdir(parents=True)
  original_manifest={"case_id":"K6V1_S35","attempt_id":"attempt_001","run_id":run_id,
   "geometry":GEOMETRIES["K6V1_S35"],"physical_contract_sha256":CONTRACT_SHA256,
   "expansion_manifest_sha256":EXPANSION_SHA256,"pre_fsp_path":str(self.pre),
   "pre_fsp_sha256":hashlib.sha256(self.pre.read_bytes()).hexdigest()}
  atomic_json(run_dir/"manifest.json",original_manifest)
  original_status={"schema":"APCD_GPU_RUN_STATUS_V1","case_id":"K6V1_S35",
   "attempt_id":"attempt_001","run_id":run_id,"state":"FAILED_POSTENTRY",
   "failure":"No module named 'mdc_tmm_complex_incident_power_v1'",
   "solver_entered":True,"solver_invocations":1}
  atomic_json(run_dir/"status.json",original_status)
  row={"case_id":"K6V1_S35","attempt_id":"attempt_001","run_id":run_id,
       "state":"FAILED_POSTENTRY","run_dir":str(run_dir)}
  atomic_json(root/"registry.json",{"schema":"APCD_GPU_RUNNER_REGISTRY_V1","runs":[row]})
  status_sha=runner_module.sha256_file(run_dir/"status.json")
  if not with_recovery:
   return {"original":status_sha}
  recovery=root/runner_module.S35_RECOVERY_RELATIVE
  recovery.mkdir(parents=True)
  truth=recovery/"truth.h5"; truth.write_bytes(b"pinned test truth")
  truth_sha=runner_module.sha256_file(truth)
  required=runner_module.S35_RECOVERY_REQUIRED_CHECKS
  validation={"schema":"APCD_GPU_RUNNER_V1_POSTENTRY_TRUTH_RECOVERY_VALIDATION_V1",
   "case_id":"K6V1_S35","attempt_id":"attempt_001","run_id":run_id,"result":"PASS",
   "checks":{name:True for name in required},
   "fresh_load_validation":{"fresh_load_verified":True,"monitors_valid":True,
    "state_valid":True,"scientific_valid":True,"max_energy_closure":1e-12,
    "truth_h5_sha256":truth_sha},"truth_h5_sha256":truth_sha}
  validation_path=recovery/"validation.json"; atomic_json(validation_path,validation)
  validation_sha=runner_module.sha256_file(validation_path)
  recovery_status={"schema":"APCD_GPU_RUNNER_V1_POSTENTRY_RECOVERY_STATUS_V1",
   "case_id":"K6V1_S35","attempt_id":"attempt_001","run_id":run_id,
   "recovery_state":"LOAD_ONLY_POSTENTRY_TRUTH_RECOVERY","scientific_truth_status":"TRUTH_VALID",
   "original_status_preserved":True,"solver_invocations_before":1,"solver_invocations_after":1,
   "replay_count":0,"solver_run_called_during_recovery":False,
   "truth_h5_sha256":truth_sha,"validation_sha256":validation_sha}
  rs_path=recovery/"recovery_status.json"; atomic_json(rs_path,recovery_status)
  records={}
  for path in (truth,validation_path,rs_path):
   records[str(path)]={"sha256":runner_module.sha256_file(path),"size_bytes":path.stat().st_size}
  hashes={"schema":"APCD_GPU_RUNNER_V1_POSTENTRY_TRUTH_RECOVERY_HASHES_V1",
   "run_id":run_id,"recovery_artifacts":records,
   "original_artifacts":{"original_status":{"sha256":status_sha,
    "size_bytes":(run_dir/"status.json").stat().st_size}}}
  hashes_path=recovery/"hashes.json"; atomic_json(hashes_path,hashes)
  return {"original":status_sha,"truth":truth_sha,"validation":validation_sha,
          "hashes":runner_module.sha256_file(hashes_path)}
 def _seed_entered_attempt(self,root,manifest,registry_state=None):
  run_dir=root/"runs"/manifest["case_id"]/manifest["attempt_id"]/manifest["run_id"]
  run_dir.mkdir(parents=True)
  atomic_json(run_dir/"manifest.json",manifest)
  atomic_json(run_dir/"status.json",{"schema":"APCD_GPU_RUN_STATUS_V1",
   "case_id":manifest["case_id"],"attempt_id":manifest["attempt_id"],
   "run_id":manifest["run_id"],"state":"SOLVER_ENTERED",
   "solver_entered":True,"solver_invocations":1})
  if registry_state is not None:
   row={k:manifest[k] for k in ("case_id","attempt_id","run_id")}
   row.update(state=registry_state,run_dir=str(run_dir))
   atomic_json(root/"registry.json",{"schema":"APCD_GPU_RUNNER_REGISTRY_V1","runs":[row]})

 def test_crash_window_new_run_id_cannot_relaunch(self):
  self._seed_entered_attempt(self.root,self.m,"PRECHECK_PASS")
  retry=dict(self.m,run_id="new-run-after-crash"); calls=[]
  with self.assertRaisesRegex(RunnerError,"POST_ENTRY_REPLAY_FORBIDDEN"):
   run_one(retry,self.root,lambda *_:calls.append(1),self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[])
  rows=json.loads((self.root/"registry.json").read_text())["runs"]
  self.assertEqual(rows[0]["state"],"SOLVER_ENTERED")

 def test_registry_rebuilt_from_entered_run_directory(self):
  self._seed_entered_attempt(self.root,self.m)
  self.assertFalse((self.root/"registry.json").exists())
  retry=dict(self.m,run_id="reconstructed-run"); calls=[]
  with self.assertRaisesRegex(RunnerError,"POST_ENTRY_REPLAY_FORBIDDEN"):
   run_one(retry,self.root,lambda *_:calls.append(1),self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[])
  rows=json.loads((self.root/"registry.json").read_text())["runs"]
  self.assertEqual(rows[0]["state"],"SOLVER_ENTERED")

 def test_entry_barrier_truth_before_done(self):
  calls=[]
  def solver(_m,d):
   calls.append(1); state=json.loads((d/"status.json").read_text())
   self.assertEqual(state["state"],"SOLVER_ENTERED"); self.assertEqual(state["solver_invocations"],1)
   (d/"truth.h5").write_bytes(b"fixture truth")
  result=run_one(self.m,self.root,solver,self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[1]); self.assertEqual(result["status"]["state"],"DONE")
  self.assertTrue((Path(result["run_dir"])/"hashes.json").is_file())
  self.assertFalse((self.root/"active_run.json").exists())
 def test_truth_bundle_created_by_fresh_load_validator_before_truth_gate(self):
  calls=[]
  def solver(_manifest,run_dir):
   calls.append("solver")
   self.assertFalse((run_dir/"truth.h5").exists())
  def validator(_manifest,run_dir):
   self.assertFalse((run_dir/"truth.h5").exists())
   (run_dir/"truth.h5").write_bytes(b"fresh-load truth")
   return {"fresh_load_verified":True,"monitors_valid":True,
           "state_valid":True,"scientific_valid":True}
  result=run_one(self.m,self.root,solver,validator,self.gpu,self.owner)
  self.assertEqual(calls,["solver"])
  self.assertEqual(result["status"]["state"],"DONE")
  self.assertEqual(result["status"]["solver_invocations"],1)
 def test_input_hash_and_capacity_wait_stays_pending_and_resumes_same_run(self):
  calls=[]; bad=dict(self.m,pre_fsp_sha256="0"*64)
  with self.assertRaisesRegex(RunnerError,"PRE_FSP_HASH_MISMATCH"):
   run_one(bad,self.root,lambda *_:calls.append("bad"),self.truth,self.gpu,self.owner)
  low=self.base/"low"
  waiting=dict(self.m,run_id="low-run")
  result=run_one(waiting,low,lambda *_:calls.append("unexpected"),self.truth,
   lambda:{"free_mib":1368,"processes":[]},self.owner)
  self.assertEqual(result["result"],"WAIT_GPU_CAPACITY")
  self.assertEqual(result["result_classification"],"NON_SCIENTIFIC_CAPACITY_WAIT")
  self.assertFalse(result["solver_entered"])
  self.assertEqual(result["solver_invocations"],0)
  status_path=low/"runs/K6V1_S35/attempt_001/low-run/status.json"
  status=json.loads(status_path.read_text())
  self.assertEqual(status["state"],"PENDING")
  self.assertFalse(status["solver_entered"])
  self.assertEqual(status["solver_invocations"],0)
  self.assertEqual(status["capacity_wait_reason"],"INSUFFICIENT_OR_UNKNOWN_GPU_HEADROOM")
  self.assertFalse((status_path.parent/"run.fsp").exists())
  rows=json.loads((low/"registry.json").read_text())["runs"]
  self.assertEqual(rows[0]["state"],"PENDING")
  with self.assertRaisesRegex(RunnerError,"PENDING_RUN_ID_CONFLICT"):
   run_one(dict(waiting,run_id="different-run"),low,lambda *_:calls.append("bypass"),
    self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[])
  def resume_solver(_m,run_dir):
   calls.append("resumed")
   (run_dir/"truth.h5").write_bytes(b"fixture truth")
  resumed=run_one(waiting,low,resume_solver,self.truth,self.gpu,self.owner)
  self.assertEqual(resumed["status"]["state"],"DONE")
  self.assertEqual(calls,["resumed"])
 def test_postentry_failure_never_replays(self):
  calls=[]
  def crash(*_): calls.append(1); raise RuntimeError("synthetic crash")
  with self.assertRaisesRegex(RunnerError,"synthetic crash"):
   run_one(self.m,self.root,crash,self.truth,self.gpu,self.owner)
  p=self.root/"runs/K6V1_S35/attempt_001/run-s35-001/status.json"
  self.assertEqual(json.loads(p.read_text())["state"],"FAILED_POSTENTRY")
  with self.assertRaisesRegex(RunnerError,"DUPLICATE_RUN_ID"):
   run_one(self.m,self.root,crash,self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[1])
 def test_lock_and_s39_order(self):
  calls=[]; second=dict(self.m,run_id="second-run")
  def solver(_m,d):
   with self.assertRaisesRegex(RunnerError,"RUNNER_LOCKED"):
    run_one(second,self.root,lambda *_:calls.append(1),self.truth,self.gpu,self.owner)
   (d/"truth.h5").write_bytes(b"fixture truth")
  s39=dict(self.m,case_id="K6V1_S39",run_id="s39-run",geometry=GEOMETRIES["K6V1_S39"])
  with self.assertRaisesRegex(RunnerError,"S39_REQUIRES_S35_DONE"):
   run_one(s39,self.root,lambda *_:calls.append(1),self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[])
  run_one(self.m,self.root,solver,self.truth,self.gpu,self.owner)
  def solver39(_m,d):
   calls.append("S39"); (d/"truth.h5").write_bytes(b"fixture truth")
  result=run_one(s39,self.root,solver39,self.truth,self.gpu,self.owner)
  self.assertEqual(result["status"]["state"],"DONE")
  self.assertEqual(calls,["S39"])

 def test_manifest_hashes_and_geometry_order_reject_before_runner_creation(self):
  bad_cases = [
   (dict(self.m,geometry=[0,*self.m["geometry"][1:]]),"GEOMETRY_MISMATCH"),
   (dict(self.m,physical_contract_sha256="0"*64),"PHYSICAL_CONTRACT_HASH_MISMATCH"),
   (dict(self.m,expansion_manifest_sha256="0"*64),"EXPANSION_MANIFEST_HASH_MISMATCH"),
  ]
  calls=[]
  for manifest,reason in bad_cases:
   with self.subTest(reason=reason), self.assertRaisesRegex(RunnerError,reason):
    run_one(manifest,self.root,lambda *_:calls.append(1),self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[])
  self.assertFalse(self.root.exists())

 def test_active_marker_identity_corruption_fails_preentry(self):
  calls=[]
  original_atomic_json=runner_module.atomic_json
  def corrupt_active_marker(path,obj):
   original_atomic_json(path,obj)
   path=Path(path)
   if path.name=="active_run.json" and obj.get("state")=="PRECHECK_PASS":
    original_atomic_json(path,dict(obj,attempt_id="tampered-attempt"))
  runner_module.atomic_json=corrupt_active_marker
  try:
   with self.assertRaisesRegex(RunnerError,"ACTIVE_RUN_OWNERSHIP_MISMATCH"):
    run_one(self.m,self.root,lambda *_:calls.append(1),self.truth,self.gpu,self.owner)
  finally:
   runner_module.atomic_json=original_atomic_json
  run_dir=self.root/"runs/K6V1_S35/attempt_001/run-s35-001"
  status=json.loads((run_dir/"status.json").read_text())
  self.assertEqual(status["state"],"FAILED_PREENTRY")
  self.assertFalse(status["solver_entered"])
  self.assertEqual(status["solver_invocations"],0)
  self.assertEqual(calls,[])
  self.assertFalse((self.root/"active_run.json").exists())
  self.assertFalse((self.root/".runner.lock").exists())

 def test_active_run_marker_blocks_before_solver_entry(self):
  self.root.mkdir(parents=True)
  marker={"run_id":"another-run","state":"SOLVER_ENTERED"}
  atomic_json(self.root/"active_run.json",marker)
  calls=[]
  with self.assertRaisesRegex(RunnerError,"ACTIVE_RUN_PRESENT"):
   run_one(self.m,self.root,lambda *_:calls.append(1),self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[])
  self.assertEqual(json.loads((self.root/"active_run.json").read_text()),marker)
  self.assertFalse((self.root/".runner.lock").exists())

 def test_legacy_v3_database_and_external_inputs_are_unchanged(self):
  import sqlite3
  legacy_db=self.base/"legacy_v3_control.sqlite3"
  con=sqlite3.connect(legacy_db)
  try:
   con.execute("CREATE TABLE sentinel(value TEXT)")
   con.execute("INSERT INTO sentinel VALUES('unchanged')")
   con.commit()
  finally:
   con.close()
  db_hash=hashlib.sha256(legacy_db.read_bytes()).hexdigest()
  pre_hash=hashlib.sha256(self.pre.read_bytes()).hexdigest()
  def solver(_m,run_dir):
   (run_dir/"truth.h5").write_bytes(b"fixture truth")
   return {"test":"zero_solver_fixture"}
  result=run_one(self.m,self.root,solver,self.truth,self.gpu,self.owner)
  run_dir=Path(result["run_dir"]).resolve()
  self.assertTrue(run_dir.is_relative_to(self.root.resolve()))
  self.assertEqual(hashlib.sha256(legacy_db.read_bytes()).hexdigest(),db_hash)
  self.assertEqual(hashlib.sha256(self.pre.read_bytes()).hexdigest(),pre_hash)
  self.assertTrue(all(p.resolve().is_relative_to(self.root.resolve()) for p in self.root.rglob("*")))
  self.assertFalse((self.root/"active_run.json").exists())


 def test_s39_accepts_only_hash_pinned_recovered_s35_without_solver_entry(self):
  pins=self._seed_s35_predecessor(self.root)
  s39=dict(self.m,case_id="K6V1_S39",geometry=GEOMETRIES["K6V1_S39"],
           run_id="s39-capacity-check",attempt_id="attempt_001")
  calls=[]
  with unittest.mock.patch.object(runner_module,"S35_ORIGINAL_STATUS_SHA256",pins["original"]):
   with unittest.mock.patch.object(runner_module,"S35_RECOVERY_PINS",
       {"truth_h5":pins["truth"],"validation":pins["validation"],"hashes":pins["hashes"]}):
    result=run_one(s39,self.root,lambda *_:calls.append("solver"),self.truth,
       lambda:{"free_mib":0},self.owner)
  self.assertEqual(result["result"],"WAIT_GPU_CAPACITY")
  self.assertEqual(calls,[])
  status=json.loads((Path(result["run_dir"])/"status.json").read_text())
  self.assertEqual(status["s35_predecessor"]["effective_scientific_outcome"],"RECOVERED_TRUTH_VALID")
  self.assertEqual(status["solver_invocations"],0)

 def test_plain_failed_postentry_s35_without_recovery_blocks_s39_before_solver(self):
  self._seed_s35_predecessor(self.root,with_recovery=False)
  s39=dict(self.m,case_id="K6V1_S39",geometry=GEOMETRIES["K6V1_S39"],
           run_id="s39-no-recovery",attempt_id="attempt_001")
  calls=[]
  with self.assertRaisesRegex(RunnerError,"S39_REQUIRES_S35_DONE"):
   run_one(s39,self.root,lambda *_:calls.append("solver"),self.truth,self.gpu,self.owner)
  self.assertEqual(calls,[])
  self.assertFalse((self.root/"runs/K6V1_S39/attempt_001/s39-no-recovery").exists())

 def test_recovered_s35_missing_historical_lineage_does_not_block_idle_owner_probe(self):
  pins=self._seed_s35_predecessor(self.root)
  self.assertFalse((self.root/".runner.lock").exists())
  self.assertFalse((self.root/"active_run.json").exists())
  with unittest.mock.patch.object(runner_module,"S35_ORIGINAL_STATUS_SHA256",pins["original"]):
   with unittest.mock.patch.object(runner_module,"S35_RECOVERY_PINS",
       {"truth_h5":pins["truth"],"validation":pins["validation"],"hashes":pins["hashes"]}):
    self.assertFalse(NativeAdapter.runner_owner_probe(self.root))
  original=json.loads((self.root/"runs/K6V1_S35/attempt_001"/
      runner_module.S35_RECOVERY_RUN_ID/"status.json").read_text())
  self.assertNotIn("solver_process_lineage",original)

if __name__=="__main__": unittest.main(verbosity=2)

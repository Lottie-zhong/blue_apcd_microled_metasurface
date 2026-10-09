import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from adapter import NativeAdapter
from postentry_failure_closeout_v1 import (
    create_postentry_failure_closeout, validate_postentry_failure_closeout,
)

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()

class GenericCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name); self.root=self.base/"runner"
        self.case="K6GDP2_DEV_G999"; self.attempt="attempt_001"; self.run="run-123"; self.rid="request-123"
        self.run_dir=self.root/"runs"/self.case/self.attempt/self.run; self.run_dir.mkdir(parents=True)
        self.req=self.root/"requests"/"scheduled_run_one_v1"/self.rid; self.req.mkdir(parents=True)
        fsp=self.run_dir/"run.fsp"; fsp.write_bytes(b"pre-entry FSP")
        pre=hashlib.sha256(fsp.read_bytes()).hexdigest()
        self.status={"schema":"APCD_GPU_RUN_STATUS_V1","case_id":self.case,"attempt_id":self.attempt,
                     "run_id":self.run,"state":"FAILED_POSTENTRY","solver_entered":True,
                     "solver_invocations":1,"pre_fsp_sha256":pre,"failure":"RunnerError:LICENSE_STARTUP_FAILED"}
        write_json(self.run_dir/"status.json",self.status)
        write_json(self.run_dir/"manifest.json",{"case_id":self.case,"attempt_id":self.attempt,"run_id":self.run,"pre_fsp_sha256":pre})
        write_json(self.run_dir/"failure_exception_v1.json",{"case_id":self.case,"attempt_id":self.attempt,"run_id":self.run,"solver_entered":True,"solver_invocations":1,"exception_type":"RunnerError","exception":"LICENSE_STARTUP_FAILED"})
        write_json(self.run_dir/"validation.json",{"state":"PENDING"});write_json(self.run_dir/"hashes.json",{"state":"PENDING"})
        write_json(self.req/"request.json",{"request_id":self.rid,"request_sha256":"request-hash","identity":{"case_id":self.case,"attempt_id":self.attempt,"run_id":self.run}})
        write_json(self.req/"result.json",{"request_id":self.rid,"request_sha256":"request-hash","state":"TERMINAL","exit_code":2,"solver_entered":True,"solver_invocations":1,"run_status":{"case_id":self.case,"attempt_id":self.attempt,"run_id":self.run,"state":"FAILED_POSTENTRY","solver_entered":True,"solver_invocations":1}})
        write_json(self.req/"worker_claim.json",{"request_id":self.rid,"request_sha256":"request-hash"})
        write_json(self.root/"registry.json",{"runs":[{"case_id":self.case,"attempt_id":self.attempt,"run_id":self.run,"state":"FAILED_POSTENTRY","run_dir":str(self.run_dir)}]})
        self.census=self.base/"census.json";write_json(self.census,{"engine_processes":[],"queue_execution_processes":[],"runner_active_processes":[],"related_processes":[],"unattributed_api_processes":[{"pid":7}]})
        self.controller=self.base/"controller.json";write_json(self.controller,{"state":"STOPPED_RECONCILED"})
    def tearDown(self):self.tmp.cleanup()
    def create(self):return create_postentry_failure_closeout(self.root,self.run_dir,self.req,self.census,self.controller,"user-task:GPU_SERIAL_PRODUCTION_RELIABILITY_CLOSEOUT_V1")
    def test_generic_receipt_is_bound_and_consumable(self):
        result=self.create(); status=json.loads((self.run_dir/"status.json").read_text())
        self.assertTrue(validate_postentry_failure_closeout(self.root,self.run_dir/"status.json",status))
        self.assertEqual(result["run_id"],self.run)
    def test_runner_owner_probe_consumes_generic_receipt(self):
        self.create()
        self.assertFalse(NativeAdapter.runner_owner_probe(self.root))
    def test_mutated_evidence_fails_closed(self):
        self.create(); (self.req/"result.json").write_text("{}",encoding="utf-8")
        status=json.loads((self.run_dir/"status.json").read_text())
        self.assertFalse(validate_postentry_failure_closeout(self.root,self.run_dir/"status.json",status))
    def test_active_marker_and_truth_artifact_reject_creation(self):
        (self.root/"active_run.json").write_text("{}",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"ACTIVE_RUNNER_MARKER_PRESENT"):self.create()
        (self.root/"active_run.json").unlink(); (self.run_dir/"truth.h5").write_bytes(b"x")
        with self.assertRaisesRegex(ValueError,"TRUTH_ARTIFACT_PRESENT"):self.create()

if __name__=="__main__":unittest.main()

"""Zero-solver independent resource-policy and native-output contract tests."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

SOURCE=Path(os.environ.get('APCD_RUNNER_TEST_SOURCE',str(Path(__file__).resolve().parents[1]/'minimal_runner_candidate/minimal_batch_runner_v3_1_1.py')))
sys.path.insert(0,str(SOURCE.parent))
spec=importlib.util.spec_from_file_location('shared_runner_test',SOURCE)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
g=r.shared_resource_gate


class SharedPolicyTests(unittest.TestCase):
 def setUp(self):
  self.requirements=dict(gpu_free_mib=4096,ram_free_mib=8192,disk_free_gib=20,cpu_threads=4,license_features={'fdtd_solutions':1,'hpc':8})
  self.policy={'gpu_uuid':'TEST-GPU'}
  sample=dict(gpu_uuid='TEST-GPU',gpu_free_mib=8000,gpu_utilization_pct=0,gpu_apps=[['11','ansysedt.exe'],['12','dwm.exe']],windows=dict(engine_count=100,compute_contexts=[],ram_free_mib=100000,cpu_load_pct=20,cpu_threads=52,legacy_tasks=[dict(enabled=False,running=False)]*3))
  self.evidence=dict(samples=[copy.deepcopy(sample),copy.deepcopy(sample)],disk_free_gib=100,sampled_unix=time.time())
  self.licenses={'fdtd_solutions':10,'hpc':100}
 def check(self):return g.evaluate(self.evidence,self.requirements,self.policy,self.licenses)
 def test_cpu_fdtd_and_edt_graphics_can_coexist(self):
  self.evidence['other_cpu_fdtd_count']=800
  self.assertEqual(self.check(),[])
 def test_zero_utilization_does_not_clear_compute_context(self):
  self.evidence['samples'][0]['windows']['compute_contexts']=[dict(Name='pid_99_engtype_Compute_0',UtilizationPercentage=0)]
  self.assertTrue(any('context' in s for s in self.check()))
 def test_nvidia_attributed_gpu_solver_blocks_even_zero_utilization(self):
  self.evidence['samples'][0]['gpu_apps'].append(['99','fdtd-engine.exe'])
  self.assertTrue(any('process' in s for s in self.check()))
 def test_unknown_gpu_attribution_holds(self):
  self.evidence['samples'][0]['windows']['engine_count']=0
  self.assertTrue(self.check())
 def test_busy_gpu_does_not_pass_as_available_graphics(self):
  self.evidence['samples'][0]['gpu_utilization_pct']=90
  self.assertTrue(self.check())
 def test_missing_cpu_measurement_is_unknown_not_idle(self):
  self.evidence['samples'][0]['windows']['cpu_load_pct']=None
  self.assertTrue(self.check())
 def test_cpu_ram_disk_gpu_shortage_each_holds(self):
  for key in ['gpu_free_mib','ram_free_mib','disk_free_gib','cpu_threads']:
   with self.subTest(key=key):
    old=self.requirements[key];self.requirements[key]=10**9;self.assertTrue(self.check());self.requirements[key]=old
 def test_license_unknown_or_exhausted_holds(self):
  for value in [0,-1]:
   self.licenses['hpc']=value;self.assertTrue(self.check())
 def test_stale_or_single_sample_holds(self):
  self.evidence['sampled_unix']-=120;self.assertTrue(self.check())
  self.evidence['sampled_unix']=time.time();self.evidence['samples'].pop();self.assertTrue(self.check())
 def test_legacy_scheduler_enabled_holds(self):
  self.evidence['samples'][0]['windows']['legacy_tasks'][0]['enabled']=True;self.assertTrue(self.check())
 def test_missing_or_bad_per_job_requirements_holds(self):
  self.assertTrue(g.evaluate(self.evidence,None,self.policy,self.licenses))
  for value in [float('nan'),0,True,'4']:
   self.requirements['cpu_threads']=value;self.assertTrue(self.check())
 def test_monitor_failure_is_not_treated_as_idle(self):
  with patch.object(g,'snapshot',side_effect=RuntimeError('monitor unavailable')):
   with self.assertRaises(RuntimeError):g.check(self.requirements,'.',self.policy)
 def test_license_parser_only_uses_summary_quantities(self):
  with patch.object(g,'command',return_value='Users of hpc:  (Total of 100 licenses issued;  Total of 9 licenses in use)'):
   self.assertEqual(g.license_free(dict(lmutil='test',license_server='test')),{'hpc':91})


class NativeOutputContractTests(unittest.TestCase):
 def test_mock_backend_load_gpu_run_save_close_and_no_layout(self):
  # Synthetic backend, isolated SQLite: does not import/launch real lumapi.
  with tempfile.TemporaryDirectory(prefix='APCD_NATIVE_CONTRACT_MOCK_') as td:
   root=Path(td);source=root/'synthetic.fsp';source.write_bytes(b'NOT_NATIVE_TEST_ONLY')
   runner=r.MinimalBatchRunner(root/'isolated.db',root/'out',root/'mutex.lock')
   manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(batch_name='mock',jobs=[dict(input_fsp=str(source),external_execution_id='platform-mock-only',physical_contract_sha256='a'*64,case_id='mock')])) )
   self.assertTrue(runner.submit_batch(manifest)[0]);calls=[]
   class MockFDTD:
    def __init__(self):calls.append('open')
    def load(self,path):calls.append(('load',Path(path).name))
    def run(self,*args):
     with sqlite3.connect(root/'isolated.db') as con:
      self_entry=con.execute('SELECT solver_entered,pre_fsp_sha256,physical_contract_sha256,case_id FROM solver_entries').fetchone()
     assert self_entry[0]==1 and len(self_entry[1])==64 and self_entry[2]=='a'*64 and self_entry[3]=='mock'
     assert runner.gpu_lock_handle is not None
     calls.append(('run',args))
    def save(self,path):calls.append(('save',Path(path).name));Path(path).write_bytes(b'MOCK_NATIVE_SAVE_CONTRACT_ONLY')
    def close(self):calls.append('close')
   policy=root/'policy.json';policy.write_text(json.dumps(dict(lumapi_path=str(root))))
   with patch.object(r.MinimalBatchRunner,'_require_live_exclusion',return_value={}),patch.object(r,'POLICY_PATH',policy),patch.dict(sys.modules,{'lumapi':types.SimpleNamespace(FDTD=MockFDTD)}):
    self.assertEqual(runner.run_batch('mock'),(1,0))
   self.assertEqual(calls,['open',('load','input.fsp'),('run',('FDTD','GPU')),('save','output.partial.fsp'),'close'])
   job=runner.status_batch('mock')['jobs'][0];folder=Path(job['output_fsp_path']).parent
   self.assertTrue((folder/'manifest.json').exists());self.assertTrue((folder/'runner.log').exists())
   self.assertEqual(r.sha256(folder/'output.fsp'),job['output_sha256'])
   self.assertEqual(runner.run_batch('mock'),(0,0))
 def test_custom_database_cannot_enter_real_solver(self):
  with tempfile.TemporaryDirectory(prefix='APCD_SHARED_GATE_') as td:
   root=Path(td);runner=r.MinimalBatchRunner(root/'test.db',lock_path=root/'lock');runner._acquire_gpu_lock()
   policy=root/'policy.json';policy.write_text(json.dumps(dict(canonical_db=str(root/'canonical.db'))))
   try:
    with patch.object(r,'POLICY_PATH',policy),self.assertRaises(r.ResourceGateError):runner._require_live_exclusion({})
   finally:runner._release_gpu_lock()


if __name__=='__main__':unittest.main(verbosity=2)

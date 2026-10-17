"""Isolated zero-solver tests. No lumapi or scientific FSP is used."""
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(os.environ.get('APCD_RUNNER_TEST_SOURCE', str(Path(__file__).resolve().parents[1] / 'minimal_runner_candidate/minimal_batch_runner_v3_1_1.py')))
sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location('runner_v31_repair', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RunnerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='APCD_V31_ZERO_SOLVER_')
        self.root = Path(self.temp.name)
        self.fsp = self.root/'synthetic.fsp'
        self.fsp.write_bytes(b'FAKE_TEST_FIXTURE_ONLY_NOT_NATIVE_FSP')
        self.digest = hashlib.sha256(self.fsp.read_bytes()).hexdigest()
        self.runner = self.new_runner()

    def tearDown(self):
        self.runner._release_gpu_lock()
        self.temp.cleanup()

    def new_runner(self):
        return module.MinimalBatchRunner(self.root/'isolated.db', self.root/'outputs', self.root/'mutex.lock')

    def manifest(self, name='A', execution='exec-A', **changes):
        job = {'input_fsp':str(self.fsp), 'sha256':self.digest, 'attempt_id':'attempt_001'}
        if execution is not None:
            job['external_execution_id'] = execution
        job.update(changes)
        p=self.root/(name+'.json')
        p.write_text(json.dumps({'batch_name':name,'jobs':[job]}),encoding='utf-8')
        return p

    def submit(self, *args, **kwargs):
        result=self.runner.submit_batch(self.manifest(*args, **kwargs))
        self.assertTrue(result[0],result)

    def rows(self, table):
        with sqlite3.connect(self.root/'isolated.db') as con:
            return con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]

    def child(self, body, *args):
        code='import importlib.util,sys; from pathlib import Path; sys.path.insert(0,str(Path(sys.argv[1]).parent)); s=importlib.util.spec_from_file_location("r",sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); '+body
        return subprocess.run([sys.executable,'-c',code,str(SOURCE)]+[str(x) for x in args],cwd=self.root,capture_output=True,text=True,timeout=20)

    def test_duplicate_execution_across_batches_rejected_atomically(self):
        self.submit()
        ok,_=self.runner.submit_batch(self.manifest('B','exec-A'))
        self.assertFalse(ok)
        self.assertEqual((self.rows('batches'),self.rows('jobs')),(1,1))

    def test_distinct_execution_ids_share_same_source(self):
        self.submit('A','exec-A');self.submit('B','exec-B')
        self.assertEqual(self.runner.run_batch('A',True),(1,0))
        self.assertEqual(self.runner.run_batch('B',True),(1,0))
        a=self.runner.status_batch('A')['jobs'][0]
        b=self.runner.status_batch('B')['jobs'][0]
        self.assertNotEqual(a['output_fsp_path'],b['output_fsp_path'])
        self.assertEqual(a['output_sha256'],b['output_sha256'])
        self.assertEqual(a['attempt']['solver_entered'],0)
        self.assertEqual(b['attempt']['solver_entered'],0)

    def test_legacy_manifest_without_identity_or_sha_still_fake_compatible(self):
        p=self.root/'legacy.json'
        p.write_text(json.dumps({'batch_name':'legacy','jobs':[{'input_fsp':'synthetic.fsp'}]}))
        self.assertTrue(self.runner.submit_batch(p)[0])
        self.assertEqual(self.runner.run_batch('legacy',True),(1,0))
        self.assertIsNone(self.runner.status_batch('legacy')['jobs'][0]['external_execution_id'])

    def test_external_job_id_alias_is_generic(self):
        self.submit(execution=None, external_job_id='owner:case/attempt-1')
        self.assertEqual(self.runner.status_batch('A')['jobs'][0]['external_execution_id'],'owner:case/attempt-1')

    def test_prior_abc_four_job_regression(self):
        for name,count in [('A',2),('B',1),('C',1)]:
            jobs=[{'input_fsp':str(self.fsp),'sha256':self.digest} for _ in range(count)]
            p=self.root/(name+'.json');p.write_text(json.dumps({'batch_name':name,'jobs':jobs}))
            self.assertTrue(self.runner.submit_batch(p)[0])
            self.assertEqual(self.runner.run_batch(name,True),(count,0))
            self.assertEqual(self.runner.status_batch(name)['completed'],count)
        self.assertEqual(self.rows('solver_entries'),4)
        self.assertEqual(self.runner.run_batch('A',True),(0,0))
        self.assertEqual(self.rows('solver_entries'),4)

    def test_existing_v31_schema_migration_preserves_entry(self):
        db=self.root/'legacy_v31.db'
        with sqlite3.connect(db) as c:
            c.execute('CREATE TABLE batches(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,description TEXT,status TEXT DEFAULT \'PENDING\',created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            c.execute('CREATE TABLE jobs(id INTEGER PRIMARY KEY,batch_id INTEGER NOT NULL,input_fsp_path TEXT NOT NULL,input_fsp_sha256 TEXT NOT NULL,status TEXT DEFAULT \'PENDING\',created_at TEXT DEFAULT CURRENT_TIMESTAMP,started_at TEXT,completed_at TEXT,output_fsp_path TEXT,error_message TEXT)')
            c.execute('CREATE TABLE solver_entries(id INTEGER PRIMARY KEY,job_id INTEGER NOT NULL UNIQUE,attempt_id TEXT NOT NULL,entered_at TEXT NOT NULL)')
            c.execute('INSERT INTO batches(id,name) VALUES(1,\'historical\')')
            c.execute('INSERT INTO jobs(id,batch_id,input_fsp_path,input_fsp_sha256,status) VALUES(1,1,?,?,\'RUNNING\')',(str(self.fsp),self.digest))
            c.execute('INSERT INTO solver_entries(job_id,attempt_id,entered_at) VALUES(1,\'original-attempt\',\'2026-10-16\')')
        r=module.MinimalBatchRunner(db,lock_path=self.root/'mutex.lock')
        self.assertFalse(r.run_job(1,fake_solver=True)[0])
        entry=r.status_batch('historical')['jobs'][0]['attempt']
        self.assertEqual(entry['attempt_id'],'original-attempt')
        self.assertEqual(entry['entered_at'],'2026-10-16')
        self.assertIsNone(entry['solver_entered'])

    def test_repeat_reservation_does_not_corrupt_completed_job(self):
        self.submit();self.runner.run_batch('A',True)
        with self.assertRaises(module.NoReplayError):
            self.runner._record_solver_entry(1,'attempt_001',True)
        self.assertEqual(self.runner.status_batch('A')['jobs'][0]['status'],'COMPLETED')

    def test_incorrect_sha_rejected(self):
        self.assertFalse(self.runner.submit_batch(self.manifest(sha256='0'*64))[0])
        self.assertEqual(self.rows('jobs'),0)

    def test_input_changed_after_submit_fails_without_entry(self):
        self.submit();self.fsp.write_bytes(b'changed')
        self.assertEqual(self.runner.run_batch('A',True),(0,1))
        self.assertEqual(self.rows('solver_entries'),0)

    def test_live_run_holds_even_if_resources_seem_idle(self):
        self.submit()
        with patch.dict(sys.modules,{'lumapi':None}):
            self.assertEqual(self.runner.run_batch('A',False),(0,0))
        self.assertTrue(self.runner.last_hold)
        self.assertEqual(self.rows('solver_entries'),0)
        self.assertEqual(self.runner.status_batch('A')['pending'],1)

    def test_direct_real_reservation_cannot_bypass_live_hold(self):
        self.submit()
        with self.assertRaises(module.ResourceGateError):
            self.runner._record_solver_entry(1,'attempt_001')
        self.assertEqual(self.rows('solver_entries'),0)

    def test_cross_process_same_file_different_cwd_lock_contention(self):
        self.runner._acquire_gpu_lock()
        code='r=m.MinimalBatchRunner(sys.argv[2],lock_path=sys.argv[3]); r._acquire_gpu_lock()'
        result=self.child(code,self.root/'child.db',self.root/'mutex.lock')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Resource gate HOLD',result.stderr)
        self.runner._release_gpu_lock()
        self.assertEqual(self.child(code+'; r._release_gpu_lock()',self.root/'child2.db',self.root/'mutex.lock').returncode,0)

    def test_nonparticipating_process_is_not_fenced_by_file_mutex(self):
        self.runner._acquire_gpu_lock()
        # Synthetic nonparticipant only; no GUI or solver launch.
        p=subprocess.run([sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).write_text("NOT_FENCED")',str(self.root/'nonparticipant.txt')],capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0)
        self.assertTrue((self.root/'nonparticipant.txt').exists())

    def test_atomic_entry_race_only_one_reservation(self):
        self.submit()
        body='r=m.MinimalBatchRunner(sys.argv[2],lock_path=sys.argv[3]); r._record_solver_entry(1,"attempt_001",fake_solver=True)'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _: self.child(body,self.root/'isolated.db',self.root/'mutex.lock'),range(2)))
        self.assertEqual(sorted(p.returncode==0 for p in results),[False,True])
        self.assertEqual(self.rows('solver_entries'),1)

    def test_concurrent_duplicate_submit_only_one_batch(self):
        paths=[self.manifest('A','same-execution'),self.manifest('B','same-execution')]
        body='r=m.MinimalBatchRunner(sys.argv[2],lock_path=sys.argv[3]); ok,msg=r.submit_batch(sys.argv[4]); print(msg); sys.exit(0 if ok else 3)'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda p:self.child(body,self.root/'isolated.db',self.root/'mutex.lock',p),paths))
        self.assertEqual(sorted(p.returncode for p in results),[0,3])
        self.assertEqual(self.rows('jobs'),1)

    def test_crash_after_reservation_never_replays(self):
        self.submit()
        body='import os; r=m.MinimalBatchRunner(sys.argv[2],lock_path=sys.argv[3]); r._record_solver_entry(1,"attempt_001",fake_solver=True); os._exit(23)'
        self.assertEqual(self.child(body,self.root/'isolated.db',self.root/'mutex.lock').returncode,23)
        restored=self.new_runner()
        self.assertEqual(restored.run_batch('A',True),(0,0))
        self.assertFalse(restored.run_job(1,fake_solver=True)[0])
        self.assertEqual(restored.status_batch('A')['running'],1)
        self.assertEqual(self.rows('solver_entries'),1)

    def test_failure_preserves_partial_file_and_log(self):
        self.submit()
        with patch.object(module.os,'replace',side_effect=OSError('synthetic rename failure')):
            self.assertEqual(self.runner.run_batch('A',True),(0,1))
        job=self.runner.status_batch('A')['jobs'][0]
        self.assertEqual(job['status'],'FAILED')
        self.assertTrue(Path(job['output_fsp_path']).is_file())
        self.assertIn('synthetic rename failure',Path(job['log_path']).read_text())
        self.assertFalse(self.runner.run_job(1,fake_solver=True)[0])
        self.assertEqual(self.rows('solver_entries'),1)

    def test_cli_failure_and_hold_exit_codes(self):
        self.submit();self.fsp.write_bytes(b'bad')
        args=[sys.executable,str(SOURCE),'run','A','--db',str(self.root/'isolated.db'),'--output-dir',str(self.root/'outputs'),'--fake-solver']
        p=subprocess.run(args,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,1,p.stdout+p.stderr)
        self.fsp.write_bytes(b'FAKE_TEST_FIXTURE_ONLY_NOT_NATIVE_FSP')
        self.submit('B','exec-B')
        args=[sys.executable,str(SOURCE),'run','B','--db',str(self.root/'isolated.db'),'--output-dir',str(self.root/'outputs')]
        p=subprocess.run(args,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,2,p.stdout+p.stderr)
        self.assertEqual(self.rows('solver_entries'),0)


if __name__=='__main__':
    unittest.main(verbosity=2)

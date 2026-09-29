import sys, tempfile, unittest, multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from shared_fdtd.control_v3 import ControlDB, Allocator
from shared_fdtd.control_v3.launch_authority import ScientificLaunchAuthority, LaunchAlreadyClaimed
from shared_fdtd.control_v3.allocator import AdmissionGateBlocked
IDENTITY=dict(pre_fsp_hash='a'*64,physical_contract_hash='b'*64,command=['fake-engine','fixture.fsp'],executable='fake-engine')

def crash_after_claim(path, lease):
    import os
    ScientificLaunchAuthority(ControlDB(path)).invoke(lease,lambda _: os._exit(17),**IDENTITY)

class LaunchAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='launch_authority_')
        self.db=ControlDB(Path(self.tmp.name)/'control.sqlite3')
        self.db.initialize(ROOT/'scripts/shared_fdtd/control_v3/schema.sql')
        self.allocator=Allocator(self.db)
        self.lease=self.allocator.acquire('traditional','TEST','attempt_001')
        self.auth=ScientificLaunchAuthority(self.db)
    def tearDown(self):self.tmp.cleanup()
    def test_concurrent_invocations(self):
        calls=[]
        def run(_):
            try:self.auth.invoke(self.lease,lambda c:calls.append(c['launch_id']),**IDENTITY);return 'START'
            except LaunchAlreadyClaimed:return 'DENIED'
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(run,range(24)))
        self.assertEqual(results.count('START'),1);self.assertEqual(len(calls),1)
    def test_exception_does_not_rollback_claim(self):
        def fail(_):raise RuntimeError('external side effect may already exist')
        with self.assertRaises(RuntimeError):self.auth.invoke(self.lease,fail,**IDENTITY)
        with self.assertRaises(LaunchAlreadyClaimed):self.auth.invoke(self.lease,lambda _:self.fail('replayed'),**IDENTITY)
    def test_process_crash_does_not_rollback(self):
        child=multiprocessing.get_context('spawn').Process(target=crash_after_claim,args=(str(self.db.path),self.lease))
        child.start();child.join(20)
        self.assertEqual(child.exitcode,17)
        with self.assertRaises(LaunchAlreadyClaimed):self.auth.claim(self.lease,**IDENTITY)
    def test_hold_after_lease_blocks(self):
        self.db.set_admission_control(new_entry_hold=True)
        with self.assertRaises(AdmissionGateBlocked):self.auth.invoke(self.lease,lambda _:self.fail('started under hold'),**IDENTITY)
    def test_prior_entry_blocks_replay(self):
        self.allocator.mark_entered(self.lease)
        with self.assertRaises(LaunchAlreadyClaimed):self.auth.claim(self.lease,**IDENTITY)
    def test_new_fence_cannot_reuse_attempt(self):
        self.auth.claim(self.lease,**IDENTITY)
        self.allocator.release_owned(self.lease,scientific_terminal='FAILED_PREENTRY')
        newer=self.allocator.acquire('traditional','TEST','attempt_001')
        with self.assertRaises(LaunchAlreadyClaimed):self.auth.claim(newer,**IDENTITY)
    def test_process_binding_idempotency_and_conflict(self):
        claim=self.auth.claim(self.lease,**IDENTITY)
        kwargs=dict(pid=123,created_at='2026-09-29T00:00:00Z',executable='fake-engine')
        self.assertEqual(self.auth.record_process(self.lease,claim['launch_id'],**kwargs),'RECORDED')
        self.assertEqual(self.auth.record_process(self.lease,claim['launch_id'],**kwargs),'IDEMPOTENT_REPLAY_OF_EVENT')
        with self.assertRaises(ValueError):self.auth.record_process(self.lease,claim['launch_id'],**{**kwargs,'pid':456})
    def test_claim_visible_inside_callback(self):
        def callback(claim):
            with self.db.connect(readonly=True) as con:
                row=con.execute('SELECT launch_id FROM scientific_launch_claims').fetchone()
                self.assertEqual(row['launch_id'],claim['launch_id'])
                self.assertEqual(con.execute("SELECT count(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0],1)
                self.assertEqual(con.execute('SELECT state FROM slots WHERE slot_id=?',(self.lease.slot_id,)).fetchone()[0],'LIVE')
            self.assertTrue(claim['solver_entered']);self.assertFalse(claim['physical_process_confirmed'])
        self.auth.invoke(self.lease,callback,**IDENTITY)
    def test_table_helpers_preserve_transaction_and_rollback(self):
        from shared_fdtd.control_v3.resources import ensure_resource_tables
        from shared_fdtd.control_v3.gpu_capacity import ensure_gpu_capacity_tables
        for helper in (ensure_resource_tables,ensure_gpu_capacity_tables):
            with self.assertRaisesRegex(RuntimeError,'rollback probe'):
                with self.db.immediate() as con:
                    con.execute("UPDATE slots SET state='OWNER_QUARANTINED' WHERE slot_id=?",(self.lease.slot_id,))
                    helper(con)
                    self.assertTrue(con.in_transaction)
                    raise RuntimeError('rollback probe')
            with self.db.connect(readonly=True) as con:
                self.assertEqual(con.execute('SELECT state FROM slots WHERE slot_id=?',(self.lease.slot_id,)).fetchone()[0],'RESERVED')

    def test_invalid_hash_no_callback(self):
        with self.assertRaises(ValueError):self.auth.invoke(self.lease,lambda _:self.fail('called'),**{**IDENTITY,'pre_fsp_hash':'missing'})

if __name__=='__main__': unittest.main(verbosity=2)

import sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from shared_fdtd.control_v3 import ControlDB,Allocator
from shared_fdtd.control_v3.launch_authority import ScientificLaunchAuthority,LaunchAlreadyClaimed
from shared_fdtd.engine.attempt_guard import exclusive_attempt

class AttemptGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='host_guard_');self.root=Path(self.tmp.name)
        self.db=ControlDB(self.root/'control.sqlite3');self.db.initialize(ROOT/'scripts/shared_fdtd/control_v3/schema.sql')
        self.lease=Allocator(self.db).acquire('traditional','T','a1')
        self.cfg=dict(db=str(self.db.path),attempt_root=str(self.root/'attempt'),branch='traditional',case='T',attempt='a1',slot_id=self.lease.slot_id,lease_token=self.lease.lease_token,fencing_generation=self.lease.fencing_generation)
    def tearDown(self):self.tmp.cleanup()
    def test_second_host_rejected(self):
        with exclusive_attempt(self.cfg):
            with self.assertRaises(LaunchAlreadyClaimed):
                with exclusive_attempt(self.cfg): self.fail('second host')
    def test_preentry_retry_after_exit(self):
        with exclusive_attempt(self.cfg):pass
        with exclusive_attempt(self.cfg):pass
    def test_claim_blocks_artifact_overwrite(self):
        root=Path(self.cfg['attempt_root']);root.mkdir();artifact=root/'attempt_ledger.json';artifact.write_text('preserved')
        ScientificLaunchAuthority(self.db).claim(self.lease,pre_fsp_hash='a'*64,physical_contract_hash='b'*64,command=['fake'],executable='fake')
        with self.assertRaises(LaunchAlreadyClaimed):
            with exclusive_attempt(self.cfg):artifact.write_text('overwritten')
        self.assertEqual(artifact.read_text(),'preserved')
    def test_historical_entry_blocks(self):
        Allocator(self.db).mark_entered(self.lease)
        with self.assertRaises(LaunchAlreadyClaimed):
            with exclusive_attempt(self.cfg):self.fail('replay')
    def test_stale_fence_blocks(self):
        self.cfg['fencing_generation']+=1
        with self.assertRaises(LaunchAlreadyClaimed):
            with exclusive_attempt(self.cfg):self.fail('foreign')
if __name__=='__main__':unittest.main()

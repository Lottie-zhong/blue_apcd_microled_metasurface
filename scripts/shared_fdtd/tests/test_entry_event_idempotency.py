from __future__ import annotations
import sys, tempfile, unittest, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.allocator import OwnershipMismatch

class EntryIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='entry_idempotency_')
        self.db = ControlDB(Path(self.tmp.name) / 'control.sqlite3')
        self.db.initialize(ROOT / 'scripts/shared_fdtd/control_v3/schema.sql')
        self.a = Allocator(self.db)
        self.lease = self.a.acquire('traditional', 'TEST', 'attempt_001')
    def tearDown(self): self.tmp.cleanup()
    def snapshot(self):
        with self.db.connect(readonly=True) as con:
            return (dict(con.execute('SELECT * FROM slots WHERE slot_id=?', (self.lease.slot_id,)).fetchone()),
                    [dict(r) for r in con.execute("SELECT * FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'")])
    def test_repeat_preserves_timestamp_version_and_event(self):
        self.assertEqual(self.a.mark_entered(self.lease)['status'], 'RECORDED')
        before = self.snapshot()
        self.assertEqual(self.a.mark_entered(self.lease)['status'], 'IDEMPOTENT_REPLAY_OF_EVENT')
        self.assertEqual(before, self.snapshot())
        self.assertTrue(json.loads(before[1][0]['metadata_json'])['semantic_event_key'])
    def test_concurrent_reconciliation_and_worker(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(lambda _: Allocator(self.db).mark_entered(self.lease)['status'], range(24)))
        self.assertEqual(statuses.count('RECORDED'), 1)
        self.assertEqual(statuses.count('IDEMPOTENT_REPLAY_OF_EVENT'), 23)
        self.assertEqual(len(self.snapshot()[1]), 1)
    def test_restart_keeps_event(self):
        self.a.mark_entered(self.lease)
        before = self.snapshot()
        Allocator(ControlDB(self.db.path)).mark_entered(self.lease)
        self.assertEqual(before, self.snapshot())
    def test_release_pending_does_not_regress(self):
        self.a.mark_entered(self.lease)
        self.a.release_pending(self.lease, 'TRUTH_PENDING')
        before = self.snapshot(); self.a.mark_entered(self.lease)
        self.assertEqual(before, self.snapshot())
    def test_quarantine_does_not_regress(self):
        self.a.mark_entered(self.lease)
        self.a.quarantine_owned(self.lease, 'INCIDENT')
        before = self.snapshot(); self.a.mark_entered(self.lease)
        self.assertEqual(before, self.snapshot())
    def test_foreign_and_stale_identity_fail(self):
        for bad in [replace(self.lease, lease_token='foreign'), replace(self.lease, fencing_generation=999), replace(self.lease, owner_branch='coupling_ml')]:
            with self.assertRaises(OwnershipMismatch): self.a.mark_entered(bad)
        self.assertEqual(len(self.snapshot()[1]), 0)
    def test_released_owner_cannot_resurrect(self):
        self.a.mark_entered(self.lease)
        self.a.release_owned(self.lease, scientific_terminal='SCIENTIFIC_VALID')
        with self.assertRaises(OwnershipMismatch): self.a.mark_entered(self.lease)
        self.assertEqual(self.snapshot()[0]['state'], 'FREE')
    def test_historical_duplicates_preserved(self):
        self.a.mark_entered(self.lease)
        with self.db.immediate() as con: self.a._event(con, self.lease, 'SCIENTIFIC_SOLVER_ENTERED', {'legacy_fixture': True})
        before = self.snapshot(); self.a.mark_entered(self.lease)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(before[1]), 2)
    def test_new_lease_same_attempt_rejected(self):
        self.a.mark_entered(self.lease)
        self.a.release_owned(self.lease, scientific_terminal='SCIENTIFIC_VALID')
        other = self.a.acquire('traditional', 'TEST', 'attempt_001')
        with self.assertRaises(OwnershipMismatch): self.a.mark_entered(other)

if __name__ == '__main__': unittest.main(verbosity=2)

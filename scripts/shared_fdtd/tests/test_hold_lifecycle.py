import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/"scripts"))
from shared_fdtd.control_v3 import ControlDB
class HoldTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.db=ControlDB(Path(self.t.name)/"control.sqlite3");self.db.initialize(ROOT/"scripts/shared_fdtd/control_v3/schema.sql")
 def tearDown(self):self.t.cleanup()
 def test_set_is_durable_and_auditable(self):
  x=self.db.set_hold(scope="GLOBAL",reason_code="INCIDENT",free_text_reason="test",created_by="test-owner",linked_incident_ids=["I1"],linked_case_ids=["C1"],release_requirements={"need":"review"});self.assertEqual(x["status"],"ACTIVE");self.assertEqual(self.db.list_holds_readonly()[0]["created_by"],"test-owner")
  with self.db.connect(readonly=True) as c:self.assertEqual(c.execute("SELECT new_entry_hold FROM admission_control").fetchone()[0],1);self.assertEqual(c.execute("SELECT event_type FROM hold_events").fetchone()[0],"HOLD_SET")
 def test_duplicate_scope_rejected(self):self.db.set_hold(scope="GLOBAL",reason_code="I",created_by="o");
 def test_release_requires_authority_and_updates_generation(self):
  x=self.db.set_hold(scope="GLOBAL",reason_code="I",created_by="o");
  with self.assertRaises(ValueError):self.db.release_hold(x["hold_id"],released_by="o",release_authority_hash="")
  y=self.db.release_hold(x["hold_id"],released_by="reviewer",release_authority_hash="sha256:abc",evidence={"checks":True});self.assertEqual(y["status"],"RELEASED");self.assertFalse(y["global_hold"]);self.assertEqual(self.db.list_holds_readonly()[0]["status"],"RELEASED")
 def test_release_is_idempotent(self):
  x=self.db.set_hold(scope="GLOBAL",reason_code="I",created_by="o");self.db.release_hold(x["hold_id"],released_by="r",release_authority_hash="h");self.assertEqual(self.db.release_hold(x["hold_id"],released_by="r",release_authority_hash="h")["status"],"RELEASED")
if __name__=="__main__":unittest.main()

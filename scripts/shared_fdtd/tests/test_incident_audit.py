import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/"scripts"))
from shared_fdtd.control_v3 import ControlDB
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.tools.shared_v3_incident_audit import audit
class IncidentTests(unittest.TestCase):
 def test_readonly_inventory(self):
  t=tempfile.TemporaryDirectory();r=Path(t.name);db=ControlDB(r/"control.sqlite3");db.initialize(ROOT/"scripts/shared_fdtd/control_v3/schema.sql");n=utc_now()
  with db.immediate() as c:
   c.execute("INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",("traditional","C","a1","POSTENTRY_NO_TRUTH","{}",n,n))
   c.execute("INSERT INTO lease_events(timestamp,slot_id,branch_id,logical_case_id,attempt_id,event_type,lease_token_hash,fencing_generation,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",(n,"GLOBAL_SLOT_1","traditional","C","a1","SCIENTIFIC_SOLVER_ENTERED","h",1,"{}"))
  result=audit(db.path);self.assertEqual(result["incident_count"],1);self.assertTrue(result["incidents"][0]["entry_lineage"]["replay_prohibited"]);self.assertTrue(result["read_only"])
if __name__=="__main__":unittest.main()

import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from shared_fdtd.control_v3 import ControlDB,Allocator
from shared_fdtd.engine.status import readonly_status
class LiveMetricTests(unittest.TestCase):
 def test_status_reads_live_events_without_mutation(self):
  t=tempfile.TemporaryDirectory();db=ControlDB(Path(t.name)/'control.sqlite3');db.initialize(ROOT/'scripts/shared_fdtd/control_v3/schema.sql');a=Allocator(db);l=a.acquire('traditional','C','a1');a.mark_entered(l)
  with db.immediate() as c:a._event(c,l,'SCIENTIFIC_SOLVER_ENTERED',{'legacy':True})
  s=readonly_status(db);self.assertEqual(s['metrics']['DUPLICATE_SCIENTIFIC_ENTRY_COUNT_LIVE'],1);self.assertEqual(s['metrics']['DUPLICATE_SCIENTIFIC_ENTRY_ATTEMPTS_LIVE'],1);t.cleanup()
if __name__=='__main__':unittest.main()

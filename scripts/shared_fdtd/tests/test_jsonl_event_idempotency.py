import sys,tempfile,unittest,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from shared_fdtd.engine.event_log import append_event,read_events
class JsonlTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'events.jsonl'
 def tearDown(self): self.tmp.cleanup()
 def test_duplicate_entry_key_dedupes(self):
  p={'case_id':'C','attempt_id':'a1','launch_id':'L'};first=append_event(self.path,'SCIENTIFIC_SOLVER_ENTERED',**p);second=append_event(self.path,'SCIENTIFIC_SOLVER_ENTERED',**p);self.assertEqual(first,second);self.assertEqual(len(read_events(self.path)),1)
 def test_concurrent_entry_writes_dedupe(self):
  p={'case_id':'C','attempt_id':'a1','launch_id':'L'};out=[];threads=[threading.Thread(target=lambda:out.append(append_event(self.path,'SCIENTIFIC_SOLVER_ENTERED',**p))) for _ in range(16)]
  [t.start() for t in threads];[t.join() for t in threads];self.assertEqual(len(read_events(self.path)),1);self.assertEqual(len({x['semantic_event_key'] for x in out}),1)
 def test_nonkeyed_history_stays_append_only(self):
  append_event(self.path,'HOST_STARTED',pid=1);append_event(self.path,'HOST_STARTED',pid=1);self.assertEqual(len(read_events(self.path)),2)
if __name__=='__main__': unittest.main()

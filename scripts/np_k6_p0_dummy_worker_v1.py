import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
hb=Path(sys.argv[1]); done=Path(sys.argv[2]); pid=Path(sys.argv[3]); duration=float(sys.argv[4])
def ts(): return datetime.now(timezone.utc).isoformat()
for i in range(int(duration)):
 hb.write_text(json.dumps({'pid':os.getpid(),'heartbeat_utc':ts(),'elapsed_s':i,'duration_s':duration}),encoding='utf-8')
 time.sleep(1)
hb.write_text(json.dumps({'pid':os.getpid(),'heartbeat_utc':ts(),'elapsed_s':duration,'duration_s':duration,'completed':True}),encoding='utf-8')
done.write_text(json.dumps({'pid':os.getpid(),'exit_code':0,'completed_utc':ts(),'duration_s':duration}),encoding='utf-8')
try: pid.unlink()
except FileNotFoundError: pass

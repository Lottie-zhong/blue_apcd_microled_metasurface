from __future__ import annotations
import json, os
from pathlib import Path
from shared_fdtd.control_v3.db import utc_now

def append_event(path: str | Path, event_type: str, **payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    row={"timestamp":utc_now(),"event_type":event_type,**payload}
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,sort_keys=True,default=str)+"\n"); f.flush(); os.fsync(f.fileno())
    return row

def read_events(path: str | Path):
    p=Path(path)
    if not p.exists(): return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

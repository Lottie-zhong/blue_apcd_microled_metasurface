from __future__ import annotations
import json, sys
from pathlib import Path

PKG=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(PKG.parent)); sys.path.insert(0,r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
import numpy as np
from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.allocator import Lease
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.persistence import atomic_json, sha256_file
from shared_fdtd.tools.real_canary_host import serialized_open

cfg=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")); root=Path(cfg["runtime"]); events=root/"events.jsonl"
seen={event["event_type"] for event in read_events(events)}
required={"SOLVER_RETURNED","NATIVE_TRUTH_DURABLE","POST_FSP_VALID"}
if not required <= seen or "SCIENTIFIC_VALID" in seen: raise SystemExit("not eligible for load-only recovery")
post=next((root/"post").glob("*__post.fsp")); append_event(events,"FRESH_LOAD_RECOVERY_STARTED",post_fsp=str(post),sha256=sha256_file(post))
fd=serialized_open(cfg["db"],post)
try: T=np.asarray(fd.transmission("tiny_monitor")).reshape(-1)
finally: fd.close()
proof={"points":int(T.size),"finite":bool(np.isfinite(T).all()),"T":T.tolist(),"recovery":"LOAD_ONLY_NO_SOLVER"}
if proof["points"]!=3 or not proof["finite"]: raise SystemExit("fresh load validation failed")
raw=root/"raw"/"monitor.json"; atomic_json(raw,proof); append_event(events,"RAW_VALID",artifact_path=str(raw),sha256=sha256_file(raw)); append_event(events,"SCIENTIFIC_VALID",recovery="LOAD_ONLY_NO_SOLVER"); append_event(events,"HF_ARCHIVED",role="INFRASTRUCTURE_CANARY")
lease=Lease(cfg["slot_id"],cfg["branch"],cfg["case"],cfg["attempt"],cfg["lease_token"],cfg["fencing_generation"]); db=ControlDB(cfg["db"]); Allocator(db).release_owned(lease,scientific_terminal="SCIENTIFIC_VALID"); append_event(events,"RELEASED",recovery="LOAD_ONLY_NO_SOLVER")
with db.immediate() as con: con.execute("update branch_queue set state='RELEASED',updated_at=? where branch_id=? and logical_case_id=? and attempt_id=?",(utc_now(),cfg["branch"],cfg["case"],cfg["attempt"]))
atomic_json(root/"terminal.json",{"status":"PASS","case":cfg["case"],"attempt":cfg["attempt"],"post_fsp":str(post),"post_sha256":sha256_file(post),"fresh_load":proof,"completed_at":utc_now()})

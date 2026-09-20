from __future__ import annotations
from shared_fdtd.control_v3.allocator import Allocator, Lease
from .event_log import read_events
from .state_machine import release_allowed, replay_allowed

def reconcile_owned(db,branch,attempt_roots):
    allocator=Allocator(db); results=[]
    for slot in allocator.list_slots_readonly():
        if slot["state"]=="FREE" or slot["owner_branch"]!=branch: continue
        key=(slot["logical_case_id"],slot["attempt_id"]); root=attempt_roots.get(key)
        if not root: results.append({"slot_id":slot["slot_id"],"status":"OWN_ATTEMPT_UNKNOWN_PRESERVE"}); continue
        events=read_events(root/"events.jsonl")
        results.append({"slot_id":slot["slot_id"],"status":"RELEASE_ELIGIBLE" if release_allowed(events) else "PRESERVE_NO_REPLAY","replay_allowed":replay_allowed(events)})
    return results

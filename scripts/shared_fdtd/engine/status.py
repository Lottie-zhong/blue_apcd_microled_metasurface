from __future__ import annotations
import json
from shared_fdtd.control_v3.allocator import Allocator

def readonly_status(db):
    slots=Allocator(db).list_slots_readonly()
    with db.connect(readonly=True) as con:
        branches=[dict(r) for r in con.execute("SELECT b.branch_id,b.cap,b.enabled,(SELECT COUNT(*) FROM slots s WHERE s.owner_branch=b.branch_id AND s.state<>'FREE') active,(SELECT COUNT(*) FROM branch_queue q WHERE q.branch_id=b.branch_id AND q.state='QUEUED') queued FROM branch_limits b ORDER BY b.branch_id")]
        metrics={r["metric_name"]:r["metric_value"] for r in con.execute("SELECT * FROM health_metrics")}
    try:
        reservations = Allocator(db).list_resource_reservations_readonly()
    except Exception:
        reservations = []
    return {"global_capacity":len(slots),"slots":slots,"branches":branches,"metrics":metrics,"resource_reservations":reservations}

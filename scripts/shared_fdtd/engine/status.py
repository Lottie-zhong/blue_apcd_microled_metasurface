from __future__ import annotations
import json
from shared_fdtd.control_v3.allocator import Allocator

def readonly_status(db):
    slots=Allocator(db).list_slots_readonly()
    with db.connect(readonly=True) as con:
        branches=[dict(r) for r in con.execute("SELECT b.branch_id,b.cap,b.enabled,(SELECT COUNT(*) FROM slots s WHERE s.owner_branch=b.branch_id AND s.state<>'FREE') active,(SELECT COUNT(*) FROM branch_queue q WHERE q.branch_id=b.branch_id AND q.state='QUEUED') queued FROM branch_limits b ORDER BY b.branch_id")]
        metrics={r["metric_name"]:r["metric_value"] for r in con.execute("SELECT * FROM health_metrics")}
        duplicate = con.execute("""
            SELECT COALESCE(SUM(extra),0) AS count, COALESCE(SUM(CASE WHEN entries > 1 THEN 1 ELSE 0 END),0) AS attempts
            FROM (SELECT branch_id,logical_case_id,attempt_id,COUNT(*) AS entries,COUNT(*)-1 AS extra
                  FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'
                  GROUP BY branch_id,logical_case_id,attempt_id)
        """).fetchone()
        metrics["DUPLICATE_SCIENTIFIC_ENTRY_COUNT_LIVE"] = int(duplicate["count"])
        metrics["DUPLICATE_SCIENTIFIC_ENTRY_ATTEMPTS_LIVE"] = int(duplicate["attempts"])
    try:
        reservations = Allocator(db).list_resource_reservations_readonly()
    except Exception:
        reservations = []
    return {"global_capacity":len(slots),"slots":slots,"branches":branches,"metrics":metrics,"resource_reservations":reservations}

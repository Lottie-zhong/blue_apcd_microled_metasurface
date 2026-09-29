from __future__ import annotations
import argparse,json,sqlite3
from pathlib import Path

TERMINAL=("POSTENTRY_NO_TRUTH","FAILED_AFTER_ENTRY","OWNER_QUARANTINED","AMBIGUOUS_QUARANTINED")
def audit(db_path):
    con=sqlite3.connect(Path(db_path).resolve().as_uri()+"?mode=ro",uri=True);con.row_factory=sqlite3.Row;con.execute("PRAGMA query_only=ON")
    rows=con.execute("SELECT branch_id,logical_case_id,attempt_id,state,payload_json,updated_at FROM branch_queue WHERE state IN (?,?,?,?) ORDER BY updated_at",TERMINAL).fetchall();incidents=[]
    for row in rows:
        key=(row["branch_id"],row["logical_case_id"],row["attempt_id"])
        events=[dict(x) for x in con.execute("SELECT event_id,event_type,fencing_generation FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? ORDER BY event_id",key)]
        entries=[x for x in events if x["event_type"]=="SCIENTIFIC_SOLVER_ENTERED"]
        truth=[x["event_type"] for x in events if x["event_type"] in ("NATIVE_TRUTH_DURABLE","POST_FSP_VALID","RAW_VALID","SCIENTIFIC_VALID")]
        active=int(con.execute("SELECT COUNT(*) FROM slots WHERE state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED') AND owner_branch=? AND logical_case_id=? AND attempt_id=?",key).fetchone()[0])
        incidents.append({"branch":key[0],"case":key[1],"attempt":key[2],"queue_state":row["state"],"updated_at":row["updated_at"],"entry_lineage":{"scientific_solver_entered_events":len(entries),"event_ids":[x["event_id"] for x in entries],"replay_prohibited":bool(entries),"fencing_generations":sorted({x["fencing_generation"] for x in events if x["fencing_generation"] is not None})},"solver_return":any(x["event_type"]=="SOLVER_RETURNED" for x in events),"truth_events":truth,"active_slot_count":active,"failure_class":row["state"]})
    con.close();return {"schema":"SHARED_V3_HISTORICAL_INCIDENT_AUDIT_V1","db_path":str(Path(db_path).resolve()),"incident_count":len(incidents),"incidents":incidents,"solver_runs":0,"scientific_solver_entries_this_task":0,"replay_performed":False,"read_only":True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("db");ap.add_argument("--out",required=True);a=ap.parse_args();result=audit(a.db);Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(json.dumps({"status":"PASS","incident_count":result["incident_count"],"solver_runs":0,"read_only":True}))
if __name__=="__main__":main()

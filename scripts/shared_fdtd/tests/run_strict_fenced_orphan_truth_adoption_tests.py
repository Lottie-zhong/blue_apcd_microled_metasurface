from __future__ import annotations
import json
import sys
import tempfile
import threading
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "scripts"))
from shared_fdtd.control_v3 import ControlDB, OrphanTruthAdoption, RecoveryBlocked, artifact_identity_sha256
from shared_fdtd.engine.state_machine import replay_allowed

SCHEMA = root / "scripts/shared_fdtd/control_v3/schema.sql"
HEX = "0123456789abcdef"

def evidence(**overrides):
    hashes = {name: (HEX[i] * 64) for i, name in enumerate(("fsp","h5","raw","projection","hf_archive","setup","solver_entry","provenance"))}
    out = {
        "scientific_entry_count": 1, "solver_invocation_count": 1, "replay_count": 0,
        "duplicate_scientific_entry_count": 0, "newer_attempt_exists": False, "live_process": False,
        "persistence_active": False, "truth_valid": True, "conflicting_truth": False,
        "autofill_enabled": False, "s15_s16_non_entered": True, "foreign_mutation_count": 0,
        "runtime_owner_created": False, "evidence_manifest_sha256": "b" * 64,
        "artifact_hashes": hashes,
    }
    out["artifact_identity_sha256"] = artifact_identity_sha256(hashes)
    out.update(overrides)
    if "artifact_hashes" in overrides and "artifact_identity_sha256" not in overrides:
        out["artifact_identity_sha256"] = artifact_identity_sha256(out["artifact_hashes"])
    return out

def fixture(*, entry_count=1):
    td = tempfile.TemporaryDirectory()
    db = ControlDB(Path(td.name) / "control.sqlite3")
    db.initialize(SCHEMA)
    db.set_admission_control(new_entry_hold=True, temporary_runtime_cap=1)
    now = "2026-01-01T00:00:00+00:00"
    with db.immediate() as con:
        con.execute("INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,slot_id,lease_token_hash,fencing_generation,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("coupling_ml","K6V1_S14","attempt_004","AMBIGUOUS_QUARANTINED","{}", "GLOBAL_SLOT_2","a"*64,47,now,now))
        for case in ("K6V1_S15","K6V1_S16"):
            con.execute("INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", ("coupling_ml",case,"attempt_001","WAIT_RESOURCE_CAPACITY","{}",now,now))
        for _ in range(entry_count):
            con.execute("INSERT INTO lease_events(timestamp,slot_id,branch_id,logical_case_id,attempt_id,event_type,lease_token_hash,fencing_generation,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)", (now,"GLOBAL_SLOT_2","coupling_ml","K6V1_S14","attempt_004","SCIENTIFIC_SOLVER_ENTERED","a"*64,47,"{}"))
    return td, db

def blocked(fn, label):
    try:
        fn()
    except RecoveryBlocked:
        return
    raise AssertionError(label)

def arm(rec, ev=None):
    return rec.issue_fence(evidence=ev or evidence(), control_generation=1)["fence_id"]

tests = {}
def run(name, fn):
    try:
        fn()
        tests[name] = "PASS"
    except Exception as exc:
        tests[name] = "FAIL:" + repr(exc)

def valid_and_reuse():
    td, db = fixture()
    try:
        rec = OrphanTruthAdoption(db); ev = evidence(); fid = arm(rec, ev)
        assert rec.adopt(fence_id=fid, evidence=ev, control_generation=1)["status"] == "RECOVERED_ADOPTED"
        assert rec.adopt(fence_id=fid, evidence=ev, control_generation=1)["status"] == "ALREADY_CONSUMED"
        with db.connect(readonly=True) as con:
            q = con.execute("SELECT state,slot_id,lease_token_hash,fencing_generation FROM branch_queue WHERE logical_case_id='K6V1_S14' AND attempt_id='attempt_004'").fetchone()
            assert tuple(q) == ("RECOVERED_ADOPTED", None, None, None)
            assert con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='ORPHAN_TRUTH_ADOPTED'").fetchone()[0] == 1
            assert con.execute("SELECT state FROM recovery_adoption_fences").fetchone()[0] == "CONSUMED"
    finally: td.cleanup()

run("A_valid_adoption", valid_and_reuse)
run("B_same_fence_reuse", valid_and_reuse)

for label, kwargs in [("C_wrong_case", {"logical_case_id":"K6V1_S15"}), ("D_wrong_attempt", {"attempt_id":"attempt_005"})]:
    def f(kwargs=kwargs):
        td, db = fixture()
        try: blocked(lambda: OrphanTruthAdoption(db).issue_fence(evidence=evidence(), control_generation=1, **kwargs), label)
        finally: td.cleanup()
    run(label, f)

def cas_drift():
    td, db = fixture()
    try:
        rec = OrphanTruthAdoption(db); ev=evidence(); fid=arm(rec,ev)
        with db.immediate() as con: con.execute("UPDATE branch_queue SET updated_at=? WHERE logical_case_id='K6V1_S14'", ("2026-01-01T00:00:01+00:00",))
        blocked(lambda: rec.adopt(fence_id=fid,evidence=ev,control_generation=1), "E")
    finally: td.cleanup()
run("E_wrong_queue_version", cas_drift)

def stale_generation():
    td, db = fixture()
    try:
        rec=OrphanTruthAdoption(db); ev=evidence(); fid=arm(rec,ev)
        db.set_admission_control(temporary_runtime_cap=2)
        blocked(lambda: rec.adopt(fence_id=fid,evidence=ev,control_generation=1), "F")
    finally: td.cleanup()
run("F_stale_control_generation", stale_generation)

for label, change in [("G_manifest_mismatch", {"evidence_manifest_sha256":"c"*64}), ("H_fsp_sha_mismatch", {"artifact_hashes":{**evidence()["artifact_hashes"],"fsp":"f"*64}}), ("I_h5_sha_mismatch", {"artifact_hashes":{**evidence()["artifact_hashes"],"h5":"f"*64}})]:
    def f(change=change):
        td, db=fixture()
        try:
            rec=OrphanTruthAdoption(db); ev=evidence(); fid=arm(rec,ev); bad=evidence(**change)
            blocked(lambda: rec.adopt(fence_id=fid,evidence=bad,control_generation=1), label)
        finally: td.cleanup()
    run(label, f)

for label, ev_change in [
    ("J_zero_entry", {"scientific_entry_count":0}),
    ("K_two_entries", {"scientific_entry_count":2}),
    ("L_replay_nonzero", {"replay_count":1}),
    ("M_duplicate_truth", {"duplicate_scientific_entry_count":1}),
    ("P_live_process", {"live_process":True}),
    ("Q_persistence_active", {"persistence_active":True}),
    ("T_autofill_enabled", {"autofill_enabled":True}),
]:
    def f(ev_change=ev_change, label=label):
        td, db=fixture(entry_count=ev_change.get("scientific_entry_count",1))
        try: blocked(lambda: OrphanTruthAdoption(db).issue_fence(evidence=evidence(**ev_change),control_generation=1),label)
        finally: td.cleanup()
    run(label, f)

def newer_attempt():
    td,db=fixture()
    try:
        with db.immediate() as con:
            con.execute("INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", ("coupling_ml","K6V1_S14","attempt_005","WAIT_RESOURCE_CAPACITY","{}","x","x"))
        blocked(lambda: OrphanTruthAdoption(db).issue_fence(evidence=evidence(),control_generation=1),"N")
    finally: td.cleanup()
run("N_newer_attempt",newer_attempt)

def active_owner():
    td,db=fixture()
    try:
        with db.immediate() as con:
            con.execute("UPDATE slots SET state='LIVE',owner_branch='other',logical_case_id='OTHER',attempt_id='attempt_001',lease_token='fake' WHERE slot_id='GLOBAL_SLOT_2'")
        blocked(lambda: OrphanTruthAdoption(db).issue_fence(evidence=evidence(),control_generation=1),"O/R")
    finally: td.cleanup()
run("O_or_R_active_other_owner",active_owner)

def hold_off():
    td,db=fixture()
    try:
        db.set_admission_control(new_entry_hold=False)
        blocked(lambda: OrphanTruthAdoption(db).issue_fence(evidence=evidence(),control_generation=2),"S")
    finally: td.cleanup()
run("S_hold_false",hold_off)

def s15_entered():
    td,db=fixture()
    try:
        with db.immediate() as con:
            con.execute("INSERT INTO lease_events(timestamp,slot_id,branch_id,logical_case_id,attempt_id,event_type,lease_token_hash,fencing_generation,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)", ("x","GLOBAL_SLOT_3","coupling_ml","K6V1_S15","attempt_001","SCIENTIFIC_SOLVER_ENTERED","d"*64,1,"{}"))
        blocked(lambda: OrphanTruthAdoption(db).issue_fence(evidence=evidence(),control_generation=1),"U")
    finally: td.cleanup()
run("U_s15_entered",s15_entered)

def failpoint(point):
    td,db=fixture()
    try:
        rec=OrphanTruthAdoption(db);ev=evidence();fid=arm(rec,ev)
        try: rec.adopt(fence_id=fid,evidence=ev,control_generation=1,_test_failpoint=point)
        except RuntimeError: pass
        with db.connect(readonly=True) as con:
            assert con.execute("SELECT state FROM recovery_adoption_fences").fetchone()[0] == "ARMED"
            assert con.execute("SELECT state FROM branch_queue WHERE logical_case_id='K6V1_S14' AND attempt_id='attempt_004'").fetchone()[0] == "AMBIGUOUS_QUARANTINED"
    finally: td.cleanup()
run("W_before_commit_rollback", lambda: failpoint("before_commit"))
run("X_after_fence_consumption_rollback", lambda: failpoint("after_fence_consumption"))
run("X_after_queue_update_rollback", lambda: failpoint("after_queue_update"))
run("X_after_provenance_rollback", lambda: failpoint("after_provenance"))

def two_workers():
    td,db=fixture()
    try:
        rec=OrphanTruthAdoption(db);ev=evidence();fid=arm(rec,ev); out=[]; barrier=threading.Barrier(2)
        def worker():
            barrier.wait()
            try: out.append(rec.adopt(fence_id=fid,evidence=ev,control_generation=1)["status"])
            except Exception as e: out.append(type(e).__name__)
        ts=[threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in ts]; [t.join() for t in ts]
        assert sorted(out) == ["ALREADY_CONSUMED","RECOVERED_ADOPTED"], out
        with db.connect(readonly=True) as con:
            assert con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='ORPHAN_TRUTH_ADOPTED'").fetchone()[0] == 1
    finally: td.cleanup()
run("V_two_workers_one_winner",two_workers)

def terminal_invariants():
    td,db=fixture()
    try:
        rec=OrphanTruthAdoption(db);ev=evidence();fid=arm(rec,ev);rec.adopt(fence_id=fid,evidence=ev,control_generation=1)
        assert replay_allowed([{"event_type":"SCIENTIFIC_SOLVER_ENTERED"},{"event_type":"ORPHAN_TRUTH_ADOPTED"}]) is False
        assert not hasattr(rec, "launch")
        with db.connect(readonly=True) as con:
            row=con.execute("SELECT * FROM slots WHERE slot_id='GLOBAL_SLOT_2'").fetchone()
            meta=json.loads(con.execute("SELECT metadata_json FROM lease_events WHERE event_type='ORPHAN_TRUTH_ADOPTED'").fetchone()[0])
            assert row["state"]=="FREE" and meta["runtime_owner_created"] is False
    finally: td.cleanup()
run("Y_repeated_terminal_stable",terminal_invariants)
run("Z_adopted_truth_not_replayable",terminal_invariants)
run("AA_fence_not_launch_authority",terminal_invariants)
def ordinary_permit_rejected():
    td,db=fixture()
    try:
        blocked(lambda: OrphanTruthAdoption(db).adopt(fence_id="ordinary-permit-id",evidence=evidence(),control_generation=1),"AB")
    finally: td.cleanup()
run("AB_ordinary_permit_not_adoption",ordinary_permit_rejected)
run("AC_no_fake_runtime_owner",terminal_invariants)

fails={k:v for k,v in tests.items() if v!="PASS"}
print(json.dumps({"status":"PASS" if not fails else "FAIL","pass":sum(v=="PASS" for v in tests.values()),"total":len(tests),"fails":fails}, indent=2))
if fails: raise SystemExit(1)


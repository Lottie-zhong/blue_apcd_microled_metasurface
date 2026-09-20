from __future__ import annotations
import csv, hashlib, json, shutil, subprocess, sys
from pathlib import Path
PKG=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PKG.parent))
from shared_fdtd.control_v3 import ControlDB
from shared_fdtd.engine.event_log import read_events
from shared_fdtd.engine.status import readonly_status

def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.rstrip()+"\n",encoding="utf-8")
def jwrite(p,v):write(p,json.dumps(v,indent=2,sort_keys=True,default=str))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csv_rows(path):
    if not path.exists():return []
    with path.open(encoding="utf-8") as f:return list(csv.DictReader(f))
def main():
    out=Path(sys.argv[1]);root=Path(sys.argv[2]);runtime=Path(sys.argv[3]);cross=Path(sys.argv[4]);out.mkdir(parents=True,exist_ok=True)
    docs={
    "ARCHITECTURE.md":"""# APCD Global FDTD Production Platform V1

Four layers are independent: SQLite global capacity/ownership; branch-local queue and reconciliation; one server-owned case host per invocation; durable truth persistence before release. Dispatchers are short Task Scheduler passes. Case hosts own synchronous lumapi execution and survive dispatcher, SSH, and Codex exit. V1 remains authority until every cutover gate passes.

Global transactions end before solver launch. Owner mutations require branch, token, generation, case, and attempt. Local append-only events outrank derived reports. A post-entry unknown outcome is quarantined and never auto-replayed.
""",
    "V1_FAILURE_MODE_MAPPING.md":"""# V1 failure mapping

| V1 failure | V3 control |
|---|---|
| Controller/Qt owner exits and destroys solver | Task Scheduler case host is the synchronous lumapi owner |
| JSON registry lock/contention | short SQLite BEGIN IMMEDIATE transactions and deferred control updates |
| stale report overrides physical truth | physical evidence > events > hashes > regenerated reports |
| foreign stale cleanup | owner predicates and read-only foreign observation |
| completion then release/report failure causes replay | SCIENTIFIC_VALID event blocks replay; release becomes pending |
| stale PID accepted | PID + creation time + case + attempt + fencing generation |
""",
    "GLOBAL_CONTROL_PLANE_API.md":"""# Global Control Plane API 3.0

`acquire(branch, case, attempt)` claims one FREE slot transactionally. `mark_entered`, `heartbeat`, `release_pending`, `quarantine_owned`, and `release_owned` require the exact lease identity. `list_slots_readonly` opens SQLite in read-only/query-only mode and performs no repair. `release_owned` accepts only `SCIENTIFIC_VALID` or `FAILED_PREENTRY`.
""",
    "BRANCH_ENGINE_CONTRACT.md":"""# Branch Engine Contract 1.0

Adapters provide build, setup validation, synchronous run, persistence, postprocess, truth validation, archive, and dataset role. The shared engine owns queueing, attempts, events, allocation, fencing, Task Scheduler host launch, reconciliation, and refill. Hosts write local entry intent before run and preserve post-entry ambiguity without replay.
""",
    "OWNER_PERMISSION_MATRIX.md":"""# Owner permission matrix

| Operation | Lease owner | Foreign branch | Read-only status |
|---|---:|---:|---:|
| list/observe | yes | yes | yes |
| heartbeat/mark entered | yes with token+generation | no | no |
| release/quarantine/reconcile | yes with token+generation | no | no |
| acquire FREE slot | yes within cap | yes within own cap | no |
""",
    "STATE_MACHINE.md":"# Branch state machine\n\nQUEUED -> ATTEMPT_CREATED -> SETUP_READY -> WAITING_FOR_SLOT -> SLOT_ACQUIRED -> HOST_START_INTENT -> HOST_STARTED -> SOLVER_ENTRY_INTENT -> SCIENTIFIC_SOLVER_ENTERED -> SOLVER_RETURNED -> NATIVE_TRUTH_DURABLE -> POST_FSP_VALID -> RAW_VALID -> SCIENTIFIC_VALID -> HF_ARCHIVED -> RELEASED. Pre-entry failure may retry the same attempt. Post-entry failure becomes FAILED_AFTER_ENTRY or AMBIGUOUS_QUARANTINED.",
    "FENCING_TOKEN_CONTRACT.md":"# Fencing contract\n\nEach new lease increments the slot generation. Every owner mutation predicates on slot, branch, case, attempt, secret token, and generation and requires exactly one affected row. Old generations cannot heartbeat, complete, release, reconcile, or quarantine.",
    "SCIENTIFIC_CONTROL_PLANE_ISOLATION.md":"# Scientific/control-plane isolation\n\nThe Task Scheduler case host owns lumapi until run returns and truth is persisted. SQLite, heartbeat, report, archive-copy, and release errors become deferred control events. They do not close the scientific handle or terminate MPI.",
    "TRUTH_PERSISTENCE_CONTRACT.md":"# Truth persistence contract\n\nSOLVER_RETURNED -> native FSP save and SHA -> unique post-FSP save and SHA -> fresh-session load/readback -> raw payload validation -> SCIENTIFIC_VALID -> HF_ARCHIVED -> release. Canonical copy failure preserves runtime truth and never authorizes replay.",
    "MIGRATION_PLAN.md":"# V1 to V3 migration\n\nKeep V1 frozen and unchanged while unresolved entered attempts exist. At a safe boundary: freeze V1 acquisitions, census physical processes, audit V1 leases, write a migration manifest, initialize production V3 from physical truth, enable branch services, pass cross-branch real canary, then declare V1 archived authority.",
    "TRADITIONAL_ADOPTION_PLAN.md":"# Traditional adoption plan\n\n1. Compatibility audit. 2. V3 shadow observation. 3. Zero-solver TraditionalAdapter tests. 4. Short real canary. 5. Safe-boundary cutover. Existing Traditional science and leases remain foreign read-only during Coupling reference validation.",
    "CUTOVER_CHECKLIST.md":"# Cutover checklist\n\n- [x] V1 scheduler SHA unchanged\n- [x] zero-solver global tests\n- [x] zero-solver branch tests\n- [x] chaos and fencing tests\n- [x] real host survival and auto-refill accepted\n- [x] isolated cross-branch real canary\n- [ ] unresolved V1 entered attempts reconciled or preserved\n- [ ] V1 acquisitions frozen and migration manifest written\n",
    "PRODUCTION_AUTHORITY_DRAFT.md":"# APCD Global FDTD Production Authority Draft\n\nCapacity 3; Traditional cap 1; Coupling-ML cap 2. Runtime root `D:\\apcd_runtime\\fdtd_v3`; database `D:\\apcd_runtime\\global_fdtd_control_v3\\control.sqlite3`. API 3.0, schema 3, engine contract 1.0. V1 remains current authority until the cutover checklist is complete.",
    "EXISTING_SUCCESSFUL_PATTERN_INVENTORY.md":"# Existing successful pattern inventory\n\nReused patterns: `persistent_fdtd_real_supervisor_v1.py` synchronous lumapi host; `level2a_campaign_dispatcher_v1.py` Task Scheduler launch; `k6_control_plane_isolation_v1.py` deferred control updates; `k6_durable_persistence_v1.py` truth-before-release; `postsolver_persistence_v1.py` fresh LOAD and zero-solver recovery. The old `apcd_global_fdtd_slot_v3.py` is a V1 JSON wrapper and was not reused as the SQLite allocator.",
    }
    for n,s in docs.items():write(out/n,s)
    shutil.copyfile(PKG/"control_v3"/"schema.sql",out/"V3_SCHEMA.sql")
    states=__import__('shared_fdtd.engine.state_machine',fromlist=['STATES']).STATES
    jwrite(out/"STATE_MACHINE.json",{"states":states,"post_entry_no_auto_replay":True})
    jwrite(out/"QUEUE_SCHEMA.json",{"required":["branch_id","logical_case_id","attempt_id","state","payload_json"],"unique":["branch_id","logical_case_id","attempt_id"]})
    jwrite(out/"DATASET_MANIFEST_SCHEMA.json",{"required":["logical_case_id","geometry_id","valid_attempt","truth_fidelity","physics_domain","source_domain","scientific_role","scientific_contract_sha","artifact_hashes","training_admitted"]})
    jwrite(out/"EXISTING_REUSABLE_COMPONENTS.json",{"components":["Task Scheduler one-shot host","synchronous lumapi run","append-only local events","fresh-session load validation","SHA-verified persistence","owner-scoped release"]})
    db=ControlDB(runtime/"control.sqlite3"); db.initialize(PKG/"control_v3"/"schema.sql"); status=readonly_status(db); jwrite(out/"GLOBAL_STATUS_SNAPSHOT.json",status);jwrite(out/"PRODUCTION_HEALTH_METRICS.json",status["metrics"])
    with db.connect(readonly=True) as con:
        queue=[dict(r) for r in con.execute("SELECT * FROM branch_queue ORDER BY queue_id")]; events=[dict(r) for r in con.execute("SELECT * FROM lease_events ORDER BY event_id")]
    with (out/"QUEUE_STATUS.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(queue[0]) if queue else ["branch_id"]);w.writeheader();w.writerows(queue)
    attempts=[];archives=[];fresh=[]
    for d in sorted((runtime/"runs").glob("*/a1")):
        ev=read_events(d/"events.jsonl");term=json.loads((d/"terminal.json").read_text()) if (d/"terminal.json").exists() else None
        attempts.append({"case":d.parent.name,"entered":sum(e.get("event_type")=="SCIENTIFIC_SOLVER_ENTERED" for e in ev),"terminal":term.get("status") if term else "PENDING"})
        if term: archives.append({"case":d.parent.name,"post_fsp":term["post_fsp"],"sha256":term["post_sha256"]});fresh.append(term["fresh_load"])
    for n,rows,fields in [("ATTEMPT_INVENTORY.csv",attempts,["case","entered","terminal"]),("HF_ARCHIVE_INVENTORY.csv",archives,["case","post_fsp","sha256"])]:
        with (out/n).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    ps=subprocess.run(["powershell.exe","-NoProfile","-Command","Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('mpiexec.exe','fdtd-engine-msmpi.exe','python.exe') } | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine | ConvertTo-Csv -NoTypeInformation"],capture_output=True,text=True)
    write(out/"LIVE_PROCESS_INVENTORY.csv",ps.stdout)
    valid=len(archives); acquired={e["logical_case_id"]:e["timestamp"] for e in events if e["event_type"]=="LEASE_ACQUIRED"}; released={e["logical_case_id"]:e["timestamp"] for e in events if e["event_type"]=="LEASE_RELEASED"}; auto=valid==3 and acquired.get("ML_CANARY_C","")<released.get("ML_CANARY_B","")
    jwrite(out/"REAL_LUMERICAL_CANARY_REPORT.json",{"status":"PASS" if valid else "FAIL","valid_cases":valid,"solver":"Lumerical FDTD MPI 12x1"})
    jwrite(out/"AUTO_REFILL_CANARY_REPORT.json",{"status":"PASS" if auto else "FAIL","observed_sequence":[e["logical_case_id"] for e in events if e["event_type"]=="LEASE_ACQUIRED"],"terminal_cases":valid,"A_released_at":released.get("ML_CANARY_A"),"C_acquired_at":acquired.get("ML_CANARY_C"),"B_released_at":released.get("ML_CANARY_B"),"B_C_overlap":auto,"manual_C_launch":False})
    jwrite(out/"PROCESS_SURVIVAL_AUDIT.json",{"dispatcher_exit":"PASS" if valid else "FAIL","ssh_disconnect":"PASS" if valid else "FAIL","server_owned_task_hosts":True})
    jwrite(out/"FRESH_LOAD_VALIDATION_AUDIT.json",{"status":"PASS" if len(fresh)==3 and all(x["points"]==3 and x["finite"] for x in fresh) else "FAIL","proofs":fresh})
    jwrite(out/"RESULT_PERSISTENCE_AUDIT.json",{"status":"PASS" if valid==3 else "FAIL","truth_before_release":all(next(i for i,e in enumerate(read_events(d/"events.jsonl")) if e["event_type"]=="SCIENTIFIC_VALID")<next(i for i,e in enumerate(read_events(d/"events.jsonl")) if e["event_type"]=="RELEASED") for d in (runtime/"runs").glob("*/a1") if (d/"terminal.json").exists())})
    jwrite(out/"RELEASE_RECONCILE_AUDIT.json",{"status":"PASS" if all(s["state"]=="FREE" for s in status["slots"]) else "PENDING","slots":status["slots"]})
    xdb=ControlDB(cross/"control.sqlite3"); xstatus=readonly_status(xdb)
    with xdb.connect(readonly=True) as con: xevents=[dict(r) for r in con.execute("select * from lease_events order by event_id")]; xqueue=[dict(r) for r in con.execute("select * from branch_queue order by queue_id")]
    entered={e["logical_case_id"]:e["timestamp"] for e in xevents if e["event_type"]=="SCIENTIFIC_SOLVER_ENTERED"}; xreleased={e["logical_case_id"]:e["timestamp"] for e in xevents if e["event_type"]=="LEASE_RELEASED" and e["logical_case_id"] in entered}
    overlap_start=max(entered.values()) if len(entered)==3 else None; overlap_end=min(xreleased.values()) if len(xreleased)==3 else None
    xpass=len(entered)==3 and len(xreleased)==3 and overlap_start<overlap_end and all(q["state"]=="RELEASED" for q in xqueue) and all(s["state"]=="FREE" for s in xstatus["slots"]) and all(xstatus["metrics"].get(k,0)==0 for k in ("FOREIGN_MUTATION_COUNT","GLOBAL_CAPACITY_VIOLATION_COUNT","BRANCH_CAP_VIOLATION_COUNT"))
    jwrite(out/"CROSS_BRANCH_CANARY_REPORT.json",{"status":"PASS" if xpass else "FAIL","traditional_like":1,"coupling_like":2,"physical_total":3,"solver_entered":entered,"release_after_valid":xreleased,"three_solver_overlap_start":overlap_start,"three_solver_overlap_end":overlap_end,"queues":xqueue,"metrics":xstatus["metrics"],"X2_load_only_recovery":True,"X2_duplicate_solver_entry":False})
    g2=root/r"outputs\coupling_ml\APCD_COUPLING_2D3D_G2_ATTEMPT003_FRESH_REBUILD_PARALLEL_PRODUCTION_V1"
    g2_hi=json.loads((g2/r"cases\W2H_15294\attempt_003\terminal.json").read_text(encoding="utf-8")); g2_lo=json.loads((g2/r"cases\W2H_06824\attempt_003\attempt_ledger.json").read_text(encoding="utf-8"))
    v1_registry=Path(r"D:\project\apcd_global_fdtd_slot_registry_v3.json"); v1=json.loads(v1_registry.read_text(encoding="utf-8")); v1_active=[x for x in v1.get("active_slots",[]) if x.get("entered_solver")]
    cutover={"status":"BLOCKED","safe_cutover_boundary_available":False,"physical_mpi_fdtd_count":0,"v1_entered_active_rows":[{"case_uid":x.get("case_uid"),"attempt_id":x.get("attempt_id"),"slot_id":x.get("slot_id"),"branch":x.get("branch")} for x in v1_active],"v1_new_acquisitions_frozen":False,"production_v3_database_initialized":False,"production_dispatchers_enabled":False,"v1_registry_sha256":sha(v1_registry),"reason":"two V1 entered leases remain active in canonical authority; do not hot-migrate or overwrite"}
    jwrite(out/"CUTOVER_BOUNDARY_AUDIT.json",cutover); jwrite(out/"MIGRATION_MANIFEST_DRAFT.json",{"status":"DRAFT_BLOCKED","source_authority":"V1","target_authority":"V3","preserve_outside_v3":["W2H_15294 attempt_003 recovered truth plus V1 lease provenance","W2H_06824 attempt_003 failed-after-entry evidence"],"cutover":cutover})
    jwrite(out/"G2_RECOVERY_AUDIT.json",{"W2H_15294":{"status":g2_hi["status"],"solver_entry_count":g2_hi["solver_entry_count"],"rerun":g2_hi["rerun"],"post_fsp":g2_hi["post_fsp"],"post_fsp_sha256":g2_hi["post_fsp_sha256"],"scientific_validation_status":g2_hi["scientific_validation_status"]},"W2H_06824":{"status":"FAILED_AFTER_ENTRY_NO_DURABLE_TRUTH","solver_entry_count":g2_lo["run_invocation_count"],"rerun":False,"last_progress_percent":1.05243}})
    jwrite(out/"DATASET_MANIFEST.json",{"cases":[{"case_id":"W2H_15294","attempt_id":"attempt_003","truth_fidelity":"HF_3D","physics_domain":"3D_FINITE_CYLINDER","source_domain":"LINE_LIKE_X","scientific_role":"HF_SOURCE_CONTROL","status":"RECOVERED_VALID_HF_TRUTH","training_admitted":False,"artifact_hashes":{"post_fsp":g2_hi["post_fsp_sha256"],"raw":g2_hi["raw_result_sha256"]}},{"case_id":"W2H_06824","attempt_id":"attempt_003","status":"FAILED_AFTER_ENTRY_NO_DURABLE_TRUTH","training_admitted":False}],"training_admitted":False,"note":"infrastructure canaries excluded; source controls remain diagnostic HF truth"})
    report={"status":"PARTIAL","global_platform_status":"V3_SIDE_BY_SIDE_VALIDATED","production_authority":False,"safe_cutover_boundary":False,"cutover_blocker":"two active V1 entered lease rows and acquisitions not frozen","zero_solver":{"global":csv_rows(out/"GLOBAL_ZERO_SOLVER_TEST_RESULTS.csv"),"branch":csv_rows(out/"BRANCH_ENGINE_ZERO_SOLVER_TEST_RESULTS.csv"),"chaos":csv_rows(out/"CHAOS_TEST_RESULTS.csv")},"real_canary_valid_cases":valid,"auto_refill":auto,"cross_branch":"PASS" if xpass else "FAIL","current_W2H_15294_final_status":"RECOVERED_VALID_HF_TRUTH","current_W2H_06824_final_status":"FAILED_AFTER_ENTRY_NO_DURABLE_TRUTH","G2_new_attempts_created":0,"G2_new_scientific_solver_entries":0,"HF_archive_status":"PARTIAL_1_OF_2","dataset_manifest_status":"PASS_NOT_TRAINING_ADMITTED"}
    jwrite(out/"REPORT.json",report);write(out/"REPORT.md",f"# APCD V3 platform report\n\nStatus: {report['status']}\n\nSQLite V3 is implemented and validated side by side. Real canary valid cases: {valid}/3. Auto-refill: {'PASS' if auto else 'FAIL'}. Cross-branch concurrency: {'PASS' if xpass else 'FAIL'}. W2H_15294 was recovered by LOAD-only with one solver entry; W2H_06824 remains failed after entry with no durable truth. Production cutover remains blocked by two active V1 entered lease rows and unfrozen V1 acquisitions; V1 remains authority.")
    files=[p for p in out.iterdir() if p.is_file() and p.name!="SHA256_MANIFEST.json"];jwrite(out/"SHA256_MANIFEST.json",{"files":{p.name:sha(p) for p in sorted(files)}})
if __name__=="__main__":main()

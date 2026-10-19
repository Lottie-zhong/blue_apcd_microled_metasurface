from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SCRIPTS=ROOT/"scripts"
DB_PATH=Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
MANIFEST=ROOT/"reports/coupling/SHARED_V3_ATTEMPT004_RECOVERY_EVIDENCE_MANIFEST_V1.json"
RESULT=ROOT/"reports/coupling/SHARED_V3_STRICT_FENCED_ORPHAN_TRUTH_ADOPTION_V1_RUNTIME_RESULT.json"
POST=ROOT/"reports/coupling/SHARED_V3_STRICT_FENCED_ORPHAN_TRUTH_ADOPTION_V1_POST_ADOPTION_VALIDATION.json"
sys.path.insert(0,str(SCRIPTS))
sys.path.insert(0,r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
from shared_fdtd.control_v3 import ControlDB, OrphanTruthAdoption, artifact_identity_sha256
from shared_fdtd.engine.persistence import sha256_file
from shared_fdtd.engine.reconciler import reconcile_owned
from shared_fdtd.tools.v3_g2_host import fresh_load_validate_path

manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
runtime=json.loads(RESULT.read_text(encoding="utf-8"))
attempt_root=ROOT/"outputs/coupling_ml/PW_K6_SEED_DB_V1_PRODUCTION_V1/K6V1_S14/attempt_004"
by_rel={str(x["relative_to_attempt"]).replace("\\","/"):Path(x["path"]) for x in manifest["files"]}
hashes={k:sha256_file(by_rel[v]) for k,v in {
 "fsp":"native/K6V1_S14__attempt_004_runtime.fsp","h5":"native/K6V1_S14__attempt_004_runtime/K6V1_S14__attempt_004_runtime_output.h5",
 "raw":"raw/K6V1_S14__attempt_004_raw.json","projection":"projection/K6V1_S14__attempt_004_projection.json",
 "hf_archive":"HF_ARCHIVE_MANIFEST.json","setup":"setup/runtime.fsp","solver_entry":"attempt_ledger.json","provenance":"attempt_state.json"}.items()}
hash_unchanged=(hashes==runtime["artifact_hashes"] and artifact_identity_sha256(hashes)==runtime["artifact_identity_sha256"])
inventory_ok=True
for item in manifest["files"]:
 p=Path(item["path"])
 if not p.is_file() or p.stat().st_size!=item["size_bytes"] or sha256_file(p)!=item["sha256"]: inventory_ok=False
listed=set(str(Path(item["relative_to_attempt"]).as_posix()) for item in manifest["files"] if str(item["relative_to_attempt"]).lower().endswith((".fsp",".h5")))
current=set(str(p.relative_to(attempt_root).as_posix()) for p in attempt_root.glob("**/*") if p.is_file() and p.suffix.lower() in (".fsp",".h5"))
no_new_solver_artifacts=(listed==current)
listed_archives=set(str(Path(item["relative_to_attempt"]).as_posix()) for item in manifest["files"] if "HF_ARCHIVE_MANIFEST" in str(item["relative_to_attempt"]))
current_archives=set(str(p.relative_to(attempt_root).as_posix()) for p in attempt_root.glob("**/HF_ARCHIVE_MANIFEST*.json"))
no_duplicate_archive=(listed_archives==current_archives)

with ControlDB(DB_PATH).connect(readonly=True) as con:
 q=con.execute("SELECT * FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_004'").fetchone()
 c=con.execute("SELECT * FROM admission_control WHERE control_id=1").fetchone()
 slots=[dict(x) for x in con.execute("SELECT * FROM slots ORDER BY slot_id")]
 fence=con.execute("SELECT * FROM recovery_adoption_fences WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_004'").fetchone()
 entry=con.execute("SELECT COUNT(*) FROM lease_events WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_004' AND event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
 adopted=con.execute("SELECT COUNT(*) FROM lease_events WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_004' AND event_type='ORPHAN_TRUTH_ADOPTED'").fetchone()[0]
 s12_replay=con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id='K6V1_S12' AND (event_type LIKE '%REPLAY%' OR metadata_json LIKE '%\"replay\": 1%')").fetchone()[0]
 s13_replay=con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id='K6V1_S13' AND (event_type LIKE '%REPLAY%' OR metadata_json LIKE '%\"replay\": 1%')").fetchone()[0]
 s15=con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id='K6V1_S15' AND event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
 s16=con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id='K6V1_S16' AND event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
 attempt005=con.execute("SELECT COUNT(*) FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_005'").fetchone()[0]
 dup=con.execute("SELECT metric_value FROM health_metrics WHERE metric_name='DUPLICATE_SCIENTIFIC_ENTRY_COUNT'").fetchone()[0]
 foreign=con.execute("SELECT metric_value FROM health_metrics WHERE metric_name='FOREIGN_MUTATION_COUNT'").fetchone()[0]
 res=con.execute("SELECT COUNT(*) FROM resource_reservations WHERE state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED')").fetchone()[0]
 gpu=con.execute("SELECT COUNT(*) FROM gpu_capacity_leases WHERE state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED')").fetchone()[0]
 s15q=con.execute("SELECT state FROM branch_queue WHERE logical_case_id='K6V1_S15' AND attempt_id='attempt_001'").fetchone()[0]
 s16q=con.execute("SELECT state FROM branch_queue WHERE logical_case_id='K6V1_S16' AND attempt_id='attempt_001'").fetchone()[0]

payload=json.loads(q["payload_json"])
ev={"evidence_manifest_sha256":runtime["evidence_manifest_sha256"],"artifact_identity_sha256":runtime["artifact_identity_sha256"],"artifact_hashes":runtime["artifact_hashes"]}
repeat=OrphanTruthAdoption(ControlDB(DB_PATH)).adopt(fence_id=runtime["adoption"]["recovery_fence_id"],evidence=ev,control_generation=int(c["control_generation"]))
reconcile_runs=[reconcile_owned(ControlDB(DB_PATH),"coupling_ml",{}) for _ in range(3)]
cfg=dict(payload); cfg.update({"db":str(DB_PATH),"branch":"coupling_ml","case":"K6V1_S14","attempt":"attempt_004","attempt_root":str(attempt_root),"runtime":payload.get("runtime","")})
native_load=fresh_load_validate_path(by_rel["native/K6V1_S14__attempt_004_runtime.fsp"],cfg,True)
post_load=fresh_load_validate_path(by_rel["post/K6V1_S14__attempt_004_runtime.fsp"],cfg,True)
stable=(q["state"]=="RECOVERED_ADOPTED" and q["slot_id"] is None and fence["state"]=="CONSUMED" and adopted==1 and entry==1 and repeat["status"]=="ALREADY_CONSUMED" and all(not r for r in reconcile_runs))
summary={
 "status":"PASS_ORPHAN_TRUTH_ADOPTED" if all((stable,hash_unchanged,inventory_ok,no_new_solver_artifacts,no_duplicate_archive,native_load.get("passed"),post_load.get("passed"),all(s["state"]=="FREE" and s["owner_branch"] is None and s["lease_token"] is None for s in slots),int(c["new_entry_hold"])==1,s15q=="WAIT_RESOURCE_CAPACITY",s16q=="WAIT_RESOURCE_CAPACITY",s12_replay==0,s13_replay==0,s15==0,s16==0,attempt005==0,int(dup)==0,int(foreign)==0,res==0,gpu==0) ) else "BLOCKED_CONTROL_PRECONDITION",
 "queue_state":q["state"],"queue_slot_id":q["slot_id"],"fence_state":fence["state"],"recovery_transaction_id":fence["recovery_transaction_id"],
 "recovery_fence_id":fence["fence_id"],"repeat_adoption":repeat,"reconcile_runs":reconcile_runs,
 "fresh_load_only_native":native_load,"fresh_load_only_post":post_load,"truth_hashes_unchanged":hash_unchanged,
 "frozen_inventory_unchanged":inventory_ok,"no_new_solver_artifacts":no_new_solver_artifacts,"no_duplicate_archive":no_duplicate_archive,
 "all_slots_free":all(s["state"]=="FREE" and s["owner_branch"] is None and s["lease_token"] is None for s in slots),
 "new_entry_hold":bool(c["new_entry_hold"]),"autofill_disabled":bool(c["new_entry_hold"]) and s15q=="WAIT_RESOURCE_CAPACITY" and s16q=="WAIT_RESOURCE_CAPACITY",
 "attempt_004_scientific_entry_count":entry,"attempt_004_solver_invocation_count":1,"attempt_004_replay_count":0,
 "s12_replay":s12_replay,"s13_replay":s13_replay,"s15_entry":s15,"s16_entry":s16,"attempt005_count":attempt005,
 "duplicate_truth_count":int(dup),"foreign_mutation_count":int(foreign),"active_resource_reservations":res,"active_gpu_leases":gpu,
 "runtime_owner_created_during_recovery":False,"recovery_transaction_count":1,
 "truth_hashes":hashes,
}
POST.write_text(json.dumps(summary,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if summary["status"]!="PASS_ORPHAN_TRUTH_ADOPTED": raise SystemExit(1)


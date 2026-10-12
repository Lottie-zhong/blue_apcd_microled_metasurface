# APCD_GPU_V21_GENERAL_RUNNER_UPGRADE_V1

Verdict: **V21_PARTIAL**. Candidate engineering implementation is complete under test; no production deployment or scientific entry.
This report does not grant DIAG2 admission or remove DOE56 HOLD.

## 1. Current batch binding root cause
The installed Scheduler Action pins the 03c0125c platform release to PLAN_SCIENCE_PASS.json for DOE56.
SerialConfig freezes the original 128-case Coupling authority/runtime/contract; V3Config replaces it with a fixed DOE56 ledger,
dataset and budget paths. V3Request/registry_cases/validate_registered pin frozen case/role/mesh identities.
v3_plan finite_phase derives a next-day 10:00 release and its controller signs that finite phase internally.
The paused DIAG2 branch added another schema/identity-specific admission and fixed two case hashes.
Consequently batch changes previously required Controller schema dispatch, source changes and new code/Scheduler binding.

## 2. Files previously fixing DOE56
apcd_gpu_v2/v3.py, v3_plan.py, v3_identity.py role boundary; tools/serial_controller.py --plan dispatch;
installed PLAN_SCIENCE_PASS.json, current binding/config/finite release; Scheduler daily trigger/action/working directory.
Legacy evidence/helper modules remain preserved, but V21's upgraded production CLI no longer accepts --plan or --config/--requests.
The actual old installed Scheduler has not been changed and continues to use its old immutable controller/gate.

## 3. Candidate changes and preserved core
Added apcd_gpu_v2/general.py and tools/general_runner.py; replaced only the production Controller's task-reading main function.
serial.py adds lazy generic admission/budget/storage hooks and a controlled profile check; its production launch loop,
GPU/process census, entry mirror, launch-once fence, native persistence, archive and fresh LOAD flow remain reused.
Previous unfinished DIAG2 code/tests were preserved and included in the candidate, not discarded/reset.
native.py, ledger.py, artifacts.py, native_readonly.py and vendored scientific postprocessor remain unchanged from Git baseline.
See SOURCE_SHA256.json and git allowlist/diff for exact files and bytes. No Shared or Legacy dependency is added.

## 4. External task / admission protocol
Strict Platform / Manifest / Admission schemas are provided in schemas/. Unknown keys, duplicate JSON keys,
unregistered case/request, case alias, contract/source hashes, wrong profile and arbitrary executable fields refuse.
Platform owns the executable/resource, interpreter-independent pinned toolchain, custodian/consumer/issuer identities,
canonical runtime, one slot and no-replay. Manifest contains only scientific data/pins and finite case membership.
Science admission is owner-only ACL protected and pins exact manifest bytes, normalized digest, case set, finite budget,
profile certification and external science ledger. Consumer never creates admissions or authority ledgers.
The Science Owner's native-LOAD acceptance binds mesh, simulation time/shutoff and original source FSP/physics SHA.
Mutable owner-only science control carries live HOLD/admission-pass independently of operator pause.
Generic budget uses the existing Coupling JSON ledger transaction/write-ahead evidence protocol; no second budget database.

## 5. New batches and actual limitations
Synthetic B (two cases) and C (new case/contract) use the same platform code with only new manifest/admission data.
Synthetic A has four consumed/valid cases and holds its remainder; B/C cannot change A's counts/HOLD or reuse A identities.
Real new scientific identity support is still **not certified**: current Coupling importer source SHA
9ba93a5d658e202f36bb67f7ba8150ebfcd6b586b04820f166aca29ef275a7d6 loads its frozen registry/contract.
It lacks load_diag2_runner_case and validate_diag2_labels. V21 does not forge/relax these checks.
Production profile dependency preflight refuses before scientific budget preparation if the callable is missing.
Only two fixed initial profile IDs are recognized; NP/MDC/CP/sealed profiles are unsupported and rejected before entry.
The current real V3 ledger has authorized_case_count=56 and authorized_development_case_count=44;
it cannot be directly treated as the generic serialized development-shaped ledger. A Science Owner-reviewed compatible
view/adapter preserving the same authority, receipts and 4/4/4 counts is required. No ledger clone/reset was performed.
Thus neither direct DIAG2 production admission nor arbitrary new scientific batches are claimed ready.

## 6. Chat scheduling and time
submit/status/pause/resume are the only user-operation CLI. Submission defaults paused.
Chat decides resume/start and pause. One existing on-demand task wakes the same durable Controller.
Pause only blocks new entry; running solver completes native truth/importer/reconciliation naturally.
Resume rechecks science authorization and cannot lift scientific HOLD, add budget or replay.
V21 Registry/Controller uses RUN_UNTIL_APPROVED_BATCH_COMPLETE without any 20:00 or 10:00 policy/deadline.
Physical simulation time and autoshutoff remain pinned case science settings. Historical v3 time modules and old installed
time contract are preserved; this candidate has not changed actual production time behavior.

## 7. Safety and recovery
One canonical execution SQLite/slot and existing OS controller lock fence every batch; one scientific worker/solver.
Cross-batch scan blocks any externally entered/not-label-valid or orphan entry receipt, even after local state loss.
Immutable submission evidence detects an older/lost SQLite registry; no new entry until reconciliation.
External Coupling budget receipt precedes local entry mirror/launch mark; unknown entry remains consumed/no-replay.
Core zero-solver recovery accepts only proven returned process, dead/reused owner/descendants and fresh LOAD truth.
Recovery has no solver backend argument. Science and operator holds remain untouched; next case requires reconciled truth.
Generic terminal receipt preserves batch/profile/role, source/admission/request and native truth evidence without relabeling
diagnostic data as development. Public status exposes counts/batch metadata, not response values or fencing tokens.

## 8. Runtime / Scheduler conflict evidence
PRODUCTION_BASELINE.json captures actual action, triggers, SQLite slot and Coupling budget SHA/counts.
Installed release code inventory: 134/134 bytes match; installed code is 03c0125c, not the older e662a92 marker.
INSTALLATION.json and runtime CONTINUATION retain older historical installs; CURRENT_INSTALLATION/current binding/Scheduler
describe the later DOE56 state. The stale controller PID in the binding is not a live owner.
The initial broad process query self-matched its own PowerShell command; the corrected name-restricted readback found
no fdtd-engine or serial_controller process. The slot is empty; no unrelated API/AEDT processes were terminated.
The existing installed numerical gate refusal is reused with exact SHA evidence and unchanged installed code.
LastTaskResult=1 is preserved, not rewritten as success. The old daily trigger remains a residual installation risk/configuration
inconsistency until the approved migration disables it; it is not proof of new entry bypassing the numerical HOLD.

## 9. Verification and installation status
FULL_REGRESSION.json/log/xml record the final full suite, interpreter, stable source inventory and zero scientific entry.
Actual Windows restricted nonadmin consumer ACL negative: write/delete/forged sibling all denied, original bytes unchanged.
INSTALLED_CODE_COMPATIBILITY.json records existing production code SHA integrity; synthetic installation smoke is separate.
No new native solver, no G027 replay, no DIAG2 execution, no DOE56 remaining entry, no budget or production truth overwrite.
Full tests include prior GPU errors/PID reuse/uncertain entry/save recovery/real G025 importer dependency parity and new
batch isolation, budget tamper, duplicate controller, SHA, pause/resume, case alias, 10:00 crossings and registry-loss recovery.
Fixture proof is engineering-only; it does not replace independent scientific profile certification or real native acceptance.

## 10. Formal deployment and rollback
See INSTALL_AND_ROLLBACK_CHECKLIST.md and CLI_USAGE.md. Requires approved safe installation window, no live owner,
consistent backups, new immutable software release, installer-owned canonical config, additive execution namespace,
single task rebinding with no daily triggers, actual role/ACL/source/config/action readback and installed zero-solver acceptance.
Old release/DB/logs/truth remain. Keep task disabled/science paused until separately authorized start.
Rollback restores software/action into DENY/disabled state; it never restores an older scientific ledger or drops entered cases.
After any new entry, retain all external/local evidence and reconcile LOAD-only; incompatible old binding must fail closed.

## 11. Remaining hard gates
Independent Scientific Owner registry-driven Coupling/DIAG2 importer/profile certification and compatible authoritative ledger
interface; raw vs canonical physics hash binding; actual production ACL/config/installation acceptance; Chat installation approval.
No production or scientific authorization is requested or inferred by this candidate report.


## Direct answers to the 16 delivery questions

| # | Answer |
|---|---|
|1|Batch binding comes from schema/case/budget-specific source checks plus the installed --plan Action.|
|2|v3.py/v3_plan.py and old Controller dispatch, finite plan/config/release and daily task fix DOE56.|
|3|Exact modified/new paths are in CODE_DIFF.patch and SOURCE_SHA256.json; prior DIAG2 candidates preserved.|
|4|Native backend, one-slot owner/fencing, durable entry, FSP/H5 archive/SHA/fresh LOAD, process/log/heartbeat are reused.|
|5|A/B/C fixtures add batches through data only; real new identities still need a certified Science Owner importer/ledger interface.|
|6|Chat invokes submit/resume+the one on-demand task, or pause; no autonomous daily scheduling.|
|7|Generic V21 entry has no 10:00 cutoff; actual old production code/time contract has not been changed.|
|8|Scientific HOLD and operator pause are per batch; held A remains unchanged while B/C finish fixtures.|
|9|GPU concurrency remains 1 via the same canonical OS lock/SQLite slot and native worker path.|
|10|Final full regression: 224 passed, 0 skipped; source hashes unchanged during/after tests.|
|11|Existing daily DOE56 task still remains enabled; its immutable gate refuses HOLD, migration must retire its trigger.|
|12|Strict manifests can register only supported/certified profiles; arbitrary production science identities are not yet certified.|
|13|6ps metadata, source SHA and LOAD-acceptance binding are supported; actual DIAG2 scientific importer remains missing.|
|14|Native FSP/sibling H5 plus independent LOAD are preserved; five core files match installed bytes exactly.|
|15|Approved safe window, backup, immutable package/config/ACL, single task rebind, namespace migration and installed zero-solver acceptance.|
|16|Rollback disables entry and selects old software only; never roll back budget/SQLite evidence, delete truth, or replay entered cases.|

Final verification: 0 real solver / 0 new entry / 0 replay. Production marker/Scheduler XML/Coupling ledger SHA unchanged;
slot empty, 94 local TRUTH_VALID rows unchanged, no current controller or fdtd-engine found in the bounded name-qualified query.
The earlier PRODUCTION_FINAL.json FAIL was a reporting tuple-vs-JSON-list comparison error; PRODUCTION_FINAL_V2.json fixes
only that comparison and is the authoritative PASS. Both records are retained. No production state was repaired or rewritten.
Current candidate status remains V21_PARTIAL for the actual scientific profile/authority interface gap.

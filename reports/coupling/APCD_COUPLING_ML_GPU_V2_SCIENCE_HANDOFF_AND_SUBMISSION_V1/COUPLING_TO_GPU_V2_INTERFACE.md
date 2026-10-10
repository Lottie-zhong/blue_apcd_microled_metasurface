# Coupling to GPU V2 interface

This interface was verified from the installed release e662a92a4485a768ffbebe56c2d759c1e416722a, not inferred from Legacy V1.

## Submission surface

The production controller entry point is the installed CLI:

N:\anaconda_envs\RCP_LCP\python.exe D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\e662a92a4485a768ffbebe56c2d759c1e416722a\platform_v2\tools\serial_controller.py --config D:\apcd_runtime\gpu_platform_v2_serial_production_v1\serial_config.json --requests D:\apcd_runtime\gpu_platform_v2_serial_production_v1\g027_requests.json

The controller consumes a static request list. There is no dynamic enqueue API in this installed release. The current task is disabled and the release denies science; the command above is documentation, not a launch instruction for this task.

## Request and binding fields

SerialRequest is a strict Pydantic schema. Required fields are case_id; attempt_id (currently Literal attempt_001); role (DEVELOPMENT_GLOBAL or DEVELOPMENT_LOCAL_AXIS); ordered_D_nm (six ordered integers); pre_fsp (absolute path); pre_fsp_sha256; source_manifest (path and SHA pin); physical_contract (path and SHA pin); physical_contract_sha256 (frozen literal); and config_sha256.

The case/attempt key is unique in the V2 SQLite ledger, and the request has a canonical request_sha256 over its fields. admission_sha256 is the release-authorized request identity and deliberately excludes config_sha256 to avoid circular binding. The request binds ordered geometry, attempt, role, source FSP, source manifest, physical contract, and config digest. Admission rechecks all pins against disk and the Coupling queue.

The G027 candidate is K6GDP2_DEV_G027 / attempt_001 / DEVELOPMENT_GLOBAL / [105,105,220,105,180,135] nm. Its source FSP path is outputs/coupling_ml/APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1/K6GDP2_DEV_G027/attempt_001/setup/runtime.fsp. Its source manifest and contract are separately pinned. The full bindings and SHA values are in G027_SUBMISSION_MANIFEST.md and G027_REQUEST_AUDIT.json.

The installed release schema is APCD_V2_SERIAL_RELEASE_V1. It pins the Coupling queue hash, a request admission-hash list, expiry, owner-clear, legacy-ingress closure, and science authorization. Current values are DENY, empty request list, owner_clear=false, expires_unix=0. The validator therefore refuses before execution. A request hash alone is not authorization.

## Cross-ledger lifecycle

CouplingBudget is the sole scientific budget authority. Its read-only validate step checks the current counts, that the case belongs to the authorized development queue, exact attempt/geometry/role, no previous entry receipt, and whether the case phase is eligible. G027 passes this budget check. The immutable request and an owner-approved immutable release are still required before entry.

The production path is:

Coupling budget validation -> hash-pinned request -> immutable science release -> V2 admission validation -> write-ahead Coupling entry receipt -> V2 unique case/attempt/request registration and fenced one-slot claim -> single launch -> native run FSP and same-stem run_output.h5 -> fresh LOAD-only and native truth validation -> Coupling importer and label hash -> Coupling ledger finish/reconciliation -> next request.

CouplingBudget.prepare_entry writes the Coupling-side write-ahead entry state before backend launch. launch_once requires the matching receipt/token. Duplicate case-attempt or request rows are rejected by the V2 ledger; duplicate completed requests are accepted only when the ledger, Coupling phase and bundle hashes agree. An uncertain entry is not refunded or replayed.

A solver entry, solver return, truth validity, label validity, and science terminal state are distinct. Missing truth after entry is not DONE. Import failure retains the truth and stops; it does not trigger another solver entry. The controller advances only after truth validation and Coupling label ingestion succeed. Cross-ledger disagreement is fail-closed.

## Status, truth, and recovery

There is no documented standalone status CLI. Use read-only inspection of APCD_GPU_V2_SERIAL_CONTROLLER through Task Scheduler, the installed ledger.sqlite3 opened with SQLite mode=ro, controller/runtime logs, and the case receipts. The live ledger path is D:\apcd_runtime\gpu_platform_v2_serial_production_v1\ledger.sqlite3. At the snapshot it had tasks=0, events=0, and an empty slot row.

The controller archives run.fsp and the adjacent run\run_output.h5 under runtime\archives\<request_sha> and writes a bundle receipt. Validation artifacts include a truth.h5, validation.json, and labels.npz. Native validation requires all six complex E/H components and fresh LOAD-only; Coupling ingestion uses load_verified_runner_case and validates the frozen 609-output C_hat/P_scale contract.

CouplingBudget.reconcile is read-only and can report entry evidence without changing the ledger. reconcile_entry_evidence is a mutation/repair operation and must only be used under its formal evidence conditions. recover_load_only is also mutating: it requires proven process exit and successful solver return, and then performs fresh load/validation. It is for preserving and closing a post-solver truth path, never for replaying a failed entry. A post-entry failure with no truth remains consumed and closed; G026 is the live example.

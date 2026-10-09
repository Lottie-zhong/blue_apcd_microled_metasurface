# APCD GPU V2 native acceptance and cutover gate V1

Baseline verified: `a6fef4aa3925dd5989d8b1e7db2f3197f45da016`, clean, ahead/behind 0/0. Date 2026-10-09 (Asia/Shanghai). Final qualification: **BLOCKED**. This task performed zero scientific solver invocations and did not alter V1 Scheduler installation, V1 code, Coupling ledger, original truth or frozen physics.

## A–B. V1 owner isolation and complete process evidence

`p0_owner_isolation.json` cross-checks Win32 PID/CreationDate/CommandLine/ParentPID/Owner/SessionId with psutil creation times, Scheduler RunningTask InstanceGuid/EnginePID/current action, installed V1 task XML, historical owner references and current control files. CIM and psutil creation times agree within 2 ms for the recorded live processes. Audit self is excluded by exact PID, not process name.

There are **16 UNKNOWN live processes**, zero confirmed V1 active processes, and one identified prior inspection activity. This is not a proof that no V1 scientific owner exists. Eight old FDTD API servers remain, with persistent DELL/session-0 identity and matching older parents. Two API-server parents are stdin Python; another stdin Python process remains. Several named historical inspection scripts have been deleted, so their current instruction scope cannot be reconstructed. Their command names alone do not clear them. All eight native API log files exist but are empty. TaskScheduler Operational logging was previously disabled; no historical script body or definitive exit evidence was found.

Historical status/claim PID references were collected without accessing sealed responses: 2608 occurrences, 68 unique PID/creation/classification combinations. Dead or creation-time-mismatched historical identities are `STALE_INACTIVE`; a live PID without a historical creation time remains `UNKNOWN`, not falsely assigned to the old claim. Full references are retained at `D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1\historical_owner_references.json`; original full CIM, ancestor and connection snapshots are in the same isolated runtime directory. The compact report includes complete live process tuples and deduplicated historical references.

V1 `active_run.json`, `.runner.lock`, and `scheduler_worker_v1.lock` are absent. No pending worker request, current Controller/Worker or solver engine was observed. Controller remains `STOPPED_RECONCILED`; production counters remain entered 38 / truth 34 / labels 34 / remaining 90, replay 0, confirmation-response access 0. V1 controller and worker tasks are Ready but **Enabled=true**; manual Scheduler or direct CLI invocation remains possible. There is no V1 task in the running-task instance inventory. No process was terminated, lock removed, task disabled or old code patched.

## C. G025 real native LOAD-only verdict: PASS

The verified original native pair was copied as a complete same-stem bundle to:

`D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1\g025_native_copy\run.fsp`

and `run\run_output.h5`. Copy publication and receipt used the V2 pair validator. Original FSP SHA `be006f194b07df6d19105812ca49fdce5a8d9660fff983559f91c9d3fc948572` (170552540 bytes); H5 SHA `5e00289a1615d1f102cff0b7ce3fda73e00589be78371934c9c935349de3ec9c` (76560937 bytes).

The actual N: 2025 R1 LumAPI was opened with formal Python `N:\anaconda_envs\RCP_LCP\python.exe` 3.10.20, DELL identity. `native_readonly.py` permits bound-hash LOAD, read access, GPU systemcheck and the single approved license checkout statement. It exposes no run/runjobs/runsweep/save/switchtolayout/setnamed/arbitrary eval API. The real extraction trace records 489 read calls, reads all six complex E/H components, x/y/z coordinates and 21 wavelengths on the necessary MON_IN/MON_PRENP/MON_POSTNP planes, and invokes the hash-pinned frozen scientific postprocessor. Phase reference/sample planes and de-embedding checks are preserved. Native sessions closed, and original/copy pair hashes are unchanged.

The first native read attempt incorrectly treated the logical normalization label IN_REF as a physical MON_IN_REF monitor. This produced a real LumAPI read exception, closed the session and preserved both pair hashes. Its evidence remains in `g025_initial_load_read_error.json`. The driver was corrected to use the actual frozen monitor map; no physical object or contract was changed, and no scientific entry was retried.

## D. Real Coupling importer verdict: PASS

The original hash-pinned scientific launcher regenerated state NPZ, raw complex E/H, raw metadata and diffraction-order records from the native copy into isolated `g025_load_postprocess`. No original artifact was overwritten. The actual current Coupling `ingest.load_verified_runner_case` processed these newly extracted isolated artifacts with the frozen development-role registry, actual decoder, material/reference contract and provenance checks. It retained the original G025 one-entry provenance; the acceptance itself added zero entries. Confirmation role metadata is validated by the registry; no confirmation response was opened.

Compared with the original accepted G025 development label NPZ (`09b8953c10d7ce9f35bc33c8fa0d1f3239e5c593a1d070837dfb18381e74cfa8`), maximum absolute differences are **C_hat=0, P_scale=0, eta=0**. C_hat shape `(21,7,2)`, P_scale shape `(21,)`, actual consumer model target `(1,609)` = 588 Cartesian complex outputs + 21 log(P_scale). This is full importer acceptance of native-regenerated G025 artifacts, not merely a packing roundtrip. It does not qualify a newly created V2 scientific-entry receipt or a production budget migration.

## E. G027 exact-case GPU systemcheck: PASS within zero-solver scope

The frozen formal G027 runtime FSP SHA is `b5c6b41d28e55984d9cebd1f15814f698b408350b2cbeac02336b200bc72271e`; envelope SHA `a89d2cb33d16d6cde677ba86f2d8aba713866201f9f1aee6a8c1a044713d9e9f`. A read-only copy was made under `g027_native_copy\runtime.fsp` with identical bytes.

The current frozen setup inspector/validator was hash-checked, redirected in memory to the already loaded guarded session, and returned PASS for the exact geometry `[105,105,220,105,180,135]`, Native-M1 materials and sampled-data hashes, source, 5 nm mesh/core coverage, 3D periodic x/y + PML z, stack, monitor and reference contracts. Selection-only `selectall/getid` supports object inventory; no geometry mutation or save occurs. The resource name `GPU license audit` was read back from the actual FDTD resource manager. Actual installed product/file versions and GPU inventory are in `g027_exact_systemcheck.json`.

Official `runsystemcheck("FDTD","GPU")` returned:

| Estimate | Bytes |
|---|---:|
| Minimum | 546176024 |
| Maximum | 641836160 |

Component estimates are retained verbatim. No fatal compatibility error occurred; the returned structure has memory fields and no separate warning field, so this report does not invent a warning-free engine run. The exact source/copy FSP hashes remain unchanged. There was no meshing/run/engine dispatch.

References: [official GPU check](https://optics.ansys.com/hc/en-us/articles/4403937981715-runsystemcheck-Script-command), [GPU result folder rule](https://optics.ansys.com/hc/en-us/articles/49708268223251-Accessing-GPU-results), [resource introspection](https://optics.ansys.com/hc/en-us/articles/360034931353-getresource-Script-command).

## F. License scope

The existing formal `license_preflight_v1.py` was reused without modification, with a guarded factory. Two real API sessions checked out and released `FDTD_Solutions_engine`, using the established ACL range 6200:6299; the precheck returned PASS.

- `API_LICENSE_AVAILABLE=true`
- `GPU_ENGINE_LICENSE_CONFIRMED=false`
- `GPU_ENGINE_LICENSE_NOT_TESTED=true`

This demonstrates API/session and explicit feature checkout, not GPU-engine/HPC launch entitlement or successful GPU dispatch. No scientific launch is used to close that gap. Source SHA, checkout/close traces and the original formal receipt path/SHA are in `license_scope.json`.

## G. Deployment staging and switching transaction

P0 failed, so production deployment is not enacted. `CUTOVER_TRANSACTION_DRAFT_V1.md` is a reviewable closed-gate sequence, not launch authority. A read-only cutover evaluator refuses qualification when UNKNOWN/active owners, markers, pending requests or native checks remain unresolved. Production ingress, trusted V2 receipts and monotonic imported budget are not yet enabled or certified; the original offline worker and NativeBackend refusal remain intact.

Ordinary `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` from SSH failed to survive the SSH launcher exit; the child exited before its started receipt and log were produced. The precise OS cause is not proven and is not hidden. A separate WMI `Win32_Process.Create` broker (hidden, no service/Scheduler installation) launched an **offline fixture only**, with independent stdio and a persistent log. After SSH/launcher exit it completed `DONE_OFFLINE` with one fixture entry and zero scientific calls. No actual logout/reboot was tested, and this fixture result alone does not certify the future scientific dispatcher.

## H–I. Regression, diff and final qualification

Regression covers real native load/read failure, source-hash binding, forbidden native operations, API open/close failure evidence, actual formal-precheck failure injection, existing PID reuse/stale-owner/fencing/real duplicate-process tests, pair integrity and qualification refusal. Test count and final lint/Git evidence are in `acceptance_summary.json` and JUnit. No V1/Coupling file belongs to this commit. Large native copies/derived fields stay outside Git in the isolated runtime.

Final decision is **BLOCKED** because current V1 owner isolation cannot be proven. Even after that gate clears, trusted production ingress and budget migration must be qualified before controlled deployment. The next formal deployment proposal is the closed-gate transaction draft; do not disable tasks or launch G027 until its prerequisites and explicit deployment/scientific authorizations are met. READY_FOR_CONTROLLED_CUTOVER would still not authorize science or imply G027 success.

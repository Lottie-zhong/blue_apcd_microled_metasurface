# GPU_PLATFORM_AGENT_CONTEXT_V1

Updated 2026-10-09. Read before continuing work; these are project handoff notes, not global memory.

## Authority and scope

Latest task `APCD_GPU_PLATFORM_CONFLICT_AUDIT_AND_V2_CLEANROOM_MVP_V1` stops new V1 patches and keeps its queue closed. It authorizes independent worktree development and offline fixture tests. It does not authorize any native GPU scientific launch, old-entry replay, Scheduler changes, WinSW deployment, protected confirmation response access or frozen physics edits. Older scientific authorization is not inherited by V2.

## Verified paths and owners

- Host `DESKTOP-NNE313K`. Connection address and local authentication parameters remain only in the private untracked local execution context; do not commit them. Use the verified current LAN connection rather than generic stale guidance.
- Python `N:\anaconda_envs\RCP_LCP\python.exe`, 3.10.20. Lumerical `N:\Program Files\ANSYS Inc\v251\Lumerical`, 2025 R1. C: installation path is absent. Native resource name `GPU license audit`.
- V1 Runner code: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`, branch `codex/apcd-gpu-production-runner-v1`, HEAD `a8a09213d14883349921e5432daacd72f2ee7bb4`, clean 0/0 at audit. Runtime `D:\apcd_runtime\gpu_production_runner_v1`. No V1 edit by this task.
- Coupling code/labels: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`, branch `work/mdc-np-coupling-ml-v1`, HEAD `a0747605c3e5fefe4e111aa5d16e3a148328ed37`. Existing 537 status entries and ahead 1 preserved. No Coupling edit/commit by this task.
- V2 code: `D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1\platform_v2`, branch `codex/apcd-gpu-platform-v2-cleanroom-v1`. V2 runtime `D:\apcd_runtime\gpu_platform_v2_offline_20261009_v1`.
- V1 request/entry ownership remains Runner; queue counters, scientific labels and ingester remain Coupling. V2 owns its offline SQLite ledger only. It cannot refund V1 budget or certify Coupling labels scientifically.

## Frozen scientific contract

Contract SHA `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5` stays frozen. The existing owner contract is GaN-top MDC `P1_ZL1_ALTERNATIVE_G3_A3`, spacer 237 nm, six ordered TiO2 diameters on 100–230 nm / 5 nm grid, height 500 nm, pitch 290 nm, x period 1740 nm, mesh 5 nm, wavelengths 440–460 nm / 21 points, +z P_XLIKE incidence, BFAST false, periodic x/y and z PML. Reference normalization remains 1722 nm. No geometry, material, reference-plane, spectral or polarization change was made.

Coupling label shape remains complex `C_hat[21,7,2]` with positive `P_scale[21]`, packed to 609 real outputs. Packaging roundtrip is verified; full V2 native scientific/importer acceptance is not.

## Checkpoint and cause

- Queue state `STOPPED_RECONCILED`; no current case or unresolved Runner request. Production entered 38, truth 34, labels 34, remaining 90, replay 0, confirmation-response access 0.
- G026 has consumed entry and is closed without truth. Never replay. G027's two observed requests failed PREENTRY with entry/invocations 0; no new request was launched here.
- Installed controller request `faa47cbef071544180bb7803127a4c52`, manifest SHA `faa47cbef071544180bb7803127a4c5276e39270937e061025dffc607618832c`; controller source SHA `5f6aeeed4b32525f4f706d110f066292e305d1b1ad0887be9e19a9f5db38a86d`.
- V1's current self lock invalidates historical closeout validation and makes `runner_owner_probe` positive. Installed code and historical receipts reproduce this entirely in memory, without writing production locks or running a solver. Exact historical exception matched object is unavailable.
- No current engine/markers; 8 old API servers persist. Two parent stdin Python sessions and another older standalone stdin Python remain unidentified. Do not terminate them by name or infer that they are unrelated. TaskScheduler Operational logging is disabled.

## Evidence and next gates

V1 forensic snapshots: `D:\apcd_runtime\gpu_production_runner_v1\diagnostics\GPU_RUNNER_AGENT_TAKEOVER_20261009_V1`. V2 committed documents/reports are under `platform_v2`; final Git receipt is outside Git under `D:\apcd_runtime\gpu_platform_v2_offline_20261009_v1\delivery_git.json` after commit.

Before a production cutover: resolve remaining process identity; prove no V1 owner/engine/queued dispatch; independently review native exact-case runsystemcheck/license/load qualification; implement validated production ingress/receipt compatibility; reconcile imported budget with Coupling; obtain explicit scientific first-entry authorization. Do not create an additional monitor or poll a science task from this offline harness.

## Current task authority and native acceptance (2026-10-09)

`APCD_GPU_V2_NATIVE_ACCEPTANCE_AND_CUTOVER_GATE_V1` supersedes the earlier offline-only acceptance scope: actual isolated native LOAD, official exact-case GPU systemcheck and formal license precheck are authorized, scientific solver/Scheduler changes remain unauthorized. Baseline a6fef4aa3925dd5989d8b1e7db2f3197f45da016 verified clean 0/0.

G025 actual native LOAD and real Coupling importer PASS, C_hat/P_scale/eta max difference=0, 609 outputs; original pair SHA unchanged. G027 exact systemcheck/setup PASS, 546176024–641836160 bytes. API feature precheck PASS; GPU engine/HPC license remains NOT_TESTED. Real exception close left no acceptance-owned API child. Ordinary detached Popen failed across SSH exit; hidden WMI broker offline fixture completed after SSH exit with persistent logs, no service/task installed.

P0 remains BLOCKED: 16 live UNKNOWN identities; 0 confirmed V1 active is not no-owner proof. Current V1 tasks remain Enabled/Ready, no pending requests or markers; manual/CLI revival remains possible. Keep queue closed, do not terminate unknown processes or delete locks. NativeBackend.run still refuses, production ingress/budget migration remain unqualified. Read NATIVE_ACCEPTANCE_DECISION_V1.md and CUTOVER_TRANSACTION_DRAFT_V1.md; the transaction is not executed or launch-authorizing. New qualification reports live in reports/native_acceptance_v1 and isolated runtime D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1. Final delivery Git receipt is outside Git in that runtime. Next priority: resolve UNKNOWN owner identities, then separately review closed-gate cutover authority.

## UNKNOWN process closure follow-up (2026-10-10)

Starting HEAD 05fa4f6d51535386635fee0a6b0cedcf496faa49 verified. Two consistent read-only snapshots: 1 confirmed historical LOAD-only inventory API (31848), 15 UNRESOLVED, 0 confirmed V1 science owner, but absence not proven. Global admission new_entry_hold=0/generation27; V1 tasks Enabled/Ready, old manual dispatch not fenced. Qualification BLOCKED_WITH_IDENTIFIED_OWNER_RISK. G027 attempt_001 unentered; counters 38/34/34/90 and G025 native hashes unchanged. No native/API/science launch, Scheduler/gate mutation or process termination. 89 tests/lint PASS. Read UNKNOWN_PROCESS_CLOSURE_DECISION_V1.md and CUTOVER_READINESS_TRANSACTION_V1.md; no production or science authorization.

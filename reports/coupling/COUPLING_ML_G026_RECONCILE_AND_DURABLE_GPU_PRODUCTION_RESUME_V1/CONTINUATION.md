# Continuation — COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1

Read this file first after context loss, then verify the live Runner handoff, Coupling ledger, current controller binding, and task-specific final report before any queue action.

## Verified workspace

- Remote host/user verified at 2026-10-09T06:26Z UTC: `DESKTOP-NNE313K` / `desktop-nne313k\dell`.
- Coupling worktree `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`, branch `work/mdc-np-coupling-ml-v1`, HEAD `877d62bddecbe38156ab544bc734be74353de9a5`, upstream 0/0. Preserve all unrelated dirty/untracked paths; do not stage broadly.
- Runner worktree `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`, branch `codex/apcd-gpu-production-runner-v1`, HEAD `79b1f4081a3d9a0e9f287c14e88f0e5399c0d4a3`, clean/upstream 0/0.
- Runner formal handoff: `docs\APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.md`, SHA-256 `ab049dc6aa7ea0e98fdd348f5db59ae1836109cfb3ef61d788da5773989bfce0`.
- Runner delivery: `reports\gpu_serial_batch_production_stabilization_v1\FINAL_REPORT.md`, SHA `b20b04f628f4e676af526d131b2ec544affa1b20825850909c5fd8aa4f952358`; continuation SHA `3cf09a0640ff4ee8ebfa6587675cc5f2b113fe509eb1cf241c3bfb41530c7424`; inventory SHA `f271865d60fae5da3c36308e5a1cfbada5f6ae2081791a3df98694cc10b72983`.

## G026 reconciliation

- `K6GDP2_DEV_G026`, `attempt_001`, run `K6V2_G026_20261009T025353Z_06303b44`; Runner request `42d15429cb67170e7a515dfe0078edeb`; controller request `bb93248ca2dff9605d7885554a319394`.
- Official Runner generic closeout: entry=1, invocation=1, replay=0, truth absent, failure `LUMERICAL_LICENSE_STARTUP_FAILED`, physical engine entry `UNKNOWN`, quarantined. Do not replay or convert UNKNOWN to zero.
- Runner receipt file SHA `7eadb65dd436e1f3c431d2e22428b744f48ac6f577df92d0a820db6c94a65f72`; internal receipt SHA `92686de76bb315df53ade6471bef5bdfd6f2a90898c7f9718f1dafbc0f729196`; verification SHA `02bfa2e031879ccabec8b5ef572ad1ae52cd373e76162fe9496056b27ca4a378`.
- Coupling reconciliation receipt path `COUPLING_POSTENTRY_RECONCILIATION_K6GDP2_DEV_G026_bb93248ca2dff9605d7885554a319394.json`, file SHA `a2ef7b77c5283e348f735b1270b64e2ae5c6f5ab020440b29fd33db5b1ec785d`; internal receipt SHA `ee761811b4d5717eb5e1e5289e1bf7be94c6708642c2956b3084a86f9e3af059`.
- Ledger after reconciliation SHA `ff9f9e92904eccf76744e60c32fa143dc2a36cf900788c3c3d6be635ed5177a2`. Verified counters: 38 entered / 34 truth-valid / 34 labels-valid / 90 unentered; training=0, P_scale fits=0, confirmation response access=0, automatic replay=0. G027 has not entered.
- Old controller status is `STOPPED_RECONCILED`, SHA `2858f77335e184e595221213f019cf6fe8c7a75d4e630f31d95cc2cd7843cc14`.

## Consumer fix and validation

The Coupling closeout consumer had case-specific legacy handling and rejected the Runner's generic `APCD_GPU_RUNNER_V1_POSTENTRY_FAILURE_CLOSEOUT_RECEIPT_V1` as `UNAUTHORIZED_FAILED_POSTENTRY_CASE`. `serial_queue.py` now has a schema-verified, fail-closed generic post-entry closeout path. It binds case/attempt/run, receipt/verification/status/registry/envelope, request lineage, ledger/current-case/controller pointers and budgets; requires exactly one consumed entry, zero replay, quarantine and no truth; terminalizes and reconciles the controller without dispatching work. G024-specific restrictions remain scoped to its legacy path.

The fix also handles exact Git LF/CRLF serialization when verifying the pinned source, excludes only the current uniquely matched reconciliation CLI process from the no-owner census, checks canonical queue-manifest identity separately from raw file SHA, and writes generation-specific resume receipts without overwriting earlier generations.

Remote RCP_LCP validation: focused generic closeout tests `9 passed`; `serial_queue.py --dry-run` returned `DRY_RUN_NO_SOLVER`, next G027 attempt_001 sequence 39, 90 remaining, solver entries this call=0, training=0, P_scale fits=0, confirmation access=0. `git diff --check` passed (only existing LF/CRLF conversion warnings). A separate official Runner read-only retirement preflight passed: G025 and G026 prior runner requests terminal; global slot free; no active controller/worker/solver; successor is G027-G116 only.

## Successor/recovery state at this checkpoint

- Old request: `bb93248ca2dff9605d7885554a319394`; old task binding SHA `2f4b6dcd2c82083569bbb38e4577dc43e2d16f6df6b07efb1079987df22a197b`.
- Successor manifest `SUCCESSOR_CONTROLLER_MANIFEST_V1.json`, request ID `bbb7f19186776ceff07f93a17fded92b`, raw SHA `bbb7f19186776ceff07f93a17fded92b036224eeaff9f95f0d1269347c58a87f`; pinned `serial_queue.py` SHA `93d29da19fcc5b8d5df826646683a3090f785673177ece82697be01542980947`; exact cases G027-G116, max 90, one slot, one entry/case, replay=0, truth-before-next.
- Queue snapshot SHA `951323df115a052933afb9bd360b1500dbc8a8a3ca6c6491f6b7dabd6d6bce4d`; retirement receipt SHA `0158543576913be51462dbce1bb61a99bbd1533a38dcfe23220a0db11fa9ae52`; owner decision SHA `1d6670211141e861a6468e19f34c3d4d0d594f9b2d4ac732fe086af342cc4991`.
- Successor manifest's `starting_*` fields remain immutable original controller lineage (35/33/33 and original ledger SHA); rebind schema only permits run id, script SHA, status path, case IDs and max_cases to change. Fresh dry-run and queue snapshot bind the live ledger at 38/34/34 before dispatch; do not rewrite frozen manifest fields outside the Runner rebind contract.
- At checkpoint, rebind/start had NOT yet occurred. Task Scheduler XML still bound old request, IgnoreNew/InteractiveToken, old PT72H. Runner current API exposes rebind then start for a new successor; `resume_controller_task` requires a previously started request and is not appropriate for G026 failure or an unstarted successor. After formal rebind, call the single official `start_controller_task` once, then verify actual task XML is PT0S, IgnoreNew and successor request-bound. PT0S is not logout/reboot persistence; task uses DELL InteractiveToken.
- Eight `fdtd-solutions.exe -server -hide` processes and two unrelated `ansysedt.exe` processes were observed; ownership of the eight API servers remains unknown. None were touched. Runner's own slot/process checks passed.

## Next actions

1. Review and commit only this task's exact allowlist: `scripts/coupling_ml/k6_v2_pipeline/serial_queue.py`, `tests/coupling_ml/k6_v2_pipeline/test_generic_postentry_closeout_reconciliation_v1.py`, and files inside this task report directory. Preserve all unrelated workspace state.
2. Recheck code SHA against successor manifest and official Runner read-only preflight.
3. Invoke official `retire_rebind_controller_task` with pinned old/new/receipt SHA values. Then inspect live task XML and binding for successor, PT0S, IgnoreNew, InteractiveToken.
4. Invoke official `start_controller_task` once for new request; do not call old G026 resume or run-one manually. Let server queue dispatch G027 onward.
5. Reconnect through a new SSH session; verify G027 actual entry, then durable native H5/FSP/provenance, Coupling truth and label validation before claiming completion or next-case dispatch. Continue observing queue autonomously; never stop it merely at 3/10-case milestones.
6. If an entered case fails without truth, preserve evidence, keep entry consumed, reconcile through generic closeout, and continue only through official safe rebind/resume within current authorization. Do not replay.

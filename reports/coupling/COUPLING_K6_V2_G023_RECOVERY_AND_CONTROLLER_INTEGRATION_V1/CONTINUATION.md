# CONTINUATION — Coupling K6 V2 recovery

Last verified: 2026-10-07 UTC on `DESKTOP-NNE313K` as `desktop-nne313k\dell`.

## Resume from here

Read this file and `G023_RECOVERY_REPORT_V1.md` before continuing. Coupling worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`, branch `work/mdc-np-coupling-ml-v1`, HEAD `bb4e105308cdb45e2a2df300cd08af3e01fdb920`.

The official K6 V2 queue ledger is reconciled and stopped: SHA `10f71003aec4cdd50fcdd7b0e0bae636072c0277c736aff70dfe67803b858955`; G023 is terminal `FAILED_POSTENTRY_NO_TRUTH`, quarantined, and counts remain 35 entered / 33 truth-valid / 33 labels-valid / 93 unentered. The idempotent G023 receipt is `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/G023_POSTENTRY_LEDGER_RECONCILIATION_V1.json`, SHA `31cb24d18431028873e80b362bdfd4d37bbd1dc1e84b7cb9d1c106169f2b7bf2`. D6_P05 pre-entry history and its later fresh success are both preserved.

The next unentered manifest case is `K6GDP2_DEV_G024`. No queue process or solver was started in this task. Do not dispatch based on this checkpoint alone. A later run requires the formal Runner controller authority/handoff, a fresh owner/hold/route/fence/slot/preflight check, and explicit user authorization for production solver entries. Do not replay any entered case; automatic post-entry replay remains zero.

The queue implementation is [scripts/coupling_ml/k6_v2_pipeline/serial_queue.py](D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\k6_v2_pipeline\serial_queue.py), SHA `5ede3c2b2d85c225f73041a5d9332397bfa6fa03d91c39c8bba40089131d5ae5`. Recovery command `--reconcile-g023-postentry-only` is exact-authority-only and idempotent. A bounded controller requires a Runner hash-bound controller manifest; direct `--execute` is rejected. `--reconcile-controller-stop-only` emits a resume receipt only at a verified case boundary. The Runner worktree still has an uncommitted Scheduler API change; its focused 17 tests passed, but formal owner acceptance is not recorded.

The diagnostic training environment remains `N:\anaconda_envs\RCP_LCP\python.exe` (Python 3.10.20, torch 2.5.1+cu121, CUDA 12.1 visible, NumPy 2.2.5, SciPy 1.15.3, scikit-learn 1.7.1). The already completed two diagnostic fits remain the only current-task fits. No environment change is needed.

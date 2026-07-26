# MDC-ML trainer harness checkpoint v1

## Scope and environment

- Execution: remote-first over `lumerical-win`.
- Canonical repository: `D:\project\blue_apcd_microled_metasurface`.
- Active worktree: `D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1`.
- Branch: `work/mdc-ml-inverse-v1`; start commit `1c26db2614b232f3f44e94e91ed1d64984977ece`.
- Trainer: SHA-256 `58de0e6d0558df7d7bf69d3ec03c8acab115d117255ee4bb1a7224c22e33ed58`, 13,067 bytes, 115 lines.
- CLI: `--help`, `--preflight`, `--status`, and synthetic-only `--fixture-smoke --fixture-output-root --fixture-run-id`; formal modes remain authorization-blocked.

## Frozen contracts and real-data preflight

- Full config SHA: `76e51a802f598e458264c31db5b6024ade4a0e0a65f3ba2cc3c4587fcd74ade6`.
- Promotion contract SHA: `71b43c40035bb49a0a9647734b8aa4b42f7a089aa9c354de0b2a90f0c93def52`.
- Training execution contract SHA: `4cc187dc18f2e18bae32dc659d1ffad6f2baf0fa411c7214fa98db02645ce886`.
- Read-only counts: 2,640 classification rows, 837 regression-eligible rows, 128 Round 1 rows, and 100 Round 1 regression-eligible rows; feature count is 150 and Round 1 sealed-test entries are zero.
- Status is `NOT_STARTED`; formal training has not begun.

## Fixture observability and tests

The harness uses three persisted evidence channels instead of relying on live SSH output: `wrapper_result.json`, separate stdout/stderr logs, and `fixture_audit_v1.json`. Run `harness-checkpoint-v1-001` exited with code 0, wrapper status PASS, persisted `FIXTURE_SMOKE_PASS=true`, audit SHA `fedb86a51d7d955fc4cd029c8d7beeadd514d39daf1b11a56c4ddeab1e981f33`, and artifact manifest SHA `a3c8b6b8bc681cb4ac6acb462206b39152c57a0174ed22132b538b53ab23a21e`.

The fixture reported 32/32 classification and 24/24 regression-eligible exact-once coverage with zero held-out leakage, group overlap, sealed-test reads/predictions, formal output writes, formal training calls, proposal calls, TMM calls, FDTD calls, and Lumerical calls. This is **INTERFACE_LEVEL_SYNTHETIC_EVIDENCE**, not full three-seed MLP path evidence. The dedicated test file collected 14 nodes and passed all 14.

## Capability matrix

| Capability | Status | Evidence |
|---|---|---|
| Remote-first execution | PASS | worktree/common-dir audit |
| Safe SCP transfer | PASS | trainer SHA/size/lines |
| Contract preflight | PASS | frozen contract SHAs |
| Status command | PASS | `NOT_STARTED` |
| Persistent fixture evidence | PASS | wrapper/log/audit |
| Interface-level classification exact-once | PASS | 32/32 fixture |
| Interface-level regression exact-once | PASS | 24/24 fixture |
| Formal candidate factory | NOT_IMPLEMENTED | code audit |
| Full classification OOF | NOT_IMPLEMENTED | code audit |
| Three-seed MLP regression OOF | NOT_IMPLEMENTED | code audit |
| Final bounded recompetition | NOT_IMPLEMENTED | code audit |
| Final retraining | NOT_IMPLEMENTED | code audit |
| Calibration/conformal full path | NOT_IMPLEMENTED | code audit |
| Bootstrap/promotion/route | NOT_IMPLEMENTED | code audit |
| Complete checkpoint/resume/finalize | NOT_IMPLEMENTED | code audit |
| Formal training | NOT_STARTED | output/status audit |

## Immutable outputs and next architecture

The formal merge/retrain directory remains the ten-file pretraining tree: 18,082,726 bytes and fingerprint `31268194235fbd21cb229f4037afb2410e59c835712ac627524739612903ae6f`. Combined, Shared, and Round 1 outputs were not written. TMM angular FWHM is not dipole-FDTD angular FWHM.

Future implementation should use the existing `src` namespace and proceed in bounded layers: (A) contracts/state/artifacts, (B) candidate factory, (C) cross-fit, (D) calibration/uncertainty, (E) final development training, and (F) evaluation/decisions/finalize. No new package is created in this checkpoint.

`TRAINER_HARNESS_CHECKPOINT_FROZEN=true`

`FULL_TRAINER_IMPLEMENTATION_FROZEN=false`

`FORMAL_TRAINING_STARTED=false`

Next task: `MDC_ML_TRAINER_BACKEND_CONTRACT_STATE_AND_CANDIDATE_FACTORY_V1`.

# POST_D8_FROZEN_FULL_JONES_MODEL_RECONSTRUCTION_AND_PRIMARY_REPLAY_V1

## STATUS
BLOCKED ? HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE

## PROVENANCE
- formal worktree: `D:\project\worktrees\blue_apcd_lp_stage11_4`
- branch: `work/lp-stage11-4`
- HEAD: `8e2fbb102bd6b9bd29656a3576694ffdaf0dbd88`
- upstream: `8e2fbb102bd6b9bd29656a3576694ffdaf0dbd88`
- `cb57069083fe7df440d6f161506b6bc498bb05b0` is reachable from both branch and upstream.
- external cwd `D:\project\blue plane wave meta-surface`: PATH_NOT_PRESENT.

## FROZEN_MODEL_GATE
- Original22 historical formal complete Jones recovered: 13
- Historical formal components missing: 9
- Frozen model specification complete: false; only Re/Im(txx) are historically frozen.
- txx max coefficient error: `0.008228297174274063`; frozen tolerance: `2e-15`.
- Result: `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`.

## REPLAY
Bounded6 full-Jones primary external replay was not run. No solver/lumapi/FDTD call, no new geometry, no D9 artifact, and no bounded6 fit leakage.

## READINESS
`POSTHOC_MODEL_DRIFT_REQUIRES_MORE_DIAGNOSTIC`; next diagnostic class: `PHASE_PROJECTOR_CROSS_BRANCH_DIAGNOSTIC`.

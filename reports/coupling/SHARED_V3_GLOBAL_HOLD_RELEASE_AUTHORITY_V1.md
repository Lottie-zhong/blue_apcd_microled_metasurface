# SHARED_V3_GLOBAL_HOLD_RELEASE_AUTHORITY_V1

**Status:** BLOCKED_BEFORE_RELEASE  
**Snapshot:** 2026-09-29T10:27:52.154076+00:00  
**Authority:** user-supplied conditional task; no unconditional release instruction.

## Decision

The GPU provenance gate is closed and the post-restore zero-solver regression passed (10/10, solver invocations 0). The six Coupling POSTENTRY_NO_TRUTH rows are terminal, have no active owners or leases, and are preserved.

The global hold was **not** released. Section 6's duplicate-entry audit found two durable SCIENTIFIC_SOLVER_ENTERED rows for one Traditional queue identity, K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001 (queue 21). The rows share one lease-token hash and fencing generation, so the evidence does not prove two distinct solver processes; however, it also cannot prove harmless duplicate logging. DUPLICATE_SCIENTIFIC_ENTRY_COUNT=0 is stale (2026-09-20T07:21:55.767045+00:00), predating these entries. This conflicts with the raw event ledger and prevents certifying no duplicate scientific attempt/current control-plane health from available authority.

No hold setter was called. No solver or controller was started. Traditional was not modified.

## GPU bundle provenance

- Dirty source classification: UNKNOWN; exact diff and original SHA256 preserved in reports/coupling/GPU_BUNDLE_DIRTY_DIFF_FORENSIC_V1.json.
- Original dirty SHA256: 4dc467624bd4e987701034a3ff3ded1492a45693cea7511a416d16e8593f5c91.
- Authorized Shared V3 commit/blob: c63b6631b0e5968c0d14e20f80447ffa5d8ff66e / e015de47fb93d0dfadbe1ef37c455e18e0340c92.
- Only scripts/shared_fdtd/engine/gpu_bundle.py was restored; current Git blob matches authority. Historical runtime import remains UNKNOWN.

## Six terminal incident records

| Case / attempt | Entry UTC | Return / saved truth | Current classification |
|---|---|---|---|
| GPU_CPU_PARITY_AND_RUNTIME_CANARY_V1 / attempt_001 | 2026-09-23T14:17:27.663165+00:00 | attempt ledger says return=true; no durable return control event; native/run FSP exists; fresh LOAD-only check missing MON_IN/Ex; H5 absent | POSTENTRY_NO_TRUTH; truth unresolved, no active owner/lease |
| K6V1_S12 / attempt_001 | 2026-09-24T12:10:20.153088+00:00 | false; no durable return event; setup/run FSP only; no accepted native result; H5 absent | POSTENTRY_NO_TRUTH; truth unresolved, no active owner/lease |
| K6V1_S13 / attempt_001 | 2026-09-24T12:55:02.583172+00:00 | false; no durable return event; setup/run FSP only; no accepted native result; H5 absent | POSTENTRY_NO_TRUTH; truth unresolved, no active owner/lease |
| W2H_06824 / attempt_001 | 2026-09-24T07:34:50.582414+00:00 | false in ledger although child exit code 0; no accepted return event; setup/run FSP only; no post/native truth; H5 absent | POSTENTRY_NO_TRUTH; truth unresolved, no active owner/lease |
| W2H_15294_INTEGRATED_REFINED / attempt_001 | 2026-09-20T13:20:20.516277+00:00 | false; no durable return event; run FSP hash equals pre-FSP; no accepted native result; H5 absent | POSTENTRY_NO_TRUTH; truth unresolved, no active owner/lease |
| W2H_15294_NP_DERIVED_BASELINE / attempt_001 | 2026-09-20T13:20:06.407008+00:00 | false; no durable return event despite ~29625.9s log completion; run FSP hash equals pre-FSP; no accepted native result; H5 absent | POSTENTRY_NO_TRUTH; truth unresolved, no active owner/lease |

All six remain HISTORICAL_TERMINAL_POSTENTRY_NO_TRUTH; none was replayed or rewritten. W2H_06824 attempt_004 is a distinct G2 task (RELEASED), not the PW_K6 attempt_001 incident. The current backend has regression coverage for each represented historical failure class; see the machine-readable coverage matrix.

## Release gates

- A GPU bundle provenance: PASS
- B zero-solver production regression: PASS (10/10; evidence SHA256 adc1178242affd83671acbd493bc629b9285ad8b16681a88e4c111e53d318af0)
- C six incidents terminal/no ownership conflict: PASS
- D no known current backend defect reproducing those six failure classes: PASS
- E stored control-plane health field: PASS, but current health evidence is NOT PROVEN because of the duplicate-entry ledger conflict above
- F S35/S39: PASS; both remain attempt_001 / WAIT_RESOURCE_CAPACITY, entry count 0
- G no active foreign scientific process/job: PASS; no engine/host/controller observed. The dormant legacy scheduled task points to the old seed-DB controller and was not run.

**Overall:** GLOBAL_HOLD_RELEASE = NOT_APPROVED; retain NEW_ENTRY_HOLD=TRUE (generation 23). This is a conservative block from the Section 6 audit, not a claim that two records prove two solver launches.

## Current state

- Capacity: global 3; Coupling-ML 2 enabled; Traditional 1 disabled; GPU 3.
- Slots all free; active resource reservations 0; active GPU leases 0.
- Reserve IDs S22/S40/S24/S43/S44/S46 have no queue rows.
- S35 and S39 are attempt_001, WAIT_RESOURCE_CAPACITY, with 0 scientific entries.
- No attempt_002, no solver invocation, no commit or push.
- Legacy hold provenance remains incomplete: original setter/reason/incident links were not recorded.

## Next

Read-only forensic reconciliation of the Traditional duplicate-entry event and stale health metric; if existing evidence cannot resolve it, obtain Chart review. Keep the global hold active until reconciled.

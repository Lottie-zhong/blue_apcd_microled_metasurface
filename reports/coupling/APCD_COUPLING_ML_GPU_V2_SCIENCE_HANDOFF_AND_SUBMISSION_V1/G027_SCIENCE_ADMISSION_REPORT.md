# G027 science admission report

## Verdict

G027_SCIENCE_ADMISSION_BLOCKED.

The candidate itself is budget-eligible and matches the frozen development queue. The current release does not authorize science, so the complete V2 admission gate correctly refuses it. No solver or controller was started.

## Case and frozen contract

- Case / attempt: K6GDP2_DEV_G027 / attempt_001
- Role: DEVELOPMENT_GLOBAL
- Ordered diameters: D1..D6 = [105, 105, 220, 105, 180, 135] nm
- Geometry hash: 3bf528151bf863d39766c05bb753628c38d782865db7f5732b6eb4b8002b390b
- Contract SHA256: 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5
- Source manifest SHA256: ee378c38a278e5edc52f8c639596b10a055ed4f2afacf8623e8962d0521d9a7c
- Case specification SHA256: 9fd316d23633b1e46c6daae3b22d8cc1ae869ded3b3c7493f8635173741e38c4
- Pre-FSP SHA256: b5c6b41d28e55984d9cebd1f15814f698b408350b2cbeac02336b200bc72271e
- Frozen request digest: fbacb483b6fc0d33b6a868baa80b8df2c9a5f128741b5c77b59771d541e0f163
- Release admission digest: d7761eb54cb4eb74721d12e9d40ea1a04b96718c4302381a2aca5dbe3cfce132

The case uses the frozen K6 3D periodic plane-wave setup, fixed MDC and 237 nm spacer, frozen materials and monitor/reference-plane contract, wavelengths 440–460 nm inclusive at 1 nm, seven transmitted orders and TE/TM, full complex C_hat plus independent P_scale (609 scalar outputs). Frozen H2 and original conjunctive H1 gates are unchanged. The 2026-10-10 G027 exact-case systemcheck is PASS and confirms source FSP and source manifest hashes, but its record says run_called=false and save_called_by_validator=false. This is setup/systemcheck evidence, not a solver result, not proof of GPU-engine license availability, and not scientific admission.

## Budget and queue

Fresh CouplingBudget.validate(G027 attempt_001) passes. Ledger snapshot SHA256 is f6577d14941310dcd48f1393044da91fe98c93793d9d53224bb25e56a908a7cd. Counts: 128 authorized; 38 entered; 34 truth-valid; 34 labels-valid; 90 unentered; replay=0; confirmation-response access=0. The G027 record is FAILED_PREENTRY_NO_ENTRY, entry_consumed=false, truth_available=false. G026 remains FAILED_POSTENTRY_NO_TRUTH with its prior entry consumed. The 32 confirmation cases remain sealed.

## Blocking authority

SCIENCE_RELEASE_DENY.json SHA256 is 8301556cccc8c385e5ac7fae98e99ef4091f342f3a44051c0fdcfe771de16e89. It has science_authorized=false, owner_clear=false, expires_unix=0, and an empty requests array. The installed validator returned FORMAL_SCIENCE_RELEASE_MISSING_OR_UNBOUND. The installed scheduled Controller task is disabled. These are intentional hard gates and were not changed.

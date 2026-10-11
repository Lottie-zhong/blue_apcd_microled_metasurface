# Four failed attempts: read-only forensic

| Case | Ordered D nm | Frozen stratum | Outer fold | Physical engine entry |
|---|---|---|---|---|
| K6GDP2_DEV_G023 | [130, 215, 140, 125, 215, 165] | DEEP_INTERIOR | 3 | UNKNOWN |
| K6GDP2_DEV_G024 | [180, 125, 135, 170, 145, 215] | DEEP_INTERIOR | 4 | False |
| K6GDP2_DEV_G026 | [205, 205, 145, 205, 130, 120] | DEEP_INTERIOR | 2 | UNKNOWN |
| K6LDA1_DEV_D6_M05 | [220, 195, 210, 150, 140, 205] | LOCAL_AXIS | 3 | UNKNOWN |

All four retain attempt_001, entry consumed1, replay0, FAILED_POSTENTRY_NO_TRUTH. UNKNOWN stays UNKNOWN; G024 engine was not observed, which does not release its consumed logical budget. Formal disposition/receipt/status/journal file SHA bindings and nativeFSP/H5 inventory are in FOUR_FAILED_CASE_FORENSIC.json. D6_M05/G023 native H5 are coordinates-only; G024/G026 have no complete E/H. Setup FSP existence is not solved truth. No zero-solver recovery candidate found. No LOAD, terminal migration, attempt_002 or ledger write occurred.

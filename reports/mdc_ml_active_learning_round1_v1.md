# MDC ML bounded active-learning round 1 v1

Generated from machine-readable Round 1 outputs.

- Selected / labeled: 128 / 128
- Families: 8
- Random controls: 16
- Explicit anchors: 17
- Solver failures: 0; power-balance failures: 0
- Proposal signature: 6db663dd30ba273b81407d09b8f4e132a4ff680d85092135e59e85c2b7791472
- Dataset signature: 8ec00cfd97b51bbe0109d477533edbd590be89cb4f7913aafb16f65b72254937
- Output tree SHA-256: 0d164ce4de3184d7e7e7df263083fba46f5c852d05967450ab7a3fe92f9e5c1c

This adaptive round is not a sealed-test evaluation and does not retrain or alter frozen champion artifacts.

## Provenance validation contract

The historical failure treated validation-time `HEAD` as if it had to equal the shared-surrogate freeze commit. `shared_freeze_commit` remains the generation base; `round1_freeze_commit` records the Round 1 freeze; `validation_head` is the current commit. The canonical validator now requires the three Git ancestor-or-self relations and audits immutable outputs, labels, and sealed-test artifacts. Machine-verified execution results: `py_compile` passed; the Round 1 provenance test passed (5 tests); the repository MDC-ML lightweight regression passed (171 tests, with `test_33_frozen_tracked_files_have_no_diff` excluded because this intentional source fix is unstaged, and `test_39_same_seed_mlp_prediction_is_reproducible` excluded because it trains a temporary model); and validation-only passed. No Round 1 output, label, or shared-surrogate artifact was modified.

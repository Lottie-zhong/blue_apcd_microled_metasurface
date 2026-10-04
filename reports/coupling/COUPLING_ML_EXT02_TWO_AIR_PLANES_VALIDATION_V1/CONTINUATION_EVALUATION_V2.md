# Continuation V2: EXT02 two-air-plane post-entry evaluation

Read the original CONTINUATION.md and frozen DIAGNOSTIC_PROTOCOL_V1.json first. Preserve the original BLOCKED_PREENTRY report and all V1 artifacts unchanged.

## Recovery identity
- Host/user: DESKTOP-NNE313K / desktop-nne313k\dell.
- Coupling worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1
- Branch: work/mdc-np-coupling-ml-v1
- Input HEAD: 8019c12c9627dad414bbbfff3579a0bffcda6aa4
- Runner branch/head at handoff: codex/apcd-gpu-production-runner-v1 / 9485d92e220abe277f08e65ac25f0b329ef624d9
- Runner handoff SHA256: 2f41bfd493f4105b013ee4269033f789b0d86d007169a57557bee3262f325d75
- Frozen protocol SHA256: fa2839ac5613df63d54508d79df9da98d5bc0243876ab9c1a5538ae75b9f92b8
- Official extractor SHA256: b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15

## Outcome and execution
- Runner truth run: one authorized solver entry; post-entry automatic replays=0; Runner status DONE / SCIENTIFIC_VALID.
- Post-processing: zero additional solver entries, zero training fits, zero P_scale fits, and zero confirmation-response reads.
- Cross-height outcome: CONSISTENCY_THRESHOLDS_MET; all five frozen engineering thresholds passed for this one case.
- No global phase alignment, fitted power scaling, or truth modification was used.

## Numerical boundaries
- Actual z: near 1801.999999999993 nm; far 2006.604166666668 nm; reference 1722 nm.
- NP range from pinned monitor audit: 1212-1712 nm. Actual FDTD mesh transition and PML inner face remain uncaptured.
- Periodic endpoint mismatch and high-order evanescent fit caveats are reported; they have no additional frozen threshold.
- Historical EXT02 comparison is descriptive only because setup FSP hashes differ and the historical mesh-contract hash is absent.
- Do not replace historical truth or add this diagnostic case to training.

## Durable artifacts
- evaluate_ext02_two_plane_handoff_v2.py
- EXT02_TWO_AIR_PLANES_EVALUATION_V2.json
- EXT02_TWO_AIR_PLANES_EVALUATION_REPORT_V2.md
- INPUT_SHA256_INVENTORY_V2.json
- CONTINUATION_EVALUATION_V2.md

# K6 V2 128-case development solver budget and first-case report

Date: 2026-10-05
Status: FIRST_CASE_DONE_PENDING_COUPLING_INGESTION_PASS

## Scope and authority

The versioned budget applies only to the 128 frozen development identities, each attempt_001, maximum one entry each, total 128, automatic replay 0. It does not authorize the 32 sealed confirmations, response reads, model fits, or manufacturing claims.

Route authority SHA-256: a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35; policy SHA-256: b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45; budget SHA-256: e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c; adapter SHA-256: a9cfb11db584bf2ab96049b9066e198415bfba0863f29d0ed278230ffddc8579.

## Pilot result

K6LDA1_DEV_D1_M05 / attempt_001 (DEVELOPMENT_LOCAL_AXIS, D [215,195,210,150,140,210]) ran once through the official single-slot Runner. Entry count 1; FDTD run 1; replay 0. The actual engine log contains fdtd-engine-msmpi.exe -gpu and identifies NVIDIA GeForce RTX 3080. Runner completed DONE; fresh LOAD, monitor/state validation, and SCIENTIFIC_VALID passed. Maximum energy closure was 1.1102230246251565e-16. Raw orders include 21 wavelengths (440-460 nm) x seven orders. Durable FSP, sibling solver H5, truth H5, raw complex fields, state, orders, projection, status and validation are hashed in the pilot inventory.

Formal truth handoff record: D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\COUPLING_K6_V2_128_DEVELOPMENT_CASES_GENERATION_V1\FIRST_CASE_TRUTH_RECORD_V1.json (SHA-256 db7b56ebcedcee2f2244c72fb06400244b57942c8e29f01e69ac0f86a50b91fc). Coupling ingestion/evaluator has not returned PASS yet. No second development case may enter before that response.

## Current counts and next action

- Authorized development budget: 128 maximum; consumed: 1; unconsumed: 127.
- FDTD runs: 1; automatic replays: 0.
- Confirmation responses accessed: 0; confirmation solver entries: 0; training/P_scale-only fits: 0.
- Next: wait for the first-case verified-ingestion result from Coupling ML. If PASS, continue exact frozen order one case at a time using the official Runner and fresh per-case launch revalidation. If rejected, stop new solver entries and repair only within the frozen contract.

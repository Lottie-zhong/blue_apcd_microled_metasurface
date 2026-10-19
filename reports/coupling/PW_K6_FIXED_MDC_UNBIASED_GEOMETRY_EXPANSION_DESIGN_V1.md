# PW_K6_FIXED_MDC_UNBIASED_GEOMETRY_EXPANSION_DESIGN_V1

## STATUS

`DESIGN_ONLY_CHART_REVIEW_PENDING`

This artifact is a zero-solver, label-blind design. No FDTD solver, scientific entry, queue mutation, NP prior, active learning, fitting, or H1 evaluation was executed.

## NP PRIOR CLOSEOUT

- `NP_V1_SCIENTIFIC_EVIDENCE = VALID`
- `NP_V2_SCIENTIFIC_PRIOR = NOT_ACCEPTED`
- `NP_PRIOR_FOR_CURRENT_H1_MAINLINE = CLOSED`
- `NP_RANKING_PROVIDER_FUTURE_SCREENING_ROLE = RETAINED`

NP evidence was not used to rank or select these geometries.

## GEOMETRY DOMAIN AUTHORITY

Authority: `reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json`  
SHA256: `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f`  
Status: `PASS_RECOVERED_CLOSED_CANDIDATE_DOMAIN`

Frozen ordered grammar: `K=6`, parameters `D1..D6`, each on the 100--230 nm observed 5 nm grid, `position_sensitive=true`, `sorting_forbidden=true`, pitch 290 nm, height 500 nm. The exact normalized distance is:

`sqrt(sum(((x-y)/130.0)^2 for x,y in zip(a,b)))`

No independent fabrication-limit authority was identified; no manufacturing acceptance is inferred. The design is restricted to the frozen candidate pool and its domain constraints.

## EXCLUSION REGISTRY

Reused unchanged: `reports/coupling/PW_K6_GEOMETRY_EXCLUSION_REGISTRY_V1.json`  
SHA256: `78f48a4400d5ab469a2054a8ad849d5cae16cb4bee042e2b542529a78973bb80`  
Status: `FROZEN_PRE_SOLVER`  
Protected ordered geometries: `25`

The registry covers the frozen 20G identities, prior scientific identities, failed/retired identities, and duplicate protection. Ordered permutations remain distinct unless the authority says otherwise.

## CANDIDATE POOL

Pool: `reports/coupling/PW_K6_EXTENSION_ELIGIBLE_CANDIDATE_POOL_V1.json`  
SHA256: `387112fda12b2fbee0b2e6e4185014e0fad4bbb825b2d9e6cded865b4988073d`  
Pool source SHA256: `None`  
Candidate count: **48**  
Eligible after protected-overlap filtering: **32**  
Constraint failures: **0**

Selection is deterministic and label-blind: sequential maximin from the frozen existing 20G, with lexicographically smallest ordered tuple as the numerical tie-break. No output labels, uncertainty, NP prediction, surrogate, or AL signal entered the selection.

## 12G TRAINING EXPANSION

Exactly 12 `TRAINING_EXPANSION_STAGE1` identities are proposed. They take the frozen 20G to 32G. They are not queued and have not been simulated.

| # | Candidate | Ordered D1..D6 (nm) | Geometry SHA256 | Nearest existing 20G | Selection score |
|---:|---|---|---|---:|---:|
| 1 | K6V1_S35 | `[110, 145, 225, 105, 185, 215]` | `bd6fb9a41c003910eeda456315bafb1962dd4335d1ec64ec055322e2f4a19276` | 1.167863573 | 1.167863573 |
| 2 | K6V1_S39 | `[175, 100, 125, 120, 100, 230]` | `7c582e2c53da5394d6cdf446a1ee9e16a970264b1fc78312d3f304df52403729` | 1.029160628 | 1.029160628 |
| 3 | K6V1_S21 | `[120, 115, 230, 140, 110, 115]` | `b76cc20026b4a260e3de72e55be3f4bb1e2665cb11a98c8d6f6d362088ac4bca` | 0.956911947 | 0.956911947 |
| 4 | K6V1_S42 | `[195, 210, 165, 130, 230, 230]` | `21f4de41082451078a32548654f1cefbd658317aa1144e596dc7d942fd9b6cee` | 0.901182655 | 0.901182655 |
| 5 | K6V1_S36 | `[115, 210, 220, 100, 150, 100]` | `1d0aee7a987b83b4a87c09484e1c2108032d08230176e1ee01219101e967296a` | 0.871983388 | 0.862602365 |
| 6 | K6V1_S31 | `[220, 195, 210, 150, 140, 210]` | `844bdc1487875afcf2b87400be032845f58e4647d29a91e9b41ee55c3cf1f765` | 0.833826284 | 0.833826284 |
| 7 | K6V1_S45 | `[195, 120, 105, 210, 220, 215]` | `4651179bfda51ae9bbe48aa50cf6909acf29030ca192dd485a2e2b99daee5d7a` | 0.819510606 | 0.819510606 |
| 8 | K6V1_S32 | `[105, 190, 105, 115, 105, 225]` | `e1b63a72b5157e5260a8243216e86f9d6e3e39ebb49d662c17eafced8a7fd18a` | 0.815892440 | 0.815892440 |
| 9 | K6V1_S47 | `[165, 160, 105, 100, 230, 170]` | `d35bc9a3166051ba8a68f8c7afe63b6a8a88e8a668abfe75a7957a56da77fa89` | 0.807692308 | 0.807692308 |
| 10 | K6V1_S33 | `[170, 175, 155, 150, 190, 105]` | `4e075a6a18a4fb86d7cf0d12fe7dff4423dc5d33c3a76e70e2d2be49e1fabe84` | 0.804940367 | 0.804940367 |
| 11 | K6V1_S37 | `[215, 170, 110, 180, 105, 130]` | `e0bb66317b39068c22e4ef3d8b4a6d4eca1da3188032583f4f9225b9780a6bd3` | 0.795698495 | 0.795698495 |
| 12 | K6V1_S48 | `[110, 100, 225, 205, 195, 175]` | `8c57542c2a7f609bf03d3b379662e4eaf7b39bbcc881e174f5d2480b9828f894` | 0.789164790 | 0.789164790 |

## 6G PROSPECTIVE RESERVE

These six identities are `PROSPECTIVE_RESERVE_ONLY`. They are not replacements for Stage 1, are not fitted or tuned against future behavior, and may only enter a later formal prospective validation after the retrospective H1 gate is resolved.

| # | Candidate | Ordered D1..D6 (nm) | Geometry SHA256 | Nearest existing 20G | Selection score |
|---:|---|---|---|---:|---:|
| 1 | K6V1_S22 | `[230, 130, 105, 120, 180, 220]` | `6dcb4c15db3adc8c09c143132e4c3aae14b2918540b00a2f6284091e591d158c` | 0.916644253 | 0.789164790 |
| 2 | K6V1_S40 | `[230, 110, 205, 230, 150, 225]` | `782239abf6931883ae452beaeff945f106dc97158a52606fd5ffd7281921995b` | 0.781630824 | 0.781630824 |
| 3 | K6V1_S24 | `[180, 230, 225, 130, 225, 155]` | `ae06e5e4c4c73d67e2cad92db6844b0fe3a5bca1070e7a70bf1f63d2e22af90d` | 0.794768397 | 0.764407958 |
| 4 | K6V1_S43 | `[190, 105, 215, 140, 165, 165]` | `9baad77600b1a1c37be48a13536a2a5cb767b5dd170e89ba41d75331870540fc` | 0.762470292 | 0.762470292 |
| 5 | K6V1_S44 | `[150, 180, 230, 200, 150, 165]` | `240f40a30fdd1c6233947db0c61a11529539ac27b4f456f5668891bd8ff892c8` | 0.751723857 | 0.751723857 |
| 6 | K6V1_S46 | `[150, 160, 170, 175, 105, 230]` | `2f4c318614c5e9b5de149f21946d4fa4719e20472c49f91495831c62c4ffc562` | 0.752707146 | 0.741819289 |

## COVERAGE GAIN

Coverage is computed over all 48 frozen candidate-pool points using the exact authority distance.

- Existing 20G candidate-pool covering radius: **1.167863573**
- Proposed 32G candidate-pool covering radius: **0.935809620**
- Absolute reduction: **0.232053953**
- Relative reduction: **19.869953856%**
- Candidate nearest-distance median: **0.785397807 → 0.000000000**
- Training-to-existing-20G distance range: **0.789164790–1.167863573**
- Reserve-to-existing-20G distance range: **0.751723857–0.916644253**
- Reserve-to-training-12G distance range: **0.741819289–0.912600809**

Marginal ranges and means, pairwise-distance summaries, nearest-neighbor distributions, covering-radius values, and duplicate/permutation audits are machine-readable in the manifest.

Duplicate audit: existing20 `0`, proposed32 `0`, candidate pool `0`; ordered-permutation collision groups `0`.

## PROPOSED HF BUDGET

- New integrated K6 geometries: **12**
- Proposed scientific entries: **12**
- Wavelengths per geometry: **21**, 440--460 nm inclusive
- Proposed wavelength rows: **252**
- Fixed MDC: `P1_ZL1_ALTERNATIVE_G3_A3`; spacer 237 nm; p=290 nm; Λx=1740 nm; Λy=290 nm; H=500 nm
- Shared V3 lifecycle and truth contract: unchanged
- Physics, monitor, wavelength, solver, admission, and queue contracts: unchanged
- Actual solver entries and queue mutations in this task: **0**

## POST-32G ANALYSIS CONTRACT

The future evaluation is preregistered against the same `PW_K6_STRUCTURED_FORWARD_MODEL_V1`, grouped geometry-held-out validation, frozen state branch, frozen `P_scale`, deterministic H2, and complete frozen H1 metrics/gates. No architecture, threshold, gate, or comparator change is permitted before seeing the 32G evaluation.

Interpretation is conditional: material improvement supports `DATA_COVERAGE_SUPPORTED_AS_MAJOR_BOTTLENECK`; little/no improvement supports `DATA_EXPANSION_INSUFFICIENT`. Neither result authorizes an automatic 40G/50G expansion.

## ARTIFACT HASHES

Source authority hashes are recorded in the manifest. The two new artifact hashes are computed after writing and reported by the verification command; the manifest is not self-hashed to avoid a self-referential digest.

## GIT

This design does not commit or push. The canonical branch and current HEAD are recorded by the final read-only verification. Existing dirty state is preserved; only the two requested report artifacts are added by this task.

## NEXT

`CHART_REVIEW_STAGE1_12G_HF_BUDGET`

Do not execute the next route automatically.

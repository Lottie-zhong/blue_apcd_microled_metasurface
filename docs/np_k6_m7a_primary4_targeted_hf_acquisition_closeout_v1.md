# NP K6 M7A Primary4 targeted HF acquisition closeout v1

Status: `NP_K6_M7A_PRIMARY4_TARGETED_HF_ACQUISITION_COMPLETE_20G_M8_RETRAIN_READY`

## Scope and frozen identity

- Preregistration: `NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1`; SHA256 `bd221dfe8d15475cb5c0f9d5959a6595fed2238ff58f7ca1befbdc421bf65951`.
- Eight authorized logical cases (4 geometries × P/S), exact 445–455 nm at 1 nm spacing, u_x=0 and k_y=0, Native-M1, fixed 5 nm core mesh, 3 ps generator V2.
- No external/sealed target was read; no M8, retraining, inverse design, angular extension, or additional HF acquisition was started.

## Case quality and provenance

All `8/8` cases passed: exact 11 finite wavelengths, closure gate, structure-interval gate, order/normalization bookkeeping, Native-M1/material and 4 MPI × 1 thread resource readback.

| Case | Role | Post-FSP SHA256 | max |1-T-R| | max structure anomaly |
|---|---|---|---:|---:|
| NP_K6_M7A_PRIMARY4_G01_P | RESIDUAL-TAIL | `c08b1545bce2e7ae3d86ba81d8579cc1a02b07ada2e7a02b53fa27d62bb05eff` | 0.00124901361 | 0.000745864128 |
| NP_K6_M7A_PRIMARY4_G01_S | RESIDUAL-TAIL | `6eac26dc699d7d72dad4e6017be7f0a8521540c51aeb251e5e556acb65390fd3` | 0.000585458242 | 0.000410031359 |
| NP_K6_M7A_PRIMARY4_G02_P | RANKING-CHAMPION-STRESS | `7f0eb53c2c70814c3168f61ea08b38658f151691f79c4319d56403e5ebac14b3` | 0.0017189237 | 0.00175834832 |
| NP_K6_M7A_PRIMARY4_G02_S | RANKING-CHAMPION-STRESS | `947f13af8ac99960cde099078fe9ca0ac2e589d6e85ac17bdc5f9b5048f12ee7` | 0.000386836047 | 0.00013948682 |
| NP_K6_M7A_PRIMARY4_G03_P | POLARIZATION-STRESS | `5c05cc9792b57f0930b9f7dd18003cf8e091df9989556d5f928f344bdf31745c` | 0.000731594965 | 0.000501150991 |
| NP_K6_M7A_PRIMARY4_G03_S | POLARIZATION-STRESS | `ecb58530de121454a89d270cffcdbefac78d1958af0a4712021c407529927bc0` | 0.000596786889 | 0.000382052894 |
| NP_K6_M7A_PRIMARY4_G04_P | COVERAGE-CONTROL | `07a63928af246f9fcc40008ccc77362a39f2255a5b1f38d42ac2f77be7723d0d` | 0.000578006372 | 0.000569408962 |
| NP_K6_M7A_PRIMARY4_G04_S | COVERAGE-CONTROL | `6e0354e8c266cda49ae7b2276bc8186cf32e2b577254f50ab20d7d72c307779d` | 0.00184915849 | 0.00194055704 |

Across all cases: max closure residual `0.00184915849` and max structure anomaly `0.00194055704`; both are below 0.01. Order and direct normalization mismatches are ≤ `3.33e-16`.

## Dataset closeout

- New M7A rows: `88`; prior formal development rows preserved: `352`; merged development view: `440` rows.
- Merged identity: `20` geometries × 2 polarizations × 11 wavelengths = `440` rows; `40` paired logical cases.
- Existing 352-row legacy `training_label` fields were preserved; the M7A rows carry `training_label=true`, `quality_gate_pass=true`, `diagnostic_only=false`, and candidate-performance provenance for this development acquisition.
- Duplicate/conflicting provenance: 0; new-vs-existing geometry overlap: 0; quarantined M6 G01 geometry absent.

## Role truth and ranking evidence

The four pre-registered roles were retained as audit labels; no post-hoc role reassignment was made.

- `K6X_D135_D155_D190_D220_D225_D230` (RESIDUAL-TAIL): observed_signal=`None`, evidence=`None`.
- `K6X_D110_D125_D135_D150_D175_D195` (RANKING-CHAMPION-STRESS): observed_signal=`None`, evidence=`None`.
- `K6X_D100_D105_D115_D165_D225_D230` (POLARIZATION-STRESS): observed_signal=`None`, evidence=`None`.
- `K6X_D100_D105_D110_D115_D190_D230` (COVERAGE-CONTROL): observed_signal=`None`, evidence=`None`.

Broadband truth champion: `K6X_D100_D115_D130_D145_D155_D185`. The G02 ranking-champion-stress geometry has true broadband rank `2`. LF full-order ranking Spearman ρ is `0.959398`, top-3 recall `0.666667`, and top-5 recall `1.000000`. These are audit results, not a claim of active-learning success.

## Polarization and LF residual audit

The paired P/S audit retains explicit polarization. Over the merged HF20 scope, |Δη(+1)| mean/max are `0.095511` / `0.501273`; the M7A4 subset is `0.117839` / `0.484915`.
- LF is the deterministic existing low-fidelity proxy from the D0 chunk library, not a new solver result; at current u_x=0 it is explicitly polarization-blind.

| LF output | mean HF−LF | mean absolute residual | max absolute residual |
|---|---:|---:|---:|
| T_proxy | -0.010687 | 0.122738 | 0.409952 |
| eta_m+0 | -0.038786 | 0.071592 | 0.214607 |
| eta_m+1 | -0.082392 | 0.104086 | 0.294763 |
| eta_m+2 | -0.041878 | 0.055842 | 0.110907 |
| eta_m+3 | -0.011640 | 0.028264 | 0.096230 |
| eta_m-1 | -0.003666 | 0.018263 | 0.118777 |
| eta_m-2 | -0.009833 | 0.019446 | 0.054718 |
| eta_m-3 | -0.021321 | 0.026172 | 0.043259 |

The residuals show systematic coupling correction, especially for total T and η(+1); they do not authorize treating LF as HF truth.

## Temporary concurrency-3 trial

Trial `APCD_PRODUCTION_CONCURRENCY3_TRIAL_V1` remained temporary: global cap `3`, NP authorized max `2`, LP max `1`, fourth FDTD forbidden, and RCWA excluded from FDTD counting.
Observed maximum active FDTD was `3` with `21` slot-3 history rows. Every M7A case used 4 processes × 1 thread and passed quality gates. Continuous CPU/RAM telemetry was not available, so no stronger resource-utilization claim is made.

## Validator and solver budget

Independent validator: `30` checks passed, 0 errors; report SHA256 `8408366527ebf68fe743b3654cceb664eb200557a13f8f4f9e80daaddc38113e`. Solver budget audit records exactly 8 entered/run invocations, 0 attempt_002, 0 replacements/replays, 0 external-HF calls, 0 sealed-target reads, and `m8_started=false` / `training_started=false`.

## Decision

The 440-row formal development dataset is complete and ready for the separately authorized M8 retraining decision. This closeout does not itself start M8 or promote a production surrogate. Next action: obtain explicit authorization before M8 retraining; keep external HF and all other solver branches frozen.

# NP K6 Coupling Forward Runtime Coverage V2

Status: `NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V2_READY`

## V1 interface audit

Classification: `B_EXECUTABLE_PROVIDER_BUT_DOMAIN_GUARD_BLOCKS_COUPLING_GEOMETRIES`. V1 is callable but resolves LF requests through exact geometry keys: an HF22 row lookup, then exact lookup in a 296,010-entry master generated only from strictly increasing `itertools.combinations(DS, 6)` and its precomputed chunks. The 20 Coupling geometries have `0/20` exact HF22 overlap and `0/220` exact V1 LF query coverage. This was a lookup-domain limitation, not evidence of invalid physical geometry.

## A1 runtime provider

`NP_LF_FEATURE_PROVIDER_V2(D1,...,D6, lambda, polarization)` is a callable deterministic implementation of the frozen D0 single-pillar `txx` + ordered six-bin DFT proxy. It does not fit a model, sort/permute the six physical +x positions, interpolate, or substitute a neighbor. Its finite runtime domain is all `27^6` ordered diameter vectors drawn from 100–230 nm in 5 nm steps, 445–455 nm integer samples, normal incidence, and `P_XLIKE` only.

Outputs use `A_m=sum_j txx_j*exp(-2πi*m*j/6)` with j in physical D1..D6 order, then `eta_m_proxy=|A_m|^2/sum_{m=-3..+3}|A_m|^2`; `T_proxy=sum(eta_-1, eta_0, eta_+1)` is not absolute HF transmission. `R` is unavailable; complex amplitudes, Jones, angular response, and coupled-device truth are not exposed. HF22 parity was checked on 242 geometry-wavelength points; maximum absolute delta was `1.78813934e-07` (gate `<=2e-6`).

The provider has no fitted geometry set. Its source calibration is the 27-diameter × 11-wavelength x-polarized single-pillar library. Separately, the full-K6 HF22 empirical support contains 22 exact ordered geometries; the 20 query geometries are `0/20` exact matches and `20/20` OOD relative to that empirical support. This is runtime coverage, not an in-domain accuracy claim.

The old D180 exclusion snapshot remains unchanged. A later one-run attempt was explicitly authorized: its persisted post-FSP SHA256 is `142c40bc78aa6605ad77b84a9be1a62508c35d46045885506828d014d19f419d`, its formal post-FSP read-only extraction is pass/warning-valid, and its 11-row results SHA256 matches the library manifest D180 source-result hash. The old provenance snapshot was not rewritten. Provenance warning: the run manifest's `pre_fsp` pointer duplicated the post hash, and the path referenced by the setup heartbeat now contains different bytes than its recorded pre-run SHA. The V2 audit preserves this unresolved pre-file linkage anomaly; it does not treat the current file as the setup artifact.

## Ordered 20-geometry audit

Physical grammar valid: 20/20. Runtime domain supported: 20/20. Exact HF22 matches: 0/20. Positionwise extrapolative: 20/20.

| Query | Ordered D1..D6 (nm) | Nearest HF22 geometry | Distance / 130 nm | Physical | Runtime | HF22 OOD |
|---|---|---|---:|---|---|---|
| K6V1_S02 | `215,105,215,230,105,130` | `K6X_D140_D160_D165_D170_D180_D190` | 1.191066 | YES | SUPPORTED | YES |
| K6V1_S03 | `230,100,130,120,230,100` | `K6X_D140_D160_D165_D170_D180_D190` | 1.240944 | YES | SUPPORTED | YES |
| K6V1_S04 | `205,215,105,225,180,100` | `K6X_D140_D160_D165_D170_D180_D190` | 1.140305 | YES | SUPPORTED | YES |
| K6V1_S05 | `215,225,100,125,110,220` | `K6X_D140_D160_D165_D170_D180_D190` | 1.138358 | YES | SUPPORTED | YES |
| K6V1_S15 | `110,135,180,230,230,100` | `K6X_D120_D125_D180_D185_D190_D195` | 0.871983 | YES | SUPPORTED | YES |
| K6V1_S16 | `175,230,230,230,100,220` | `K6X_D150_D205_D215_D220_D225_D230` | 1.011765 | YES | SUPPORTED | YES |
| K6V1_EXT01 | `220,210,230,225,205,105` | `K6X_D200_D205_D215_D220_D225_D230` | 0.994065 | YES | SUPPORTED | YES |
| K6V1_EXT02 | `220,120,155,100,105,110` | `K6X_D100_D105_D115_D120_D125_D130` | 1.015414 | YES | SUPPORTED | YES |
| K6V1_EXT03 | `120,110,225,225,100,205` | `K6X_D120_D125_D180_D185_D190_D195` | 0.844404 | YES | SUPPORTED | YES |
| K6V1_EXT04 | `105,230,100,100,230,220` | `K6X_D100_D140_D145_D155_D225_D230` | 0.887120 | YES | SUPPORTED | YES |
| K6V1_EXT05 | `210,220,100,230,195,225` | `K6X_D200_D205_D215_D220_D225_D230` | 0.928669 | YES | SUPPORTED | YES |
| K6V1_EXT06 | `165,110,115,230,155,115` | `K6X_D140_D160_D165_D170_D180_D190` | 0.956912 | YES | SUPPORTED | YES |
| K6V1_EXT07 | `115,230,125,105,100,130` | `K6X_D100_D105_D115_D120_D125_D130` | 0.997037 | YES | SUPPORTED | YES |
| K6V1_EXT08 | `230,115,185,220,220,155` | `K6X_D200_D205_D215_D220_D225_D230` | 0.959228 | YES | SUPPORTED | YES |
| K6V1_EXT09 | `110,225,125,210,200,145` | `K6X_D140_D160_D165_D170_D180_D190` | 0.797555 | YES | SUPPORTED | YES |
| K6V1_EXT10 | `230,225,190,225,105,135` | `K6X_D140_D160_D165_D170_D180_D190` | 1.207104 | YES | SUPPORTED | YES |
| K6V1_EXT11 | `230,150,225,110,205,105` | `K6X_D140_D160_D165_D170_D180_D190` | 1.172919 | YES | SUPPORTED | YES |
| K6V1_EXT12 | `100,230,230,185,225,120` | `K6X_D100_D200_D205_D210_D215_D220` | 0.851382 | YES | SUPPORTED | YES |
| K6V1_EXT13 | `100,110,115,120,225,100` | `K6X_D100_D105_D115_D120_D125_D130` | 0.804021 | YES | SUPPORTED | YES |
| K6V1_EXT14 | `110,120,100,225,105,190` | `K6X_D100_D115_D130_D145_D155_D185` | 0.767305 | YES | SUPPORTED | YES |

## Providers, coverage, and governance

- A1 deterministic LF: available, callable, P/XLIKE only, power-level auxiliary features.
- A2 learned provider: unavailable; frozen parity gate remains failed/not enabled.
- Complex provider: runtime not ready; not added to V2.
- Runtime feature cache: `20/20` geometries and `220/220` geometry-wavelength queries; SHA256 `acdbeab1ff20eba081aaf20d433d3d4b9a75dae3485e852ad519c54cbea1accc`.
- All 20 geometries remain OOD versus exact HF22 support. Coupling outcomes were not read or used.
- Future Stage-1 geometry-only metadata was not found in the checked frozen execution plan; no future labels were read.
- Immutable V1 confirmatory contract SHA256 remains `b8e156432c8ebd3b3087386b2dd768a177b6e0ef912f8eba4f1e40d3843e255c`.
- New FDTD/LumAPI solver runs, HF acquisition, RCWA, training, inverse design, and sealed HF reads: `0`.

## Authority

V1 authority base: `f8dad0e8438167ffca5ab22c19aa4790fa94b8d6`; repository branch at build: `work/np-k6-mdc-v1`; HEAD at build: `aeb8411f9c8300bc84fa9554caa4f25f1d57cc0f`.

Machine-readable detailed audit: `outputs/np_k6_coupling_forward_runtime_coverage_v2/`. This provider is not integrated Coupling truth, an FDTD replacement, a complex scattering operator, or a guarantee of OOD accuracy.

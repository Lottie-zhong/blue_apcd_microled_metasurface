# PW_K6_20G_H1_LEARNABILITY_BOUNDARY_AND_SPECTRAL_LATENT_V1

## STATUS

`PASS_WITH_REVIEW`

This is a zero-solver, offline-only learnability and spectral-latent audit. The
historical production conclusion is preserved: `H1_NOT_SUPPORTED_AFTER_TRUTH_FIX`.
The new diagnostic conclusion is `H1_LATENT_PARTIALLY_SUPPORTED`; this is not a
production-admission decision.

## Scope and safety boundary

- Scientific solver invocations: `0`.
- GPU/FDTD/AL/NP rebuild/geometry creation: not executed.
- Frozen `PW_K6_GRATING_TRUTH_V2` and `C_PW` physical truth: unchanged.
- Dataset: immutable ordered 20G set, D1--D6 geometry families as represented by
  the frozen dataset, 21 wavelengths from 440--460 nm, one spectral sample per
  geometry.
- All PCA bases used for spectral LOGO were fitted inside the corresponding
  training fold; the held-out geometry was not used to fit its basis.

## 20G data authority

| Item | Authority |
|---|---|
| Dataset size | 20 geometries x 21 wavelengths |
| Wavelengths | 440, 441, ..., 460 nm |
| Geometry metric | `sqrt(sum(((D_i-D_j)/130.0)^2))` |
| Truth schema | `PW_K6_GRATING_TRUTH_V2` |
| IN state | 324 coordinates, 81 propagating orders |
| PRENP state | 36 coordinates, 9 propagating orders |
| POSTNP state | 28 coordinates, 7 propagating orders |

The analysis uses propagating `C_hat` state for each plane. POSTNP compression
reconstructs the state and uses the exact frozen `P_scale` only for the physical
decoder, so state-compression error and scale-prediction error remain separable.

## Intrinsic dimension and variation decomposition

Required PCA ranks are shown as `90% / 95% / 99% / 99.9%` explained variance.

| Plane / stack | Global | Wavelength variation | Geometry variation |
|---|---:|---:|---:|
| IN | 7 / 9 / 15 / 24 | 7 / 9 / 15 / 24 | 8 / 10 / 14 / 18 |
| PRENP | 5 / 9 / 14 / 18 | 5 / 9 / 14 / 18 | 9 / 11 / 14 / 16 |
| POSTNP | 10 / 11 / 14 / 14 | 9 / 11 / 14 / 14 | 8 / 10 / 12 / 14 |
| IN+PRENP+POSTNP | 11 / 15 / 23 / 30 | 11 / 14 / 23 / 30 | 9 / 11 / 15 / 18 |

The complex state is therefore compressible in a descriptive PCA sense, but the
required dimension is not small enough to imply that a geometry-only predictor
will be accurate. TE/TM global ranks also differ materially:

| Plane | TE global | TM global |
|---|---:|---:|
| IN | 4 / 6 / 11 / 18 | 6 / 8 / 13 / 20 |
| PRENP | 12 / 15 / 17 / 18 | 5 / 9 / 14 / 18 |
| POSTNP | 10 / 12 / 14 / 14 | 10 / 11 / 14 / 14 |

At the individual-order level, the IN groups require median rank 2 at all four
variance targets (range 1--3 at 90% and 1--4 at 99.9%). Every PRENP and POSTNP
order group has rank 2 at all four targets. This indicates that order-local
coordinates are much simpler than the joint cross-order state, while the joint
state remains the relevant object for reconstruction.

## H2-preserving latent dimension

For the POSTNP global PCA reconstruction, the frozen H2 diagnostic criterion is
`routing/absolute-order/total q95 <= 0.002` for strict preservation and
`<= 0.005` for near-lossless preservation.

| PCA rank | State q95 | Routing q95 | Absolute-order q95 | Total-power q95 |
|---:|---:|---:|---:|---:|
| 8 | 0.57355 | 2.79724 | 1.38654 | 0.30289 |
| 12 | 0.31028 | 0.94092 | 0.80330 | 0.07396 |
| 16 | 3.80e-05 | 0.001485 | 0.001472 | 1.50e-09 |
| 20 | 2.54e-05 | 0.001485 | 0.001472 | 6.09e-10 |

Both `r_h2_strict` and `r_h2_near_lossless` are `16`. Thus a low-dimensional
latent exists diagnostically, but the physical H2-preserving latent is not the
10-dimensional 90%-variance representation; it requires at least 16 sampled
coordinates under the tested frozen decoder and q95 criteria.

## Pointwise versus spectral LOGO

The prior pointwise H1-D Ridge result remains poor: state relative-error median
`0.8415`, routing median `0.8449`, absolute-order median `0.9222`, and scale
relative-error median `0.4953`. The shallow MLP gives state median `1.1709`,
routing median `0.8431`, absolute-order median `0.8409`, and scale median
`0.2376`; this does not establish production learnability.

The new fold-fitted spectral LOGO uses PCA rank 16:

| Model | State relative median / q95 | Routing relative median / q95 | Absolute-order relative median / q95 | Total relative median / q95 |
|---|---:|---:|---:|---:|
| Ridge | 0.84699 / 1.16819 | 0.75335 / 14.04637 | 0.74365 / 4.00362 | 0.31091 / 0.61814 |
| Shallow MLP | 0.98114 / 1.42506 | 0.77863 / 15.89104 | 0.75224 / 7.98438 | 0.18237 / 0.49579 |

Spectral parameterization changes the error profile but does not remove the
large held-out-geometry tails. It is therefore not evidence for a production
H1 pass, and it does not justify changing the frozen comparator.

## Geometry to latent / state LOGO

The direct pointwise Ridge learning curve gives state relative-error medians of
`0.9243`, `0.8568`, `0.8531`, and `0.8415` for 8G, 12G, 16G, and 20G. The
improvement is modest and not enough to make the state prediction usable for
production reconstruction.

Geometry-only local interpolation is also insufficient. Median errors are:

| Baseline | State | Routing | Absolute order | Total power* |
|---|---:|---:|---:|---:|
| Nearest | 1.13246 | 0.73533 | 0.70906 | ~0 |
| IDW | 0.77149 | 0.86356 | 0.90335 | 0.52491 |
| RBF | 0.76943 | 0.87446 | 0.90891 | 0.51935 |

`*` The nearest-baseline total is near zero only because the exact frozen
`P_scale` was used in this decoder diagnostic; it must not be interpreted as a
learned total-power result. Nearest routing and absolute-order tails are also
very large (q95 `22.49` and `11.18`, respectively).

## P_scale branch

The scalar/spectral power-scale branch is more learnable than the complex state,
but still not production-ready by itself:

| Model | Relative median / q95 | Pearson / Spearman |
|---|---:|---:|
| Ridge | 0.14982 / 0.52737 | 0.93504 / 0.92983 |
| Shallow MLP | 0.15739 / 0.71663 | 0.92309 / 0.90329 |

This supports separating `P_scale` from state prediction in future model
benchmarks. It does not repair the high-dimensional complex-state and
order-resolved error tails.

## Geometry smoothness and coverage

Across 190 geometry pairs, geometry distance is only weakly and negatively
correlated with state distance (Pearson `-0.2041`, Spearman `-0.1925`) and with
routing distance (Pearson `-0.1937`, Spearman `-0.1974`). The state-distance
Lipschitz statistic has median `4.1216`, q95 `7.6594`, and maximum `9.2304`.

The sampled geometry domain is not densely local: nearest-neighbor distances
are approximately `0.825`--`1.069` for the listed cases. A representative
near pair has geometry distance `0.9012` but state distance `8.3183`, whereas a
far pair at distance `1.7929` has state distance `3.7423`. This is evidence
against assuming smooth Euclidean geometry-to-state interpolation, although it
is not a proof of a physical discontinuity outside this sampled domain.

Coverage diagnostics do not show a clean data-limited law. Nearest geometry
distance versus factor-Ridge state error gives Pearson `-0.3790` and Spearman
`-0.3126`; versus absolute-order error it gives Pearson `0.0982` and Spearman
`0.0279`. Farther points are not consistently harder, and the absolute-order
metric has essentially no monotonic coverage relationship.

## 8G -> 12G -> 16G -> 20G learning curve

Direct pointwise Ridge medians:

| Geometry count | State | Routing | Absolute order | Total power |
|---:|---:|---:|---:|---:|
| 8G | 0.92435 | 0.79483 | 0.82693 | 0.61430 |
| 12G | 0.85683 | 0.83680 | 0.88251 | 0.63252 |
| 16G | 0.85308 | 0.82330 | 0.89253 | 0.71049 |
| 20G | 0.84152 | 0.84489 | 0.91625 | 0.71984 |

Only the complex-state median improves slightly with more geometries. Routing,
absolute-order, and total-power medians are non-monotonic or worsen. The curve
does not support a simple claim that adding the current geometry points will
close H1.

## H1 failure classification

Dominant classification: `MIXED`.

Evidence does not support a single-cause label:

- **Not cleanly data-limited:** distance-to-error correlations are weak and the
  error does not grow monotonically with nearest geometry distance.
- **Not cleanly spectral-parameterization-limited:** fold-fitted spectral PCA
  changes some medians but leaves large held-out tails.
- **Not cleanly geometry-smooth:** geometry/state and geometry/routing pairwise
  correlations are weak, with large response differences among moderately
  close geometries.
- **Model/target capacity remains a live limitation:** Ridge, shallow MLP, and
  local interpolation do not reliably predict the H2-preserving state or its
  physical decoded quantities; the separate `P_scale` branch is materially
  easier but does not solve the state problem.

Diagnostic verdict: `H1_LATENT_PARTIALLY_SUPPORTED`.

This means the immutable truth contains a useful compressible latent structure
and a separable, moderately learnable scale branch. It does not mean that
geometry-only inference currently meets production H1 fidelity. The historical
verdict `H1_NOT_SUPPORTED_AFTER_TRUTH_FIX` remains unchanged.

## NP and MDC forensic boundary

The NP provider artifact is still missing: `NP_PROVIDER_ARTIFACT_MISSING`.
Only read-only forensic status is recorded; no NP rebuild or retraining was
performed. The future prior question remains: compare geometry-to-`z_CPW` with
geometry plus exact frozen NP features to `z_CPW`. NP remains a low-fidelity
physics prior, not an available production truth source in this task.

MDC is fixed in the 20G dataset. No variable-MDC surrogate feature was added.

## Exactly one next route recommendation

**D. MODEL_CAPACITY_BENCHMARK** — design one controlled offline benchmark for
state-plus-`P_scale` capacity, retaining the frozen `C_PW`, decoder, truth,
geometry metric, and fold discipline. Do not execute it in this task. Active
learning is `ACTIVE_LEARNING_NOT_READY` until a model family can pass the
frozen held-out state/order gates without relying on oracle scale.

## Provenance and hashes

| Artifact | SHA256 |
|---|---|
| Freeze manifest | `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c` |
| Source provenance | `e32d72cd0898d17dad0f0fb7cf2879e514139cafe1d2b5328f1fbbe229f20d5d` |
| `PW_K6_GRATING_TRUTH_V2` | `4f894932b14be549a5483f3a3731a1e71869759357d4eddeb7ba4dc0d5108408` |
| State code | `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15` |
| Launcher code | `48d3c332fde679a9d8dc991a5ba8cd75aecdcb54750d7ec1774f732203ef08be` |
| Geometry-domain authority | `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f` |

Machine-readable companion:
`reports/coupling/PW_K6_20G_H1_LEARNABILITY_BOUNDARY_AND_SPECTRAL_LATENT_V1_ANALYSIS.json`

## Git and execution boundary

- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `eefda35d53eb6953fb5819da25b659dbfc4fd4df`
- Upstream: none
- No commit and no push performed.
- Existing dirty/untracked worktree content was preserved.
- No scientific solver action was executed.


# PW_K6_STRUCTURED_FORWARD_MODEL_FREEZE_V1

## STATUS

`PASS_WITH_REVIEW`

This is a zero-solver, offline-only model-definition freeze. It freezes a
research-use structured forward-model contract and a statistical comparator;
it is not a production-admission event.

No FDTD solver, scientific attempt, new geometry, Active Learning run, NP
rebuild, variable-MDC run, K4/K9 run, broad hyperparameter search, truth
rewrite, or retraining to improve the existing 20G metrics was performed in
this task.

## PRIMARY MODEL CONTRACT

### Version and role

The primary structured candidate is frozen as:

`PW_K6_STRUCTURED_FORWARD_MODEL_V1`

It is the M5-type ordered geometry-to-state model with width `32`, selected
from the already completed M5 capacity probes. It is a research-use forward
model, not an H1 production-certified model.

### Immutable data authority

- Ordered 20G geometry set, exactly in this order:
  `K6V1_S02, K6V1_S03, K6V1_S04, K6V1_S05, K6V1_S15, K6V1_S16,
  K6V1_EXT01 ... K6V1_EXT14`.
- Wavelength grid: 21 points, 440--460 nm.
- Planes: `IN`, `PRENP`, `POSTNP`.
- POSTNP state: 28 real coordinates representing seven propagating orders
  and two polarizations.
- Joint H2 spectral latent: rank 16, fit inside each outer training fold.
- Order-local representation: seven absolute-order-specific rank-2 PCA
  latents, one PCA per propagating order, fit inside each outer training fold.
- Frozen truth: `PW_K6_GRATING_TRUTH_V2`.
- Original `C_PW` and the `C_hat/P_scale` factorization remain unchanged.
- Decoder: deterministic frozen H2 decoder.
- Geometry metric:
  `sqrt(sum(((D_i-D_j)/130.0)^2))`.
- Absolute-order threshold used by the completed benchmark:
  `0.0009885656815447454`.

### Input and state branch

Input is the physical ordered vector `D1 ... D6`. The order is meaningful;
the contract does not impose diameter sorting, permutation invariance, or
cyclic invariance.

The frozen state branch is:

```text
D1...D6
  -> six-dimensional ordered geometry input
  -> feature scaling fit only on the outer training geometries
  -> shared encoder: Linear(6,32) -> ReLU -> Linear(32,32) -> ReLU
  -> seven absolute-order heads: each Linear(32,2)
  -> concatenate 7 x rank-2 order-local latent = 14 values
  -> cross-order residual fusion:
       Linear(14,32) -> ReLU -> Linear(32,14)
       output = order-local output + fusion output
  -> inverse-transform the seven fold-fitted rank-2 PCA representations
  -> reconstruct joint normalized C_hat
```

The model has `2,684` trainable parameters at width 32. The parameter count
and architecture are frozen; any change requires a new model version.

### Physics and scale branch

The physical forward path is:

```text
predicted C_hat + predicted P_scale
  -> frozen physical state reconstruction
  -> deterministic H2 decoder
  -> routing power, absolute-order power, and total power
```

`P_scale` is never replaced by oracle truth in prospective use.

### Training contract

- Optimizer: `AdamW`.
- Learning rate: `2e-3`.
- Weight decay: `1e-4`.
- Gradient norm clipping: `5.0`.
- Activation: `ReLU`.
- Maximum epochs: `320`.
- Early stopping patience: `45` epochs without validation improvement.
- Early-stopping objective: normalized mean-square error on the geometry-held
  inner validation fold.
- Fixed seeds: `0, 1, 2`; final prediction is the mean of the three seed
  predictions.
- Random seeds are not a license for post-hoc seed selection.

Width selection is now frozen to `32`; no future width search is implied.

## PREPROCESSING CONTRACT

1. Geometry input is the ordered six-vector divided by `130.0` nm, followed by
   a `StandardScaler` fitted only on the relevant outer-training geometries.
2. For each outer fold, the rank-2 PCA bases are fitted only on training
   geometries. The seven order bases operate on the per-order real/imaginary
   spectral features `[Re(TE), Re(TM), Im(TE), Im(TM)]` over 21 wavelengths.
3. State targets are the seven order-local rank-2 scores. The decoder receives
   the reconstructed normalized POSTNP state and the separately predicted
   scale.
4. No wavelength-random split, truth-derived test normalization, oracle scale,
   diameter sorting, or symmetry augmentation is allowed.

## P_SCALE MODEL CONTRACT

`PW_K6_PSCALE_MODEL_V1`

- Input: the same ordered six-dimensional geometry vector used by the state
  branch; no wavelength is an input.
- Target: the 21-wavelength `POSTNP_TOTAL_POWER_V2` spectrum, i.e. `P_scale`.
- Model: independent Kernel Ridge regression with an RBF kernel.
- Input and target normalization: `StandardScaler` fit inside each outer
  training fold; inverse-transform predictions before physical decoding.
- Candidate grid already evaluated, and now frozen as the selection grid:
  `alpha in {0.1, 1.0, 10.0}`, `gamma in {0.1, 1.0}`.
- Selection: minimum normalized MSE averaged over the three geometry-grouped
  inner folds of the outer training set. The test geometry is never used for
  selection.
- Fold discipline: strict 20-fold geometry LOGO; one geometry remains wholly
  held out with all 21 wavelengths.
- Oracle `P_scale` is forbidden.

The completed benchmark selected Kernel Ridge on 19/20 outer folds and Ridge
on 1/20 under its model-family comparison. This freeze fixes the model family
to Kernel Ridge for future prospective use; it does not retroactively change
the completed benchmark numbers.

## KERNEL COMPARATOR

`PW_K6_KERNEL_BASELINE_V1`

This is M2 Kernel Ridge, a prospective statistical nonlinear comparator and
not the primary structured model.

- Input: ordered geometry `D1...D6`, normalized by `130.0` and then scaled
  within the outer training fold.
- Target: the fold-fitted rank-16 joint spectral latent of the normalized
  POSTNP state.
- Kernel: RBF Kernel Ridge.
- Candidate grid: `alpha in {0.1, 1.0, 10.0}` and
  `gamma in {0.1, 1.0}`.
- Hyperparameter rule: three geometry-grouped inner folds, minimum normalized
  MSE; no test-geometry information.
- Reconstruct state with the fold-fitted rank-16 PCA basis and use the frozen
  decoder and non-oracle scale branch for physical metrics.

## RETROSPECTIVE 20G PERFORMANCE

All values below are `RETROSPECTIVE_20G_BENCHMARK` values. They are not
prospective validation and do not establish production H1 admission.

### Exact frozen M5 width-32 capacity probe

| Metric | Train median | Held-out median | Held-out q95 |
|---|---:|---:|---:|
| State relative error | 0.69515 | 0.80160 | 0.98857 |
| Routing relative error | 0.83605 | 0.86160 | 3.75076 |
| Absolute-order relative error | -- | 0.90152 | 0.99908 |
| Total-power relative error | -- | 0.50162 | 0.66745 |

Parameter count is `2,684`. The width-32 probe improved routing q95 over
width 16 (`3.75076` vs `4.81610`) and improved state median (`0.80160` vs
`0.81008`), while state q95 was slightly worse (`0.98857` vs `0.97719`).
The train/held-out relationship did not show a stronger overfit signal than
width 16. This is the frozen balance choice, not a claim of universal metric
dominance.

Offline comparison of the existing per-geometry outputs against matched M0a
Ridge gives width-32 improved/worsened counts:

| Metric | Improved | Worsened |
|---|---:|---:|
| State | 7 | 13 |
| Routing | 7 | 13 |
| Absolute-order | 9 | 11 |
| Total power | 9 | 11 |

These counts are descriptive and do not override the production gate.

### Completed M5 mixed-width LOGO record

The benchmark's selected-width M5 record (the prior evidence used to choose
the freeze) was:

| Metric | Median | q95 |
|---|---:|---:|
| State relative error | 0.76692 | 0.97735 |
| Routing relative error | 0.87111 | 3.55808 |
| Absolute-order relative error | 0.90450 | 0.99864 |
| Total-power relative error | 0.50545 | 0.65135 |

Routing Pearson correlation was `0.80973`; seed state-median standard
deviation was `0.01619`. The mixed-width record improved state on 11/20,
routing on 9/20, absolute-order on 10/20, and total power on 13/20 against
M0a. It is retained as historical benchmark evidence, not as the frozen
prospective architecture.

### Kernel comparator record

| Metric | Median | q95 |
|---|---:|---:|
| State relative error | 0.76838 | 1.00521 |
| Routing relative error | 0.87458 | 3.05270 |
| Absolute-order relative error | 0.90927 | 0.99699 |
| Total-power relative error | 0.51073 | 0.65618 |

Routing Pearson correlation was `0.80981`. M2 improved state on 11/20,
routing on 13/20, and absolute-order on 13/20 against M0a, but had negative
worst-case improvement on every such comparison. It remains a comparator.

### P_scale record

For the already evaluated standalone scale family:

| Model | Median | q95 | Pearson | Spearman |
|---|---:|---:|---:|---:|
| Ridge | 0.13247 | 0.41708 | 0.95562 | 0.94577 |
| Kernel Ridge | 0.12977 | 0.40941 | 0.95615 | 0.94201 |
| Shallow MLP | 0.16340 | 0.72450 | 0.91990 | 0.89916 |

## VALIDATION CONTRACT

### Retrospective benchmark

- Outer: strict 20-fold geometry LOGO.
- Inner: three geometry-grouped folds inside every outer training set.
- Statistical unit: one geometry; the 21 wavelengths remain correlated within
  that geometry.
- All scaling, PCA basis fitting, model selection, and early stopping are
  outer-training-only.

### Future prospective validation

Every new HF geometry must be classified before solver entry as exactly one of:

`PROSPECTIVE_VALIDATION` or `TRAINING_EXPANSION`.

For `PROSPECTIVE_VALIDATION`:

1. Score once with the frozen V1 model and frozen P_scale model.
2. Persist the prediction and its hash before revealing HF truth.
3. Do not use it for architecture choice, hyperparameter choice, PCA refit,
   preprocessing redesign, or model refit before the validation record is
   frozen.
4. After HF truth is available, compare state, routing, absolute-order, and
   total-power metrics using the frozen decoder.
5. Preserve the geometry as prospective evidence; only a separately declared
   `TRAINING_EXPANSION` may later enter fitting.

## H1 PRODUCTION GATES

The following gate structure is frozen as a candidate contract. Numeric limits
must come from the existing technical-lead/Chart authority before any claim
of `PRODUCTION_H1_PASS`; no permissive thresholds are invented here.

All four physical metrics must be evaluated on strict held-out geometries and
on every prospective validation geometry:

1. **State fidelity gate**: state median and q95 must be at or below the
   pre-registered state limits, with no unresolved NaN, latent reconstruction,
   or decoder failure.
2. **Routing fidelity gate**: routing median and q95 must be at or below the
   pre-registered routing limits, and correlation must meet the pre-registered
   lower bound.
3. **Absolute-order fidelity gate**: the thresholded absolute-order median and
   q95 must be at or below the pre-registered limits, with the frozen absolute
   order threshold unchanged.
4. **Total-power fidelity gate**: total-power median and q95 must be at or
   below the pre-registered limits using predicted, not oracle, `P_scale`.
5. **Held-out/prospective stability gate**: no metric may be accepted solely
   from a favorable aggregate median. Per-geometry results, worst geometry,
   prospective prediction-before-truth records, and seed variability must be
   retained and pass the pre-registered stability rules.

Current gate state:

- `RESEARCH_USEFUL`: supported by controlled capacity evidence.
- `PRODUCTION_H1_PASS`: **NOT DECLARED**.
- Numeric H1 limits: **not newly frozen by this task**.
- Active Learning: **disabled** until usable prospective H1 evidence and
  physically closed uncertainty semantics exist.

## H1 RESEARCH STATUS

`RESEARCH_USEFUL`

The completed evidence supports freezing a structured research candidate and
continuing prospective validation. It does not support relabeling the model as
production H1.

## H1 PRODUCTION STATUS

`H1_NOT_SUPPORTED_AFTER_TRUTH_FIX` remains the historical production status.
The current freeze does not alter that status and does not declare a new H1
pass.

## FUTURE NP PRIOR ABLATION

NP remains `NP_PROVIDER_ARTIFACT_MISSING`; no rebuild was attempted.

Pre-registered future comparison:

- A: `PW_K6_STRUCTURED_FORWARD_MODEL_V1` with geometry only.
- B: the same frozen architecture with exact frozen NP-prior features appended
  or conditioned.

Geometry split, target representation, P_scale target, decoder, optimizer,
seeds, and metrics must remain matched. Architecture retuning for B is not
allowed without a new versioned benchmark.

## FUTURE MDC PRIOR ROLE

MDC is fixed in the current 20G set and is not injected into this freeze.

Future variable-MDC work, if separately authorized, is:

```text
geometry inputs + z_NP + z_MDC -> integrated state
```

MDC and NP surrogate outputs remain low-fidelity physics features and never
replace frozen truth.

## ACTIVE LEARNING STATUS

`DISABLED / NOT_READY`

Freezing this model does not authorize Active Learning. AL requires usable
prospective H1 evidence, physically closed uncertainty semantics, and stable
unseen-geometry prediction.

## ARTIFACT HASHES

Hashes carried unchanged from the completed benchmark authority:

| Artifact | SHA256 |
|---|---|
| `PW_K6_20G_DATASET_FREEZE_MANIFEST_V1.json` | `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c` |
| `PW_K6_20G_SOURCE_PROVENANCE_MANIFEST_V1.json` | `e32d72cd0898d17dad0f0fb7cf2879e514139cafe1d2b5328f1fbbe229f20d5d` |
| `PW_K6_GRATING_TRUTH_V2.json` | `4f894932b14be549a5483f3a3731a1e71869759357d4eddeb7ba4dc0d5108408` |
| `pw_complex_floquet_state_v1.py` | `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15` |
| `pw_scientific_launcher.py` | `48d3c332fde679a9d8dc991a5ba8cd75aecdcb54750d7ec1774f732203ef08be` |
| `PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json` | `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f` |
| completed benchmark analysis JSON | `dfb65f4b70567ffbf3f33036a605b9ace3ebfb405551d79c8b59f088e694b41e` |

The report path is:

`reports/coupling/PW_K6_STRUCTURED_FORWARD_MODEL_FREEZE_V1.md`

## GIT

- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `eefda35d53eb6953fb5819da25b659dbfc4fd4df`
- Upstream: none.
- Existing dirty/untracked files are preserved and are not part of this
  report operation.
- No broad staging, commit, or push is authorized by this report operation.

## NEXT RECOMMENDATION

Do not execute automatically. The single next recommendation is:

`CHART_REVIEW_OF_FROZEN_V1_AND_NUMERIC_H1_GATE_AUTHORITY`

After that review, any prospective HF geometry must be explicitly classified
before solver entry. No solver or Active Learning action is authorized by this
freeze.

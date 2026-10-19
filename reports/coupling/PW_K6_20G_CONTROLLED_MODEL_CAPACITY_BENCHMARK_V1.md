# PW_K6_20G_CONTROLLED_MODEL_CAPACITY_BENCHMARK_V1

## STATUS

`PASS_WITH_REVIEW`

This is a zero-solver, offline-only controlled model-capacity benchmark. The
historical production verdict remains `H1_NOT_SUPPORTED_AFTER_TRUTH_FIX`.
The diagnostic update is `H1_CAPACITY_SUPPORTED`; this is not a production
H1 admission.

No FDTD solver, scientific attempt, Active Learning, NP rebuild, variable MDC,
K4/K9 branch, or truth modification was performed.

## Frozen benchmark authority

- Dataset: immutable ordered 20G geometry set, one geometry as one independent
  sample.
- Wavelengths: 21 correlated observations per geometry, 440--460 nm.
- Outer validation: strict 20-fold geometry LOGO.
- Inner validation: 3-fold geometry-grouped validation inside each outer
  training set.
- No wavelength-random train/test splitting.
- Truth: `PW_K6_GRATING_TRUTH_V2`, original `C_PW`, frozen
  `C_hat/P_scale` factorization, deterministic H2 decoder.
- POSTNP state: 28 coordinates, 7 propagating orders.
- Primary joint spectral latent: rank 16, fitted inside each outer training
  fold.
- Order-local spectral latent: rank 2 separately for each of the 7 POSTNP
  orders, fitted inside each outer training fold.
- Geometry metric:
  `sqrt(sum(((D_i-D_j)/130.0)^2))`.

All input/output scaling, PCA fitting, regularization selection, and neural
early stopping were restricted to outer-training geometries. GPU was used only
for compact ML training. The scientific GPU guard found no
`fdtd-solutions.exe`/FDTD engine process before ML execution.

## FROZEN BASELINES

Historical H1-D numbers are carried forward without modification:

| Historical comparator | State relative median | Routing relative median | Absolute-order relative median |
|---|---:|---:|---:|
| Ridge H1-D | 0.84152 | 0.84489 | 0.92225 |
| Shallow MLP H1-D | 1.17091 | 0.84308 | 0.84092 |

The matched-fold benchmark baselines use the rank-16 fold-fitted spectral
representation and a non-oracle, inner-selected P_scale branch. They are not
substitutions for the historical numbers:

| Matched baseline | State median / q95 | Routing median / q95 | Absolute-order median / q95 | Total median / q95 |
|---|---:|---:|---:|---:|
| M0a Ridge | 0.76797 / 1.01287 | 0.87558 / 3.25164 | 0.90833 / 0.99812 | 0.50602 / 0.65670 |
| M0b shallow MLP | 0.98798 / 1.45302 | 0.78316 / 16.14190 | 0.76150 / 8.03460 | 0.25144 / 0.67636 |

The matched M0a Ridge is the reference for held-out geometry consistency.

## QUADRATIC RIDGE

M1 adds ordered geometry terms
`D_i`, `D_i^2`, and `D_iD_j` with regularized Ridge selection inside
the inner folds. No sorting, permutation invariance, or cyclic invariance was
introduced.

| Metric | Median / q95 |
|---|---:|
| State relative error | 0.77433 / 1.03769 |
| Routing relative error | 0.84826 / 5.40883 |
| Routing correlation, Pearson | 0.79650 |
| Absolute-order relative error | 0.87038 / 1.07161 |
| Total-power relative error | 0.49568 / 0.66189 |

Quadratic interactions do not improve the full held-out routing tail and are
not sufficient as the primary capacity solution.

## KERNEL / GP

The controlled nonlinear kernel family used Kernel Ridge with an RBF kernel and
a small inner-fold grid over alpha and gamma. A GP was not run; Kernel Ridge
was the preferred practical kernel model for this benchmark, and no broad
architecture/kernel search was performed.

| Metric | Kernel Ridge median / q95 |
|---|---:|
| State relative error | 0.76838 / 1.00521 |
| Routing relative error | 0.87458 / 3.05270 |
| Routing correlation, Pearson | 0.80981 |
| Absolute-order relative error | 0.90927 / 0.99699 |
| Total-power relative error | 0.51073 / 0.65618 |

Against M0a Ridge, Kernel Ridge improves 11/20 geometries in state error,
13/20 in routing error, and 13/20 in absolute-order error. Its median
improvements are +0.00137, +0.03316, and +0.00200, respectively. The
worst-case improvements remain negative, so the result is useful capacity
evidence but not a uniformly stable production model.

## COMPACT MLP

M3 is a compact residual MLP with ordered six-dimensional geometry input,
widths 16/32/64, small inner selection, and three fixed seeds. The final
held-out ensemble is the mean of the three seed predictions.

| Metric | M3 median / q95 |
|---|---:|
| State relative error | 0.83710 / 1.03306 |
| Routing relative error | 0.80484 / 10.82382 |
| Routing correlation, Pearson | 0.75348 |
| Absolute-order relative error | 0.79682 / 2.85476 |
| Total-power relative error | 0.39273 / 0.62350 |
| Seed state-median standard deviation | 0.00729 |

M3 improves total power and some median order metrics, but its routing q95
remains unstable. Against M0a, it improves state on 6/20 geometries and
routing on 7/20, while worsening state on 14/20 and routing on 13/20.

## ORDER-LOCAL MULTI-HEAD

M4 uses a small shared encoder and seven absolute-order-specific heads. Each
head predicts a separately fitted rank-2 spectral latent for one propagating
POSTNP order, then reconstructs the order state and assembles the joint
`C_hat` before the deterministic H2 decoder.

| Metric | M4 median / q95 |
|---|---:|
| State relative error | 0.79536 / 0.978999 |
| Routing relative error | 0.86785 / 3.63891 |
| Routing correlation, Pearson | 0.80964 |
| Absolute-order relative error | 0.90729 / 0.99812 |
| Total-power relative error | 0.49733 / 0.64922 |
| Seed state-median standard deviation | 0.00887 |

M4 reduces the state q95 relative to M0a, but does not reduce the routing q95
or absolute-order q95 enough to establish a uniform H1 improvement.

## CROSS-ORDER COUPLING

M5 adds one small cross-order fusion block after the order-local heads. It is
not a generic deep network.

| Metric | M5 median / q95 |
|---|---:|
| State relative error | 0.76692 / 0.97735 |
| Routing relative error | 0.87111 / 3.55808 |
| Routing correlation, Pearson | 0.80973 |
| Absolute-order relative error | 0.90450 / 0.99864 |
| Total-power relative error | 0.50545 / 0.65135 |
| Seed state-median standard deviation | 0.01619 |

M5 gives the best state median among the tested state-mediated models and
improves state on 11/20 geometries against M0a. However, routing improves on
only 9/20 geometries, and its routing/absolute-order q95 values do not beat
M0a. Cross-order coupling is therefore promising for state representation but
not yet a complete physical-fidelity solution.

## P_SCALE BRANCH

P_scale was trained separately and was never replaced by oracle P_scale during
the final end-to-end evaluations.

| Model | Relative median / q95 | Pearson / Spearman |
|---|---:|---:|
| Ridge | 0.13247 / 0.41708 | 0.95562 / 0.94577 |
| Kernel Ridge | 0.12977 / 0.40941 | 0.95615 / 0.94201 |
| Shallow MLP | 0.16340 / 0.72450 | 0.91990 / 0.89916 |

The scale branch is substantially easier than complex-state prediction. This
supports retaining a separate scale branch in the forward model, but it does
not by itself establish H1 production fidelity.

## CAPACITY CURVE

Training and held-out metrics below use the same non-oracle scale branch. The
capacity probes are descriptive outer-fold evaluations; they were not used to
select a model using held-out geometry information.

### M3 compact residual MLP

| Width | Parameters | Train state median | Held-out state median / q95 | Held-out routing median / q95 |
|---:|---:|---:|---:|---:|
| 16 | 768 | 0.70982 | 0.91973 / 1.20991 | 0.77075 / 16.10548 |
| 32 | 1,920 | 0.69268 | 0.88200 / 1.07671 | 0.76416 / 8.26181 |
| 64 | 5,760 | 0.67543 | 0.88030 / 1.07776 | 0.77585 / 15.20316 |

Width 16→32 improves both training and held-out state error. Width 64 lowers
training error further but does not improve held-out state and worsens the
routing tail. This is controlled capacity with an overfit/instability signal
at the larger width.

### M4 order-local multi-head

| Width | Parameters | Train state median | Held-out state median / q95 | Held-out routing median / q95 |
|---:|---:|---:|---:|---:|
| 16 | 622 | 0.69394 | 0.79682 / 0.97467 | 0.88720 / 4.46978 |
| 32 | 1,742 | 0.70787 | 0.79102 / 0.98625 | 0.84851 / 4.07007 |

M4 improves held-out state median with width 32 and improves routing q95, but
the state q95 is slightly better at width 16. This is not a monotonic capacity
curve across all physical metrics.

### M5 shared + cross-order coupling

| Width | Parameters | Train state median | Held-out state median / q95 | Held-out routing median / q95 |
|---:|---:|---:|---:|---:|
| 16 | 1,100 | 0.68780 | 0.81008 / 0.97719 | 0.86643 / 4.81610 |
| 32 | 2,684 | 0.69515 | 0.80160 / 0.98857 | 0.86160 / 3.75076 |

M5 width 32 improves routing q95 relative to width 16, while its state q95
slightly worsens. The structured models show useful inductive structure but
not a universal capacity-dominates-error pattern.

## HELD-OUT GEOMETRY CONSISTENCY

Improvement is defined as M0a error minus candidate error; positive means the
candidate is better. Counts are over 20 held-out geometries.

| Candidate | State improved/worsened | Routing improved/worsened | Absolute-order improved/worsened | Total improved/worsened |
|---|---:|---:|---:|---:|
| M1 quadratic Ridge | 6 / 14 | 5 / 15 | 9 / 11 | 15 / 5 |
| M2 Kernel Ridge | 11 / 9 | 13 / 7 | 13 / 7 | 9 / 11 |
| M3 compact MLP | 6 / 14 | 7 / 13 | 10 / 10 | 19 / 1 |
| M4 order-local | 10 / 10 | 8 / 12 | 9 / 11 | 13 / 7 |
| M5 cross-order | 11 / 9 | 9 / 11 | 10 / 10 | 13 / 7 |

The best global q95 combination among the tested state-mediated candidates is
M2 Kernel Ridge for routing and absolute-order tails, while M5 has the best
state median/q95 combination in the structured branch. No candidate improves
every metric and every worst geometry relative to M0a.

## DIRECT ROUTING COMPARATOR

The secondary direct comparator is:

`[geometry, wavelength] -> routing`

using the existing shallow MLP form. It is not used to replace the physical
state mainline.

| Comparator | Routing relative median / q95 | Pearson correlation | RMSE |
|---|---:|---:|---:|
| Direct routing MLP | 1.00258 / 25.98431 | 0.48263 | 0.19213 |
| M2 state-mediated | 0.87458 / 3.05270 | 0.80981 | -- |
| M5 state-mediated | 0.87111 / 3.55808 | 0.80973 | -- |

The best state-mediated models exceed this direct-routing comparator in the
observed routing median, q95, and correlation while retaining the physically
interpretable H2 decoder. This is a secondary comparison, not an admission
gate.

## CPU/GPU PARITY

One compact MLP fold was trained through both CPU and CUDA paths:

- maximum prediction absolute difference: `2.76e-6`
- prediction RMSE difference: `1.30e-6`
- parity status: `PASS_NUMERICAL_CLOSE`
- scientific entry count changed: `false`

GPU was used only for ML training. No `fdtd-solutions.exe` or FDTD engine
was invoked.

## CAPACITY VERDICT

**`USEFUL_MODEL_CAPACITY_FOUND`**

The verdict is deliberately narrow. Kernel Ridge produces a small but
consistent aggregate improvement over the matched Ridge baseline in state,
routing, and absolute-order q95, and the structured M4/M5 branch improves
state-tail behavior. However, the worst-geometry and metric-by-metric
consistency tables show that useful capacity has not converted into a
uniformly production-safe H1 model.

## H1 DIAGNOSTIC UPDATE

- Historical production verdict: `H1_NOT_SUPPORTED_AFTER_TRUTH_FIX`
- Diagnostic capacity status: `H1_CAPACITY_SUPPORTED`
- H2: `SUPPORTED`
- Production H1 PASS: **not declared**
- Active Learning: prohibited until useful strict held-out structure is
  stable across the frozen physical metrics.

The capacity result means that controlled nonlinear and structured model
capacity can materially improve selected strict held-out metrics. It does not
authorize changing the frozen comparator or starting scientific production.

## NP PROVIDER STATUS

`NP_PROVIDER_ARTIFACT_MISSING`.

Only read-only artifact status was used. No NP rebuild, retraining, or prior
injection was performed. A future NP comparison remains reserved for:

`best geometry model` versus `best geometry + exact frozen NP-prior model`.

## NEXT SCIENTIFIC ROUTE

**A. `FREEZE_STRUCTURED_FORWARD_MODEL`**

Freeze one controlled structured forward-model candidate, retaining the rank-16
joint state, separate P_scale branch, order-local heads, deterministic H2
decoder, and geometry-grouped validation contracts. Do not execute this route
in this task.

## Provenance and hashes

| Artifact | SHA256 |
|---|---|
| Freeze manifest | `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c` |
| Source provenance | `e32d72cd0898d17dad0f0fb7cf2879e514139cafe1d2b5328f1fbbe229f20d5d` |
| V2 truth | `4f894932b14be549a5483f3a3731a1e71869759357d4eddeb7ba4dc0d5108408` |
| State code | `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15` |
| Launcher code | `48d3c332fde679a9d8dc991a5ba8cd75aecdcb54750d7ec1774f732203ef08be` |
| Geometry-domain authority | `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f` |

Machine-readable companion:

`reports/coupling/PW_K6_20G_CONTROLLED_MODEL_CAPACITY_BENCHMARK_V1_ANALYSIS.json`

## GIT

- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `eefda35d53eb6953fb5819da25b659dbfc4fd4df`
- Upstream: none
- Existing dirty/untracked worktree content preserved.
- No commit and no push performed.

## NEXT

Do not execute the recommended route in this task. Preserve the benchmark JSON
and this report as the current offline evidence boundary.


# PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1

## STATUS

`PASS_WITH_REVIEW`

This is a zero-solver authority freeze and a read-only application of Chart
H1 gates to the existing frozen 20G evidence. No FDTD solver, scientific
attempt, retraining, retuning, prospective HF validation, NP rebuild, Active
Learning, truth modification, or C_PW modification was performed.

## CHART NUMERIC AUTHORITY

The following limits are conjunctive. A favorable mean, median, correlation,
or low-power ratio cannot compensate for another physical-gate failure.

| Gate | Limit |
|---|---:|
| State relative RMSE median | <= 0.50 |
| State relative RMSE q95 | <= 0.80 |
| Routing eta RMSE median | <= 0.05 |
| Routing eta RMSE q95 | <= 0.10 |
| Routing Pearson | >= 0.95 |
| Absolute-order source-normalized RMSE median | <= 0.05 |
| Absolute-order source-normalized RMSE q95 | <= 0.10 |
| Thresholded absolute-order relative median | <= 0.30 |
| Thresholded absolute-order relative q95 | <= 0.75 |
| Total-power relative median | <= 0.15 |
| Total-power relative q95 | <= 0.30 |
| Total-power Pearson | >= 0.95 |
| Seed state-median standard deviation | <= 0.03 |

The frozen thresholded absolute-order significance threshold is
`0.0009885656815447454`.

## METRIC DEFINITIONS

- **State:** relative RMSE of predicted frozen `C_hat` versus true `C_hat`.
- **Routing:** RMSE on normalized propagating-order fractions `eta_m`.
- **Absolute order:** source-normalized RMSE on
  `PW_K6_GRATING_TRUTH_V2` absolute order powers.
- **Thresholded absolute order:** the already frozen significance-thresholded
  relative metric; no low-power ratio may override source-normalized physical
  error.
- **Total power:** relative error and Pearson correlation for
  `POSTNP_TOTAL_POWER_V2 / P_scale`.
- **Scale:** predicted non-oracle `P_scale`; oracle scale is forbidden.

## CURRENT V1 GATE TABLE

The frozen primary contract is `PW_K6_STRUCTURED_FORWARD_MODEL_V1`, M5
width=32, 2,684 parameters. The values below are taken from the existing
width-32 capacity-curve summary; no retraining was performed.

| Metric | Value | Limit | Status |
|---|---:|---:|---|
| State relative RMSE median* | 0.80160452 | 0.50 | FAIL |
| State relative RMSE q95* | 0.98856517 | 0.80 | FAIL |
| Routing eta RMSE median | not persisted | 0.05 | UNVERIFIED |
| Routing eta RMSE q95 | not persisted | 0.10 | UNVERIFIED |
| Routing Pearson | not persisted for exact width=32 | 0.95 | UNVERIFIED |
| Absolute-order source-normalized RMSE median | not persisted | 0.05 | UNVERIFIED |
| Absolute-order source-normalized RMSE q95 | not persisted | 0.10 | UNVERIFIED |
| Thresholded absolute-order relative median | 0.90152472 | 0.30 | FAIL |
| Thresholded absolute-order relative q95 | 0.99908094 | 0.75 | FAIL |
| Total-power relative median | 0.50161599 | 0.15 | FAIL |
| Total-power relative q95 | 0.66745220 | 0.30 | FAIL |
| Total-power Pearson | not persisted | 0.95 | UNVERIFIED |
| Fixed width=32 seed state-median standard deviation | not persisted | 0.03 | UNVERIFIED |

`*` The saved benchmark field is `state_relative`, a normalized L2-relative
summary. The exact Chart RMSE arrays were not persisted. It is reported as the
closest saved state diagnostic and is not silently redefined as a newly
computed RMSE.

The saved diagnostic routing relative values were median `0.86160115`, q95
`3.75075908`, and Pearson `0.80078315`; they are not substituted for the
Chart-defined eta RMSE gate.

The existing analysis JSON contains aggregate summaries only. It contains no
per-sample frozen prediction snapshot from which the missing exact RMSE and
Pearson metrics can be recomputed. No new model execution was used to fill
that gap.

## RETROSPECTIVE H1 STATUS

`RETROSPECTIVE_H1_GATE_FAIL`

The classification is forced by the explicit known failures in state,
thresholded absolute-order, and total-power gates. The unverified exact
metrics are a reproducibility gap, not a pass. Therefore:

- `RESEARCH_USEFUL`: retained.
- `H1_CAPACITY_SUPPORTED`: retained as a diagnostic statement.
- `H1 production`: not admitted.

## PROSPECTIVE VALIDATION CONTRACT

Future production admission requires exactly six previously unseen K6
geometries. Each must be declared before solver entry as
`PROSPECTIVE_VALIDATION`.

Required order:

```text
geometry identity/hash freeze
  -> frozen V1 prediction persist
  -> prediction hash freeze
  -> only then reveal/generate HF truth
```

Before the prospective record is frozen, the geometry may not be used for
architecture changes, hyperparameter selection, PCA refitting, preprocessing
redesign, model refitting, or NP-prior tuning.

## PROSPECTIVE NUMERIC GATES

The pooled six-geometry prospective set must satisfy every retrospective Chart
gate. In addition, every individual geometry must satisfy all of these
catastrophic hard limits:

| Individual metric | Limit |
|---|---:|
| State relative RMSE | <= 1.00 |
| Routing eta RMSE | <= 0.15 |
| Absolute-order source-normalized RMSE | <= 0.15 |
| Total-power median relative error | <= 0.40 |

Any single catastrophic failure means `PROSPECTIVE_H1_FAIL`; aggregation may
not hide it.

## PRODUCTION H1 ADMISSION LOGIC

- `RESEARCH_USEFUL`: useful predictive structure, formal H1 gates not passed.
- `RETROSPECTIVE_H1_GATE_PASS`: all retrospective numerical gates pass.
- `PROSPECTIVE_H1_GATE_PASS`: pooled prospective gates and every individual
  catastrophic gate pass.
- `PRODUCTION_H1_PASS` requires both of the previous two pass states.

Current result:

`PRODUCTION_H1_PASS = false`

No exception is available for a favorable subset of metrics.

## ACTIVE LEARNING STATUS

`DISABLED`

Even a future `PRODUCTION_H1_PASS` would not automatically start Active
Learning. AL additionally requires a separately validated uncertainty and
acquisition-semantics contract. AL is not executed here.

## NEXT ROUTE

Because V1 fails the retrospective H1 gate, the only authorized next route is:

`RECOVER_FROZEN_NP_PROVIDER_AND_RUN_MATCHED_PRIOR_ABLATION`

This route is registered only and was **not executed**. NP remains
`NP_PROVIDER_ARTIFACT_MISSING`.

The future ablation must compare:

- A: frozen V1 geometry-only model.
- B: the same frozen model plus exact historical frozen NP-prior features.

Geometry membership, target representation, P_scale target, decoder,
optimizer, seeds, metrics, and validation discipline must remain matched.

## ARTIFACT HASHES

| Artifact | SHA256 |
|---|---|
| Dataset freeze manifest | `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c` |
| Source provenance | `e32d72cd0898d17dad0f0fb7cf2879e514139cafe1d2b5328f1fbbe229f20d5d` |
| V2 truth | `4f894932b14be549a5483f3a3731a1e71869759357d4eddeb7ba4dc0d5108408` |
| State code | `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15` |
| Launcher code | `48d3c332fde679a9d8dc991a5ba8cd75aecdcb54750d7ec1774f732203ef08be` |
| Geometry authority | `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f` |
| Capacity analysis JSON | `dfb65f4b70567ffbf3f33036a605b9ace3ebfb405551d79c8b59f088e694b41e` |
| Structured freeze report | `8a4680008870ba4cba0f2ca22e59cee93f6d31a375c7d81087d2dfa6edda4228` |

Machine-readable authority:

`reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json`

## GIT

- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `eefda35d53eb6953fb5819da25b659dbfc4fd4df`
- Existing dirty/untracked worktree content preserved.
- No commit and no push performed.

## NEXT

Do not execute the NP-prior route in this task. Preserve this gate authority,
the machine-readable JSON, and the retrospective FAIL decision for Chart
review.

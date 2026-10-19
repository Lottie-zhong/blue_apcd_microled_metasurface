# PW_K6_GRATING_TRUTH_INTERPRETATION_V2_AND_H1_H2_RETEST_V1

## STATUS

`PASS_WITH_REVIEW`

This zero-solver task completed the interpretation correction, immutable
derived truth view, three-way closure, H2 retest, and minimal geometry-grouped
H1 retest. No FDTD solver was launched, no case was replayed, no scientific
attempt was created, and no frozen FSP/H5/raw truth or historical C_PW/grating
field was overwritten.

The scientific conclusion is deliberately split:

- the previous absolute-power conflict was a truth-definition/legacy-grating
  interpretation problem;
- the corrected factor representation is physically well-defined but is not
  yet learnable enough under the prescribed 20-geometry LOGO test.

## LEGACY GRATING SEMANTICS

The saved fields were classified from executed launcher/API code and stored
metadata, not from variable names alone.

| saved field | classification | exact meaning |
|---|---|---|
| raw E/H | physical field evidence | `0.5 Re(Ex conj(Hy)-Ey conj(Hx))` integrated over the monitor plane; after unit-cell-area and incident-flux normalization it is the independent POSTNP total-flux authority |
| original `C_PW` | modal coefficient state | complex Floquet coefficients; power is obtained only through the frozen deterministic modal decoder |
| `power_fraction_of_monitor_total` | C: monitor-total-normalized order fraction | order fraction returned by the grating analysis, with the saved propagating-order sum equal to one |
| `power_fraction_of_source` | E: legacy derived quantity | `abs(total_power) * power_fraction_of_monitor_total`; it is source-normalized only under the launcher `total_power` convention and is not absolute multi-order truth |
| `T_FDTD` | D: zero-order/spatial-average estimator | computed after periodic-monitor E/H spatial averaging, therefore primarily the spatial-average / `(0,0)` field-amplitude transmission estimator |
| `R_FDTD` | E: legacy derived quantity | source-normalized reflection scalar from the same launcher average-field convention |
| `R/T/A` | E: legacy projection quantities | internally closed quantities under the launcher convention; they are not independent proof that `T_FDTD` is total all-order transmitted flux |

The launcher sequence is:

1. average the periodic monitor fields over x/y;
2. form forward/backward amplitudes from the averaged fields;
3. compute `T_FDTD` from the averaged forward amplitude;
4. multiply grating monitor-total fractions by that scalar.

The saved metadata confirms the exact consequence: for representative S02,
S16, and EXT08 samples, `sum(power_fraction_of_monitor_total)=1` to floating
point precision, while `sum(power_fraction_of_source)=T_FDTD`.

## V2 TRUTH DEFINITION

The new immutable derived view is:

`reports/coupling/PW_K6_GRATING_TRUTH_V2.json`

Schema: `PW_K6_GRATING_TRUTH_V2`; 20 geometries × 21 wavelengths × 7
propagating orders = 2,940 order rows.

The definitions are:

```text
POSTNP_TOTAL_POWER_V2
  = P_EH_native / (A_cell * P_inc_per_area)

GRATING_ETA_V2[m]
  = power_fraction_of_monitor_total[m]

GRATING_ABSOLUTE_ORDER_POWER_V2[m]
  = POSTNP_TOTAL_POWER_V2 * GRATING_ETA_V2[m]
```

`A_cell = 1740 nm × 290 nm = 5.046e-13 m²`. This is a dimensional unit-cell
area conversion, not a fitted normalization constant.

The V2 view preserves references to all legacy fields and source hashes. It
does not duplicate or rewrite raw FDTD truth. `T_FDTD` and
`power_fraction_of_source` remain available but are explicitly marked:

`LEGACY_GRATING_SOURCE_POWER_SEMANTICS = NOT_ABSOLUTE_MULTIORDER_TRUTH`

## PRENP / POSTNP ROLE CHECK

The interpretation was not transferred blindly between planes.

| plane | effective saved basis / medium evidence | total-flux authority | eta authority | absolute-order authority |
|---|---|---|---|---|
| IN | saved Floquet basis; effective complex `n≈2.41537+0.08435i`; incident-side lossy medium | same-plane raw E/H only; no POSTNP air-side transfer promoted | only where a matching grating basis exists | not promoted |
| PRENP | saved Floquet basis; effective `n≈1.42619+0i` | same-plane raw E/H only; no cross-medium transfer assumed | only where a matching grating basis exists | not promoted |
| POSTNP | air-side saved Floquet basis; effective `n=1+0i` | `POSTNP_TOTAL_POWER_V2` from raw E/H | `GRATING_ETA_V2` | `GRATING_ABSOLUTE_ORDER_POWER_V2` |

The V2 absolute-order authority is therefore POSTNP-only in this task.

## EH–CPW–GRATING V2 CLOSURE

All metrics below use the frozen 20G dataset and no solver output generated in
this task.

### Total power

| comparison | correlation | median relative error | RMSE |
|---|---:|---:|---:|
| E/H normalized total vs C_PW total | 0.9999999956 | 1.06151e-4 | 4.79328e-5 |
| E/H normalized total vs V2 total | 1.0000000000 | 0 | 0 |
| C_PW total vs V2 total | 0.9999999956 | 1.06151e-4 | 4.79328e-5 |

### Order power and routing

For 2,940 order rows, with meaningful-order threshold
`0.00098856568`:

- V2 absolute order vs C_PW modal order correlation: `0.9999999557`;
- meaningful-order median relative error: `3.81502e-4`;
- q95 relative error: `1.54871e-3`;
- maximum meaningful relative error: `1.99190e-3`;
- order-power RMSE: `2.74266e-5`;
- V2 eta vs C_PW eta correlation: `0.9999999389`;
- eta median relative error: `3.97963e-4`;
- eta q95 relative error: `1.48531e-3`.

The worst meaningful V2-vs-C_PW order error is still only `0.00199190` in
relative terms. The legacy C_PW-vs-legacy-grating comparison remains the
previous mismatch: correlation `0.81534495`, median ratio `2.19805`, q95
`6.11102`.

This closes the three-way interpretation: raw E/H total, C_PW modal total,
and V2 absolute grating order power are mutually consistent. The old conflict
was produced by using the legacy `T_FDTD` scalar as the absolute multi-order
scale.

## LEGACY FIELD DEPRECATION

No legacy field was deleted or modified. Future training/validation must fail
closed if it requests `power_fraction_of_source` or `T_FDTD` as absolute
multi-order truth without an explicit legacy override. The V2 view is the only
absolute order-power authority created by this task.

## H2 RELATIVE ROUTING

`H2_RELATIVE_ROUTING = SUPPORTED`

The saved grating eta and C_PW modal eta agree over all 2,940 rows with
correlation `0.9999999389` and median relative error `3.97963e-4`.

## H2 ABSOLUTE POWER

`H2_TOTAL_POWER = SUPPORTED`

Independent raw E/H and C_PW total power agree with correlation
`0.9999999956` and median relative error approximately `1.06e-4`.

`H2_ABSOLUTE_ORDER_POWER = SUPPORTED`

After replacing the legacy grating scale with `POSTNP_TOTAL_POWER_V2`, the
V2 order powers agree with C_PW modal order powers at median relative error
`3.81502e-4`, q95 `1.54871e-3`, and maximum `1.99190e-3` above the meaningful
threshold.

## H2 SPECTRAL ROUTING

`H2_SPECTRAL_ROUTING = SUPPORTED`

The result holds across the complete 440--460 nm wavelength contract and all
20 geometry groups, not only a selected wavelength. The independent spectral
routing evidence therefore supports:

`UPDATED H2 = H2_SUPPORTED`

This conclusion concerns physical truth reconciliation. It does not imply ML
learnability or Active Learning readiness.

## C_PW_FACTOR_V1

The derived candidate representation is:

```text
C_PW_FACTOR_V1 = {
    C_hat  = C_PW_original / sqrt(P_CPW_modal_total),
    P_scale = POSTNP_TOTAL_POWER_V2
}
```

`C_PW_original` remains preserved. No arbitrary fitted normalization constant
was introduced. `P_scale` is physically validated and constrained to be
nonnegative when used as a model output in the H1 diagnostic.

## H1 RETEST

The retest used only geometry + wavelength features:

- six ordered geometry dimensions `ordered_D_nm` plus wavelength;
- 20 geometry groups;
- leave-one-geometry-out, with all wavelengths of the held-out geometry kept
  together;
- Ridge and one shallow MLP `(32,32)`, no architecture search;
- 420 samples, zero solver invocations.

Interpretation of the four variants:

- H1-A predicts original C_PW;
- H1-B predicts C_hat and uses true P_scale only to isolate state/routing
  representation quality;
- H1-C predicts P_scale only; its absolute-order diagnostic uses true routing
  as an oracle and is not end-to-end;
- H1-D predicts both C_hat and P_scale and is the end-to-end factor test.

### Ridge summary

| variant | normalized-state median relative RMSE | phase median | scale median relative error | absolute-order median relative error | routing median relative error |
|---|---:|---:|---:|---:|---:|
| H1-A | 0.8866 | 74.18° | — | 0.9001 | 0.8264 |
| H1-B | 0.8415 | 78.44° | oracle | 0.9163 | 0.8449 |
| H1-C | — | — | 0.4953 | 0.4798* | oracle |
| H1-D | 0.8415 | 78.44° | 0.4953 | 0.9222 | 0.8449 |

`*` H1-C absolute-order value uses oracle routing and is scale-only evidence.

### Shallow MLP summary

| variant | normalized-state median relative RMSE | phase median | scale median relative error | absolute-order median relative error | routing median relative error |
|---|---:|---:|---:|---:|---:|
| H1-A | 1.1559 | 70.06° | — | 0.7915 | 0.7826 |
| H1-B | 1.1709 | 74.75° | oracle | 0.8262 | 0.8390 |
| H1-C | — | — | 0.2376 | 0.2333* | oracle |
| H1-D | 1.1709 | 74.75° | 0.2376 | 0.8409 | 0.8431 |

The MLP scale-only result is better than Ridge (`corr=0.8601`, median scale
relative error `0.2376`) but does not rescue the complete factor model. The
end-to-end H1-D routing correlation is only `0.7818` for Ridge and `0.4744`
for the MLP; meaningful absolute-order median relative errors remain
`0.9222` and `0.8409`, respectively.

Per-geometry behavior is unstable. For Ridge H1-D, the largest state errors
occur at EXT06, EXT08, and EXT09. For the MLP, S15, EXT02, EXT12, and EXT08
are particularly unstable; EXT08 reaches an absolute-order relative error of
approximately `10.49` in the per-geometry diagnostic.

Therefore:

`UPDATED H1 = H1_NOT_SUPPORTED_AFTER_TRUTH_FIX`

The truth-definition problem is closed, but the representation/model/data
problem remains. The factor representation is physically meaningful, yet the
current geometry + wavelength inputs do not provide usable geometry-grouped
learnability for the requested minimal models.

## NP PROVIDER RECOVERY

Historical search of the expected NP project authority and provider patterns
did not recover the exact frozen forward-provider artifact.

`NP_PROVIDER_ARTIFACT_MISSING`

No NP rebuild was attempted. No compatibility check was run. The H1 result is
therefore a no-NP result, as required.

## NP PRIOR EFFECT

Not available. Since the exact frozen NP provider was not recovered, the
optional matched NP-prior ablation was not executed. Unsupported wavelength
extrapolation was not used.

## ACTIVE LEARNING READINESS

`ACTIVE_LEARNING_NOT_READY`

H2 truth semantics are now physically closed, but H1 does not demonstrate
usable geometry-grouped learnability. Active Learning remains blocked; no AL,
new geometry, variable MDC, K4, or K9 was started.

## PROVENANCE AND IMMUTABILITY

The derived artifacts are:

- `reports/coupling/PW_K6_GRATING_TRUTH_V2.json`;
- `reports/coupling/PW_K6_GRATING_TRUTH_INTERPRETATION_V2_AND_H1_H2_RETEST_V1_ANALYSIS.json`.

The audit records `solver_invocations=0`, `gpu_used=false`, and
`frozen_truth_unchanged=true`.

Primary source hashes:

- freeze manifest: `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c`;
- source provenance manifest: `e32d72cd0898d17dad0f0fb7cf2879e514139cafe1d2b5328f1fbbe229f20d5d`;
- C_PW state code: `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15`;
- launcher code: `48d3c332fde679a9d8dc991a5ba8cd75aecdcb54750d7ec1774f732203ef08be`.

## GIT

- branch: `work/mdc-np-coupling-ml-v1`;
- HEAD before/after: `eefda35d53eb6953fb5819da25b659dbfc4fd4df`;
- upstream: none, so ahead/behind is unavailable;
- worktree: dirty with pre-existing modifications/untracked artifacts plus
  the new derived V2 JSON, H1/H2 analysis JSON, and this report;
- no commit, reset, checkout, clean, or push was performed.

## NEXT

Chart review of the V2 truth authority and H1 failure boundary. Do not start
solver, replay, NP rebuild, Active Learning, or new geometry before review.

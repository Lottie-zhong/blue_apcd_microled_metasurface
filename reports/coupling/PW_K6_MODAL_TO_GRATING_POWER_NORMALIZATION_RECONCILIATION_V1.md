# PW_K6_MODAL_TO_GRATING_POWER_NORMALIZATION_RECONCILIATION_V1

## STATUS

`PASS_WITH_REVIEW` for the zero-solver reconciliation audit. No scientific
solver was launched, no attempt was created or replayed, and frozen FSP/H5/raw
truth was not modified. Production admission is unchanged.

Primary normalization verdict:

`B. GRATING_NORMALIZATION_CONVENTION_DIFFERENCE`

The saved C_PW modal power is independently validated by raw E/H flux. The
remaining absolute mismatch is between that physical modal flux and the saved
grating-order source-scaled values.

## DATA AND SCOPE

The audit used the frozen PW_K6 20G scientific-valid dataset only:

- 20 geometries: `K6V1_S02-S05`, `K6V1_S15-S16`, and `K6V1_EXT01-EXT14`;
- 21 wavelengths, 440--460 nm;
- saved `IN`, `PRENP`, and `POSTNP` raw complex fields;
- saved C_PW state/projection data;
- saved grating-order JSON and saved R/T/A projection values.

`solver_invocations=0`, `gpu_used=false`, and
`frozen_truth_unchanged=true` in the derived audit manifest.

## POWER DEFINITIONS

The three quantities were kept separate.

1. Raw E/H plane flux:

   `P_EH_native = integral 0.5 Re(Ex conj(Hy) - Ey conj(Hx)) dx dy`.

   The integration uses actual x/y coordinates and trapezoidal weights. This
   is an integrated monitor quantity and is not directly comparable to an
   area-normalized modal coefficient.

2. Area- and source-normalized E/H power:

   `P_EH_norm = P_EH_native / (A_cell * P_inc_per_area)`.

   `A_cell = 1740 nm * 290 nm = 5.046e-13 m^2`. This is the physical unit-cell
   area bridge, not a fitted correction factor.

3. C_PW modal power:

   `P_CPW = sum_{propagating orders, TE/TM} |Re(P_z_per_abs_e2)| |C_PW|^2`.

   The sum is over the canonical propagating +z orders and uses the frozen
   incident-normalized C_PW state.

4. Saved grating-order power:

   `P_GRATING_ORDER = power_fraction_of_source` from the frozen launcher
   output. The saved total is the sum of these rows. Its routing fractions are
   separately represented by `power_fraction_of_monitor_total`.

## RAW E/H POYNTING RESULT

Across 420 POSTNP samples, after the unit-cell-area bridge:

| comparison | median absolute error | median relative error | weighted relative error | correlation |
|---|---:|---:|---:|---:|
| `P_EH_norm` vs `P_CPW` | 3.12805e-05 | 1.06140e-04 | 1.12838e-04 | 0.9999999956 |

The `P_EH_norm/P_CPW` ratio has median `0.9998983`, q05 `0.9998185`, q95
`1.0000217`, and range `0.9996282--1.0012995`.

Before division by `A_cell`, the E/H-to-C_PW ratio was approximately
`5.046e-13`, exactly the unit-cell area. This identifies the dimensional
bridge and rules out that factor as a modal-physics error.

## CPW TOTAL POWER RESULT

The C_PW total is finite and stable across the dataset. It agrees with the
independent E/H flux at the `1e-4` relative scale. Therefore the frozen C_PW
modal power formula is not the source of the large grating discrepancy.

Representative sample (`K6V1_EXT14`, 450 nm):

- `P_EH_norm = 0.81077005`;
- `P_CPW = 0.81083125`;
- saved grating total = `0.57555731`.

## GRATING TOTAL POWER RESULT

Across 420 POSTNP samples, C_PW versus saved grating total gives:

- meaningful threshold: `0.0338846583`;
- meaningful samples: `378/420`;
- median absolute error: `0.14174452`;
- median relative error on meaningful samples: `1.10671186`;
- weighted relative error: `1.04931999`;
- correlation: `0.81534495`;
- `P_CPW/P_GRATING` median: `2.19804917`;
- q95: `6.11101949`;
- maximum: `127.63964`.

The corresponding E/H versus grating statistics are effectively identical:
correlation `0.81538027`, meaningful weighted relative error `1.04911332`,
ratio median `2.19782257`, q95 `6.10994211`.

## THREE-WAY CLOSURE

The three-way result is:

`P_EH_norm ~= P_CPW != saved P_GRATING_total`.

This is not an ambiguity between two independent modal decoders. Raw E/H and
C_PW agree, while both disagree with the grating absolute scale. The result
is therefore a grating-total convention problem, not a C_PW modal-power
formula failure.

## ORDER-BY-ORDER CLOSURE

For 2,940 saved order rows:

- absolute C_PW-order versus grating-order correlation: `0.94740562`;
- meaningful absolute ratio median: `2.20180806`;
- q95: `5.57312170`;
- normalized routing-fraction (`eta`) correlation: `0.99999994`;
- normalized eta relative error median: `3.97963e-04`;
- eta ratio median: `1.00019881`;
- eta ratio range: `0.9972663--1.0023934`.

Thus the order allocation is essentially preserved, while the common absolute
scale is wrong. This is the expected signature of a total-power normalization
problem.

The saved-order metadata provides a direct check. For representative S02,
S16, and EXT08 wavelengths, the seven returned propagating rows satisfy:

- `sum(power_fraction_of_monitor_total) = 1.0` to floating-point precision;
- `sum(power_fraction_of_source) = saved T_FDTD`.

Examples include S02 at 440 nm: `1.0` and `0.04732573345`; S16 at 460 nm:
`1.0` and `0.13302625690`; and EXT08 at 450 nm: `1.0` and `0.00418012440`.

## LOW-POWER OUTLIER ANALYSIS

The extreme ratios are amplified by a small saved grating denominator, but
this is not the dominant explanation. The largest example is:

`K6V1_EXT08 @ 452 nm`: `P_EH_norm=0.53345552`, `P_CPW=0.53354959`,
saved grating total `0.00418012`, ratio `127.6396`.

The next high ratios are EXT08 at 451--454 nm and EXT10 at 458--460 nm. They
are denominator-amplified outliers. However, after excluding the bottom 10%
of grating totals, the C_PW/grating ratio is still median `2.10671186` and
q95 `4.82768623`. Therefore `E. LOW_POWER_RATIO_ARTIFACT_DOMINANT` is
rejected.

## REFERENCE-PLANE AUDIT

The saved raw sample/reference planes are approximately:

- IN: sample `-100.787739 nm`, reference `-50 nm`;
- PRENP: sample `1152 nm`, reference `1202 nm`;
- POSTNP: sample `1802 nm`, reference `1722 nm`.

For PRENP and POSTNP propagating modes, the de-embedding multiplier magnitude
is one and the reference/sample modal-power ratio is one. These homogeneous
regions are phase-only for the propagating modes.

At IN, the multiplier magnitude median is `0.2358773` (maximum `0.9419406`)
and the modal-power ratio median is `0.0556381`. This is consistent with the
complex-kz/passive branch in the lossy GaN-side medium. It is a physical
amplitude change under the frozen de-embedding contract, not the cause of the
POSTNP C_PW/grating mismatch.

## ENERGY TRIANGULATION

The saved R/T/A closure is zero to floating-point precision for all 420
samples: `abs(1-R-T-A)=0` throughout the stored projection rows.

Correlations are:

- E/H versus C_PW: `0.9999999956`;
- E/H versus grating: `0.81538027`;
- C_PW versus grating: `0.81534495`.

The exact R/T/A closure validates internal arithmetic closure of the saved
projection convention; it does not establish that the averaged-field
`T_FDTD` scalar is the total power carried by all propagating grating orders.

## ROOT NORMALIZATION CAUSE

The source audit identifies the mechanism in the frozen launcher:

1. `_mode_amplitudes` first averages E/H over the periodic monitor x/y plane.
   For a periodic field, this selects the spatially averaged, effectively
   `(0,0)` Fourier component rather than summing power in all propagating
   orders.
2. `T_FDTD` is then computed from that averaged forward amplitude.
3. `_orders` obtains `power_fraction_of_monitor_total` from the grating
   analysis and multiplies it by `total_power=t_fdtd` to create
   `power_fraction_of_source`.
4. Consequently, the saved source-scaled order rows sum to `T_FDTD`, while
   their eta distribution sums to one.

The stored metadata confirms exactly this relationship. The physical total
power represented by raw E/H and C_PW is not the same scalar as the saved
averaged-field T convention. The primary verdict is therefore
`B. GRATING_NORMALIZATION_CONVENTION_DIFFERENCE`; the averaged-field source
normalization is the mechanism. No evidence supports `A. CPW_MODAL_POWER_FORMULA_ERROR`
or `C. REFERENCE_PLANE_NORMALIZATION_ERROR` as the primary cause.

## PHYSICAL BRIDGE

The defensible bridge is:

`raw integrated E/H power`
` -> divide by unit-cell area`
` -> normalize by incident flux density`
` = physical source-normalized flux`
` ~= sum of propagating C_PW modal powers`.

For order-resolved data, keep two fields distinct:

- `eta_order`: routing fraction normalized by the grating monitor total;
- `T_total`: an independently valid total transmitted flux.

Then use `P_order = eta_order * T_total`. The currently saved
`power_fraction_of_source` should not be treated as that absolute physical
order power until its scalar total is corrected or reinterpreted.

## RECONCILED REPRESENTATION

Candidate, not yet production-admitted:

`PW_K6_POWER_RECONCILED_V1`

- preserve historical C_PW and all frozen raw truth unchanged;
- use `P_CPW` as the modal physical-power coordinate;
- carry the E/H area/source normalization as an independent audit channel;
- store order `eta` separately from the total-power scalar;
- do not overwrite the historical grating rows;
- record the grating total-convention provenance explicitly.

This is a representation definition for review, not an executed decoder fix
and not an ML admission.

## UPDATED H2

H2 is supported for the modal-to-grating discrepancy: the large absolute
disagreement is explained by a frozen grating total-power convention, with
low-power denominator amplification as a secondary outlier effect.

H2 does not yet establish that any ML learnability or production fidelity
gate passes. It also does not authorize changing the frozen comparator or
reprocessing the scientific truth.

## MINIMAL H1 RETEST

Not executed. The minimum matched-LOGO H1 retest must wait until the grating
truth interpretation is reviewed and a reconciled representation is formally
accepted. No solver action, replay, new geometry, broad sweep, or ML training
was performed in this task.

## NP PROVIDER ARTIFACT STATUS

`NP_PROVIDER_ARTIFACT_MISSING` remains the status. The expected NP provider
library at
`D:\project\blue_apcd_np_k6_mdc_v1\outputs\np_k6_p1d2_broadband_library_27point_v1\library_long.csv`
was not available. No NP data was used and this absence did not block the
E/H--C_PW--grating normalization reconciliation.

## NEXT SCIENTIFIC ROUTE

Recommended route, not executed:

`C. FIX_GRATING_TRUTH_INTERPRETATION`

Perform a zero-solver/chart-reviewed correction or explicit reinterpretation
of the grating total convention, retaining `eta_order` and an independently
validated `T_total`. Only after that review should the reconciled representation
be considered for the minimal H1 retest. Do not execute this route as part of
the current audit.

## PROVENANCE

Derived analysis companion:

`reports/coupling/PW_K6_MODAL_TO_GRATING_POWER_NORMALIZATION_RECONCILIATION_ANALYSIS_V1.json`

Frozen/source hashes used by the audit:

- dataset freeze manifest: `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c`;
- C_PW state code: `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15`;
- scientific launcher: `48d3c332fde679a9d8dc991a5ba8cd75aecdcb54750d7ec1774f732203ef08be`.

The audit analysis records `solver_invocations=0` and `frozen_truth_unchanged=true`.

## GIT

The report and its derived JSON are uncommitted audit artifacts on branch
`work/mdc-np-coupling-ml-v1`. Existing dirty/untracked worktree content was
preserved. No reset, clean, checkout, commit, or push was performed.

## NEXT

Chart review of `C. FIX_GRATING_TRUTH_INTERPRETATION`; no solver action.

# Paper A CP current Native-M1 broadband revalidation

## Status

- Stage: `PAPER_A_CP_CURRENT_NATIVE_BROADBAND_REVALIDATION_V1`
- Candidate: `BW2_J1J2_D194_T90_PSI99_H525`
- Native-M1 FDTD cases: center-X and center-Y, 2/2 entered and completed; no additional solver.
- CP convention: `R=(Ex-iEy)/sqrt(2)`, `L=(Ex+iEy)/sqrt(2)`; metrics below use incoherent x/y power combination.

## 20 deg incoherent broadband result

- 420-480 nm: all L_fraction > 0.5 = `True`; handedness transitions = `0`; minimum L_fraction = `0.705890` at `479.616 nm`; longest continuous L-dominant span = `{'start_nm': 420.1680672268908, 'end_nm': 479.6163069544365, 'bandwidth_nm': 59.44823972754568, 'points': 60}`.
- Useful target-L power: mean `4.34479e-11` arb., worst `2.86598e-11` arb.; total cone power mean `5.70203e-11` arb., worst `4.0601e-11` arb.
- 450 nm anchor (nearest native point `450.450 nm`): L_fraction `0.751410`, DoCP(R-L) `-0.502820`.
- 400-500 nm exploratory: all L_fraction > 0.5 = `True`; handedness transitions = `0`; minimum L_fraction = `0.671242` at `500.000 nm`.

## MDC source-weighted result

- Weight source: frozen MDC `ZL-1 alternative` `r12_normalized_output` from `D:\project\worktrees\blue_apcd_mdc_defect_450\outputs\mdc_device_closure_figures_v1\spectral_profiles_420_480_plot_data.csv`; relative shape only, normalized over actual 420-480 nm common coverage, with no extrapolation outside that evidence. Effective center `448.151757 nm`, sigma `25.908382 nm`, native CP points used `101`. Frozen MDC FDTD peak `447.8 nm`, output FWHM `18.782087 nm`.
- 20 deg weighted L_fraction `0.759664`, weighted DoCP(R-L) `-0.519328`, weighted useful L power `4.39934e-11` arb., weighted total cone power `5.79117e-11` arb.; diagnostic weighted mean L_fraction `0.756577`.

## Verdict

`CP_NATIVE_M1_BROADBAND_L_PRESERVED`

Current Native-M1 preserves the tested legacy broadband L-selective CP behavior over the formal 420-480 nm window. This closeout is current Native-M1 evidence only; it does not run or admit angular, position, MDC-integrated, RCLED, fabrication, or other Paper A physics stages.

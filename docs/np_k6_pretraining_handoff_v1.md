# NP K6 pretraining handoff and MDC interface pending decisions v1

## Status

`NP_K6_PRETRAINING_HANDOFF_COMPLETE_MDC_INTERFACE_DECISION_PENDING`

This is a frozen handoff. No solver, LumAPI engine, new FSP, model training, active-learning acquisition, or sealed-test access was performed in this phase.

## Gate-0A closure

The only consumed Gate-0A case is `RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE0A`, attempt_001, with `entered/engine/controller/post-save/run = 1/1/1/1/1`. It remains diagnostic-only. The 5 nm candidate is rejected for `HARD_GATE_RUN3C_N2_NOT_STRICTLY_NESTED` and `N2_NATIVE_M1_CLOSURE_GATE_FAILED`; full-band maximum closure residual is 0.0812666. This does not reject the K6 steering physics, RUN3A/B/C functional evidence, or Native-M1 material validity.

## Database and training policy

The active authority remains the 27-point D100-D230, 5 nm database: 296010 geometries and 3256110 LF geometry-wavelength rows over 445-455 nm. The 26-point contract remains historical and isolated. The 120 HF task rows remain unentered, unauthorized, and unlabeled. LF/DFT data are for DOE and candidate selection only; formal HF labels must come from FDTD. RCWA labels, diagnostic-only N1/N2 data, constant-epsilon controls, and historical sparse FDTD are not formal training labels.

## Deferred numerical forensics

Sourcepower normalization, outer-z nesting, N2 replay, N3, material-only runs, conformal variants, and additional mesh/monitor controls are recorded as deferred. They are not automatically resumed and require explicit user authorization.

## MDC interface

Coupling level, integration stack, wavelength range, angular range, polarization/source basis, output tensor, and formal-label compatibility remain pending MDC decisions. Shared conventions are pending cross-branch freeze. See `mdc_np_interface_pending_decisions_v1.json`.

## Training start gate

All G1-G10 gates are `PENDING`; `NP_K6_MAINLINE_TRAINING_AUTHORIZED=false`. Production mesh remains unfrozen and formal HF label count is zero.

## Next action

`WAIT_FOR_MDC_INTERFACE_DECISION`

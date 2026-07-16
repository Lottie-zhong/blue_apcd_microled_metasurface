# MDC-ML F0 smoke v1

This report records the Native-M1 TMM baseline reproduction and deterministic
17-structure end-to-end smoke. Numerical results are reported from the generated
machine-readable files in `outputs/mdc_ml_f0_smoke_v1/`; no FDTD or model training
is part of this task.

## Frozen contracts reused

- Native-M1 material loading: `scripts/apcd_native_materials.py`.
- Complex-incident power and conserved-real-kx TMM:
  `scripts/mdc_tmm_complex_incident_power_v1.py`.
- Spectral FWHM: `stage_mdc_native_m1_topology_coarse_scan.fwhm`.
- Angular FWHM: `audit_mdc_gan_native_m1_tmm_angle_convention_v1.fwhm`.
- Symmetric peak-set semantics:
  `audit_mdc_gan_native_m1_tmm_angle_convention_v1._postprocess_metrics`.
- Grammar, canonical identity, simulation provenance and schema validation:
  the frozen MDC-ML spec-v1 modules.

The runner calls the existing TMM functions directly. It does not contain a
second transfer-matrix solver. In particular, `A_stack = power_entering - T`;
`1 - R - T` is stored only as `far_field_balance_offset`.

## Outputs and interpretation

`baseline_recompute_v1.json` is the stop/go gate. The remaining sixteen
structures are evaluated only after this gate passes. `validation_v1.json`
contains schema, hash, artifact, finite-value, uniqueness, topology and
deterministic-rerun results. `runtime_summary_v1.json` contains measured smoke
timings and linear serial estimates only; it is not evidence from a 2,000- or
5,000-structure run.

All cone quantities are in-plane TMM transmission proxies. They are not device
extraction efficiency, dipole output power, or APCD device throughput.

## Executed result (2026-07-15)

- Frozen Alternative gate: PASS. Recomputed spectral FWHM
  `3.2999999999999545 nm`, angular FWHM `14.996580473442913 deg`, peak set
  `[0.0]`, ratio `45.66660483135923`, canonical hash `b30dff...8ed0`, and
  physical-configuration hash `8a2672...0d37`.
- APCD-ready Alternative unpolarized proxies: cone5 integral
  `0.10718319221988529`, cone10 integral `0.18568740184058813`, cone5 fraction
  `0.45356109240238607`, cone10 fraction `0.7857629454756327`, and normal
  448--453 nm band transmission `0.6313084408788102`.
- Full smoke: 17 structures, exactly two non-baseline structures per each of
  eight topology families, 17 unique canonical hashes, Level B count zero, and
  tolerance-child count zero.
- Generated validation: PASS for all 17 schema records, artifact SHA checks,
  NaN/Inf audit, duplicate audit, topology coverage, power naming, deterministic
  sample rebuild, and two-pass metric/artifact rebuild. Deterministic content
  signature: `e2a51efb5b642049eff545718c8f519fd8378c6b672f56795c78ed8bab2a1026`.
- Output size: `4,055,972 bytes`, including `3,797,789 bytes` of NPZ arrays.
- Measured second-pass runtime: baseline `1.4633 s`, 17-structure total
  `27.5670 s`, mean `1.5663 s`, and P95 `1.8178 s` per structure.

## Frozen-test inconsistency

The combined relevant pytest run produced 42 passes and 2 failures. Both
failures are the same pre-existing HEAD assertion in
`tests/test_mdc_ml_inverse_design_spec_v1.py`: the frozen audit still requires
HEAD `40dedf4098fa0ca19e0e5f0e3395e73fb4949c53`, while this task explicitly
requires HEAD `ba361fa39a5c04cccbaa55ad1d89b328c5a8d91b`. The frozen audit and tests
were not modified. This inconsistency does not affect the generated smoke
validation, but it remains a repository test blocker.

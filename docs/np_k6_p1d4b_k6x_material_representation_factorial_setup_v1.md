# NP K6-x 2x2 material representation setup-only factorial

Status: READY_FOR_RUN3C_N1_MATERIAL_REPRESENTATION_TIO2_CONSTANT_ONLY_DIAGNOSTIC_AUTHORIZATION

No solver was run for either new mixed-material control. The existing CC constant-epsilon result remains diagnostic-only; CS/SC effects are not computed until their separately authorized solver runs.

## Independent setups

- TiO2-only case: `RUN3C_N1_MATERIAL_REPRESENTATION_TIO2_CONSTANT_ONLY_DIAGNOSTIC`, attempt_001, entered=false, run_invocation_count=0, SHA256 `67d41e6fa71d623da7a11b0ad11f2a0554846859b65c76823dfa58c3a6dd2ce1`
- SiO2-only case: `RUN3C_N1_MATERIAL_REPRESENTATION_SIO2_CONSTANT_ONLY_DIAGNOSTIC`, attempt_001, entered=false, run_invocation_count=0, SHA256 `4074df820f230bddb9fbbc480ef6148c4d6f759553b21ad13ce9f5237a04ba05`

Both setups were independently reloaded after save; SHA256 remained stable. Each object-level diff contains only the intended material assignment changes and no unexpected differences.

## Material readback

- TiO2-only: TiO2 is scalar Dielectric with ε449=6.447676439940916; SiO2 remains canonical Sampled 3D data with 101 samples and varying canonical ε445/449/455.
- SiO2-only: SiO2 is scalar Dielectric with ε449=2.034121524760185; TiO2 remains canonical Sampled 3D data with 101 samples and varying canonical ε445/449/455.

## Factorial scope

- SS: completed sampled baseline
- CS: setup-only, solver not entered
- SC: setup-only, solver not entered
- CC: existing completed constant-epsilon diagnostic
- Missing CS/SC effects and interaction are intentionally not inferred from setup-only data.

Production mesh remains unfrozen; no DOE, candidate, or training label is authorized.

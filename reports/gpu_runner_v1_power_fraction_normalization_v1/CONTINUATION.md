# Continuation — Runner V1 power-fraction normalization

Updated: 2026-10-05T09:10:12.268408+00:00

## Completed

- Kept Runner V1 serial / single-slot semantics, the pinned GPU observability and state dependencies, and the frozen physical contract unchanged.
- Replaced the output-order source-power scale that reused the zero-order `T_FDTD` proxy with directly measured full-period POSTNP E/H Poynting flux divided by IN_REF incident cell power; per-order source fractions remain that scale times the same grating eta.
- Refreshed two read-only audits against the actual archived `K6LDA1_DEV_D1_M05/attempt_001` FSP using current pinned backend `pw_powernorm_v1_aaaa25b53a9a3322`. FSP/H5 hashes did not change; the existing order JSON was read only. The archive status records one prior `DONE` solver invocation (`K6V2_D1M05_20261004T175055Z_449c4f94`); this audit added zero entries.
- Regression tests: 30 passed under Python 3.10.20. Postprocess dependency preflight: PASS. No solver entry/run/replay.

## Evidence

- Physical report: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\gpu_runner_v1_power_fraction_normalization_v1\INDEPENDENT_PHYSICAL_POWER_AUDIT.json`; SHA256 `8302638ec31cf34f5fce370d5d6d3da47a681092c1e5303c5e5079ce21b19a11`; `APCD_GPU_RUNNER_V1_INDEPENDENT_PHYSICAL_POWER_AUDIT_V1` / `MEASURED`.
- Current-backend LOAD-only report: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\gpu_runner_v1_power_fraction_normalization_v1\LOAD_ONLY_AUDIT.json`; SHA256 `c17655db5f1fb7af8bb2bf6f9ada0660a7298f99ac38fe1068d22e82ba702248`; `APCD_GPU_RUNNER_V1_POWER_FRACTION_NORMALIZATION_LOAD_ONLY_AUDIT_V1` / `PASS`.
- Test and preflight report: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\gpu_runner_v1_power_fraction_normalization_v1\TEST_AND_PREFLIGHT.json`; SHA256 `602a0741d76f26233c7c311e11084c41974932281f3de16a441ca77cc2c33c63`.
- Handoff and hash inventory are adjacent in this directory. The inventory is generated after this file.

## Interpretation boundary

Frozen Coupling representation checks passed: 147/147 source-fraction comparisons at `rtol=1e-3, atol=1e-9` and 21/21 eta sums at `atol=1e-6`. Those checks do not establish physical modal closure. Measured POSTNP E/H versus the 9×9 H2 modal sum has max relative residual `0.000289567`; per-order Runner versus H2 modal fraction max relative residual is `0.00149906`. No frozen physical threshold was found. Leave the Coupling importer default fail-closed and await independent Coupling review before any case-specific supplement intake.

The one-case audit is not a qualification of all 160 V2 geometries. Their solver authorization remains zero. Queue21 stays physical-entry UNKNOWN and quarantined. The independent EXT02 two-plane diagnostic remains a separate completed one-entry case; this audit neither changes nor substitutes its scientific comparison.

## Next

Coupling independently cross-checks the physical report and decides the explicitly scoped supplement intake for this one archived case. Do not rewrite the archived order JSON or truth, do not launch a new case from this report, and do not infer dataset/ML readiness.

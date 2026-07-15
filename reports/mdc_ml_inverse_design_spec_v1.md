# MDC-ML inverse design specification v1

## Scope

This contract covers static Level-A `GaN -> TiO2/SiO2 MDC -> Air` inverse-design records. It does not authorize TMM, FDTD, Lumerical, model training, pilot generation, large databases, or Level-B structures.

The authoritative baseline remains `P1_ZL1_ALTERNATIVE_G3_A3`, read layer-by-layer from `outputs/mdc_p1_asymmetric_scan_static_v1/p1_asymmetric_structures.csv`.

## Identity hierarchy

Four identities have separate responsibilities:

1. `canonical_geometry_hash` v3 hashes the canonicalization contract, source/exit canonical IDs, and ordered `(canonical material ID, integer thickness nm)` layers. It excludes material source hashes, solver settings, grids, mesh, and tolerance seed.
2. `physical_configuration_hash` v1 binds that geometry to `MDC_NATIVE_M1` version 5, the source FSP hash, GaN raw-table hash, and the exposed TiO2/SiO2 material model identities.
3. `simulation_provenance_hash` v2 adds solver ID/version, wavelength and angle grid IDs, angle convention, polarization contract, and numerical-settings contract.
4. `split_group_hash` v1 is derived from the nominal parent canonical geometry. Tolerance children inherit it; material versions and simulation grids cannot move the same parent geometry across splits.

Mirror reversal remains a distinct geometry. Reconstructing the same ordered physical layers produces the same canonical geometry identity.

## Legacy lineage

The frozen historical geometry hash `c38694d6f162c04322ae8a87def91622d4fd4f272e4ec286e85acc978f74d888` is retained. The P0-A value `878c4c625432d1d3bcfb990b7e40038f129289e4eee1187b73738d6a25f8a221` is also retained and explicitly classified as a material-bound legacy/P0-A physical hash, not as the pure v3 geometry identity.

## Staged Pareto activation

The full inventory remains 14 unique fields without an arbitrary weighted score.

Nominal Pareto is 4D:

- `angular_fwhm_450`
- `spectral_fwhm_normal`
- `tmm_apcd_ready_cone5_integral_proxy`
- `tmm_band_transmission_448_453_normal_proxy`

These four fields serve the F0 nominal pilot, first forward surrogate, first nominal Pareto search, and nominal active-learning acquisition.

Robust shortlist Pareto is 5D and adds `tolerance_robustness_penalty_pm3`. It is executable only after nominal screening, shortlist admission, and a completed +/-3 nm tolerance evaluation with a real stored label. A missing label makes the candidate ineligible; it is never converted to zero or imputed. The first nominal surrogate does not predict robustness by default.

## Preserved contracts

P0-A geometry bounds, optical gates, APCD-ready proxy mathematics, tolerance definitions, external NPZ/HDF5 response storage, and solver/fidelity boundaries are unchanged. The frozen alternative still requires an F0 proxy recomputation before its baseline-relative Go threshold can become executable.

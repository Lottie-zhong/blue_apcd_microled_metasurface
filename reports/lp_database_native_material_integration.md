# Canonical LP database native-material integration

## Schema
SQLite tables: materials, material_samples, geometries, simulation_cases, jones_labels, candidate_metrics, provenance.

## Counts
- materials: 2
- material_samples: 202
- geometries: 26
- simulation_cases: 78
- jones_labels: 78
- candidate_metrics: 14
- provenance: 4
- legacy_constant_index cases: 78
- native_sampled_epsilon cases: 0
- unknown_legacy cases: 0

## Historical material audit
- B01/C02/C05: all LP-ML1B2E rows use `legacy_constant_index=2.6`; the shared base runner hard-codes Object defined dielectric index=2.6.
- LP-ML2A A00/A02/A04/A05/B02/C02: all completed 450 nm onecase rows are `legacy_constant_index` using manifest `n_material` values 2.25/2.35/2.50/2.60; none is native `tio22`.

## Adapter
- status: success
- detail: {'APCD_TIO2_NATIVE_M1': 'APCD_TIO2_NATIVE_M1', 'APCD_SIO2_NATIVE_M1': 'APCD_SIO2_NATIVE_M1'}

## New-run gate
New LP simulation runners must use APCD_TIO2_NATIVE_M1 via the sampled-material adapter. Historical constant-index results remain read-only comparison data and are not native baselines.

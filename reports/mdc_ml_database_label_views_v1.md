# MDC ML database label views v1

Source HEAD: `16ff883920c9d539b08b88434b2edf62046b9a8d`; database/schema `1.0.0/1.0.0`.

## Source files

- database_manifest.json: 566 bytes; SHA256 `5c17eb52c90971712d26773f92248eda5558184a4ddeb3ac9b241472e50824b7`
- schema.json: 43678 bytes; SHA256 `05f9fa91a6b6dcd56c5da5351b2d9dc9ffd2599252375d30a0c072b67ea4daf0`
- README.md: 875 bytes; SHA256 `d5b2dcfb8e84f5d5947cfccba75a7ce26b4a8dc941386157e66bfd622efd7747`
- geometry_master.csv: 6815605 bytes; SHA256 `77121fdb8cf271f031c9bb73d257ee7f10de7fc5fc9298f47f277947c95efe03`
- tmm_nominal_metrics.csv: 1115860 bytes; SHA256 `7a57065ba9242e0450a75c8281b3e2c920684f55a78a4c8fbb81097ab9fe8af5`
- tolerance_samples.csv: 5166231 bytes; SHA256 `9e28bae487bb597b16ddf0e2473104a59e16e73b7ab0deea8add4dc6902085e3`
- fdtd_validation.csv: 6148 bytes; SHA256 `11f440456c89fc6c75db8a0b0729124723bf54eb3ed41828728b7bf9e6c9f919`
- split_assignments.csv: 1365817 bytes; SHA256 `2559005462b6f18c9626e99eb6977e13dde9c3d86ea48dc33d1c4910a5fd2c00`
- label_dictionary.csv: 2052 bytes; SHA256 `48e8dadfc79a2dc6c2942571c8ff1cf2290d0aeafd34ebee1d89d0f5acc36f9a`
- quality_audit.json: 309 bytes; SHA256 `9c5b5909af6e4b9dd4b1c1664417d88ad8167ad51dbd82b31f94f8101c4206e4`
- split_audit.json: 476 bytes; SHA256 `9381addaf9b1b7b12694ba104dee112aac8e5db205406e2f21645272a1beec0a`

## Sample roles

- `canonical_tmm_sweep`: 2,688 TMM facts (coarse 2,673 + refined 15).
- `tolerance_perturbation`: 8,400 robustness rows; not training rows.
- `fdtd_external_high_fidelity_reference`: 11 external rows; never mixed into canonical TMM.
- `geometry_master.is_nominal_geometry`: legacy reference-candidate marker only; never used as a canonical filter.

## Views

- spectral view: 2688 rows; topology {'Explicit': 1848, 'ZL-1': 630, 'ZL-2': 210}; geometry_hash unique.
- angular sparse view: 2688 rows; angular FWHM valid 15; maximum angle valid 2; missing values remain blank with `not_computed`.
- tolerance view: 8400 rows; parent join status {'unique_matched': 7157, 'geometry_matched_canonical_missing': 1243}; non-canonical parents retain blank deltas with explicit missing reason.
- FDTD reference view: 11 rows; single-wavelength spectral FWHM status `not_available`.

## Semantics and limitations

- No missing label was filled with zero and no strict/near-normal threshold was invented.
- TMM angular transmission metrics are plane-wave metrics, not dipole far-field metrics.
- FAB/PERF/ratio labels are preserved source fields; this task does not redefine their thresholds.
- No model, checkpoint, prediction, loss curve, or new simulation data was created.

## Validation

- Cardinality checks pass for geometry and parent hash joins; tolerance parent hashes not present in canonical TMM are explicitly marked.
- Canonical TMM excludes tolerance and FDTD rows by source role.
- Outputs are deterministic byte-stable for identical frozen inputs.

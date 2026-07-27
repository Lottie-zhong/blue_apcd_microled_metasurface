# APCD MDC-ML Classification Crossfit Backend — Stage B Final Freeze

Status: `FROZEN_SYNTHETIC_BACKEND_AND_EXECUTION_HARNESS_V1`

`CLASSIFICATION_CROSSFIT_BACKEND_FROZEN=true`

`FORMAL_CLASSIFICATION_OOF_STARTED=false`

`FULL_TRAINER_IMPLEMENTATION_FROZEN=false`

`FORMAL_TRAINING_STARTED=false`

This freeze covers the synthetic classification crossfit backend, its persistent execution state, failure/resume behavior, fresh-process worker, CLI audits, fixtures, and evidence harness. It does not claim that formal classification OOF, formal model training, regression, test evaluation, a v2 champion, or an MDC–NP joint model has run.

## Stage A history

Stage A commit: `038e410960656d777af531b64e1ae406cd0c1b45`.

Stage A supplied the classification metadata audit, frozen four-fold plan, synthetic ExtraTrees candidate path, calibration and threshold logic, OOF serialization, and the initial fixture. Its freeze language was premature because `TrainingExecutionState`, failure/resume evidence, completed-fold skipping, artifact SHA/mtime preservation, drift rejection, and an independent Python fresh-process roundtrip were not yet fully demonstrated.

## Stage B implementation

Stage B connects classification execution to `TrainingExecutionState` and atomic checkpoints. The fixture proves:

- top-level state `PARTIAL`;
- `PREFLIGHT=COMPLETE` and `CLASSIFICATION_OOF=COMPLETE`;
- fold units 0–3 `COMPLETE`;
- injected fold-2 failure and an observed `FAILED` state;
- real resume with completed folds 0 and 1 skipped;
- completed artifact SHA and mtime preservation;
- artifact drift rejection;
- an independent Python worker with distinct parent/worker PIDs;
- matching raw, calibrated, and label signatures;
- 512 OOF target rows, exact-once;
- 16 synthetic classification fits and 16 synthetic calibration fits.

Formal classification fits, formal OOF, formal training, regression, MLP, conformal, bootstrap, promotion, routing, proposal, sealed-test access, output writes, TMM, FDTD, Lumerical, and solver calls remain zero.

## Evidence results

### Classification

- collected: 3
- executed: 3
- all pass: true
- V3 manifest SHA-256: `449FBCC5724CB77F4F8BD52C73536CC225B7D7A32B75B6D9BF3848717DB87156`

### Backend

- collected/planned/executed: 106/106/106
- exact-once: true
- missing/duplicate/unexpected/failed: `[]` / `[]` / `[]` / `[]`
- attempt-02 summary SHA-256: `5a5504d724a6c00a82dbeefb7772389671142cae4f0cb2f90df42a157610e286`
- attempt-02 manifest SHA-256: `5c0e8ea864455ee7454f7d53fcb96e912de45d6bcb2aa0fded7c0d89cb86d977`

### Harness and Python compilation

- harness collected/executed: 14/14
- harness all pass: true
- harness summary SHA-256: `3d0ad86d84bf55d616af9d40c1b795ef44e0cdc9fc2853a16364b2c4483a90f7`
- harness manifest SHA-256: `3cd6e20a01d6a8f5bbee525f0491551b9d8fc7ad4a71d116395d057a788b8dcc`
- modified Python files compile successfully.

### CLI audits

- preflight: `PASS`
- status: `NOT_STARTED`
- backend audit: `PASS`
- classification backend audit: `PASS`
- Round1 rows: 128
- fold count/sizes: 4 / `[31,34,39,24]`
- group and train/held-out overlap: 0 / 0
- fixed candidate: `extra_trees_1`
- fit/formal/sealed/solver/write counters: 0

### Pre-commit fixture

- run ID: `classification-stageb-precommit-durable-v1-001`
- command return code: 0
- task result: 0
- checkpoint count: 14
- fixture audit SHA-256: `4b65cff2880cd6c107d355c92116c0253a46583874b2ac8dd2f2614f06803b77`
- fixture artifact manifest SHA-256: `af24819d555218c5f8af434e02d940bcd9e292c7a643d307199b1cc39ee4cf3c`
- fixture state manifest SHA-256: `1461e81390f3dcdc0e36a325f71cfcbcbc027cd9893925ba0e85d61441883a34`
- fixture child-process evidence SHA-256: `123f4e2e7d46eb0a0c188ab66587f1ef50c688440573a10c6089fd9b609c1b6e`
- parent/worker PID: 22276 / 30548
- OOF rows/exact-once: 512 / true
- synthetic classification/calibration fits: 16 / 16

### Official outputs

- Combined SHA-256: `d738ebd5545b2b582b47721cd5c9e02c116d736eb2784caa6019d76488a576c4`
- Shared SHA-256: `a0a486e2508ed5da0560947fbd5b2f04f6412d7a81056e1ec3d09bb19b7d597e`
- Round1 SHA-256: `7fff8fa3eef74177b14e27ba1404789a521656eec667bcd1546c30cfe360b054`
- formal merge/retrain tree: 10 files, 18,082,726 bytes
- formal tree fingerprint: `31268194235fbd21cb229f4037afb2410e59c835712ac627524739612903ae6f`
- before/after exact match: true
- changed/added/removed: `[]` / `[]` / `[]`

### Pre-commit aggregate

- P54 summary SHA-256: `023e50f025b847b98cd7791696bc2e73f3f9955f6e147f361095519714bab637`
- P54 manifest SHA-256: `f4d7095e87299a978bbdd7d464bfab3a2c1bf5f1cd6c890e97adf88baacf8c25`
- final pass: true
- pre-commit evidence closure: true
- effective failed/interrupted capsules: 0/0

## Superseded history retained

The evidence chain retains, but does not count as effective failure:

1. PowerShell `Process.ExitCode` null observations, superseded by shell `ERRORLEVEL`.
2. V4-001 runner preparation failure before pytest execution.
3. V4-002 stale backend assertion text; the dedicated guard is `FORMAL_CLASSIFICATION_OOF_REQUIRES_SEPARATE_AUTHORIZATION`.
4. False-positive H13 caused by interpreting batch size maximum 10 as minimum 10. The authoritative 106-node plan is `[10,10,10,10,10,10,10,10,10,10,6]`.
5. Ordinary P41–P44 and TEMP runner attempts, preserved as superseded evidence.

## MDC labels retained for future MDC–NP physical coupling

This section freezes only the future MDC-side interface. It creates no data and does not backfill any database.

### Bidirectional complex scattering matrices

Retain the real and imaginary components of all Jones entries:

- `r_plus_xx_re/im`, `r_plus_xy_re/im`, `r_plus_yx_re/im`, `r_plus_yy_re/im`
- `r_minus_xx_re/im`, `r_minus_xy_re/im`, `r_minus_yx_re/im`, `r_minus_yy_re/im`
- `t_plus_xx_re/im`, `t_plus_xy_re/im`, `t_plus_yx_re/im`, `t_plus_yy_re/im`
- `t_minus_xx_re/im`, `t_minus_xy_re/im`, `t_minus_yx_re/im`, `t_minus_yy_re/im`

For a strictly one-dimensional isotropic TMM representation, TE/TM storage is permitted only with an explicit basis definition and transform version.

### Wavelength, angle, ports, phase, and normalization

Retain `wavelength_nm`, `frequency_hz`, `kx_per_um`, `ky_per_um`, `incident_theta_deg`, `incident_phi_deg`, `angle_convention`, `kx_convention`, `polarization_basis`, `basis_transform_version`, `source_side`, `incident_medium_id`, `output_medium_id`, `reference_plane_top_z_nm`, `reference_plane_bottom_z_nm`, `phase_reference_contract_id`, `phase_unwrap_convention`, `time_harmonic_convention`, `field_amplitude_normalization`, and `power_normalization`.

### Structure and provenance

Retain `mdc_structure_id`, `geometry_hash`, `canonical_source_group`, `layer_sequence`, `layer_material_ids`, `all_layer_thicknesses_nm`, `pair_numbers`, `defect_material_id`, `defect_thickness_nm`, `defect_position`, `top_termination`, `bottom_termination`, `source_branch`, `source_commit`, `source_script`, `source_config_sha256`, `geometry_sha256`, `material_data_sha256`, `solver_name`, `solver_version`, `fidelity`, `run_id`, and `timestamp`.

`fidelity` includes at least `TMM`, `FDTD`, `RECOVERED_REFERENCE`, and `ANALYTIC_OR_PHYSICAL_CASCADE`.

### Derived targets, quality, and negative samples

Retain `spectral_fwhm_normal_nm`, `angular_fwhm_450_deg`, `cone5_integral_proxy`, `normal_band_transmission_proxy`, `peak_wavelength_nm`, `peak_transmission`, `peak_reflection`, `peak_angle_deg`, `phase_slope_at_peak`, `group_delay_proxy`, `direction_asymmetry`, `energy_closure_error`, `spectral_valid`, and `angular_valid`.

Also retain `geometry_valid`, `solver_started`, `solver_completed`, `solver_converged`, `runtime_failure`, `postprocess_failure`, `nan_detected`, `power_balance_pass`, `energy_closure_pass`, `reference_plane_valid`, `classification_eligible`, `regression_eligible`, `failure_stage`, and `failure_reason`.

NP metasurface labels remain owned by the NP branch. The MDC branch does not duplicate the NP database. Future coupling occurs through structure IDs, port contracts, and full complex scattering-matrix interfaces. Stage B does not train a joint model. Four summary regression targets do not replace the full complex scattering matrices. All failed and ineligible samples remain available for validity and reliability modelling.

## Next module

`MDC_ML_REGRESSION_THREE_SEED_CROSSFIT_CONFORMAL_BACKEND_V1`

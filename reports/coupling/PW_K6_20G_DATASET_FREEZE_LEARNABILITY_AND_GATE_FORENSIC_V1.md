# PW_K6 20G dataset freeze, learnability and gate forensic

Status: PASS (zero-solver scientific analysis; control gate fixed in source)
Generated: 2026-09-27T14:50:28Z

## Scope and freeze

- Fixed-MDC PW periodic dataset; no solver, replay, enqueue, or production DB mutation in this task.
- Ordered dataset: base S02/S03/S04/S05/S15 + valid S16/attempt_002 + EXT01-EXT14/attempt_001 = 20 unique geometries.
- Snapshots: 8G = base six + EXT01/02; 12G = 8G + EXT03-06; 20G = 12G + EXT07-14.
- Each selected case has one scientific entry, one return, one valid truth/archive, and no replay.
- S16/attempt_001 is setup-only and is explicitly excluded; S16/attempt_002 is the accepted truth.

Authoritative files:

- `PW_K6_20G_DATASET_FREEZE_MANIFEST_V1.json`
- `PW_K6_20G_DATASET_LEDGER_V1.json`
- `PW_K6_20G_SOURCE_PROVENANCE_MANIFEST_V1.json`
- `PW_K6_20G_FRESH_LOAD_ONLY_VALIDATION_V1.json`
- `PW_K6_20G_CPU_LEARNABILITY_ANALYSIS_V1.json`

## Fresh LOAD-only validation

Result: PASS; 20/20 FSPs loaded.
Each case reported FDTD=1 and MON_IN/MON_PRENP/MON_POSTNP=1. The validation script sets `solver_called=false` and never calls `run()`.

## CPU-only learnability

Evaluation split: geometry-grouped leave-one-geometry-out; wavelengths remain ordered and are never randomly split. Models: Ridge, shallow MLP; exact GP for R/T on 8G and 12G only because exact GP is cubic and not practical for 20G. Routing target is the seven post orders `power_fraction_of_source`. Complex state uses the 324 real/imag components per sample from `PW_COMPLEX_FLOQUET_STATE_V1`; phase is circular and reported for all coefficients, while relative magnitude uses a 1e-8 denominator floor.

### 8G

- Scalar R/T/A, Ridge: RMSE=0.14287899398586223, MAE=0.11711954572213112, corr=0.6392701806194231; shallow MLP: RMSE=0.11046205310945613, MAE=0.0840356715460222, corr=0.8096817526039132.
- Seven-order routing decoder, Ridge: RMSE=0.0597096816422549, MAE=0.03876682339344086, corr=0.38824244473380276; MLP: RMSE=0.039150502377737074, MAE=0.022303208734125515, corr=0.6174608817947198.
- Worst scalar geometry (MLP): K6V1_S15; worst routing geometry (MLP): K6V1_EXT01.
- Exact GP R/T: R RMSE=0.16015222178488964, corr=-0.153691613090428; T RMSE=0.11942136055861122, corr=-0.3913400857080711.

### 12G

- Scalar R/T/A, Ridge: RMSE=0.15319629102502572, MAE=0.12195208281615268, corr=0.5798656744912194; shallow MLP: RMSE=0.0961759045009958, MAE=0.07455302372849253, corr=0.857599918367221.
- Seven-order routing decoder, Ridge: RMSE=0.05633215298390332, MAE=0.026391664918780464, corr=0.36906095580867904; MLP: RMSE=0.04595993342230279, MAE=0.021475767916754585, corr=0.5901679236715993.
- Worst scalar geometry (MLP): K6V1_EXT04; worst routing geometry (MLP): K6V1_EXT04.
- Exact GP R/T: R RMSE=0.16362695089688378, corr=-0.1759883688701252; T RMSE=0.13429861272260094, corr=-0.47163599082231183.

### 20G

- Scalar R/T/A, Ridge: RMSE=0.1424307506518855, MAE=0.11467823332799018, corr=0.682305721728288; shallow MLP: RMSE=0.10675679865785176, MAE=0.08674258915866451, corr=0.8485110834880275.
- Seven-order routing decoder, Ridge: RMSE=0.04644199976922973, MAE=0.021172734784445053, corr=0.46546357128186977; MLP: RMSE=0.040462835488872945, MAE=0.02013705607789868, corr=0.6387342023515791.
- Worst scalar geometry (MLP): K6V1_EXT08; worst routing geometry (MLP): K6V1_EXT14.

### 20G complex-state detail

For the 20G state models, each line gives propagating-subspace and evanescent-subspace complex relative-error summaries plus Re/Im RMSE, magnitude RMSE, and circular phase MAE. The frozen upstream-prior rows are diagnostic conditional models, not production predictors.

- `plane_0_ridge_geometry_only`: propagating median relative=1.0015958072554834, p95=1.5493894541645663, ReRMSE=0.34237302435244216, ImRMSE=0.26031692400078965, |C|RMSE=0.2370714225388215, phaseMAE=84.82020710360331 deg; evanescent median relative=None, p95=None, ReRMSE=None, ImRMSE=None, |C|RMSE=None, phaseMAE=None deg; worst=K6V1_EXT03.
- `plane_1_ridge_geometry_only`: propagating median relative=1.0082212512074273, p95=1.7464736684388835, ReRMSE=1.3943065109498332, ImRMSE=1.6219346791391211, |C|RMSE=1.8593809553928404, phaseMAE=85.67983591214423 deg; evanescent median relative=1.0142462098881666, p95=2.168699273873746, ReRMSE=0.43820570826701805, ImRMSE=0.43255305021662793, |C|RMSE=0.5538926060103792, phaseMAE=84.42921517506181 deg; worst=K6V1_EXT02.
- `plane_1_ridge_frozen_upstream_prior`: propagating median relative=0.4017542437789124, p95=2.7716436313841144, ReRMSE=0.5656606881715771, ImRMSE=0.5656459400862451, |C|RMSE=0.5198046674118086, phaseMAE=33.25812636276271 deg; evanescent median relative=0.7747425919638193, p95=3.932559613814199, ReRMSE=0.4173633743812875, ImRMSE=0.4232686570371011, |C|RMSE=0.36174192131162747, phaseMAE=49.093388615333254 deg; worst=K6V1_EXT08.
- `plane_2_ridge_geometry_only`: propagating median relative=1.0120397985342526, p95=2.022781346795263, ReRMSE=2.020614874374472, ImRMSE=2.0373257334318673, |C|RMSE=2.3137564253582212, phaseMAE=83.0267865973665 deg; evanescent median relative=0.992698123750934, p95=1.8746547880329145, ReRMSE=0.5412010487592462, ImRMSE=0.5379315073828353, |C|RMSE=0.6295018688692894, phaseMAE=83.48764608663608 deg; worst=K6V1_EXT13.
- `plane_2_ridge_frozen_upstream_prior`: propagating median relative=1.1821454384710852, p95=5.110280628780743, ReRMSE=2.240751808408209, ImRMSE=2.3412512293208843, |C|RMSE=1.962124679629581, phaseMAE=68.38806159240205 deg; evanescent median relative=1.1458533880722817, p95=4.6227334243204, ReRMSE=0.5263756377083049, ImRMSE=0.5383232876041909, |C|RMSE=0.4603093600949895, phaseMAE=68.08057637733363 deg; worst=K6V1_EXT04.

Interpretation: scalar observables and seven-order routing improve from 8G to 20G, but geometry-only complex state prediction remains around unit relative error with large phase error. The 20G data therefore supports a learnability diagnostic, not a solver-replacement or ML production admission. The PRENP frozen-upstream prior improves the 20G median relative error and phase versus geometry-only; the POSTNP prior does not establish a production-quality surrogate.

## Control-plane forensic

- EXT01/EXT02 were recovered after the sidecar-readiness race and reached valid durable truth. Their release caused normal queue refill because the global hold was false.
- EXT03-EXT14 each has one actual scientific entry and valid truth; these entries are retained as valid data but are labeled `NORMAL_AUTOFILL_AFTER_RELEASE`, not retroactively reclassified as validation-only.
- At generation 20 the canonical `admission_control` row was `new_entry_hold=0`, `health_status=PASS`; EXT03-EXT14 admission and final revalidation events recorded `new_entry_hold=false` and no exact permit. Queue payloads had no row-level validation-only/autofill veto.
- Root cause: control-state/policy mismatch (A) plus missing explicit validation-only queue gate (D). It is not a geometry, wavelength, extraction, FDTD persistence, or solver-return truth failure.

Fix: `dispatcher.py` now leaves rows with `validation_gate=VALIDATION_ONLY`/`MANUAL_ONLY` or `autofill_enabled=false` in WAIT_RESOURCE_CAPACITY during release refill. An exact permit does not bypass final admission; it is only the explicit manual path into that existing gate. No schema change and no production DB mutation.

## Regression and authority

- Admission gate: PASS, 34 checks including the two new validation-only/autofill checks.
- Global zero-solver: PASS 20/20.
- Branch/integration: PASS 20/20 plus Coupling-ML integration PASS.
- Chaos/runtime/recovery: PASS 12/12 and supporting post-entry, pre-entry, orphan-fence suites PASS.
- Persistence/finisher: PASS 20/20.
- All listed tests report solver_invocations=0, scientific_solver_entries=0.
- Production evidence: foreign_mutation_count=0, duplicate_scientific_entry_count=0, selected PW scientific entry count=20, replay_count=0.

## Scientific decision boundary

The 20G dataset is frozen and analyzable. Do not launch a new solver or promote the surrogate from this report. Any future solver entry must first carry the explicit validation gate policy and receive a separate Chart-approved scientific authorization.

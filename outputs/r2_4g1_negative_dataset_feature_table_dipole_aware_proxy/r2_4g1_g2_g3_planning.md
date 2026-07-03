# R2-4G1 G2/G3 Planning

G2 is optional and not immediate. It requires explicit review/approval after G1.

G2 boundary:
- maximum 2 new candidates;
- tri-point x-dipole only;
- 453 nm only;
- no y/z/broadband;
- fail stops the candidate.

G3 boundary:
- update threshold/risk-score rules using G1 negatives plus any approved G2 calibration results;
- no new candidate generation until proxy thresholds are updated;
- output calibrated guards before G4 candidate generation.

Recommended G2 task name:
`R2-4G2_optional_minimal_dipole_proxy_calibration_fdtd_plan`

Recommended G3 task name:
`R2-4G3_update_dipole_aware_proxy_thresholds_from_negative_dataset`

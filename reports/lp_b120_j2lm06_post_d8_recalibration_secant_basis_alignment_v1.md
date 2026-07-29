# POST-D8 Recalibration Secant Basis Alignment v1

## Scope
Offline analysis only. No solver, lumapi, FDTD, D9, candidate geometry, progression plan, or canonical merge.

## Common basis
Raw vector: `['J1_side_nm', 'J2_length_nm', 'J2_width_nm', 'D_nm', 'Psi_deg']`. Active vector: `['J2_width_nm', 'D_nm', 'Psi_deg']`. Normalization steps: W=1 nm, D=0.5 nm, Psi=0.285762116876534 degree. Psi derivatives remain degree/degree; radians are not mixed.

## Secant families
S1 J2LM06¡úD7: 8 rows. S2 D7 anchor¡úD8: 8 rows. S3 D8 trade-off¡úrecalibration: 4 rows. S4 D8 trade-off¡úlowest-phase D8: 1 row.

## Alignment
Recalibration normalized phase gradient: [0.5144941647821362, -0.07321142571127329, 0.02128526966027953]; raw derivatives: W 0.514494 degree/nm, D -0.146423 degree/nm, Psi 0.074486 degree/degree. Aggregate phase residual MAE across secants: 1.702527 degree. Pairwise phase-gradient angles: [{"family_a":"S1_J2LM06_TO_D7","family_b":"S2_D7_TO_D8","cosine":-0.9945492510484982,"principal_angle_deg":174.01501333900086},{"family_a":"S1_J2LM06_TO_D7","family_b":"S3_D8_TO_RECALIBRATION","cosine":-0.13355942330802087,"principal_angle_deg":97.67532656787381},{"family_a":"S2_D7_TO_D8","family_b":"S3_D8_TO_RECALIBRATION","cosine":0.22452930541522562,"principal_angle_deg":77.02479881926014}].

## Validation
Leave-one-stage-out: {"S1_J2LM06_TO_D7":{"n":8,"mae_deg":2.694963563487899,"max_abs_deg":3.210176087586433,"prediction_model":"anchor-centered phase secant"},"S2_D7_TO_D8":{"n":8,"mae_deg":0.7784882760039157,"max_abs_deg":1.7093217045664528,"prediction_model":"anchor-centered phase secant"},"S3_D8_TO_RECALIBRATION":{"n":4,"mae_deg":16.841331351708973,"max_abs_deg":24.304519117940828,"prediction_model":"anchor-centered phase secant"},"S4_D8_TO_D8_LOWEST_PHASE":{"n":1,"mae_deg":2.9435917307553923,"max_abs_deg":2.9435917307553923,"prediction_model":"anchor-centered phase secant"}}. D7-fit¡úD8 frozen audit MAE=1.573067 degree; D7+D8¡úrecalibration MAE=25.042293 degree; recalibration leave-one-probe phase MAE=1.2002 degree and Jones max=0.03378.

## Closure and diagnosis
Tetrahedral observed phase closure=0.876454 degree; first-order prediction=-0.074674 degree; normalized closure error=0.752465. This is significant unresolved curvature evidence, not a fabricated Hessian. Inactive J1_side/J2_length components are retained explicitly.

Primary diagnosis: **MIXED_SCALE_DRIFT_AND_CURVATURE**. Route: **LOCAL_CURVATURE_REQUIRES_ADDITIONAL_DIAGNOSTIC**.

No next geometry or D9 authorization is created.

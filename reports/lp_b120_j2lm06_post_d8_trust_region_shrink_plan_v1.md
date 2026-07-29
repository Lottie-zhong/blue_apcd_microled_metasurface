# APCD LP D8 Trust-Region Shrink Plan Freeze v1

Status: HARD_GATE_QUANTIZATION_FLOOR_PREVENTS_MEANINGFUL_SHRINK

Offline-only; solver/lumapi/FDTD calls = 0. No D9, progression candidate, execution package, or physics staging.

Anchor: `D8_TRV_PLAN_d6f4911593b64495`; active variables J2_width_nm, D_nm, Psi_deg; fixed J1_side=110 nm, J2_length=106 nm, H=500 nm, period=432 nm, material=APCD_TIO2_NATIVE_M1.

Central gradient rank=3, singular values=[2.230534533533062, 2.000003154818233, 1.417690570949192], condition=1.5733578111051718; normalized phase gradient=None.
Directional curvature is negative in 4/4 directions; mean=-1.711364, max abs=2.290816, even/odd magnitude ratio=9.718991.

Quantization rules: centers integer/exact-half-nm, J2 width integer, D/Psi recomputed from quantized centers. Required nominal alpha values: 1/2, 1/3, 1/4, 1/5, 1/8.

For Design A at alpha=1/2, normalized-ray angular errors are 39.17 deg, 45.00 deg, 39.45 deg, 39.29 deg. Width rounding collapses the width component for all four directions. At alpha=1/3 and 1/4 the ray distortion remains large; at alpha=1/5 and 1/8 all four points collapse exactly to anchor. The first nonzero integer width step requires alpha=1, which is not a shrink.

Design A uniform radial: rejected; no common alpha gives four unique, ray-preserving shrunken geometries.
Design B two reduced central pairs: rejected; same width-grid collapse/angular distortion and incomplete curvature-direction coverage.
Design C anisotropic width-full/D-Psi-half: rejected; effective width alpha remains 1, so it cannot establish a reduced-radius linear region; center quantization remains an angular-risk.

Manufacturing geometry remains legal for enumerated points (direct/periodic gaps above 60 nm, no overlap, primitive valid), but quantization prevents meaningful access to a smaller trust region. Therefore no future solver budget is frozen: 0 geometries / 0 x-y subruns / 450 nm only, planning-only not authorized.

No full Hessian is claimed; this is a sampled directional shrink audit only.

Outputs:
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_trust_region_shrink_factor_audit_v1.json` SHA256 `422b30dd084fc18871de28ef2d7022de43d60f63ebfc4d88272d1e68fd81286d`
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_trust_region_quantization_floor_v1.json` SHA256 `56bb0de31973b07e374ceeee7a996b854f07a0364594ec04a29ecbcc0a5058b8`
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_trust_region_design_comparison_v1.json` SHA256 `4636145899d2fe889de0037562dc001b75774324e2e0b57142ed1a023b313cfd`
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_trust_region_geometry_gate_v1.csv` SHA256 `3f9cc98e5f0958ce657cc83f5aa91451c1a68ca1c2a3648ce79a75c1cac4cfab`
- `outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_trust_region_shrink_diagnostic_plan_v1.json` SHA256 `e8c59b7a5a171d4d8abc63c92fee87fd986ad01e8bff668f197fba9baa72aca6`
- `outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_trust_region_shrink_diagnostic_plan_v1.csv` SHA256 `493f89103a9ecfeeebd3d1679569556138ab0cf7993d9851afdf1f077ecbb465`
- `outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_trust_region_shrink_execution_contract_v1.json` SHA256 `ee8af9945ca04b69b531054384d0b358ce5caf547cf818f401bc96bee98bd0af`
- `outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_trust_region_shrink_ml_label_contract_v1.json` SHA256 `1bf24eff02ceec331e0ada84f9189e8c154ceb5e1d3eddfeb65bba80a8d15fc5`
- `outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_trust_region_shrink_validation_metric_contract_v1.json` SHA256 `e66ae69042bc664b8a69de6d49165a89c3e7cb21408a9630297e0dabcb425d53`

Protected report SHA256 before/after are unchanged; existing D7/D8/canonical physics evidence remains read-only.

# mdc_stage_al1_solver_budget_audit_v1

```json
{
  "run_root": "D:\\project\\worktrees\\blue_apcd_mdc_ml_inverse_v1\\outputs\\mdc_fdtd_active_learning_stage_al1_v1\\al1-20260730T001100Z-dfc33018fde6",
  "new_geometries": 6,
  "total_independent_geometries_with_frozen_existing": 9,
  "unique_cases": 36,
  "solver_calls": 36,
  "paired_geometry_count": 6,
  "formal_filter": "0.2",
  "dipole_tmm_allowed_metrics": [
    "angular FWHM",
    "cone5",
    "cone10",
    "cone20",
    "angular shape prior"
  ],
  "prohibited_proxy_metrics": [
    "relative upward power",
    "x/z polarization delta",
    "source-depth sensitivity",
    "absolute extraction",
    "Purcell/LDOS"
  ],
  "route": "PROCEED_TO_AL2_REMAINING_36",
  "residual_geometry_dependent": true,
  "sample_sufficiency": "Nine independent geometries support diagnostics and grouped low-dimensional calibration only; no high-capacity residual surrogate is trained or authorized.",
  "filter_audit": [
    {
      "candidate_id": "EX_N2_L79_H47_C153",
      "mean_abs_normalized_delta": 0.005729436936816262,
      "max_abs_normalized_delta": 0.02517578348726901
    },
    {
      "candidate_id": "EX_N2_L81_H44_C160",
      "mean_abs_normalized_delta": 0.006776566717297672,
      "max_abs_normalized_delta": 0.03213870965807375
    },
    {
      "candidate_id": "EX_N3_L79_H45_C156",
      "mean_abs_normalized_delta": 0.011827393524636626,
      "max_abs_normalized_delta": 0.07601422956220438
    },
    {
      "candidate_id": "EX_N3_L79_H47_C161",
      "mean_abs_normalized_delta": 0.0325342008156922,
      "max_abs_normalized_delta": 0.19839360553908914
    },
    {
      "candidate_id": "EX_N5_L78_H45_C156",
      "mean_abs_normalized_delta": 0.05202856350343158,
      "max_abs_normalized_delta": 0.8340805003249736
    },
    {
      "candidate_id": "ZL2_N3_L80_H45",
      "mean_abs_normalized_delta": 0.014659802966798065,
      "max_abs_normalized_delta": 0.05967370608457223
    }
  ],
  "xz_eta_range_min_max": [
    0.004077305655515888,
    0.04476359052097316
  ],
  "source_depth_eta_span_min_max": [
    0.004077305655515888,
    0.04476359052097316
  ]
}
```

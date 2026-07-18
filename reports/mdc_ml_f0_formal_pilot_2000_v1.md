# MDC_ML_F0_FORMAL_PILOT_2000_V1_RESULT

## P2K-A POWER-BALANCE AND TRAINING ELIGIBILITY FREEZE

- Contract: `post_TMM_training_eligibility_mask_v1`; fixed `power_balance_tolerance = 0.001`.
- Postprocess decision: `PATH_A`. The only formal power-balance failure was already excluded by its all-false continuous target mask, invalid FWHM fields, `nominal_4d_objective_eligible = false`, `shortlist_quality_eligible = false`, both Pareto sets, and the 15-item interesting set. No output, NPZ, raw metric, artifact hash, candidate signature, dataset signature, or combined signature was changed.
- `solver_valid` and `power_balance_failure` remain independent: a successful solver record can be retained for classification, anomaly detection, and solver-quality analysis while being excluded from continuous regression.
- Above-unity raw values remain unclipped. An above-unity sample inside the fixed tolerance is not excluded unless another quality rule fails.

| Sample | Origin | Family/category | T450 raw | Raw NPZ maximum and location | Excess | Failure | Final continuous / 4D / shortlist / formal Pareto / combined Pareto / interesting |
|---|---|---|---:|---|---:|---|---|
| `F0_PRE1_GLOBAL_DUAL_DEFECT_011` | PRE1 | dual defect / global | 1.0000791296 | 1.0008996124, TE, 448.0 nm, -11 deg | 0.0000791296 | false | true / true / true / n/a / false / n/a |
| `F0_FORMAL_GLOBAL_DUAL_DEFECT_0103` | FORMAL | dual defect / global | 1.0006811513 | 1.0012042773, TM, 450.0 nm, -1 deg | 0.0006811513 | false | true / true / false / true / true / false |
| `F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0033` | FORMAL | hybrid periodic-aperiodic / global | 1.0011407213 | 1.0012403420, TE, 448.0 nm, -12 deg | 0.0011407213 | true | false / false / false / false / false / false |

The failure is not a single-grid-point event: values above 1.001 occur in angular, spectral, and APCD-ready TE/TM arrays. All 52 NPZ arrays are finite; the artifact SHA matches its manifest. At the maximum point, `P_entering = 1.001240341994908`, `R = 0.001105451392388`, `A_stack = -1.33e-15`, and `far_field_balance_offset = -0.002345793387297`, supporting a numerical power-balance quality failure rather than artifact corruption.

Training readiness is frozen as:

```json
{
  "ready_shared_surrogate": true,
  "need_5000_before_training": false,
  "recommended_next_stage": "SHARED_SURROGATE_V1",
  "classification_population": 2512,
  "continuous_regression_population": 737,
  "model_topology": "shared global surrogate",
  "family_encoding": "embedding or one-hot",
  "heads": ["validity classification", "masked continuous regression"],
  "independent_family_models_supported": false
}
```

The four frozen continuous targets remain spectral FWHM, angular FWHM, cone5 integral, and normal-band proxy. Invalid FWHM remains null, never zero-filled. The cone5/band correlation warning remains active. A later 5,000 expansion must be decided from first-model validation error, uncertainty, and active-learning coverage, not as a prerequisite for first shared-surrogate training.

## ENVIRONMENT

- Host: `DESKTOP-NNE313K`; worktree: `D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1`; branch: `work/mdc-ml-inverse-v1`.
- HEAD: `143dd6a49a4eaa04a74fba03f195c4ebbedacfbd`; disk free at gate: `1431661195264` bytes.

## FROZEN_CONTRACT_GATE

- Repository/frozen/smoke/PRE1 gates: `PASS`; payload drift: `0`.

## FILES_CREATED

- Exactly the five authorized formal config/builder/runner/test/report files; no tracked file modified.

## CANDIDATE_GENERATION

- Seed `20260718`; raw `2106`; valid `2000`; invalid `72`; PRE1 collisions `24`; smoke collisions `0`; formal duplicates `10`; refills `106`.
- Candidate signature: `fc8c1798fcc6d5b764f15bf6bb746d141143b49a05edd9e082de0b666ac21119`; deterministic rebuild: `PASS`.

## SOURCE_AND_FAMILY_QUOTAS

```json
{
  "asymmetric_pair_count": {
    "ANCHOR_NEIGHBORHOOD": 0,
    "FAMILY_CHALLENGE": 32,
    "FAMILY_STRATIFIED_GLOBAL": 157,
    "RARE_CROSS_FAMILY": 16,
    "total": 205
  },
  "dual_defect": {
    "ANCHOR_NEIGHBORHOOD": 0,
    "FAMILY_CHALLENGE": 31,
    "FAMILY_STRATIFIED_GLOBAL": 156,
    "RARE_CROSS_FAMILY": 16,
    "total": 203
  },
  "grouped_chirped": {
    "ANCHOR_NEIGHBORHOOD": 0,
    "FAMILY_CHALLENGE": 31,
    "FAMILY_STRATIFIED_GLOBAL": 156,
    "RARE_CROSS_FAMILY": 16,
    "total": 203
  },
  "hybrid_periodic_aperiodic": {
    "ANCHOR_NEIGHBORHOOD": 0,
    "FAMILY_CHALLENGE": 31,
    "FAMILY_STRATIFIED_GLOBAL": 156,
    "RARE_CROSS_FAMILY": 15,
    "total": 202
  },
  "locally_aperiodic": {
    "ANCHOR_NEIGHBORHOOD": 0,
    "FAMILY_CHALLENGE": 31,
    "FAMILY_STRATIFIED_GLOBAL": 156,
    "RARE_CROSS_FAMILY": 15,
    "total": 202
  },
  "off_center_defect": {
    "ANCHOR_NEIGHBORHOOD": 250,
    "FAMILY_CHALLENGE": 31,
    "FAMILY_STRATIFIED_GLOBAL": 156,
    "RARE_CROSS_FAMILY": 16,
    "total": 453
  },
  "symmetric_periodic": {
    "ANCHOR_NEIGHBORHOOD": 125,
    "FAMILY_CHALLENGE": 32,
    "FAMILY_STRATIFIED_GLOBAL": 157,
    "RARE_CROSS_FAMILY": 16,
    "total": 330
  },
  "termination_reversed": {
    "ANCHOR_NEIGHBORHOOD": 0,
    "FAMILY_CHALLENGE": 31,
    "FAMILY_STRATIFIED_GLOBAL": 156,
    "RARE_CROSS_FAMILY": 15,
    "total": 202
  }
}
```

## STATIC_GATE

- Formal canonical/physical unique `2000/2000`; PRE1/smoke/anchor overlap `0`; combined unique `2512`; integer/legality/source/exit `100%`; Level-B/tolerance `0`; gate `PASS`.

## ANCHOR_CONTROLS

```json
{
  "controls": [
    {
      "anchor_id": "P1_EXPLICIT_FAB_G3_A3",
      "artifact": {
        "array_content_hash": "3bc2339fef05317c9710f2e60f838b654d7e0018779936fcc99c97d96cd05f6c",
        "bytes": 222917,
        "canonical_geometry_hash": "ebddda773461126fdcc8d72d0bf1b47e30b8a9ac31fc6333c75b47acd209c03c",
        "fields": {
          "angular_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_r_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_r_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "apcd_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "apcd_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              11
            ]
          },
          "spectral_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_r_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_r_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              601
            ]
          }
        },
        "format": "NPZ",
        "grid_ids": {
          "angular": "angle_air_450_m60_p60_step_1_deg_v1",
          "apcd_ready": "apcd_ready_wl448_453_step0p5_angle_m60_p60_step1_v1",
          "spectral": "wl_normal_420_480_step_0p1_nm_v1"
        },
        "path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/controls/artifacts/00_ebddda773461126f.npz",
        "sample_id": "P1_EXPLICIT_FAB_G3_A3",
        "sha256": "472c62d8419328911912d13a57d41a6e0ec0975fddd2d2975bce9322f87659ca"
      },
      "authority_file": "outputs/mdc_p1_asymmetric_scan_static_v1/p1_asymmetric_structures.csv",
      "canonical_geometry_hash": "ebddda773461126fdcc8d72d0bf1b47e30b8a9ac31fc6333c75b47acd209c03c",
      "checks": {
        "artifact_array_hash": true,
        "frozen_smoke_reference_when_available": true,
        "independent_frozen_pre1_array_hash": true,
        "independent_frozen_pre1_scalar_metrics": true
      },
      "frozen_smoke_reference": null,
      "reference_array_content_hash": "3bc2339fef05317c9710f2e60f838b654d7e0018779936fcc99c97d96cd05f6c",
      "reference_mode": "independent_frozen_PRE1_recompute",
      "scalar_metrics": {
        "angular_fwhm_450_deg": 26.619013992836376,
        "cone10_fraction_proxy": 0.6045843662847109,
        "cone5_fraction_proxy": 0.3168008129043566,
        "maximum_angle_set_deg": [
          -3.0,
          3.0
        ],
        "normal_band_transmission_proxy": 0.7297593087722971,
        "ratio": 40.115520224477926,
        "spectral_fwhm_normal_nm": 7.399999999999977
      },
      "status": "PASS"
    },
    {
      "anchor_id": "P1_ZL1_NOMINAL_G3_A3",
      "artifact": {
        "array_content_hash": "267f6097e8819e436a828219e7b0c912c02e90fbfb9e46b76b8b3246a16102c4",
        "bytes": 223607,
        "canonical_geometry_hash": "359110db21157c31e5a8dda91f7ca71193d773468894c669338ccb7d1bbe659f",
        "fields": {
          "angular_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_r_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_r_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "apcd_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "apcd_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              11
            ]
          },
          "spectral_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_r_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_r_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              601
            ]
          }
        },
        "format": "NPZ",
        "grid_ids": {
          "angular": "angle_air_450_m60_p60_step_1_deg_v1",
          "apcd_ready": "apcd_ready_wl448_453_step0p5_angle_m60_p60_step1_v1",
          "spectral": "wl_normal_420_480_step_0p1_nm_v1"
        },
        "path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/controls/artifacts/01_359110db21157c31.npz",
        "sample_id": "P1_ZL1_NOMINAL_G3_A3",
        "sha256": "922f3c1455be97a50ed976e16b7969dc01ec69c6eb5540387c1eb6ebfe2be45e"
      },
      "authority_file": "outputs/mdc_p1_asymmetric_scan_static_v1/p1_asymmetric_structures.csv",
      "canonical_geometry_hash": "359110db21157c31e5a8dda91f7ca71193d773468894c669338ccb7d1bbe659f",
      "checks": {
        "artifact_array_hash": true,
        "frozen_smoke_reference_when_available": true,
        "independent_frozen_pre1_array_hash": true,
        "independent_frozen_pre1_scalar_metrics": true
      },
      "frozen_smoke_reference": null,
      "reference_array_content_hash": "267f6097e8819e436a828219e7b0c912c02e90fbfb9e46b76b8b3246a16102c4",
      "reference_mode": "independent_frozen_PRE1_recompute",
      "scalar_metrics": {
        "angular_fwhm_450_deg": 17.826891244564308,
        "cone10_fraction_proxy": 0.7735436105667252,
        "cone5_fraction_proxy": 0.4219643322855401,
        "maximum_angle_set_deg": [
          -4.0,
          4.0
        ],
        "normal_band_transmission_proxy": 0.6534703931296145,
        "ratio": 63.08879456874723,
        "spectral_fwhm_normal_nm": 3.3000000000000114
      },
      "status": "PASS"
    },
    {
      "anchor_id": "P1_ZL1_ALTERNATIVE_G3_A3",
      "artifact": {
        "array_content_hash": "d1809afbec9fa2dc28e2f83fd90099b4ecb2f193d570319e15d8fc61094070f7",
        "bytes": 223668,
        "canonical_geometry_hash": "b30dff7f757c1401a595ee448869f65b5e4535e28995afc3976585dcbf688ed0",
        "fields": {
          "angular_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_r_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_r_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "apcd_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "apcd_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              11
            ]
          },
          "spectral_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_r_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_r_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              601
            ]
          }
        },
        "format": "NPZ",
        "grid_ids": {
          "angular": "angle_air_450_m60_p60_step_1_deg_v1",
          "apcd_ready": "apcd_ready_wl448_453_step0p5_angle_m60_p60_step1_v1",
          "spectral": "wl_normal_420_480_step_0p1_nm_v1"
        },
        "path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/controls/artifacts/02_b30dff7f757c1401.npz",
        "sample_id": "P1_ZL1_ALTERNATIVE_G3_A3",
        "sha256": "2d1b903ae1431462afe57290701c33e73966c42e10b07b1173d0ae33a166d33a"
      },
      "authority_file": "outputs/mdc_p1_asymmetric_scan_static_v1/p1_asymmetric_structures.csv",
      "canonical_geometry_hash": "b30dff7f757c1401a595ee448869f65b5e4535e28995afc3976585dcbf688ed0",
      "checks": {
        "artifact_array_hash": true,
        "frozen_smoke_reference_when_available": true,
        "independent_frozen_pre1_array_hash": true,
        "independent_frozen_pre1_scalar_metrics": true
      },
      "frozen_smoke_reference": {
        "array_content_hash": "d1809afbec9fa2dc28e2f83fd90099b4ecb2f193d570319e15d8fc61094070f7",
        "bytes": 223668,
        "canonical_geometry_hash": "b30dff7f757c1401a595ee448869f65b5e4535e28995afc3976585dcbf688ed0",
        "fields": {
          "angular_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_R_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_T_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "angular_r_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_r_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TE": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "angular_t_TM": {
            "dtype": "complex128",
            "shape": [
              121
            ]
          },
          "apcd_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_R_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_T_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_angle_air_deg": {
            "dtype": "float64",
            "shape": [
              121
            ]
          },
          "apcd_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_r_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TE": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_t_TM": {
            "dtype": "complex128",
            "shape": [
              11,
              121
            ]
          },
          "apcd_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              11
            ]
          },
          "spectral_A_stack_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_A_stack_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_R_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_T_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_far_field_balance_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_incident_interference_offset_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TE": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_power_entering_TM": {
            "dtype": "float64",
            "shape": [
              601
            ]
          },
          "spectral_r_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_r_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TE": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_t_TM": {
            "dtype": "complex128",
            "shape": [
              601
            ]
          },
          "spectral_wavelength_nm": {
            "dtype": "float64",
            "shape": [
              601
            ]
          }
        },
        "format": "NPZ",
        "grid_ids": {
          "angular": "angle_air_450_m60_p60_step_1_deg_v1",
          "apcd_ready": "apcd_ready_wl448_453_step0p5_angle_m60_p60_step1_v1",
          "spectral": "wl_normal_420_480_step_0p1_nm_v1"
        },
        "path": "outputs/mdc_ml_f0_smoke_v1/responses/00_b30dff7f757c1401.npz",
        "sample_id": "P1_ZL1_ALTERNATIVE_G3_A3",
        "sha256": "2d1b903ae1431462afe57290701c33e73966c42e10b07b1173d0ae33a166d33a"
      },
      "reference_array_content_hash": "d1809afbec9fa2dc28e2f83fd90099b4ecb2f193d570319e15d8fc61094070f7",
      "reference_mode": "independent_frozen_PRE1_recompute",
      "scalar_metrics": {
        "angular_fwhm_450_deg": 14.996580473442913,
        "cone10_fraction_proxy": 0.7857629454756327,
        "cone5_fraction_proxy": 0.45356109240238607,
        "maximum_angle_set_deg": [
          0.0
        ],
        "normal_band_transmission_proxy": 0.6313084408788102,
        "ratio": 45.66660483135923,
        "spectral_fwhm_normal_nm": 3.2999999999999545
      },
      "status": "PASS"
    }
  ],
  "resume_skipped": 3,
  "status": "PASS",
  "wall_time_seconds": 11.14603399997577
}
```

## PREFLIGHT

- 32 samples; signature `f671b41d7530cf5914767621b3e31582a7b7332963c6d2bc7ce83ad92b8ed7c7`; solver/schema/artifact `32/32/32`; wall `12.028s`; SHA snapshot unchanged `True`.

## FORMAL_RUN

```json
{
  "checkpoint_first_mtime": 1784369350.1563985,
  "checkpoint_last_mtime": 1784370882.0922587,
  "effective_checkpoint_span_throughput": 1.2846490843280434,
  "evidence_source": "captured_primary_runner_stdout_and_per_sample_checkpoints",
  "formal_checkpoint_span_seconds": 1531.935860157013,
  "formal_wall_time_limitation": "original exact batch wall was overwritten by later resume-only postprocessing; checkpoint span is a lower-bound execution span, end-to-end wall is exact captured stdout",
  "formal_wall_time_seconds": null,
  "newly_solved_count": 1968,
  "preflight_retry_samples_after_schema_adapter_fix": 32,
  "primary_full_default_end_to_end_wall_seconds": 1577.8365180999972,
  "resume_skipped_count": 32,
  "retry_count": 0,
  "solver_runtime_mean": 1.9224410105997232,
  "solver_runtime_p50": 1.719825749984011,
  "solver_runtime_p95": 2.991143064876087,
  "solver_success_count": 2000,
  "warning_count_current_run": 19569053,
  "warning_count_total": 19781496
}
```

## FORMAL_DATASET

- Solver/schema/artifact/SHA/array: `2000/2000/2000/2000/2000`; dataset signature `daea19d4b12cc704f39584589aa7539c5a36365639c1b745f6ebd8683ea4bc4c`.

## COMBINED_2512

- PRE1/formal/combined `512/2000/2512`; canonical/physical unique `2512/2512`; artifact references `2512`; signature `d14b0555e488516dcd94443386a283a0cb7d8de119ab069d9ec20b2b93c7591d`; PRE1 copies `0`.

## QUALITY_AUDIT

- Formal spectral/angular/4D/shortlist: `1000/1000/580/103`.
- Combined spectral/angular/4D/shortlist: `1265/1256/737/131`.

## FAMILY_AND_CATEGORY_VALIDITY

```json
{
  "category": {
    "ANCHOR_NEIGHBORHOOD": {
      "angular_valid": 216,
      "four_objective_eligible": 146,
      "shortlist_eligible": 35,
      "spectral_valid": 214,
      "total": 375
    },
    "FAMILY_CHALLENGE": {
      "angular_valid": 123,
      "four_objective_eligible": 68,
      "shortlist_eligible": 8,
      "spectral_valid": 121,
      "total": 250
    },
    "FAMILY_STRATIFIED_GLOBAL": {
      "angular_valid": 600,
      "four_objective_eligible": 333,
      "shortlist_eligible": 52,
      "spectral_valid": 604,
      "total": 1250
    },
    "RARE_CROSS_FAMILY": {
      "angular_valid": 61,
      "four_objective_eligible": 33,
      "shortlist_eligible": 8,
      "spectral_valid": 61,
      "total": 125
    }
  },
  "family": {
    "asymmetric_pair_count": {
      "angular_valid": 107,
      "four_objective_eligible": 70,
      "shortlist_eligible": 7,
      "spectral_valid": 118,
      "total": 205
    },
    "dual_defect": {
      "angular_valid": 101,
      "four_objective_eligible": 68,
      "shortlist_eligible": 2,
      "spectral_valid": 121,
      "total": 203
    },
    "grouped_chirped": {
      "angular_valid": 89,
      "four_objective_eligible": 57,
      "shortlist_eligible": 5,
      "spectral_valid": 107,
      "total": 203
    },
    "hybrid_periodic_aperiodic": {
      "angular_valid": 88,
      "four_objective_eligible": 44,
      "shortlist_eligible": 13,
      "spectral_valid": 92,
      "total": 202
    },
    "locally_aperiodic": {
      "angular_valid": 108,
      "four_objective_eligible": 55,
      "shortlist_eligible": 12,
      "spectral_valid": 94,
      "total": 202
    },
    "off_center_defect": {
      "angular_valid": 244,
      "four_objective_eligible": 162,
      "shortlist_eligible": 32,
      "spectral_valid": 258,
      "total": 453
    },
    "symmetric_periodic": {
      "angular_valid": 154,
      "four_objective_eligible": 87,
      "shortlist_eligible": 24,
      "spectral_valid": 144,
      "total": 330
    },
    "termination_reversed": {
      "angular_valid": 109,
      "four_objective_eligible": 37,
      "shortlist_eligible": 8,
      "spectral_valid": 66,
      "total": 202
    }
  }
}
```

## PRE1_VS_FORMAL_DRIFT

```json
{
  "coverage_proportions": {
    "source_category": {
      "ANCHOR_NEIGHBORHOOD": {
        "formal": 0.1875,
        "pre1": 0.1875
      },
      "FAMILY_CHALLENGE": {
        "formal": 0.125,
        "pre1": 0.125
      },
      "FAMILY_STRATIFIED_GLOBAL": {
        "formal": 0.625,
        "pre1": 0.625
      },
      "RARE_CROSS_FAMILY": {
        "formal": 0.0625,
        "pre1": 0.0625
      }
    },
    "topology_family": {
      "asymmetric_pair_count": {
        "formal": 0.1025,
        "pre1": 0.1015625
      },
      "dual_defect": {
        "formal": 0.1015,
        "pre1": 0.1015625
      },
      "grouped_chirped": {
        "formal": 0.1015,
        "pre1": 0.1015625
      },
      "hybrid_periodic_aperiodic": {
        "formal": 0.101,
        "pre1": 0.1015625
      },
      "locally_aperiodic": {
        "formal": 0.101,
        "pre1": 0.1015625
      },
      "off_center_defect": {
        "formal": 0.2265,
        "pre1": 0.2265625
      },
      "symmetric_periodic": {
        "formal": 0.165,
        "pre1": 0.1640625
      },
      "termination_reversed": {
        "formal": 0.101,
        "pre1": 0.1015625
      }
    }
  },
  "metric_diagnostics": {
    "T450_unpolarized": {
      "formal_quantiles": {
        "max": 1.0011407212603527,
        "min": 1.682935197978963e-06,
        "p10": 0.0001842307453873584,
        "p25": 0.0030004937388069582,
        "p50": 0.031598979054758884,
        "p75": 0.45712608501572616,
        "p90": 0.8397152609952522
      },
      "ks_statistic": 0.050578124999999974,
      "pre1_quantiles": {
        "max": 1.0000791296228742,
        "min": 1.9402038052445463e-06,
        "p10": 0.00021409559688010123,
        "p25": 0.004901712393227448,
        "p50": 0.03905796683536358,
        "p75": 0.4994875825080268,
        "p90": 0.8522961211699162
      }
    },
    "cone5_integral_proxy": {
      "formal_quantiles": {
        "max": 0.17412345627840678,
        "min": 3.028385391034181e-07,
        "p10": 3.478611772699724e-05,
        "p25": 0.0005844452709867186,
        "p50": 0.0062287751624256,
        "p75": 0.07810415063887019,
        "p90": 0.14375710374884615
      },
      "ks_statistic": 0.05279687500000002,
      "pre1_quantiles": {
        "max": 0.1723395466289209,
        "min": 3.3906153820245526e-07,
        "p10": 3.869897828510789e-05,
        "p25": 0.0009005396530005516,
        "p50": 0.008276680314592767,
        "p75": 0.0862883568565241,
        "p90": 0.14728134823917088
      }
    },
    "layer_count": {
      "formal_quantiles": {
        "max": 25.0,
        "min": 9.0,
        "p10": 9.0,
        "p25": 12.0,
        "p50": 15.0,
        "p75": 21.0,
        "p90": 23.0
      },
      "ks_statistic": 0.015812500000000007,
      "pre1_quantiles": {
        "max": 25.0,
        "min": 9.0,
        "p10": 9.0,
        "p25": 12.0,
        "p50": 13.0,
        "p75": 19.0,
        "p90": 23.0
      }
    },
    "normal_band_transmission_proxy": {
      "formal_quantiles": {
        "max": 0.9976018104259549,
        "min": 1.7278472048030032e-06,
        "p10": 0.00019920987065318163,
        "p25": 0.003311056846170812,
        "p50": 0.03547313013159775,
        "p75": 0.45094946339552383,
        "p90": 0.8239548537379048
      },
      "ks_statistic": 0.05229687500000002,
      "pre1_quantiles": {
        "max": 0.9866118043642619,
        "min": 1.9462596969146065e-06,
        "p10": 0.0002193803409371145,
        "p25": 0.005151628039822147,
        "p50": 0.04615624717865495,
        "p75": 0.49972182310220586,
        "p90": 0.8427593108573485
      }
    },
    "secondary_peak_ratio": {
      "formal_quantiles": {
        "max": 0.9999919388398252,
        "min": 0.0,
        "p10": 0.0,
        "p25": 0.0,
        "p50": 0.023014498031848376,
        "p75": 0.7349001516461839,
        "p90": 0.9291690940972543
      },
      "ks_statistic": 0.024859375000000017,
      "pre1_quantiles": {
        "max": 0.9993202897185066,
        "min": 0.0,
        "p10": 0.0,
        "p25": 0.0,
        "p50": 0.012600090156945144,
        "p75": 0.7506509093594986,
        "p90": 0.943301976449047
      }
    },
    "total_thickness_nm": {
      "formal_quantiles": {
        "max": 2173.0,
        "min": 508.0,
        "p10": 869.0,
        "p25": 977.0,
        "p50": 1141.0,
        "p75": 1355.0,
        "p90": 1554.0
      },
      "ks_statistic": 0.03101562499999999,
      "pre1_quantiles": {
        "max": 2017.0,
        "min": 500.0,
        "p10": 867.0,
        "p25": 964.0,
        "p50": 1133.5,
        "p75": 1360.5,
        "p90": 1578.6000000000001
      }
    }
  },
  "note": "formal quota changes are intentional; no result-dependent deletion or resampling was applied",
  "sampler_drift_judgment": "NO_SEVERE_VALIDITY_DRIFT",
  "validity_rate_differences": {
    "angular_fwhm_valid": {
      "absolute_difference": 0.0,
      "formal": 0.5,
      "pre1": 0.5,
      "signed_difference": 0.0
    },
    "center_is_global_max": {
      "absolute_difference": 0.013765625000000004,
      "formal": 0.129,
      "pre1": 0.115234375,
      "signed_difference": 0.013765625000000004
    },
    "nominal_4d_objective_eligible": {
      "absolute_difference": 0.01664062500000002,
      "formal": 0.29,
      "pre1": 0.306640625,
      "signed_difference": -0.01664062500000002
    },
    "spectral_fwhm_valid": {
      "absolute_difference": 0.017578125,
      "formal": 0.5,
      "pre1": 0.517578125,
      "signed_difference": -0.017578125
    },
    "strong_secondary_peak_flag": {
      "absolute_difference": 0.006984374999999987,
      "formal": 0.327,
      "pre1": 0.333984375,
      "signed_difference": -0.006984374999999987
    }
  }
}
```

## OBJECTIVE_CORRELATION

```json
{
  "combined": {
    "angular_fwhm_450_deg": {
      "angular_fwhm_450_deg": 1.0,
      "cone5_integral_proxy": 0.7576693326239295,
      "normal_band_transmission_proxy": 0.7565264010832848,
      "spectral_fwhm_normal_nm": 0.7996463462079058
    },
    "cone5_integral_proxy": {
      "angular_fwhm_450_deg": 0.7576693326239294,
      "cone5_integral_proxy": 1.0,
      "normal_band_transmission_proxy": 0.9995521025087654,
      "spectral_fwhm_normal_nm": 0.7093733315656231
    },
    "normal_band_transmission_proxy": {
      "angular_fwhm_450_deg": 0.7565264010832848,
      "cone5_integral_proxy": 0.9995521025087654,
      "normal_band_transmission_proxy": 1.0,
      "spectral_fwhm_normal_nm": 0.7076779931438337
    },
    "spectral_fwhm_normal_nm": {
      "angular_fwhm_450_deg": 0.7996463462079058,
      "cone5_integral_proxy": 0.7093733315656231,
      "normal_band_transmission_proxy": 0.7076779931438337,
      "spectral_fwhm_normal_nm": 1.0
    }
  },
  "combined_leave_one_out": {
    "angular_fwhm_450_deg": {
      "pareto_size": 12,
      "sample_ids": [
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_011",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0009",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0026",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0028",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0073",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0117",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0005",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0140",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0021",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0138"
      ]
    },
    "cone5_integral_proxy": {
      "pareto_size": 71,
      "sample_ids": [
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_003",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_032",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_038",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_042",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_045",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_046",
        "F0_PRE1_CHALLENGE_ASYMMETRIC_PAIR_COUNT_007",
        "F0_PRE1_CHALLENGE_TERMINATION_REVERSED_007",
        "F0_PRE1_GLOBAL_DUAL_DEFECT_019",
        "F0_PRE1_GLOBAL_DUAL_DEFECT_029",
        "F0_PRE1_GLOBAL_GROUPED_CHIRPED_038",
        "F0_PRE1_GLOBAL_LOCALLY_APERIODIC_017",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_011",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_013",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_031",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_037",
        "F0_PRE1_GLOBAL_SYMMETRIC_PERIODIC_019",
        "F0_PRE1_GLOBAL_TERMINATION_REVERSED_037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0012",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0060",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0063",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0098",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0121",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0193",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0197",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0201",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0222",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0224",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0235",
        "F0_FORMAL_ANCHOR_SYMMETRIC_PERIODIC_0062",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_GROUPED_CHIRPED_0029",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0009",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0017",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0029",
        "F0_FORMAL_CHALLENGE_SYMMETRIC_PERIODIC_0022",
        "F0_FORMAL_CHALLENGE_TERMINATION_REVERSED_0022",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0026",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0031",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0079",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0117",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0120",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0143",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0152",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0005",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0050",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0061",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0081",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0100",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0102",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0103",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0140",
        "F0_FORMAL_GLOBAL_GROUPED_CHIRPED_0052",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0018",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0037",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0038",
        "F0_FORMAL_GLOBAL_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0018",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0021",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0034",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0072",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0091",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0100",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0138",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0037",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0069",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0144",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0006"
      ]
    },
    "normal_band_transmission_proxy": {
      "pareto_size": 74,
      "sample_ids": [
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_003",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_032",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_038",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_042",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_045",
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_046",
        "F0_PRE1_CHALLENGE_ASYMMETRIC_PAIR_COUNT_007",
        "F0_PRE1_CHALLENGE_TERMINATION_REVERSED_007",
        "F0_PRE1_GLOBAL_DUAL_DEFECT_019",
        "F0_PRE1_GLOBAL_DUAL_DEFECT_029",
        "F0_PRE1_GLOBAL_GROUPED_CHIRPED_038",
        "F0_PRE1_GLOBAL_LOCALLY_APERIODIC_017",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_011",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_013",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_031",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_037",
        "F0_PRE1_GLOBAL_TERMINATION_REVERSED_037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0012",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0060",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0062",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0063",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0121",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0151",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0193",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0197",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0201",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0222",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0224",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0230",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0235",
        "F0_FORMAL_ANCHOR_SYMMETRIC_PERIODIC_0062",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_GROUPED_CHIRPED_0029",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0009",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0017",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0029",
        "F0_FORMAL_CHALLENGE_SYMMETRIC_PERIODIC_0022",
        "F0_FORMAL_CHALLENGE_TERMINATION_REVERSED_0022",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0026",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0028",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0031",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0073",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0079",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0117",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0120",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0143",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0152",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0005",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0050",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0061",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0081",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0100",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0102",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0103",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0140",
        "F0_FORMAL_GLOBAL_GROUPED_CHIRPED_0052",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0018",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0037",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0038",
        "F0_FORMAL_GLOBAL_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0018",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0021",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0034",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0072",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0091",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0100",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0138",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0037",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0069",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0144",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0006"
      ]
    },
    "spectral_fwhm_normal_nm": {
      "pareto_size": 30,
      "sample_ids": [
        "F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_003",
        "F0_PRE1_CHALLENGE_ASYMMETRIC_PAIR_COUNT_007",
        "F0_PRE1_CHALLENGE_TERMINATION_REVERSED_007",
        "F0_PRE1_GLOBAL_LOCALLY_APERIODIC_017",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_011",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_013",
        "F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_031",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0063",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0098",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0151",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0193",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0201",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0222",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0224",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0235",
        "F0_FORMAL_ANCHOR_SYMMETRIC_PERIODIC_0062",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_GROUPED_CHIRPED_0029",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0017",
        "F0_FORMAL_CHALLENGE_SYMMETRIC_PERIODIC_0022",
        "F0_FORMAL_CHALLENGE_TERMINATION_REVERSED_0022",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0031",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0050",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0061",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0100",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0037",
        "F0_FORMAL_GLOBAL_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0144"
      ]
    }
  },
  "formal": {
    "angular_fwhm_450_deg": {
      "angular_fwhm_450_deg": 1.0,
      "cone5_integral_proxy": 0.7551657350535601,
      "normal_band_transmission_proxy": 0.7531074056858612,
      "spectral_fwhm_normal_nm": 0.795715234125039
    },
    "cone5_integral_proxy": {
      "angular_fwhm_450_deg": 0.7551657350535601,
      "cone5_integral_proxy": 1.0,
      "normal_band_transmission_proxy": 0.9995521237555011,
      "spectral_fwhm_normal_nm": 0.7061660505359094
    },
    "normal_band_transmission_proxy": {
      "angular_fwhm_450_deg": 0.7531074056858612,
      "cone5_integral_proxy": 0.9995521237555012,
      "normal_band_transmission_proxy": 1.0,
      "spectral_fwhm_normal_nm": 0.7036824746652052
    },
    "spectral_fwhm_normal_nm": {
      "angular_fwhm_450_deg": 0.795715234125039,
      "cone5_integral_proxy": 0.7061660505359094,
      "normal_band_transmission_proxy": 0.7036824746652052,
      "spectral_fwhm_normal_nm": 1.0
    }
  },
  "formal_leave_one_out": {
    "angular_fwhm_450_deg": {
      "pareto_size": 12,
      "sample_ids": [
        "F0_FORMAL_GLOBAL_SYMMETRIC_PERIODIC_0011",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0026",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0028",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0073",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0117",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0021",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0138",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0005",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0140",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0009"
      ]
    },
    "cone5_integral_proxy": {
      "pareto_size": 54,
      "sample_ids": [
        "F0_FORMAL_GLOBAL_SYMMETRIC_PERIODIC_0011",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0026",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0031",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0079",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0117",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0120",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0143",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0152",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0018",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0021",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0034",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0072",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0091",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0100",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0138",
        "F0_FORMAL_GLOBAL_GROUPED_CHIRPED_0052",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0005",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0050",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0061",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0081",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0100",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0102",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0103",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0140",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0037",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0069",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0144",
        "F0_FORMAL_GLOBAL_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0018",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0037",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0038",
        "F0_FORMAL_ANCHOR_SYMMETRIC_PERIODIC_0062",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0012",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0060",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0063",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0098",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0121",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0193",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0197",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0201",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0222",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0224",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0235",
        "F0_FORMAL_CHALLENGE_SYMMETRIC_PERIODIC_0022",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_GROUPED_CHIRPED_0029",
        "F0_FORMAL_CHALLENGE_TERMINATION_REVERSED_0022",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0009",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0017",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0029",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0006"
      ]
    },
    "normal_band_transmission_proxy": {
      "pareto_size": 59,
      "sample_ids": [
        "F0_FORMAL_GLOBAL_SYMMETRIC_PERIODIC_0011",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0026",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0028",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0031",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0073",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0079",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0117",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0120",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0143",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0152",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0018",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0021",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0034",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0072",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0091",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0100",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0138",
        "F0_FORMAL_GLOBAL_GROUPED_CHIRPED_0052",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0005",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0050",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0061",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0081",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0100",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0102",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0103",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0140",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0037",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0069",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0144",
        "F0_FORMAL_GLOBAL_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0018",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0037",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0038",
        "F0_FORMAL_ANCHOR_SYMMETRIC_PERIODIC_0062",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0012",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0060",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0062",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0063",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0098",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0121",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0151",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0193",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0197",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0201",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0222",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0224",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0230",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0235",
        "F0_FORMAL_CHALLENGE_SYMMETRIC_PERIODIC_0022",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_GROUPED_CHIRPED_0029",
        "F0_FORMAL_CHALLENGE_TERMINATION_REVERSED_0022",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0009",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0017",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0029",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0006"
      ]
    },
    "spectral_fwhm_normal_nm": {
      "pareto_size": 28,
      "sample_ids": [
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0026",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0031",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0073",
        "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0093",
        "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0091",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0050",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0061",
        "F0_FORMAL_GLOBAL_DUAL_DEFECT_0100",
        "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0144",
        "F0_FORMAL_GLOBAL_LOCALLY_APERIODIC_0005",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0037",
        "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0038",
        "F0_FORMAL_ANCHOR_SYMMETRIC_PERIODIC_0062",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0037",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0063",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0098",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0151",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0193",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0201",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0222",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0224",
        "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0235",
        "F0_FORMAL_CHALLENGE_SYMMETRIC_PERIODIC_0022",
        "F0_FORMAL_CHALLENGE_ASYMMETRIC_PAIR_COUNT_0001",
        "F0_FORMAL_CHALLENGE_GROUPED_CHIRPED_0029",
        "F0_FORMAL_CHALLENGE_TERMINATION_REVERSED_0022",
        "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0017",
        "F0_FORMAL_RARE_LOCALLY_APERIODIC_0005"
      ]
    }
  }
}
```

## PARETO

- Formal valid/Pareto `580/59`; combined `737/76`.

## INTERESTING_FORMAL_CANDIDATES

```json
[
  {
    "T450_TE": 0.9764993785750604,
    "T450_TM": 0.9764993785750604,
    "T450_unpolarized": 0.9764993785750604,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 33.79333114399005,
    "angular_fwhm_raw_deg": 33.79333114399005,
    "angular_fwhm_valid": true,
    "array_content_hash": "1c7a2cbcbff4772693d061f42641e04b0a8bab0949588c76ede82db10771e585",
    "artifact_bytes": 220903,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/0277_a6ddfb5c678aa6a3.npz",
    "artifact_sha256": "0f379b69d3c7435d0961374a5e112b3b01d9b805945b06c084a9b220c547c2eb",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "a6ddfb5c678aa6a3e9bb10811ee3cf89062a4638f8cdaff01493cf338ce0297a",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.25880407328313626,
    "cone10_integral_proxy": 0.27996784925228335,
    "cone5_fraction_proxy": 0.1338099175876258,
    "cone5_integral_proxy": 0.14475226127777469,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      6
    ],
    "finite_arrays": true,
    "layer_count": 15,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.07521772432174259,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.8374532300493003,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "fa5be7e91b2fc817dae01c836cc09c3378109d8de9615d59357ad316ec1bb082",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 1.627168208969281,
    "sample_id": "F0_FORMAL_GLOBAL_ASYMMETRIC_PAIR_COUNT_0120",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "477ca155edbe7c6cf053e44c4457a297ed7e1e2f9ead02d4a551b6d2270a51e0",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 6.7999999999999545,
    "spectral_fwhm_raw_nm": 6.7999999999999545,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      32,
      68,
      32,
      68,
      32,
      68,
      205,
      68,
      32,
      68,
      32,
      68,
      32,
      68,
      32
    ],
    "topology_family": "asymmetric_pair_count",
    "total_thickness_nm": 905,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.9764993785750604,
    "worker_runtime_seconds": 1.693312699906528
  },
  {
    "T450_TE": 0.9757277390900171,
    "T450_TM": 0.9757277390900171,
    "T450_unpolarized": 0.9757277390900171,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 38.36748707211559,
    "angular_fwhm_raw_deg": 38.36748707211559,
    "angular_fwhm_valid": true,
    "array_content_hash": "9d8a94449e640a23d9faa1acf6184b23ceeccbf939d7c206f814899f7ee25bb4",
    "artifact_bytes": 221719,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1132_24b791d024edafb1.npz",
    "artifact_sha256": "e4971895610d5177cca5e950ac77fdb586d507de0829bb5c075388dc8136a3ef",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "24b791d024edafb191ef9eaacdba8c26677b740e4a6153fc4fd8388b0eca644f",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.2754366502769565,
    "cone10_integral_proxy": 0.30795877485854795,
    "cone5_fraction_proxy": 0.14177240166103544,
    "cone5_integral_proxy": 0.1585121481850199,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      12
    ],
    "finite_arrays": true,
    "layer_count": 25,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.07781281894131097,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.9159100654942977,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "1a80ad2ddbc0d3923e0132170cab69fd72381ebf576eca7a1cb73829fd36d03e",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 1.741749510214479,
    "sample_id": "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0038",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "4408875568a9e5493b74578d869f70b3002a43835678362db90df338f51061a1",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 15.5,
    "spectral_fwhm_raw_nm": 15.5,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      37,
      53,
      43,
      47,
      37,
      53,
      43,
      47,
      37,
      53,
      43,
      47,
      152,
      53,
      37,
      53,
      37,
      53,
      37,
      53,
      37,
      53,
      37,
      53,
      37
    ],
    "topology_family": "hybrid_periodic_aperiodic",
    "total_thickness_nm": 1232,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.9757277390900171,
    "worker_runtime_seconds": 2.79595739999786
  },
  {
    "T450_TE": 0.9754230835840368,
    "T450_TM": 0.9754230835840368,
    "T450_unpolarized": 0.9754230835840368,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 29.617849379570888,
    "angular_fwhm_raw_deg": 29.617849379570888,
    "angular_fwhm_valid": true,
    "array_content_hash": "26cfc3c4f989d3d74dbafde571d88818a07f95bac6bfb494a261ce9dc17bf09c",
    "artifact_bytes": 222637,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/0943_4d7e0f9a52a136f4.npz",
    "artifact_sha256": "3270bbbb0c2ba5720c2f49d0e3bdd9787f121204f7eea29724f99585c40aa3b4",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "4d7e0f9a52a136f44f6f5eb6027bfa60b6a4000fd51aacf03656516eca94c2cd",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.5677050546898608,
    "cone10_integral_proxy": 0.2843132157175573,
    "cone5_fraction_proxy": 0.2972227148951568,
    "cone5_integral_proxy": 0.1488525514403069,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      6
    ],
    "finite_arrays": true,
    "layer_count": 13,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.06538051163008392,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.8639160635927438,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "9aea6f56f920910d49577043fd6bfe5c8598c7af4c6307cd75120e00ec939e07",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 58.25294487405345,
    "sample_id": "F0_FORMAL_GLOBAL_LOCALLY_APERIODIC_0005",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "8059d75c4351a4312ae3bc511b203d0df1348e731603478adc9e3c4d767aba17",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 9.5,
    "spectral_fwhm_raw_nm": 9.5,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      55,
      99,
      55,
      85,
      55,
      99,
      151,
      92,
      48,
      92,
      62,
      92,
      48
    ],
    "topology_family": "locally_aperiodic",
    "total_thickness_nm": 1033,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.9754230835840368,
    "worker_runtime_seconds": 1.7081832000985742
  },
  {
    "T450_TE": 0.9644902216580465,
    "T450_TM": 0.9644902216580465,
    "T450_unpolarized": 0.9644902216580465,
    "anchor_parent_id": "P1_ZL1_ALTERNATIVE_G3_A3",
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 16.122522130368836,
    "angular_fwhm_raw_deg": 16.122522130368836,
    "angular_fwhm_valid": true,
    "array_content_hash": "483d8148c7174bb77fa7225825f60830854ecccadf6d57627e9799906d04935e",
    "artifact_bytes": 223571,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1599_2232a0bab7bb2da5.npz",
    "artifact_sha256": "34b55daa9a131756a550567009b2a29cb338eac5f0adaafc3555740d29950580",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "2232a0bab7bb2da52919049795f9e66365e9503ef205d28f38749ca1b95d5793",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.7728727775803466,
    "cone10_integral_proxy": 0.1970167213291723,
    "cone5_fraction_proxy": 0.4404461489894981,
    "cone5_integral_proxy": 0.11227624870892808,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      5
    ],
    "finite_arrays": true,
    "layer_count": 12,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.04458333317297556,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.6611812180468393,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "d0e729d78b15362c62d3447f7d5919db2aa7c9edf4fd2f17f0b7c8ebeddd8080",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 63.48282863987525,
    "sample_id": "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0224",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "5292ca9edd963e88c0497297bcbc18ed7f71cf2d6de2712a25d12d4dcc4b93ba",
    "solver_valid": true,
    "source_category": "ANCHOR_NEIGHBORHOOD",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 3.6000000000000227,
    "spectral_fwhm_raw_nm": 3.6000000000000227,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "L",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      52,
      71,
      52,
      71,
      52,
      300,
      52,
      71,
      52,
      71,
      52,
      71
    ],
    "topology_family": "off_center_defect",
    "total_thickness_nm": 967,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.9644902216580465,
    "worker_runtime_seconds": 1.4018427999690175
  },
  {
    "T450_TE": 0.9622805376578297,
    "T450_TM": 0.9622805376578297,
    "T450_unpolarized": 0.9622805376578297,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 28.525694703793107,
    "angular_fwhm_raw_deg": 28.525694703793107,
    "angular_fwhm_valid": true,
    "array_content_hash": "0ed01a28ef5a1f4742f87a7ba4acf0b3f2bf54c090492cdf3c2f55ca90adc873",
    "artifact_bytes": 222346,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/0332_783f83a297f7f6f7.npz",
    "artifact_sha256": "b8b30f4a1ac83f46b5b819b34f534482533fd77dba41f3b06301190714201f5b",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "783f83a297f7f6f7fda410ea0df8990513da11a40098c880ff160f4aa6d63fb1",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.550783067288692,
    "cone10_integral_proxy": 0.2483682868755114,
    "cone5_fraction_proxy": 0.2851386711006285,
    "cone5_integral_proxy": 0.12857948522608292,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      6
    ],
    "finite_arrays": true,
    "layer_count": 15,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.07102409727717021,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.744264444133005,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "3554147b33dc0b3eaa705a45fd63a1a44e682368998c33304ba3ea66c1c85ae8",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 45.76030067987533,
    "sample_id": "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0018",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "6fb0d648a8446137d29a484a2a1f1b8112b24def34ec9c19c50ba144f6a86f2e",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 5.0,
    "spectral_fwhm_raw_nm": 5.0,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      68,
      56,
      68,
      56,
      68,
      56,
      173,
      56,
      68,
      56,
      68,
      56,
      68,
      56,
      68
    ],
    "topology_family": "off_center_defect",
    "total_thickness_nm": 1041,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.9622805376578297,
    "worker_runtime_seconds": 1.7093909997493029
  },
  {
    "T450_TE": 0.873711469842686,
    "T450_TM": 0.873711469842686,
    "T450_unpolarized": 0.873711469842686,
    "anchor_parent_id": "P1_ZL1_NOMINAL_G3_A3",
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 14.079548187668436,
    "angular_fwhm_raw_deg": 14.079548187668436,
    "angular_fwhm_valid": true,
    "array_content_hash": "43f6803abdb9edb69048a20bde44be94ff8c2ecd35532e598b47863a54c0d723",
    "artifact_bytes": 223580,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1473_9d9a38b89677a3df.npz",
    "artifact_sha256": "2a925525bf9e9b16c85f424dbe01d79601c1dceb8e67e67b4f5a0d5e48db0392",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "9d9a38b89677a3df887ea1e41a95ef7cbcded6d4555fb5014cf3775b011598e7",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.7939509577504574,
    "cone10_integral_proxy": 0.17181666341424093,
    "cone5_fraction_proxy": 0.4737434828050239,
    "cone5_integral_proxy": 0.1025214765914855,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      5
    ],
    "finite_arrays": true,
    "layer_count": 12,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.04599371145391916,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.6116071577178585,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "968d124883b023aaa84d99cc44189f392a1ee6a0560f621b8f6805290fa4538a",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 44.8107706094129,
    "sample_id": "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0098",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "f80421fa2e4a04bc442f4bc4a14bcfdb91999992a510746bd3cab7485d79e988",
    "solver_valid": true,
    "source_category": "ANCHOR_NEIGHBORHOOD",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 3.1999999999999886,
    "spectral_fwhm_raw_nm": 3.1999999999999886,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "L",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      43,
      83,
      43,
      83,
      43,
      315,
      43,
      83,
      43,
      83,
      43,
      83
    ],
    "topology_family": "off_center_defect",
    "total_thickness_nm": 988,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.873711469842686,
    "worker_runtime_seconds": 1.5946929003112018
  },
  {
    "T450_TE": 0.8541348346458969,
    "T450_TM": 0.8541348346458969,
    "T450_unpolarized": 0.8541348346458969,
    "anchor_parent_id": "P1_EXPLICIT_FAB_G3_A3",
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 23.377363680455204,
    "angular_fwhm_raw_deg": 23.377363680455204,
    "angular_fwhm_valid": true,
    "array_content_hash": "8c0d364459d78dfea2edab80251fd78a23472d23267ccb376d7d203c210aeec5",
    "artifact_bytes": 222431,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1312_e48aabf66748d13d.npz",
    "artifact_sha256": "e9eb959bd8fdc98355c1897f3bbcae2437107b3ed9a42c797f8313df80f7ab6d",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "e48aabf66748d13d66fae28c7a17db6a7bbbe36d2466ea077f279899f4951d5a",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.6374010483609391,
    "cone10_integral_proxy": 0.23312479239804973,
    "cone5_fraction_proxy": 0.34857734258453243,
    "cone5_integral_proxy": 0.12748962499143393,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      6
    ],
    "finite_arrays": true,
    "layer_count": 13,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.055803419082505926,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.7492092645701643,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "b3b8e46e8e6a82c7e829038be016649711f71f89afa5abf8f2c6b70fe9012704",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 51.71117829422145,
    "sample_id": "F0_FORMAL_ANCHOR_SYMMETRIC_PERIODIC_0062",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "dd3d48e83fa310b3183abb23258e74b85b616f8b82dbdf6e5cc0ef979610642c",
    "solver_valid": true,
    "source_category": "ANCHOR_NEIGHBORHOOD",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 7.899999999999977,
    "spectral_fwhm_raw_nm": 7.899999999999977,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "L",
      "gan_side": "L"
    },
    "thickness_sequence_nm": [
      95,
      42,
      95,
      42,
      95,
      42,
      150,
      42,
      95,
      42,
      95,
      42,
      95
    ],
    "topology_family": "symmetric_periodic",
    "total_thickness_nm": 972,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.8541348346458969,
    "worker_runtime_seconds": 1.6002827999182045
  },
  {
    "T450_TE": 0.8149577744770299,
    "T450_TM": 0.8149577744770299,
    "T450_unpolarized": 0.8149577744770299,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 21.99740717664162,
    "angular_fwhm_raw_deg": 21.99740717664162,
    "angular_fwhm_valid": true,
    "array_content_hash": "94c6c161dd09daab06c369600797921fa3282c20f014f36c74958d0c6741b2d1",
    "artifact_bytes": 223340,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1112_2bbeec2eeddc2d36.npz",
    "artifact_sha256": "f2a9233349fcb419c7204ade01ba83053281ffb89135ed582eaf43dfd91adf0b",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "2bbeec2eeddc2d36b68fbbb7513f0afe09c9b345fd5ea12f3e9803344219ff73",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.5556348348842444,
    "cone10_integral_proxy": 0.17546022616951565,
    "cone5_fraction_proxy": 0.2904007396382829,
    "cone5_integral_proxy": 0.09170371664574085,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      6
    ],
    "finite_arrays": true,
    "layer_count": 13,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.060153186857555066,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.5324175480506742,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "be625659a38d5106da87e2a00c6bff09d856e692a96647d04fbf511404ca472d",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 19.194775727872734,
    "sample_id": "F0_FORMAL_GLOBAL_HYBRID_PERIODIC_APERIODIC_0018",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "eb305f10fc5631e62151047eebbb21c651a7249c56452ff7b37265c760f36328",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 3.0,
    "spectral_fwhm_raw_nm": 3.0,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      55,
      55,
      62,
      48,
      55,
      55,
      278,
      55,
      55,
      55,
      55,
      55,
      55
    ],
    "topology_family": "hybrid_periodic_aperiodic",
    "total_thickness_nm": 938,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.8149577744770299,
    "worker_runtime_seconds": 1.6363999997265637
  },
  {
    "T450_TE": 0.7862015985536106,
    "T450_TM": 0.7862015985536106,
    "T450_unpolarized": 0.7862015985536106,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 12.652628178234119,
    "angular_fwhm_raw_deg": 12.652628178234119,
    "angular_fwhm_valid": true,
    "array_content_hash": "5a32c21f535cc273ad72128b53d331c460ab0a367da2574c1ba5ebc91221dc73",
    "artifact_bytes": 222561,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1873_743db97fd75433d5.npz",
    "artifact_sha256": "a0e26b9c26fbf3fcd3f293e6a45fc9d902246adaeebdd30ea94a7cf7d23c0c83",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "743db97fd75433d5540c041b2579a04472cbc9ebad3eaa9a3220c527d21de37e",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.4597452691579258,
    "cone10_integral_proxy": 0.0863683506210942,
    "cone5_fraction_proxy": 0.23537077942886966,
    "cone5_integral_proxy": 0.044217064029624255,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      8
    ],
    "finite_arrays": true,
    "layer_count": 17,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.0835603834663109,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.25480874635790196,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "74cc2aa5fc6ebd3c9ffd9a9db3e849bfc31d06304b2be95cc46c247ee0d51232",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 4.626633570926678,
    "sample_id": "F0_FORMAL_CHALLENGE_HYBRID_PERIODIC_APERIODIC_0029",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "ef228e8894417bbc0fd1591a31383d61116891ce20327dfc79ec6560e9d085c4",
    "solver_valid": true,
    "source_category": "FAMILY_CHALLENGE",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 1.099999999999966,
    "spectral_fwhm_raw_nm": 1.099999999999966,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      33,
      83,
      37,
      79,
      33,
      83,
      37,
      79,
      273,
      83,
      33,
      83,
      33,
      83,
      33,
      83,
      33
    ],
    "topology_family": "hybrid_periodic_aperiodic",
    "total_thickness_nm": 1201,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.7862015985536106,
    "worker_runtime_seconds": 2.1578138996846974
  },
  {
    "T450_TE": 0.6292276535099128,
    "T450_TM": 0.6292276535099128,
    "T450_unpolarized": 0.6292276535099128,
    "anchor_parent_id": "P1_ZL1_NOMINAL_G3_A3",
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 14.056800665371659,
    "angular_fwhm_raw_deg": 14.056800665371659,
    "angular_fwhm_valid": true,
    "array_content_hash": "5d63425e6f56c591c94fe11e3d851abab634c576e18f2651eb3b9ac21778c236",
    "artifact_bytes": 223595,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1387_bb6fa9bc10610339.npz",
    "artifact_sha256": "5de6872e92eb0454273aa770263bcd88fe32d2c45b3ac653e8bbc0ed1238ca68",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "bb6fa9bc106103391eb0b82bbe0fc6bef891e6b8d9e9798d4f97a23af3ba3e94",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.7834778628357186,
    "cone10_integral_proxy": 0.1416954718795993,
    "cone5_fraction_proxy": 0.4871260707393342,
    "cone5_integral_proxy": 0.08809892625228907,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      5
    ],
    "finite_arrays": true,
    "layer_count": 12,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.04501433990507914,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.5394795021449069,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "260aa1537b07c27a2ed8cca16b8ceac1b8633c3dfb18704645eab8a9a2935a6a",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 38.462395403713856,
    "sample_id": "F0_FORMAL_ANCHOR_OFF_CENTER_DEFECT_0012",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "2956d996e00649b02cd051ff300980e2f7a85e67fbee0ef71b18a7d37b17edc2",
    "solver_valid": true,
    "source_category": "ANCHOR_NEIGHBORHOOD",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 3.3999999999999773,
    "spectral_fwhm_raw_nm": 3.3999999999999773,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "L",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      49,
      75,
      49,
      75,
      49,
      304,
      49,
      75,
      49,
      75,
      49,
      75
    ],
    "topology_family": "off_center_defect",
    "total_thickness_nm": 973,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.6292276535099128,
    "worker_runtime_seconds": 1.4488551001995802
  },
  {
    "T450_TE": 0.6208881019031405,
    "T450_TM": 0.6208881019031405,
    "T450_unpolarized": 0.6208881019031405,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 18.3320475781079,
    "angular_fwhm_raw_deg": 18.3320475781079,
    "angular_fwhm_valid": true,
    "array_content_hash": "8bdcaea5e4b87239f1e4cafdd72f442d8a759d8d3d87a80f0cdb5a19a2551e7d",
    "artifact_bytes": 224037,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1976_9e9da835d81ba5db.npz",
    "artifact_sha256": "424e89725ea3407b3c8c85175af2ba9f44151407d80c68e03a906d82070deca7",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "9e9da835d81ba5db2bfcdb83e7a13b3a45538690175d759b1c8f41b441c79bd8",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.6827755231780976,
    "cone10_integral_proxy": 0.1470330419776466,
    "cone5_fraction_proxy": 0.3767431068767578,
    "cone5_integral_proxy": 0.0811301564976433,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      6
    ],
    "finite_arrays": true,
    "layer_count": 13,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.05669478696833674,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.4787385639490848,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "d03bb1006022ff4723c1fb8a4cdc3dbff742a8105f764dc69190c15232ba815c",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 49.87020518076376,
    "sample_id": "F0_FORMAL_RARE_LOCALLY_APERIODIC_0006",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "5e42017093311824be8c3af8c45f4f438c24ab950e70850119a916264aa679ed",
    "solver_valid": true,
    "source_category": "RARE_CROSS_FAMILY",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 3.0,
    "spectral_fwhm_raw_nm": 3.0,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      47,
      97,
      47,
      81,
      47,
      97,
      253,
      89,
      39,
      89,
      55,
      89,
      39
    ],
    "topology_family": "locally_aperiodic",
    "total_thickness_nm": 1069,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.6208881019031405,
    "worker_runtime_seconds": 1.5852867998182774
  },
  {
    "T450_TE": 0.4679172820622953,
    "T450_TM": 0.4679172820622953,
    "T450_unpolarized": 0.4679172820622953,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 13.201211102501432,
    "angular_fwhm_raw_deg": 13.201211102501432,
    "angular_fwhm_valid": true,
    "array_content_hash": "2519da8c914c969384e32246fb51e30792b104770f0b22482718ce40f85add4e",
    "artifact_bytes": 223351,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/0631_0583f6d350004e73.npz",
    "artifact_sha256": "8258ac09162e9b454759dcba8d2cf425e5340bc241378af5dd6ce42ed44dc292",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "0583f6d350004e730062e9b77e67740f30a70061e2770a6ed5228fc73fe1ada1",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.624676181864325,
    "cone10_integral_proxy": 0.08747298315413482,
    "cone5_fraction_proxy": 0.32625264202681414,
    "cone5_integral_proxy": 0.04568493675368239,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      6,
      8
    ],
    "finite_arrays": true,
    "layer_count": 15,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.07731061401413244,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.26457017272134375,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "dd706081b7d9d3e31d5a80fb486456b5babc92e0d0d1b13cd80fc67d8481557e",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 10.033008015321776,
    "sample_id": "F0_FORMAL_GLOBAL_DUAL_DEFECT_0005",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "6064b17e46a26458ad59bdb358a0a73f49556f2fb7323b391ecc981c70391cbf",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 0.6000000000000227,
    "spectral_fwhm_raw_nm": 0.6000000000000227,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      41,
      71,
      41,
      71,
      41,
      71,
      346,
      71,
      347,
      71,
      41,
      71,
      41,
      71,
      41
    ],
    "topology_family": "dual_defect",
    "total_thickness_nm": 1436,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.4679172820622953,
    "worker_runtime_seconds": 1.9041361003182828
  },
  {
    "T450_TE": 0.4573338939735291,
    "T450_TM": 0.4573338939735291,
    "T450_unpolarized": 0.4573338939735291,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 8.362815671370283,
    "angular_fwhm_raw_deg": 8.362815671370283,
    "angular_fwhm_valid": true,
    "array_content_hash": "f80048f78e41e592ea2d337133c8f8aecbff7d6b5aceffc0df461eab2763090d",
    "artifact_bytes": 224611,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/0851_305b4132c6ae4c29.npz",
    "artifact_sha256": "148be3233468f4e51ec7bd65a407ee2c95dde4b230dd1b567e89044da3224231",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "305b4132c6ae4c294cff946ef807f601f641a811220ac96ec257fb0c592ca269",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.9348326929137218,
    "cone10_integral_proxy": 0.07341756245292316,
    "cone5_fraction_proxy": 0.5805082228478555,
    "cone5_integral_proxy": 0.04559050943386437,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      10
    ],
    "finite_arrays": true,
    "layer_count": 21,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.07580481927919672,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.26819100598522827,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "d590544c04ad833870746f5af0f597c46ffa1d3daed9b579f935da541e1a1e06",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 738.0482275942327,
    "sample_id": "F0_FORMAL_GLOBAL_TERMINATION_REVERSED_0069",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "f3c77b5b6c929835296e222cc3ba0dd50e44e64f61e3ea8980a2324730eeb7d0",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 1.1000000000000227,
    "spectral_fwhm_raw_nm": 1.1000000000000227,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "L",
      "gan_side": "L"
    },
    "thickness_sequence_nm": [
      81,
      54,
      81,
      54,
      81,
      54,
      81,
      54,
      81,
      54,
      281,
      54,
      81,
      54,
      81,
      54,
      81,
      54,
      81,
      54,
      81
    ],
    "topology_family": "termination_reversed",
    "total_thickness_nm": 1631,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.4573338939735291,
    "worker_runtime_seconds": 2.4574079997837543
  },
  {
    "T450_TE": 0.11265425224501754,
    "T450_TM": 0.11265425224501754,
    "T450_unpolarized": 0.11265425224501754,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 9.974799453480482,
    "angular_fwhm_raw_deg": 9.974799453480482,
    "angular_fwhm_valid": true,
    "array_content_hash": "92c1dd3aa210eaf4786d45f226c49c987e9cc35a8386de0d8310ebf96ad9aa47",
    "artifact_bytes": 225583,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/0452_5d32f547768a4ae4.npz",
    "artifact_sha256": "4d6eaaea81af0a423a517ff8060366b266c8ca6ca918693dc014ef0bd8d2c7ba",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "5d32f547768a4ae41d67a92c27a538cd436dc6bba50f790da44a000bfcb6a097",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.856846761941762,
    "cone10_integral_proxy": 0.04453241183299287,
    "cone5_fraction_proxy": 0.4497766047626308,
    "cone5_integral_proxy": 0.02337598493194295,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      8
    ],
    "finite_arrays": true,
    "layer_count": 19,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.057561246146198106,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.14095153523760282,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "2cb216ee981f0490368918aeff079345a1def3d3f7100f350802ccafd18035d2",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 26.497161310559104,
    "sample_id": "F0_FORMAL_GLOBAL_OFF_CENTER_DEFECT_0138",
    "schema_valid": true,
    "secondary_peak_angle_deg": null,
    "secondary_peak_count": 0,
    "secondary_peak_ratio": 0.0,
    "secondary_peak_value": 0.0,
    "shortlist_quality_eligible": true,
    "simulation_provenance_hash": "f20d0951fd73bc0094e78e664949263f85d5a96b1c715295a0ff0beef6863ee0",
    "solver_valid": true,
    "source_category": "FAMILY_STRATIFIED_GLOBAL",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 0.39999999999997726,
    "spectral_fwhm_raw_nm": 0.39999999999997726,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": false,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      48,
      75,
      48,
      75,
      48,
      75,
      48,
      75,
      177,
      75,
      48,
      75,
      48,
      75,
      48,
      75,
      48,
      75,
      48
    ],
    "topology_family": "off_center_defect",
    "total_thickness_nm": 1284,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.11265425224501754,
    "worker_runtime_seconds": 2.3913352000527084
  },
  {
    "T450_TE": 0.9055898932751911,
    "T450_TM": 0.9055898932751911,
    "T450_unpolarized": 0.9055898932751911,
    "anchor_parent_id": null,
    "angular_boundary_clipped": false,
    "angular_fwhm_450_deg": 34.35763733232364,
    "angular_fwhm_raw_deg": 34.35763733232364,
    "angular_fwhm_valid": true,
    "array_content_hash": "d963f673e20d4b1e4c69eafa5d84d8463e55694473179c4db2a666be48c2b3a3",
    "artifact_bytes": 222208,
    "artifact_path": "outputs/mdc_ml_f0_formal_pilot_2000_v1/formal/artifacts/1749_3c65ee989495649a.npz",
    "artifact_sha256": "c1d5e2d19886f64fcc5f08010b72475c651695ebf02ed9490b41908542aca52e",
    "artifact_valid": true,
    "calibration_only_declaration": "formal TMM pilot candidate only; not an FDTD, manufacturing-robust, or final design",
    "canonical_geometry_hash": "3c65ee989495649aa451cf9623f64bc677982ce5347c571959be55645d21d34b",
    "center_is_global_max": true,
    "center_to_global_ratio": 1.0,
    "cone10_fraction_proxy": 0.4578579530525204,
    "cone10_integral_proxy": 0.29237006715131736,
    "cone5_fraction_proxy": 0.2352983272053526,
    "cone5_integral_proxy": 0.15025225021641214,
    "continuous_regression_target_mask": {
      "T450_unpolarized": true,
      "angular_fwhm_450_deg": true,
      "cone5_integral_proxy": true,
      "normal_band_transmission_proxy": true,
      "spectral_fwhm_normal_nm": true
    },
    "defect_indices": [
      8
    ],
    "finite_arrays": true,
    "layer_count": 17,
    "low_band_proxy_flag": false,
    "low_t450_flag": false,
    "material_sequence": [
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1",
      "APCD_SIO2_NATIVE_M1",
      "APCD_TIO2_NATIVE_M1"
    ],
    "max_abs_far_field_balance_offset": 0.071204419391982,
    "maximum_angle_set_deg": [
      0.0
    ],
    "nominal_4d_objective_eligible": true,
    "normal_band_transmission_proxy": 0.8669681188815416,
    "pareto_status": "non_dominated",
    "peak_angle_zero_compatible": true,
    "physical_configuration_hash": "9d7e9d8af485bc8d72b364adc6a567a2ba775a85b044d492064691b4cbf862d2",
    "power_balance_failure": false,
    "power_balance_tolerance": 0.001,
    "quality_mask_contract_id": "post_TMM_objective_eligibility_mask_v1",
    "ratio": 5.903335614868941,
    "sample_id": "F0_FORMAL_CHALLENGE_GROUPED_CHIRPED_0029",
    "schema_valid": true,
    "secondary_peak_angle_deg": 59.0,
    "secondary_peak_count": 4,
    "secondary_peak_ratio": 0.5488111296768715,
    "secondary_peak_value": 0.4969978123523151,
    "shortlist_quality_eligible": false,
    "simulation_provenance_hash": "2eaf86cfc5f401fe84bf899bd98bcdf03e51886aac3496bcd60cd4b0a617c339",
    "solver_valid": true,
    "source_category": "FAMILY_CHALLENGE",
    "spectral_boundary_clipped": false,
    "spectral_fwhm_normal_nm": 20.30000000000001,
    "spectral_fwhm_raw_nm": 20.30000000000001,
    "spectral_fwhm_valid": true,
    "strong_secondary_peak_flag": true,
    "symmetric_peak_pair": false,
    "termination": {
      "air_side": "H",
      "gan_side": "H"
    },
    "thickness_sequence_nm": [
      54,
      100,
      60,
      97,
      57,
      103,
      54,
      100,
      362,
      100,
      54,
      103,
      57,
      97,
      60,
      100,
      54
    ],
    "topology_family": "grouped_chirped",
    "total_thickness_nm": 1612,
    "transmission_above_unity_excess": 0.0,
    "transmission_above_unity_flag": false,
    "transmission_raw": 0.9055898932751911,
    "worker_runtime_seconds": 2.27053610002622
  }
]
```

These are formal TMM pilot candidates only, not FDTD, manufacturing-robust, or final designs.

## RUNTIME_AND_STORAGE

```json
{
  "artifact_bytes": 444622365,
  "artifact_files": 2000,
  "hard_gate_exceeded": false,
  "hard_limit_bytes": 838860800,
  "metadata_bytes": 91351652,
  "output_files": 4031,
  "soft_gate_exceeded": false,
  "soft_limit_bytes": 734003200,
  "total_bytes": 535974017
}
```

## TRAINING_READINESS

```json
{
  "artifact_complete": true,
  "automatic_training_or_expansion_started": false,
  "combined_4d_eligible": 737,
  "combined_per_family_eligible": {
    "asymmetric_pair_count": 83,
    "dual_defect": 87,
    "grouped_chirped": 71,
    "hybrid_periodic_aperiodic": 62,
    "locally_aperiodic": 67,
    "off_center_defect": 209,
    "symmetric_periodic": 106,
    "termination_reversed": 52
  },
  "combined_strict_shortlist": 131,
  "decision": "READY_SHARED_SURROGATE",
  "ready_shared_surrogate": true,
  "need_5000_before_training": false,
  "recommended_next_stage": "SHARED_SURROGATE_V1",
  "classification_population": 2512,
  "continuous_regression_population": 737,
  "formal_4d_eligible": 580,
  "formal_strict_shortlist": 103,
  "model_contract_if_ready": "shared model with family embedding/one-hot, validity classification head, and masked continuous regression heads",
  "validity_label_negative": 1775,
  "validity_label_positive": 737
}
```

## TESTS

- Generated-output validation, combined rebuild/signature, artifact SHA/array/schema audits and repository regressions are reported in the task handoff.

## GIT

- HEAD remains `143dd6a49a4eaa04a74fba03f195c4ebbedacfbd`; no stage/commit/push; outputs ignored.

## DECLARATION

- Generated 2,000 new legal unique candidates and completed their Native-M1 TMM responses; built a 2,512-reference registry; no pre-TMM performance filtering; no frozen-file edit; no 5,000 expansion, FDTD/Lumerical start, ML training, tolerance sweep, or Level-B generation.

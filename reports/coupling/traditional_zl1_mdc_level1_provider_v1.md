# Traditional ZL-1 MDC Level-1 real FDTD provider v1

## 状态

PASS: all six formal 2D Native-M1 FDTD cases completed once; no replay.

## P/S MDC provider

- P-family: TOP_X, CENTROID_X, BOTTOM_X -> raw aggregation -> normalization.
- S-family: TOP_Z, CENTROID_Z, BOTTOM_Z -> raw aggregation -> normalization.
- `source_orientation` and `interface_polarization_family` remain separate fields.
- NP P/S operator must act before x/z incoherent aggregation.

## ux support

frozen native grid: 420–480 nm, 301 points, 2000-point nonuniform theta grid; formal coupling support is conditioned to 445–455 nm.

```json
{
  "P": {
    "asymmetric_99_percent_interval": {
      "ux_max": 0.9945086101656629,
      "ux_min": -0.9945086101656628
    },
    "band_nm": [
      445.0,
      455.0
    ],
    "denominator_raw_integral": 2.5651319251064105e-06,
    "mean_ux": -7.08224842660421e-09,
    "negative_mass": 0.5000000118656973,
    "positive_mass": 0.4999999881343027,
    "support": {
      "symmetric_50_percent": {
        "captured_mass": 0.49971941396981717,
        "u_abs": 0.17908956792351438
      },
      "symmetric_90_percent": {
        "captured_mass": 0.9005000717544195,
        "u_abs": 0.898449807733072
      },
      "symmetric_95_percent": {
        "captured_mass": 0.95035454561412,
        "u_abs": 0.9544785809644698
      },
      "symmetric_99_percent": {
        "captured_mass": 0.9895599839767928,
        "u_abs": 0.9945086101656628
      }
    },
    "ux_mass_closure": 1.0
  },
  "S": {
    "asymmetric_99_percent_interval": {
      "ux_max": 0.5912957615838054,
      "ux_min": -0.5912957615838053
    },
    "band_nm": [
      445.0,
      455.0
    ],
    "denominator_raw_integral": 2.022779138400822e-06,
    "mean_ux": 3.1827008251106292e-09,
    "negative_mass": 0.499999985684319,
    "positive_mass": 0.5000000143156811,
    "support": {
      "symmetric_50_percent": {
        "captured_mass": 0.49852001866980106,
        "u_abs": 0.1400700528945287
      },
      "symmetric_90_percent": {
        "captured_mass": 0.9001549179729125,
        "u_abs": 0.3071536192245955
      },
      "symmetric_95_percent": {
        "captured_mass": 0.9501672964388004,
        "u_abs": 0.37818914976600054
      },
      "symmetric_99_percent": {
        "captured_mass": 0.9900268058513496,
        "u_abs": 0.5912957615838053
      }
    },
    "ux_mass_closure": 1.0
  }
}
```

## Quality / provenance

- Grid SHA256: `f3e2b786901c912240ea0267886d4ea9d9e5c62b78846bf1428dbed3c25a0ac9`; tensor shape: `301×2000`; theta-to-ux remap is conservative and no-extrapolation.
- Geometry: `P1_ZL1_ALTERNATIVE_G3_A3`, 975 nm, reference plane z=975 nm; no 237 nm spacer and no NP geometry.
- Provider manifest: `D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\outputs\coupling\traditional_zl1_mdc_level1_real_fdtd_v1\queued_20260810T000000Z\provider_manifest.json`.

## Safety / tests / Git

- Solver counts: 2D FDTD=6; NP=0; integrated 3D=0; TMM=0; RCWA=0; FEM=0; training=0; ML=0; replay=0.
- Raw FSP/tensor runtime artifacts remain outside Git.

## 下一步

REQUEST_NP_LEVEL1_PS_UX_GRID_SOLVER_AUTHORIZATION

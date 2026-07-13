# MDC Design Space Coverage Audit V1B

This is an actionable, read-only-derived patch. It does not add simulations, candidates to the canonical database, or a new physical score.

## OUTPUT_PATH_SAFETY
- Current audit files are confined to `outputs/mdc_design_space_coverage_audit_v1/`.
- The current `nominal_identity_summary.json` and frozen semantic-audit counterpart have distinct paths and distinct SHA256 values; neither historical frozen file was overwritten.

## PARAMETER_COVERAGE_DETAILS
```json
{
  "Explicit": {
    "rows": 1848,
    "by_N": {
      "2": 462,
      "3": 462,
      "4": 462,
      "5": 462
    },
    "by_H_nm": {
      "42": 308,
      "43": 308,
      "44": 308,
      "45": 308,
      "46": 308,
      "47": 308
    },
    "by_L_nm": {
      "76": 264,
      "77": 264,
      "78": 264,
      "79": 264,
      "80": 264,
      "81": 264,
      "82": 264
    },
    "FAB_by_N": {
      "3": 3
    },
    "PERF_by_N": {
      "5": 3
    },
    "by_C_nm": {
      "152": 168,
      "153": 168,
      "154": 168,
      "155": 168,
      "156": 168,
      "157": 168,
      "158": 168,
      "159": 168,
      "160": 168,
      "161": 168,
      "162": 168
    },
    "theoretical_HxLxCxN": 1848,
    "actual_HxLxCxN": 1848,
    "refined_only_combinations": 0,
    "missing_combinations": 0
  },
  "ZL-1": {
    "rows": 630,
    "by_N": {
      "2": 126,
      "3": 126,
      "4": 126,
      "5": 126,
      "6": 126
    },
    "by_H_nm": {
      "42": 105,
      "43": 105,
      "44": 105,
      "45": 105,
      "46": 105,
      "47": 105
    },
    "by_L_nm": {
      "76": 90,
      "77": 90,
      "78": 90,
      "79": 90,
      "80": 90,
      "81": 90,
      "82": 90
    },
    "FAB_by_N": {
      "3": 3
    },
    "PERF_by_N": {
      "3": 1
    },
    "by_M": {
      "1": 210,
      "3": 210,
      "5": 210
    },
    "effective_center_nm": {
      "min": 152.0,
      "max": 492.0,
      "unique_count": 21,
      "values": [
        152.0,
        154.0,
        156.0,
        158.0,
        160.0,
        162.0,
        164.0,
        304.0,
        308.0,
        312.0,
        316.0,
        320.0,
        324.0,
        328.0,
        456.0,
        462.0,
        468.0,
        474.0,
        480.0,
        486.0,
        492.0
      ],
      "same_effective_multiple_ML": {}
    },
    "FAB_by_M": {
      "1": 3
    },
    "PERF_by_M": {
      "3": 1
    }
  },
  "ZL-2": {
    "rows": 210,
    "by_N": {
      "2": 42,
      "3": 42,
      "4": 42,
      "5": 42,
      "6": 42
    },
    "by_H_nm": {
      "42": 35,
      "43": 35,
      "44": 35,
      "45": 35,
      "46": 35,
      "47": 35
    },
    "by_L_nm": {
      "76": 30,
      "77": 30,
      "78": 30,
      "79": 30,
      "80": 30,
      "81": 30,
      "82": 30
    },
    "FAB_by_N": {
      "3": 3
    },
    "PERF_by_N": {},
    "effective_center_nm": {
      "values": [
        152.0,
        154.0,
        156.0,
        158.0,
        160.0,
        162.0,
        164.0
      ],
      "unique_count": 7
    },
    "actual_HxLxN": 210
  }
}
```

- Explicit theoretical H×L×C×N=1848 and actual=1848; missing=0; refined-only=0.

## GLOBAL_PARETO_DIAGNOSIS
- The prior global high-dimensional Pareto result (`2688` non-dominated) is retained as a fact but explicitly marked **non_actionable**. More objectives than useful ordering dimensions made it ineffective.
- `edge_stability=min(T448,T453)` is a conservative derived edge-band transmission, not a weighted composite score.
- Actionable views: FWHM(min) versus T450(max), edge_stability(max), layer_count(min), and total_thickness(min), globally and within topology/topology×N.

## ACTIONABLE_CANDIDATE_POOLS
```json
{
  "FAB": {
    "count": 9,
    "by_topology_N": {
      "Explicit|N=2": 0,
      "Explicit|N=3": 3,
      "Explicit|N=4": 0,
      "Explicit|N=5": 0,
      "ZL-1|N=2": 0,
      "ZL-1|N=3": 3,
      "ZL-1|N=4": 0,
      "ZL-1|N=5": 0,
      "ZL-1|N=6": 0,
      "ZL-2|N=2": 0,
      "ZL-2|N=3": 3,
      "ZL-2|N=4": 0,
      "ZL-2|N=5": 0,
      "ZL-2|N=6": 0
    },
    "two_dimensional_pareto_counts": {
      "fwhm_vs_T450": 3,
      "fwhm_vs_edge_stability": 6,
      "fwhm_vs_layer_count": 2,
      "fwhm_vs_total_thickness": 2
    }
  },
  "PERF": {
    "count": 4,
    "by_topology_N": {
      "Explicit|N=2": 0,
      "Explicit|N=3": 0,
      "Explicit|N=4": 0,
      "Explicit|N=5": 3,
      "ZL-1|N=2": 0,
      "ZL-1|N=3": 1,
      "ZL-1|N=4": 0,
      "ZL-1|N=5": 0,
      "ZL-1|N=6": 0,
      "ZL-2|N=2": 0,
      "ZL-2|N=3": 0,
      "ZL-2|N=4": 0,
      "ZL-2|N=5": 0,
      "ZL-2|N=6": 0
    },
    "two_dimensional_pareto_counts": {
      "fwhm_vs_T450": 3,
      "fwhm_vs_edge_stability": 4,
      "fwhm_vs_layer_count": 2,
      "fwhm_vs_total_thickness": 4
    }
  },
  "combined": {
    "count": 13,
    "by_topology_N": {
      "Explicit|N=2": 0,
      "Explicit|N=3": 3,
      "Explicit|N=4": 0,
      "Explicit|N=5": 3,
      "ZL-1|N=2": 0,
      "ZL-1|N=3": 4,
      "ZL-1|N=4": 0,
      "ZL-1|N=5": 0,
      "ZL-1|N=6": 0,
      "ZL-2|N=2": 0,
      "ZL-2|N=3": 3,
      "ZL-2|N=4": 0,
      "ZL-2|N=5": 0,
      "ZL-2|N=6": 0
    },
    "two_dimensional_pareto_counts": {
      "fwhm_vs_T450": 3,
      "fwhm_vs_edge_stability": 10,
      "fwhm_vs_layer_count": 3,
      "fwhm_vs_total_thickness": 6
    }
  }
}
```
- Candidate rows are in `actionable_pareto_candidates.csv`; roles are suggestions only, never a declaration of final primary status.

## MISSING_TOLERANCE_PARENT_CLASSIFICATION
```json
[
  {
    "parent_nominal_geometry_hash": "276e90ad367bb3e8a245515ecae95577332641c1c5e8dd81f4279f28166b1a33",
    "parent_geometry_id": "GEO_276e90ad367bb3e8",
    "candidate_id": "ZL1_N3_M3_L79_H44_C316",
    "topology": "ZL-1",
    "N": "3",
    "H_nm": "41",
    "L_nm": "76",
    "C_nm": "",
    "M": "3",
    "compiled_sequence": "H41 L76 H41 L76 H41 L318 H41 L76 H41 L76 H41 L76",
    "tolerance_row_count": 1238,
    "source_stage": "zl1_independent_mc;zl1_local_basin",
    "historical_tmm_metrics_found": false,
    "canonical_absence_reason": "legacy reference geometry has tolerance children but is not an exact canonical TMM hash",
    "classification": "historical_reference"
  },
  {
    "parent_nominal_geometry_hash": "7ddbff8cd2cdd5437b77c0899dcca71c8c4858586425990f649b512fc5d9cfef",
    "parent_geometry_id": "GEO_7ddbff8cd2cdd543",
    "candidate_id": "ZL1_N3_M3_L78_H46",
    "topology": "ZL-1",
    "N": "3",
    "H_nm": "41",
    "L_nm": "76",
    "C_nm": "",
    "M": "3",
    "compiled_sequence": "H41 L76 H41 L76 H41 L315 H41 L76 H41 L76 H41 L76",
    "tolerance_row_count": 1,
    "source_stage": "zl1_local_basin",
    "historical_tmm_metrics_found": true,
    "canonical_absence_reason": "same candidate identity exists in canonical TMM but parent hash differs",
    "classification": "alias_or_name_mismatch"
  },
  {
    "parent_nominal_geometry_hash": "8ce9052f905256daed7e9c30c793621d4d8c8b793abeab9655db58f63b5535c3",
    "parent_geometry_id": "GEO_8ce9052f905256da",
    "candidate_id": "ZL1_N3_M3_L78_H46",
    "topology": "ZL-1",
    "N": "3",
    "H_nm": "41",
    "L_nm": "76",
    "C_nm": "",
    "M": "3",
    "compiled_sequence": "H41 L76 H41 L76 H41 L317 H41 L76 H41 L76 H41 L76",
    "tolerance_row_count": 1,
    "source_stage": "zl1_local_basin",
    "historical_tmm_metrics_found": true,
    "canonical_absence_reason": "same candidate identity exists in canonical TMM but parent hash differs",
    "classification": "alias_or_name_mismatch"
  },
  {
    "parent_nominal_geometry_hash": "dc563dd1b6f7efadbb14d4ac33af352eb84b8d67388591b6cb609cd5d9711e4d",
    "parent_geometry_id": "GEO_dc563dd1b6f7efad",
    "candidate_id": "ZL1_N3_M3_L78_H46",
    "topology": "ZL-1",
    "N": "3",
    "H_nm": "41",
    "L_nm": "76",
    "C_nm": "",
    "M": "3",
    "compiled_sequence": "H41 L76 H41 L76 H41 L313 H41 L76 H41 L76 H41 L76",
    "tolerance_row_count": 1,
    "source_stage": "zl1_local_basin",
    "historical_tmm_metrics_found": true,
    "canonical_absence_reason": "same candidate identity exists in canonical TMM but parent hash differs",
    "classification": "alias_or_name_mismatch"
  },
  {
    "parent_nominal_geometry_hash": "eda91664097b6a1e449b0c5d50abfaf7af6194272f3c35d3a805cecd758527ee",
    "parent_geometry_id": "GEO_eda91664097b6a1e",
    "candidate_id": "ZL1_N3_M3_L78_H46",
    "topology": "ZL-1",
    "N": "3",
    "H_nm": "41",
    "L_nm": "76",
    "C_nm": "",
    "M": "3",
    "compiled_sequence": "H41 L76 H41 L76 H41 L314 H41 L76 H41 L76 H41 L76",
    "tolerance_row_count": 1,
    "source_stage": "zl1_local_basin",
    "historical_tmm_metrics_found": true,
    "canonical_absence_reason": "same candidate identity exists in canonical TMM but parent hash differs",
    "classification": "alias_or_name_mismatch"
  },
  {
    "parent_nominal_geometry_hash": "eee37c4008820658573f213506d3e92d47892a646bf471871907980b1f7c6780",
    "parent_geometry_id": "GEO_eee37c4008820658",
    "candidate_id": "ZL1_N3_M3_L78_H46",
    "topology": "ZL-1",
    "N": "3",
    "H_nm": "41",
    "L_nm": "76",
    "C_nm": "",
    "M": "3",
    "compiled_sequence": "H41 L76 H41 L76 H41 L316 H41 L76 H41 L76 H41 L76",
    "tolerance_row_count": 1,
    "source_stage": "zl1_local_basin",
    "historical_tmm_metrics_found": true,
    "canonical_absence_reason": "same candidate identity exists in canonical TMM but parent hash differs",
    "classification": "alias_or_name_mismatch"
  }
]
```
- These are classified evidence gaps only; no hashes or canonical rows were repaired.

## PROPOSED_SCAN_MATRIX
- Proposed structures=34; all sequence fields are parseable JSON and have unique stage/sequence/control keys.
- P1=15, P2=4, P3=6, P4=9, P5=0.

## METHOD_ALLOCATION
1. Every proposed structure: Native-M1 TMM spectral.
2. Only gate-passing subset: Native-M1 TMM lambda-angle.
3. Representative subset: 2D plane-wave FDTD validation.
4. Last, only 8-12 structures: 2D dipole FDTD validation.

## SCANNED_STATUS
- scanned: H/L/C/M grouped variables and canonical topology/N grid.
- partially_scanned: Explicit C (152-162 nm); P3 adds only boundary gaps.
- not_scanned: asymmetric mirrors/defect position, termination/order, N_air/N_GaN, free per-layer nominal variables.
- termination/order reversal 未扫描：canonical v1 中不存在 Air/GaN termination reversal 或完整 layer-order reversal；P2 中相关结构仅为 proposed-only，尚未运行。
- proposed_only: P1-P4 matrix rows.

## VALIDATION
- all generated CSV/JSON are readable; proposed layer sequences parse; source database and prepared-view SHA256 values are unchanged.
- no simulation/model/runtime file was created.

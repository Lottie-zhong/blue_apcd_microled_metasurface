# LP 5D Phase Reachability Probe V1

- Outcome: `LP_5D_PHASE_REACHABILITY_PROBE_LEVEL3_5D_INSUFFICIENT`
- Evidence level: `LEVEL_3_5D_PHASE_LEVERAGE_INSUFFICIENT`
- Solver calls: `48`
- Wavelength: `450.0 nm only`

## Frozen probe

24 frozen geometries, 48 x/y subruns, no replacement or geometry expansion.

## Active-process preflight

Existing FDTD/Python process lines were recorded; no external process was terminated.

## Solver accounting

- Accepted x/y subruns: 48/48
- Complete Jones: 24/24
- Entered=true subruns were not retried.

## Accepted x phase evidence

- Phase-only evidence rows: 24
- New probe envelope: {'count': 24, 'min_phase_deg': 72.51623323236915, 'max_phase_deg': 98.50239984119824, 'span_deg': 25.986166608829095, 'largest_uncovered_circular_arc_deg': 334.0138333911709, 'circular_coverage_deg': 25.98616660882908}

## Complete Jones evidence

- Full-Jones rows: 24
- Maximum direct/scalar projector consistency error: 1.0824674490095276e-15

## Old vs new phase envelope

- OLD_SUPPORT: {'count': 409, 'min_phase_deg': 62.053626948833056, 'max_phase_deg': 106.89783294848239, 'span_deg': 44.84420599964933, 'largest_uncovered_circular_arc_deg': 315.1557940003507, 'circular_coverage_deg': 44.84420599964932}
- NEW_PROBE_ONLY: {'count': 24, 'min_phase_deg': 72.51623323236915, 'max_phase_deg': 98.50239984119824, 'span_deg': 25.986166608829095, 'largest_uncovered_circular_arc_deg': 334.0138333911709, 'circular_coverage_deg': 25.98616660882908}
- COMBINED_SUPPORT: {'count': 433, 'min_phase_deg': 62.053626948833056, 'max_phase_deg': 106.89783294848239, 'span_deg': 44.84420599964933, 'largest_uncovered_circular_arc_deg': 315.1557940003507, 'circular_coverage_deg': 44.84420599964932}

## New low/high phase extrema

- Lowest: [{'candidate_id': 'LP_5D_PHASE_REACHABILITY_V2_01', 'role': 'LOW_PHASE_EXTREME', 'exact_geometry_hash_sha256': '5f34817ae0c4ff550b6ab7e3a1ba39454bf2e83832e334841f26d7547e0ee6d2', 'phase_deg': 72.51623323236915, 'abs_txx': 0.9916764980262333, 'source_T': 0.9834235347006397, 'phase_evidence_label': 'PHASE_ONLY_REACHABILITY_PHYSICS', 'physics_origin': 'PROSPECTIVE_5D_PHASE_REACHABILITY_PROBE'}, {'candidate_id': 'LP_5D_PHASE_REACHABILITY_V2_02', 'role': 'LOW_PHASE_EXTREME', 'exact_geometry_hash_sha256': 'a9b25489818435d9b0ac15f667a789c13e4613cebe5be5fda694003a6f2cc601', 'phase_deg': 72.84554671437762, 'abs_txx': 0.9924579442307189, 'source_T': 0.9849736754670266, 'phase_evidence_label': 'PHASE_ONLY_REACHABILITY_PHYSICS', 'physics_origin': 'PROSPECTIVE_5D_PHASE_REACHABILITY_PROBE'}]
- Highest: [{'candidate_id': 'LP_5D_PHASE_REACHABILITY_V2_11', 'role': 'HIGH_PHASE_EXTREME', 'exact_geometry_hash_sha256': 'ac2b72fe2603d777c376ff550c877126ba5a9a495de6e542e252d0383553e645', 'phase_deg': 98.50239984119824, 'abs_txx': 0.9893065776767273, 'source_T': 0.9787510971256909, 'phase_evidence_label': 'PHASE_ONLY_REACHABILITY_PHYSICS', 'physics_origin': 'PROSPECTIVE_5D_PHASE_REACHABILITY_PROBE'}, {'candidate_id': 'LP_5D_PHASE_REACHABILITY_V2_10', 'role': 'HIGH_PHASE_EXTREME', 'exact_geometry_hash_sha256': 'e1769ae862a5b822aff877c0b362875de1f1395a3e95086d4ae2fbc25d54e18c', 'phase_deg': 98.12403357267148, 'abs_txx': 0.9830119575189579, 'source_T': 0.9663427225054834, 'phase_evidence_label': 'PHASE_ONLY_REACHABILITY_PHYSICS', 'physics_origin': 'PROSPECTIVE_5D_PHASE_REACHABILITY_PROBE'}]

## Probe-role effectiveness

{
  "5D_BOUNDARY_SPARSE_REGION": {
    "above_old_max_count": 0,
    "below_old_min_count": 0,
    "count": 4,
    "max_phase_deg": 79.44957941867875,
    "min_phase_deg": 77.0495103417824
  },
  "DISAGREEMENT_PHYSICS_CONTROL": {
    "above_old_max_count": 0,
    "below_old_min_count": 0,
    "count": 4,
    "max_phase_deg": 82.077290769832,
    "min_phase_deg": 80.91782120687522
  },
  "HIGH_PHASE_EXTREME": {
    "above_old_max_count": 0,
    "below_old_min_count": 0,
    "count": 6,
    "max_phase_deg": 98.50239984119824,
    "min_phase_deg": 95.3957720538224
  },
  "LOW_PHASE_EXTREME": {
    "above_old_max_count": 0,
    "below_old_min_count": 0,
    "count": 6,
    "max_phase_deg": 76.25227622198071,
    "min_phase_deg": 72.51623323236915
  },
  "PHASE_PROJECTOR_TRADEOFF": {
    "above_old_max_count": 0,
    "below_old_min_count": 0,
    "count": 4,
    "max_phase_deg": 80.87653955714795,
    "min_phase_deg": 79.94489866370067
  }
}

## Phase/projector tradeoff

{
  "all_full_jones": {
    "circular_coverage_deg": 25.98616660882908,
    "count": 24,
    "largest_uncovered_circular_arc_deg": 334.0138333911709,
    "max_phase_deg": 98.50239984119824,
    "min_phase_deg": 72.51623323236915,
    "span_deg": 25.986166608829095
  },
  "best25_projector_error": {
    "circular_coverage_deg": 3.106627787375828,
    "count": 6,
    "largest_uncovered_circular_arc_deg": 356.8933722126242,
    "max_phase_deg": 98.50239984119824,
    "min_phase_deg": 95.3957720538224,
    "span_deg": 3.1066277873758423
  },
  "best50_projector_error": {
    "circular_coverage_deg": 18.557501177497556,
    "count": 12,
    "largest_uncovered_circular_arc_deg": 341.44249882250244,
    "max_phase_deg": 98.50239984119824,
    "min_phase_deg": 79.94489866370067,
    "span_deg": 18.55750117749757
  },
  "no_new_absolute_threshold": true,
  "projector_error_consistency_max_abs_error": 1.0824674490095276e-15,
  "throughput_ge_median": {
    "circular_coverage_deg": 9.231744055454385,
    "count": 12,
    "largest_uncovered_circular_arc_deg": 350.7682559445456,
    "max_phase_deg": 82.077290769832,
    "min_phase_deg": 72.84554671437762,
    "span_deg": 9.231744055454385
  },
  "throughput_median": 0.9835912934180809
}

## Boundary saturation

{
  "extreme_coordinate_status": [
    {
      "D": "interior",
      "J1_side": "at_lower",
      "J2_length": "at_lower",
      "J2_width": "at_lower",
      "Psi": "interior",
      "candidate_id": "LP_5D_PHASE_REACHABILITY_V2_01",
      "phase_deg": 72.51623323236915
    },
    {
      "D": "interior",
      "J1_side": "at_lower",
      "J2_length": "at_lower",
      "J2_width": "interior",
      "Psi": "interior",
      "candidate_id": "LP_5D_PHASE_REACHABILITY_V2_02",
      "phase_deg": 72.84554671437762
    },
    {
      "D": "interior",
      "J1_side": "interior",
      "J2_length": "interior",
      "J2_width": "at_upper",
      "Psi": "interior",
      "candidate_id": "LP_5D_PHASE_REACHABILITY_V2_11",
      "phase_deg": 98.50239984119824
    },
    {
      "D": "interior",
      "J1_side": "interior",
      "J2_length": "interior",
      "J2_width": "interior",
      "Psi": "interior",
      "candidate_id": "LP_5D_PHASE_REACHABILITY_V2_10",
      "phase_deg": 98.12403357267148
    }
  ]
}

## 60-degree reachability

{
  "full_jones_sectors": [
    1
  ],
  "maximum_pairwise_phase_separation_deg": 25.986166608829095,
  "phase_only_sectors": [
    1
  ]
}

## Evidence level

`LEVEL_3_5D_PHASE_LEVERAGE_INSUFFICIENT`

## 5D sufficiency decision

`LP_5D_PHASE_REACHABILITY_PROBE_LEVEL3_5D_INSUFFICIENT`

## Future freedom ranking

Offline-only ranking retained: H first; no new freedom implemented.

## Hard gates

No D9, broadband, K6, model fill, retraining, replacement, or protected-report modification.

## Execution provenance

The 48-subrun execution contract froze runner SHA256 `3327d0cb391b2c7085ff4e42b11607d5e8420dbc8caee8507d51522b4a289326`; a postprocess-only fix changed the current code to `1f2bab31c69faee048abf90d69e5a08da6ecc9dd35e39c36c974a24e96c5618a` after all 48 accepted subruns. No solver was rerun and no physics checkpoint was modified.

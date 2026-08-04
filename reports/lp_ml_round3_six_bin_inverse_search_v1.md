# LP-ML Six-Bin Surrogate-Only Inverse Search v1

## Status

`LP_ML_SIX_BIN_INVERSE_PARTIAL_COVERAGE_ROUND3_RECOMMENDED`

This run is offline surrogate planning only. Solver/FDTD calls = 0; no physics dataset, split, normalization, checkpoint, or protected report was modified.

## Frozen evidence

Clean v2 contains 319 geometries / 2871 rows and geometry 054 remains quarantined with zero admitted rows. C0 is the global guard; validation-frozen OLD_C5_BLEND_0.95 (weights C0=0.9025, C1=0.0475, C5=0.05) is the planning model; C1-C5/seed ensembles provide disagreement diagnostics.

## Optimization coverage

Coarse phi offsets: 0..55 degrees at 5-degree spacing; each bin/offset used 128 Sobol/diversified starts. Fine offsets were searched around the best complete coarse tuple with 64 starts/bin. A bounded derivative-free cross-check used 32 starts/bin and 24 local iterations. All continuous optima were quantized and rescored before admission.

## Phi-offset and tuple result

Best tuple: `{"all_bins_covered": true, "candidate_ids": ["LPML_INV_B0_GRA_25833c0adf80", "LPML_INV_B1_GRA_85a555199234", "LPML_INV_B2_GRA_01584ff79146", "LPML_INV_B3_GRA_b1ef16f6bd18", "LPML_INV_B4_GRA_002a5696d677", "LPML_INV_B5_GRA_134a1276c277"], "geometry_families": 6, "phi_offset_deg": 55.0, "risk_counts": {"CONSENSUS_LOW_RISK": 0, "CONSENSUS_MODERATE_RISK": 0, "MODEL_DISAGREEMENT_HIGH_RISK": 6}, "tuple_score": 79.47724928857065}`. Candidate pool size: 508; tuple front size: 103.

## Per-bin coverage

{
  "0": {
    "count": 59,
    "high": 59,
    "low": 0,
    "moderate": 0
  },
  "1": {
    "count": 263,
    "high": 263,
    "low": 0,
    "moderate": 0
  },
  "2": {
    "count": 55,
    "high": 55,
    "low": 0,
    "moderate": 0
  },
  "3": {
    "count": 45,
    "high": 45,
    "low": 0,
    "moderate": 0
  },
  "4": {
    "count": 46,
    "high": 46,
    "low": 0,
    "moderate": 0
  },
  "5": {
    "count": 40,
    "high": 40,
    "low": 0,
    "moderate": 0
  }
}

## Future FDTD proposal

The proposal is 6-10 novel candidates per bin (36-60 total; 72-120 x/y subruns), 450 nm only, subject to separate authorization. No runnable solver package or FDTD shortlist execution was created.

## Hard gates

No geometry 054, no inverse FDTD, no K6, no six-bin promotion, no frozen-test tuning, and no new physics. Round-3 C5 was trained offline from scratch before this search; coverage is 58/64 complete geometries. Known controls are labeled `KNOWN_PHYSICS_CONTROL`; generated rows are `SURROGATE_PREDICTION_NOT_PHYSICS`.

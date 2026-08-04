# LP-ML Six-Bin Surrogate-Only Inverse Search v1

## Status

`LP_ML_SIX_BIN_INVERSE_PARTIAL_COVERAGE_ROUND3_RECOMMENDED`

This run is offline surrogate planning only. Solver/FDTD calls = 0; no physics dataset, split, normalization, checkpoint, or protected report was modified.

## Frozen evidence

Clean v2 contains 319 geometries / 2871 rows and geometry 054 remains quarantined with zero admitted rows. C0 is the global guard; the alpha=0.95 C0/C1 blend is the primary differentiable model; C1-C4/seed ensembles provide disagreement diagnostics.

## Optimization coverage

Coarse phi offsets: 0..55 degrees at 5-degree spacing; each bin/offset used 128 Sobol/diversified starts. Fine offsets were searched around the best complete coarse tuple with 64 starts/bin. A bounded derivative-free cross-check used 32 starts/bin and 24 local iterations. All continuous optima were quantized and rescored before admission.

## Phi-offset and tuple result

Best tuple: `{"all_bins_covered": true, "candidate_ids": ["LPML_INV_B0_DER_7e4aba91db0d", "LPML_INV_B1_GRA_7cfbdf3fa522", "LPML_INV_B2_DER_8428a271313a", "LPML_INV_B3_DER_a20f5c1228d9", "LPML_INV_B4_DER_aa57da44feda", "LPML_INV_B5_DER_c610edfe60b2"], "geometry_families": 6, "phi_offset_deg": 40.0, "risk_counts": {"CONSENSUS_LOW_RISK": 0, "CONSENSUS_MODERATE_RISK": 0, "MODEL_DISAGREEMENT_HIGH_RISK": 6}, "tuple_score": 79.68196154519124}`. Candidate pool size: 522; tuple front size: 120.

## Per-bin coverage

{
  "0": {
    "count": 66,
    "high": 66,
    "low": 0,
    "moderate": 0
  },
  "1": {
    "count": 269,
    "high": 269,
    "low": 0,
    "moderate": 0
  },
  "2": {
    "count": 54,
    "high": 54,
    "low": 0,
    "moderate": 0
  },
  "3": {
    "count": 39,
    "high": 39,
    "low": 0,
    "moderate": 0
  },
  "4": {
    "count": 45,
    "high": 45,
    "low": 0,
    "moderate": 0
  },
  "5": {
    "count": 49,
    "high": 49,
    "low": 0,
    "moderate": 0
  }
}

## Future FDTD proposal

The proposal is 6-10 novel candidates per bin (36-60 total; 72-120 x/y subruns), 450 nm only, subject to separate authorization. No runnable solver package or FDTD shortlist execution was created.

## Hard gates

No geometry 054, no Round-3, no inverse FDTD, no K6, no six-bin promotion, no frozen-test tuning, no model retraining, and no new physics. Known controls are labeled `KNOWN_PHYSICS_CONTROL`; generated rows are `SURROGATE_PREDICTION_NOT_PHYSICS`.

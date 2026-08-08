# NP K6 HF P0 anchor dataset pilot v1

Status: `NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY`.

Six sequential attempt_001 anchors passed the frozen V2 numerical gates and were promoted transactionally to exactly 66 formal HF observations (3 geometries × 2 polarizations × 11 exact wavelengths). `pilot_training_authorized=true`; bulk MDC-compatible training remains false; no real training or sealed test was started.

## Anchor gates

| case | post-FSP SHA256 | max closure | structure anomaly | order mismatch | direct normalization mismatch |
|---|---|---:|---:|---:|---:|
| RUN3C_P_PILOT_HF_V1 | `c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca` | 0.004513767612906006 | 0.003592535616673165 | 2.220446049250313e-16 | 1.1102230246251565e-16 |
| RUN3C_S_PILOT_HF_V2 | `f31404b25632cf5b9e5c7307540e360b1b1f29f5955b6903784c5777b3f4a945` | 0.0018506553672153897 | 0.001851197502713231 | 2.220446049250313e-16 | 1.1102230246251565e-16 |
| RUN3A_P_PILOT_HF_V1 | `eb30cc93ee74c4c0ed04361ac3d6393a8fe495579f6076861aa458dba8fddaea` | 0.001980973581946238 | -0.00040745958337495836 | 2.220446049250313e-16 | 1.1102230246251565e-16 |
| RUN3A_S_PILOT_HF_V1 | `b4ca137b2b7d43b6d990c1d13cc1640188c9791aaebfdd25729d5dd5e772a8fd` | 0.0004988900917509698 | 9.514723995474039e-05 | 1.1102230246251565e-16 | 1.1102230246251565e-16 |
| RUN3B_P_PILOT_HF_V1 | `67d8d721e2b679d53eca99fbdfbe7aca1560ed207a41d27977149fd386fdd2a0` | 0.004793612404252301 | -0.0025563666856925904 | 2.220446049250313e-16 | 1.1102230246251565e-16 |
| RUN3B_S_PILOT_HF_V1 | `8490c35a5bb95fa2deb2d19ce13ac24c8a0d9c5b48662e06ca34457399a03904` | 0.00034150934929878113 | -0.00020535698471180197 | 1.1102230246251565e-16 | 1.1102230246251565e-16 |

All cases have exact wavelengths 445–455 nm, finite values, read-only reload, dominant transmitted order +1, and `quality_gate_pass=true`. No rerun or attempt_002 was used; the obsolete consumed RUN3C-S V1 identity remains excluded.

## p/s preliminary audit

The three geometry-family comparisons remain `P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA`; this pilot does not make a final p/s equivalence claim.

```json
{
  "classification_set": [
    "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA",
    "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA",
    "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA"
  ],
  "final_p_s_equivalence_claim": false,
  "rows": [
    {
      "classification": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA",
      "geometry_family": "RUN3C",
      "max_abs_delta_T": 0.3859462569503582,
      "max_abs_delta_eta_plus1": 0.39135162366433196,
      "mean_abs_delta_eta_plus1": 0.15956877132435665,
      "p_case_id": "RUN3C_P_PILOT_HF_V1",
      "s_case_id": "RUN3C_S_PILOT_HF_V2"
    },
    {
      "classification": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA",
      "geometry_family": "RUN3A",
      "max_abs_delta_T": 0.1202389811290463,
      "max_abs_delta_eta_plus1": 0.15943466424436148,
      "mean_abs_delta_eta_plus1": 0.07375088045211702,
      "p_case_id": "RUN3A_P_PILOT_HF_V1",
      "s_case_id": "RUN3A_S_PILOT_HF_V1"
    },
    {
      "classification": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA",
      "geometry_family": "RUN3B",
      "max_abs_delta_T": 0.23189368407334832,
      "max_abs_delta_eta_plus1": 0.2990310731428377,
      "mean_abs_delta_eta_plus1": 0.13050199728539633,
      "p_case_id": "RUN3B_P_PILOT_HF_V1",
      "s_case_id": "RUN3B_S_PILOT_HF_V1"
    }
  ]
}
```

Dataset files are under `outputs/np_k6_hf_pilot_dataset_v1/`. Training has not started (`checkpoint_count=0`).

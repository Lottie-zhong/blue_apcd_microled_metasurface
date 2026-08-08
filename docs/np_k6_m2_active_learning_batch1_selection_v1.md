# NP K6 M2 active-learning Batch1 selection v1

Status: NP_K6_M2_ACTIVE_LEARNING_BATCH1_SELECTED_FDTD_AUTHORIZATION_PENDING.

Acquisition-only development selection. No FDTD solver was called, no sealed labels were accessed, and no M1 retraining was performed.

- P0: 3 formal geometries / 66 observations.
- M1: 3 CNN acquisition checkpoints (seeds 17/29/43); MLP committee is acquisition-only.
- Development pool: 48 total, 3 formal HF excluded, 12 sealed excluded, 45 eligible unlabeled.
- Batch1: exactly 6 geometries and 12 planned p/s tasks; expected observations after successful future acquisition: 198.

## Selected slots

- U1: K6X_D200_D205_D215_D220_D225_D230; D=200,205,215,220,225,230; predicted eta(+1)=0.238613; rationale={"fallback_near_duplicate_relaxed": false, "metric": "highest CNN epistemic uncertainty", "rank_position": 1, "slot": "U1"}
- U2: K6X_D100_D140_D145_D155_D225_D230; D=100,140,145,155,225,230; predicted eta(+1)=0.807426; rationale={"fallback_near_duplicate_relaxed": false, "metric": "highest committee uncertainty after U1 near-duplicate exclusion", "rank_position": 2, "slot": "U2"}
- D1: K6X_D100_D200_D205_D210_D215_D220; D=100,200,205,210,215,220; predicted eta(+1)=0.594752; rationale={"fallback_near_duplicate_relaxed": false, "metric": "farthest from current three formal HF geometries", "rank_position": 5, "slot": "D1"}
- D2: K6X_D100_D110_D115_D220_D225_D230; D=100,110,115,220,225,230; predicted eta(+1)=0.864320; rationale={"fallback_near_duplicate_relaxed": false, "metric": "maximin coverage against existing HF and selected set", "rank_position": 1, "slot": "D2"}
- X1: K6X_D100_D130_D135_D155_D160_D225; D=100,130,135,155,160,225; predicted eta(+1)=0.808990; rationale={"fallback_near_duplicate_relaxed": false, "metric": "highest CNN/MLP eta/order disagreement", "rank_position": 7, "slot": "X1"}
- P1: K6X_D100_D105_D115_D120_D125_D130; D=100,105,115,120,125,130; predicted eta(+1)=0.882329; rationale={"fallback_near_duplicate_relaxed": false, "metric": "highest predicted eta(+1), excluding nearby selected candidates", "rank_position": 2, "slot": "P1"}

## Gates

- All selected tasks have entered=false, run_invocation_count=0, solver_authorized=false, development=true, sealed=false.
- Contexts are p/s × 445–455 nm, u_x=0, k_y=0, 3 ps maximum simulation time, auto-shutoff 1e-5.
- Selection order is U1 -> U2 -> D1 -> D2 -> X1 -> P1; near-duplicate threshold is the eligible-pool pairwise-distance 25th percentile.

Next action: wait for explicit authorization NP_K6_M2_BATCH1_FDTD_ACQUISITION.

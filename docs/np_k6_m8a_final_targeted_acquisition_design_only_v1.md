# NP K6 M8A final targeted development acquisition design-only v1

**Status:** `NP_K6_M8A_FINAL_TARGETED_ACQUISITION_PRIMARY2_READY_FOR_SOLVER_AUTHORIZATION`
**Scope:** ZERO-SOLVER design only; no FDTD/LumAPI/new HF/external/sealed/inverse access.

## Preregistration
- ID: `{j("NP_K6_M8A_FINAL_TARGETED_ACQUISITION_PREREG_V1.json")["preregistration_id"]}`
- SHA256: `{ph}`
- Candidate identities were generated only after preregistration hash freeze.
- Scope: ordered physical `[D1..D6]`, `u_x=0`, `NORMAL_INCIDENCE_ONLY`; no angular generalization.

## Primary2 recommendation

- **TAIL-LOCALIZATION**: `K6X_D100_D140_D165_D190_D225_D230`; hash `21b70b358c2bfdf1aedcf8c0b7cff52623e49009d66f8ebdc8316f4e58399911`; tail score `0.692355`; ranking score `0.350392`. Rationale: highest frozen role-specific score after anti-duplication and deterministic hash tie-break.
- **RANKING-DISAMBIGUATION**: `K6X_D105_D110_D115_D125_D165_D230`; hash `8562bc97d6c350f55a323b07984a1523cafda55a9534ed81b3eb0c333215b5ae`; tail score `0.421567`; ranking score `0.625549`. Rationale: highest frozen role-specific score after anti-duplication and deterministic hash tie-break.

The two primary identities are distinct, outside the formal HF20/HF16 overlap and quarantined G01 geometry, and preserve physical order. Candidate scores are proxy-only; no HF truth was used for selection.

## Backup queue
1. `K6X_D105_D110_D165_D200_D215_D220` — tail `0.600985`, ranking `0.313985`, P/S proxy `0.050160`.
2. `K6X_D150_D155_D160_D165_D195_D225` — tail `0.599050`, ranking `0.422374`, P/S proxy `0.148913`.
3. `K6X_D100_D120_D130_D150_D165_D180` — tail `0.591612`, ranking `0.449865`, P/S proxy `0.160882`.
4. `K6X_D125_D135_D150_D175_D195_D210` — tail `0.561082`, ranking `0.398449`, P/S proxy `0.052301`.
5. `K6X_D110_D125_D135_D155_D175_D195` — tail `0.555825`, ranking `0.396874`, P/S proxy `0.132717`.
6. `K6X_D160_D165_D170_D175_D180_D220` — tail `0.552414`, ranking `0.465012`, P/S proxy `0.168733`.

## G01 residual-tail forensic audit
- Geometry: `K6X_D135_D155_D190_D220_D225_D230`; ordered diameters `[135.0, 155.0, 190.0, 220.0, 225.0, 230.0]`; adjacent jumps `[20.0, 35.0, 30.0, 5.0, 5.0]` nm.
- HF20 rows: 22; HF eta(+1) broadband mean `0.383110` vs LF proxy `0.707794`; HF-LF residual mean per order `[0.002826, -0.020043, 0.02917, 0.019475, -0.324684, -0.032986, -0.001109]`.
- The audit separates isolated-outlier, local smooth, diameter-jump, P/S-dependent and order-redistribution hypotheses. It is diagnostic/proxy evidence only; it does not create new truth.

## Ranking, P/S, and coverage audit
- Ranking score is preregistered from model-rank variance, pairwise reversal, near-Top3 margin, eta(+1) potential, Ridge/CNN disagreement and P/S proxy.
- P/S remains explicit; no P/S averaging or equivalence assumption.
- Candidate pool is anti-duplicated against formal HF20/HF16, external registry, sealed pool and duplicate hashes.

## Baselines and 2-vs-4 marginal value
- `proposed_Primary2`: ['K6X_D100_D140_D165_D190_D225_D230', 'K6X_D105_D110_D115_D125_D165_D230']; tail mean `0.556961`, ranking mean `0.487971`, P/S mean `0.130979`.
- `residual_score_top2`: ['K6X_D105_D110_D165_D200_D215_D220', 'K6X_D105_D110_D115_D120_D135_D200']; tail mean `0.461589`, ranking mean `0.383325`, P/S mean `0.102123`.
- `performance_only_top2`: ['K6X_D100_D120_D130_D150_D165_D180', 'K6X_D115_D125_D135_D155_D180_D195']; tail mean `0.566578`, ranking mean `0.417567`, P/S mean `0.141095`.
- `ranking_ambiguity_top2`: ['K6X_D100_D120_D130_D150_D165_D180', 'K6X_D115_D125_D135_D155_D180_D195']; tail mean `0.566578`, ranking mean `0.417567`, P/S mean `0.141095`.
- `random2_seeded_20260816`: ['K6X_D150_D155_D160_D165_D195_D225', 'K6X_D100_D130_D135_D165_D170_D230']; tail mean `0.538265`, ranking mean `0.454615`, P/S mean `0.092014`.
- Primary2: 4 future formal cases / 44 rows using 4 MPI x 1 thread.
- Optional first4 (Primary2 + next two backups): 8 cases / 88 rows. Marginal audit: `{"lf_response_diversity": -0.016302955281914874, "ps_information_mean": -0.015720962991260676, "ranking_disambiguation_mean": -0.05989539395494764, "redundancy_mean": -0.0042772508881916416, "tail_localization_mean": 0.021528018705043506}`.
- Recommendation: `PRIMARY2_ONLY_RECOMMENDED`; no automatic backup substitution.

## Future acceptance and stopping rule
- Tail success: continuous/error-cluster localization OR informative negative result showing isolated/proxy failure.
- Ranking success: near-champion ordering materially clarified OR agreement confirmed.
- Plateau stop: If after Primary2 and M9 no model passes all gates, common-HF20 lacks consistent improvement, and tail/champion failures do not converge, stop automatic development-HF loop and enter FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED.

## Governance and validation
- Solver calls/new HF/external HF/sealed target reads/inverse design: all zero.
- Future concurrency is frozen as 4 MPI × 1 thread; any concurrency-3 observation is functional-stability evidence only, not throughput optimization.
- M8A validator: PASS; focused tests: 7 passed.
- External HF is not recommended or authorized by this design stage.

## Evidence
- `outputs/np_k6_m8a_final_targeted_acquisition_design_v1/`
- `docs/np_k6_m8a_final_targeted_acquisition_design_only_v1.md`

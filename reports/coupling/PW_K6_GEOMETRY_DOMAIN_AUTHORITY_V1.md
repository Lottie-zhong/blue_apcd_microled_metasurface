# PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1

Status: `PASS_RECOVERED_CLOSED_CANDIDATE_DOMAIN`

The original selection authority was recovered from historical commit `8bb3e918b7f1d5085cacec5db7691b286f62647b`.

## Exact authority sources

- Historical builder: `scripts/shared_fdtd/tools/build_pw_k6_seed_db_v1_manifest.py`, SHA256 `35d8b7818064b0934676ccd33ecb30fb30c788564d90ca9fd21effb4ed9edf72`.
- Historical zero-solver regression: `scripts/shared_fdtd/tests/run_pw_k6_seed_manifest_zero_solver_tests.py`, SHA256 `a1bef21abd4bc36eefad737b280d6dbdad1f78df6fa9fdb49528ecc4802c4942`.
- Frozen 64G candidate pool: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1\K6_V1_64G_DOE_CANDIDATES.csv`, SHA256 `a623d61b1d5e0fdec7ee7cbd006b816ad00f4a8a35298cd12bb0e41afccbd2a1`.
- Current deterministic generator audit source: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\apcd_database_authority_audit_v1.py`, SHA256 `8102abb05b8a44a9a28d762054b73ce0ea66564080929cc9c27d604a40024aed`.

## Recovered domain

- Ordered K6 tuple `[D1,D2,D3,D4,D5,D6]`; position identity is significant and sorting is forbidden.
- Observed candidate bounds `100..230 nm` on a `5 nm` grid; `K=6`, `p=290 nm`, `H=500 nm`.
- Historical origin: `deterministic_halton_maximin_on_observed_candidate_grid`, Halton bases `(2,3,5,7,11,13)`.
- Historical distance: `sqrt(sum(((x-y)/130)^2))`.
- Historical hash: SHA256 of comma-joined integer D1..D6.
- Original K6 authority: Core4 plus the first 16 unique entries in frozen `K6V1_S01..S48` order; no reranking.

## Fabrication boundary

The historical source explicitly records `UNRESOLVED_INDEPENDENT_FILE_NOT_IDENTIFIED` for a separate fabrication-limit file. No manufacturing bound or minimum-gap rule was inferred. The extension is restricted to the existing frozen candidate pool, so every selected point passes the recovered candidate-domain contract; manufacturing acceptance is not asserted by this extension manifest.

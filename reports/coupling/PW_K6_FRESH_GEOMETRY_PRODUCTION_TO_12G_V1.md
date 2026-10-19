# PW_K6_FRESH_GEOMETRY_PRODUCTION_TO_12G_V1

Generated: `2026-09-25T06:25:19.763394+00:00`  
Authority branch: `work/mdc-np-coupling-ml-v1`  
Production HEAD: `3a4cf14b4ceda2e3e5930cbd3833e71b7809ac8d`  
Source manifest SHA256: `463ceaece52121b1a968d22881944c082a26041c16b4489c25b6a0b8f44db62b`

## STATUS

`BLOCKED_FRESH_MANIFEST_EXHAUSTED`

The frozen manifest contains 20 entries, but the fresh-only admission rule yields **0 eligible geometry** (required: 6). No new queue row, setup, solver, replay, recovery, or autofill action was performed in this task.

## FRESH ELIGIBILITY POOL

- Eligibility manifest: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\PW_K6_FRESH_ELIGIBILITY_MANIFEST_V1.json`
- Pool count: **0**
- Selected geometries: **[]**
- Manifest order was preserved; no sorting or new geometry was introduced.

Historical exclusion summary:

- `W2H_15294`: prior solver ledger evidence exists in historical G1/G2/NP/5-nm output namespaces; not fresh.
- `W2H_06824`, `W2H_19451`, `W2H_10588`: prior K6 production attempts exist.
- `K6V1_S01`, `K6V1_S06`-`S11`: prior failed-preentry attempts; non-reusable under the task rule.
- `K6V1_S02`-`S05`, `K6V1_S15`, `K6V1_S16`: existing fresh-native truth; already counted in the current valid set.
- `K6V1_S12`, `K6V1_S13`: explicit post-entry/no-truth exclusions.
- `K6V1_S14`: explicit recovered-adopted exclusion; no reuse.

## PRODUCTION STATE

- Fresh-native valid count: **6** (`K6V1_S02`, `S03`, `S04`, `S05`, `S15`, `S16`).
- Completed this task: **0**.
- Active: **0**.
- Coupling-ML pending/ready queue: **0**.
- Coupling-ML nonterminal queue rows: `[]`.
- All global slots: `[{'slot_id': 'GLOBAL_SLOT_1', 'state': 'FREE', 'owner_branch': None, 'logical_case_id': None, 'attempt_id': None}, {'slot_id': 'GLOBAL_SLOT_2', 'state': 'FREE', 'owner_branch': None, 'logical_case_id': None, 'attempt_id': None}, {'slot_id': 'GLOBAL_SLOT_3', 'state': 'FREE', 'owner_branch': None, 'logical_case_id': None, 'attempt_id': None}]`.
- Admission control: `{'control_id': 1, 'new_entry_hold': 0, 'temporary_runtime_cap': None, 'health_status': 'PASS', 'control_generation': 20, 'updated_at': '2026-09-25T06:05:37.424484+00:00'}`.
- Traditional nonterminal rows were observed and left untouched: `[{'logical_case_id': 'K6_5X3_SP237_X_XPOS_M2', 'attempt_id': 'attempt_001', 'state': 'SETUP_READY', 'slot_id': 'GLOBAL_SLOT_1'}, {'logical_case_id': 'PW_TRADITIONAL_BASELINE_P', 'attempt_id': 'attempt_001', 'state': 'SETUP_READY', 'slot_id': 'GLOBAL_SLOT_1'}]`.
- Traditional production remains disabled; no scheduled scientific entry was enabled.

## 8G / 12G GATES

- 8G immutable snapshot: `NOT_REACHED` (only 6 fresh-native geometries available).
- 8G CPU sanity: `NOT_RUN`.
- 12G immutable snapshot: `NOT_REACHED`.
- Learnability A/B/C: `NOT_RUN`.
- NP-prior effect: `NOT_RUN`.
- Representation diagnosis: `NOT_RUN`.

## CONTROL SAFETY

- Solver launches this task: **0**.
- Scientific replay/rerun: **0**.
- Queue mutations this task: **0**.
- Traditional mutation: **0**.
- New automation/scheduled task: **0**.
- Existing generated artifacts were preserved; no broad cleanup was performed.

## GIT

- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `3a4cf14b4ceda2e3e5930cbd3833e71b7809ac8d`
- Worktree: `DIRTY` (pre-existing changes plus the requested report/eligibility manifest; no unrelated files were staged or committed).
- Push: `NOT_PUSHED`.

## NEXT

`BLOCKED_FRESH_MANIFEST_EXHAUSTED`: obtain a new frozen manifest containing never-attempted geometries, then rerun the fresh-only admission audit. Do not reuse any excluded case and do not start 8G/12G analysis from fewer than the required fresh set.

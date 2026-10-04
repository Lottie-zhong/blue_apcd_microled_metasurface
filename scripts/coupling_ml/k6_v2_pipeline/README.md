# K6 V2 pipeline

This package implements the frozen V2 data, training, validation, local-affine, and two-air-plane interfaces. It is preparation code: loading real development truth and calling the production fit scheduler are separate operations.

## Frozen interfaces

- `contracts.py`: wavelength/order/polarization axes, state shapes, roles, and truth containers.
- `consumer_exclusions.py`: versioned fail-closed truth provenance and quarantine checks shared by import, training, ranking, confirmation, diagnostics, and local-affine entry points.
- `ingest.py`: registry and role allowlists; verified Runner-truth ingestion; development, confirmation, and diagnostic isolation; one-shot reveal authorization.
- `splits.py`: geometry-grouped folds and train-only geometry scaling.
- `models.py`, `training.py`: RBF KRR and the 6→32→32 Cartesian MLP, log-positive P_scale head, nested learning-curve plan, resumable fits, and dry-run task plan.
- `h1.py`: frozen H2 reconstruction and original conjunctive H1 metrics. C_hat is complex arithmetic mean over seeds. P_scale is inverse-log-normalized and exponentiated per seed, then averaged arithmetically in physical positive units.
- `validation.py`: fixed outer-fold development evaluation only.
- `local_affine.py`: 12 leave-one-axial-out evaluations plus final local fit interface.
- `evaluators.py`: raw two-air-plane Floquet E/H fit diagnostics, de-embedding, and frozen engineering thresholds.
- `confirmation.py`: artifact-byte freeze gate and one-shot confirmatory report orchestration.

## Preparation and recovery

Start by reading the task `CONTINUATION.md` and frozen SHA inventory. Build the task list with `training.build_fit_plan(repository_root)`; compare it to `DRY_RUN_FIT_PLAN_V1.json`. Do not invoke `execute_global_pipeline` until all 160 development cases pass role, provenance, contract, and truth-integrity checks. Its production API rejects raw arrays and requires the exact frozen plan and role-bound case collection.

The confirmation path requires both global candidates' prediction bundles and their hashes before reveal authorization. Once authorization is issued, confirmation is consumed once; an interrupted evaluation must be audited rather than silently replayed. Never use confirmation responses for model selection. Two-plane evaluation requires actual raw E/H from both heights and reports evaluator readiness only if fields or provenance are missing.

## Scope guard

No solver, production model fit, standalone P_scale fit, reserve case, confirmation reveal/evaluation, GPU Runner, or FDTD command is launched by importing these modules. Synthetic fixtures validate code behavior only; they do not establish label validity, physical accuracy, H1 admission, or manufacturing compliance.

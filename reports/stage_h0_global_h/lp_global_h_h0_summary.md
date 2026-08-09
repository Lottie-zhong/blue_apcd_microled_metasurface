# Stage H0 - LP Global-H readiness / phase-reference audit

- Branch: `work/lp-global-h-manifold-v1`
- HEAD: `208059092011c18628be859e6caaa9d14120f198`
- `solver_runs_new = 0`
- `entered_true_new = 0`
- NP active runner isolation: `PASS`

## Verdicts

- `phase_reference_verdict`: `PHASE_REFERENCE_SAFE_AS_IS`
- `global_h_builder_verdict`: `UNIFIED_GLOBAL_H_CODE_FIXED_AND_TESTED`
- `level3_baseline_reproduction_verdict`: `REPRODUCED_WITH_EXPLICIT_SCOPE_SPLIT`

## Phase reference

The formal builder keeps both pillar bottom planes at `z=0`, changes only the shared pillar top `H_global`, keeps the source at `z=-250 nm`, and keeps transmission and field monitors at `z=1000 nm`. The 432 nm periodic cell, FDTD z bounds, coordinate-weighted full-period G0 extraction, endpoint handling, and `sqrt(T)/norm(weighted Ex,Ey)` normalization remain fixed. Verdict: `PHASE_REFERENCE_SAFE_AS_IS`; explicit de-embedding is not required before an H sweep.

## Dirty-worktree provenance

- Dirty tracked files: `17`
- Untracked files: `204`
- Old LP modified by H0: `false`
- Physics admitted from dirty/untracked files: `false`
- Unknown-provenance physics admitted: `false`

## H=500 baseline

The authoritative quarantine excludes only exact hash `f6bcfd429f3cd1b722f520bc67dbc62501854a686b17d8deae492cc66e950b21` and records `admitted_physics_rows = 0`. Legal suffix-054 geometries with different exact hashes remain admitted. The corrected read-only analysis admits `409` unique geometries from `412` raw rows; phase-only and full-Jones scopes are both `409` unique rows, while x-only evidence is not admitted to ML.

- Historical real phase: `62.053626948833 to 106.897832948482 deg`; raw span `44.844205999649 deg`; circular coverage `44.844205999649 deg`.
- Historical quantile best-50 projector slice: `27.845019017638 deg`.
- Dedicated 24-geometry formal probe projector-compatible slice: `18.557501177498 deg` (the approximately 18.56 deg handoff value; separate from the historical 409-row quantile slice).
- Raw extrema, circular coverage, and display-only unwrapped representation are separate fields in the JSON utility.

## Artifacts and reproduction

- Machine-readable audit: `outputs/lp_global_h_h0/lp_global_h_h0_audit.json`
- Anchor manifest: `reports/stage_h0_global_h/anchor_manifest.json`
- Analyzer: `python scripts/lp_global_h_h0_audit_v1.py`
- Tests: `python -m pytest tests/test_lp_global_h_h0.py`
- No FDTD, new entered case, NP worktree/runtime write, or protected/raw evidence write occurred.

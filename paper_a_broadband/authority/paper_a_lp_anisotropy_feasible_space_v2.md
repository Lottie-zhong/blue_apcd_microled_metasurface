# Paper A LP anisotropy feasible-space V2 authority

`LP_ANISOTROPY_FEASIBLE_SPACE_V2` is a zero-solver pre-admission planning stage.

Scientific state: `PAPER_A_LP_ANISOTROPY_FEASIBLE_SPACE_V2_PLANNED`.
Scientific readiness: `INITIAL_TRUTH_CANDIDATES_READY`.
Solver state: `WAIT_EXTERNAL_SOLVER_ADMISSION`.

The candidate set is selected from the current six-dimensional box after exact integer/half-grid quantization and exact polygon direct/periodic-image distance checks. Selection is geometry-only; no optical ranking is present.

Transferred hard gates are direct clearance >=60 nm, periodic-image clearance >=60 nm, no overlap/touching, cell containment, integer lateral dimensions, and half-grid-compatible centers. No current authoritative minimum linewidth/aspect-ratio hard gate was found; minimum feature and H/min-feature are diagnostics only.

AF01-AF04 are initial setup-only x/y candidates. AF05-AF08 are conditional registry-only candidates. No solver is authorized or queued by this artifact.

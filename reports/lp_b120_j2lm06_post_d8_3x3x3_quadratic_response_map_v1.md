# APCD LP POST-D8 3x3x3 Quadratic Response Map v1

## Status
`HARD_GATE_DATA_CONFLICT` before solver entry.

## Environment and accounting
Expected HEAD `4f4964310c88e05768816f6129ef78f4e027a79c`. Planned: 18 new geometries / 36 x-y subruns / 450 nm. Actual solver invocations: 0; accepted/recovered/failed: 0/0/0; missing: 36. Phase A and Phase B were not started. No execution package or physics staging was created.

## Geometry-grid conflict
The frozen mapping uses J2 width `100+uW`, relative x separation `200.5+0.5*uD` nm and relative y separation `1+uPsi` nm, with D/Psi recomputed from integer/half-grid centers. It produces 27 symbolic coordinates but only 22 physically unique geometries because five required new coordinates duplicate existing formal geometries.

| planned coordinate | planned ID | existing formal geometry |
|---|---|---|
| `(-1, 0, 0)` | `POSTD8_QMAP_WM_D0_P0` | `D8_TRV_PLAN_2709798bc19d7b76` |
| `(0, 0, -1)` | `POSTD8_QMAP_W0_D0_PM` | `D8_TRV_PLAN_3f9495af463cc07b` |
| `(1, 0, -1)` | `POSTD8_QMAP_WP_D0_PM` | `POSTD8_CAL_PROBE_WP_DM_PM` |
| `(-1, 0, 1)` | `POSTD8_QMAP_WM_D0_PP` | `POSTD8_CURV_MIRROR_WP_DM_PM` |
| `(-1, 0, -1)` | `POSTD8_QMAP_WM_D0_PM` | `D8_TRV_PLAN_2c6c4edac3638079` |

The task contract explicitly requires 18 new geometries and forbids existing-geometry reruns, point removal, substitution, or dynamic insertion. Therefore execution cannot proceed without a revised geometry-grid contract. No quadratic design matrix, active 3x3 Hessian, holdout validation or 27-point Pareto result is claimed.

## Constraints
Existing D7/D8/recalibration/curvature/canonical physics remained read-only. No D9, K6/K7, spectrum, tolerance, Micro-LED device simulation, canonical merge, model training, solver retry or external-process termination occurred.

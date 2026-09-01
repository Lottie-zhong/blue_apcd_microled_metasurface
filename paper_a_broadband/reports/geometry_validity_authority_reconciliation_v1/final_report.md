# Geometry-validity authority reconciliation

Status: PASS

## A02 disposition

A02 remains `A02_BENCHMARK_REJECTED_CURRENT_GEOMETRY_CONTRACT`. The old 0.032 nm value is a pillar_2-to-bottom-cell-boundary margin. It is not a pillar-pillar or translated periodic polygon gap. The corrected physical gaps are 44.531995530125 nm direct and 52.531995530125 nm periodic, and the exact 195.5/76.5 nm lateral dimensions violate the current integer-lateral contract. The old doubled-boundary interpretation remains retained as superseded provenance.

## Lineage

The early `lp_anisotropy_bootstrap_v1.py` aggregate `min_edge_gap_nm` mixed cell-boundary margins with polygon distances and only made containment/overlap validity decisions. The corrected V2 method computes direct and translated-polygon segment distances separately. The current authority inherits those exact distances and the 60 nm, overlap/touch, containment, integer-lateral, and half-grid gates. No new threshold was introduced.

## Current authority audit

15 unique geometry records covering BF01-BF04, BF04R I01-I04, BF04R C01/C02, I03/IC1/IC2, IAR1-IAR4, and IAR4-OC1 were independently recomputed. All current authority geometries pass: `True`. Scientific truth was not modified.

## Historical disposition

A01-A08 remains earlier design-stage provenance. The existing corrected audit was read only for classification; it changes no DOE, ranking, candidate selection, admission, or solver budget. Current science is I03 intrinsic local basin -> finite integrated source/angular cancellation -> integrated-aware IAR4 -> IAR4-OC1 orientation causal evidence.

## Safety

Zero-solver reconciliation: NEW_FDTD_BUDGET=0, solver_run_called=false, solver_entered=0, RCWA=0, ML=0. No geometry, truth, candidate, protected file, or frozen upstream worktree was modified.

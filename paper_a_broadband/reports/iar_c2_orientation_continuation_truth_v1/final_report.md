# IAR-C2 / IAR-C2-OC80 bounded validation

This is the final bounded local integrated-aware LP validation batch. It uses current Native-M1, the existing finite 3000 x 3000 nm mesa / centered 5 x 5 architecture, 400-500 nm and 101 points, and sourcepower normalization. W_emit remains unresolved; no historical Gaussian or absolute LEE claim is used.

## Solver truth

Four independent cases were authorized and run sequentially with 12 MPI processes x 1 thread and PAPER_A active FDTD <= 1. Pair Stokes uses S_i,pair = 0.5 S_i,x + 0.5 S_i,y; fields are not coherently added and DoLP/psi are not averaged.

## 450 nm anchor

| candidate | pair DoLP | C_source | C_angular | upward top-face/source | useful LP | useful LP/S0 |
|---|---:|---:|---:|---:|---:|---:|
| IAR-C2 | 0.0560096693 | 0.135145624 | 0.112340416 | 0.00741511779 | 1.93072223 | 0.528004835 |
| IAR-C2-OC80 | 0.0631160583 | 0.157797178 | 0.1106319 | 0.00742685348 | 1.95027238 | 0.531558029 |

## Scope boundaries

The OC80-C2 comparison is the strict orientation continuation comparison; C2-IAR4 is a local-basin/clearance transfer comparison; OC80-IAR4 is a practical continuation comparison. 445-455 nm is an unweighted diagnostic window and 400-500 nm is a diagnostic band. No new composite score or promotion threshold is introduced. Chart retains the final LP GO/STOP decision.

## Status

4/4 individual validity and both pair closeouts are PASS. Individual validity status is `VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH`; the active V2 instrumented contract is retained in each validity artifact. Solver accounting: {"authorized": 4, "entered": 4, "returned": 4, "accepted": 4, "replay": 0, "RCWA": 0, "ML": 0}; active FDTD after closeout: 0.

## Artifacts

See `canonical_geometry_provenance.json`, `per_source_validity/`, the three comparison JSON files, `spectral_delta_metrics.csv`, `absolute_performance_summary.json`, `power_collapse_audit.json`, `solver_accounting.json`, and `validation_tests.json`. Runtime FSP/MAT/LOG remain outside Git.

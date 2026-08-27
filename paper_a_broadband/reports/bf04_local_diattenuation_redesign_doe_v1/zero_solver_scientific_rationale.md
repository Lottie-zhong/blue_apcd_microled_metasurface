# BF04 local diattenuation redesign DOE v1

Status: `BF04_LOCAL_DOE_READY_FOR_INITIAL_TRUTH`

This is a zero-solver geometry-only mechanism DOE around exact BF04. The purpose is to preserve the discovered high-`delta_theta` dominant-channel stability while probing stronger singular-channel separation / diattenuation. No optical performance is predicted and no scalar gap proxy is used as a performance ranking.

## Domain and gates

The local continuous neighborhood is the intersection of the frozen global anisotropy-expanded domain and BF04 +/-5% for L1/W1/L2/W2, BF04 +/-7.5 deg for `delta_theta`, and BF04 +/-12 nm for D. After existing Paper A quantization, the dense deterministic Sobol pool used 16384 raw samples, 16384 unique quantized samples, and 10439 feasible geometries. The exact existing hard gates are direct polygon clearance >=60 nm, periodic-image polygon clearance >=60 nm, no overlap/touching, cell containment, integer lateral dimensions, and half-grid-compatible centers.

## Mechanism coordinates

Every feasible geometry records A1=(L1-W1)/(L1+W1), A2=(L2-W2)/(L2+W2), A_mean, Delta_A=A1-A2, D, delta_theta, footprint-related dimensions, and both clearances. The six selected geometries are intentionally geometry-only probes; BF05-BF08 were not reused.

## Selected candidates

| ID | role | mechanism direction | L1/W1/L2/W2 nm | A1/A2/A_mean/Delta_A | total footprint nm2 / fill | delta_theta deg | D nm | direct / periodic nm |
|---|---|---|---|---|---:|---:|---:|---:|
| BF04R_I01 | INITIAL_LOCAL_MECHANISM_CANDIDATE | increase A_mean while approximately preserving Delta_A | 261/89/207/77 | 0.491429/0.457746/0.474588/0.033682 | 39168 / 0.209877 | 81.518898904 | 213 | 60.453715 / 66.453715 |
| BF04R_I02 | INITIAL_LOCAL_MECHANISM_CANDIDATE | decrease A_mean while approximately preserving Delta_A | 244/95/194/80 | 0.439528/0.416058/0.427793/0.023470 | 38700 / 0.207369 | 81.618082523 | 216 | 66.705284 / 66.705284 |
| BF04R_I03 | INITIAL_LOCAL_MECHANISM_CANDIDATE | increase Delta_A while approximately preserving A_mean | 264/87/194/80 | 0.504274/0.416058/0.460166/0.088215 | 38488 / 0.206233 | 85.819861293 | 220 | 76.842340 / 68.842340 |
| BF04R_I04 | INITIAL_LOCAL_MECHANISM_CANDIDATE | decrease or reverse Delta_A while approximately preserving A_mean | 245/93/207/77 | 0.449704/0.457746/0.453725/-0.008042 | 38724 / 0.207497 | 89.696137458 | 215 | 64.797276 / 66.797276 |
| BF04R_C01 | CONDITIONAL_LOCAL_MECHANISM_CANDIDATE | reduce D while retaining high delta_theta | 263/87/198/78 | 0.502857/0.434783/0.468820/0.068075 | 38325 / 0.205359 | 82.744267434 | 207 | 60.367130 / 78.367130 |
| BF04R_C02 | CONDITIONAL_LOCAL_MECHANISM_CANDIDATE | small delta_theta perturbation with approximately preserved anisotropy | 244/88/199/78 | 0.469880/0.436823/0.453351/0.033056 | 36994 / 0.198227 | 82.728939056 | 215 | 67.364149 / 69.364149 |

The high-`delta_theta` BF04 mechanism is preserved by construction: every selected candidate lies in the local high-angle neighborhood, and the conditional D probe explicitly retains `delta_theta >= BF04-3 deg`. This DOE is ready for future initial truth only; no solver is authorized by this artifact.

## Safety

`NEW_FDTD_BUDGET=0`; `solver_run_called=false`; `solver_entered=0`; RCWA=0; ML=0; BF05-BF08 not run; no geometry/physics/source/monitor/mesh/boundary contract was changed.

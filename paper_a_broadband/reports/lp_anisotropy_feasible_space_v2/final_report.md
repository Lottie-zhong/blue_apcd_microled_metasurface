# LP anisotropy feasible-space V2 pre-admission report

Status: PASS (zero-solver planning and setup-only audit)

- Physics box: a1,b1,a2,b2 in [0.85, 1.15], delta_theta in [0, 90] deg, D in [170, 220] nm.
- Frozen backbone: current Paper A H=525 nm, Px=Py=432 nm, Native-M1, existing broadband full-Jones template.
- Formal legality: exact direct and periodic-image polygon clearance >=60 nm, no overlap/touch, containment, integer lateral dimensions, half-grid-compatible centers.
- Selection used geometry only; no optical information, RCWA, ML, surrogate or solver metrics.

Raw Sobol points: 4096; feasible unique pool: 8 selected from 1879 feasible unique points.

## Selected geometries

| ID | Role | L1/W1/L2/W2 (nm) | theta1/theta2 (deg) | D (nm) | direct (nm) | periodic image (nm) | global min (nm) | min feature (nm) | H/min feature |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AF01 | INITIAL | 229/102/173/89 | 0.0/44.538574219 | 207 | 63.611187 | 81.611187 | 63.611187 | 89 | 5.898876 |
| AF02 | INITIAL | 196/85/153/77 | 0.0/0.0 | 170 | 89.000000 | 181.000000 | 89.000000 | 77 | 6.818182 |
| AF03 | INITIAL | 259/86/203/97 | 0.0/3.098144531 | 172 | 75.085169 | 163.085169 | 75.085169 | 86 | 6.104651 |
| AF04 | INITIAL | 215/109/204/80 | 0.0/1.779785156 | 171 | 73.351369 | 163.351369 | 73.351369 | 80 | 6.562500 |
| AF05 | CONDITIONAL | 197/88/203/101 | 0.0/4.284667969 | 196 | 94.057883 | 134.057883 | 94.057883 | 88 | 5.965909 |
| AF06 | CONDITIONAL | 256/91/204/77 | 0.0/82.727050781 | 219 | 67.446702 | 61.446702 | 61.446702 | 77 | 6.818182 |
| AF07 | CONDITIONAL | 258/107/159/103 | 0.0/6.789550781 | 180 | 65.962446 | 137.962446 | 65.962446 | 103 | 5.097087 |
| AF08 | CONDITIONAL | 255/115/205/101 | 0.0/20.280761719 | 217 | 76.602105 | 74.602105 | 74.602105 | 101 | 5.198020 |

Initial truth candidates: AF01–AF04 (x/y setup-only prepared; no solver entry).
Conditional registry-only candidates: AF05–AF08.

Old A01–A08 remains immutable planning provenance; DOE was not changed.
No authoritative current minimum-linewidth or aspect-ratio hard gate was found in the transferred formal legality authority; those values are diagnostics only.

Safety: NEW_FDTD_BUDGET=0; solver_run_called=false; solver_entered=0; no READY/pending/hidden admission; no global scheduler policy change.

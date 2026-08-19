# LP anisotropy V2 balanced mechanism-stratified selection

Status: PASS. The original 1879-point feasible pool was reused unchanged.

Initial truth candidates: BF01–BF04, exactly one in each S1–S4. Conditional truth candidates: BF05–BF08, exactly one in each S1–S4.

Selection uses only normalized six-dimensional geometry coordinates. No optical data, FDTD, RCWA, ML, surrogate, DoLP, power, phase, Jones or CP response was used.

| ID | Role | Stratum | L1/W1/L2/W2 nm | theta1/theta2 deg | D nm | direct / periodic / global nm | min feature | H/min feature | A1/A2/delta_A | lineage |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| BF01 | INITIAL_TRUTH_CANDIDATE | S1 | 196/85/153/77 | 0.000000/0.000000 | 170 | 89.000000 / 181.000000 / 89.000000 | 77 | 6.818182 | 0.395018/0.330435/0.064583 | AF02 |
| BF02 | INITIAL_TRUTH_CANDIDATE | S2 | 229/102/173/89 | 0.000000/44.538574 | 207 | 63.611187 / 81.611187 / 63.611187 | 89 | 5.898876 | 0.383686/0.320611/0.063075 | AF01 |
| BF03 | INITIAL_TRUTH_CANDIDATE | S3 | 264/87/153/98 | 0.000000/64.533691 | 220 | 86.363838 / 78.363838 / 78.363838 | 87 | 6.034483 | 0.504274/0.219124/0.285150 | - |
| BF04 | INITIAL_TRUTH_CANDIDATE | S4 | 256/91/204/77 | 0.000000/82.727051 | 219 | 67.446702 / 61.446702 / 61.446702 | 77 | 6.818182 | 0.475504/0.451957/0.023547 | AF06 |
| BF05 | CONDITIONAL_TRUTH_CANDIDATE | S1 | 259/86/203/97 | 0.000000/3.098145 | 172 | 75.085169 / 163.085169 / 75.085169 | 86 | 6.104651 | 0.501449/0.353333/0.148116 | AF03 |
| BF06 | CONDITIONAL_TRUTH_CANDIDATE | S2 | 264/111/206/78 | 0.000000/23.620605 | 193 | 60.497579 / 106.497579 / 60.497579 | 78 | 6.730769 | 0.408000/0.450704/-0.042704 | - |
| BF07 | CONDITIONAL_TRUTH_CANDIDATE | S3 | 202/86/198/100 | 0.000000/50.449219 | 214 | 62.826915 / 66.826915 / 62.826915 | 86 | 6.104651 | 0.402778/0.328859/0.073919 | - |
| BF08 | CONDITIONAL_TRUTH_CANDIDATE | S4 | 206/112/157/103 | 0.000000/87.099609 | 212 | 74.994670 / 82.994670 / 74.994670 | 103 | 5.097087 | 0.295597/0.207692/0.087905 | - |

Previous AF01–AF08 remain valid geometry records but are superseded for truth role by this balanced selection.

Solver state: WAIT_EXTERNAL_SOLVER_ADMISSION. NEW_FDTD_BUDGET=0; no server-performance benchmark.

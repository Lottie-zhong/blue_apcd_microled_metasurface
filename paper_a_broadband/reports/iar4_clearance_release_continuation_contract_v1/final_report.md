# IAR4 clearance-release continuation contract

Status: PASS (zero-solver geometry-only pre-admission planning).

- Strict causal pair: IAR4 <-> IAR4-OC1.
- Top-level causal verdict: ORIENTATION_CAUSAL_EFFECT_WAVELENGTH_DEPENDENT; 450 nm smaller delta-theta favored.
- W_emit unresolved; no optical ranking, composite score, or new threshold used.
- Current corrected direct/periodic polygon authority used; A01-A08 planning validity artifacts not reused.

IAR4 exact: L1/W1/L2/W2=259/87/203/79 nm, D=210 nm, delta_theta=82.820909321 deg, H=525.0 nm, Px=Py=432.0 nm.
IAR4 high-precision clearance: direct=60.859360975715348347637952821549510528304012692031 nm; periodic-image=72.859360975715348347637952821549510528304012692031 nm.

| D (nm) | min legal delta_theta (deg) | direct (nm) | periodic (nm) | min headroom over 60 (nm) |
|---:|---:|---:|---:|---:|
| 208 | 85.105630507 | 60.000000000151 | 76.000000000151 | 0.000000000151 |
| 209 | 83.121772635 | 60.000000000391 | 74.000000000391 | 0.000000000391 |
| 210 | 80.824233962 | 60.000000000254 | 72.000000000254 | 0.000000000254 |
| 211 | 80.000000000 | 60.682910051417 | 70.682910051417 | 0.682910051417 |
| 212 | 80.000000000 | 61.682910051417 | 69.682910051417 | 1.682910051417 |
| 213 | 80.000000000 | 62.682910051417 | 68.682910051417 | 2.682910051417 |
| 214 | 80.000000000 | 63.682910051417 | 67.682910051417 | 3.682910051417 |
| 215 | 80.000000000 | 64.682910051417 | 66.682910051417 | 4.682910051417 |
| 216 | 80.000000000 | 65.682910051417 | 65.682910051417 | 5.682910051417 |
| 217 | 80.000000000 | 66.682910051417 | 64.682910051417 | 4.682910051417 |
| 218 | 80.000000000 | 67.682910051417 | 63.682910051417 | 3.682910051417 |
| 219 | 80.824233962 | 69.000000000254 | 63.000000000254 | 3.000000000254 |
| 220 | 82.021870357 | 70.500000000239 | 62.500000000239 | 2.500000000239 |

Theta floor 80 deg is legal for D=211, 212, 213, 214, 215, 216, 217, 218 nm.
IAR4-CR1 prospective/not-authorized: D=211 nm, delta_theta=80.000000000 deg, D change=+1 nm, theta change=-2.820909321 deg.
CR1 high-precision clearance: direct=60.682910051417133194632776246775479670414870701665 nm; periodic-image=70.682910051417133194632776246775479670414870701665 nm.
No CR2 is needed because D-only is feasible. IAR-C2 remains reference-only and is not an orientation-only control.

Future plan only: IAR4-CR1 + IAR-C2, x/y each, maximum 4 FDTD jobs after separate authorization. Current solver budget is zero.
No authoritative linewidth/aspect-ratio hard threshold was found; existing geometry gates are unchanged.

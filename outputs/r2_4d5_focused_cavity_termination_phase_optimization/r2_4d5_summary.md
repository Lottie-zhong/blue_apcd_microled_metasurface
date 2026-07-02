# R2-4D5 Focused Cavity/Termination Phase-Guided Optimization

No FDTD, Lumerical, lumapi, setup-only FSP, LDF, MAT/H5, or raw monitor data were created.

## Scope

- Primary seed: `R2_4B_OPT_06176`
- Fixed pair counts: top=10, bottom=12
- Trials evaluated: 34200
- Robust combined TE/TM shortlist exists: `True`
- Best candidate ID: `D5_BASE_13461`

## Top 5 Phase-Guided Candidates

| candidate | score | cavity | top term | bottom term | worst normal err deg | worst margin deg | conservative N/O | accept |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| D5_BASE_13461 | 533449968802.703 | 182.0 | 0.0 | 113.0 | 1.102 | 40.971 | 1.33e+11 | True |
| D5_BASE_13481 | 488493247715.276 | 182.0 | 5.0 | 108.0 | 1.082 | 40.931 | 1.22e+11 | True |
| D5_BASE_13881 | 473813957985.129 | 183.0 | 0.0 | 113.0 | 2.967 | 35.513 | 1.18e+11 | True |
| D5_BASE_14322 | 458856152817.588 | 184.0 | 5.0 | 113.0 | 2.275 | 38.456 | 1.15e+11 | True |
| D5_BASE_08955 | 341545142538.383 | 171.0 | 30.0 | 53.0 | 2.685 | 36.224 | 8.54e+10 | True |

## Final Shortlist

| role | candidate | cavity | top term | bottom term | TE normal err | TM normal err | TE margin | TM margin | TE 30-40 risk | TM 30-40 risk | avg normal resonance | N/O proxy | top outcoupling |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D5_PRIMARY | D5_BASE_13461 | 182.0 | 0.0 | 113.0 | 1.102 | 1.102 | 138.654 | 40.971 | 131.999 | 9.682 | 453.00 | 1.33e+11 | 0.136 |

## Interpretation

The shortlist is still a TMM phase/outcoupling proxy. It is ready for setup-only FSP generation only after review; FDTD should wait until the generated geometry is GUI-inspected.

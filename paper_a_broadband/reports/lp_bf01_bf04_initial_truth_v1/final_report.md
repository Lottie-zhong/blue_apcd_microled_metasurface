# Paper A LP balanced initial truth v1

Status: `PAPER_A_LP_BALANCED_INITIAL_TRUTH_COMPLETE`

Current Native-M1; source/monitor 430-470 nm; formal axis-free full-Jones evaluation 435-465 nm at 1 nm; zero-order J_xy from independent x/y inputs.
Solver entered: 8/8. Conditional BF05-BF08 was not authorized or run.

| geometry | weighted DoLP | weighted P_LP | FWHM psi span | FWHM DoLP worst | pass | promising |
|---|---:|---:|---:|---:|---|---|
| BF04 | 0.441575 | 0.477642 | 39.625 | 0.051591 | False | False |
| BF03 | 0.141874 | 0.385328 | 229.842 | 0.009418 | False | False |
| BF02 | 0.133706 | 0.388518 | 165.222 | 0.020359 | False | False |
| BF01 | 0.121789 | 0.380843 | 90.000 | 0.023330 | False | False |

## Integrity note

The zero-solver closeout entered no new solver. BF04_y retains its pre-entry authority hash and V2 validity; a post-entry on-disk pre-FSP drift is recorded as a provenance warning in input_chain_audit.json. No replay or repair was performed.

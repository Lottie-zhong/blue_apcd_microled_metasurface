# BF08 attempt_003 measurement/provenance forensic

## Status

PASS — `PAPER_A_LP_BF08_ATTEMPT003_ROOT_CAUSE_NUMERICAL_TIME_DOMAIN_DIVERGENCE_CONFIRMED`

## Root cause

The negative values are not a monitor-normal, forward/backward, placement, wavelength-index, or downstream normalization artifact. They are stored solver outputs from a numerically divergent 5 ps time-domain run. BF08_x ended with auto-shutoff `2367.4` (peak `2448.03`); BF08_y ended at `1.64048`. The same source/monitor convention gives nonnegative formal transmission for all 14 BF01-BF07 x/y controls.

BF08_x and BF08_y differ only in source polarization angle. Their divergence severity tracks that basis change, consistent with polarization-dependent excitation of a numerically unstable BF08 mode; provenance cannot identify the mode itself.

## Authority boundary

The fresh pre-FSP setup provenance remains valid, but both attempt_003 post-FSP result states are invalid for physics truth. No zero-solver post-processing can recover them. The base LP monitor/full-Jones convention has no systematic sign or placement defect; the runner lacks a mandatory late-time divergence gate. Existing BF01-BF04 truth is unaffected. Future BF01-BF04 runs may use only the proven original contract; the BF08 5 ps replay patch is not safe to generalize without new authority and a convergence gate.

No solver was run, no truth file was modified, and no attempt was promoted.

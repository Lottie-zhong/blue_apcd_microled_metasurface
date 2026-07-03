# Recommended R2-4E1 Plan

Recommended task name: **R2-4E1_Python_only_new_family_candidate_generator_proxy_scan**.

E1 should be a Python-only candidate generator and proxy scan, not FDTD.

## E1 Scope
- Generate candidates from the E0 new design families instead of reusing the D9 no-pass pool.
- Include lower-Q angle-stable, phase-balanced 30-40 rejection, finite-MQW source-position robust, and reduced-center-contrast families.
- Score candidates with D8/D9 proxy terms baked in from the start.
- Explicitly mark source-position stability as requires_tri_point_FDTD; do not claim it is proven by Python-only proxy.
- Produce at most a tiny FDTD-ready shortlist, preferably 0-2 candidates.

## E1 Must Not Do
- Do not launch Lumerical.
- Do not generate setup-only FSPs.
- Do not run tri-point FDTD; that belongs to a later stage after E1 review.

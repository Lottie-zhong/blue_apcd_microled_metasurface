# R2-4G3 Proxy v1 Scoring Definition

Proxy v1 is a reject/risk proxy, not a success predictor. The dataset has only negative samples, so it cannot train or claim a positive pass classifier.

Relaxed final FDTD targets remain:
- spectral FWHM <= 10 nm;
- angular FWHM <= 20 deg;
- peak_abs_angle <= 8 deg.

These are final FDTD pass targets, not Python-only success claims.

Risk-score proposal:
- hard_reject component: +100 each;
- strong_warning component: +20 each;
- weak_warning component: +5 each.

Candidate FDTD entry gate for future G4 output:
- no hard_reject;
- total_risk_score < 40;
- no D5-like, E1-like, F0_0781-like, or F0_0204-like red flags;
- source_position_status remains `requires_tri_point_FDTD`, never `pass`;
- candidate must include route family and full structure parameters;
- shortlist maximum 1 primary + 1 backup;
- if no candidate passes, output no-pass and do not force shortlist.

Do not overfit by rejecting all literature-seeded routes unless they match known failure modes. A 25-30 deg route may be recorded as an intermediate literature baseline, but not as final relaxed-target pass.

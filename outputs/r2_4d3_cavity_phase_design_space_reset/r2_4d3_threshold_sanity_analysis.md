# R2-4D3 Threshold Sanity Analysis

Essential protections to keep:

- 20-60 deg off-axis penalty.
- 30-40 deg resonance penalty.
- minimum normal-window response.
- no strong multi-peak behavior.

Thresholds that may be too strict for proxy-only screening:

- peak_abs <= 5 can remain preferred, but <= 7 is a practical first-screen maximum.
- spectral peak 450-456 is physically motivated, but a temporary 448-458 scout band may diagnose phase reachability.
- population-relative normal/off-axis thresholds rejected all candidates and should be calibrated with negative samples, not used blindly.

Recommendation: do not relax the negative-sample protections; instead run a focused cavity-phase/variable-space reset to move spectral centering and angular risk together.

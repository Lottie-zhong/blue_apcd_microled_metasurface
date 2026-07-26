# NP-K6 P1-D2B2 H500 D110 x broadband pillar

## Scope and execution evidence

- Case: `NP_P1D2_BROADBAND_PILLAR_H500_D110_X`; H=500 nm, D=110 nm, radius=55 nm, gap=180 nm, AR=4.5454545.
- x-polarized normal incidence; source 440–460 nm; exact analysis axis 445–455 nm in 1 nm increments.
- One foreground SSH solver call entered and completed. The pre/post FSP SHA-256 values are recorded in `run_manifest.json`; post-FSP extraction was read-only.
- The contracted 33-monitor single-wavelength backend and blank/pillar physical contract gates passed. D105→D110 differs only in the allowed geometry, case, hash, and output-path fields.

## D110 broadband results

- T: 0.98060838–0.98750732; R_total: 0.01268937–0.01904445.
- |t_xx|: 0.98222205–0.98666585; CV=0.00143690; max |t_yx|=1.38527e-9.
- Wrapped-reference phase: 78.59259° (445 nm), 75.04728° (450 nm), 71.79492° (455 nm); 445→455 shift=-6.79768°, slope=-0.679280°/nm, fit RMS=0.052044°.
- Max energy residual=0.000347174; max reconstruction residual=0.03924799. The formal data-quality status is `warning_valid`, and P1D2B2 formal status is `pass`.

## Adjacent pair and provisional local line

- D105→D110 relative phase: 15.43325° (445 nm), 14.53813° (450 nm), 13.72947° (455 nm); mean=14.55477°, std=0.53785°, peak-to-peak=1.70378°, max deviation from 450 nm=0.89512°.
- Differential slope=-0.170012°/nm; differential-fit RMS=0.015493°; amplitude-ratio mean=0.997888; mean T difference=-0.004169. Pair stability is `stable`.
- `partial_line_d100_d105_d110.json` is explicitly provisional. It provides local diameter-chain unwrapping, local slopes, curvature, and pair-step differences only; it makes no phase-library, 2pi, six-bin, or K6 claim.

## Historical 450 nm cross-contract audit

- Official comparison source: `outputs/np_k6_p1d1a0_h500_d110_v1/results.json`; its values are read unchanged.
- At 450 nm, |ΔT|=0.017113, |ΔR_total|=0.000338, Δ|t_xx|=0.036926, and minimal wrapped phase difference=-16.18536°.
- The audit status is `warning_review`: amplitude/power thresholds pass, while phase is in the 10–20° review range. Source spectrum, monitor backend/priming, and matched broadband blank differences are recorded as expected contract differences, so strict equality is not required.

## Release state

- Tests after extraction: 10 passed.
- `P1D2_D115_READY=true`; next authorized action is `BROADBAND_PILLAR_D115_X_ONLY`.

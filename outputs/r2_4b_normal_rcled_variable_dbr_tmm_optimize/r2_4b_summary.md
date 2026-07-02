# R2-4B Normal RCLED Variable DBR TMM-Style Proxy Optimization

No FDTD, Lumerical, FSP, LDF, or raw monitor data were created. This is a Python-only multilayer proxy screen with fixed seed `20260701`.

## Best Candidate

- candidate_id: `R2_4B_OPT_06361`
- top_pair_count: 8
- bottom_pair_count: 12
- cavity_spacer_nm: 336.0
- top_termination_nm: 63.0
- bottom_termination_nm: 61.0
- peak_abs_angle_deg at 453 nm: 7.0
- angular_FWHM_deg at 453 nm: 12.986
- normal/off-axis ratio: 21.030296
- normal-window spectral peak: 452.25 nm
- normal-window spectral FWHM: 5.462 nm
- pass level: acceptable_proxy_pass

## Interpretation

The proxy found normal-direction candidates that improve the normal/off-axis metric relative to the rejected off-axis route. The numbers are not FDTD evidence; they are only a cheap ranking filter for setup-only FSP generation.

## References

R2_1_00223 and R2_1_04067 were not recomputed here. They remain prior-stage references, and R2-4B should be compared to them only after identical 2D FDTD smoke validation.

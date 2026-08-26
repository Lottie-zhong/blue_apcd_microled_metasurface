# Figure and numerical QA notes

Task: BF04_POLARIZATION_MECHANISM_DIAGNOSTIC_V1
Backend: Python/matplotlib only.

## Numerical QA

- Source rows: 124 = 4 candidates x 31 formal wavelengths.
- Formal grid: exact 435-465 nm at 1 nm; no interpolation or row deletion.
- SVD reconstruction max absolute error: 5.722e-16.
- Source singular-value consistency: PASS.
- U1 phase ambiguity handled with phase-invariant absolute overlaps; Stokes descriptors are phase invariant.
- Canonical raw low-DoLP psi values remain in the data and plots; bottom-quartile marking is diagnostic only.

## Panel audit

| Figure | Panels | Unique claim | Visual check |
|---|---:|---|---|
| figure_svd_channel_separation | 4 | singular values and channel separation across the formal spectrum | PASS; corrected labels, no collisions |
| figure_dominant_channel_stability | 4 | U1 orientation, ellipticity, reference and adjacent stability | PASS; FWHM band and labels clear |
| figure_poincare_stokes_trajectories | 4 | normalized Stokes trajectory comparison | PASS; color scale and endpoints clear |
| figure_bf04_failure_attribution | 6 | BF04 DoLP collapse versus gap, axis stability and ellipticity | PASS; low-DoLP markers retained |

## Export QA

- Python source validator: PASS, 20 PASS / 0 WARN / 0 FAIL.
- Four PDF text audits: PASS; minimum text sizes 6.0-7.0 pt, no glyph below 5 pt.
- SVG/PDF editable text configured; TIFF 600 dpi; PNG 300 dpi.
- No solver, RCWA, ML, or BF05-BF08 execution occurred in this diagnostic.

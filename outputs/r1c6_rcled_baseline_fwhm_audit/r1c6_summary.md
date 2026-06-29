# R1C6 RCLED Baseline FWHM Audit

## Angular FWHM

| wavelength_nm | angular_FWHM_deg | status | source |
|---:|---:|---|---|
| 450 | 46.49419962557087 | directly_extracted | r1c4_source_y_results.csv |
| 453 | 46.86880208688322 | directly_extracted | r1c4_source_y_results.csv |
| 456 | 19.527357789035474 | directly_extracted | r1c4_source_y_results.csv |

Angular FWHM was directly extracted from existing R1C4 center-source output when available.

## Spectral FWHM

Spectral FWHM is not yet available. No continuous spectral scan was found for `R1C2_C2_cav230`; the existing validated wavelengths are 450, 453, and 456 nm only. Spectral FWHM cannot be computed from only 450/453/456.

## Recommended Next Stage

If spectral FWHM is needed, run a small spectral scan around 445-460 nm for `C2_cav230`.

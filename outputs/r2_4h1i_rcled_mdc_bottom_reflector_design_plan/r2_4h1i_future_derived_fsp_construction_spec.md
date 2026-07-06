# R2-4H1I future derived-FSP construction specification

H1I is planning only. It does not open, modify, copy, or save any `.fsp` file.

Future H1J/H1K derived FSP construction should start from `F:\wc_312\MDC_blue_oujizi.fsp`, keep the existing top MDC unchanged, disable PlaneSource `source`, and keep DipoleSource `source_1` as the x-oriented electric dipole with theta=90 deg, phi=0 deg, wavelength 450 nm.

The first derived design should add a bottom DBR under the LED/source region on the negative-y side. The primary bottom reflector is `DBR_QW_exact_450_10pair` using TiO2 44.368 nm / SiO2 78.886 nm for 10 pairs. The estimated DBR thickness is 1232.5 nm. A secondary comparison is `DBR_Huang_like_10pair` using TiO2 50 nm / SiO2 77 nm for 10 pairs.

The source must remain between the bottom DBR and top MDC. The bottom DBR must not overlap source_1 at y=-800 nm. Because the 10-pair DBR is about 1.2-1.3 um thick, the FDTD y-min boundary will likely need to move downward with a PML safety margin.

Cavity length is not finalized in H1I. It should be recorded as a follow-up geometry variable after a no-run H1J geometry audit.

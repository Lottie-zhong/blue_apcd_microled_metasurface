# Future H1L FDTD Validation Constraints

H1L is allowed only after explicit user approval. H1K4 itself does not run FDTD.

Required H1L constraints:

- x-only / x-dipole
- wavelength = 453 nm
- source-isolated
- PlaneSource disabled
- source_1 positions at least x = -2500 nm, 0 nm, +2500 nm
- y fixed at -800 nm unless explicitly changed
- incoherent intensity/power averaging across source positions
- no center-only validation
- no y-dipole
- no broadband
- no APCD coupling

Required metrics:

- peak_angle_deg
- angular_FWHM_deg
- eta5, eta10, eta20
- leakage20_40
- leakage40_60
- normal_to_40_60_ratio
- double_lobe_flag if applicable
- comparison to H1H corrected MDC-only benchmark

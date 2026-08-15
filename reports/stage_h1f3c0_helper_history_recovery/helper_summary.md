# H1F-3C0 Historical Helper / Trimer Physics Evidence Recovery

Status: PASS; zero solver.

- Actual historical helper FDTD exists in the separate `red_plane_wave_metasurface_archive`; representative v8 `hr_aniso_push_08` has X/Y FSP artifacts and a complex linear Jones result at 633 nm.
- Historical helper classification: **HELPER_PROMISING_LEGACY_EVIDENCE_ONLY**.
- Legacy helper data are not current LP-formal compatible: c-Si/Al2O3, H=300 nm, P=340 nm, one wavelength, and no current G0/reference/Px provenance.
- Representative v8 helper geometry passes its legacy gap audit: same-cell 56.55675044638735 nm; periodic 56.55675044638733 nm; same global H=300 nm.
- Circular `arg(t_alpha_star_from_alpha)` comparison is recorded, but current LP projector error and spectral stability are unavailable.
- Formal route: **HELPER_FORMAL_REVALIDATION_FIRST**, proposed-only 2-case x/y revalidation if an exact current-formal baseline can be reused; otherwise retain grouped-D READY_STANDBY.
- K6 registry remains 720 rows; versioned local registry remains 578; `ml_admitted=false`; solver_entered_delta=0.

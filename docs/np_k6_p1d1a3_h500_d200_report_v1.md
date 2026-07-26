# NP-K6 P1-D1A3 H500/D200 and spectral readiness audit

D200 used a trusted historical post-run FSP through a foreground read-only audit; no solver was started. Its 450 nm result is retained separately from the spectral-readiness result. The FSP monitor axes were read directly: they do not provide the required common 445–455 nm eleven-point grid, so no spectral interpolation or provisional spectral-stability result was created.

P1-D2 is therefore proposed-ready only: it specifies the 445–455 nm, 1 nm grid and a new matched broadband blank, but has `P1D2_SOLVER_RELEASE=false`.

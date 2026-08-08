# LP-ML Stage-I Formal P_APCD Freeze and Phase Audit v2

Outcome: `LP_ML_FORMAL_P_APCD_FREEZE_PHASE_PARTIAL`.

Formal numerical operator is frozen as `P_APCD=diag(1,0)` with Pxx=+1 real and arg(Pxx)=0 deg (matrix SHA256 accd073c7d27086debc80e21056dade6b534080bc6e5d4fbb7025821587348f0). Wang Eq.5 at psi=0, chi=0 reproduces the matrix within 1e-12. For the frozen Jones ordering, c(J)=<P,J>/||P||²=txx exactly; phase is arg(txx). Internal contract source SHA256: bb575391319f97e417ccac16be95c3e1d3569dece2363a9d1d338d2d7c1e74e5.

35 Stage-I rows were recomputed; formal circular tuple enumeration contains 38880 combinations and all residuals are bounded by 180 deg. The best phase-grid RMS remains 93.933612 deg, so tuple closure is partial rather than promoted.

Corrected B0-B5 formal ranges:
- B0: phase range 73.191842 to 82.520743 deg; circular target error range 73.191842 to 82.520743 deg
- B1: phase range 73.227900 to 85.453432 deg; circular target error range 13.227900 to 25.453432 deg
- B2: phase range 88.957304 to 94.418305 deg; circular target error range 25.581695 to 31.042696 deg
- B3: phase range 82.124630 to 93.567293 deg; circular target error range 86.432707 to 97.875370 deg
- B4: phase range 73.871459 to 92.607521 deg; circular target error range 147.392479 to 166.128541 deg
- B5: phase range 73.404522 to 85.187579 deg; circular target error range 133.404522 to 145.187579 deg

Phase conditioning on five deterministic raw-Jones controls:
- 0.5% perturbation: median=0.073833 deg, max=0.287507 deg
- 1.0% perturbation: median=0.167373 deg, max=0.511485 deg
- 2.0% perturbation: median=0.327322 deg, max=1.196312 deg
- 5.0% perturbation: median=0.748500 deg, max=3.060302 deg

Clean-v3 formal coverage contains 377 450-nm physics rows; provisional phase range is 62.053627 to 106.897833 deg. Stored surrogate phase values were not present; arg(predicted_txx) was recomputed and no derived-phase bug was asserted. Five-dimensional insufficiency remains unconfirmed.

Solver/FDTD calls: 0. Raw Jones and protected reports were not modified.

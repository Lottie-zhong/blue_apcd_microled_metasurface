# LP-FMM0A FMM-vs-FDTD audit plan

FMM/RCWA is suitable for early periodic normal-incidence dimer screening because the geometry is periodic and the target output is a Jones transmission matrix.
It cannot replace finite patch, dipole, Micro-LED, DBR/RCLED, or final validation because those require source, boundary, finite-size, and stack physics outside this periodic plane-wave screen.

## Required convergence check
Run planned Fourier orders 7x7, 11x11, 15x15, and 21x21 before trusting ranking.

## FMM-vs-FDTD comparison metrics
phase_error_deg difference; Tx difference; leakage difference; ratio difference; matrix_error difference; nearest-bin consistency; candidate ranking consistency; top-candidate overlap; runtime speedup.

## Go criteria
phase difference <= 5-10 deg; Tx difference <= 0.03-0.05; leakage difference <= 0.03-0.05; nearest-bin consistency >= 85%; B240/B300 ranking better than random; FMM top list overlaps with FDTD top list.

## No-Go criteria
unstable Fourier-order convergence; incorrect nearest-bin ranking; B240/B300 false positives dominate; strong disagreement with FDTD anchors.

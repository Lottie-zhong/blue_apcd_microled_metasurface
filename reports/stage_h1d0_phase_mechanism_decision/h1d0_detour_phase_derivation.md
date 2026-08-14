# H1D-0 Detour-Phase Derivation

## Frozen convention

- K = 6 dimers; dimer pitch = 431.907786 nm; supercell period P = K*p = 2591.446716 nm.
- +x is the phase-gradient direction and the target diffraction order is m=+1.
- The repository array-factor convention is `A_m = sum_j c_j exp(-i*2*pi*m*j/K)/K`; a translation by Delta-x therefore contributes `exp(-i*G_m*Delta-x)` with `G_m=2*pi*m/P`.

## Derivation

For a desired relative phase phi_k = 60 deg*k, solve `exp(-i*G_1*Delta-x_k) = exp(i*phi_k)`. Thus

`Delta-x_k = -P*phi_k/(2*pi) mod P = -P*k/6 mod P`.

The ideal offsets are `[0, 5P/6, 4P/6, 3P/6, 2P/6, P/6]` nm for target bins `[0,60,120,180,240,300]` deg. Equivalently, at increasing physical x slots `[0,p,2p,3p,4p,5p]`, assign bins `[0,300,240,180,120,60]` deg.

The existing `FORWARD_BINS=[0,60,120,180,240,300]` is a phase-library order, not by itself a proof of physical +1 steering. Under the repository minus-sign convention, using that order at increasing +x would select the opposite sign order; H1D0 freezes the explicit reverse assignment for m=+1.

## Broadband behavior

For fixed physical Delta-x and fixed normalized order m, `G_m=2*pi*m/P` is geometric and contains no wavelength. The detour contribution is therefore exactly wavelength-independent in the normalized supercell-order formulation. The diffraction angle remains wavelength-dependent through `sin(theta_m)=m*lambda/P`; that angular dispersion is not a wavelength dependence of the order coefficient phase.

This is analytic initialization only. It is not final order-resolved `J_xy`, alpha/beta conversion, or `t_{alpha*<-alpha}^{(m)}` evidence.

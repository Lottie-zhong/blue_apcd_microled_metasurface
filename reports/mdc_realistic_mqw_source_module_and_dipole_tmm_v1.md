# Realistic MQW source module and Dipole-TMM v1

- 12 primary wells are modeled at the frozen well-first coordinates, with equal weights and x/z incoherent averaging.
- Optical scope is `homogeneous_GaN_optical_approximation`; no InGaN, AlGaN, AlN, or sapphire constants are invented.
- Strain-release wells remain a separate sensitivity branch with zero formal primary-emission weight.

## Decision

The full 12-well average remains the formal TMM result. For a minimal later FDTD budget, sample wells 1, centroid, and 12 for both candidates and both in-plane orientations.

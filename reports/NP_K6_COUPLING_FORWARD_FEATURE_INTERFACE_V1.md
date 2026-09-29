# NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1

## Verdict

NP_COUPLING_FORWARD_FEATURE_INTERFACE_READY

This is a read-only, physics-informed auxiliary feature provider. It is not a
complex scattering operator, integrated MDC-NP truth, angular replacement, or
FDTD replacement.

## Frozen route decision

The HF22 complex coefficient route remains
NP_COMPLEX_COEFFICIENT_NOT_COMPOSABLE_AS_SCATTERING_STATE. The interface fails
closed for composable complex coefficients, Jones matrices, multi-input
Floquet scattering, and returning-order rescattering. No
NP_K6_COMPLEX_DEPLOYMENT_PROVIDER_V1 is created.

## Normal incidence

Inputs preserve ordered [D1,D2,D3,D4,D5,D6], explicit P/S, integer 445--455
nm, u_x=0, and k_y=0. The LF bundle carries the tracked m=-3..+3 proxy
vector and propagating m=-1,0,+1 powers; T_proxy is their sum. LF R is
explicitly unavailable. Exact HF22 rows may return FROZEN_HF_TRUTH R/T/order
values. Ranking and learned spectral components remain unavailable because the
frozen provider parity/recovery contract is not enabled.

## Angular handoff

Only frozen sparse metadata is exposed. u_x=+0.2241379310, P remains
unresolved and not truth; u_x=-0.4827586206 remains Rayleigh stress-test
only. No symmetry substitution or invented interpolation is performed.

## Domain support

The 20 selected Coupling geometries have exact HF22 overlap 0/20 and are
ordered-domain extrapolative under the audited positionwise support rule.
Each request returns per-position support, nearest HF22 geometry, normalized
distance sqrt(sum(((D_i-g_i)/130 nm)^2)), and an OOD warning.

## Governance

solver_calls=0, new_hf_acquisition=0, training_runs=0, rcwa_runs=0,
sealed_hf_target_reads=0, and Coupling target/performance labels read=0.

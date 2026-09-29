# NP_K6_COMPLEX_PROVIDER_AND_COUPLING_RESIDUAL_POC_V1

## Status

COMPLEX_COMPONENT_COMPOSITION_BLOCKED_REFERENCE_PLANE

This is a zero-solver, existing-artifact-only POC. It does not modify NP_K6_NORMAL_INCIDENCE_SCREENING_PROVIDER_V1, the NP HF truth, or the Coupling worktree.

## Authority and scope

- NP frozen scientific authority: c8e6eb422ed7d63d6a4608fd823341c929bd2b8f
- NP checkout observed for this audit: 10252a6072497d0ef077d3c51a2c19a47362e41b
- NP complex benchmark source commit: 4f343b6dbe4b5b28125e576693d861735b5f27da
- NP source: 22 geometries, 44 P/S logical cases, 8712 complex-state rows, 445-455 nm, u_x=0, k_y=0.
- Coupling authority: 20 valid cases, 21 wavelengths (440-460 nm), three planes, 81 2D Floquet orders, TE/TM complex states.
- Potential metadata intersection at 445-455 nm: 20 x 2 x 11 = 440 rows.
- NP and Coupling geometry identities do not overlap; valid numerical C_component rows are therefore 0 even before the reference-plane gate is applied.

## Provider POC contract

The proposed non-production interface is NP_K6_COMPLEX_FORWARD_PROVIDER_POC_V1.

Inputs preserve ordered [D1,D2,D3,D4,D5,D6], wavelength, u_x=0, k_y=0, and explicit P/S. Outputs preserve the NP signed order vectors and paired Re/Im complex modal state at the raw monitor planes. This POC is normal-incidence only and is not a Jones matrix, multi-input Floquet scattering matrix, or arbitrary returning-order rescaterrer.

FULL_2x2_JONES_MATRIX=false, MULTI_INPUT_FLOQUET_SCATTERING_MATRIX=false, ARBITRARY_RETURNING_ORDER_RESCATTERING=false, and PRODUCTION_APPROVED=false.

## Reference-plane hard gate

The Coupling contract is resolved from MDC right plane z=975 nm through 237 nm native SiO2 to NP_PILLAR_BOTTOM at z=1212 nm, with propagation exp(+i*kz_sio2*d). The NP complex archive, however, stores raw monitor-plane phase (nominal transmission z=900 nm and reflection z=-300 nm), with deembedding disabled and no arbitrary phase alignment. No frozen deterministic transform connects those phases to NP_PILLAR_BOTTOM in the Coupling convention.

Therefore B2 composition is not numerically constructed. Multiplying the MDC/spacer phase by the NP raw coefficients would introduce an unregistered phase/gauge assumption and is prohibited.

## Baseline disposition

- B0 - direct integrated Coupling HF characterization: existing 20-case Coupling archive retained as characterization authority; not used for model selection or residual fitting.
- B1 - current Level-1 baseline: unavailable/not authoritative (offline_screening_authorized=false, direct_stage_a_ready=false).
- B2 - NP complex + MDC TMM + spacer: blocked before numerical construction; valid_C_component_rows=0.

No residual RMSE, PCA, coupling learnability, or component-vs-HF numerical audit is reported because the gate blocks construction of the target labels. Any refit on the 20 Coupling geometries would be POC_REFIT_ONLY and was not run.

## Governance

- new solver: 0
- new HF acquisition: 0
- new training: 0
- sealed HF target read: 0
- Coupling H1 errors/candidate labels read: 0
- inverse design: 0
- deployment provider created: 0

## Artifacts

- outputs/np_k6_complex_provider_coupling_residual_poc_v1/poc_manifest.json
- outputs/np_k6_complex_provider_coupling_residual_poc_v1/matched_domain_audit.json
- outputs/np_k6_complex_provider_coupling_residual_poc_v1/matched_domain_audit.csv
- outputs/np_k6_complex_provider_coupling_residual_poc_v1/reference_plane_audit.json
- outputs/np_k6_complex_provider_coupling_residual_poc_v1/provider_interface_contract.json
- outputs/np_k6_complex_provider_coupling_residual_poc_v1/baseline_status.json

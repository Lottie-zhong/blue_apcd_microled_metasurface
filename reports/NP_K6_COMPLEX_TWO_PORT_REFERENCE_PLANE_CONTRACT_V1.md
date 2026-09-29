# NP_K6_COMPLEX_TWO_PORT_REFERENCE_PLANE_CONTRACT_V1

## Status

Primary verdict: NP_COMPLEX_COEFFICIENT_NOT_COMPOSABLE_AS_SCATTERING_STATE
Secondary coordinate status: NP_COMPLEX_REFERENCE_PLANE_CONTRACT_PARTIAL.

Strict zero-solver, read-only forensic closeout. No solver, training, RCWA, new HF acquisition, Coupling residual fit, or deployment provider was run or created.

## Authority and scope

- Frozen scientific authority: c8e6eb422ed7d63d6a4608fd823341c929bd2b8f
- Current checkout: 44a8bdd004835903f2753d85e3d1063762b3113c
- Branch: work/np-k6-mdc-v1
- HF authority: 22 geometries x P/S x 11 wavelengths = 44 logical cases / 484 rows.
- Ordered geometry is [D1,D2,D3,D4,D5,D6]; u_x=0, k_y=0, m=+1 is physical +x.

## Coordinate contract

The audited NP setup lineage gives substrate top / pillar bottom z=0 nm, TiO2 pillar top z=500 nm, source z=-250 nm with Forward/+z, reflection monitor z=-300 nm, transmission/order monitor z=900 nm, Px=1740 nm, Py=290 nm, Native-M1 substrate-side SiO2 and air output-side medium.

Candidate ports:
- NP_INPUT_PORT = z=0^- in homogeneous substrate-side SiO2.
- NP_OUTPUT_PORT = z=500^+ in homogeneous air.

P0 anchor setup contracts do not repeat all coordinate fields; their coordinate entries are marked inherited from the corrected NP setup lineage in coordinate_audit.json.

## Complex semantics and hard gates

Existing post-FSP extraction is load-only and contains finite complex E/H at both reflection_monitor and transmission_monitor for all 44 logical cases, with 11 wavelength points per case. gratingvector order closure is a valid power-bookkeeping check.

The stored coefficient is sqrt(formal_total_power) times gratingvector_component, where sourcepower(f) is a real power normalization. No incident complex modal amplitude division, source/reference-field de-embedding, or common inter-case phase reference is stored. Phase is raw monitor-plane phase.

Hard gates:
1. COEFFICIENT_IS_NOT_SCATTERING_NORMALIZED = FAIL.
2. INCIDENT_COMPLEX_PHASE_REFERENCE_NOT_RECOVERABLE = FAIL.

Reflection raw E/H flux is non-isolated because the incident standing-field contribution is present. Power closure does not repair complex scattering normalization.

## Conditional analytic de-embedding

For a future valid scattering-normalized coefficient, homogeneous propagation uses kx=2*pi*m/Px, ky=0, passive kz with Re(kz)>=0 and Im(kz)>=0. Transmission z=900 to z=500+ uses exp(-i*kz_air*delta_z); reflection z=-300 to z=0- uses exp(-i*kz_SiO2*delta_z) for the backward wave.

These are conditional analytic transforms only; they are not frozen as a composable two-port contract because the incident phase/coefficient gauge is unresolved.

## Coupling handoff audit

The Coupling 20G manifest was read only for ordered geometry metadata. No Coupling performance labels, H1 errors, candidate labels, sealed targets, or model-selection data were read.

Normalized ordered-distance is min_g sqrt(sum_j ((D_j-g_j)/130 nm)^2), where g ranges over 22 HF ordered geometries and 130 nm is the frozen HF observed global diameter span. All 20 Coupling geometries are extrapolative in the ordered-position domain; exact overlap is zero. See coupling_geometry_domain_audit.csv/json.

Coordinate mapping to Coupling is geometric only: NP local z=0 maps to Coupling global z=1212 nm because 975+237=1212 nm, with native SiO2 spacer and the recorded propagation convention. This does not resolve NP incident complex phase gauge.

## Not authorized

- No t_alpha_star_from_alpha(order) or polarization-selective complex scattering claim.
- No full 2x2 Jones matrix: each geometry has only one P and one S input column.
- No production/deployment provider.
- No solver invocation to repair this contract in this task.

## Evidence files

- coordinate_audit.json
- coefficient_semantics_audit.json
- incident_phase_audit.json
- deembedding_transform_audit.json
- coupling_mapping_audit.json
- coupling_geometry_domain_audit.csv/json
- contract_manifest.json

## Next gate

CHART_REVIEW_NP_COMPLEX_ROUTE_LIMITATION

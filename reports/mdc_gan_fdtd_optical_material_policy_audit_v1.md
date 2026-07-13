# MDC GaN FDTD optical material policy audit v1

## Search scope

- Read-only repository search: configs, scripts, reports, frozen manifests/JSON/CSV, MDC/RCLED/dipole-FDTD helpers, and Native-M1 material helpers.
- No static repository source established a formal dispersive GaN FDTD registration; the traceable values found were legacy constants.

## Decision

- Status: `formal_candidate_incomplete`.
- `is_nominal` or a single FSP material name is insufficient to freeze a formal FDTD GaN mapping.
- `gan_material_policy_candidate.json` is `null`: only a unique formal candidate may produce a proposed-not-frozen policy record.
- Legacy `n=2.41` is `legacy_constant_index_reference` and `not_allowed_for_formal_fdtd`.
- No candidate is written into plane-wave global configuration.

## Sources

- `scripts/mdc_tmm_core.py:12`: legacy constant n=2.41.
- Existing MDC/RCLED helpers use constant custom GaN names; they are not dispersive formal candidates.
- Targeted FSP: `F:\wc_312\MDC_blue_oujizi_m\m_1.fsp`; SHA256 and byte size recorded in candidate CSV.

## Read-only FSP inspection

- Read-only FSP object/material mapping: `GaN` object -> `GaN` material.
- Five queried points (not exported material data): 420 nm: n=2.466469, k=0.094666, 448 nm: n=2.417746, k=0.084683, 450 nm: n=2.414946, k=0.084153, 453 nm: n=2.410884, k=0.083392, 480 nm: n=2.380501, k=0.077868.
- n(450 nm)=2.414946; delta versus historical n=2.41 is +0.004946.
- 420-480 nm query coverage is PASS; material-model type, sample count, interpolation/extrapolation policy, and deterministic blank-session registration remain unresolved.

## Legacy comparison boundary

- The n(450) difference is recorded only as a data comparison. It can affect sourcepower normalization, Bloch kx, Fresnel boundaries, and TMM-FDTD disagreement; this audit neither changes TMM nor asserts equivalence.

## Inspection safety

- Read-only inspection evidence retained: `True`; this invocation started a session: `False`.
- Solver execution, analysis execution, and project save: false/false/false.

## Impact

- Phase A/B/C remain blocked unless a future audit returns `unique_formal_candidate_found`.
- Minimal next step: obtain an approved, versioned material registration/provenance record for this FSP's `GaN` material; do not fit or import external n,k data.

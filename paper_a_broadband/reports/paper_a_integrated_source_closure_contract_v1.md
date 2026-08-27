# Paper A integrated source closure contract V1

- Status: **HARD_GATE_CONTRACT_LEVEL**
- Verdict: **PAPER_A_INTEGRATED_SOURCE_CLOSURE_HARD_GATE**
- Canonical branch: `work/paper-a-lp-cp-broadband-v1`
- Contract-generation HEAD: `906e2236ddd64349cdca03d12f73d945abe917b9`

## Completed

The zero-solver audit froze the real source ensemble, MDC/CP/LP provenance, finite-boundary requirements, four-way ablation matrix, direct coherency/Stokes metric contract, V2 adapter specification, and future staged budget plan. The target configuration remains direct MQW source + frozen ZL-1 MDC + finite I03, with no product-rule spectral shortcut.

## Exact source and provenance

The primary source authority is `MDC_REALISTIC_MQW_SOURCE_MODULE_V1`: 12 primary wells at `[-171.5, -190.5, ..., -380.5] nm` in the source frame, 3 nm well thickness, 16 nm barriers, equal weights, and zero formal weight for the three strain-release wells. Each primary well has independent in-plane x/y dipole cases, combined incoherently at coherency/Stokes level. The copied source/interface evidence and SHA256 values are in `source_asset_inventory.json`.

The frozen CP reference is `BW2_J1J2_D194_T90_PSI99_H525`; the frozen MDC provider is `P1_ZL1_ALTERNATIVE_G3_A3`, with relative `r12_normalized_output` only. LP uses `BF04R_I03` as a local-basin current-Native reference; no new LP candidate was generated.

## Hard gate

No authoritative 3D finite mesa extent, finite I03 replication/placement, absolute MQW-to-MDC-to-I03 z registration, or explicit decision on the Coupling-only 237 nm spacer was found. The existing CP x/y-periodic FSP, 2D MDC evidence, R1C5 source module, and old K6 finite patch are therefore not substituted. The emitter spectral envelope is also not silently invented.

The four ablations are defined but `NOT_RUN`; mesh/PML reuse is deferred until finite layout and clearance are authoritative.

## Zero-solver proof

`FDTD=0`, `RCWA=0`, `ML=0`, `solver_run_called=false`, `solver_entered=0`, no admission, no DOE execution, and no modification to frozen LP/CP/MDC source worktrees.

See `integrated_source_closure_contract_audit.json` for the audit boundary and `future_solver_budget_plan.json` for non-authorizing future counts.

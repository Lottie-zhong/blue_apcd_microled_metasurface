# Coupling ML requirements for the Physics Codex provider

## Highest-priority first delivery

First deliver an immutable, convention-matched integrated C_physics complex modal state and independent P_scale on a small, explicitly identified geometry/wavelength set. Use the exact frozen H1 axes and +z (0,0) TM incident state. This directly tests whether an analytic baseline can support residual learning. Include MDC, spacer and NP component operators in the same package when available so the composed state can be audited; a bare integrated state alone does not validate the proposed component cascade.

## Required data contract

Provide:

1. Versioned physics contract, physics model version, schema, contract hash and provider result ID.
2. Explicit ordered input and output mode axes. Each mode needs port identity, order, polarization, propagation direction and propagating/evanescent status.
3. Complex output-by-input coefficients with declared normalization, reference planes, phase convention and incident normalization.
4. Exact geometry values and units, wavelength grid and material configuration.
5. Separate P_scale with its POSTNP Poynting-integral definition, incident reference and cell-area normalization.
6. Solver and extraction provenance: software/version, mesh, boundary conditions, monitor/reference planes, run ID, input asset SHA, pre/post artifact hashes, logs and extraction code version.
7. Completeness mask, independent validation and convergence evidence, known limitations, uncertainty or validity-domain indicators.
8. Unknown-geometry availability: which inputs the provider can calculate, what inputs are out of domain, required assets, failure behavior, and whether evaluation requires an RCWA run.
9. End-to-end compute cost: setup, provider solve, extraction and any network inference, with hardware and timing protocol.

## Compatibility with frozen H1

For H1 full-state mode, deliver the full (21,7,2) complex state for the frozen 440-460 nm grid, m=-3..+3, n=0, TE/TM output basis, for the +z (0,0) TM incident state. Demonstrate that reference plane, source gauge, mode normalization and axes match H2. Provide a coverage mask. If any channel is absent, evanescent under the chosen convention, or unvalidated, mark the payload partial and do not claim H1 full-state compatibility.

Deliver the 21 positive P_scale values separately. Power-only data cannot stand in for complex coefficients, and complex coefficients cannot stand in for the independent transmitted-power observable.

## Component-cascade package

Provide each component's T and R matrices on a common ordered internal mode basis, with port directions and reference planes. Include propagation operator P or all material and spacing data needed to construct it. Identify evanescent truncation and provide convergence checks as the internal basis is enlarged. State the matrix-axis and sign conventions. Include a trusted composition check.

## Current open blocker

The present DIAG2 evidence is setup-only: a 6 ps setup passed native LOAD-only readback and changed simulation_time from 3 to 6 ps while the 5 nm mesh and 1e-6 auto-shutoff remained unchanged. It has no solver entry, truth, formal admission or supported installed consumer. Existing numerical comparisons ended at 3 ps and did not reach the 1e-6 shutoff, leaving a temporal-convergence confound. This preparation does not resolve or authorize that issue.

The DOE56 record remains 4 entered / 4 truth-valid / 4 label-valid / 52 unentered. Keep the serial no-replay and truth-before-next controls intact. No request in this work authorizes solver entry or release of additional DOE cases.

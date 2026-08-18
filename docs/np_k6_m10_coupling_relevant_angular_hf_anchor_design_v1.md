# NP K6 M10 coupling-relevant angular HF anchor design v1

- Status: `NP_K6_M10_COUPLING_RELEVANT_ANGULAR_HF_PRIMARY_BATCH_READY_FOR_SOLVER_AUTHORIZATION`
- Solver authorization: **not granted**; this stage is zero-solver.
- Consumed Coupling package pin: `NP_CONSUMED_COUPLING_B_TERMINAL_PACKAGE_PIN_V1.json`; source HEAD `92ccb15441d4c5b9bfe6853743738db8747800f5`; source dirty=`True`; post-read hash check PASS.
- Coupling worktree was read-only; no intermediate B state was polled or read.

## Exact identities

- ALT1/B: `NP_K6X_100_115_130_145_155_185`, D1...D6=`[100, 115, 130, 145, 155, 185]`, geometry hash `00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1`.
- CONTROL0: `NP_K6X_125_135_150_175_190_210`, D1...D6=`[125, 135, 150, 175, 190, 210]`; package does not store a separate geometry hash.
- H=500 nm, period=1740 x 290 nm, SiO2 -> native TiO2 K6 -> Air, `m=+1` physical +x.

## Existing HF 3/4

Exact reuse is allowed for ALT1 S at `u_x=+0.22413793103448276` and ALT1 P/S at `u_x=+0.37868939998860307`. ALT1 P at `+0.22413793103448276` remains unresolved after two entered failures and is permanently excluded from replay, replacement, and attempt_003.

## Selection and batch

The preregistration was created after package pinning and before final selection. Formal MDC mass exists for 4/9 nodes only; all other nodes are `MDC_IMPORTANCE=UNKNOWN`, never zero-filled. The minimum informative new batch is therefore two ALT1 cases at `u_x=-0.48275862068965514`, paired P/S. The nominal four-case preference is reduced by exact reuse of the accepted `+0.378...` pair. `u_x=-0.9549788465408765` remains a secondary P/S-stress candidate because its MDC mass is unknown. A CONTROL0 matched anchor is conditional on post-HF evidence of geometry-dependent RCWA error.

Decision-stability is frozen as `E_ALT1 + E_CONTROL0 < Delta_candidate`, or common-provider `E/Delta_candidate < 0.5`; this is not a solver result or promotion claim.

## Scope limits

RCWA provider scope is Level-1 exploratory only; Jones complex amplitudes and Level-2 integrated truth are unavailable. Full-grid MDC-weighted support is unavailable (4/9 partial support only). No angular HF, training, external HF, replay, or inverse operation was executed.

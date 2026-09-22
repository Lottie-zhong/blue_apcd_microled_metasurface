# FAST_PW_VALIDATION_GATE_V1

Status: FROZEN_PREENTRY

## Purpose

This contract authorizes comparison of exactly one new W2H_15294 FAST_PW
candidate against the recovered 5 nm baseline. It does not authorize a
retry, replay, duplicate entry, MEDIUM_PW run, or seed-database start before
the FAST decision is PASS.

## Reference authority

The reference is the completed W2H_15294 NP-derived 5 nm run:

- role: EXPENSIVE_NUMERICAL_REFERENCE_TRUTH
- solver completed
- fresh LOAD-only native and post FSP recovery: PASS
- raw recovery: PASS
- solver entries: 1
- replay count: 0
- rerun: forbidden

The recovery record can report
PW0_truth_status=NOT_ADMITTED_REFINED_TRUTH_MISSING. That status means the
refined 2.5 nm comparison attempt is incomplete; it is not a rejection of
the completed 5 nm truth. The incomplete refined attempt is forensic-only.
This contract therefore uses the recovered 5 nm result as the frozen
reference and does not modify or rerun it.

## Candidate and physical scope

FAST_PW is the lower-cost integrated periodic 3D plane-wave FDTD candidate:

- W2H_15294, K6 fixed MDC, fixed 237 nm spacer
- x/y Periodic and z PML
- 1740 x 290 nm cell, 500 nm pillars
- GaN to air, +z normal incidence, X / P_XLIKE
- native APCD materials
- 440-460 nm at 1 nm spacing, 21 wavelengths

The FAST mesh authority is the existing design-only FAST specification:
10 nm x/y in pillar boxes, 5 nm z through pillar/spacer/MDC interface
bands, 15 nm integrated background, and 20 nm homogeneous GaN/air. The
design-only runtime and reduction estimates are not admission evidence.

## Fidelity gate

The following are inherited unchanged from
contracts/coupling/medium_pw/MEDIUM_PW_VALIDATION_GATE_V1.json:

- complex-state error max: 0.05
- R absolute error max: 0.05
- T absolute error max: 0.05
- each materially populated order absolute error max: 0.05
- routing spectral-trajectory correlation minimum: 0.98
- missing required wavelengths: 0

The inherited normalization is
E_C(lambda)=||C_FAST-C_5nm_reference||_2/||C_5nm_reference||_2.
The established per-wavelength, per-order aggregation, phase/gauge
alignment, routing definition, materially-populated-order definition,
REVIEW rule, and FAIL rule are taken from the MEDIUM contract and are not
reinterpreted here. Per-wavelength and per-order checks precede all
aggregate reporting; a good aggregate cannot mask a local failure.

## Structural gates

The FAST result must also have:

- all 21 wavelengths and no missing truth payload;
- identical PRENP/POSTNP reference-plane, normalization, material, MDC,
  spacer, geometry, and diffraction-order sign/index semantics;
- no unexpected diffraction topology change from 440 to 460 nm;
- energy closure abs(1-(R+T+A)) < 0.01 at every wavelength after native
  readback and reference-plane validation;
- no hidden replay and no duplicate scientific entry;
- intact native/post FSP, raw payload, archive, and provenance truth.

## Decision

PASS requires every numeric and structural gate to pass. On PASS, declare
FAST_PW_PRODUCTION_FIDELITY_ADMITTED, freeze FAST fidelity, count the
W2H_15294 FAST result as one of the 20 seed geometries without rerunning it,
and then start PW_K6_SEED_DB_V1.

On any FAIL or REVIEW, do not start the seed database. Report exact
wavelength/order/state failures and recommend MEDIUM_PW as the next
fallback. MEDIUM is not authorized by this contract.

## Source provenance

- MEDIUM gate:
  contracts/coupling/medium_pw/MEDIUM_PW_VALIDATION_GATE_V1.json
- FAST mesh design:
  outputs/coupling_ml/PW_PERIODIC_W2H15294_NP_DERIVED_MESH_CALIBRATION_GATE_A_V1/PW_COST_DOWN_DESIGN_V1.json
- recovered reference:
  outputs/coupling_ml/PW_PERIODIC_W2H15294_NP_DERIVED_MESH_CALIBRATION_GATE_A_V1/BASELINE_RECOVERY_FINAL.json
- reference-plane, modal, order-sign, and energy contracts are recorded in
  the JSON companion with SHA256 provenance.

No solver was run while this contract was created.

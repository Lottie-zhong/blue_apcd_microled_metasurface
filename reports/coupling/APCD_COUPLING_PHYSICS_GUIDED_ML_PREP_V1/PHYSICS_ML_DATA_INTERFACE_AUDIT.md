# Physics-guided ML data interface audit

## Scope and disposition

This is a static audit of the frozen Coupling ML dataset and model target contract. No solver was entered, no new model was fit, no confirmation or sealed response was opened, and no dataset label was rewritten. The 156G labels remain authoritative only within their documented dataset contract; this audit does not upgrade them into a full scattering matrix.

## Evidence reviewed

| Evidence | SHA-256 | Finding |
|---|---|---|
| reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1/FROZEN_156G_DATA_MANIFEST.json | cbd3aaa4b6ac966a2bc3fdb980e2ae3d16056d36ab80fefefe514e92328c67ea | 156 unique development geometry groups, all valid |
| reports/coupling/APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json | 9e2687d61496850bca4f79b5fb24d20f446f47b56944c7a69edb127757a38403 | valid_count=156; no inventory errors; confirmation, queue21 and independent diagnostics excluded |
| scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py | b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15 | frozen H2 complex-state decoder |
| scripts/coupling_ml/k6_v2_pipeline/h1.py | 8a541f7d2357a4566e1a005a0c60451454ce2f7a97ae6d9d2987f0b250a4ffff | current H1 implementation |
| reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json | 8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd | frozen conjunctive H1 limits |
| reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1/FINAL_SCIENTIFIC_REPORT.md | 0ac4cce0f9df0fee83a3989c4f7b37dc87f620b7b355124879eaffbbbb653055 | frozen report records the completed historical 268-fit package; this task ran no fits |

The legacy 32G archive and all 124 newer per-case label NPZ files were rehashed in this task: all 124 NPZ hashes matched their inventory, and the legacy archive hash matched. No confirmation/sealed files were accessed.

## Frozen input and output axes

- Input: ordered geometry dimensions D1 through D6, in nanometres.
- Wavelength: 21 points from 440 through 460 nm at 1 nm spacing.
- Incident state: +z, order (0,0), TM.
- Output channels: order m=-3 through +3 at n=0, each with TE and TM.
- Complex state C_hat: shape (21, 7, 2), or 294 complex values / 588 real and imaginary scalars.
- Separate P_scale: 21 positive dimensionless POSTNP transmitted-power values.
- Packed training target: 609 scalars, with 588 real/imaginary state components and 21 log(P_scale) values. The existing pack/unpack APIs are in scripts/coupling_ml/k6_v2_pipeline/contracts.py.

The H2 decoder forms one source-referenced phase gauge per wavelength from the incident +z (0,0) TM reference and reuses it across output channels. This retains relative phase among channels. Do not independently phase-align output channels after decoding.

P_scale is the POSTNP transmitted power derived from the E/H trapezoidal Poynting integral, normalized by cell area and incident power per area. Training uses log(P_scale); inversion uses exp. H2 computes modal power as weight times |C_hat|^2, sums TE/TM within each order, and normalizes to routing eta. Absolute order power is eta times P_scale. In this decoder, total_power equals P_scale by construction and is not an independent power-closure check.

## Scope boundary

Each geometry has one incident +z TM input. The labels identify one incident column of a response, not a bidirectional or full multiport S-matrix. A full S-matrix is not identifiable from this dataset alone. Any provider interface must name input and output modes explicitly and may not infer missing columns.

A recomputation of H2 routing from saved labels over the 156 geometries showed median absolute eta difference 3.62025e-5 and maximum 3.41991e-4. This supports decoder/label consistency only; it is not a new physical validation.

## Audit conclusion

The frozen 609-value target is structurally usable for forward prediction of the documented incident state. A provider-conditioned or residual model is not currently wired into the production model API. Full-state use requires complete validated complex values and an explicit channel mask. Power-only or partial complex provider data cannot be silently promoted to the H1 full-state target.

## Split and provenance boundary

The 156 development groups are role-labeled: 32 DEVELOPMENT_OLD32, 113 DEVELOPMENT_GLOBAL, and 11 DEVELOPMENT_LOCAL_AXIS. All are development roles; confirmation responses remain excluded. The frozen inventory and manifest bind group identity and label provenance. Future comparisons must split by geometry group, retain every wavelength/order/polarization for a group in one split, and fit all normalizers on training groups only. The historical formal package records 268 completed fits; the current recommendation uses the frozen H1 baseline results and does not repeat or reinterpret those fits as new evidence.

## Learnability and numerical limits

The frozen H1 results show that neither historical aggregate predictor passes the mandatory gates. The dataset has a strongly TM-dominated output distribution and order-dependent routing, but those are label properties and do not establish that the corresponding outputs are easy to predict. The observed median norm ratios below 1.0 are consistent with prediction contraction, not proof of its cause.

The 11 local-axis cases permit descriptive reporting only; the reviewed evidence does not provide a validated matched finite-difference response study around common anchors. Local response sensitivity and whether 156 geometries support a small shared residual model are UNRESOLVED.

The 5 nm / 3 ps numerical comparison did not reach the stated 1e-6 shutoff. A 6 ps setup passed LOAD-only readback but was not run. This remains a temporal-convergence confound; it cannot be assigned as the cause of historical ML failure, and the 5 nm/4 nm diagnostic cases must not be added to training data.

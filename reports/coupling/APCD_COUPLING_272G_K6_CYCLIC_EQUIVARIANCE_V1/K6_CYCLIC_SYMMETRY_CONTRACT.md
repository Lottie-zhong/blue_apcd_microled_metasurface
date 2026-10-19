# K6 cyclic symmetry contract

Status: **PASS for the ideal, periodic K6 label transform used in this zero-solver study.** This is an algebraic and code-path validation; no independent rotated-geometry FDTD pair exists in the 272G table, so it is not a new physical-solver parity claim.

## Geometry action

The frozen builder places ordered `D1…D6` at ascending x centers `[-725,-435,-145,145,435,725] nm` in a `1740 nm` x-periodic cell. The generator's `T(D)=roll(D,+1)=[D6,D1,D2,D3,D4,D5]` moves each pillar center by `+290 nm` modulo `1740 nm`. Thus `T^6(D)=D`. It preserves pillar order around the periodic cell, x/y axes, normal incidence, and TE/TM channel labels; it is a translation, not a mirror, reversal, or 60-degree physical rotation. The exact 5 nm mesh divides both the shift (58 cells) and the superperiod (348 cells).

Implementation evidence: `scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py`, `pillar_centers_nm` lines 51–52, periodic x/y boundaries lines 158–162, and ordered `NP_D1…NP_D6` construction lines 171–174. The frozen full-cell contract retains the 290 nm pitch and 1740 nm x period.

## 609D complex-state action

The production projector uses the negative Fourier kernel `exp(-i G_m x)` (`scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py`, line 230). Translating a field by `+k·290 nm` therefore gives:

`C_hat(T^k D)[λ,m,pol] = C_hat(D)[λ,m,pol] · exp(-i·2π·m·k/6)` for `m=-3,…,+3`.

Both TE and TM receive the same order-dependent phase. `m=0` is unchanged. Complex magnitudes are unchanged for every order and polarization. `P_scale` is unchanged because the incident normal-incidence reference and global phase gauge are unchanged under lateral translation. No independent channel phase rotation, magnitude normalization, or label modification is applied.

The frozen H2 decoder (`scripts/coupling_ml/k6_v2_pipeline/h1.py`, lines 41–53) constructs modal power from fixed TE/TM modal weights times `abs(C_hat)**2`, normalizes across the seven orders, and multiplies by `P_scale`. It is therefore invariant under this phase action. The decoder identity used in this study is `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15`; the H1 authority identity is `8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd`.

## Authorized use in this experiment

1. **Training augmentation:** for training-only unique rotations `D_k=roll(D,k)`, transform the complex target by the formula above and keep `P_scale` unchanged. All 21 wavelengths of a geometry remain together. Deduplicate identical views within each geometry before expansion.
2. **Six-view inference:** evaluate all six rotated inputs, multiply each predicted complex response back by `exp(+i·2π·m·k/6)`, and take the arithmetic mean of aligned complex responses; average positive-domain `P_scale` predictions arithmetically.
3. **H2 decoding:** decode the final aligned response with the existing frozen H2. The symmetry transform does not change the H2 definition or any truth label.

The 272G table contains 272 distinct canonical cyclic orbits, and each checked training geometry has six distinct rotations. Synthetic rotations are training views, not additional physical geometries or FDTD labels.

## Scope boundary

This contract applies to the normal-incidence, x-periodic, ordered six-pillar supercell and its frozen global incident-phase gauge. It does not authorize reordering labels arbitrarily, reversing the sequence, changing the period or reference plane, or treating symmetry-generated copies as independently measured truth. FAST data remain `ML_TRAINING_GRADE`; H1 remains a development-only gate and final generalization remains uncertified.

## H5 coordinates and z-reference bookkeeping

The representative existing labels-valid case `K6AL_COMPLEX_R03_G001` was read in place for a coordinate audit; this is not a rotated-pair FDTD parity test. Its receipt records `attempt_001`, `ML_TRAINING_GRADE`, source/setup SHA `4ea64d0b52249db80148a8594b093380b9cd9299cdd24783fe2eb29e5ea94a87`, truth-H5 SHA `f0975716d9242233e9941b767f169714a484510fa7108a1707291062e302d265`, and native-H5 SHA `5211f708efb9c337946a7468e178970fa4ea03ad0b37e0da4b869329c69ae65c`; `truth.h5` stores the frozen physical-contract SHA `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`. These are the already recorded identities; the large H5 files were not rehashed or modified.

The Runner native H5 stores monitor x/y coordinates centered at zero (Monitor0 x `[-0.87,+0.87]`, y `[-0.145,+0.145]`; 349 × 59 samples). In the canonical `truth.h5`, `EH_complex` stores the same coordinates in SI metres, x `[-8.70e-7,+8.70e-7]`, y `[-1.45e-7,+1.45e-7]`. After applying the native-to-canonical coordinate scale `1e-6`, the maximum absolute differences are x `1.059e-22 m`, y `1.323e-23 m`, z `0.000e+00 m` for IN, PRENP, and POSTNP. This establishes the H5 lateral phase origin at `(x,y)=(0,0)` for the inspected case.

The actual H5 sample z planes for this case are IN `-100.787739 nm`, PRENP `1152 nm`, POSTNP `1802 nm`. The frozen extractor de-embeds to its pinned z references IN `-50 nm`, PRENP `1202 nm`, POSTNP `1722 nm` (`pw_complex_floquet_state_v1.py::_REFERENCE_NM`). The Fourier phase is evaluated on the actual recorded x/y coordinates with origin zero; the source contract is normal incidence with amplitude 1 and phase 0. The cyclic action changes only x; it does not alter these z references, monitor ordering, global incident-phase gauge, or TE/TM order.

Machine-readable audit: `CYCLIC_H5_COORDINATE_AUDIT.json`. The H5 coordinate inspection corroborates the code convention for one existing native case; no physical rotated-geometry pair was present, so real-solver cyclic parity remains **NOT MEASURED**.

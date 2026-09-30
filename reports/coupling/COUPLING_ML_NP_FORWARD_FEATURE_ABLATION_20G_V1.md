# COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1

## Status

**BLOCKED at the matched-feature coverage gate; no model was trained and no outer-fold test metric was computed.** This is not a solver failure and does not alter the Coupling scientific truth or H1 admission.

## Authority and matched labels

- Coupling: `work/mdc-np-coupling-ml-v1` at `f01f0dcd1a53a02592d9b7ea55c8f8e70dfdeb55`; upstream divergence `0	0`.
- Frozen 20G manifest SHA256: `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c`; status PASS; 20 selected cases, 20 scientific entries, zero duplicate entries, zero replay entries.
- All 20 selected cases have direct case-local `scientific_validation.json=PASS`, `HF_ARCHIVE_MANIFEST.json=PASS`, ledger entry/return evidence, canonical state JSON+NPZ with matching SHA, and existing FSP/H5 artifacts. The authoritative state schema is `PW_COMPLEX_FLOQUET_STATE_V1` with 3 planes × 21 wavelengths × 81 orders × 2 directions × 2 polarizations; the paired band contains 220 geometry-wavelength rows and 1,540 order-wavelength rows.
- The 20G manifest's `fsp.sha256` records the pre-entry/setup FSP digest (verified against the applicable pre-entry/setup manifest or attempt ledger); the saved post-solver FSP has a different digest, independently matching the archived V2 `runtime_fsp_sha256` or legacy `post_fsp_sha256`. S16's pre-entry sidecar is explicitly absent in the frozen manifest, so its ledger supplies the entry hash; its archived post-FSP hash and path verify. State sidecar hash fields refer to the paired NPZ payload; both links were verified. No hash mismatch was waived.
- Paired domain is exactly 445–455 nm at 1 nm spacing, P/XLIKE only. The 12G expansion is not substituted for the frozen 20G authority.
- Frozen baseline report SHA256 `8a4680008870ba4cba0f2ca22e59cee93f6d31a375c7d81087d2dfa6edda4228` identifies `PW_K6_STRUCTURED_FORWARD_MODEL_V1` (width 32, 2,684 parameters); H1 gate source SHA256 `8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd`. H2 decoder source SHA256 `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15`.

## NP interface coverage

- NP worktree: `work/np-k6-mdc-v1` at `f8dad0e8438167ffca5ab22c19aa4790fa94b8d6`; the frozen interface provenance records authority HEAD `c8e6eb422ed7d63d6a4608fd823341c929bd2b8f`.
- Interface: `NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1`; adapter SHA256 `7838c0cf10b84f1c11ea37c66d436280771d15a8706e6b26492a1aa3740c5ede`, interface manifest SHA256 `e7325852bb0533088339966ba6c2ae4312ce38564e6d563563e9210ce8b53dbe`.
- The allowed A1 fields are the frozen LF order vector m=−3…+3 and `T_proxy=sum(m=−1,0,+1)`, queried only through `FrozenAuthority.lf_features(ordered geometry, wavelength, P)`. All 20 Coupling geometries are absent from the frozen LF geometry master; all **220/220** requests returned `UNAVAILABLE / geometry_not_present_in_frozen_LF_design_space`.
- The support manifest independently reports exact HF22 overlap 0/20 and all 20 extrapolative. It was used for diagnostics only. Geometry sorting, permutation, interpolation, hand-filled LF values, HF truth substitution, and support metadata as model inputs were not used.
- A2 skipped: `LEARNED_SCALAR_FEATURE_ARM_NOT_REPRODUCIBLY_AVAILABLE`. A3 skipped because A1 and A2 are not both available.

## Preregistration and scores

`preregistration.json` was frozen before any outer-fold score calculation. The 20-fold LOGO/3-fold grouped inner split manifest was generated, but no fitting or scoring was started because A1 had zero matched values. A0 is marked NOT_RUN in this paired package; no unpaired baseline errors are presented. OOF and per-geometry CSV files contain headers only. See `paired_ablation_metrics.json` for explicit null/not-computed status.

## H1 and scientific boundary

The frozen conjunctive H1 numerical gates remain unchanged. No new H1 score was computed; NP auxiliary-feature utility is not equivalent to production admission. No complex cascade, Jones matrix, or MDC+spacer+NP composition was constructed.

## Leakage and execution

The LF adapter received only ordered geometry, wavelength, and P polarization; it was called through `lf_features`, not the general request path. Coupling state artifacts were integrity/schema checked only and never passed to the NP feature generator or an ML fit. Fold IDs keep complete geometries together. No solver, GPU entry, Shared V3 control/SQLite, final dipole data, or sealed validation was accessed.

## Outcome

`COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_BLOCKED`. The matching Coupling labels exist; the frozen NP provider does not cover their exact ordered geometry domain. Resume only after a formal NP provider/interface authority supplies exact values for all matched rows without sorting or synthetic extrapolation. The 32G confirmatory contract is frozen at `NP_FEATURE_ABLATION_CONFIRMATORY_CONTRACT_V1.json` and must not be tuned from this 20G result.

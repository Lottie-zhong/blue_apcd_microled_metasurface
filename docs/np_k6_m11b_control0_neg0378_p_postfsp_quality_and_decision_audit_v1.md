# NP K6 M11B CONTROL0 P post-FSP quality and decision audit v1

Status: TERMINAL_QUALITY_GATE_FAIL / formal_accept=false.

## Frozen identity

- case: CONTROL0_NEG0378_P, attempt attempt_001
- ordered diameters: [125, 135, 150, 175, 190, 210] nm
- polarization: P_XLIKE
- exact u_x: -0.3786893999886029
- canonical geometry hash: 5744baf84e4b4405711f0aabdbb7965c294d4b3e4f099f670457fbbbae1c2710
- pre-FSP SHA256: d980fbded5cb59f7ff2d7712897d5d9d3c34dc705358db2b217f0de8f298a10f
- post-FSP SHA256: bd71b568c1a9632a27e92d956ebcdd708c7739e35756c8202cccdcf7badb91cb

## Formal quality

- independent read-only extraction: True
- exact wavelengths: [445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455]
- closure max |1-T-R|: 0.012351796077454; threshold 0.01; FAIL
- order-sum/T max mismatch: 2.220446049250313e-16; threshold 1e-8; PASS
- normalization max mismatch: 1.1102230246251565e-16; threshold 1e-8; PASS
- structure anomaly: NOT_OBSERVABLE_FROM_SAVED_STATE
- no NaN/Inf or duplicate wavelength rows

The 453 nm row is the closure worst case. No renormalization or clipping was applied.

## Matched RCWA audit

The pinned CONTROL0 RCWA provider was read from the existing coupling terminal package; no RCWA was run. Existing ALT1 matched RCWA/FDTD rows were read from the frozen M11 table. Residuals and candidate separations are in CONTROL0_NEG0378_P_RCWA_VS_FDTD_AUDIT_V1.json, control0_rcwa_vs_fdtd_residual_long.csv, and matched_control0_alt1_22row_table.csv.

- provider-error classification: MIXED_WAVELENGTH_DEPENDENCE
- P-side decision stability: AT_RISK
- candidate ordering: MIXED_BY_WAVELENGTH
- CONTROL0 S recommendation: CONTROL0_S_MATCHED_HF_RECOMMENDED_FOR_FULL_DECISION_AUDIT
- full P/S two-sided decision: NOT_PROVEN (CONTROL0 S was not run)
- ALT1 handoff: NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY remains valid

## Governance

solver_calls_in_audit=0, rcwa_calls_in_audit=0, replay=0, attempt_002=0, CONTROL0 S=0, training/external/inverse=0. The original slot was released after the original attempt and no slot was reacquired.

Evidence directory: outputs/np_k6_m11b_control0_neg0378_p_matched_hf_v1/.

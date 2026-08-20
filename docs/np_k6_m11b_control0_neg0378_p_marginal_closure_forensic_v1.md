# NP K6 M11B CONTROL0-P marginal closure forensic v1

Status: MARGINAL_LOCAL_CLOSURE_EXCURSION; confidence MEDIUM.

CONTROL0-P has 10/11 wavelengths at or below the 0.01 closure gate and 1/11 above it. The worst point is 453 nm. ALT1-P has 11/11 passing points. Detailed values are in closure_profile_11points.csv.

The matched numerical contract is classified CONTROL0_ALT1_MATCHED_NUMERICAL_CONTRACT_IDENTICAL from the frozen formal setup diff and parent setup identity. Known incomplete source readback fields (angle theta and injection axis) are explicitly excluded from equality comparison and are not treated as physical differences. Geometry, ordered diameters and case identity are the intended differences. Both logs show successful early autoshutoff termination; final autoshutoff values are recorded in termination_and_shutoff_audit.json.

The transmitted air-side order set is stable across the band with no order appearance/disappearance or exact cutoff crossing. The nearest-air-cutoff and normalized kz audit is in order_cutoff_audit.json. This does not prove absence of substrate-side boundary sensitivity.

RCWA/FDTD residual-vs-closure correlations and the contamination classification are in provider_error_closure_correlation.json. The primary forensic classification is MARGINAL_LOCAL_CLOSURE_EXCURSION; the secondary interpretation is GEOMETRY_SPECIFIC_NUMERICAL_SENSITIVITY_PLAUSIBLE. The controlled attempt002 value decision is ONE_CONTROLLED_CONTROL0_P_ATTEMPT002_JUSTIFIED; the single proposed lever is reflection-monitor/reference-plane z-position robustness. No solver is authorized by this artifact.

CONTROL0-S remains not entered. ALT1 handoff remains NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY. ALT1 may proceed to Coupling Level-2, while a full CONTROL0/ALT1 H2 decision remains deferred.

Evidence: outputs/np_k6_m11b_control0_neg0378_p_marginal_closure_forensic_v1/.

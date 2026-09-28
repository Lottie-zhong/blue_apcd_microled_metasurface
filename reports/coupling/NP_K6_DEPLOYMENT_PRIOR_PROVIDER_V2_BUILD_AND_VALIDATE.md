# NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_BUILD_AND_VALIDATE

- STATUS: NP_PRIOR_V2_NOT_ACCEPTED
- SOURCE AUTHORITY: c8e6eb4; HF22 SHA256 `5c5dca90928498c927663ad3eedbf502394a68c741feef836195573846ba1599`; historical M9 OOF SHA256 `3184bb5aa2ff14d046bb6212847e1e4b443d0575e10d889ec002de14af6e76c8`
- V1 HISTORICAL STATUS: historical executable recovery closed; no full-data deployment provider frozen.
- V2 MODEL CONTRACT: ordered D1..D6 + wavelength + u_x + explicit P/S; LF ranking directly; multi-output Ridge residual spectral correction with inner geometry-LOGO alpha selection.
- LOGO VALIDATION: 22-fold geometry-LOGO, 484 rows, held geometry includes both polarizations and all 11 wavelengths.
- HISTORICAL REFERENCE COMPARISON: historical full-order OOF MAE approximately 0.03960; historical eta(+1) Spearman approximately 0.9616036; these are reference values only, not parity targets.
- V2 ACCEPTANCE GATE: `{"full_order_geometry_logo_mae": 0.06366880336792446, "full_order_mae_max": 0.05, "full_order_gate_pass": false, "geometry_broadband_eta_plus1_spearman": 0.9503105590062113, "ranking_spearman_min": 0.9, "ranking_gate_pass": true, "geometry_leakage": false, "ordered_d_correctness": true, "ps_explicit": true, "energy_output_sanity_pass": true}`
- FULL-DATA DEPLOYMENT STATUS: NOT_FIT_GATE_FAILED
- RANKING COMPONENT: frozen executable LF physics response; no learned ranking network.
- SPECTRAL COMPONENT: LF baseline + Ridge residual correction; R uses direct Ridge target because no legal LF R baseline exists.
- COUPLING FEATURE INTERFACE: `NP_PRIOR_FEATURES_V2`; P/TM/XLIKE future branch only.
- WAVELENGTH MASK: 445–455 nm valid; 440–444 nm and 456–460 nm explicit unsupported mask/rejection.
- COUPLING H1 CONTAMINATION: not read and not used.
- RUNTIME ARTIFACTS: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2`; manifest `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2\NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_MANIFEST.json`.
- ARTIFACT HASHES: recorded in manifest.
- SOLVER: zero FDTD/RCWA/HF acquisitions.
- NEXT: CHART_REVIEW_SKIP_NP_PRIOR_AND_PLAN_UNBIASED_FIXED_MDC_EXPANSION

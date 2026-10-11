# V3 phase design contribution (read-only sub-agent audit)

Verified DESKTOP-NNE313K, Coupling HEAD fa44f59ca3e3b8d4f73561375e756d12826ae936. No remote writes, FSP LOAD, solver, model fit, or confirmation-response read.

## One priority model: shared order/spectral physics-conditioned circular phase network

This is a proposed supervised integrated-state surrogate, not a Maxwell solver, an NP scattering operator, or a complex LF residual. Reuse the full-rank amplitude head and the independent P_scale branch. Do not replace either prediction with truth. A later training authorization must freeze optimization/checkpoint budget before any fit.

Physical coordinates: lambda=440..460 nm, m=-3..3, n=0, p in [TE,TM], original P_XLIKE input, output reference z_ref=1722 nm, original exp(-i omega t)/+z exp(+i kz z). Ordered positions x_j=[-725,-435,-145,145,435,725] nm, Lx=1740 nm. Six ordered diameters remain explicit; no sorting, cyclic quotient, or permutation-invariant pooling.

For the homogeneous air output define G_m=2*pi*m/Lx, k0=2*pi/lambda, kz_air=sqrt(k0^2-G_m^2)>0. Let z_top be the verified canonical NP top (1712 nm, verified by canonical geometry validator z_min1212/z_max1712; source pinned in SOURCE_AUTHORITY_PINS.json); P_out=exp(+i*kz_air*(z_ref-z_top)). This is exact continuous-medium propagation between these air reference planes, not a claim about internal NP scattering. Reference-to-monitor de-embedding uses C_ref=C_sample*exp(+i*kz_air*(z_ref-z_sample)), actual sample z only. Never use nominal monitor z in place of actual samples.

The deterministic geometry descriptor is g_m(D)= (1/6)*sum_j[(D_j/230)^2*exp(-i G_m x_j)]. This is the Fourier moment of ordered cross-sectional-area weights, NOT a complex transmission coefficient or physical phase truth. Signed m and x phase origin must remain explicit. g_-m=conj(g_m) does NOT impose that C_-m=conj(C_m); the model also receives all six ordered D coordinates.

Only the existing normal-incidence MDC r_L,t_LR,r_R,t_RL can currently be consumed. Four complex numbers at each lambda supply 8 Re/Im features. They are GaN/SiO2 interface amplitudes, not air amplitudes; 975 nm MDC excludes the 237 nm SiO2 spacer. P_sp=exp(+i*k0*n_SiO2(lambda)*237 nm), passive material branch, can be computed from the formally pinned Native-M1 material interpolation used by the TMM helper. Apply this as a conditioning feature once, not an asserted NP/MDC cascade. A material lookup discrepancy or missing source pin must block this feature until reconciled, not silently use a constant refractive index. No oblique r_R(m) values are presently frozen; do not pretend normal r_R is the m!=0 return coefficient.

Per-coordinate input v(D,lambda,m,p) has 23 entries: [(D-100)/130 six entries, (lambda-450)/10, m/3, TE/TM one-hot two entries, kz_air/k0, Re/Im P_sp two entries, Re/Im of r_L,t_LR,r_R,t_RL eight entries, Re/Im g_m two entries]. Geometry and lambda ranges are fixed authority scales. Any optional train-centering must fit only current training geometries; no per-query adaptation or held-out truth. Fixed physical features vary across order/wavelength and enter a SHARED head, so they are not just constant vectors appended to a geometry-to-whole-spectrum KRR.

One shared 23 -> 32 -> 32 -> 2 tanh network produces w=(w_R,w_I) for all 294 coordinates, retaining all TE/TM channels including weak ones. Trainable parameter count=768+1056+66=1890. All wavelengths/orders of one geometry remain one grouped sample; 294 outputs are NOT independent geometries. No separate fits for each order, no rank-2 PCA, no GNN, no NP88 extension, no inverse design.

u_hat_res = (w_R+i*w_I)/|w| if |w|>64*eps64, otherwise 1. C_hat_pred=A_frozen_pred*P_out*u_hat_res. rho=|w| is retained as an uncalibrated concentration diagnostic only, never a calibrated uncertainty or post-hoc shrinkage knob. P_scale_pred is the original positive independent prediction. Output is 21x7x2 complex=588 Cartesian real coordinates plus 21 P_scale=609. No additional C_hat renormalization or clipping. H2 and original H1 must be run unchanged. Because H2 has no phase cross term, identical A/P preserves routing/order power to roundoff and cannot itself establish complete-state gain.

Training-only phase targets: for coordinate energy fraction e=|C|^2/sum_(m,p)|C|^2 at that wavelength, reliable=e>=1e-4 and |C|>0. Reliable target u_res=(C/|C|)*conj(P_out); unreliable target=1, phase loss weight=0. Weights normalize over reliable coordinates inside each geometry. Zero/weak target phases have no physical uniqueness; all output channels nevertheless remain present. No dominant-mode reference, no switching, no HF inference oracle, no global phase alignment, no naked angle regression. At reliable coordinates round-trip C=A*P_out*u_res is exact; at exact zero any unit phase gives C=0. Canonicalizing nonzero weak phases is lossy but bounded by their measured energy and must be reported separately; do not call that exact full-state parity. Exact mathematical representation audit should retain original phase for every nonzero coordinate, separately from training masking.

Use one preregistered coherent phase objective (fixed three normalized components, equal coefficients): L_abs=weighted |u_hat_res-u_res|^2; L_spectral=weighted |u_hat(lambda+1)*conj(u_hat(lambda))-u_true(lambda+1)*conj(u_true(lambda))|^2; L_order=weighted |u_hat(m)*conj(u_hat(n))-u_true(m)*conj(u_true(n))|^2 over all same-polarization order pairs m<n. Pair weights=sqrt(e_i*e_j) with both reliable; each component normalized per geometry and omitted with explicit count when denominator zero. No assumed linear spectral phase or enforced +/-m conjugacy. Absolute term retains common phase, pair terms encourage cross-order/spectral coherence without eliminating physical incident gauge. This objective is a hypothesis; it is not shown superior in this audit. Optimization and fit count are future authorization items, not executed.

Why this is a model change rather than a phase-relabeling trick: for multioutput isotropic KRR W=(K+alpha I)^-1 Y, a fixed block-orthogonal output rotation Q gives W'=WQ and inverse-rotated predictions W'Q^-1=W exactly (provided scaling is rotation-invariant). A D-independent per-coordinate propagation/TMM carrier alone cannot improve that KRR. Here the new hypotheses are shared order/wavelength parameterization, explicit signed modal/geometry features, and coherent losses. Carrier removal alone is not a scientific gain claim. Pointwise/non-invariant scaling could break mathematical equivalence but would be an implementation/protocol change, not physics evidence.

## Mechanistic evidence and boundaries

OBSERVED: original circular phase error dominates full-state SSE (81.3%). 1-NN all124 state median1.132484, S31 local11 median0.306594, global113 median1.148178; the user headline1.132 is pooled, not global113. Global distance-phase Spearman0.024468. Weak TE is retained but cannot drive selection. Current labels show +/-3 relative coherence median0.817908 vs individual absolute coherence0.128817/-3 and0.095161/+3. This supports testing coherent structure, does not prove exact symmetry or a physical operator.

SUPPORTED_HYPOTHESIS: shared spectral/order conditioning may learn phase relationships more effectively than independent588-output KRR. Deterministic free-space phase and fixed MDC dispersion are legitimate known context; Fourier geometry moments may encode spatial interference grammar. These are inductive biases, not verified scattering responses.

UNRESOLVED: NP/MDC multiple-reflection mechanism is not identified by the existing single-input integrated state. PRENP/POSTNP E/H can support retrospective upward/downward modal diagnostics only; they are NOT query inputs. NP complex archives have explicit two-port FAIL for incident reference and scattering normalization. A valid LF residual requires a full compatible incident-normalized multi-order NP T/R block, return inputs, TE/TM basis, reference planes and whole21-point wavelength support; none is supplied by NP88. Improving NP standalone accuracy is not necessary for this priority model, and cannot fix missing complex contract. Obtaining legal NP complex scattering is a separate optional future route with its own data/solver authority, not required to execute this supervised feature-conditioned model.

V3 numerical repeats must establish whether +/-5 nm response exceeds same-contract independent-run error; two mesh diagnostics only show tested sensitivity, not strict convergence. This audit does not assign a phase model future PASS or change frozen H1.

## Source verified records (absolute paths and complete SHA256)

- D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_NP_MDC_MULTIFIDELITY_AND_COMPLEX_RESIDUAL_AUDIT_V1\EVIDENCE_INDEX.json : 93ace31da3f782968145bafc1494fb13968caa0624caa537e8cc21cc75b2ab90
- Same directory MDC_COMPLEX_RESPONSE_MATRIX.md : 95263f842ec1eb3cf3991f4e8ab8099dce52c3574fde7ac8fd29484d8d94117c
- Same directory NP_FEATURE_CAPABILITY_MATRIX.md : 7a450d08e34177bec90bead71690fdfada4a516f465c7b3d48897ed7d7b9b73e
- Same directory LF_HF_COMPATIBILITY_MATRIX.md : cdd52baa11a6b4931ec5a8e3c0ef202a5ed3eac44438a0020babcb50c1f157c1
- D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\MDC_TMM_COMPLEX_2PORT_PRIOR_V1_HANDOFF.json : af1e471f91103664058d98540e2e2dc5555ab6852aef622dd448d1b787611c3b
- D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\reports\MDC_TMM_COMPLEX_2PORT_PRIOR_V1.json : b8e856fed0c7859b6ce3d1aa7d40549f40720b0c317b6f3dbf362e62c7e37a38
- D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts\mdc_tmm_complex_2port_prior_v1.py : a7d618b697a71ed59bf8b56d9d5239b570f0cb03f9f650497fa49ce37a5a6a00
  _normal_response lines81-88 calls normal_stack_power; _response_for_direction lines91-104 reverses layer order and media; evaluate_row lines107-149 rejects oblique angle and emits complex bidirectional amplitudes with admittance/power diagnostics. Time/reference convention lines206-216.
- D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_complex_two_port_reference_plane_contract_v1\contract_manifest.json : a51a36dd1e9aa6f67fab3d43d132b38280a45705ae60ded3820b9f7d3e4ca45b
- Same NP directory incident_phase_audit.json : b8dd7d5348fcb7ed3fafc2a7b157167355139a9bca62e3649ee2c36f95112b25
- D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_ORDER_RESOLVED_PHASE_AND_LOCAL_CONDITIONING_AUDIT_V1\ORDER_RESOLVED_PHASE_STRUCTURE.json : 60852e78a486042a2b683d5d3e55fa4494907fec8a023f79cd35dedd53b67a0d
- D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_GEOMETRY_NEAREST_NEIGHBOR_PHASE_TRANSFER_AUDIT_V1\NEXT_DIRECTION_SCIENTIFIC_DECISION.json : cdbee2ab7940ce33cf9037428f8c741d66cedd52662a7c27d80412ace500409c
- Same NN directory FINAL_REPORT.md : a979e7672491e9b2ee660f5f762e5882ffebe47f651aa02592cc14a431a0bbdc
- D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json : 93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f

Local supporting read-only scripts/stdout: v3_phase_read.py .. v3_phase_read5.py under C:\Users\zlt\.codex\tmp\gpu_takeover_20261009. Main owns final report source inventory and commit, this contribution is not an independent authority.

## Material source pins

Native-M1 spacer index must use existing frequency-linear complex-epsilon interpolation with passive square root; no outside-domain extrapolation or constant-index fallback.

- `D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts\apcd_native_materials.py`: 12a1b183380137b50d0d381e6c93c1877ae5ed552d8b3807deb8a06fb297b07a (get_complex_index line99).
- `D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\configs\mdc_defect_450_material_policy.json`: 73d1ab830795dd7bcd5ed7fa49f2f84653a151151a823a82969e2ab5ee8f98ee.
- `D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\outputs\material_reference\mdc_blue_oujizi_m\material_ref_native_sampled_mdc_native_m1.csv`: 16cf9219c577ad264c10d0e9933a40e9b9f1a43775878ae52806cecc47a4f4b6.

Model training remains a proposed next-stage authorization. Minimum 4 paired geometry-grouped phase fits, plus1 final phase fit only after explicit approval. Four frozen amplitude/P_scale fold models may be reused for their matched predictions; absence of a legitimate final full-rank amplitude model must be declared before blind evaluation. No silent new amplitude/P_scale fits or ensemble convention.

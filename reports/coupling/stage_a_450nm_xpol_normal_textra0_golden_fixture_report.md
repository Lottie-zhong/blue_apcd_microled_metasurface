# APCD MDC-NP Coupling V1 Stage-A golden fixture report

Task: `APCD_MDC_NP_COUPLING_V1_STAGE_A_450NM_XPOL_NORMAL_TEXTRA0_GOLDEN_FIXTURE_FULLWAVE`

Formal state: `APCD_MDC_NP_COUPLING_V1_STAGE_A_450NM_XPOL_NORMAL_TEXTRA0_GOLDEN_FIXTURE_COMPLETE`
Joint scope remains `EXPLORATORY_ONLY`; this is a direct periodic plane-wave joint full-wave result, not Micro-LED/device efficiency or ML optimization.

## Golden fixture

- MDC: `P1_ZL1_ALTERNATIVE_G3_A3`, ZL-1 alternative, 12 layers, total 975 nm, final `APCD_SIO2_NATIVE_M1` 79 nm layer.
- NP: `NP_K6X_125_135_150_175_190_210`, six pillars ordered from physical -x to +x, H=500 nm, period 1740 x 290 nm.
- Stack: `APCD_GAN_NATIVE_M1 -> MDC -> MDC final 79 nm SiO2 -> t_extra=0 -> RUN3A K6-x -> Air`.
- Source: 450 nm, x-pol, normal incidence, `u_x=0`; `m=+1` is physical +x.
- Pre-FSP entry-time SHA256: `5b348658f3ba3acb5f48fe95ab861d97a57722f7fe3caee3c3285d05115d0643`.
- Current pre-FSP path SHA256 after the run: `b403f4248747903a9afb5c7a00ab467fa1b4fbefd27809510c017a109bb9d8ce`; Lumerical performed a post-entry setup-side mutation (`_p0.log` evidence). The entry-time hash is immutable in the ledger/setup records; no replay was performed.
- Post-FSP: `cfda69e11338ec90ac3a13cc185710c9910567e3dc8fcac0216699925c6b0269`.
- Post-FSP identity audit: PASS.

## Full-wave result

- `R_total=0.115330140299`; `T_total=0.332909083774`.
- `eta_t(+1)=0.290305555168`; `eta_t(0)=0.008603709728`; `eta_t(-1)=0.003159508023`.
- `theta_out(+1)=14.988234482305 deg`; directionality `0.989233784802`.
- Transmitted open x-orders: `m=-3..+3`; reflected open orders include x `m=-9..+9` and y `m_y=-1,0,+1` where propagating.
- Order closure: transmitted residual `0.000e+00`, reflected residual `4.163e-17`, PASS.
- `R+T=0.448239224073` and residual `0.551760775927`. This is reported as Native-M1 GaN absorption under the project loss convention; formal lossless `R+T` tolerance is not claimed.
- Dominant redistribution: Native-M1 GaN absorption residual `0.551761` and reflection `0.115330` dominate the reduction in source-normalized +1; transmitted non-target power is led by `m=+2` (`0.024046`).

## Standalone comparison

Formal RUN3A reference was read from `D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_p1d4b_k6x_phase_candidate_run3a_audit_v1\run3a_order_sign_audit.json` at NP authoritative commit `7a8588f6b5a1c96d88813f60406d418b488135fd`, artifact SHA256 `065c6dcf449777d7eef0cbe1bd50afb3ff9c417e62f34106e08e9af401269902`:

- standalone eta(+1) `0.745970692811`; eta(0) `0.010478489513`; eta(-1) `0.005755124074`; directionality `0.992344118101`.
- joint minus standalone: delta eta(+1) `-0.455665137643`; delta eta(0) `-0.001874779785`; delta eta(-1) `-0.002595616051`; delta directionality `-0.003110333300`.

The comparison is provenance-aware but not an equal-substrate control: standalone RUN3A is SiO2-substrate/RUN3A/Air, while this joint case contains lossy Native-M1 GaN and the MDC stack. The observed +1 reduction is therefore a diagnostic of the full joint stack plus source-medium loss, not a standalone steering failure.

## Safety

Exactly one physical FDTD case entered and completed. No B0/B1/B2 solver, spacer sensitivity, y-pol, oblique angle, second wavelength, sweep, training, surrogate field, sealed-test read, or Test40 read was performed. No source worktree was written.

Artifacts and hashes are indexed by `registries/coupling/stage_a_result_registry_v1.json`; FSP and raw arrays remain untracked generated artifacts. The pre-FSP mutation is an audit caveat, not a solver replay trigger.

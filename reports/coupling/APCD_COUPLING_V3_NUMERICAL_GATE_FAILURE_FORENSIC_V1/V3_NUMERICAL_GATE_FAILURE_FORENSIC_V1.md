# V3 numerical gate failure forensic V1

Observed UTC: 2026-10-12T04:01:21.737330+00:00. Coupling inspected HEAD: `d84401bd5e907a0ad82f29bcb00029bc6edc34a1`. Host DESKTOP-NNE313K / DELL.

**FORENSIC_PARTIAL — NUMERICAL_ROOT_CAUSE: LIKELY — NUMERICAL_ADVANCEMENT: HOLD**

The grid-dependent response difference is reproduced directly from native E/H. No case-pairing or 609D extraction error was found. Attribution to spatial mesh alone is not closed: all four solves reached the fixed 3 ps time limit, and the actual 3D conformal material mask/high-field volume was not saved. No production change or new solver budget is authorized.

## 1. Authority, scope, and production safety

Four diagnostic attempts only, plus the two immutable historical references explicitly pinned by the repeatability protocol. No other development response or sealed response was scanned. DELL is the production custodian; data was read under its existing ACL, without impersonation or access changes.

V3 remains 4 entered / 4 truth-valid / 4 labels-valid / 52 unentered; replay=0. Development remains 156G. New FDTD=0, RCWA=0, fits=0, P_scale fits=0, confirmation/sealed access=0. No native LOAD session, setup save, Scheduler/release/controller/queue or time-policy mutation. The numerical receipt and ledger hashes were checked before and after analysis. This is a scientific numerical HOLD, not a 10:00 window stop.

Frozen numerical protocol SHA: `7407bfb3df56501a4b5b178caa0b7a7777b785f34dbb4fdd6eed65f8e7272d8e`. Receipt SHA: `c2511d1571d61f7d1593cc5b3a954627582a49f150251392a58db5a1352d624b`. V3 registered interface SHA: `9f0c04217174ff9bd29b0cda9440f6a85f99b77b3843a8244762f257c4785cd9`. Full absolute source paths/SHA are in SOURCE_SHA_INVENTORY.json. User AGENTS instructions govern; no AGENTS.md was found at the checked remote worktree/project locations.

## 2. Independent 5 nm physical solves

A1 = [120,160,165,175,160,195] nm, compared with historical K6GDP2_DEV_G001. A2 = [210,115,175,115,180,125] nm, compared with historical K6GDP2_DEV_G004. These are two repeat experiments at different geometries, each paired with its own historical solve. They are not replicates of each other. All use attempt_001 and one consumed entry.

| Case | Engine PID | UTC start / return | Launcher wall s | FDTD wall s |
|---|---:|---|---:|---:|
| K6V3_NUM_REPEAT_A1 | 32020 | 2026-10-11T12:23:23.730544+00:00 / 2026-10-11T12:32:52.631841+00:00 | 568.901 | 548.960819 |
| K6V3_NUM_MESH4_A1 | 46160 | 2026-10-11T12:35:39.448646+00:00 / 2026-10-11T12:54:34.934361+00:00 | 1135.486 | 1110.598597 |
| K6V3_NUM_REPEAT_A2 | 46400 | 2026-10-11T12:58:20.333372+00:00 / 2026-10-11T13:07:44.298473+00:00 | 563.965 | 544.070146 |
| K6V3_NUM_MESH4_A2 | 29044 | 2026-10-11T13:10:31.702532+00:00 / 2026-10-11T13:29:30.996846+00:00 | 1139.294 | 1114.424456 |

Each request has a distinct attempt directory, engine creation event, completed 3D GPU log, source/setup SHA, solved FSP, native six-component H5, entry receipt and validation/label lineage. Source FSP and solved FSP hashes differ; actual engine executable is fdtd-engine-msmpi.exe. The run logs show GPU 68 SMs, real32, full meshing and complete time stepping, not a LOAD-only operation. Native API launcher log is empty; the substantive independent solver evidence is run_p0.log plus process events, not that empty log.

Both new 5nm native H5 datasets (all monitors, coordinates and six components) are bitwise identical to their corresponding old native H5 payloads. All raw NPZ arrays are also bitwise identical. Old solver returns predate the new engine launches by days. Therefore equality is backed by new physical execution evidence, not inferred from equal labels. Deterministic real32 execution with identical setup/engine conditions is consistent with this observation; two geometries do not establish reproducibility under other GPU, precision, fit, or machine conditions, nor numerical accuracy. Raw/native payload hashes and exact historical paths are retained in FIVE_NM_REPEATABILITY.json and NATIVE_PAYLOAD_SHA.json.

## 3. Complete available physical/setup comparison

Full recursive comparison of actual fresh-LOAD readback for A1 and A2 finds only case identity, FSP path/SHA, and NP_DERIVED_BASELINE_N2 step [5,5,5]→[4,4,4] nm. The 4nm actual_readback is used; its canonical_readback is the pre-change 5nm record and must not be mistaken for the solved setup. Both declared-only-mesh validators report PASS.

| Item | 5nm / 4nm evidence |
|---|---|
| Ordered geometry / CAD | Same six circle centers x=[−725,−435,−145,145,435,725] nm, y=0, radii D/2, z=1212…1712nm, height 500nm |
| Period / region | Same 1740×290nm periodic cell; z=−600…3000nm, 3D |
| MDC / spacer | Same 12-layer TiO2/SiO2 MDC: 44,79,44,79,44,316,44,79,44,79,44,79nm; total975nm. Same237nm spacer to1212nm |
| Materials | Same Native-M1 names and sampled-data SHA for GaN/TiO2/SiO2; recovered GaN frequency indices used without fitting |
| Sources | Same two enabled, co-located frozen X-forward source objects, z=−250nm, angle0°, amplitude1, phase0°, 440–460nm standard pulses. Both existed in the frozen source; no source was added by the mesh diagnostic |
| P/S / incidence | P_XLIKE, normal incidence kx=ky=0; output TE/TM are two modal coordinates for one incident state, not a full Jones/multiport operator |
| Boundaries / PML | Same x/y periodic, z PML, 8 PML layers |
| Mesh overrides | 10nm MESH_NP_MDC_SPACER_BASELINE unchanged; NP_DERIVED_BASELINE_N2 [5,5,5]→[4,4,4], center z1462nm, z span700nm (1112…1812nm) |
| FDTD options | Mesh accuracy4, conformal variant0, dt stability0.99, simulation time3ps, auto shutoff minimum1e-6, unchanged |
| Monitors | Same full-period IN−100, PRE1150, POST1800, reflection−400nm nominal positions; 21 points, wavelength spacing and source limits unchanged |
| Reference / normalization | IN reference−50nm, POST1722nm; same +z incident (0,0) TM phase and power normalization |
| Modal order / wavelength | Same m=−3…3,n=0, TE/TM, 440…460nm at1nm; all seven propagate in air across band |

Actual full-volume grids: 350×60×372 (5nm) versus437×75×412 (4nm). Time step: 9.53287e-18s versus7.60204e-18s. Completed314700 versus394631 updates, both approximately3ps. All four stopped at the time limit; last reported99% auto-shutoff values are 6.7674e-5,5.72136e-5,4.96233e-5,3.63202e-5 respectively, above1e-6. No claim of temporal convergence is justified.

POST actual sampling z changes 1802→1801.095744680834nm; PRE1152→1150.829787234041nm; IN remains−100.787739408888nm. True pillar-top gap is90→89.095744680834nm, not the10nm reference-to-top gap. Actual-z propagation to1722nm is applied separately to each dataset. The uncompensated air Δz phase bound at440nm is about0.01291rad; it is smaller than the observed strong-mode phase RMSE, and this offset has already been deembedded.

Complete available readback is saved in ACTUAL_GRID_AND_CAD_EVIDENCE.json; diff in COMPLETE_READBACK_CONTRACT_DIFF.json. Missing from saved evidence: full volume Yee/conformal permittivity coefficients, detailed mesh-grading sequence, fitted dispersive pole coefficients, detailed pulse waveform settings beyond stored readback, PML cell-by-cell profile, local high-field volume. Equal material tables do not independently prove every fitted pole. These gaps are stated, not filled from assumptions.

## 4. Independent native E/H → 609D calculation

Native run_output.h5 contains all six complex components (interleaved float32 real/imag) and micrometre coordinates; wrapper truth.h5 contains metrics_json/raw_json and is not the E/H container. Raw NPZ contains complex six-component fields with SI coordinates. Both are hashed.

Independent implementation integrates actual x/y coordinates with trapezoidal half-endpoint weights and exp(−ikx x), solves a six-component E/H four-channel (+TE,+TM,−TE,−TM) basis with passive kz, then deembeds exp(i direction kz(zref−zsample)). IN(0,0)+TM supplies a single physical source phase/power normalization. C_hat divides by sqrt(sum q|C|²), q=kz/k0. P_scale is independently integrated POST Poynting flux divided by IN incident power. No global oracle alignment or power-ratio fitting is used. Native H5 stores magnetic fields in impedance-scaled units; H/ETA0 gives SI H. Its common wavelength-dependent excitation factor cancels through incident phase/power normalization. Direct native-H5 reconstruction confirms this mapping, without estimating a correction from label truth.

Raw E/H→C_hat max error across four cases: 6.886e-15; P_scale max absolute error: 7.605e-15. Native H5→C_hat maximum relative L2: 1.411e-10; native P_scale max relative error: 3.079e-10.

Independent power-weighted H2 reconstruction was also checked against the unchanged frozen evaluator; see FROZEN_H2_INTERFACE_AUDIT.json. Published label eta is native-grating eta, distinct from modal H2 eta by existing small differences (max2.931e-4 here). This is not a newly relaxed tolerance or the0.045/0.117 mesh difference. All gate comparisons in this audit use the frozen H2 modal path.

Floquet fit residual maxima are3.1e-6…6.1e-6; SI mixed E/H basis condition max618.52; downward/upward propagating power max about3.15e-5. These do not prove absolute accuracy. Periodic endpoint closure and actual coordinates are saved explicitly. Evanescent modes are not assigned far-field power. Full-plane flux versus seven upward modal power is distinct because flux includes downward and weak nonpropagating contributions. Existing1−R−T energy closure is algebraic when A is defined from R,T; it is not independent absorption validation.

## 5. Wavelength / modal error attribution

| Pair | State max (median) | Routing max | Absolute-order max | Power max relative | Significant phase RMSE max |
|---|---:|---:|---:|---:|---:|
| A1 | 0.130251 (0.032064) | 0.045038 | 0.016211 | 0.160485 | 0.123231 |
| A2 | 0.192538 (0.028735) | 0.116551 | 0.031465 | 0.322073 | 0.174215 |
| Frozen threshold | 0.02 | 0.005 | 0.005 | 0.01 | 0.05 rad |

Both pairs fail every listed maximum gate. Maxima can occur at different wavelengths; no average substitutes for the conjunctive gate. A1 state worst is446nm; A2 is460nm, with another major excursion at446nm. The full21-point curves and all294 modal coordinates per pair are retained.

Exact decomposition: |C4−C5|²=(A4−A5)²+2 A4 A5(1−cos Δphi). A1 amplitude/phase fractions21.26%/78.74%; A2 32.34%/67.66%. TM contributes >99.999997% of total SSE. Weak coordinates under the frozen near/reference fraction1e-4 mask contribute <3e-8 of total SSE. Thus near-zero TE phase cannot explain the failure.

A1 order SSE fractions m=−3…+3:8.54%,7.69%,14.51%,14.39%,24.81%,25.50%,4.55%. Main channels include+1 and+2. A2:20.19%,6.60%,12.71%,27.00%,10.70%,4.55%,18.24%; m0,−3,+3 matter. Error is not solely+1 or a single weak high order. Amplitude and power also change; a phase reference error alone cannot account for the routing/flux changes.

Incident-power ratio4nm/5nm stays within0.99876…1.00281, while total transmission differs by up to32.21%. Raw POST flux changes dominate the scale difference; source denominator changes are below0.3%. This supports a native-field response change rather than an importer normalization artifact. No causal claim that one pillar or one resonance explains it is made.

Figures: WAVELENGTH_COMPARISON.svg/pdf/png; ORDER_POLARIZATION_ERROR.svg/pdf/png; COMPLEX_AMPLITUDE_PHASE.svg/pdf/png. Sources: WAVELENGTH_ERROR.csv and MODAL_AMPLITUDE_PHASE.csv. No spectral smoothing, oracle phase alignment, or missing-data exclusion. Weak/strong masks, unmasked phases, real/imag and all amplitudes remain in CSV.

## 6. Geometry discretization and convergence boundaries

Nominal CAD is unchanged. Saved transverse coordinates, grid dimensions and time steps demonstrably change. The fine override overlaps the TiO2 pillars and upper spacer, with mesh transitions nearby; the MDC layer CAD is unchanged and mostly outside this fine override. Circular boundaries and high-index interfaces will be represented on different grids. Analytic circle-node counts on monitor transverse coordinates are provided only as an illustration; they are not the solver conformal fill fractions.

No saved full-volume material mask/high-field map allows direct assignment of the difference to pillar edges, spacer interface or a resonance hotspot. Those mechanisms are plausible, not demonstrated. A4nm result is not automatically closer to the continuum than5nm, and two resolutions cannot establish an extrapolated converged value. Fixed3ps truncation can couple to mesh-shifted resonances; this remains unresolved.

## 7. Scientific cause verdict

| Category | Finding |
|---|---|
| A PROVENANCE_OR_CASE_PAIRING_ERROR | Not found: case/attempt, geometry, request, raw/native and labels all bind; independent repeat engines and raw payloads verified |
| B LABEL_EXTRACTION_OR_REFERENCE_ERROR | Not found for609D: independent raw and native calculations reproduce C_hat/P_scale; actualz and ±z signs checked without alignment |
| C SOLVER_OR_SETUP_CONTRACT_MISMATCH | No extra mismatch in available fresh readback. Only declared fine-mesh step changes; detailed unsaved settings remain a limitation |
| D GENUINE_MESH_SENSITIVITY | Grid-dependent native field/state/power difference is observed. Spatial-mesh mechanism is LIKELY; exclusive cause and convergence are not proven |
| E UNRESOLVED | Temporal truncation/mesh interaction, actual conformal voxel changes, material pole fit identity and high-field localization |

## 8. Consequences for156G and minimal next proposal — DO NOT EXECUTE

Original156G labels remain provenance-valid under their frozen5nm contract; no labels, historical results or H1/H2 were altered. They are not thereby certified mesh-converged physical truth. These two cases show that numerical sensitivity can be comparable to scientifically important phase changes; this limits absolute physical claims and interpretation of±5nm geometry perturbations. It does not demonstrate that all156G are invalid or that observed ML errors are exclusively numerical.

First priority: a separately reviewed space/time convergence diagnostic on these two exact physical geometries, with new independent scientific identities. Stage1 proposal:4 entries (5nm and4nm at each anchor) under an independently frozen longer-time/stricter-decay diagnostic contract, retaining6-component fields and full grid/material-coefficient evidence if available. Compare temporal convergence at fixed mesh before attributing remaining differences to spatial mesh. If significant differences persist, Stage2 proposal:2 additional3nm cases (one per anchor), after its own budget approval. This staged4+2 proposal is not an authorization, is not replay, and excludes historical failed attempts.

Do not automatically adopt4nm canonical mesh. Review time/mesh cost and convergence evidence first. No zero-solver label repair is warranted by current evidence. Existing preserved FSPs could support additional custodian-owned LOAD-only extraction of detailed grid/material evidence if separately authorized; this audit opened no new native sessions. Advancement of remaining52 stays frozen regardless of revised diagnostics until Chat scientific decision.

## 9. Artifacts, tests, and recovery entry

Start from CONTINUATION.md, FORENSIC_PROTOCOL.json, TEST_AND_SCOPE_AUDIT.json and this report. Independent scripts and source hashes are included. Basis recovery, trapezoidal endpoints and amplitude/phase identity synthetic tests pass; no fit. Native-H5/raw/label and frozenH2 comparisons are saved, not substituted into originaltruth. Source input and ledger/registry/gate hashes were checked unchanged.

SHA_INVENTORY.json hashes all task artifacts except itself; SOURCE_SHA_INVENTORY.json records full source SHA and absolute paths. Final commit identity is reported at handoff; inspected parent HEAD is above. Unrelated staged/dirty files are preserved.

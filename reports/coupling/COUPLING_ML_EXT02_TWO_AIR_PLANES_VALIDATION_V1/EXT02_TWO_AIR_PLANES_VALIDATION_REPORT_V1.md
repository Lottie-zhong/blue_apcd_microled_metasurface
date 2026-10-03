# COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1

- Status: BLOCKED_PREENTRY / PARTIAL. The frozen Runner authority does not admit the requested EXT02 diagnostic contract. No setup copy was modified, no staging FSP was created, and no solver-capable CLI was invoked.
- Date: 2026-10-04
- Remote: DESKTOP-NNE313K / desktop-nne313k\dell.
- Coupling worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1; branch work/mdc-np-coupling-ml-v1; input HEAD 03f4a5b737a99bb0ec5b6a0d38b64a5d51ad1a3f.
- Expected task-start HEAD bdc540baa0b0455b4c13b4a3f3471b2af86e8b7e is an ancestor. Later commits include the completed train-validation trajectory audit; no reset or checkout occurred.
- Runner worktree is clean on codex/apcd-gpu-production-runner-v1 at 1afa3e30f1de5e0192be6240a3754c89e2eb6f25; its frozen executable code is commit 783bd5741eb5e6853a3be5532624f4282f9488b7. The later commit updates authority/handoff/qualification evidence only.

## Solver and replay accounting

- This task: 0 solver entries, 0 FDTD runs, 0 post-entry automatic replays.
- The Runner registry had 12 historical rows: 11 DONE and the preserved S35 FAILED_POSTENTRY. This task created no run ID or registry row.
- No process was stopped or modified. A read-only host snapshot showed 8 fdtd-solutions.exe, 2 ansyscl.exe, 1 ansyslmd.exe, and 1 ansysedt.exe; this task did not query or use the GPU slot.

## Planes and mesh limits

- The monitor audit records EXT02 NP z=1212–1712 nm; existing POSTNP nominal z=1800 nm and actual saved sample z≈1802 nm, 90 nm above the NP top. The de-embedding reference z=1722 nm is 10 nm above the NP top.
- The original FDTD top is z=3000 nm. The previous audit inferred a configured PML inner edge near z=2806 nm from the eight-layer layout grid.
- The planned z=2000 nm plane would be nominally 288 nm above the NP top and about 806 nm below that inferred PML edge. The intended monitor copies the existing full-period 1740×290 nm span and six E/H components.
- The plane at 2000 nm was not instantiated. Its actual nearest-mesh sample z, local mesh coordinates/spacing, and final clearances are not measured. It lies beyond the prior local mesh override extents, so its grid may differ from the near plane. New-plane air/PML/structure clearance is a design estimate, not a validated setup readback.

## Frozen comparison protocol

- DIAGNOSTIC_PROTOCOL_V1.json freezes actual-z de-embedding to 1722 nm, the official full-period E/H Floquet projection with ±z × TE/TM, and the extractor propagation signs. Global-phase oracle alignment and fitted power rescaling are prohibited.
- The near-truth significant mask is frozen per wavelength as |c_near|² / sum_propagating(|c_near|²) >= 1e-4. Significant-coordinate phase RMSE uses near-plane amplitude weights; unmasked results and per-order amplitudes remain separate.
- Engineering thresholds remain: propagating-state relative L2 <=0.02; max per-order routing difference <=0.005; max source-normalized absolute-order difference <=0.005; propagating total-power relative difference <=0.01; significant-coordinate amplitude-weighted phase RMSE <=0.05 rad.
- These are one-case inter-plane consistency thresholds, not H1/production gates. No complex coefficient, power, routing, endpoint, least-squares, Poynting, or evanescent comparison was computed. Historical EXT02 truth is unchanged; repeatability remains distinct from cross-height validation.

## Exact Runner incompatibility

The current machine authority file is D:\project\worktrees\blue_apcd_gpu_production_runner_v1\APCD_GPU_PRODUCTION_RUNNER_V1_AUTHORITY.json. Its approved Stage-1 list excludes K6V1_EXT02. Under the pinned 5nm authority root, EXT02 has no authority_input_manifest.json or load_only_validation.json. Its SHA256 is 021951707cd94d62ca93076f5f2a6867b400df4c9921932286b32ffc1840972c; the current handoff markdown SHA256 is 397e41476938392d43e7eaf6c5252425991a8bfa62b7fb88442bf5da4fe0feb7 and handoff JSON SHA256 is ca7e4a9fcc15ccb60f4921feb788bf3663e1b8fd3c56f64892894cc8299df599.

The frozen adapter source is D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1\adapter.py with SHA256 e9b105c7ab71274c619d8c9f0aa27ef4a204cc8a8466f0ab4a354e3bcc97cfcf. In adapter.py lines 363–430 and 510–528, setup validation requires the exact case authority root/schema, case spec, approved LOAD-only proof, production contract SHA256 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5, expansion hash, canonical source FSP path, and exact source/staged FSP hash parity.
- Handoff documents adapter.py run-one <immutable-case-manifest.json>. A cloned FSP with the added monitor cannot match the approved canonical FSP path/hash. The Runner pins its production contract; reusing that hash for the modified setup would misrepresent the contract, and changing the hash is rejected.
- Thus the interface cannot admit this independent EXT02 monitor overlay without changing protected Runner authority/code or bypassing its validator. I stopped before staging or invoking run-one, as required.
- PROPOSED_DIAGNOSTIC_CONTRACT_V1.json contains candidate design fingerprint SHA256 0842d2d3dcbab38cb193227f6c11c8cf0d759b3bf69671005fd20586cdd50153 only. It is not an actual/materialized setup contract and is not accepted by the Runner.

## Dependency check and next review

- The Runner internal read-only postprocess dependency preflight passed under N:\anaconda_envs\RCP_LCP\python.exe 3.10.20 with NumPy 2.2.5, h5py 3.16.0, Lumerical 2025 R1, and pinned launcher/state/TMM hashes. This checks dependencies only; it is not a legal EXT02 case preflight.
- At scientific review, decide whether the Runner authority owner should provide an explicitly supported diagnostic-only case/monitor-overlay schema and matching immutable EXT02 authority/LOAD-only proof. Until then, do not change Runner code/authority, substitute another case, or start a solver outside its frozen entry.

## Artifacts

EXT02_TWO_AIR_PLANES_VALIDATION_REPORT_V1.md
DIAGNOSTIC_PROTOCOL_V1.json
PROPOSED_DIAGNOSTIC_CONTRACT_V1.json
RUNNER_COMPATIBILITY_AUDIT_V1.json
POSTPROCESS_DEPENDENCY_PREFLIGHT_V1.json
CONTINUATION.md
ARTIFACT_HASHES_V1.json

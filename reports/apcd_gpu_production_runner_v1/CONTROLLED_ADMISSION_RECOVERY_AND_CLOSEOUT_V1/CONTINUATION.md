# Continuation — controlled EXT02 setup ready, no solver execution

Last verified: 2026-10-04. Remote access works over NetBird SSH to `DESKTOP-NNE313K` as `desktop-nne313k\dell`.

## State

- Route: `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`.
- Only admission: `K6V1_EXT02 / attempt_001`, with exact overlay `EXT02_POSTNP_DIAG_Z2000`.
- Final adapter SHA256: `b7a1d074b3ab776cb1d192868192ad3a300a5192af3c439b35bfa6f0dea6d106`.
- Final Runner SHA256: `c97f459ffb3434d1a9419d8f203de2ca34630748c92626ff3d967edcfbd4f6aa`.
- Final formal setup preflight V2: PASS, report SHA256 `916b6e46c26e26346043bad43efc70413c07a7917dd4c3535654f143405f3a7e`.
- Source/staged FSP SHA256: `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`.
- Contract SHA256: `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`.
- Source manifest SHA256: `77107310820f44f19aff32baa8bc2db5170775187025fa95cee76ef2ba6d7ffb`.
- Setup LOAD proof SHA256: `2e97596b983df1b11d3d0a06309df41cabff6c7076917a30ebf446459f3ce386`.
- Solver entry/run/replay counts for this closeout: `0 / 0 / 0`. EXT02 budget remains exactly one future entry and zero automatic replays.
- No other K6 geometry is authorized. Do not add local 16-point or 128+32-point sets.

## Required before the one future entry

1. Reconnect over NetBird and verify `hostname`, `whoami`, Runner branch/HEAD/upstream and worktree status.
2. Recheck the exact route policy/authority hashes, case and attempt, physical contract, setup fingerprint, source manifest, source/staged FSP and LOAD-proof hashes. Confirm no prior EXT02 entry and no changed staged file.
3. Create a new immutable run envelope with a unique `run_id`, exact `K6V1_EXT02 / attempt_001`, same controlled route and `preflight_only=false`. Do not use `formal_preflight_envelope.json` as the run envelope.
4. Run the final `preflight-setup` again against the exact run envelope assets if any hash or file changed. Immediately before entry, the Runner must pass the live 1369 MiB GPU quota check and owner/fencing checks. A pre-entry failure consumes no solver entry; do not broaden the change or start another case.
5. Invoke only the existing `adapter.py run-one <new-immutable-run-envelope>` once. Automatic replay is forbidden. Stop after any post-entry failure or lineage ambiguity.
6. Require full GPU engine/process lineage, durable `run.fsp` and sibling `run/run_output.h5`, fresh LOAD, `SCIENTIFIC_VALID`, and `RELEASED`. Verify sidecar has at least five complete monitor groups and the additional monitor's six field datasets.
7. After completion, use `extract_controlled_monitor_load_only_v1.py --run-dir <immutable-run-directory>`. It creates the diagnostic NPZ/JSON beneath `monitor_extraction` and does no solve. Missing monitor/H5 data or schema mismatch is a terminal extraction failure, never a reason to replay.
8. Compare the actual `MON_POSTNP` and `EXT02_POSTNP_DIAG_Z2000` results after verifying actual sampled z, coordinates/local mesh and PML inner face. De-embed both to reference z=1722 nm using the frozen Coupling protocol; no global-phase oracle alignment. Do not claim dual-plane validation until this comparison passes.

## Current verified geometry/readback

Configured diagnostic z=2000 nm; x/y spans 1740×290 nm; six E/H components; 21 points 440–460 nm; nearest mesh cell; downsample 1. Actual monitor sampled z is unavailable before solving. API setup readback gives NP z=1212…1712 nm (height 500 nm), so configured plane is 288 nm above the NP top and 10 nm above the 1722 nm reference plane. The NP 5 nm mesh region is z=1112…1812 nm; actual field mesh at z=2000 is pending. FDTD boundaries are −600/3000 nm with eight PML layers; actual PML inner face is pending.

## Extraction evidence boundary

The real existing S39 archive probe verified generic H5-to-monitor matching for `MON_POSTNP` (`Monitor2`, actual z 1802 nm, 21 wavelengths, six components, field shape `(349,59,1,21,3)`). It does not prove EXT02 second-plane persistence or extraction. The new reader requires `run.fsp`, `run/run_output.h5`, `truth.h5`, manifest/status/validation/hashes/setup-validation/pre-entry proof, logs, process lineage and runtime timeline. It validates `DONE`, exactly one entry, fresh LOAD, `SCIENTIFIC_VALID`, hashes and GPU lineage, then loads only the exact named monitor.

See `FINAL_CLOSEOUT_REPORT_V1.md` for full hashes and test results. See `../../../docs/APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.md` for the production route details.

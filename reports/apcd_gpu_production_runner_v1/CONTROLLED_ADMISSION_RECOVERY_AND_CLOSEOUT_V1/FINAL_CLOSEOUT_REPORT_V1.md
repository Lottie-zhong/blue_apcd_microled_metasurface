# APCD GPU Runner V1 controlled-admission recovery closeout

Date: 2026-10-04

## Status

`READY_FOR_ONE_AUTHORIZED_EXT02_ENTRY` — limited to `K6V1_EXT02 / attempt_001` and the single declared overlay monitor. This is setup-admission readiness, not scientific validation or K6-wide authorization.

## Remote connectivity

NetBird peer `desktop-nne313k.netbird.cloud` (`100.81.105.58`) was connected; SSH public-key authentication succeeded. Remote identity: `DESKTOP-NNE313K`, `desktop-nne313k\dell`.

## Final route and start-time revalidation

- Route: `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`.
- Adapter SHA256: `b7a1d074b3ab776cb1d192868192ad3a300a5192af3c439b35bfa6f0dea6d106`.
- Runner core SHA256: `c97f459ffb3434d1a9419d8f203de2ca34630748c92626ff3d967edcfbd4f6aa`.
- Policy SHA256: `e26c2f1e5b13743da455277f4562ccf2a6262567e4dabf1a2fae06735d624f5f`.
- Authority SHA256: `e6043ff7bec4711d16d326ca3d8305b9693647250349dea11b59b57e0cd2d1ec`.
- Controlled source SHA256: `56dc7913f450ee76b50a5b6f474e53c3061cf6335dfd1215c1df386b0cdf6c03`.
- The final callback re-reads the route envelope, case authority, contract, source manifest, staged FSP and setup LOAD proof after setup LOAD, rechecks GPU quota, and is bracketed by Runner owner/fencing checks before entry. The run's content fingerprint is recorded with durable `pre_entry_revalidation.json`; mismatch fails pre-entry. The fingerprint is content-addressed, not a shared controller's monotonic generation number.
- For the EXT02 overlay, the adapter persists the additional declared field monitor through the pinned launcher builder and waits for a stable, fsynced H5 sidecar with at least five complete monitor groups. The standard raw export and pinned backend were not replaced.

## Legacy 12-case compatibility

The existing 12-case setup-validation path remains unchanged. The final synthetic regression suite verifies those IDs stay on the legacy route and are rejected by controlled admission. Previously recorded real Stage-1 preflight evidence remains 12/12 PASS; the 12 FSPs were not reloaded in this recovery closeout.

## Real EXT02 setup and final preflight

The final actual `preflight-setup` used Lumerical 2025 R1. Result `PASS`; solver invocations and scientific entries both zero; existing monitor parity 0 mismatches; source/staged semantic parity 0 mismatches; proof/fresh-LOAD semantic parity 0 mismatches. The route is authorized only for `K6V1_EXT02 / attempt_001`; all new K6 geometry authority remains empty.

| Input/artifact | SHA256 |
|---|---|
| Physical contract | `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68` |
| Source FSP | `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30` |
| Staged FSP | `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30` |
| Source manifest | `77107310820f44f19aff32baa8bc2db5170775187025fa95cee76ef2ba6d7ffb` |
| Setup LOAD-only proof | `2e97596b983df1b11d3d0a06309df41cabff6c7076917a30ebf446459f3ce386` |
| Setup fingerprint | `95c40a99da6ca199e297496a638f051a4f1d1547c2d25b86455a2c4bf3afbea2` |
| Final preflight JSON V2 | `916b6e46c26e26346043bad43efc70413c07a7917dd4c3535654f143405f3a7e` |

Readback of `EXT02_POSTNP_DIAG_Z2000`: z=2000 nm configured; 1740×290 nm span; E/H six components; 21 wavelengths 440–460 nm; nearest mesh cell; downsample 1; reference plane 1722 nm. Existing four monitors remain. `NP_D1…NP_D6` are circles spanning z=1212…1712 nm; the new plane is 288 nm above the NP top and 10 nm above the reference plane. The NP-derived 5 nm mesh region is z=1112…1812 nm, so this diagnostic plane is outside it. FDTD z boundaries are −600 and 3000 nm, with eight PML layers; actual PML inner face, generated mesh coordinates and actual monitor sampling z await a solver result.

The setup LOAD proof establishes loadability and declared setup readback only. It does not establish post-solver truth.

## Second-plane extraction readiness

New file: `scripts/shared_fdtd/gpu_runner_v1/extract_controlled_monitor_load_only_v1.py` (SHA256 `3ca4720000ce16851cbe889b0297a1595a817b9d1395d2974f0044dc6b901c52`). It accepts `--run-dir` for the immutable completed EXT02 run. Required artifacts include `run.fsp`, `run/run_output.h5`, `truth.h5`, manifest/status/validation/hashes/setup-validation/pre-entry proof, solver stdout/log, process-exit provenance and runtime timeline. The reader requires one entered solver, `DONE`, fresh LOAD and `SCIENTIFIC_VALID`, consistent hashes, and GPU engine lineage; it extracts E/H by the exact diagnostic monitor name and matches the monitor group to actual coordinates in H5. Failure is terminal for extraction and never triggers solver replay.

Generic real-file check on an existing S39 archive passed: `MON_POSTNP` matched H5 group `Monitor2`, actual z 1802 nm, 21 wavelengths, shape `(349,59,1,21,3)`, six components. Probe report SHA256 `3a8ea1742de06b0d100f508bd40cb9084f45a7fe8cc004bc095f3987ca5af92b`. This is not an EXT02 second-plane result. EXT02 persistence and extraction against the actual added monitor await its one future entry.

## Tests and counts

Final remote run: **68 passed, 38 subtests passed** (synthetic/offline). Actual EXT02 setup LOAD/preflight: PASS. Existing S39 FSP/H5 extraction probe: PASS. Solver entry: **0**; FDTD run: **0**; post-entry replay: **0**. No physical contract, monitor authority, mesh, or standard export was changed beyond the declared added monitor persistence route.

## Unresolved items

- No EXT02 solver truth or dual-plane numerical comparison exists yet.
- Actual sampled z, local field mesh coordinates/spacing and PML inner face remain post-run readbacks.
- The final setup preflight does not reserve a GPU slot or prove live quota; the start callback enforces the live quota and owner/fence checks immediately before a future entry.
- Eight pre-existing hidden `fdtd-solutions.exe -server -hide` processes were observed (creation timestamps on 2026-09-28); no `fdtd-engine-msmpi.exe` process was present. They were left untouched because this closeout could not establish ownership or a safe termination request. No solver was started by this task.

## Next — do not execute

Recheck exact authority/hashes, zero prior EXT02 entry, owner/fence and live GPU quota; create a new immutable run envelope with a unique run ID (do not reuse the setup-preflight envelope); invoke the existing Runner once with automatic replay disabled. Require complete GPU lineage, durable FSP/H5, fresh LOAD, `SCIENTIFIC_VALID`, then `RELEASED`. Only then run the extraction CLI on that archived run directory and perform the frozen same-reference-plane comparison without a phase oracle. Any post-entry ambiguity or missing truth stops the attempt; do not replay.

# APCD GPU Runner controlled case admission design V1

## Decision

Use two explicit case classes behind a future versioned admission route. Keep the production V1 adapter, runner core, authority file, and current `run-one` path frozen. The new reference validator in `scripts/shared_fdtd/gpu_runner_v1/design_only/` is offline-only and is not imported by production dispatch. It makes the permitted diffs executable and reviewable without admitting EXT02 or any new dataset case today.

The fixed 12 IDs remain on their original authority and validator. The frozen Runner handoff records all 12 Stage-1 setup LOAD-only checks as PASS, and the offline compatibility test asserts the same ordered ID list plus unchanged adapter/runner hashes. This turn did not reopen their FSPs or invoke Lumerical.

## Controlled change classes

| Case class | Only scientific change allowed | Must stay identical | Contract hash rule |
| --- | --- | --- | --- |
| `K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1` | Ordered `D1…D6` geometry vector | Materials, source/polarization, wavelengths, boundaries, stack, monitor set, references/de-embedding, mesh implementation, stopping rule, launcher, persistence and truth validation | Byte and semantic physical-contract hashes equal the approved production contract. Each case still gets a new resolved setup fingerprint, authority/source manifest, setup LOAD proof and source/staged FSP hashes. |
| `EXT02_DECLARED_EH_MONITOR_DIAGNOSTIC_V1` | Append exactly `EXT02_POSTNP_DIAG_Z2000` | EXT02 geometry, all existing contract values and all existing monitors | Materialized diagnostic contract gets its own byte hash and semantic fingerprint; both differ from the old production contract. The proposal hash is metadata only and cannot stand in for the actual hash. |

For a K6 geometry case, the six values must be finite, positive and ordered. Eligibility comes from an owner-controlled geometry authority that names the exact case ID and vector. Do not infer authorization from a numeric range or geometry hash. If the pinned expansion file does not list a new vector, an explicitly approved source authority must bind the replacement/extension by exact SHA256 before dispatch.

The diagnostic monitor is a 2D Z-normal frequency-domain monitor at nominal `z=2000 nm`, spanning `1740 × 290 nm`, with `Ex/Ey/Ez/Hx/Hy/Hz` and 21 wavelengths from 440–460 nm in 1 nm steps. It copies the existing POSTNP interpolation, downsampling and coordinate policy. The actual sampled z and local mesh spacing are unknown until the actual setup/result is read back; record those measured values later and do not label the nominal z as the measured sample plane.

The diagnostic may not change geometry, material, source, polarization, wavelength, boundary, mesh, stopping rule, normalization, reference plane, existing monitor, or postprocessing settings. The historical 2 nm seed FSP is not a 5 nm authority.

## Per-setup provenance and first admission

Every new case has its own immutable `authority_root/case_id/attempt_id` directory and a versioned source manifest binding:

1. The resolved setup contract and its byte hash.
2. The actual physical-contract file and both its byte-level SHA256 and canonical semantic fingerprint.
3. The exact source FSP and staged FSP, with matching byte hashes.
4. The case-specific geometry/diagnostic source authority and its hash.
5. The pre-entry setup LOAD-only proof and its hash.
6. A resolved setup fingerprint computed from case class, case/attempt identity, ordered geometry, physical-contract byte hash and semantic fingerprint.

The versioned dispatch envelope must bind the source-manifest SHA and resolve the case authority against the owner-controlled authority root. Case-local paths must stay under that case/attempt directory. Only pinned source-authority files may be referenced outside it. Reject missing files, path traversal, symlinks, duplicate JSON keys, unexpected fields, source/staged hash mismatch, contract mismatch and stale fingerprints.

For a first run, generate the case-specific setup and manifest, stage the exact FSP, run LOAD-only validation on that exact staged file, persist full setup readback with `solver_run_called=false` and `scientific_entry_count=0`, then validate the immutable envelope. This is the new case's pre-entry setup proof. It does not require a historical post-entry truth recovery artifact, because the case has not run yet.

After its single solver entry, the existing post-entry chain remains separate and mandatory: GPU process lineage, durable FSP/H5, fresh LOAD truth recovery, `SCIENTIFIC_VALID`, completion barrier, truth-before-DONE, and only then `RELEASED`. Any post-entry failure remains non-replayable.

## Compatibility and implementation boundary

Production `adapter.py`, `runner.py`, the 12-case authority, pinned contract, GPU slot policy, and current execution state machine are not modified. The proposal is an isolated reference policy/prototype. A future implementation must route the two case classes through an explicitly versioned admission envelope while retaining the old 12-case path exactly; it must not broaden `run-one` by weakening existing path/hash/provenance validation.

The offline validator checks synthetic JSON and synthetic byte strings only. It cannot prove an actual new FSP, Lumerical LOAD readback, actual mesh sampling, GPU lineage, or scientific truth. EXT02 remains unadmitted until its 5 nm setup, source authority, actual contract fingerprint and pre-entry LOAD proof exist under the new per-case route.

## Next real validation

After the versioned route has been integrated and a real EXT02 5 nm setup pack has been created and LOAD-validated, the next scientific validation is exactly `case_id=K6V1_EXT02`, `attempt_id=attempt_001` in the new controlled authority root, with **one solver entry maximum and zero automatic replays**. Keep this route separate from the historical seed-DB `attempt_001`. Validate the added monitor's actual sampled z and local mesh from the materialized output. Do not start this case as part of the present design task.

No K6 new-geometry case should precede exact geometry-source enrollment. Its future solver budget is one entered run per explicitly enrolled case, with no post-entry retry.

## Continuation

Read this file, `CONTROLLED_CASE_ADMISSION_POLICY_V1.json`, `OFFLINE_VALIDATION_REPORT_V1.json`, and `CONTINUATION.md` before resuming. Current result: design and synthetic offline checks only; solver entries `0`, FDTD runs `0`. Production admission remains the original 12-case route. Preserve the Coupling worktree's pre-existing untracked files and do not launch EXT02 or any new K6 case from this continuation.

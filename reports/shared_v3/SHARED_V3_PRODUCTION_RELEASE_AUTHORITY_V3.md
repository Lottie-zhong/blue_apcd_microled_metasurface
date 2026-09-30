# Shared V3 production release authority (prospective)

Status: PROSPECTIVE - fresh pre-release gates PASS for review and conditional authorization of S35/S39 attempt_001 only. Authority review/commit/push and the official hold-release event are still pending; the production hold remains ON. This draft does not release it.

## Scope and authorization

Initial scope: K6V1_S35 and K6V1_S39, attempt_001 only. Candidate target count is 2; full Stage 1 authority gate remains 12. Do not dispatch attempt_002 or the other ten cases until both initial cases are GPU-confirmed. No physics or contract changes are authorized.

The V3 task text defines no separate external Chart approval artifact. This authority cites the user instruction in this Codex task to complete Shared V3 readiness and conditionally release only after all V3 gates pass.

## Gate status

| Gate | Evidence | Status / condition |
|---|---|---|
| Backend and candidate provenance | Backend commit 01e2320; pinned manifests and candidate bundle below | PASS; candidate not activated |
| Restart fail-safe / no replay | Separate adjudication addendum plus preserved original FAIL | PASS for V3 fail-safe criterion; caveat recorded |
| Slots, leases, reservations, health | 3/3 slots free, active leases/reservations 0, health PASS at generation 23; DB SHA stable through 12:17 UTC | PASS at capture; refresh before release |
| GPU capacity | RTX 3080 free 7642 MiB at 1% utilization; threshold 1369 MiB | PASS at 12:17 UTC; WDDM per-process memory N/A; refresh before each launch |
| S35/S39 entry count | attempt_001 entry count 0 each at DB SHA 253e0811...d02fcc | PASS; recheck before release |
| Physical source chain | Contract/geometry/manifest/pre-FSP hashes linked; formal validate_config passed on both payloads with validation-only lease sentinels | PASS for config validation; refresh live lease/resource checks before production entry |
| Legacy hold API | Isolated SQLite backup set_hold then release_hold qualification | PASS on copy only; production not changed |
| Authority commit, production release, dispatch | Not performed | PENDING; no production action yet |

## Pinned provenance

- Reliability branch codex/shared-v3-gpu-reliability-v1, HEAD 01e2320ebf237bdbcd52573665520d57705d2800, upstream delta 0/0.
- Backend commit 01e2320ebf237bdbcd52573665520d57705d2800; manifest SHA-256 88161d48340f14c6bfb07ee98c8cf46e1cff82ce1e0ffe381be82d39c885a5a2 (91 pinned source files). Reconciler service SHA-256 2a023e7d36ffcfc2a554f1091c32c869b48f5be6f948de6e2d4619bb2b7e1549; implementation SHA-256 27c9c66eb58b24bdae48327e27a2b3e44ae2ad8da21671c1e3feade287998126.
- Candidate controller SHA-256 e4cd8429b81a838933edefb147ccf5d0b907013fd581fb9a2f5b68aa1bb04e99; inventory SHA-256 b8d64a602ff5014ed90806575abe4b5195de4b8e3714d6ddea267b286fa259db; source manifest SHA-256 aacb3f8429c8953c878631bb74a078babbc4e540284a805e1a79513dff6eacc5.
- Expansion manifest SHA-256 4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f; frozen physical contract SHA-256 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.
- Seed manifest raw SHA-256 463ceaece52121b1a968d22881944c082a26041c16b4489c25b6a0b8f44db62b; normalized SHA-256 4a85eeda07e18a5ee098183b1303d8a2e6f1ed08a8dfc4cb72687b00ebe998ee.
- gpu_bundle.py source/blob SHA-256 2712e3c221a742af32db43b6c899fe79369e961fee2c4a3e8739950fbaa72d9f. This is a source-code hash, not a native FSP/H5 truth-artifact hash.
- S35 geometry bd6fb9a41c003910eeda456315bafb1962dd4335d1ec64ec055322e2f4a19276; pre-FSP dc1abfd755d443ed16fe0a6c0771f8aa3ce2700a3c999bb0cd77a7caa799378a (522322 bytes, declared/actual match).
- S39 geometry 7c582e2c53da5394d6cdf446a1ee9e16a970264b1fc78312d3f304df52403729; pre-FSP 5e7beeeaa5d87b11f687efd279b10cdcf5eb054bea6c8ace9863f660f9c476c2 (522322 bytes, declared/actual match).

## Fail-safe, truth, and capacity policy

Original retry1 report remains FAIL, SHA-256 4193e04476a20697bc77987bb6c3f221784c027a6b5fcce1c3a0de7599d130ad, because expected_dispatch_calls=4 was invalid for RUNNING to POSTENTRY_NO_TRUTH. Separate adjudication addendum is PASS for the V3 fail-safe criterion only, SHA-256 4c350923074010283b2fe2891a5dfce0d630550e5d85207e9e9f4129f3b0a6b2. It records two controller starts, entry/claim/acquire/release counts of 1, zero real solver, no replay/new attempt, POSTENTRY_NO_TRUTH terminalization, and no slot/reservation leak.

Entry is non-replayable. Truth must validate before success and release. V3 defers automatic post-entry truth recovery; missing truth is quarantined as POSTENTRY_NO_TRUTH or POSTENTRY_RECOVERY_REQUIRED, never repaired by a second solver launch.

Each real launch requires a durable GPU snapshot before claim/start. Minimum free headroom is 1369 MiB, the ceiling of validated observed 1.336057 GiB peak. Historical 9246 MiB is a baseline, not threshold. Missing/low capacity yields WAIT_EXTERNAL_GPU_CAPACITY, zero entry, and no global hold. Record utilization, used/free memory, visible processes, Shared V3 owners, external consumers, and resolved physical identity.

## Hold lifecycle and release procedure

Production has a legacy boolean global hold at generation 23 but no hold_lifecycle/hold_events record; original hold provenance is incomplete and will not be reconstructed. Isolated API qualification report SHA-256 23fe41c50505455f899b8842e0335999bd4d130eb87e75238adf0b319a7ac4f5 proved versioned ControlDB.set_hold(GLOBAL) then release_hold(authority_hash,evidence) creates one linked HOLD_RELEASED event, preserves health/caps, and transitions generation 23 to 24 to 25. Production main DB SHA-256 was 253e0811178f93163178f420e5a16e8da5e4c52d434be4bff317a21809d02fcc before and after; no production API was called.

Only after review, authority commit/push, and fresh PASS gates: call versioned set_hold to create a prospective lifecycle row while disclosing legacy origin is unknown, then release_hold with the committed authority JSON SHA and evidence. Record hold ID, event ID, authority hash, generation and caps; verify health PASS and hold false before dispatch.

## Historical incident disposition

- Six historical POSTENTRY_NO_TRUTH rows: preserve, no replay; current snapshot shows no active owner/resource conflict.
- Traditional queue21: LINEAGE_NOT_RECOVERABLE due two same-token/fence entry events with empty metadata and no PID/launch identity. Preserve and do not replay; forensic SHA-256 12cff822935ca852daeebb3b06073fbbeedb9a5fbc2d39ab67e04a617b2375eb.
- Controller path-binding incident: preserve report and state; do not rewrite DB/cache; report SHA-256 ee4f40c3e0c0f116fbb6d431eae4cb77294f80dd35d483564cc722cf7556b878.
- A3 canary has both success and later failure markers. Preserve both. Durable post-FSP/load/validation/archive evidence exists, but contradiction means it is not clean release proof and is absent from current production queue/event state.
- A4 infrastructure exception canary PASS, audit SHA-256 ef2ee30e5a48e0cc79f7046040cf64ae0ac03e60644c6244c937aa18c134dbd0; it is not evidence of S35/S39 GPU FDTD completion.

## Required fresh check before dispatch

Recheck production hold/generation/health/caps, slots, leases, reservations, owners/processes, S35/S39 attempt_001 entry count zero, physical contract and FSP hashes, candidate/backend hashes, scheduled task actions, GPU headroom at least 1369 MiB, and current official pre-entry validator. If any gate fails, keep hold and do not dispatch. If all gates pass and this authority is committed, use official lifecycle APIs and dispatch only S35/S39 attempt_001. No other case or retry is authorized.


## Explicit readiness claims and current preflight

- SAFE_FOR_TRADITIONAL_PRODUCTION: YES for readiness to authorize only the bounded S35/S39 attempt_001 rollout; the Traditional cap remains disabled. This does not certify general Traditional throughput or completed GPU results.
- SAFE_FOR_COUPLING_ML_PRODUCTION: YES for the controlled initial S35/S39 attempt_001 release only; this does not claim GPU results, native truth artifacts, or all 12 cases are complete.
- GLOBAL_NEW_ENTRY_HOLD_RELEASE_RECOMMENDED: YES conditionally after this authority is reviewed and committed/pushed; use the official lifecycle API only. No release has occurred.

The candidate patch is pinned at SHA-256 49ba825e3474a86326252c4d8c9b83a5bf8aefa54c09be73e995b0736f07e24c. The complete 91-file runtime manifest is embedded in the JSON under provenance.backend.runtime_manifest_complete and pinned by SHA-256 88161d48340f14c6bfb07ee98c8cf46e1cff82ce1e0ffe381be82d39c885a5a2.

The versioned official pw_scientific_launcher.validate_config function passed on the exact S35 and S39 queue payloads; report SHA-256 fce0e3af2429187ca3527091b1c241c62a75bfa130b0fe8ec72e7e8ae1dec712. Since no production lease exists under the hold, slot/token/fence were validation-only sentinels. This is config-contract validation, not a live resource or lease admission check. It ran without host startup, lumapi, FDTD load or solver invocation.

Fresh snapshot at 2026-09-30 12:17 UTC: RTX 3080 utilization 1%, 2412 MiB used, 7642 MiB free; 1369 MiB minimum. Two AEDT GUI PIDs were present, and WDDM reported `[N/A]` for all per-process memory rows. Eight FDTD `-server -hide` LumAPI daemons had no project args or solver children; PID 8448 is an Ansys licensing client. PID 8168 is a live SYSTEM `smpd-intel` MPI runtime daemon with no children, zero CPU delta over two seconds, and no active solver link observed; it remains running and is disclosed. Two `python.exe -` helper identities cannot be recovered from command line, though they had no project args or solver children. The process-tree addendum SHA-256 is 728154036682b97a4dd0d89f78ecac4fd47f715cd675210165233d9ebc270ed4. Refresh this volatile snapshot before release and every actual launch.

Current S35/S39 attempt_001 each have entry count zero and no native/post FSP or H5 truth artifact. That absence is expected because neither attempt entered the scientific solver. The gpu_bundle.py value above is a source-code hash, not a native truth-artifact hash.

The isolated official hold API qualification report is embedded under hold_lifecycle.isolated_qualification.report_json and pinned by SHA-256 23fe41c50505455f899b8842e0335999bd4d130eb87e75238adf0b319a7ac4f5. The A3 canary contradiction, A4 exception canary, historical queue21 lineage and controller path-binding incident remain explicitly listed in the JSON; no contradictory or historical artifact is deleted or overwritten.

## Final fresh readiness adjudication (2026-09-30 12:24 UTC)

Pre-release operational gates pass for authority review and conditional release of S35/S39 attempt_001 only. These are separate capture times: primary production preflight at 2026-09-30T12:10:16.986959Z; PID 8168 classification at 12:13:44.470795Z-12:13:48.630860Z; process-tree, DB, and GPU snapshot at 12:16:59.714025Z-12:17:08.168390Z; consolidated gate adjudication at 2026-09-30T12:24:11.306091Z. The primary fresh gate JSON SHA-256 is 861f436bf266d5aec91521be8070b78e31991a693a693dc5a20d388e3b5b4d64; MPI process classification SHA-256 is bb3a9fe905c4357381354fc46d968d51e0854298e791337b2723779eaf5d790e; process-tree snapshot SHA-256 is 728154036682b97a4dd0d89f78ecac4fd47f715cd675210165233d9ebc270ed4; consolidated gate adjudication SHA-256 is 8e73140f72dfa2cb17f5e6a83058ff9bb4abcb1e80ae78f3c670110c61097044. Production DB remained SHA-256 253e0811178f93163178f420e5a16e8da5e4c52d434be4bff317a21809d02fcc, hold=ON, generation=23, health=PASS, three slots free, active leases/reservations=0. Both target attempts remain WAIT_RESOURCE_CAPACITY with entry count zero.

The original process predicate matched only the exact name `smpd.exe` and omitted `smpd-intel-4.0.3.009-x64.exe`; its literal zero-MPI result is superseded by explicit process evidence, not hidden. PID 8168 is a live system MPI runtime service with no children and no observed solver link. The corrected active-owner condition passes because no FDTD engine or `mpiexec` process exists, no active lease/reservation exists, and all solver/server process trees were inspected.

These YES readiness claims authorize review/commit and then a conditional official hold release for S35/S39 attempt_001 only. They do not claim successful solver entry, native truth, completion of the two cases, or readiness of the remaining ten cases. Authority commit/push, official hold-release event, live resource admission, FDTD execution, and validated truth remain PENDING.

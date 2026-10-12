# APCD_GPU_V21_COUPLING_SCIENCE_ADAPTER_CLOSEOUT_V1

Final status: **V21_PARTIAL**. Engineering regression PASS; scientific interface closeout PARTIAL. This candidate is not installed and grants no science entry.

## Source and installation identity

GPU branch codex/apcd-gpu-v2-serial-production-v1, starting HEAD 2294f90270d5452355dd4ca282ef582b23077f49. Final committed HEAD is in DELIVERY_GIT.json (kept outside the self-referencing commit inventory).
Remote Git worktree is D:/project/worktrees/blue_apcd_gpu_v2_serial_production_v1, origin blue_apcd_microled_metasurface.git. Local delivery is an artifact copy inside a distinct local blue_plane_wave_metasurface repository, branch codex/restore-mdc-ml, HEAD 521bea90d1d4eae3a722cfa28b1ffe574584b68d. Old report/continuation/inventory copy SHAs match the remote originals. See REPOSITORY_PROVENANCE.json.
Actual production Scheduler still binds the immutable 03c0125c4a6b1e9f239a694d9052cbeb3229242a code. No V2.1 installation, release switch, Scheduler edit, time-policy change or production ACL change occurred.

## Implemented adapter boundary

One lowercase profile coupling_609d_v1 replaces batch-specific profile routing. Generic requests retain their own batch identity; diagnostic roles no longer select a hardcoded DIAG2 consumer. Science Owner module k6_v2_pipeline.generic_profile is selected only through the fixed certified API and pinned SHA.
Native preflight invokes Science Owner validate_profile_admission with exact case/attempt/role/geometry/physics/source and manifest/admission/certification bindings before Coupling entry receipts. GeneralBudget revalidates it; missing or conflicting returns refuse. Nested unresolved physics contracts refuse before entry when they lack frozen postprocessor inputs.
Native run manifest now binds the original accepted source manifest path/SHA, batch/profile/role/geometry, scientific contract identity and all three authorization SHAs. Scientific label acceptance is verified by the GPU, preserved in native validation, and rechecked before external terminal publication. This does not alter any C_hat/P_scale/reference-plane/Floquet/TE/TM/H1/H2 formulas.
Scientific identity SHA and raw contract-file Pin SHA are independent. Signed source acceptance must bind both, plus role and original source-manifest SHA. The GPU does not invent a canonical science hash algorithm.

## Authority, budgets and permissions

Coupling remains the only science budget authority. Candidate external ledger APCD_COUPLING_BATCH_ENTRY_LEDGER_V1 uses authorized_entry_budget and exact case sets; diagnostic entries are not relabeled development. No existing DOE56/128 ledger is migrated, cloned, reset or enlarged.
Conservative durable ordering remains entry receipt -> Coupling entered ledger -> V2 mirror -> launch-request receipt -> process. Any partial transaction or uncertain entry blocks other batches; no replay/refund. Existing native recovery performs LOAD-only under returned-process/PID creation-time proof.
Science Owner ACL and delete-child checks cover the external science ledger and its parent chain as well as manifests/admissions/certifications/control/LOAD proofs. Direct Registry API submit/operate/drain enforce operator identity, not merely CLI guards. A consumer cannot lift science HOLD or modify budget authority.
Actual restricted consumer fixture denied write/delete/forged admission and denied sealed read/write/list. Production roles/ACLs were not modified.

## Validation scope and three-batch evidence

Final full GPU suite after all source changes: **231 PASS / 0 SKIP**, wall 360.88s; source inventory stable. Directed generic tests cover dynamic namespace, finite budget, no replay, atomic gap recovery, cross-batch uncertainty, SHA tamper, duplicate controller/owner lock, pause versus science HOLD, no 20:00/10:00 candidate cutoff, rejected old Scheduler arguments, role/authorization binding, unsupported resolved-contract inputs and direct API permissions.
Synthetic A HOLD and independent B/C serial queue fixtures pass engineering processing and FSP/H5 fixture acceptance without changing A. Their validator test doubles are explicitly marked; they are **not** a full frozen-importer scientific positive result. No coding roundtrip or fixture receipt is reported as real science.
Independent Science Owner work supplies a parameterized copy of the frozen importer kernel and numeric/source-equivalence tests. The current independent review does not certify the complete real DIAG2 authority. The required full synthetic B/C formal importer closeout remains unproved; it is a remaining acceptance condition.

## Confirmed scientific evidence gap

DIAG2 setup FSPs and their existing native LOAD proofs still match their SHA pins. CONTRACT_DIFF verifies only 3ps -> 6ps, fixed 5nm override and 1e-6 stop threshold, all other saved setup readback sections unchanged. These setup proofs do not claim new 6ps truth or time-convergence results.
The Coupling candidate contract declares scientific SHA afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f; its own documented canonical algorithm recomputes **5220e0f869bcd718e0e1caf807c7d75519ef424c3a600d3ad2f28d454018928d**. Raw file SHA is **6d15721bb3d69342c1b24f4fae687efb10bc55c375b44624aec717c7b351524b**. It also lacks flat materials/monitors/reference/sample/stack/wavelength fields required by the current postprocessor.
No historical contract was rewritten, no old 3ps identity/output was promoted into 6ps science, and no fake hash preimage or global constant monkeypatch was used. Science Owner must issue a separately versioned, internally consistent contract/accepted source bundle and finish synthetic B/C positive importer verification before SCIENTIFIC_INTERFACE_PASS. The platform rejects incomplete production admission before entry.

## Preserved core and production

native.py, ledger.py, artifacts.py, native_readonly.py and science/postprocess.py match installed bytes exactly. PRESERVED_CORE_REVIEW_NORMALIZED.json is authoritative; the raw Git comparison report differs only because Git LF and checkout CRLF bytes differ.
DOE56 remains 4 entered / 4 truth / 4 labels / 52 unentered with numerical HOLD. Historical 128 ledger remains 128 entered / 124 truth / 124 labels. Final production marker, budget SHA, task XML and canonical execution state are checked in PRODUCTION_FINAL_V2.json.
Production Scheduler is still enabled, Ready/IgnoreNew with the old daily --plan action. Existing installed numerical-HOLD rejection evidence is reused with exact SHA; no real Scheduler trigger was executed. Candidate CLI rejects old --plan, but this is not deployment or retirement of the currently installed action. LastTaskResult=1 is preserved.

## Installation and rollback gate

INSTALL_AND_ROLLBACK_PLAN.md describes disabled immutable release publication, separately pinned Science Owner adapter, authoritative ledger preservation, canonical config migration, exact task rebind/readback and zero-solver installed-path tests. No installation approval is requested while scientific closeout is incomplete. Rollback never rewinds entry evidence/budget/truth or revives old automatic production.

## Verdict matrix

| Requirement | Result |
|---|---|
|GPU engineering regression|PASS|
|Generic queue/data-only batch registration|PASS under offline fixture|
|Independent complete science profile acceptance|PARTIAL|
|Full B/C frozen importer positive chain|NOT COMPLETED|
|ACL/ledger isolation|PASS in directed tests and restricted-account fixtures|
|Installation migration plan|PREPARED; execution not authorized|
|V21_OFFLINE_READY|NO|

Final counters this task: 0 scientific entries, 0 FDTD runs, 0 replay. DOE56 HOLD and production time policy remain unchanged. Next action is Science Owner resolution of canonical/resolved contract authority and legal synthetic importer positives, then another combined closeout. Stop at the installation gate.

Independent final review: SCIENCE_INTERFACE_PARTIAL, 5/5 directed tests PASS, Coupling HEAD b742750418d1b99dc4b5a5c1c40d51fab3eb54bc. Exact copied report/continuation/inventory and module/test pins are in SCIENCE_OWNER_REVIEW_REFERENCE.json. This independent report confirms the B/C positive-chain acceptance gap; it is not a full scientific PASS.

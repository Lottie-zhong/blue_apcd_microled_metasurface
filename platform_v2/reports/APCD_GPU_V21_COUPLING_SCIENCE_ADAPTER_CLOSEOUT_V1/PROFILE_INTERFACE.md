# coupling_609d_v1 candidate interface

The platform invokes Science Owner module `k6_v2_pipeline.generic_profile`, pinned by the profile certification/toolchain. It does not calculate or approve scientific labels.

`load_authorized_runner_case(record, *, expected_role, root, authority)` returns the existing `contracts.CaseTruth` with exact case, attempt, role and ordered geometry. `validate_authorized_labels(imported, *, authority)` returns verdict PASS, outputs 609, scientific_validated true, profile_id coupling_609d_v1, and exact physical_contract_sha256.

`validate_profile_admission(*, authority, case_id, attempt_id)` is mandatory before any conservative entry claim in PRODUCTION_GPU. It returns scientific_admission PASS, exact profile_id/case_id/attempt_id/physical_contract_sha256; absent or conflicting certification refuses before Coupling receipts. The same module is pinned and revalidated by GeneralBudget. It checks certified role/physics/source semantics without launching a solver or issuing additional budget.

Authority schema APCD_GPU_V21_PROFILE_AUTHORITY_V1 includes complete immutable manifest/admission/certification plus their raw file SHA. Caller validates owner ACL, pin integrity, exact registration/source LOAD acceptance. Science module independently verifies certified physics/source/role/registration and all frozen native truth/numeric checks. Consumer cannot select arbitrary module/functions.

No legacy case alias, global constant monkeypatch, diagnostic-specific dataset routing or GPU-side science PASS is permitted. Frozen scientific evaluation remains with Coupling; explicit no-replay authority stays in its external ledger.

Candidate external ledger schema APCD_COUPLING_BATCH_ENTRY_LEDGER_V1 uses authorized_entry_budget (not development count), batch_id, admission_sha256, no_replay true, replay_count 0, four case-ID sets/counts and case_records. The GPU adapter never creates this production authority ledger. Scientific Owner must ratify this candidate protocol before deployment.

Conservative protocol: immutable entry receipt -> external Coupling entered ledger -> V2 mirror -> immutable launch-request receipt -> process. Any interrupted step remains consumed/uncertain, blocks next entry and cannot replay. Recovery only reconciles existing receipts, never refunds or increases authorization.

Source LOAD acceptance additionally requires exact role, original source_manifest_sha256, scientific physics_contract_sha and raw physics_contract_file_sha256. Nested unresolved descriptions are not runnable postprocess contracts. Science Owner must supply an independently validated flat/resolved contract; the GPU refuses incompatible inputs before entry.


## Final science interface closure
science_owner_id is the logical Owner identity; science_owner_sid is solely ACL identity. Case and GeneralRequest bind case_request_sha256, separate from execution hash. Manifest canonicalization is APCD_COUPLING_CASE_REQUEST_CANON_V1. Profile optionally pins postprocess_resolver_certification; truth_toolchain pins postprocess_contract_resolver. Actual preflight, monitor selection and postprocess consume exactly six Owner-resolved fields with projection SHA. Native bindings include science request, execution request, raw physics/source acceptance and native FSP/H5 SHA. Production rejects fixture/audit authority. See SCIENCE_OWNER_FINAL certificate and interface.

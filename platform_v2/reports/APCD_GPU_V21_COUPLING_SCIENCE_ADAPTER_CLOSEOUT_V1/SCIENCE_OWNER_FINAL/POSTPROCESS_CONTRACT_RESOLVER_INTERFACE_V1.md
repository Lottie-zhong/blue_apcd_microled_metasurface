# POSTPROCESS_CONTRACT_RESOLVER_INTERFACE_V1

Status: Science Owner certified, read-only resolver. This certifies interface and deterministic contract projection only. It does not certify physical truth or issue scientific entry authority.

## Owned files and pins

- Module: scripts/coupling_ml/k6_v2_pipeline/postprocess_contract_resolver.py
- Import name: k6_v2_pipeline.postprocess_contract_resolver
- Entrypoint: resolve_postprocess_contract(authority, case_id, attempt_id)
- Resolver schema: APCD_COUPLING_POSTPROCESS_CONTRACT_RESOLVER_V1
- Resolved object schema: APCD_COUPLING_RESOLVED_POSTPROCESS_CONTRACT_V1
- Certification: POSTPROCESS_CONTRACT_RESOLVER_CERTIFICATION_V1.json
- Source contract: SCIENCE_CONTRACT_6PS.json, schema APCD_COUPLING_PHYSICS_CONTRACT_V2, section parent_physical_contract_fields
- The certificate pins the resolver module, generic_profile.py, ingest.py, source-contract schema/SHA, selected section, and exact six-field list. The certificate file uses sorted, compact, ASCII JSON so its raw SHA256 equals the frozen ingest._canon digest.

## Call contract

The caller supplies the profile authority object already used by the frozen coupling_609d_v1 importer. It must add:

- resolver_certification: decoded certificate JSON
- resolver_certification_file_sha: raw SHA256 of the canonical certificate file

The caller invokes the resolver with the intended case_id and attempt_id. The resolver verifies the pinned profile authority and certification, profile admission, manifest case and attempt identity, existing case-request canonical hash, source-acceptance file, physics-contract file SHA and canonical SHA, contract schema/section, temporal-stop values, and any explicit case geometry binding. It preserves the signed source JSON value types; for example, integer 5 and floating-point 5.0 remain different case-request identities under the frozen canonicalizer.

The resolved_contract mapping contains exactly these six keys and their unchanged values from parent_physical_contract_fields:

- materials
- monitors
- references_nm
- samples_nm
- stack_layers
- wavelengths_nm

The structural checks require a valid material/monitor mapping, matching reference and sample monitor keys, valid layer/material references, and 21 ascending wavelengths. They do not rewrite scientific values or modify the frozen importer.

## Returned identity

A successful return includes the resolver verdict, profile/batch/case/attempt/role, case_request_sha256, source_acceptance_file_sha256, resolver_certification_file_sha256, physical_contract_sha256, physical_contract_file_sha256, source contract schema/section, geometry-binding result, resolved_contract_schema, resolved_contract_sha256, resolved_contract, entry_authorization=false, native_truth_validated=false, and solver_entry_count=0.

The projection digest is SHA256 of UTF-8 bytes from sorted compact ASCII JSON:

{"resolved_contract": exact six-field mapping, "schema": "APCD_COUPLING_RESOLVED_POSTPROCESS_CONTRACT_V1"}

This is the existing ingest._canon rule. The fixed vector in the certificate and unit test is c13356f4b4f51aabce9a82db23fdb503e6b6e159388ce7055da8c09e9cf1b75b. The test independently serializes the same payload and asserts the exact digest.

## GPU integration requirements

1. Pin both the resolver module SHA and resolver-certification file SHA in the GPU-owned profile configuration. Do not copy the certificate values into a consumer-issued authority or allow the consumer to self-issue the science-owner certificate.
2. Call the resolver before any scientific entry. Reject test_fixture_only, audit_only, TEST_FIXTURE_ONLY, and AUDIT_ONLY authority/source records in production.
3. Use the returned resolved_contract mapping as the same immutable input for native preflight, launch monitor names, and postprocessing. Do not use the nested source-contract envelope as the postprocessor mapping or reread its monitor names independently after validation.
4. Keep case identity, attempt identity, physical-contract file SHA, source-acceptance SHA, and resolved projection digest bound to the serial record and receipt.
5. Scientific budget, duplicate/replay prevention, batch separation, and entry authorization remain with the authoritative science-admission/ledger layer. The resolver does not issue authority, increment a budget, or write a ledger.
6. Run the GPU-owned complete regression before requesting admission-readiness revalidation.

## Boundaries and evidence

The test authorities in this packet are explicitly test-fixture-only. B/C exercises prove the offline profile and isolated-ledger interface; they are not native truth, do not establish DIAG2 6 ps validity, and do not authorize production admission. Historical parity uses read-only completed development artifacts. No sealed/confirmation response is accessed by this resolver or its tests.

No GPU release, Scheduler, Controller, Worker, production SQLite, production Science Admission, or solver was modified or invoked by the Science Owner.

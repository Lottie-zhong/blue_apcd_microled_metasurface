# Trusted Admission interface closeout

Source: `44bee753f34cb01b308dc8975a84537b8cfead35`. Initial implementation: d2613bb5d877198409281a94b53ee0864fcbf7c2.
The executable implementation is `apcd_gpu_v2/trusted_admission.py`, integrated
through `general.load_batch`, `GeneralBudget`, and the native production guard.
It is not a documentation-only signing proposal.

The existing trust boundary is installer-protected canonical Platform plus
Windows token/SID and DACL validation. No key, certificate, trust root, signer
service, allocator or second scientific budget DB was created. A production
issuer must authenticate as the configured Science Owner, be distinct from
consumer/operators, and execute the inventoried installed module. A protected
OwnerIntent pins exact manifest, ordered cases/attempts, finite budget/no-replay,
contract and source/setup/provenance, certification, and immutable release.
Plain JSON, approved=true, or a consumer-provided actor identifier is not proof.

Supported API: `require_science_owner`, `issue_and_initialize`, explicit identical
`recover=True`, and `verify_issued_admission`. The production CLI is:

```text
<formal Python> -m apcd_gpu_v2.trusted_admission check|issue|recover|verify
 --platform <canonical platform_config.json> --platform-sha256 <actual SHA>
 --manifest <protected formally enrolled manifest> --manifest-sha256 <actual SHA>
 --intent <Science Owner protected intent> --intent-sha256 <actual SHA>
```

There is no fixture option in the CLI. The isolated FixturePrincipal requires
PRODUCTION_EQUIVALENT/zero_solver roots; issued evidence is fixture_only and is
rejected by production and the old installed Admission schema.

Science Owner authority approves contract/identity/budget, GPU authority verifies
and manages execution/resource transactions, Chat separately approves start.
Issuance creates no Registry row or worker. Registration defaults PAUSED.
Activation explicitly says SCIENCE_READY_NOT_SOLVER_AUTHORIZATION.

Current actual permissions do NOT permit formal issuance: installed Science SID
and GPU operator SID are both the DELL account ending 1001; the token is an
Administrator. Authority roots have no enrolled files; profiles=[]. Candidate
policy returns SCIENCE_GPU_PRINCIPAL_SEPARATION_REQUIRED. Administrators/SYSTEM
are existing trusted OS roots, not adversaries isolated by this protocol.
No new production account or keys may be invented to make this pass.

Science Owner must independently endorse this new protocol and exact code/profile
enrollment. User must approve the exact distinct principal/DACL and existing
Coupling mutable-ledger writer capability plan, plus Disabled code deployment.
This review has not occurred in this task; no scientific PASS is self-signed.

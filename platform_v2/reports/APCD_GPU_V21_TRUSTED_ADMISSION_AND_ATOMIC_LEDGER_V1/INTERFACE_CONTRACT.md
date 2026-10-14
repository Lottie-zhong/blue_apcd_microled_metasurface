# V2.1 trusted Admission and atomic ledger interface

Status: candidate protocol, offline only. It has not been deployed, endorsed as a
production issuer by the Science Owner, or used to issue a real Admission.

## Existing authority and hard boundary

The existing installer-owned canonical `platform_config.json` defines the
Science Owner SID, consumer SID, operator SIDs, protected science/source roots,
and certified profiles. The existing `load_platform`/`verify_acl` mechanism is
the authority boundary. This adapter adds no key, certificate, signing root,
service, scheduler or scientific budget database. Its production proof is an
ACL-backed protected operation, not a cryptographic signature.

`require_science_owner` reads the Windows process token. A production issuer
must use the configured Science Owner SID, distinct from every GPU operator
and consumer SID, and must run from an inventoried immutable installed release.
The supplied Platform must equal the installer-protected canonical Platform.
Every authority artifact is read through the existing restrictive SID DACL
checks. GenericAll/GenericWrite ACEs count as write authority. Administrators
and SYSTEM remain trusted Windows roots; arbitrary administrator execution is
outside this boundary. A JSON `science_owner` or `approved=true` is never proof.

The present production configuration has Science Owner SID == operator SID,
zero enrolled profiles, and roots writable by Administrators/SYSTEM rather than
an independently provisioned Science Owner. Production issuance is therefore
refused. No account, root, ACL, installer binding or permission was created by
this task. A separate approved identity/ACL and science-ledger writer plan is
required; changing the configuration is not authorized here. In particular,
simply splitting accounts without providing the existing Coupling entry writer
the correct narrowly scoped capability would break the current JSON writer.
This deployment requirement must be reviewed with the Science Owner.

## Interfaces

`validate_batch_inputs(platform, manifest_pin, ledger_required=False)` reuses
the consumer's manifest, profile, source SHA, physical contract and certified
source-acceptance checks, without requiring a ledger that has not been created.
It does not authorize science.

`OwnerIntent` is an immutable protected Science Owner operation input. It binds:

- exact manifest file/canonical SHA, batch and ordered case set;
- one `attempt_001` per case, exact finite budget and no replay;
- profile certification SHA and installed code inventory Pin;
- scientific evidence Pins, raw/logical physics SHA via the manifest;
- distinct source-run truth, setup input, candidate setup and source-manifest
  Pins for each case, plus auxiliary source proofs;
- `scope=SCIENCE_ADMISSION_AND_LEDGER_GENESIS_ONLY` and
  `solver_entry_authorized=false`.

An intent is not a substitute for the protected actor or the Science Owner's
independent scientific approval. The informational DIAG2 final-binding report
is evidence to pin; its status alone cannot authorize this operation.

`issue_and_initialize(platform, manifest_pin, intent_pin)` authenticates the
Science token, validates every binding and current source/setup byte SHA,
requires science HOLD to be absent for that batch, and publishes the protocol
below. It never changes the V2 execution SQLite, PAUSE/start state, Scheduler,
release pointer, DOE56 control, ACL or solver process.

`issue_and_initialize(..., recover=True)` is explicit recovery of the identical
transaction. It cannot reset a ledger. Repeating an already active ordinary
issue is DENY; explicit recovery of an active transaction only returns the same
immutable identity without mutation, including after an entry was consumed.

`verify_issued_admission` verifies the complete protected commit evidence and
ledger genesis identity. `load_batch` requires it for all production V2.1
Admissions. Raw pre-V2.1 science configs are rejected by the production entry
function; LOAD-only historical recovery is not rewritten.

Production CLI (only after independent deployment/identity enrollment):

```text
<formal Python> -m apcd_gpu_v2.trusted_admission check|issue|recover|verify
  --platform <canonical platform_config.json> --platform-sha256 <file SHA>
  --manifest <protected enrolled batch manifest> --manifest-sha256 <file SHA>
  --intent <protected independently approved Science Owner intent> --intent-sha256 <file SHA>
```

The CLI has no fixture credential option. Run `check` first under the separately
authorized Science Owner token. The current installation cannot run the new
module and remains Disabled; these are generated steps, not executed commands.

## One Coupling ledger, no circular hashes

The science budget remains the existing
`APCD_COUPLING_BATCH_ENTRY_LEDGER_V1` JSON ledger. The V2 SQLite retains execution
state only. No second SQLite budget, allocator or signing service is added.

The only ledger path for a batch is
`<source_root>/<batch_id>/science_ledger.json`. A protected immutable reservation
at `<science_root>/_admissions/<batch_id>/reservation.json` binds that batch,
case/attempt set and ledger path. A global existing-style OS byte lock serializes
issuance. An already reserved case/attempt cannot obtain another batch budget.

The canonical immutable genesis includes manifest/intent/release identities,
profile, exact case/attempt and source/contract pins, finite budget, ledger path
and no-replay. It contains neither a mutable ledger-file SHA nor an Admission
SHA. The Admission contains the genesis digest; the mutable ledger contains
that genesis digest and the final Admission file SHA. The manifest contains
only the ledger's stable path. This is an acyclic binding graph:

```text
manifest + protected intent + installation identity -> genesis digest
genesis digest -> Admission file SHA
genesis digest + Admission file SHA -> mutable Coupling ledger identity
all immutable identities -> final activation record
```

## Atomic publication and recovery

Under the issuer lock, validate inputs, then publish in order:

1. immutable reservation;
2. immutable genesis;
3. immutable Admission;
4. Coupling ledger with entered=0, remaining=exact approved budget, no records;
5. revalidate inputs and publish immutable activation last.

Each JSON is written to a same-directory exclusive temporary file, flushed and
fsynced, then published by a no-overwrite atomic NTFS hard link. A partially
written temporary file is never an accepted artifact. Existing files must have
the exact canonical bytes; nothing is overwritten. The consumer checks every
commit artifact and requires the final activation. Crashes before activation
leave an inert preparation, not executable Admission. A crash after activation
leaves a complete verifiable transaction. An explicit exact-input recovery may
finish an inert preparation; conflicts or existing science records remain HOLD.

The activation status is `SCIENCE_READY_NOT_SOLVER_AUTHORIZATION`. It does not
unpause the GPU registry or enable a task. A failed SQLite registration after
this commit cannot launch; default registration is PAUSED and may be retried
with the same immutable authority. Existing submission evidence and cross-batch
uncertainty checks remain in force. No budget is returned after uncertain entry.

The existing Coupling entry receipt-before-ledger protocol, launch-once marker,
and V2 fencing enforce no replay. An active admission recovery never rewrites
entry counts. A later science HOLD still blocks new entry but does not prevent
immutable authority inspection for zero-solver truth recovery.

## Three permissions

Science Owner approves scientific identity/contract/budget and invokes issuance.
GPU Owner verifies that authority, manages the one execution slot and resource
checks, and submits PAUSED execution state. Chat/user separately authorizes
actual production start. Neither the issuer nor ledger initializer can call an
operator resume, Scheduler enable or backend. Even valid science authority is
insufficient when the live GPU/license gate is HOLD.

## Fixture isolation and DIAG2 evidence

Tests use `PRODUCTION_EQUIVALENT`, an isolated `zero_solver` root and a
`FixturePrincipal` explicitly scoped to that root. All related writable roots
must remain under it. Intent, Admission and activation carry fixture scope;
production rejects it and the CLI offers no fixture path. The old installed
Admission schema also refuses the new fixture envelope. No production-ready
credential is generated or committed.

Real DIAG2 tests pin the frozen A1/A2 manifest, unchanged 6 ps contract, exact
source/setup/candidate bytes, official certification and final-binding evidence.
Test source-acceptance/profile enrollment and the actor are explicitly isolated
fixtures. They are not new Science Owner certification, actual Admission,
6 ps truth, importer parity, or a physical numerical-convergence PASS.

## Deployment gates and shortest future operation

1. Science Owner independently reviews this interface/intent protocol and binds
   the exact candidate source/release and certified profile enrollment.
2. User authorizes a versioned deployment and an exact nonoverlapping principal,
   DACL and existing Coupling ledger-writer capability plan. Do not invent keys
   or grant permission in an engineering task.
3. Deploy Disabled, verify the installed issuer/code/profile pins, then the
   independently authorized Science Owner supplies a genuine protected intent
   for only DIAG2 and runs `check`, `issue`, `verify`; record genesis identity and
   Admission SHA. An interrupted preparation uses exact-input `recover` only.
4. GPU Owner verifies and submits PAUSED state. DOE56 remains HOLD; no budget
   transfer occurs. Separately obtain Chat's real-entry authorization and fresh
   passing GPU/global-owner/license/resource checks adjacent to fenced launch.

No step in this document is itself deployment, trust-root or solver permission.

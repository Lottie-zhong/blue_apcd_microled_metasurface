# APCD_GPU_V21_TRUSTED_ADMISSION_AND_ATOMIC_LEDGER_V1

Status: **V21_TRUSTED_ADMISSION_LEDGER_HOLD**.

Offline engineering implementation and regression: **PASS**. Production trusted
issuance: **HOLD**. No real Admission or DIAG2 science ledger was created.

## Precise root cause and available authority

The installed V2.1 release consumes Admission JSON and validates fields, SHA pins
and SID DACLs, but has no supported Science Owner issuing operation, activation
transaction or scientific-ledger initializer. Registry.submit initializes only
the local execution registration; CouplingBudget.prepare_entry consumes science
entry and cannot be used as genesis. The live science budget protocol is Coupling
JSON (`APCD_COUPLING_BATCH_ENTRY_LEDGER_V1`), not the execution SQLite schema.

Existing trust is installer-owned platform configuration plus Windows token/SID
and restrictive DACLs. No existing key, signer service or verifier endpoint was
found in the scoped installed/source interfaces. The actual read-only token is
DELL SID ending 1001 with Administrator membership. The same SID is configured
as both Science Owner and GPU operator; consumer SID 1007 is separate. Authority
roots are Administrators-owned and allow Administrators/SYSTEM write, with no
independently scoped Science Owner operation. Thus a matching account cannot
prove which role authorized an operation. Candidate policy correctly returns
`SCIENCE_GPU_PRINCIPAL_SEPARATION_REQUIRED`. Production profiles remain empty.

## Candidate minimal interfaces

- Added `trusted_admission.py`: existing ACL-backed identity verification,
  protected OwnerIntent, exact case/attempt/source/setup/profile/release binding,
  issuance, explicit recovery, verifier and production-only CLI. No keys, service,
  scheduler, allocator or second scientific budget DB were added.
- Extracted existing manifest/profile/source acceptance checks into a reusable
  pre-ledger validator. Production consumers now require complete trusted
  issuance evidence. GenericWrite/GenericAll DACL rights are correctly treated
  as write capability. Old raw production config entry paths fail before entry.
- Native FDTD invocation, physics, FSP/H5 persistence, fresh LOAD and frozen
  609D formulas were not rewritten. Two isolated legacy unit tests explicitly
  mock the new admission guard to retain their original dependency/engine-
  receipt coverage; integrated admission denial has dedicated tests.

Source commit: `d2613bb5d877198409281a94b53ee0864fcbf7c2` (normal push verified; source ahead/behind 0/0).
Key file SHA-256: trusted_admission.py `ca91d9c79a519efe1a0aba4cf8c01587dc82673544be2df6b14e014e28ceb39b`.
All source locations and hashes are in SHA_INVENTORY.json.

## Atomic ledger and permission separation

A protected immutable per-batch reservation prevents a second ledger path or
cross-batch reuse of the same case/attempt. Genesis binds manifest, exact source
and contract pins, profile, installed inventory and finite budget. It excludes
both mutable ledger SHA and Admission SHA. Admission pins genesis; the existing
Coupling ledger pins genesis plus Admission SHA. There is no cyclic SHA graph.

Reservation -> genesis -> Admission -> entered=0/remaining=2 ledger -> activation
is written under an OS issuer lock. Same-directory fsynced temporary files are
published without replacement using atomic NTFS hard links. Activation is the
only consumer-visible commit point. Earlier crashes leave inert preparation;
explicit exact-input recovery completes it or refuses a conflict. It never
overwrites records or refunds entry. Active repeat issue is DENY; active explicit
recovery returns the identical identity without mutation, including after entry.

Science issuance never registers/resumes a worker or touches the production
SQLite. GPU registration stays PAUSED. Chat's separate start authority and live
GPU/license gates remain required. A legitimate Admission cannot override HOLD.
Administrators/SYSTEM remain trusted Windows roots; arbitrary administrator or
same-user execution is not claimed to be isolated by this adapter.

## Offline evidence and complete regression

Final applicable regression: **287 PASS / 0 FAIL / 0 SKIP**.
All 15 test files were covered exactly once across three isolated pytest
partitions; wall time 169.976 s. New trusted-interface cases:
**35 PASS**. Six abrupt process-exit checkpoints passed, including
partial file write and post-activation loss of the caller. SQLite-registration
abort/retry, duplicate authority/entry, cross-batch reservation, SHA tampering,
identity denial, profile/admission absence, resource HOLD, and fixture escape
were tested. The first full run's 282 PASS / 2 FAIL is preserved in separate
logs; those two failures were old unit fixtures intercepted by the new guard.

Frozen real A1/A2 identifiers, geometry, 5 nm / 6 ps / 1e-6 contract and 16
source/setup pins passed the isolated issuance/ledger chain. The raw contract
SHA remains `51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36`;
official certification remains `11ddbf2fc13e2dd34a9a4c4b07daf17c6d2c8275a64eb27fa3202e67cad204ca`.
Actor, source-acceptance enrollment and profile carrier in this new interface
test are explicit fixtures, rejected by production and by the production CLI;
the old installed Admission schema also rejects the fixture envelope. Existing
609D adapter/importer regression is retained. No new native parity, 6 ps truth,
physical convergence or Science Owner approval is claimed by these tests.

## Production and GPU readback

Production pre/post snapshots are identical: installed code/config/binding and
DENY release SHA, relevant Scheduler XML, SQLite schema and task counts, slot,
DOE56 and historical queue ledger SHA. Authority roots still contain zero files.
Installed immutable release remains `v21_diag2_validator_b9abe87058d6`, code
inventory SHA `ea92f62348f6d32c15bb46a992d1ca370a159c7f645808a472ae4013a6a756e1`.
Scheduler entries remain Disabled; slot generation 95 has no owner/token/request;
the existing 94 V2 rows remain TRUTH_VALID. No candidate release was installed.

Resource sample at 2026-10-14T10:29:47.898439+00:00: NVIDIA GeForce RTX 3080, 610.60, 1 %, 1931 MiB, 10240 MiB.
NVIDIA lists 29 contexts, per-process memory N/A.
No scientific engine was observed; three WDDM samples showed no active non-system
engine. This does not prove global reservation or attribute the allocated GPU
memory. CURRENT_GPU_CONFLICT=UNKNOWN; LIVE_SCIENCE_ENTRY=HOLD. The composed gate
was not invoked here because it collects argv; no stdin, command line, credentials
or license-context payload was read. A fresh passing global resource/owner and
license check is required next to any future fenced launch.

## Remaining hard gates and shortest safe continuation

1. Science Owner must independently approve this proposed intent/genesis protocol,
   source/release identity and certified-profile enrollment. This task does not
   self-sign that approval.
2. User must approve a versioned Disabled deployment and exact distinct identity,
   DACL and existing Coupling ledger-writer capability plan. No new cryptographic
   trust root is proposed; if a cryptographic signer is required instead, key/root
   allocation is a separate authority decision. Do not merely split accounts and
   break the existing JSON writer or grant broad write permission.
3. After those changes, the authorized Science Owner supplies a genuine protected
   DIAG2 manifest/intent and runs `check -> issue -> verify` through the documented
   CLI, or exact-input `recover` after an interruption. GPU Owner verifies and
   submits PAUSED execution state. Neither step enables Scheduler or a solver.
4. Chat separately authorizes real entry only after fresh GPU/license/owner checks
   and current DOE56 HOLD readback. The approved two-entry budget is not increased.

DIAG2 production entered=0/2; DOE56 last formal status=4 entered / 52 HOLD.
New solver entries=0; FDTD=0; FMM/RCWA=0; ML fits=0; replay=0; sealed access=0.
Coupling worktree HEAD read back as `2cc687020e90ec4397e6cd4ed31efed59aaaf386`; it was not edited.

Read INTERFACE_CONTRACT.md, ATOMIC_LEDGER_TEST_EVIDENCE.json, the complete logs,
AUTHORITY_CAPABILITY_READBACK.json, PRODUCTION_UNCHANGED.json and SHA_INVENTORY.json.

# GPU V2 and Coupling ledger reconciliation

## Authority split

The Coupling JSON queue ledger is the only scientific budget authority. The GPU V2 SQLite ledger records execution ownership, request lifecycle, slot fencing, events, and runtime receipts. Neither ledger alone can authorize a scientific entry.

Snapshot at 2026-10-10 08:01 UTC:
- Coupling ledger SHA256: f6577d14941310dcd48f1393044da91fe98c93793d9d53224bb25e56a908a7cd
- Coupling counts: authorized=128, entered=38, truth_valid=34, labels_valid=34, unentered=90, replay=0, confirmation_response_access=0
- G027: FAILED_PREENTRY_NO_ENTRY; entry_consumed=false; no truth
- G026: FAILED_POSTENTRY_NO_TRUTH; one consumed prior entry; no replay
- GPU V2 ledger: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\ledger.sqlite3, opened read-only; tasks=0, events=0; one slot row with generation=0, token=null, owner=null, request_sha=null
- Controller task: disabled
- Release: DENY

The G027 live audit hashes the Coupling ledger before and after the read-only budget/admission checks and requires equality. Observed before and after SHA are identical. No entry receipt, reconciliation, status write, ledger migration, or controller dispatch was performed.

## Required production ordering

1. CouplingBudget.validate confirms the exact authorized case, role, geometry, attempt, remaining budget and non-entry state.
2. The immutable request binds the FSP, geometry, source manifest, contract and V2 config.
3. The release owner authorizes the exact admission digest and queue under a new immutable release.
4. V2 validate_admission checks all paths and hashes, role/geometry/queue, release, expiry and executable pin.
5. CouplingBudget.prepare_entry writes the write-ahead science entry receipt and marks entry uncertainty before backend launch.
6. The V2 SQLite ledger claims its unique case/attempt/request and fenced single slot. launch_once accepts only the matching token and receipt.
7. A single backend run may return; native FSP and the sidecar run_output.h5 must persist.
8. Fresh LOAD-only validation checks the saved project and six complex E/H components, full wavelengths/orders, provenance and SHA.
9. NativeTruthValidator emits the frozen 609-coordinate labels; Coupling import validates and records their provenance/hash.
10. Only successful validation and label ingestion can reach the Coupling truth/labels-valid terminal and permit the next request.

A failed/ambiguous post-entry attempt stays consumed. A failed importer stops after preserving the truth; it does not launch another solve. Duplicate request/case-attempt registration is refused; an already-completed duplicate is accepted only when the stored V2, Coupling phase and bundle hashes agree. Startup/recovery cannot bypass science-release validation. Any cross-ledger mismatch fails closed.

## Reconciliation and post-solver recovery

CouplingBudget.reconcile is read-only. It can compare current receipt/ledger evidence and report replay_allowed=false; it does not repair state. reconcile_entry_evidence is a controlled mutation and must use a verified request-specific receipt. The V2 recover_load_only path is also mutating: it requires proven process exit and successful solver return and then performs fresh LOAD-only validation. It must not be used to re-enter a solver.

For an uncertain or no-truth post-entry failure, preserve the evidence, record entry as consumed when proven, and stop for formal reconciliation. Do not set entry to zero, mark truth valid without a persisted native bundle, or replay. G026 remains closed under these rules.

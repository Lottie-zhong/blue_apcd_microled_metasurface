# Durable launch barrier increment

ScientificLaunchAuthority atomically commits an immutable attempt claim, unique launch_id,
conservative SCIENTIFIC_SOLVER_ENTERED and LIVE resource state before invoking external code.
The entry consumes budget prospectively; it explicitly does not assert an observed engine process.
Crashes/ambiguous launch failures never make that attempt automatically retryable.
Pre-FSP and physical-contract hashes, host PID, command hash, executable and timestamps are recorded.
The host uses this barrier for standalone GPU, PW API and legacy API calls.
An OS attempt lock rejects concurrent hosts; durable claims/entries are checked before setup writes.
Dispatcher and host resolve the shared backend from their own checkout, avoiding the old runtime host copy.
Legacy scientific adapter location is preserved separately; no scientific contract is modified.

The concurrent test exposed SQLite executescript implicitly committing owner transactions in
resource/GPU table helpers. They now execute DDL statements individually. A rollback probe verifies
the transaction survives each helper and failed state changes are rolled back.

Final verification: 24 pytest tests; 52 core, 18 capacity, 34 admission, 14 exact-permit checks;
same-launcher preentry handshake passed. Actual solver calls: zero.
An earlier transaction regression failed and is preserved in LAUNCH_ATOMIC_REGRESSION_V1.json.
One SSH reset interrupted a patch command before it was applied; file inspection detected this.
LAUNCH_TRANSACTION_REGRESSION_V1.json is the final post-fix result; V2 predates the transaction fix.

Not production ready: the process-binding API is tested but not yet connected end-to-end to
OS solver creation evidence; JSONL idempotency, metrics, hold lifecycle, incident audit,
full fault matrix, legacy task quarantine and authorized canary remain open.
The production DB and launchers have not been migrated/deployed. Global hold is unchanged.
The external scheduled-task disable request is pending; no task/process has been changed.

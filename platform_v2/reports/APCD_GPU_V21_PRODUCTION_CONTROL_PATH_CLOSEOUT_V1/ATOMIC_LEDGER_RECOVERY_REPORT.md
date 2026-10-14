# Atomic ledger / recovery closeout

The authoritative science budget remains Coupling's existing JSON protocol
APCD_COUPLING_BATCH_ENTRY_LEDGER_V1. Execution SQLite stores registration,
worker/slot state and mirrored evidence only; it cannot mint science budget.

The immutable genesis excludes Admission SHA and mutable ledger SHA. Admission
pins genesis; ledger pins genesis plus Admission SHA. The stable manifest pins
the canonical ledger path. This is an acyclic identity graph.

Under the OS issuer lock: reservation -> genesis -> Admission -> 0-entered ledger
-> final activation. Temporary JSON is flushed/fsynced and exclusively published
by NTFS hard link. Activation is the only accepted commit point. A partially
written file or incomplete preparation is inert. Ordinary duplicate issuance is
DENY; explicit exact recovery may finish preparation or return existing active
identity without mutation. It never resets consumed counts or overwrites truth.

Six real child exits tested partial temporary write, reservation, genesis,
Admission, ledger, activation. SQLite registration abort rolls back; the existing
submission receipt makes lost registration fail-closed. A later retry can only
register identical authority PAUSED. Shared batch/case reservations prevent a
second independent budget for the same attempt.

The full Controller test then injected nine runtime interruption points, including
receipt-before-ledger, science commit before local mirror, launch request,
process start/return, and truth before either ledger terminal. All retain a
conservative no-replay hold and keep A2 unentered. An actual SQLite trigger
aborted entry mirroring: the science count remained consumed while local entered
was 0; restart did not launch. No automatic refund or retry was added.

A separate actual Controller child exited after a successful harmless executable
return. Its PID/create_time and process-return receipt were recovered by a new
Controller, PAUSED. LOAD/truth ports were simulated; no executable was permitted
in recovery. A1 truth reconciled with entry still 1 and A2 still unentered; only
an explicit isolated resume allowed A2. Two Controllers were tested in separate
OS processes against the same actual byte lock; the second was rejected.

Evidence: END_TO_END_TEST_EVIDENCE.json and FULL_JUNIT.xml; preceding protocol
detail and initial fault records remain in the prior committed report directory.
These are process-crash tests, not hardware power-loss or new physics validation.

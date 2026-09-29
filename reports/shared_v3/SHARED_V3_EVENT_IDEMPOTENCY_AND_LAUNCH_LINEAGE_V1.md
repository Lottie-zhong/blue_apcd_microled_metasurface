# Entry event idempotency: first isolated increment

Allocator.mark_entered now checks owner/fence and prior entry under BEGIN IMMEDIATE.
Repeated reconciliation/worker observations preserve the first event, timestamp, version and resource state.
Late observations cannot regress RELEASE_PENDING or OWNER_QUARANTINED to LIVE.
Conflicting lease authority fails closed; historical duplicate events are retained.
New events contain a deterministic semantic key for branch/case/attempt/event.
This is observation idempotency, NOT a solver-launch permit. Unique launch lineage and launch fencing remain required before production readiness.
No SQL schema migration or unique index over historical duplicate rows was performed.

Validation: 9 focused tests (including 24 concurrent calls), 52 core checks, 18 capacity checks,
11 Coupling integration checks, 6 schema checks, 17 truth-before-release checks, and host-liveness test passed.
pytest independently reports 9 passed. Initial invocation failures and corrected reruns are retained in the JSON log.
Actual solver invocations: 0. Existing zero-solver suites use synthetic entry events only.

Outstanding: JSONL idempotency, a durable one-shot launch claim with process identity,
live duplicate metrics, auditable hold lifecycle, legacy controller quarantine,
complete persistence/incident audit, and authorized infrastructure canary.
Production readiness remains false. Do not deploy this increment alone or release the hold.

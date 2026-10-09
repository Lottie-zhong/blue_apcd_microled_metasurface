# V1 → V2 closed-gate switching transaction (NOT EXECUTED)

This is a proposed transaction for separate formal deployment approval. It modifies no Scheduler or production state in this task. P0 remains BLOCKED, so none of the apply steps is authorized by this artifact.

## Precondition and preparation

1. Resolve every UNKNOWN live process using PID+creation identity and launch ownership evidence. Obtain an owner-approved closeout for any live process that must end. Do not kill by name or delete locks. Refresh Win32/psutil/Scheduler instance/engine evidence and verify no V1 scientific owner/engine/pending request. Any unresolved identity keeps the global admission gate CLOSED.
2. Hash-pin V1 task XML/enabled states/action/principal, current request pool and receipts, registry, V1/Coupling code, frozen G027 envelope/FSP/contract, production ledger and global admission control. Prepare durable before-state receipts and a rollback plan. Do not reuse G027 old request IDs. Keep G026 and all consumed cases unclaimable.
3. Qualify the production V2 ingress and Coupling interface in shadow mode: exact case/attempt/role/request/contract/pre-FSP hashes; inherited consumed-entry budget (38 entered, not just 34 truths); label/truth counts and failed-entry tombstones; new trusted V2 entry/result/receipt schema accepted by real Coupling importer. Offline fixture records must never enter the production ledger. No physics/reference/material default may be supplied or changed by migration.

## Apply order after separate authorization

1. Establish a durable global `CLOSED_FOR_CUTOVER` admission generation before changing any external component. Record transaction ID and pinned before-state SHA. Scheduler+filesystem+SQLite cannot share one ACID transaction; safety comes from keeping the admission gate closed across every step.
2. Disable the old V1 Controller and Worker tasks, preserving their definitions and exact readback receipts. Do not unregister or delete them. Re-query RunningTask InstanceGuid/EnginePID, Enabled=false and action hash, then verify no live V1 owner. A changed action/unknown process aborts while the gate stays CLOSED.
3. Fence the V1 request generation and prevent any old request resurrection. Archive immutable pending/terminal request inventory rather than deleting history. Validate that manual old task invocation and supported old CLI paths cannot enter under the cutover fence. Because V1 does not read a new V2 gate automatically, this must be enforced at the old dispatch authority/account/runtime boundary; disabling Scheduler alone is insufficient. Do not implement this by patching V1 lifecycle or GPU parameters.
4. Provision one independently hosted V2 worker identity with absolute interpreter/code/config paths, durable stdio/event logs, PID+creation ownership and a unique SQLite fencing generation. Use a reviewed broker/service/task only after explicit deployment approval. The WMI offline fixture proves an SSH-independent staging path; plain detached Popen is unqualified. No service or task is installed here.
5. Import the shadow ledger only while CLOSED. Compare all case/attempt budget states and Coupling counts against pinned originals, commit the V2 ledger generation atomically, and publish one migration receipt. Coupling remains the scientific-label owner; V2 remains the entry/worker owner. Requests cannot independently update both ledgers as separate competing authorities.
6. Re-verify V1 launch inhibition, single V2 owner, request binding, native pair validator and read-only state query. Publish `CUTOVER_COMMITTED_CLOSED` only when every component agrees with the same transaction/fencing generation. No old actor can resume automatically. The gate does not open merely because a process or SSH session exited.

## G027 admission (requires separate scientific first-entry authorization)

Bind exactly one new admission ticket to `K6GDP2_DEV_G027 / attempt_001`, the frozen source FSP `b5c6b41d…`, contract `32e60a78…`, ordered diameters `[105,105,220,105,180,135]`, verified native resource and current qualification receipt. Revalidate inherited G027 entry=0 and all historical requests closed, complete exact-case check/license scope, and confirm no owner or global hold. Then obtain explicit scientific first-launch authorization.

Only the authorized production implementation may atomically set solver_entered=true, timestamp/pre-FSP/contract SHA and consumed budget BEFORE invoking the native interface. A crash/SSH loss/license error after that commit conservatively consumes the entry and forbids automatic replay. Do not refund based on missing results or substitute a new attempt. Persist the FSP and sibling native H5, verify/load-only extract, then let Coupling ingest the trusted receipt before any next case.

## Abort and recovery

Any mismatch leaves the admission gate CLOSED, records the failed substep and retains owner evidence. Before any entry, a separately approved rollback can restore only pinned Scheduler/dispatch definitions after proving V2 inactive. Once any entry is durably consumed, no automatic rollback, V1 restart or scientific replay is permitted. Native result recovery uses LOAD-only and original hashes. This transaction is a draft, not an implemented claim of all-or-nothing cross-system atomicity.

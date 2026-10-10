# GPU V2 automated serial queue plan

## Current scope

The Coupling ledger has 90 unentered development rows, beginning with G027 and extending through G116. G027 is the only candidate currently packaged in the installed V2 request file. G027 is not released. The controller task is disabled and the release is DENY. The 32 confirmation cases are excluded and remain sealed.

The installed V2 interface consumes a static request list. It does not expose dynamic per-case enqueue. Do not append cases to the current G027 file or mutate its release. No request or release for G028–G116 was created in this task.

## Future authorized batch pattern

After explicit authorization covers a defined batch, prepare one immutable request list and one matching owner-issued immutable science release whose request-admission pins and Coupling queue hash match that batch. Revalidate every case against the existing Coupling ledger immediately before freezing the list. Requests must retain their existing case IDs, attempt identities, geometry order, FSP/source-manifest pins, physical contract, and role. Never include confirmation, diagnostic, historical failed, or already-entered cases.

Run the existing server-owned single-slot controller over that static list. Its controller loop registers and handles cases serially; it does not proceed past a case until truth validation and Coupling label ingestion succeed. Maintain automatic_replays=0. A post-entry failure consumes that case's entry; continuation may proceed only after the formal failure receipt is verified and the controller/request list has been safely reconciled. Never skip a case lacking a legitimate terminal or reconciliation record.

The existing Task Scheduler action is bound to the installed V2 CLI, uses IgnoreNew and PT0S, and is disabled. It is an InteractiveToken task with no trigger. Enabling or starting it requires the formal owner release and explicit science authorization. PT0S is not proof of survival after user logoff, reboot, or loss of the interactive session; persistence across those events has not been established here. Do not kill a running controller or solver to test durability.

## Operational evidence at each batch

For every authorized case, preserve the request digest, admission digest, FSP and source hashes, owner release, task/controller PID and runtime log, slot claim, entry receipt, solver return code and wall time, archived FSP/H5 hashes, validation receipt, imported label hashes, Coupling ledger state, and replay counter. Verify one owner and slot before start; verify the previous case reached truth_valid and labels_valid before any next case registers.

Status reads must be read-only: Task Scheduler query, process inventory filtered by exact installed controller command, SQLite opened in mode=ro, controller logs and immutable receipts. Do not use recover_load_only or reconciliation-write APIs to query status.

The candidate next action is for Chat to decide whether to grant a one-case G027 scientific entry under the exact hashes in G027_SUBMISSION_MANIFEST.md. This handoff does not grant that authority.

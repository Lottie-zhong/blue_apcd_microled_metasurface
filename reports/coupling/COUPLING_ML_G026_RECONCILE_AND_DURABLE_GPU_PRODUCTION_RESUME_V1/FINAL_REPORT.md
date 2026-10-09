# COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1

## Status at saved checkpoint

**BLOCKED — G026 is reconciled and Runner retirement preflight passed, but the official Runner rebind API rejects the installed legacy controller Task Scheduler XML. No G027 solver entry or new truth is present.**

## Authority and current versions

- Host `DESKTOP-NNE313K`, user `desktop-nne313k\dell`.
- Coupling branch `work/mdc-np-coupling-ml-v1`, observed HEAD `877d62bddecbe38156ab544bc734be74353de9a5`, upstream 0/0; many unrelated worktree entries remain dirty/untracked and were preserved.
- Runner branch `codex/apcd-gpu-production-runner-v1`, HEAD `79b1f4081a3d9a0e9f287c14e88f0e5399c0d4a3`, clean, upstream 0/0.
- Runner handoff SHA `ab049dc6aa7ea0e98fdd348f5db59ae1836109cfb3ef61d788da5773989bfce0`; stabilization report SHA `b20b04f628f4e676af526d131b2ec544affa1b20825850909c5fd8aa4f952358`; continuation `3cf09a0640ff4ee8ebfa6587675cc5f2b113fe509eb1cf241c3bfb41530c7424`; inventory `f271865d60fae5da3c36308e5a1cfbada5f6ae2081791a3df98694cc10b72983`.

## G026 reconciliation and consumer fix

G026 `attempt_001` / `K6V2_G026_20261009T025353Z_06303b44` is formally `FAILED_POSTENTRY_NO_TRUTH`, quarantined. It consumed one entry/invocation; replay=0; physical GPU engine entry remains `UNKNOWN`. Runner request `42d15429cb67170e7a515dfe0078edeb`; controller request `bb93248ca2dff9605d7885554a319394`.

Runner closeout receipt file SHA `7eadb65dd436e1f3c431d2e22428b744f48ac6f577df92d0a820db6c94a65f72`, internal receipt SHA `92686de76bb315df53ade6471bef5bdfd6f2a90898c7f9718f1dafbc0f729196`; verification file SHA `02bfa2e031879ccabec8b5ef572ad1ae52cd373e76162fe9496056b27ca4a378`. Coupling reconciliation receipt SHA `a2ef7b77c5283e348f735b1270b64e2ae5c6f5ab020440b29fd33db5b1ec785d`, internal hash `ee761811b4d5717eb5e1e5289e1bf7be94c6708642c2956b3084a86f9e3af059`. Ledger SHA after reconciliation: `ff9f9e92904eccf76744e60c32fa143dc2a36cf900788c3c3d6be635ed5177a2`.

Root cause: Coupling's post-entry failure consumer recognized legacy case-scoped G023/G024 paths but did not accept Runner's generic, verified closeout schema, so G026 was rejected as `UNAUTHORIZED_FAILED_POSTENTRY_CASE`. The Coupling generic consumer now validates official receipt identity and hashes, verification/status/registry/envelope bindings, controller and ledger lineage, exact one-entry/zero-replay accounting, quarantine/no-truth state and single-case membership before changing terminal bookkeeping. It fails closed on mismatches and does not allow replay.

Focused regression suite: `9 passed`. Full serial queue dry-run passed with 128 frozen identities, 38 entered, 34 truth/labels-valid, 90 remaining; next is G027 / `attempt_001` / sequence 39. Dry-run entries=0, training=0, P_scale fits=0, confirmation access=0. `git diff --check` passed with existing line-ending conversion warnings.

## Successor binding and live scheduler state

Old request `bb93248ca2dff9605d7885554a319394` is `STOPPED_RECONCILED`; status SHA `2858f77335e184e595221213f019cf6fe8c7a75d4e630f31d95cc2cd7843cc14`. Historical Runner requests G025 `28c992f00bb8b032ecf06f4d8e8dc431` and G026 `42d15429cb67170e7a515dfe0078edeb` passed terminal retirement checks; G025 truth is durable, G026 quarantined.

Successor manifest `SUCCESSOR_CONTROLLER_MANIFEST_V1.json` raw SHA `bbb7f19186776ceff07f93a17fded92b036224eeaff9f95f0d1269347c58a87f`, successor ID `bbb7f19186776ceff07f93a17fded92b`, includes only G027-G116 (90 cases), one slot, max one entry/case, replay=0, truth-before-next. Pinned Coupling source SHA `93d29da19fcc5b8d5df826646683a3090f785673177ece82697be01542980947`. Queue snapshot SHA `951323df115a052933afb9bd360b1500dbc8a8a3ca6c6491f6b7dabd6d6bce4d`; retirement receipt SHA `0158543576913be51462dbce1bb61a99bbd1533a38dcfe23220a0db11fa9ae52`; owner decision SHA `1d6670211141e861a6468e19f34c3d4d0d594f9b2d4ac732fe086af342cc4991`.

Official Runner read-only preflight passed for the approved manifest delta and retirement receipt, both prior Runner requests terminal, free global slot, and no active controller/worker/solver process. The current controller task XML still points to the old request and has `PT72H`, `IgnoreNew`, `InteractiveToken`; the worker task has `PT0S`, `IgnoreNew`, `InteractiveToken`. The successor is not yet bound. The Runner API requires retire/rebind and then one `start_controller_task` for an unstarted successor; `resume_controller_task` is not valid for failed G026 or a successor without a start claim.

## Runtime and persistence boundaries

Global Runner entry control was read-only PASS, generation 27, with no active hold; slot clear. Eight Lumerical API-server processes and two unrelated AEDT processes were observed; ownership of the API servers is unknown and none were terminated. G026's license startup error remains unresolved. Scheduler identity is DELL/Interactive; PT0S removes runtime limit but does not establish logout/reboot survival. No new continuous production is yet observed.

No new training, P_scale fit, confirmation-response access, solver entry, replay, or budget expansion occurred at this saved checkpoint. Historical failed attempts remain consumed.

## Next

Commit only task-owned code/test/report files by exact allowlist. Then run Runner's official `retire_rebind_controller_task`, inspect the live task XML and binding for successor + PT0S + IgnoreNew, and call `start_controller_task` once. Verify actual G027 entry in a new SSH connection, then verify durable native H5/FSP/provenance and label ingestion before the next case. Keep the queue running and update this report, continuation, and SHA inventory with observed production evidence.


## Final formal rebind attempt — 2026-10-09 UTC

The official `retire_rebind_controller_task` API was invoked once with the verified old binding SHA, successor manifest SHA, and retirement receipt SHA. It failed closed with `CONTROLLER_REBIND_TASK_DEFINITION_MISMATCH` at Runner `task_scheduler_v1.py:1705`. Direct validation of the installed old task reports `SCHEDULER_TASK_EXECUTION_TIME_LIMIT_INVALID`: Task Scheduler reports `ExecutionTimeLimit=PT72H`, and the exported old XML omits an explicit `ExecutionTimeLimit` element (it also omits an explicit `Enabled` element). Runner's current validator defaults to requiring the new `PT0S` contract, so it refuses to recognize its own prior installed task as the old side of a rebind. The Runner delivery report documents that old task as PT72H, therefore this is a compatibility gap in the Runner rebind path, not a Coupling receipt or case-lineage mismatch.

The call created only the successor request's immutable manifest/binding under Runner request storage; it created no `start_claim.json` or successor controller status. The active task binding is unchanged and still points to old request `bb93248ca2dff9605d7885554a319394`; Task Scheduler remains Ready/LastTaskResult=2, PT72H, IgnoreNew, DELL/InteractiveToken. No controller, worker, or FDTD engine is active; the eight unowned `fdtd-solutions.exe -server -hide` API processes remain untouched. G027 remains unentered. Ledger is unchanged at 38 entered / 34 truth-valid / 34 labels-valid / 90 unentered; replay, training fits, P_scale fits, and confirmation-response access remain 0.

The failure and state snapshot are saved in `CONTROL_TRANSITION_EVIDENCE_V1.json` and `POST_REBIND_FAILURE_STATE_V1.json`; see `SHA256_INVENTORY_V1.json`. Coupling's exact-allowlist commit `135d48c8becdc8c85ff45f7916372ac865ba1167` is pushed. A Runner-owned compatibility update is required before another official rebind attempt. No manual Scheduler XML edit or validator bypass was made.

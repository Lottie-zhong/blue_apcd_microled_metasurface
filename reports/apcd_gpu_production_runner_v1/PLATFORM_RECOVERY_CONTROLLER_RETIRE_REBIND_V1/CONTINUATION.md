# CONTINUATION — Runner V1 controller retire/rebind

Current state: the Runner lifecycle API is implemented and passes offline validation. No production binding or Task Scheduler mutation occurred.

Code base at validation: branch codex/apcd-gpu-production-runner-v1, HEAD 671745718a8d70bc5076b59a2236e8a3ea8703f3.

Current queue facts:
- Production binding still pins request f0aeb35290a77db5c05c0346f1a40f81 and queue K6V2V128REMAINING20261007105811Z.
- Coupling status remains RUNNING/current G024; Runner G024 is terminal FAILED_POSTENTRY_NO_TRUTH, entry consumed once, no truth, replay 0.
- G024 closeout exists, but Coupling has not reconciled its current status/queue. No successor manifest or owner retirement receipt is present.

Sole next action, owned by Coupling: reconcile terminal G024 in the durable queue/controller ledger and publish the exact successor manifest plus a current owner-approved retirement receipt and queue snapshot bound to current hashes. Do not restart or replay G024 and do not create an attempt_002.

After those inputs are available, Runner should re-read the binding, Coupling status/ledger, process inventory, task/slot state, and hashes; validate the receipt and manifest delta; then invoke the formal versioned retire/rebind API once. Verify the transaction journal is COMPLETE, the old task is disabled, the successor task is enabled but not running, and the binding pins the successor request/manifest. Do not invoke run-one or start a case as part of controller rebind.

This implementation verification had solver entry 0, FDTD run 0, replay 0, and case launches 0.

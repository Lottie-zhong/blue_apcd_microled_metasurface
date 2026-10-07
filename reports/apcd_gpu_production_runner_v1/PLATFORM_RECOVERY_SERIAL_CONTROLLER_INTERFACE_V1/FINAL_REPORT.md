# Runner V1 serial-controller Scheduler interface

Status: PARTIAL. The Runner Scheduler contract is implemented; offline tests and an actual Windows Task Scheduler synthetic lifecycle exercise pass. The current Coupling working-tree candidate passes both Runner and Coupling manifest validators, but the supplied claimed official source SHA does not match the live working tree or committed file. No production controller task was installed or started.

## Serial rule implemented

Task Scheduler hosts the Coupling-owned bounded serial controller directly. Runner adds no second queue loop or launcher; each real scientific case still passes through the existing single-case Runner API and final launch revalidation. The controller manifest requires an ordered queue subset, a hard case count, global concurrency of one, no more than one entry per case, zero automatic replay, startup reconciliation, and truth-before-next.

A fixed durable start claim excludes duplicate starts. The task uses IgnoreNew, no triggers, no automatic restart, a 72-hour limit, and the existing DELL InteractiveToken at LeastPrivilege. A controller process loss is surfaced as NEEDS_RECONCILIATION, never automatically restarted. Resume requires a status-hash and generation-bound reconciliation receipt, no active case, zero unresolved requests, zero replay, and terminal durable Runner evidence for every prior request. Entered requests must show exactly one invocation, zero replay, DONE, fresh LOAD and scientific validation, and non-empty FSP/H5/validation/hash artifacts.

## Manifest and CLI contract

Manifest schema: APCD_GPU_RUNNER_V1_COUPLING_QUEUE_CONTROLLER_MANIFEST_V1. Required identity/evidence fields: controller_run_id, queue_id, controller_script_path plus SHA256, queue_manifest_path plus SHA256, ordered case_ids, max_cases, max_concurrent_cases=1, per_case_max_solver_entries=1, post_entry_automatic_replays=0, startup_reconcile_before_dispatch=true, truth_before_next_case=true, controller_protocol=APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_CLI_V1, and status_path.

Runner Scheduler commands:

- task_scheduler_v1.py install-controller-task <controller_manifest>
- task_scheduler_v1.py start-controller-task <request_id>
- task_scheduler_v1.py query-controller-task <request_id>
- task_scheduler_v1.py resume-controller-task <request_id> <reconciliation_receipt>

Install stages and registers only; it does not start execution. Task arguments bind the controller manifest path, SHA and request ID. Explicit resume also binds the reconciliation receipt path and SHA. The install and resume XML use the verified Windows account SID; this was exercised against the real Task Scheduler.

## Actual Windows Task Scheduler synthetic lifecycle

No FDTD, run-one, Runner case request, or solver was called. The isolated roots and evidence are under C:\Users\DELL\AppData\Local\Temp\apcd_runner_controller_lifecycle_20261007T101136Z_2beca09a and copied synthetic artifacts beside this report.

Temporary task: APCD_GPU_RUNNER_V1_SYNTHETIC_CONTROLLER_1787DAA4221C. First Scheduler start was logged at 2026-10-07 18:11:40 local. Its process PID 6968 was owned by Windows Task Scheduler service svchost.exe PID 4484. After the SSH helper returned, it emitted progress at 2026-10-07T10:11:48.557174Z and then intentionally exited 73. A duplicate start returned START_ALREADY_REQUESTED_RECONCILE_BEFORE_RESUME; query returned CONTROLLER_EXITED_NEEDS_RECONCILIATION. There was no automatic restart.

The synthetic zero-case reconciler bound a receipt to the prior status SHA eeebf13a6cb2aea1d2fb2593dbb0aaf831d5f41c271677b4ffcded585062c08d. Receipt SHA: 2355f9e3b55c07c484cafe5a76174d25a0fe96fa36b89728f15b3c04d3893223. Explicit resume generation 1 returned RESUME_START_REQUESTED at 2026-10-07T10:13:43.318555Z; Scheduler process PID 36308 ran under the Schedule service and exited 0. Runner query returned COMPLETED.

The resumed synthetic controller wrote truth A before starting synthetic case B and logged TRUTH_BEFORE_NEXT_CONFIRMED. Truth A SHA: f66d6116188af20c09167c3568f7a17846f78def5b845cc59456df640390071d. Truth B SHA: 5d33ae18beab6b575cc1ace05e80cd7ed1ef6560a70f8d2e2169443b5c5d08bb. Both fixtures record entry=0, FDTD=0, replay=0. The exact temporary task was deleted after terminal success and a follow-up Scheduler query confirmed it absent. Temporary files were retained.

The first harness returned KeyError after successful installation/start because it expected prepare_controller_task to return a result key. This was a harness-shape error; the scheduled process continued, exited 73 as designed, and was subsequently queried, reconciled, resumed and cleaned up. It did not affect the Runner implementation or any production task.

Task logon is InteractiveToken: SSH disconnect survival is tested while DELL remains logged in; Windows logoff behavior was not tested.

## Live Coupling manifest compatibility

Read-only Runner core-validator and Coupling verify_controller_manifest checks both PASS against the current serial_queue.py working-tree SHA 5ede3c2b2d85c225f73041a5d9332397bfa6fa03d91c39c8bba40089131d5ae5, actual queue manifest raw SHA fbcac249c59e3f242e48dfa16a8e92298c98bab48f5fe7256900b8feed10bca7, and case K6LDA1_DEV_D2_P05. The read-only controller manifest SHA is 59c1f37c4e5b74add3bc51ccdfb2820ff61683e2a78e4c9ad7d38d7990d530e0; its status path was not created. The Coupling validator independently accepted the same manifest and source.

The hash 3499b93302857cf3e93cdf4b3832e042e0680574a2e2692ffc739eb40947ce05 supplied as the claimed official script SHA was rejected by Runner with CONTROLLER_ENTRYPOINT_HASH_MISMATCH. The actual current Coupling worktree is dirty: current file SHA is 5ede3c2b2d85c225f73041a5d9332397bfa6fa03d91c39c8bba40089131d5ae5, while the committed HEAD copy SHA is 8865671d21047a1e0f65d35946de54829539638e756eb25210d3286652e61e2e. Thus the current candidate is technically compatible, but the separately supplied official pin is not the bytes currently on disk. Do not install production task until Coupling owner resolves that pin discrepancy and supplies an approved clean source/manifest.

The current Coupling source includes an explicit FAILED_PREENTRY recovery path for K6LDA1_DEV_D6_P05. This Runner-side audit did not invoke Coupling reconciliation or mutate the Coupling ledger; a fresh Coupling-owned reconciliation result remains required before production queue start.

## Other live observations

The existing single-case Runner worker was Ready at the read-only check; the production controller task was absent. Eight pre-existing fdtd-solutions.exe -server -hide API processes had Python helper parents and were left untouched; no fdtd-engine process was found. The owner lookup for those API processes was not available through the attempted CIM method. At inspection, the GPU showed 2% utilization and 2164 MiB used; no Lumerical process appeared in the NVIDIA compute-app listing. This is not a production workload qualification.

## Verification

- All 15 Runner V1 test modules: 174 passed and 50 subtests passed after SID and trigger validation fixes.
- Focused Scheduler/controller tests: 35 passed.
- Python compilation and git diff --check passed; only LF-to-CRLF Git notices.
- Actual Task Scheduler synthetic start, duplicate exclusion, disconnect progress, exit reconciliation, receipt-bound resume, fake truth-before-next and exact-task cleanup passed.
- Live Runner and Coupling manifest validators both accepted the current working-tree candidate; mismatched claimed 3499 hash was rejected.
- No production Coupling task, queue call, case request, solver entry, FDTD run, replay, Coupling ledger edit, or Coupling source edit occurred in this Runner task.

The implementation is an offline Runner control integration. It does not authorize any case or qualify production queue execution.


## Reproducible test command and coverage

Executed from the canonical Runner worktree root, after the Windows SID XML fix:

    N:\anaconda_envs\RCP_LCP\python.exe -m pytest -q scripts/shared_fdtd/gpu_runner_v1/test_controlled_admission_v1.py scripts/shared_fdtd/gpu_runner_v1/test_controlled_monitor_extraction_v1.py scripts/shared_fdtd/gpu_runner_v1/test_controlled_preentry_h5_v1.py scripts/shared_fdtd/gpu_runner_v1/test_d6_m05_orphan_closeout_v1.py scripts/shared_fdtd/gpu_runner_v1/test_d6_p05_orphan_preentry_recovery_v1.py scripts/shared_fdtd/gpu_runner_v1/test_g023_postentry_closeout_v1.py scripts/shared_fdtd/gpu_runner_v1/test_gpu_runner_v1.py scripts/shared_fdtd/gpu_runner_v1/test_gpu_runner_v1_adapter.py scripts/shared_fdtd/gpu_runner_v1/test_k6_v2_solver_budget_v1.py scripts/shared_fdtd/gpu_runner_v1/test_power_fraction_normalization.py scripts/shared_fdtd/gpu_runner_v1/test_queue21_exception_and_global_hold_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_lifecycle_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_task_scheduler_v1.py scripts/shared_fdtd/gpu_runner_v1/test_session_lifecycle_v1.py scripts/shared_fdtd/gpu_runner_v1/test_task_scheduler_v1.py

Result: 174 passed, 50 subtests passed in 42.63 seconds. The focused command was:

    N:\anaconda_envs\RCP_LCP\python.exe -m pytest -q scripts/shared_fdtd/gpu_runner_v1/test_task_scheduler_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_lifecycle_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_task_scheduler_v1.py

Result: 35 passed in 3.66 seconds.

Coverage includes duplicate submission/start exclusion in test_install_and_start_are_singleton_and_duplicate_start_is_idempotent, test_concurrent_controller_starts_create_one_owner_and_one_task_run, and test_duplicate_submission_maps_to_one_request_and_one_worker_claim; controller loss and explicit reconciliation in test_controller_process_loss_is_reported_and_never_auto_restarted, test_resume_requires_reconciliation_and_proves_durable_truth_handoff, and test_resume_refuses_unresolved_or_nonterminal_runner_request; one-slot and zero-replay manifest bounds in test_controller_manifest_rejects_unbounded_or_unauthorized_requests; and durable truth-before-next in both the receipt handoff test and actual synthetic Task Scheduler event sequence.

At the start of this report update the Runner branch was codex/apcd-gpu-production-runner-v1, HEAD a97245c4f64d737cb9e26763ceabc82b1cb82658, upstream divergence 0/0, and only the three intended Runner source/test files plus this report directory and Runner handoff were dirty. Exact commit and push state are reported in the task completion response; no Coupling path is included in the Runner allowlist.

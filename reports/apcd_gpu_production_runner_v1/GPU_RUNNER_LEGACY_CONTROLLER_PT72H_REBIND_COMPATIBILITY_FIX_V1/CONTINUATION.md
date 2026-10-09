# Continuation: PT72H controller rebind

Rebind is COMPLETE; do not repeat the API unless a live read proves drift.

Runner: D:\project\worktrees\blue_apcd_gpu_production_runner_v1
Branch codex/apcd-gpu-production-runner-v1, HEAD d4dc99fd5ffb0ecefc7a1b09d6e2c940c4eb2ccb, clean/upstream 0/0 at verification.
Transaction b02087204164ae25428af0794915423304931c81cfb817f601fedea1df5a139f; journal phase COMPLETE, SHA256 6f6f85ce5dabd4f6c28836c020aa7012d80cee0218cec9d1a4df16b19bed0620.

Old request bb93248ca2dff9605d7885554a319394 is STOPPED_RECONCILED. New request bbb7f19186776ceff07f93a17fded92b is installed. Live task state Ready, PT0S, IgnoreNew; no start was issued. Runtime binding SHA256 155b81aeab5227aa99ac55bf5a9778f0c2e3fd2e79a31c1d17c9b2474dd65193. New task has no start claim. Old historical start claim is retained.

Bound successor scope: G027-G116, 90 cases; max concurrency 1, one entry per case, replay=0, truth-before-next. Queue snapshot SHA256 951323df115a052933afb9bd360b1500dbc8a8a3ca6c6491f6b7dabd6d6bce4d records active=0 and pending replay=0. Coupling code SHA256 93d29da19fcc5b8d5df826646683a3090f785673177ece82697be01542980947.

G026 remains one consumed entry, replay=0, no truth, physical engine entry UNKNOWN. This task added zero solver entries. No target controller/worker/engine process or Runner active marker was observed. Unknown API servers were untouched.

Coupling's G026 FINAL_REPORT still says successor not bound, and its worktree has unrelated dirty/staged files. Do not edit or stage Coupling files here. Coupling owner should refresh its report/continuation using the Runner journal and live readback, then start the unstarted successor once with:
N:\anaconda_envs\RCP_LCP\python.exe D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1\task_scheduler_v1.py start-controller-task bbb7f19186776ceff07f93a17fded92b

Do not use resume-controller-task. This task did not test logout/reboot survival or observe continuous production.
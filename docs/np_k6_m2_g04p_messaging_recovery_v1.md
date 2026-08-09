# NP K6 M2 G04-P messaging repair and post-save recovery v1

Status: `NP_K6_M2_G04P_MESSAGING_REPAIR_BLOCKED`

- case: `NP_K6_M2_BATCH1_G04_P`, attempt `attempt_001`
- immutable ledger: entered=1, run_invocation_count=1, engine_completed=1, controller_completed=0, post_save_completed=0
- zero-solver recovery calls: 0; attempt_002: forbidden; no post-FSP created
- original run/setup SHA256: `db666c715fe430080f0013e1bdbb03c42286095f97c880bcf404304f5307377c`
- blank LumAPI smoke: failed at `appOpen` with `Failed to start messaging, check licenses...`
- license service: reachable on `1055@DESKTOP-NNE313K`; no service restart or configuration change
- original-attempt search: no distinct persisted solver result dataset or post-FSP; source/run/backup FSPs are identical setup artifacts
- V2 numerical gate: `NOT_EVALUABLE`
- later Batch1 cases entered: false; sealed access: 0; training: false

The evidence includes a transparent correction record for an earlier cleanup that terminated PIDs 5756 and 32608; later process-tree evidence identified them as children of active non-NP `lp_global_h_h1a_probe_v1.py` processes. No license service, FDTD engine, MPI, G04-P controller, or parent LP process was terminated.

Evidence directory: `D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_m2_g04p_messaging_recovery_v1`

Captured UTC: `2026-08-09T13:33:39.744691+00:00`


## Root-cause refinement

Read-only postmortem logs show the v251 local Ansys Licensing Client Proxy at `54018@127.0.0.1` failing SSL handshake and exiting; the shared FlexNet server at `1055@DESKTOP-NNE313K` remains reachable with capacity. `AWP_LOCALE251=zh` also points to a missing `language\zh\ansysli_msgs.xml`; a process-local `en-us` override was tested and still failed. The remaining repair would affect active non-APCD Ansys EDT licensing-client processes (PIDs 9228/22012), so no restart or termination was performed.

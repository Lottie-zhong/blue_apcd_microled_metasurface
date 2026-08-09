# NP K6 M2 G04-P local license proxy repair v1

Status: `NP_K6_M2_G04P_ENGINE_COMPLETED_RESULT_NOT_PERSISTED_UNRECOVERABLE`

- isolated owner: old `ansyscl.exe` PID 9228, port 54018, parent PID 21060 absent
- dependency classification: `LOCAL_PROXY_SAFE_TO_RESTART`
- repair: exact PID 9228 normal stop; official v251 `ansyscl.exe` restarted as PID 5148 on port 54018
- shared FlexNet `1055@DESKTOP-NNE313K` was not restarted or modified
- two independent zero-solver LumAPI smokes passed using process-local `AWP_LOCALE251=en-us`; session creation, messaging, license checkout and close passed; run/load/save remained false
- G04-P ledger remains entered=1, run_invocation_count=1, engine_completed=1, controller_completed=0, post_save_completed=0
- original result search found no solver monitor dataset, autosave result, or distinct post-FSP; pre-run/run/backup FSP artifacts share setup SHA `db666c715fe430080f0013e1bdbb03c42286095f97c880bcf404304f5307377c`
- numerical gate: `NOT_EVALUABLE`; provisional/training labels: false; attempt_002 and rerun: forbidden
- non-NP processes preserved; unrelated termination count in this stage: 0

Evidence: `D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_m2_g04p_local_license_proxy_repair_v1`

Captured UTC: `2026-08-09T14:03:23.540488+00:00`

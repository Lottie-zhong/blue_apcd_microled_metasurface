# CONTINUATION - APCD GPU V2.1 DIAG2 validator fix

Status: V21_REAL_DIAG2_VALIDATOR_OFFLINE_PASS

- GPU worktree: D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1
- Branch: codex/apcd-gpu-v2-serial-production-v1
- Candidate source commit: b9abe87058d65cb2ba52c5ce1a7acb377a2ab048; normal push completed.
- Baseline candidate: a16f30d8cda254722fc77015f0cec9530b2d18c9.
- Coupling worktree HEAD read-only: e3a9528c1d5cf3eb4b27ff9a0b4201618d28f512; 940 pre-existing dirty/staged entries were not changed.
- Full offline regression: 252 passed, 0 failed, 0 skipped.
- The frozen 6 ps contract passes the candidate physical-contract adapter for A1/A2 without changing its bytes or SHA. Missing Profile and missing production Admission remain separate default-deny gates.
- Installed disabled release: 83c4fcd1329252e069760789ef5d0e92b02a781a; installed diag2.py SHA read back: 99f6c199fe077d0a2d2d5e420a9ccdda3a4c4ebc8c8eeabe5ef6419eff517a5e. Candidate patch is not installed.
- Live GPU pre-entry status remains HOLD unless a future complete pre-entry gate passes. Current bounded WDDM sample reason: WDDM_NON_SYSTEM_GPU_ACTIVITY_PRESENT.
- V2 slot readback: {"generation": 95, "owner_present": false, "request_present": false, "token_present": false}; DIAG2 task rows=0; Coupling DIAG2 remains 0/2 and DOE56 remains 4 entered / 52 HOLD.

Next:
1. Request one controlled patch-deployment authorization for the pushed source commit. Do not install until that authorization is received.
2. Before any later scientific entry, repeat a fresh complete live GPU exclusivity check; the current WDDM result is not an admission.
3. DIAG2 production entry still requires a separately issued valid Science Admission and finite release. Offline fixtures are never production credentials.

This task performed no installation, Scheduler/ACL edit, process termination, scientific solver entry, replay, or ML fit.

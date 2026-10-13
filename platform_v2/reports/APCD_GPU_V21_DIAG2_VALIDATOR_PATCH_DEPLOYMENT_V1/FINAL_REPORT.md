# APCD GPU V2.1 DIAG2 Validator Patch Deployment - Final Report

Status: GPU_V21_DIAG2_PATCH_INSTALLED_DISABLED_VALIDATED

PATCH_INSTALLATION=PASS
CONTRACT_COMPATIBILITY_INSTALLED=PASS
DEFAULT_DENY_INSTALLED=PASS
SCHEDULER_DISABLED=PASS
NO_SCIENTIFIC_ENTRY=PASS
ROLLBACK_READINESS=PASS
GPU_RESOURCE_GATE_MECHANISM=PASS
GPU_RESOURCE_LIVE_PREENTRY=HOLD

Report timestamp (UTC): 2026-10-13T17:15:15.027338+00:00

## Release identity

Original installed release base: 83c4fcd1329252e069760789ef5d0e92b02a781a.
Installed patch source commit: b9abe87058d65cb2ba52c5ce1a7acb377a2ab048.
GPU source worktree HEAD at audit: 8143b79ee69de0606695f4b86aa4ea687522493a. The installer did not copy the whole latest HEAD; it used the prior installed release plus exactly these three tested runtime modules: diag2.py, gpu_readonly.py, serial.py.

Installed release path: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_diag2_validator_b9abe87058d6
Installed code inventory SHA-256: ea92f62348f6d32c15bb46a992d1ca370a159c7f645808a472ae4013a6a756e1
Patch release manifest SHA-256: d4f37eeb249747eb07e1227ef9a64eb7a256712661a496d014e777e679a8b30a
Current installation marker SHA-256: fd6f673db4f5f318421bb1842ae2ceaca3885c4b04b48eeaec5b0bc44fcbbb47

The 26 inventoried release files all match their SHA-256/size records. The changed modules are byte-identical between the installed release and GPU worktree. The old release remains available and no immutable release was overwritten.

## Frozen DIAG2 contract

The installed adapter accepts the Science Owner's real A1/A2 frozen manifest and official 6 ps contract in offline tests. The official contract file SHA-256 is 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36; candidate manifest SHA-256 is 8472518baf1425243b05292ac882a141bd886f91524b1f2bd664e4f4d962e5c7. The coupling_609d_v1 certification SHA-256 remains 11ddbf2fc13e2dd34a9a4c4b07daf17c6d2c8275a64eb27fa3202e67cad204ca. Coupling worktree HEAD at audit was e3a9528c1d5cf3eb4b27ff9a0b4201618d28f512. The four Science Owner handoff artifacts and the two referenced ledger SHA-256 values are recorded in SHA_INVENTORY.json; the DOE56 ledger is 9e277f111f3ba6e7399d74e730f05a1f0a69388be8e40506135b28d8ffc84367 and the queue ledger is a25cb5347cb97020c6abbddfdc99f669843b384c4f1932de5892fa249813572a. The 6 ps physics contract and profile certification hashes are unchanged.

The 25-test focused installed suite passed. It includes the real-contract compatibility test, wrong-contract-SHA denial, case/geometry mismatch denial, and proof that an unissued production admission remains denied after adapter conversion. The contract, source/setup SHA, A1/A2 identities, and the approved two-entry ceiling were not changed. The test fixture was offline-only and is not a production credential.

## Installed default-deny and scheduler

profiles is empty. CURRENT_SCIENCE_BINDING remains science_authorized=false and SCIENCE_RELEASE_DENY remains false/no requests. The Science Owner candidate manifest still has production_admission_issued=false and entry_authorization_issued=false.

The V2 Controller and both V1-exclusive Controller/Worker Scheduled Tasks are Disabled, AllowDemandStart=false, with zero exported XML triggers and no next run. The V2 action now points to the installed patch release. V1 task definitions were unchanged. The V2 task LastTaskResult was preserved; it was not edited to simulate success. No controller/worker launch process matched the known installed entry scripts.

## Installed regression and runtime preservation

Final installed-release regression: 252 passed, 0 failed, 0 skipped, 13 warnings, 369.94 seconds. The installed module-origin record places apcd_gpu_v2, diag2, serial, and gpu_readonly under the new immutable release. The focused contract suite passed 25/25.

A first custom test wrapper produced 250 passes and two multiprocessing timeouts because it lacked a Windows main guard. Two later test harness setup attempts failed closed before collection (plugin newline encoding, then source-path precedence). Those logs are preserved and superseded. The canonical standard python -m pytest invocation used a report-local config without the source tree's pythonpath override and passed the full suite.

The installed SQLite remained SHA-256 8c52bb709b7f595dd500b474c9023175889ae34551630fbce8a281dc67dc6e99, identical to predeployment. It still contains 94 TRUTH_VALID rows, 216634 events, no DIAG2 task rows, and an empty generation-95 slot. Runtime config SHA is 575f3e853f3799d5db62574f73d21e69f7f871f5fe5a9ceb158e14beaad19e09; science binding SHA is a391904e7b9fce13e30ae04bcc83dbfde16f7af868b52ebb979146756478e530; deny file SHA is 8301556cccc8c385e5ac7fae98e99ef4091f342f3a44051c0fdcfe771de16e89. ACL readback is identical before/after.

Counts for this task: solver entries 0; FDTD 0; FMM/RCWA 0; new ML fits 0; replay 0; sealed access 0. DIAG2 remains 0/2. DOE56 remains 4 entered / 52 unentered under FROZEN_NUMERICAL_ADVANCEMENT_HOLD.

## Resource gate

The installed resource-gate mechanism passes offline regression, including WDDM, compute-activity, PID-reuse/identity-loss, missing-counter and N/A process-memory checks.

The live science gate remains HOLD. At the latest snapshot, the RTX 3080 showed 0 percent utilization but 1946 MiB / 10240 MiB allocated; no nonzero WDDM 3D, VideoEncode or Compute rows were returned. Eight fdtd-solutions.exe and two ansysedt.exe images remain; nvidia-smi process memory is N/A for the relevant Ansys processes. There is no fdtd-engine.exe or known Controller/Worker process. PIDs 18936 and 40664 remain alive and partially classified; only PID, creation time, image, parent and parent creation time were read. Their command lines and stdin were not read. No process was terminated. These facts do not prove global GPU exclusivity, so no science entry is permitted.

## Rollback

Rollback was not executed. All 52 backup entries verify against the backup manifest. The original immutable release and saved disabled V2 task definition remain intact. See DEPLOYMENT_AND_ROLLBACK_RECORD.md for the exact restore point and disabled-only rollback sequence.

## Git

Branch codex/apcd-gpu-v2-serial-production-v1, source HEAD 8143b79ee69de0606695f4b86aa4ea687522493a, upstream ahead/behind 0	0 before committing this report. No tracked source changes were present. Existing untracked reports and all Coupling worktree changes were preserved. The release/readback/report commit and push result is recorded in the final delivery status.

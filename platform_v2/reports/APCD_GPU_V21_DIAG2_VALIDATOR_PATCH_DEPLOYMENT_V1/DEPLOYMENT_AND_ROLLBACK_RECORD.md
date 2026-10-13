# Deployment and rollback record

## Installation transaction

Before patching, the immutable release was based on 83c4fcd1329252e069760789ef5d0e92b02a781a; its code inventory SHA-256 was 2d229e44be8c7e97a5cbc14a1e8384550a09a66c8393c27ede9d8e6a3a49d668. The replacement release is D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_diag2_validator_b9abe87058d6, built from the old release plus only diag2.py, gpu_readonly.py and serial.py. Its 26-file code inventory SHA-256 is ea92f62348f6d32c15bb46a992d1ca370a159c7f645808a472ae4013a6a756e1; the release manifest SHA-256 is d4f37eeb249747eb07e1227ef9a64eb7a256712661a496d014e777e679a8b30a. Every file and size matches the release inventory.

V2 Controller Scheduler action changed from:
"D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_83c4fcd1329252e069760789ef5d0e92b02a781a\platform_v2\tools\serial_controller.py" --platform "D:\apcd_runtime\gpu_platform_v2_serial_production_v1\platform_config.json" --platform-sha256 575f3e853f3799d5db62574f73d21e69f7f871f5fe5a9ceb158e14beaad19e09
to:
"D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_diag2_validator_b9abe87058d6\platform_v2\tools\serial_controller.py" --platform "D:\apcd_runtime\gpu_platform_v2_serial_production_v1\platform_config.json" --platform-sha256 575f3e853f3799d5db62574f73d21e69f7f871f5fe5a9ceb158e14beaad19e09

The executable remains N:\anaconda_envs\RCP_LCP\python.exe; working directory remains D:\apcd_runtime\gpu_platform_v2_serial_production_v1. The task stayed Disabled before and after, AllowDemandStart stayed false, exported XML contains zero triggers, NextRunTime is null, and LastTaskResult was left untouched. The current export SHA-256 is 093f1f1a1bf011fe86beb1e5c6a4a483b71e455ef1ca3e254bdf8d5607baea92, matching install readback. Both V1-exclusive tasks remained Disabled and unchanged.

Platform config SHA stayed 575f3e853f3799d5db62574f73d21e69f7f871f5fe5a9ceb158e14beaad19e09; science binding SHA stayed a391904e7b9fce13e30ae04bcc83dbfde16f7af868b52ebb979146756478e530; release deny SHA stayed 8301556cccc8c385e5ac7fae98e99ef4091f342f3a44051c0fdcfe771de16e89. profiles remains empty. Runtime ACL SDDL is identical before/after. V2 SQLite SHA stayed 8c52bb709b7f595dd500b474c9023175889ae34551630fbce8a281dc67dc6e99; no rows/events/slot state changed. No Shared or Coupling database, science ledger, FSP/H5, receipt, or sealed item was modified.

## Post-install acceptance

The 25 focused installed tests passed against the actual frozen DIAG2 manifest and 6 ps contract. Full installed-release regression passed 252/252 with 0 skips. Final zero-solver counts are: entry 0; FDTD 0; FMM/RCWA 0; ML fits 0; replay 0; sealed access 0. DIAG2 remains 0/2 and DOE56 remains 4/52 HOLD.

The patch is installed successfully while live science entry remains HOLD. The fresh GPU sample showed 0 percent utilization and 1946 MiB allocated; Lumerical API and Ansys GUI processes remain with N/A per-process GPU memory, so global exclusivity is unproven. Unknown PID 18936 and SSH child 40664 were not terminated or queried for command line/stdin.

## Verified rollback point

Rollback was not executed. Backup path: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\installation_backups\v21_diag2_validator_patch_20261013T162838Z. Backup manifest SHA-256: 60a863f7cbae26caa97787b80983920275ccf177ae2817ea8222f87247c2d2fa. All 52 entries verify. Original release path: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_83c4fcd1329252e069760789ef5d0e92b02a781a. Original release inventory SHA-256: 2d229e44be8c7e97a5cbc14a1e8384550a09a66c8393c27ede9d8e6a3a49d668. Saved old task XML SHA-256: 439f2320c6a0a7529172d9ff411f21a37e70b03505e34368761f82ba99f5b74e; it records the old release action with Enabled=false, demand-start=false and zero XML triggers.

If a rollback is later authorized:
1. Verify no Controller, Worker or solver is running; keep the V2 Scheduled Task Disabled.
2. Restore the V2 task action fields from the saved task.xml: original interpreter, old serial_controller.py under the 83c4fcd1329252e069760789ef5d0e92b02a781a release, original --platform/config SHA arguments, and original working directory. Do not enable the task.
3. Restore only installation pointer/manifest files and installed-code inventory from the verified backup. Reverify the old immutable release inventory.
4. Keep science binding unauthorized and release DENY. Do not restore or rewind SQLite, Coupling ledgers, FSP/H5, receipts or truth.
5. Read back Disabled/demand-start/zero-trigger state, pointer/code hashes, DENY state, empty slot and unchanged DB SHA; stop before any solver invocation.

The saved raw task XML is retained as evidence; this deployment did not import it directly.

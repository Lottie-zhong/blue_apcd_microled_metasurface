# APCD GPU Runner V1 - owner recovery and EXT02 diagnostic

Status: **PASS for the authorized single GPU run, durable truth and two-plane extraction handoff. Coupling's frozen comparison remains pending.**

## Consumer quarantine and hold release

Coupling exclusion commit 8019c12c9627dad414bbbfff3579a0bffcda6aa4 has registry SHA256 01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261. Inventory SHA256 fde78be0e927ba084301cfcbf8b8500206eaea1dc7fdfb4715eb88517231c48b; all 12 listed file hashes match. Its final report records 32 focused tests passed. The report is hash-verified; those tests were not rerun here.

The registry binds the V2 disposition, owner decision and delegation. Current Runner authority binds the V3 exception disposition SHA256 0f0ba84d472a179dc67b7ed62f382d3ee78ad0673098f3bc9ca29d6877d5280b and the same registry, decision and delegation. Its generation-26 ACTIVE hold field is the registry's creation-time snapshot; the registry explicitly does not release Runner holds. Queue21 physical solver-entry count remains UNKNOWN and its case/truth remain quarantined.

The owner-approved queue21 hold hold-4a6eab94af3b4a6d8510ba2fe32a5b66 was released via official API authority SHA256 7b2412e3271aa518fe67deb9b6cd8b74cf7da99e1c8331bee948e493aad0b7d2, result SHA256 9b2b31924ddc2e1a400b5e07e2b480d053ab9b4c627b32dbd6d720b55b7e54d7, hold event 4, generation 27. Current control is hold=0, health=PASS, active global holds=0.

## Diagnostic execution and truth

Only K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001 was authorized and run. Runner HEAD at dispatch was 472bf2ae4c5bc8faaea04adec13d0a441777fc3f. Exactly one official run-one call and one solver entry; automatic replays: 0. Run ID: EXT02_DIAG_20261004T141216Z_1b4ce0df234b. Terminal DONE; lineage: fdtd-solutions PID 40392 -> mpiexec PID 9384 -> fdtd-engine-msmpi PID 28316 with -gpu. Fresh LOAD and SCIENTIFIC_VALID passed. Maximum energy-closure absolute error: 1.1102230246251565e-16. The Runner lock and active-run marker are released.

- FSP: D:\apcd_runtime\gpu_production_runner_v1\runs\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001\EXT02_DIAG_20261004T141216Z_1b4ce0df234b\run.fsp; SHA256 68ae5cd34144bbe908fc57a5628ac041a4bef2be35058fc614133f58233b27df (212070498 bytes).
- Native FSP H5: D:\apcd_runtime\gpu_production_runner_v1\runs\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001\EXT02_DIAG_20261004T141216Z_1b4ce0df234b\run\run_output.h5; SHA256 3ae7828f30ec1edcd6e8493461064325163ecd3fa993bb7baefb7cf212551077 (95856561 bytes).
- Truth H5: D:\apcd_runtime\gpu_production_runner_v1\runs\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001\EXT02_DIAG_20261004T141216Z_1b4ce0df234b\truth.h5; SHA256 05495a2d202795fd215474ac63c461558269efed05581e528048ed383627eb25 (651200 bytes).
- Raw fields including incident-reference IN E/H: D:\apcd_runtime\gpu_production_runner_v1\runs\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001\EXT02_DIAG_20261004T141216Z_1b4ce0df234b\raw\K6V1_EXT02_TWO_AIR_PLANES_DIAG__attempt_001_raw_complex_fields.npz; SHA256 159a9d3413b72791d9ecca51df8d8e4ca84c12f8765191e132a080ae399b07d7.

## Two-plane extraction

The current LOAD-only extractor SHA256 616f857a6b620460b370904ca3f3825d28090f712413240b9b3a4f15a61611ef passed 9 focused tests. Both named monitors were read from archived FSP and matched uniquely to H5 groups; six finite complex E/H components were extracted at 349 x 59 x 1 x 21 samples.

- MON_POSTNP: configured z=1800 nm, actual z=1801.9999999999932 nm, H5 group Monitor2, NPZ SHA256 9746a3c41174f16aac7994e322cc76086fda6b4318dc6876c996b4f1d3a646b7.
- EXT02_POSTNP_DIAG_Z2000: configured z=2000 nm, actual z=2006.6041666666679 nm, H5 group Monitor4, NPZ SHA256 84186284d4320bf3966af14a823918e85a53cfc89f350ae5ca07d6ac2cd24ce7.

Both use frozen reference plane z=1722 nm. Incident-reference MON_IN E/H and spectrum are linked from the raw NPZ for the official Coupling normalization; Runner applied no fitted scale or phase alignment. Configured mesh/PML values are recorded separately. Actual local mesh spacing at both planes and actual PML inner face were not captured in saved results and remain unknown.

Machine-readable Coupling handoff: D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1\EXT02_COUPLING_HANDOFF_V1.json; SHA256 2f41bfd493f4105b013ee4269033f789b0d86d007169a57557bee3262f325d75. This is an input handoff; the frozen two-plane numerical comparison has not passed or been run by Runner.

## Boundaries and next

The diagnostic's one-entry budget is consumed. Do not rerun or create attempt_002. Queue21 remains UNKNOWN/quarantined. All 160 V2 geometries remain at zero solver authorization and zero entries. Coupling should now run only the frozen one-case comparison using the handoff and protocol. No point reselection, sign change, fitted normalization or global-phase oracle alignment.

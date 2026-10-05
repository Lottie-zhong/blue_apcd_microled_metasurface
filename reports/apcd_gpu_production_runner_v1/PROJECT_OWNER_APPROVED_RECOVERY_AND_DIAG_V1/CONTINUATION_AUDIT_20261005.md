# Continuation audit - current status on 2026-10-05

This is an append-only verification note for the project-owner recovery and single-entry EXT02 diagnostic. It records the current audit only; it does not replace the earlier final report, consumer registry, queue21 history, or solver artifacts.

## Queue21 consumer exclusion

- Current Runner worktree: branch codex/apcd-gpu-production-runner-v1, HEAD 6afb002ac4df29dedaedc8f65d67a3ecabc9eedf, upstream divergence 0/0, tracked tree clean.
- Current Coupling worktree: branch work/mdc-np-coupling-ml-v1, HEAD 01a14940cd92072daf13173588ea02d5416b62dc, upstream divergence 0/0, tracked tree clean. Existing unrelated untracked files were preserved.
- Coupling consumer-exclusion commit 8019c12c9627dad414bbbfff3579a0bffcda6aa4 is an ancestor of current Coupling HEAD. The consumer enforcement source/test paths have no changes after that commit.
- Registry SHA256: 01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261. Inventory SHA256: fde78be0e927ba084301cfcbf8b8500206eaea1dc7fdfb4715eb88517231c48b. All 12 inventory entries match current bytes and sizes. The linked report records 32 focused tests passed; the report and sources were hash-verified, not rerun in this audit.
- Registry-bound V2 exception disposition SHA256 468331313528c2a1d68e079617d84c8cac7baceff329e1384a65a38d1ec7de97, owner decision SHA256 da6176fe98a1e7f38e149db417e419455720922527d6d9699772456f308a752a, and execution delegation SHA256 14ee2b2e84fb291775b9e2c4dbfb501b253c3d10b5ab88ecda9abea2575d55f1 match their Runner files. Current V3 exception disposition SHA256 is 0f0ba84d472a179dc67b7ed62f382d3ee78ad0673098f3bc9ca29d6877d5280b and records consumer quarantine enforcement.
- The registry Runner HEAD 88c8ba7afe99ab8e58a4f41f0698b56f65bc0b35 and generation-26 ACTIVE hold are immutable creation-time provenance. They are not current-state claims and were not rewritten. The current Runner is later; consumer protection remains applicable because the pinned consumer code and its 32-test source set are unchanged after commit 8019c12.

## Hold and current execution state

- The official hold-release result records release of only hold-4a6eab94af3b4a6d8510ba2fe32a5b66 using authority SHA256 7b2412e3271aa518fe67deb9b6cd8b74cf7da99e1c8331bee948e493aad0b7d2, release event 4, generation 26 to 27. Result SHA256: 9b2b31924ddc2e1a400b5e07e2b480d053ab9b4c627b32dbd6d720b55b7e54d7.
- A fresh read-only official control API call returned PASS, generation 27, new_entry_hold=0, no active global holds, control DB SHA256 af802fd46c023009f0a342cfa9540990c8e3a0df9b30af09ef62deeba817d9fe.
- Current Runner registry contains 14 terminal rows and no active row. Current process inspection found no fdtd-engine-msmpi.exe and no mpiexec.exe; eight long-running fdtd-solutions.exe -server -hide API contexts remain. They were not terminated. This conclusion uses runner registry/lock/lease and process evidence, not GPU utilization alone.

## EXT02 diagnostic - already consumed, never replay

- Identity: K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001; run ID EXT02_DIAG_20261004T141216Z_1b4ce0df234b.
- Existing launch evidence records prior entries 0, one adapter invocation, maximum one entry, and automatic replay budget 0. Dispatch result records adapter invocation count 1 and automatic replay count 0. Terminal state is DONE; fresh LOAD and SCIENTIFIC_VALID are true. The execution consumed its authorized entry before this audit. No run-one call or FDTD run occurred in this audit.
- Run directory: D:/apcd_runtime/gpu_production_runner_v1/runs/K6V1_EXT02_TWO_AIR_PLANES_DIAG/attempt_001/EXT02_DIAG_20261004T141216Z_1b4ce0df234b.
- Verified durable hashes: run.fsp 68ae5cd34144bbe908fc57a5628ac041a4bef2be35058fc614133f58233b27df; sibling run/run_output.h5 3ae7828f30ec1edcd6e8493461064325163ecd3fa993bb7baefb7cf212551077; truth.h5 05495a2d202795fd215474ac63c461558269efed05581e528048ed383627eb25; raw complex fields and incident reference 159a9d3413b72791d9ecca51df8d8e4ca84c12f8765191e132a080ae399b07d7.
- Two-plane LOAD-only outputs contain complex Ex,Ey,Ez,Hx,Hy,Hz, shape 349 x 59 x 1 x 21 x 3, with 21 wavelengths 440-460 nm. MON_POSTNP actual z is 1801.9999999999932 nm (H5 Monitor2); EXT02_POSTNP_DIAG_Z2000 actual z is 2006.6041666666679 nm (H5 Monitor4). Both use frozen reference plane z=1722 nm. The extractor called no solver.
- NPZ SHA256: MON_POSTNP 9746a3c41174f16aac7994e322cc76086fda6b4318dc6876c996b4f1d3a646b7; EXT02_POSTNP_DIAG_Z2000 84186284d4320bf3966af14a823918e85a53cfc89f350ae5ca07d6ac2cd24ce7. Metadata SHA256: MON_POSTNP 9c5c8e27d8ea624aad20935c67bc228afc857b02fb1df7aed3abfe8d9034a3ba; second plane d04f7e07b533542b12ff8c55d9f67a289e7d381b1c248066a6b5873e71b5fd20.
- Actual local mesh spacing at the planes and actual PML inner face remain unknown. Configured values are not treated as measurements. Coupling's frozen numerical comparison is pending; no dual-plane scientific pass is claimed.

## Scope conflict observed

The current Runner handoff has also gained a separate K6 V2 development budget authority (APCD_GPU_RUNNER_EXT02_AND_K6_V2_DEV_BUDGET_20261005_V1, budget SHA256 e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c) authorizing 128 development identities, while this project-owner recovery instruction says all 160 V2 data cases remain at zero solver authorization. The live Runner registry now contains K6LDA1_DEV_D1_M05 / attempt_001 in DONE, and its status.json records solver_entered=true. This audit did not start another V2 case or change that separate budget. Reconcile this versioned authority before any further K6 V2 launch; do not infer that this EXT02 task authorizes the V2 batch.

The earlier Runner SHA256_INVENTORY_V4.json is a historical snapshot, not a valid current whole-tree inventory. Rechecking it found 35/38 entries matching: its pinned Runner handoff markdown has since changed, the runtime Runner registry has since changed, and one listed APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.json path is absent. This does not change the independently verified Coupling V1 inventory or the current diagnostic artifact hashes.

## Handoff

The machine-readable truth handoff is EXT02_COUPLING_HANDOFF_V1.json (SHA256 2f41bfd493f4105b013ee4269033f789b0d86d007169a57557bee3262f325d75). Its reference protocol SHA256 is fa2839ac5613df63d54508d79df9da98d5bc0243876ab9c1a5538ae75b9f92b8. The Coupling evaluator has been sent the paths, hashes, actual coordinates, and explicit limits. Wait for its frozen comparison result; do not launch any case from this continuation.

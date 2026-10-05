# Owner-approved recovery and EXT02 revalidation

Captured 2026-10-05 06:33 UTC. Read-only continuation for the already completed owner-approved recovery and diagnostic.

## Coupling exclusion
- Commit 8019c12c9627dad414bbbfff3579a0bffcda6aa4 is an ancestor of Coupling HEAD a50854f8425718d5d109b341a12b75dcbc328b43. Registry SHA-256 01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261; V1 inventory SHA-256 fde78be0e927ba084301cfcbf8b8500206eaea1dc7fdfb4715eb88517231c48b; all 12 inventory items match current bytes and hashes.
- Re-ran the documented four-file focused suite at current Coupling HEAD: 32 passed in 30.13 seconds.
- Bound V2 disposition, owner decision, and delegation hashes still match current Runner files: 468331313528c2a1d68e079617d84c8cac7baceff329e1384a65a38d1ec7de97; da6176fe98a1e7f38e149db417e419455720922527d6d9699772456f308a752a; 14ee2b2e84fb291775b9e2c4dbfb501b253c3d10b5ab88ecda9abea2575d55f1. Current V3 disposition: 0f0ba84d472a179dc67b7ed62f382d3ee78ad0673098f3bc9ca29d6877d5280b. Registry's Runner HEAD 88c8ba7 and generation-26 ACTIVE are historical snapshot values. Queue21 physical entry count remains UNKNOWN and data remains quarantined.

## Live Runner state
- Runner branch codex/apcd-gpu-production-runner-v1, HEAD 8d8287970b3230254bcfc58b56162b85959b01e0, clean and synchronized with origin.
- Read-only adapter control snapshot at 2026-10-05 06:27 UTC: PASS, generation 27, new_entry_hold=0, no active holds, DB SHA-256 af802fd46c023009f0a342cfa9540990c8e3a0df9b30af09ef62deeba817d9fe. Queue21 hold was already officially released, authority SHA-256 7b2412e3271aa518fe67deb9b6cd8b74cf7da99e1c8331bee948e493aad0b7d2, event 4, generation 26 to 27. This revalidation did not call release or alter the DB.
- Runner registry has 14 terminal rows, none active; owner probe false; no fdtd-engine-msmpi.exe, mpiexec.exe, or fdtd-solutions.exe process. RTX 3080 snapshot: 8001 MiB free; external desktop clients visible, not FDTD processes.

## Diagnostic truth and handoff
- K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001 is already DONE, run EXT02_DIAG_20261004T141216Z_1b4ce0df234b; status.json says solver_entered=true and solver_invocations=1. Budget 1/1 consumed. No run-one/FDTD/replay occurred during this revalidation.
- Source/staged FSP SHA-256 5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30; pre-entry proof be51affff991e69cf22149bf49eed16b647f7b1e0c4a3ee9f50297abe2c48ded; setup validation 5f75025cc8681dcfc145c397051493539288b2a2edcd2b051d9d3f99d4e7e019.
- Current artifact hashes: run.fsp 68ae5cd34144bbe908fc57a5628ac041a4bef2be35058fc614133f58233b27df; sibling H5 3ae7828f30ec1edcd6e8493461064325163ecd3fa993bb7baefb7cf212551077; truth H5 05495a2d202795fd215474ac63c461558269efed05581e528048ed383627eb25; raw fields 159a9d3413b72791d9ecca51df8d8e4ca84c12f8765191e132a080ae399b07d7.
- MON_POSTNP actual z 1801.9999999999932 nm, H5 Monitor2, NPZ 9746a3c41174f16aac7994e322cc76086fda6b4318dc6876c996b4f1d3a646b7. EXT02_POSTNP_DIAG_Z2000 actual z 2006.6041666666679 nm, H5 Monitor4, NPZ 84186284d4320bf3966af14a823918e85a53cfc89f350ae5ca07d6ac2cd24ce7. Both are 6 complex E/H fields, 349 x 59 x 1 x 21, 440-460 nm, de-embed to z=1722 nm. Actual local mesh and PML inner face remain unknown.
- Handoff JSON SHA-256 2f41bfd493f4105b013ee4269033f789b0d86d007169a57557bee3262f325d75 was sent to Coupling for the frozen independent comparison. Runner did not run that comparison.

## V2 authority conflict
The existing Runner continuation audit records a separate 128-ID development budget (SHA-256 e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7) and K6LDA1_DEV_D1_M05 / attempt_001 DONE with solver_entered=true. This conflicts with a blanket current claim that all 160 V2 IDs have zero authorization/entries. This revalidation started no V2 case; preserve the pilot history and reconcile the authority before any more V2 generation.

Revalidation counts: tests 32 passed; new solver entries 0; FDTD runs 0; replays 0.
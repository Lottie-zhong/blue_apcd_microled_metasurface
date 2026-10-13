# CONTINUATION - GPU V2.1 DIAG2 Validator Patch

Current status: GPU_V21_DIAG2_PATCH_INSTALLED_DISABLED_VALIDATED.

Installed release: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_diag2_validator_b9abe87058d6
Code inventory SHA-256: ea92f62348f6d32c15bb46a992d1ca370a159c7f645808a472ae4013a6a756e1
Patch source commit: b9abe87058d65cb2ba52c5ce1a7acb377a2ab048
GPU source HEAD at audit: 8143b79ee69de0606695f4b86aa4ea687522493a
Coupling HEAD at audit: e3a9528c1d5cf3eb4b27ff9a0b4201618d28f512

The real frozen A1/A2 manifest and official 6 ps contract pass the installed offline compatibility suite. Full installed-release regression is 252 passed, 0 failed, 0 skipped. Controller and both V1-exclusive Scheduler tasks remain Disabled; profiles is empty and production Science Admission is unissued.

DIAG2 remains 0/2 entered. DOE56 remains 4 entered / 52 unentered under FROZEN_NUMERICAL_ADVANCEMENT_HOLD. This patch deployment used zero solver entries, FDTD, FMM/RCWA, ML fits, replay, and sealed access.

The installed GPU gate mechanism passes offline regression. Live pre-entry exclusivity remains HOLD due nonzero allocated memory and existing Ansys/Lumerical processes without complete process attribution. Do not start A1/A2.

A future science attempt requires a new formal Science Admission bound to the two frozen A1/A2 attempt_001 identities, the unchanged 6 ps contract SHA 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36, coupling_609d_v1 certification SHA 11ddbf2fc13e2dd34a9a4c4b07daf17c6d2c8275a64eb27fa3202e67cad204ca, and exact two-entry budget; then a fresh live GPU-exclusive pre-entry check and separate explicit science-entry authorization. No such Admission or start occurred in this task.

Rollback was not executed; the prior immutable release and all verified backup artifacts remain available. Keep the Scheduled Task Disabled during any later restore.

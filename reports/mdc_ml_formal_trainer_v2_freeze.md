# MDC-ML Canonical Formal Executor V2 Refreeze

The prior `35089b3` freeze supplied interface guards and a synthetic harness, but the first formal preflight correctly stopped at H11 because it lacked a canonical loader, run-root allocator, persisted state initialization, and authorized production dispatch.

This refreeze adds read-only canonical input discovery and fingerprinting, scoped authorization, collision-safe formal-run allocation outside the worktree, persisted contract/state/manifest initialization, and plan/readiness dispatch for classification, regression, and future stages. Real canonical readiness reports 2640 classification rows, 837 regression rows, Round1 classification 128 split `[31,34,39,24]`, regression 100/28 split `[24,22,34,20]`, 150 features, and no sealed target loading.

No formal fit, prediction, formal output write, solver call, or sealed-test access was performed by this repair task. The prior H11 control root remains failure evidence only and is superseded for formal execution.

## Classification production-dispatch v3 attestation

Freeze A (`35089b3`) provided guards and a synthetic harness but not the canonical production chain. Freeze B (`810dde5`) added the canonical loader, allocator, authorization, and plan route but deliberately failed closed before a fold executor. Freeze C candidate (`f6472a4a`) wired the classification backend and the 128-row synthetic provider, but its initial durable evidence was incomplete.

The v3 attestation repair binds the fixture route to the frozen classification crossfit executor, its atomic state/checkpoint store, and its artifact manifest writer. It materializes the 128 sample-level OOF artifacts from the 512 target-level backend rows. It does not start formal OOF, formal regression, or formal training; it does not access sealed targets or solvers. Regression production dispatch remains unproven, and `FULL_TRAINER_IMPLEMENTATION_FROZEN=false`.

The durable synthetic attestation recorded four classifier fits, four calibrator fits, four threshold materializations, 128 exact-once sample predictions, artifact reload/replay validation, and failure/resume/drift rejection. These are fixture-only calls under a system temporary root and are not formal OOF calls.

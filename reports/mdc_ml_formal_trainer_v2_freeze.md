# MDC-ML Canonical Formal Executor V2 Refreeze

The prior `35089b3` freeze supplied interface guards and a synthetic harness, but the first formal preflight correctly stopped at H11 because it lacked a canonical loader, run-root allocator, persisted state initialization, and authorized production dispatch.

This refreeze adds read-only canonical input discovery and fingerprinting, scoped authorization, collision-safe formal-run allocation outside the worktree, persisted contract/state/manifest initialization, and plan/readiness dispatch for classification, regression, and future stages. Real canonical readiness reports 2640 classification rows, 837 regression rows, Round1 classification 128 split `[31,34,39,24]`, regression 100/28 split `[24,22,34,20]`, 150 features, and no sealed target loading.

No formal fit, prediction, formal output write, solver call, or sealed-test access was performed by this repair task. The prior H11 control root remains failure evidence only and is superseded for formal execution.

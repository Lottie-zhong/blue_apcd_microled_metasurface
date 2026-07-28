# MDC-ML Formal Merge-Retrain Execution Runner V2 Freeze

`FULL_TRAINER_IMPLEMENTATION_FROZEN=true`

This commit freezes formal-execution code and synthetic validation only. Formal classification OOF, formal regression OOF, final competition/retraining, sealed-test access, solver calls, official-output writes, promotion execution, and routing execution remain unstarted.

## Frozen execution contract

- One implementation head binds all future formal artifacts.
- Classification OOF, regression OOF, final classifier/regressor competition, calibration/threshold, target-wise conformal, OOF/validation comparison, paired-group bootstrap, promotion and route have named persisted artifact contracts.
- Regression conformal is target-wise, original-calibration-only, coverage 0.90 and alpha 0.10; no sweep is permitted.
- Formal entry points reject without separate authorization.

## Synthetic fixture evidence

`formal-v2-synthetic-freeze` passed. It ran the frozen synthetic classification and regression fixtures, wrote only TEMP artifacts, and recorded the implementation commit. Counts: formal classification OOF=0, formal regression OOF=0, formal training=0, sealed target/prediction=0, sealed evaluation count=1, and TMM/FDTD/Lumerical=0.

## Scope

No NP scope, formal input, formal output, joint MDC-NP model, or solver artifact was modified. The next phase remains separately authorized formal execution.

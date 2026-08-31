# IAR4 orientation-causal-control zero-solver gate

Status: **PASS**

This report audits existing IAR4 integrated truth and constructs a geometry-only angle-matched control. No FDTD, RCWA, ML, or new physics was run.

## Existing truth power audit

At 450 nm, IAR4 pair DoLP is `0.05357584` versus frozen I03 `0.03787684`; source cancellation C is `0.12712781` versus `0.08854257`; angular C is `0.10519643` versus `0.08612762`.
IAR4 upward source-normalized power / useful LP / useful LP over S0 are `7.39307247e-03` / `1.93828797` / `0.52678792`; I03 is `7.39292200e-03` / `1.89304003` / `0.51893842`.
Descriptive power assessment: **NO_OBVIOUS_POWER_COLLAPSE_IN_AVAILABLE_450NM_SOURCE_NORMALIZED_METRICS**. This is not a promotion threshold and uses no W_emit.
IAR4 has complete 400–500 nm wavelength rows. I03 source/linear pair rows are available on that grid, but frozen I03 upward power is anchor-only and frozen C_angular is only available at 440/450/460 nm; the audit preserves nulls rather than extrapolating.

## Angle-only control

IAR4 exact fixed geometry is L1/W1/L2/W2=`259/87/203/79` nm, D=`210` nm, H=`525.0` nm, Px=Py=`432.0` nm, delta_theta=`82.820909321` deg.
The exact I03-angle control test used delta_theta=`85.819861293` deg with all other IAR4 fields fixed. Its direct clearance is `62.390756888` nm and periodic-image clearance is `74.390756888` nm; validity is `True`.
Decision: **IAR4_ANGLE_ONLY_CAUSAL_CONTROL_FEASIBLE**; selection mode `EXACT_I03_ANGLE_MATCHED_CONTROL`.
Frozen matched control `IAR4-OC1` uses delta_theta=`85.819861293` deg, angle separation from IAR4=`2.998951972` deg, direct/periodic clearances=`62.390756888`/`74.390756888` nm, hash `03e4683c2f2b0a6fbf0cecb4ea8e15767623159ad91de7410a6bc8e8a117d228`. It remains unrun and is not an optical promotion.

## IAR-C2 fallback boundary

IAR-C2 exact authority is read from the conditional registry: L1/W1/L2/W2=`258/88/198/78` nm, D=`217` nm, delta_theta=`82.818204313` deg, direct/periodic=`69.901004908`/`67.901004908` nm.
IAR-C2 changes dimensions and D as well as angle; it can support an IAR4-like local basin interpretation only, never an orientation-only causal claim.

## Authority boundary

The inherited hard gates are direct polygon clearance >=60 nm, periodic-image polygon clearance >=60 nm, no overlap/touching, containment, integer lateral dimensions, and half-grid centers. No authoritative minimum linewidth/aspect-ratio gate beyond diagnostics was found; none was invented here.
The allowed interpretation remains `IAR4_LIKE_LOCAL_PERTURBATION_POSITIVE_INTEGRATED_RESPONSE`. `ORIENTATION_CAUSAL_LEVER` is not established until a future solver comparison of the matched control is authorized.

## Solver accounting

`NEW_FDTD_BUDGET=0`, `solver_run_called=false`, `solver_entered=0`, `FDTD=0`, `RCWA=0`, `ML=0`; DOE and physics contracts were unchanged.

See `existing_truth_power_audit.json`, `polygon_validity_audit.json`, `matched_angle_search.csv/json`, `causal_control_contract.json`, `provenance.json`, and `validation_tests.json` for machine-readable evidence.

# NP K6 HF Pilot Gate-0 N2 RUN1

## State

`NP_K6_HF_PILOT_GATE0_BLOCKED_BY_NUMERICAL_FIDELITY`

The six corrected Native-M1 sampled N2 setup contracts passed. The strict sequence stopped after the first RUN3C-x task failed the frozen full-band closure gate. No later task, rerun, attempt_002, sealed-test task, or formal HF dataset was created.

## Execution

| planned | entered | completed | early stop |
|---:|---:|---:|---|
| 6 | 1 | 1 | yes, after RUN3C-x |

RUN3C-x / attempt_001: entered=1, engine=1, controller=1, post-save=1, run_invocation_count=1. Post-FSP SHA256: `54f1e4a98f97f520501ecbfd73fd03b584b4a61d2ae38dc0255408ba6ea6d0f7`.

## Numerical gates

- 11 finite points, 445--455 nm.
- T range: `0.532070079`--`0.771106020`.
- R range: `0.225518993`--`0.386663296`.
- Maximum `|1-T-R|`: `0.081266625` at `448 nm`; threshold `0.02`, failed.
- 449 nm: T=`0.632657334`, R=`0.361551280`, residual=`0.005791386`, eta(+1)=`0.480561995`.
- 449 nm structure interval anomaly=`-0.004703843`; threshold `0.02`, passed.
- Maximum transmitted order-sum relative mismatch=`2.902e-16`, passed.
- Maximum raw/sourcepower/monitor mismatch=`3.775e-15`, passed using the documented time-averaged Poynting factor `0.5`.

N1-to-N2 observable convergence and six-case cross-grid equality were not evaluated because the first numerical hard gate failed. Intended N1/N2 nesting passed at setup level; production mesh remains unfrozen.

## HF database and isolation

Promoted tasks: 0; geometries: 0; polarizations: 0; spectral observations: 0; training labels: 0. Remaining development tasks: 90. Sealed-test tasks: 24, labels generated: 0. Formal HF dataset was not created.

Evidence root: `outputs\np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1\`.

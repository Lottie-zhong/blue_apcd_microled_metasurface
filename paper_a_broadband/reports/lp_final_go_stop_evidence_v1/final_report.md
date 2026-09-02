# Paper A LP final GO/STOP evidence

Status: `PASS` — zero-solver extraction from accepted existing truth only.

## 450 nm absolute performance

`upward_source_normalized_power_pair` is the retained source-normalized pair quantity; the full-angle counterpart is listed separately. No W_emit or historical Gaussian is used.

| candidate | pair DoLP | C_source | C_angular | full-angle DoLP | upward pair | full-angle upward | useful LP | P_LP/S0 | 5° | 10° | 20° |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| I03 | 0.03787684412 | 0.08854257162 | 0.08612761641 | 0.05403785552 | 0.007392922 | 5.232322043 | 1.893040032 | 0.5189384221 | 0.0742393939 | 0.4438686816 | 0.3158925065 |
| IAR4 | 0.05357583764 | 0.1271278143 | 0.1051964252 | 0.0668194266 | 0.007393072471 | 5.237341857 | 1.938287968 | 0.5267879188 | 0.1199539137 | 0.4808387336 | 0.3445746079 |
| IAR-C2 | 0.05600966932 | 0.1351456237 | 0.1123404162 | 0.07064290304 | 0.007415117794 | 5.24520928 | 1.930722227 | 0.5280048347 | 0.1565718812 | 0.3992607376 | 0.3077320511 |
| IAR-C2-OC80 | 0.06311605829 | 0.1577971783 | 0.1106318997 | 0.06982656554 | 0.007426853481 | 5.25455229 | 1.95027238 | 0.5315580291 | 0.2036899649 | 0.3795214904 | 0.2974723358 |

## 445–455 nm unweighted diagnostic window

This is not W_emit weighting.

| candidate | metric | mean | median | worst | best |
|---|---|---:|---:|---:|---:|
| IAR4 | DoLP | 0.04134047908 | 0.04024420579 | 0.02503349165 | 0.05827399383 |
| IAR4 | C_source | 0.1001476801 | 0.09452004974 | 0.07023450443 | 0.1467389749 |
| IAR4 | C_angular | 0.06585540105 | 0.056789504 | 0.02467219391 | 0.1051964252 |
| IAR4 | useful_LP | 1.9193223 | 1.938287968 | 1.609035518 | 2.192783077 |
| IAR4 | upward_source_normalized_power | 0.0074220625 | 0.007393072471 | 0.006586657698 | 0.008315761866 |
| IAR-C2 | DoLP | 0.04291165013 | 0.04426619849 | 0.01873949645 | 0.06487809997 |
| IAR-C2 | C_source | 0.1059210276 | 0.1017472087 | 0.05406579044 | 0.1680228288 |
| IAR-C2 | C_angular | 0.0681980876 | 0.06420746277 | 0.01362690203 | 0.1123404162 |
| IAR-C2 | useful_LP | 1.909319493 | 1.930722227 | 1.579581845 | 2.175547162 |
| IAR-C2 | upward_source_normalized_power | 0.007437564035 | 0.007415117794 | 0.006572374593 | 0.008328308419 |
| IAR-C2-OC80 | DoLP | 0.04998647071 | 0.05376165194 | 0.02311569222 | 0.06885600946 |
| IAR-C2-OC80 | C_source | 0.1268967357 | 0.1275476857 | 0.06854331966 | 0.1842292141 |
| IAR-C2-OC80 | C_angular | 0.07025700382 | 0.06984848264 | 0.01621316019 | 0.1106318997 |
| IAR-C2-OC80 | useful_LP | 1.929759769 | 1.95027238 | 1.597477456 | 2.196281947 |
| IAR-C2-OC80 | upward_source_normalized_power | 0.007456931241 | 0.007426853481 | 0.006602215466 | 0.008344909517 |

## Functional magnitude

OC80 remains in the low-DoLP regime; the 450 nm pair DoLP is 0.0631161. The change is a mechanism-level source-reinforcement correction, not a functionally strong integrated-LP transition. There is no throughput collapse in source-normalized upward power or useful LP.

## Mechanism maturity

The strict causal comparators are IAR4↔IAR4-OC1 and IAR-C2↔IAR-C2-OC80. Smaller-delta_theta preference for pair DoLP and C_source is reproduced at 450 nm across both matched controls; source reinforcement also agrees in the 445–455 nm means. Angular reinforcement is not consistent, so no global monotonic claim is made. Further local orientation scanning is not required solely to establish causality.

## Evidence for GO

- Matched causal effect reproduced at 450 nm in both controls.
- Source reinforcement is positive in both controls at 450 nm and in the blue-window means.
- No throughput collapse.
- No new orientation scan is needed for basic causal attribution.

## Evidence for STOP

- Absolute pair DoLP remains low (0.0535758 IAR4; 0.0560097 C2; 0.0631161 OC80 at 450 nm).
- Angular response is mixed and C_angular decreases from C2 to OC80 at 450 nm.
- No functionally strong integrated-LP transition is established.
- W_emit remains unresolved, preventing production emitter-weighted closure.

## Decision boundary

Final GO/STOP remains a Chart decision. The evidence is stronger for STOP on immediate LP promotion; no new solver or redesign is authorized by this task.

## Accounting

`NEW_FDTD_BUDGET=0`; `solver_run_called=false`; `solver_entered=0`; `RCWA=0`; `ML=0`. Existing truth was read only; no solver was started.

## Artifacts

- `absolute_performance_table.csv`
- `relative_gain_table.csv`
- `blue_window_summary.json`
- `mechanism_maturity.json`
- `go_stop_evidence.json`
- `provenance.json`
- `validation_tests.json`

# MDC P1 asymmetric scan static build v1

Static compilation only; no TMM, FDTD, solver, runtime, or performance metric was run/created.

## Direction and grammar

Canonical calculation direction: GaN -> stack -> Air. Reverse display is Air -> stack -> GaN only.

- Explicit: `(LH)^N_GaN / L_C / (HL)^N_Air`; C=156 nm, 13 physical layers, 900 nm total.
- ZL-1: the left-terminal L merges with inserted L^M into L_(M+1); no adjacent independent L layers remain.
- Nominal: M=3, L=78, added=234 nm, effective center=312 nm, 12 layers, 978 nm total.
- Alternative: M=3, L=79, added=237 nm, effective center=316 nm, 12 layers, 975 nm total. `C316` is a historical effective-center identity, not an added independent C layer.

## Counts

- 15 structures: 3 existing symmetric controls and 12 proposed novel asymmetric structures.
- Each seed has splits (1,5), (2,4), (3,3), (4,2), (5,1); total mirror pairs remain 6.
- Canonical sequence hashes and geometry hashes are unique; all symmetric control hash replays pass.

## Structures

|id|seed|split|layers|thickness nm|status|
|---|---|---|---:|---:|---|
|P1_EXPLICIT_FAB_G1_A5|explicit_fab|(1,5)|13|900|proposed_novel|
|P1_EXPLICIT_FAB_G2_A4|explicit_fab|(2,4)|13|900|proposed_novel|
|P1_EXPLICIT_FAB_G3_A3|explicit_fab|(3,3)|13|900|existing_canonical_control|
|P1_EXPLICIT_FAB_G4_A2|explicit_fab|(4,2)|13|900|proposed_novel|
|P1_EXPLICIT_FAB_G5_A1|explicit_fab|(5,1)|13|900|proposed_novel|
|P1_ZL1_NOMINAL_G1_A5|zl1_nominal|(1,5)|12|978|proposed_novel|
|P1_ZL1_NOMINAL_G2_A4|zl1_nominal|(2,4)|12|978|proposed_novel|
|P1_ZL1_NOMINAL_G3_A3|zl1_nominal|(3,3)|12|978|existing_canonical_control|
|P1_ZL1_NOMINAL_G4_A2|zl1_nominal|(4,2)|12|978|proposed_novel|
|P1_ZL1_NOMINAL_G5_A1|zl1_nominal|(5,1)|12|978|proposed_novel|
|P1_ZL1_ALTERNATIVE_G1_A5|zl1_alternative|(1,5)|12|975|proposed_novel|
|P1_ZL1_ALTERNATIVE_G2_A4|zl1_alternative|(2,4)|12|975|proposed_novel|
|P1_ZL1_ALTERNATIVE_G3_A3|zl1_alternative|(3,3)|12|975|existing_historical_reference_control|
|P1_ZL1_ALTERNATIVE_G4_A2|zl1_alternative|(4,2)|12|975|proposed_novel|
|P1_ZL1_ALTERNATIVE_G5_A1|zl1_alternative|(5,1)|12|975|proposed_novel|

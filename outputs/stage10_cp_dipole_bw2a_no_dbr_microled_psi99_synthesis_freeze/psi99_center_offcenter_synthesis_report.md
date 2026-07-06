# Stage10 CP BW2A PSI99 no-DBR center+offcenter synthesis freeze

## English technical summary

No FDTD was run for this synthesis. The package reads existing CSV/JSON summaries from the center spectral power audit and the off-center edge/power validation only.

The verified center-only PSI99 no-DBR CP-selection window is at least **420-480 nm** over the sampled range. At 20 deg, the center total cone-power maximum is **424 nm** with total power **1.129805e-10**. The center usable L_out power maximum is **422 nm** with usable L_out power **9.180541e-11**. The center CP-selectivity maximum is **420 nm** with L_fraction **0.817724**.

For off-center x-axis validation at 20 deg, all tested x_minus_q and x_plus_q cases remain L_out dominant. The highest off-center usable L_out power is **480.0 nm / x_plus_q** with usable L_out power **5.159875e-11**. The best retention relative to center is **480.0 nm**, with min off-center retention **0.69386**.

422 nm remains the center usable-power maximum, but it is **not** the best wavelength after off-center displacement because its x_plus_q retention is weak. 480 nm does **not** fail by CP selectivity; it remains robust and is currently the best off-center retention / usable-power reference.

Frozen wavelength roles:

- **422 nm**: center-power maximum / blue-side stress case.
- **453 nm**: project-center reference.
- **480 nm**: off-center robustness reference.
- **420 nm**: blue-edge selectivity reference.

Next simulation stage: stop no-DBR center/offcenter scouting. Wait for RCLED/source-module design, then run RCLED-coupled validation at 453 and 480 first, with 422/420 as stress checks.

## Cautions

- Do not claim full device bandwidth yet.
- Do not claim RCLED-coupled bandwidth yet.
- Current conclusion is for PSI99 no-DBR ordinary MicroLED, center and x-axis off-center positions only.
- No y-offset or full 2D source-position sweep was performed.
- No DBR, RCLED, or MQW-coupled validation was performed.

## ????

???? CSV/JSON/MD ????????? FDTD????????? FSP/LDF/runtime ???

PSI99 no-DBR ?? MicroLED ? center-only CP ?????????????? **420-480 nm**?20 deg ??center ? cone power ??? **424 nm**?center ?? L_out power ??? **422 nm**?center CP ?????? **420 nm**?

?? x_minus_q / x_plus_q ??????????? 20 deg ???? L_out ????????? L_out power ??? **480.0 nm / x_plus_q**??? center ??????????? **480.0 nm**?

???**422 nm ? center power ??????????????**?**480 nm ???? CP ?????????????????????**??????? no-DBR center/offcenter ??????? RCLED/source-module ??????? 453 nm ? 480 nm??? 422/420 nm ??????

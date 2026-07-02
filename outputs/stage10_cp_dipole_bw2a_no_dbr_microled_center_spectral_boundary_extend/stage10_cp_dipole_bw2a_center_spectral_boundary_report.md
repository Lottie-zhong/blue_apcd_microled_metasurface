# Stage10 CP BW2A PSI99 Center Spectral Boundary Extension

- Scope: PSI99 only, no-DBR ordinary MicroLED center dipole only.
- New wavelengths: 436, 438, 462, 464 nm.
- Reused existing center/boundary rows: 440, 442, 444, 446, 447, 448, 450, 453, 454, 455, 456, 458, 460 nm.
- No +/-q, no PSI97, no DBR/RCLED/MQW/mirror/spacer/full matrix.
- CP basis: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); L_out dominance means DoCP_RminusL < 0.
- Boundary pass threshold: 20 deg incoherent L_fraction >= 0.60.

## Combined 20 deg L_fraction

|wavelength_nm|value|data_source|
|---:|---:|---|
|436|0.76348|new_boundary_extend|
|438|0.758408|new_boundary_extend|
|440|0.75661|new_boundary_scout|
|442|0.754661|new_boundary_scout|
|444|0.750926|new_boundary_scout|
|446|0.750981|new_boundary_scout|
|447|0.751464|new_spectral_run|
|448|0.752449|new_spectral_run|
|450|0.754561|new_spectral_run|
|453|0.759234|reused_existing_453_data|
|454|0.760695|new_spectral_run|
|455|0.761842|new_boundary_scout|
|456|0.763261|new_boundary_scout|
|458|0.765744|new_boundary_scout|
|460|0.768006|new_boundary_scout|
|462|0.76886|new_boundary_extend|
|464|0.769236|new_boundary_extend|

## Combined 20 deg DoCP_RminusL

|wavelength_nm|value|data_source|
|---:|---:|---|
|436|-0.526959|new_boundary_extend|
|438|-0.516816|new_boundary_extend|
|440|-0.51322|new_boundary_scout|
|442|-0.509323|new_boundary_scout|
|444|-0.501851|new_boundary_scout|
|446|-0.501963|new_boundary_scout|
|447|-0.502928|new_spectral_run|
|448|-0.504899|new_spectral_run|
|450|-0.509123|new_spectral_run|
|453|-0.518468|reused_existing_453_data|
|454|-0.521391|new_spectral_run|
|455|-0.523684|new_boundary_scout|
|456|-0.526521|new_boundary_scout|
|458|-0.531488|new_boundary_scout|
|460|-0.536012|new_boundary_scout|
|462|-0.537719|new_boundary_extend|
|464|-0.538473|new_boundary_extend|

## Combined 20 deg total_cone_power

|wavelength_nm|value|data_source|
|---:|---:|---|
|436|1.09623e-10|new_boundary_extend|
|438|1.09506e-10|new_boundary_extend|
|440|1.08986e-10|new_boundary_scout|
|442|1.08605e-10|new_boundary_scout|
|444|1.08108e-10|new_boundary_scout|
|446|1.08376e-10|new_boundary_scout|
|447|1.08622e-10|new_spectral_run|
|448|1.11989e-10|new_spectral_run|
|450|1.11587e-10|new_spectral_run|
|453|1.10605e-10|reused_existing_453_data|
|454|1.10257e-10|new_spectral_run|
|455|1.06894e-10|new_boundary_scout|
|456|1.06466e-10|new_boundary_scout|
|458|1.05773e-10|new_boundary_scout|
|460|1.04687e-10|new_boundary_scout|
|462|1.05503e-10|new_boundary_extend|
|464|1.03859e-10|new_boundary_extend|

## Boundary Interpretation

- Preliminary blue-side pass boundary: at least down to 436 nm.
- Preliminary red-side pass boundary: at least up to 464 nm.
- Current 447-454 nm verified window can be expanded: yes.
- Lower-side extension scan recommended: yes, because 440 nm passes.
- Upper-side extension scan recommended: yes, because 460 nm passes.
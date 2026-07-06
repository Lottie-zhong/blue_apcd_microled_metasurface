# LP-ML0 Existing Data Audit

No FDTD was run. No Lumerical GUI was opened. This is a CSV/JSON/MD audit and schema freeze only.

Total unified candidate rows: 339

## Counts by H_nm
```json
{
  "500": 176,
  "500.000000": 21,
  "600": 110,
  "650": 24,
  "700": 8
}
```
## Counts by target_bin_deg
```json
{
  "0": 20,
  "120": 31,
  "180": 20,
  "240": 103,
  "300": 119,
  "60": 21,
  "unknown": 25
}
```
## Counts by pass level
```json
{
  "fail": 119,
  "loose": 4,
  "loose_near_miss": 1,
  "strict": 20,
  "unknown": 195
}
```
## H500 450 nm Single-Point Seed Library
| target_bin_deg | candidate_id | strict_or_loose_or_fail | conversion_to_leakage_ratio | Tx | phase_error_deg | matrix_error | library_role | robust_451_453_ready | direct_k6_ready |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | H500DIMER2C_029 | strict | 812.0 | 1.016 | 3.24 |  | 450nm_single_point_seed_only | false | false |
| 60 | H500DIMER2B_006 | strict | 258.74 | 0.93 | 6.01 |  | 450nm_single_point_seed_only | false | false |
| 120 | H500DIMER2C_004 | loose | 4.5 | 0.506 |  | 0.471 | 450nm_single_point_seed_only | false | false |
| 180 | H500DIMER2C_026 | strict | 16.27 | 0.934 |  |  | 450nm_single_point_seed_only | false | false |
| 240 | H500DIMER2D_018 | loose_near_miss | 6.33 | 0.784 | 15.788 |  | 450nm_single_point_seed_only | false | false |
| 300 | H500DIMER2D_006 | strict | 13.46 | 0.987 |  |  | 450nm_single_point_seed_only | false | false |
## B240 Diagnosis
| candidate_id | target_bin_deg | phase_error_deg | Tx | conversion_to_leakage_ratio | matrix_error | diagnosis_bucket |
| --- | --- | --- | --- | --- | --- | --- |
| H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 240 |  |  |  |  | b240_candidates:no_overlap_evidence |
| H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 240 |  | 0.909409 | 11.271773 | 0.297861 | b240_candidates:projector_good_phase_wrong |
| H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 240 |  | 0.909409 | 11.271773 | 0.297861 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_001_B240_x_pair_swap_G90_O-28 | 240 |  | 0.909409 | 11.271773 | 0.297861 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_004_B240_x_pair_swap_G90_O-30 | 240 |  | 0.924435 | 11.575897 | 0.293924 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_005_B240_x_pair_swap_G90_O-26 | 240 |  | 0.891867 | 10.883725 | 0.303125 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_004_B240_x_pair_swap_G90_O-30 | 240 |  | 0.433866 | 4.201513 | 0.487862 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_005_B240_x_pair_swap_G90_O-26 | 240 |  | 0.391807 | 3.778578 | 0.514442 | b240_candidates:no_overlap_evidence |
| H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 240 |  | 0.388795 | 3.759887 | 0.515718 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_001_B240_x_pair_swap_G90_O-28 | 240 |  | 0.388795 | 3.759887 | 0.515718 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_004_B240_x_pair_swap_G90_O-30 | 240 |  |  |  |  | b240_candidates:no_overlap_evidence |
| H500DIMER12A_005_B240_x_pair_swap_G90_O-26 | 240 |  |  |  |  | b240_candidates:no_overlap_evidence |
| H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 240 |  |  |  |  | b240_candidates:no_overlap_evidence |
| H500DIMER12A_001_B240_x_pair_swap_G90_O-28 | 240 |  |  |  |  | b240_candidates:no_overlap_evidence |
| H500DIMER12A_004_B240_x_pair_swap_G90_O-30 | 240 |  | 0.433866 | 4.201513 | 0.487862 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_005_B240_x_pair_swap_G90_O-26 | 240 |  | 0.391807 | 3.778578 | 0.514442 | b240_candidates:no_overlap_evidence |
| H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 240 |  | 0.388795 | 3.759887 | 0.515718 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_001_B240_x_pair_swap_G90_O-28 | 240 |  | 0.388795 | 3.759887 | 0.515718 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_002_B240_x_pair_swap_G85_O-28 | 240 |  | 0.890712 | 10.902810 | 0.302855 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_002_B240_x_pair_swap_G85_O-28 | 240 |  | 0.760663 | 7.974163 | 0.354135 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_002_B240_x_pair_swap_G85_O-28 | 240 |  | 0.433359 | 4.220184 | 0.486784 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_003_B240_x_pair_swap_G95_O-28 | 240 |  | 0.920005 | 10.897709 | 0.302943 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_003_B240_x_pair_swap_G95_O-28 | 240 |  | 0.740069 | 7.522228 | 0.364610 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_003_B240_x_pair_swap_G95_O-28 | 240 |  | 0.415128 | 3.853636 | 0.509410 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_006_B240_x_pair_swap_G80_O-28 | 240 |  | 0.862008 | 9.452898 | 0.325259 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_006_B240_x_pair_swap_G80_O-28 | 240 |  | 0.744654 | 7.785388 | 0.358407 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_006_B240_x_pair_swap_G80_O-28 | 240 |  | 0.436834 | 4.246788 | 0.485257 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_007_B240_x_pair_swap_G100_O-28 | 240 |  | 0.926186 | 10.733088 | 0.305243 | b240_candidates:projector_good_phase_wrong |
| H500DIMER12A_007_B240_x_pair_swap_G100_O-28 | 240 |  | 0.682515 | 6.860554 | 0.381790 | b240_candidates:no_overlap_evidence |
| H500DIMER12A_007_B240_x_pair_swap_G100_O-28 | 240 |  | 0.359517 | 3.376517 | 0.544210 | b240_candidates:no_overlap_evidence |
## B300 Diagnosis
| candidate_id | target_bin_deg | phase_error_deg | Tx | conversion_to_leakage_ratio | matrix_error | diagnosis_bucket |
| --- | --- | --- | --- | --- | --- | --- |
| H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 300 |  |  |  |  | b300_candidates:no_overlap_evidence |
| H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 300 |  | 0.972728 | 70.267809 | 0.119294 | b300_candidates:projector_good_phase_wrong |
| H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 300 |  | 0.972728 | 70.267809 | 0.119294 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_001_B300_x_pair_swap_G70_O-30 | 300 |  | 0.956686 | 97.179138 | 0.101443 | b300_candidates:projector_good_phase_wrong |
| H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 300 |  | 0.972728 | 3.845420 | 0.509951 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_001_B300_x_pair_swap_G70_O-30 | 300 |  | 0.956686 | 3.523155 | 0.532763 | b300_candidates:no_overlap_evidence |
| H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 300 |  |  |  |  | b300_candidates:no_overlap_evidence |
| H500DIMER12D_001_B300_x_pair_swap_G70_O-30 | 300 |  |  |  |  | b300_candidates:no_overlap_evidence |
| H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 300 |  | 0.972728 | 3.845420 | 0.509951 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_001_B300_x_pair_swap_G70_O-30 | 300 |  | 0.956686 | 3.523155 | 0.532763 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_002_B300_x_pair_swap_G80_O-30 | 300 |  | 0.972728 | 70.267809 | 0.119294 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_002_B300_x_pair_swap_G80_O-30 | 300 |  | 0.987489 | 13.460022 | 0.272570 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_002_B300_x_pair_swap_G80_O-30 | 300 |  | 1.002055 | 3.845420 | 0.509951 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | 300 |  | 1.006287 | 71.048907 | 0.118636 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | 300 |  | 0.986508 | 18.055529 | 0.235339 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | 300 |  | 1.002041 | 4.507269 | 0.471025 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_004_B300_x_pair_swap_G80_O-40 | 300 |  | 0.992986 | 40.736321 | 0.156679 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_004_B300_x_pair_swap_G80_O-40 | 300 |  | 1.005218 | 23.484862 | 0.206351 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_004_B300_x_pair_swap_G80_O-40 | 300 |  | 0.980281 | 4.467450 | 0.473118 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_005_B300_x_pair_swap_G80_O-20 | 300 |  | 0.978161 | 1001.399288 | 0.031604 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_005_B300_x_pair_swap_G80_O-20 | 300 |  | 0.992870 | 12.513692 | 0.282688 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_005_B300_x_pair_swap_G80_O-20 | 300 |  | 0.998208 | 3.230742 | 0.556351 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_006_B300_x_pair_noswap_G80_O-30 | 300 |  | 0.975489 | 29.809825 | 0.183156 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_006_B300_x_pair_noswap_G80_O-30 | 300 |  | 0.995819 | 20.752870 | 0.219514 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_006_B300_x_pair_noswap_G80_O-30 | 300 |  | 0.986911 | 4.531912 | 0.469742 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_007_B300_x_pair_noswap_G100_O-24 | 300 |  | 0.975170 | 145.029548 | 0.083037 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_007_B300_x_pair_noswap_G100_O-24 | 300 |  | 1.002368 | 13.275763 | 0.274455 | b300_candidates:projector_good_phase_wrong |
| H500DIMER12D_007_B300_x_pair_noswap_G100_O-24 | 300 |  | 0.995356 | 3.724836 | 0.518140 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_008_B300_y_pair_swap_G80_O-30 | 300 |  | 0.419077 | 0.421363 | 1.541319 | b300_candidates:no_overlap_evidence |
| H500DIMER12D_008_B300_y_pair_swap_G80_O-30 | 300 |  | 0.618374 | 0.626199 | 1.264278 | b300_candidates:no_overlap_evidence |
## B300 Failure Interpretation
B300 shows phase/projector decoupling evidence when high-selectivity rows are far from the B300 phase target.
## Recommended LP-ML1 Sampling Focus
Start with a small supervised data schema around projector-good/phase-wrong and phase-near/projector-bad B240/B300 examples. Learn geometry to complex Jones matrix over wavelength before any inverse geometry network.

Boundary: the H500 seed library is 450 nm single-point only, not robust over 451-453 nm and not direct K=6 ready.

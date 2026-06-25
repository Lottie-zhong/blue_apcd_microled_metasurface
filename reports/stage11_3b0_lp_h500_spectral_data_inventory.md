# Stage11-3B0 LP H500 Spectral Data Inventory

## Scope
- Repo root inspected: `D:\project\blue_apcd_microled_metasurface`
- Tracked lightweight files inspected: 189
- Files/directories searched: reports, docs, scripts, tests, tracked lightweight *.csv/*.json/*.md/*.py outside excluded paths
- Files/directories intentionally excluded: outputs/, *.fsp, *.ldf, *.log, *monitor*, *farfield*, *far_field*, *fielddump*, *dump*
- `outputs/` was not read or written in this Stage11-3B0 inventory.

## Frozen Six-bin Candidate Inventory
| phase_bin_deg | candidate_id | available_wavelengths_nm | missing_449_450_451_nm | missing_448_449_450_451_452_nm | source_files | status |
|---|---|---|---|---|---|---|
| 0 | H500DIMER2C_029_B240_x_pair_noswap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 60 | H500DIMER2B_006_B180_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 120 | H500DIMER2C_004_B120_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md; scripts/stage11_lp_apcd_audit_h500_120_y_pair_micro_rescue_stage11_2h.py; scripts/stage11_lp_apcd_audit_h500_dimer_120_240_refine_stage11_2f.py; scripts/stage11_lp_apcd_diagnose_h500_120_selectivity_stage11_2g.py | only 450 nm single-point data exists |
| 180 | H500DIMER2C_026_B240_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 240 | H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md; src/metasurface/stage12_10a_240bin_refinement.py; src/metasurface/stage12_11a_phase_origin_search.py; tests/test_stage12_0_k6_analytic.py; tests/test_stage12_1_k6_layout.py | only 450 nm single-point data exists |
| 300 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |

## Available Wavelength Table
| phase_bin_deg | candidate_id | available_wavelengths_nm | missing_449_450_451_nm | missing_448_449_450_451_452_nm | source_files | status |
|---|---|---|---|---|---|---|
| 0 | H500DIMER2C_029_B240_x_pair_noswap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 60 | H500DIMER2B_006_B180_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 120 | H500DIMER2C_004_B120_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md; scripts/stage11_lp_apcd_audit_h500_120_y_pair_micro_rescue_stage11_2h.py; scripts/stage11_lp_apcd_audit_h500_dimer_120_240_refine_stage11_2f.py; scripts/stage11_lp_apcd_diagnose_h500_120_selectivity_stage11_2g.py | only 450 nm single-point data exists |
| 180 | H500DIMER2C_026_B240_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 240 | H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md; src/metasurface/stage12_10a_240bin_refinement.py; src/metasurface/stage12_11a_phase_origin_search.py; tests/test_stage12_0_k6_analytic.py; tests/test_stage12_1_k6_layout.py | only 450 nm single-point data exists |
| 300 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |

## Missing Wavelength Table
| phase_bin_deg | candidate_id | available_wavelengths_nm | missing_449_450_451_nm | missing_448_449_450_451_452_nm | source_files | status |
|---|---|---|---|---|---|---|
| 0 | H500DIMER2C_029_B240_x_pair_noswap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 60 | H500DIMER2B_006_B180_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 120 | H500DIMER2C_004_B120_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md; scripts/stage11_lp_apcd_audit_h500_120_y_pair_micro_rescue_stage11_2h.py; scripts/stage11_lp_apcd_audit_h500_dimer_120_240_refine_stage11_2f.py; scripts/stage11_lp_apcd_diagnose_h500_120_selectivity_stage11_2g.py | only 450 nm single-point data exists |
| 180 | H500DIMER2C_026_B240_x_pair_swap_G60_O-20 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |
| 240 | H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md; src/metasurface/stage12_10a_240bin_refinement.py; src/metasurface/stage12_11a_phase_origin_search.py; tests/test_stage12_0_k6_analytic.py; tests/test_stage12_1_k6_layout.py | only 450 nm single-point data exists |
| 300 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | 450 | 449;451 | 448;449;451;452 | reports/stage11_lp_apcd_status_summary.md | only 450 nm single-point data exists |

## Minimal Rerun Plan
- First pass: periodic plane-wave Jones extraction at 449, 450, 451 nm.
- Second pass if needed: add 448 and 452 nm.
- Extended pass only after first-pass review: add 447 and 453 nm, or 450-456 nm if a deliberate long-wavelength-tail check is needed.

## Conclusion
Only single-wavelength 450 nm LP H500 data is available; true narrow-spectrum robustness cannot be concluded yet.

No FDTD was run, no `.fsp`/`.ldf` files were created, and no K=6/metagrating work was touched.

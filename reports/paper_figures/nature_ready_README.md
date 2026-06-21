# Nature-ready figures from existing results

All panels were generated from existing CSV/Markdown results. No FDTD was run and no Lumerical solver was opened.

## Generated figures

### Fig. 2 - APCD six-state phase-library metrics

Files: `fig2_phase_library_metrics.jpg`, `fig2_phase_library_metrics.pdf`, `fig2_phase_library_metrics.svg`

Sources:
- `red_archive/outputs/apcd_k6_metagrating_633nm/archive_mixed_height_k6_p179_p183_20260608_193423/outputs__apcd_k6_active_learning__p179_stage10_frozen_phase_library.csv`

### Fig. 3 - APCD K=6 phase-ramp supercell summary

Files: `fig3_k6_phase_ramp_summary.jpg`, `fig3_k6_phase_ramp_summary.pdf`, `fig3_k6_phase_ramp_summary.svg`

Sources:
- `red_archive/outputs/apcd_k6_metagrating_633nm/archive_mixed_height_k6_p179_p183_20260608_193423/outputs__apcd_k6_active_learning__p180_k6_phase_ramp_supercell_plan.csv`
- `red_archive/outputs/apcd_k6_metagrating_633nm/archive_mixed_height_k6_p179_p183_20260608_193423/outputs__apcd_k6_active_learning__p181_k6_supercell_geometry_plan.csv`

### Fig. 4 - APCD K=6 scalar grating orders

Files: `fig4_k6_scalar_grating_orders.jpg`, `fig4_k6_scalar_grating_orders.pdf`, `fig4_k6_scalar_grating_orders.svg`

Sources:
- `red_archive/outputs/apcd_k6_metagrating_633nm/archive_mixed_height_k6_p179_p183_20260608_193423/outputs__apcd_k6_metagrating_633nm__p182c_p181_phase_ramp_substrate_incidence_setup_only__p183_p182c_grating_orders.csv`
- `red_archive/outputs/apcd_k6_metagrating_633nm/archive_mixed_height_k6_p179_p183_20260608_193423/outputs__apcd_k6_metagrating_633nm__p182c_p181_phase_ramp_substrate_incidence_setup_only__p183_p182c_grating_order_summary.md`

### Fig. 5 - PB N=6 blue reference (not APCD)

Files: `fig5_pb_n6_blue_reference.jpg`, `fig5_pb_n6_blue_reference.pdf`, `fig5_pb_n6_blue_reference.svg`

Sources:
- `red_archive/outputs/pb_supercell_N6_refine_LW_H450/pb_sweep_summary.csv`
- `red_archive/outputs/pb_supercell_N6_L210_W70_H_sweep/PB_N6_CASE_REDACTED/PB_N6_CASE_REDACTED_lcp_order_spectrum.csv`
- `red_archive/outputs/pb_supercell_N6_L210_W70_H_sweep/PB_N6_CASE_REDACTED/PB_N6_CASE_REDACTED_rcp_order_spectrum.csv`

### Fig. 6 - CP dipole-position robustness

Files: `fig6_cp_position_robustness.jpg`, `fig6_cp_position_robustness.pdf`, `fig6_cp_position_robustness.svg`

Sources:
- `blue_repo/outputs/blue_stage10_cp_zprop_validation/five_position_sweep/five_position_position_averages.csv`

## Metric definitions

- `target_conversion`: power fraction in the intended converted-spin channel for a selected single-dimer state.
- `opposite_spin_leakage`: power fraction in the undesired opposite-spin leakage channel.
- `conversion_to_leakage_ratio`: target conversion divided by opposite-spin leakage.
- `phase_error`: wrapped absolute phase difference between extracted phase and target phase state.
- `grating_value`: scalar/default normalized grating-order value from the existing extraction.
- `eta_order_source_norm`: approximate source-normalized order efficiency, calculated as `grating_value x transmission_monitor_value`.

## Anonymization

Candidate identifiers, exact geometry, and server paths are hidden from figure panels.

- Structure A = 0 deg state
- Structure B = 60 deg state
- Structure C = 120 deg state
- Structure D = 180 deg state
- Structure E = 240 deg state
- Structure F = 300 deg state

## Interpretation boundaries

- Mixed-height APCD K=6 proof-of-concept; not a final single-height fabrication library.
- This is scalar/default grating-order extraction only; it is not order-resolved APCD alpha/beta polarization-channel extraction.
- The +15 deg scalar order exists but is not the dominant scalar order; no verified APCD steering claim is made.
- PB N=6 blue reference is not APCD.
- CP dipole-position robustness, when present, is a separate blue-reference dataset and is not evidence for APCD K=6 steering.
- No FDTD was run.

## Figure contract and QA

- Backend: Python/matplotlib only.
- Archetypes: quantitative grids and a schematic-led composite.
- Export: editable-text SVG/PDF and 600 dpi or higher JPG.
- Image integrity: plots reproduce tabulated values; no interpolation or synthetic values were introduced.
- Review risk: scalar diffraction data cannot establish order-resolved APCD polarization selectivity without a Jones-basis extraction.

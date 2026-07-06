# LP-ML1A Seed Manifest Dry-Run

Purpose: generate a seed full-wave candidate manifest and geometry legality dry-run for future LP-ML1B data generation.

Baseline: LP-ML0 pushed at 604c38b Stage LP-ML0 existing data audit and schema freeze.

Input files used:
- outputs/lp_ml0_existing_data_audit/lp_hnew_all_candidates_unified.csv
- outputs/lp_ml0_existing_data_audit/lp_hnew_b240_b300_diagnosis.csv
- outputs/lp_ml0_existing_data_audit/lp_h500_450nm_single_point_seed_library.csv
- outputs/lp_ml0_existing_data_audit/lp_ml0_audit_summary.json

Generated candidates: 600
Rejected/source-metadata-only records: 600

## Count by target bin
```json
{
  "0": 15,
  "120": 15,
  "180": 15,
  "240": 245,
  "300": 295,
  "60": 15
}
```
## Count by sampling group
```json
{
  "B240_focused": 180,
  "B300_focused": 240,
  "H500_450nm_seed_robustification": 90,
  "global_escape": 90
}
```
## Count by H_nm
```json
{
  "500": 338,
  "600": 188,
  "650": 67,
  "700": 7
}
```
## Count by source diagnosis category
```json
{
  "b240_candidates:no_overlap_evidence": 36,
  "b240_candidates:phase_near_projector_bad": 12,
  "b240_candidates:projector_good_phase_wrong": 182,
  "b300_candidates:no_overlap_evidence": 25,
  "b300_candidates:projector_good_phase_wrong": 255,
  "loose": 15,
  "loose_near_miss": 15,
  "strict": 60
}
```
## Geometry Missingness Summary
LP-ML0 source rows have sparse L/W/theta fields. Rows with missing source geometry were used as metadata anchors only; project_default geometry ranges were used explicitly and documented in reports/lp_ml1a_geometry_rules.yaml.

## Top 20 Highest-Priority Candidates
| candidate_id | target_bin_deg | sampling_group | H_nm | source_candidate_id | source_diagnosis_category | priority_score |
| --- | --- | --- | --- | --- | --- | --- |
| LPML1A_0001_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0002_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0003_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_001_B300_x_pair_swap_G70_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0004_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_002_B300_x_pair_swap_G80_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0005_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_002_B300_x_pair_swap_G80_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0006_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0007_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0008_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_004_B300_x_pair_swap_G80_O-40 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0009_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_004_B300_x_pair_swap_G80_O-40 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0010_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_005_B300_x_pair_swap_G80_O-20 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0011_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_005_B300_x_pair_swap_G80_O-20 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0012_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_006_B300_x_pair_noswap_G80_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0013_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_006_B300_x_pair_noswap_G80_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0014_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_007_B300_x_pair_noswap_G100_O-24 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0015_B300_focused_B300_H500 | 300 | B300_focused | 500 | H500DIMER12D_007_B300_x_pair_noswap_G100_O-24 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0016_B300_focused_B300_H500 | 300 | B300_focused | 500 | H600_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0017_B300_focused_B300_H500 | 300 | B300_focused | 500 | H600_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0018_B300_focused_B300_H500 | 300 | B300_focused | 500 | H600_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0019_B300_focused_B300_H500 | 300 | B300_focused | 500 | H600_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30 | b300_candidates:projector_good_phase_wrong | 440 |
| LPML1A_0020_B300_focused_B300_H500 | 300 | B300_focused | 500 | H600B300PULL_001_FROM_H500DIMER12D_002_B300_x_pair_swap_G80_O-30 | b300_candidates:projector_good_phase_wrong | 440 |

## Why B300 Receives More Samples Than B240
B300 is the unresolved phase/projector decoupling bottleneck, so it receives 240 candidates. B240 has partial loose evidence and receives 180 focused candidates.

## Priority Score
base(B300=400, B240=300, H500 seed=200, global=100) + source bonuses for projector-good/phase-wrong or phase-near evidence - fabrication-edge and duplicate penalties.

No FDTD was run.
No Lumerical GUI was opened.
No model was trained.
No K=6 was attempted.

Next recommended step: LP-ML1B full-wave runner planning, not execution.

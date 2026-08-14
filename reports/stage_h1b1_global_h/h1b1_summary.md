# Stage H1B-1 Targeted Full-Dimer Expansion

- Status: `COMPLETE_ANALYSIS`
- Verdict: `H1B1_TARGETED_EXPANSION_IMPROVED_BUT_BELOW_60`
- Route recommendation: `MINIMAL_FULL_DIMER_REFINEMENT_OR_CONSTITUENT_DIAGNOSTIC`
- Branch / HEAD: `work/lp-global-h-manifold-v1` / `c5b41876a21675884a9715bd3a96a15a7c036b58`
- Planned / entered / accepted: `10` / `10` / `10`

## Frozen contract

- H_global = J1_H = J2_H = 550 nm; x+y only; period 432 nm; native material APCD_TIO2_NATIVE_M1.
- H500 is authoritative control only and was not scheduled.
- Full Jones uses the existing weighted full-period complex G0 extraction and does not assume txy=tyx.

## H550 comparison

- Old H1A compatible span: `30.096722115615` deg
- Merged raw span: `44.471233680899` deg
- Merged compatible count / span: `6` / `40.347422746576` deg
- Delta compatible span: `10.250700630961` deg
- Max compatible pair / sector gap: `40.347422746576` / `19.652577253424` deg

## Flags

- FLAG_60_SECTOR: `False`
- FLAG_120_ML_RESTART: `False`; not an automatic ML start.

## Candidate effects

- H1B1_A_LOWER_COMPATIBLE_EDGE: phi=66.617866824 deg, projector_error=0.08444499745689715, compatible=True, lower_extension=True, upper_extension=False
- H1B1_B_UPPER_COMPATIBLE_EDGE: phi=85.694289983 deg, projector_error=0.2679099903284172, compatible=False, lower_extension=False, upper_extension=False
- H1B1_C_J1_SIDE_CONTRAST: phi=73.659238415 deg, projector_error=0.3918309450529901, compatible=False, lower_extension=True, upper_extension=False
- H1B1_D_D_PSI_CONTRAST: phi=83.911141372 deg, projector_error=0.10393534540257765, compatible=True, lower_extension=False, upper_extension=False
- H1B1_E_INTERIOR_PROJECTOR_CONTROL: phi=72.868281992 deg, projector_error=0.16488077862258887, compatible=True, lower_extension=True, upper_extension=False

## Artifacts

- candidate_manifest: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_candidate_manifest.json`
- solver_accounting: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_solver_accounting.json`
- full_jones: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_full_jones.csv`
- phase_only: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_phase_only.csv`
- merged_manifold: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_h550_merged_manifold.csv`
- candidate_effects: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_candidate_effects.csv`
- span_comparison: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_span_comparison.json`
- final: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_final.json`
- summary: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b1\h1b1_summary.md`

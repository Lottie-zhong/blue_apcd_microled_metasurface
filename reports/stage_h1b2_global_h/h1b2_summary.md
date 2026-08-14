# Stage H1B-2 Second-Generation H550 Compatible-Edge Continuation

- Status: `COMPLETE_ANALYSIS`
- Verdict: `H1B2_CONTINUED_IMPROVEMENT_BELOW_60`
- Route recommendation: `RETURN_TO_CHART_FOR_FINAL_EDGE_REFINEMENT_DECISION`
- Branch / HEAD: `work/lp-global-h-manifold-v1` / `9b64fbcc2f2488e7faf65de98ae99ac50695b41a`
- Planned / entered / accepted: `10` / `10` / `10`

## Frozen contract

- H_global = J1_H = J2_H = 550 nm; x+y formal runs; period 432 nm; APCD_TIO2_NATIVE_M1.
- Full Jones is the transmission-side coordinate-weighted complex G0 with endpoint deduplication, periodic reclosure and existing normalization.
- H500 was not scheduled or replayed.

## Circular edge decomposition

- Old H1B-1 compatible arc: `66.617866824188 -> 106.965289570764` deg; span `40.347422746576` deg.
- New compatible arc: `66.617866824188 -> 114.818324908441` deg; span `48.200458084253` deg.
- Lower / upper extension: `0.000000000000` / `7.853035337677` deg.
- Single-point dominated: `True`.

## Candidate effects

- H1B2_A_A_EDGE_CONTINUATION: phi=75.06850204805193, projector_error=0.4155187850548283, margin=-0.22902264804638572, Txx=0.9140869041710988, compatible=False, lower_extremum=False, upper_extremum=False
- H1B2_B_A_EDGE_CONSERVATIVE_CONTINUATION: phi=74.5591336298285, projector_error=0.35950225232322386, margin=-0.17300611531478127, Txx=0.277126708496372, compatible=False, lower_extremum=False, upper_extremum=False
- H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION: phi=114.81832490844113, projector_error=0.17425118141458695, margin=0.012244955593855633, Txx=0.9480295104147646, compatible=True, lower_extremum=False, upper_extremum=True
- H1B2_D_A_DIRECTION_J1_CONTRAST: phi=94.09613112567246, projector_error=0.4005667657623553, margin=-0.2140706287539127, Txx=0.6601226679549844, compatible=False, lower_extremum=False, upper_extremum=False
- H1B2_E_INTERIOR_PROJECTOR_CONTROL: phi=40.297497908740894, projector_error=0.6355533080613014, margin=-0.4490571710528588, Txx=0.5634318192226787, compatible=False, lower_extremum=False, upper_extremum=False

## Artifacts

- candidate_selection_audit: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_candidate_selection_audit.json`
- candidate_manifest: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_candidate_manifest.json`
- solver_accounting: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_solver_accounting.json`
- full_jones: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_full_jones.csv`
- merged_manifold: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_merged_h550_manifold.csv`
- edge_decomposition: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_edge_decomposition.json`
- candidate_effects: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_candidate_effects.csv`
- span_comparison: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_span_comparison.json`
- final: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_final.json`
- summary: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\outputs\lp_global_h_h1b2\h1b2_summary.md`

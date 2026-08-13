# Stage H1A — Repeated-Anchor Global-H Sensitivity Probe

- Status: `COMPLETE_ANALYSIS`
- Verdict: `H1A_GEOMETRY_DEPENDENT_H_RESPONSE_OBSERVED`
- Branch / HEAD: `work/lp-global-h-manifold-v1` / `31b2fab21d6ee370f92944b55bdd6f9843de4971`
- Unique anchors: `6`
- Solver budget planned / entered / accepted / quarantined: `48` / `48` / `48` / `0`

## Frozen contract

- H grid: `400, 450, 500, 550, 600 nm`; only 400/450/550/600 were scheduled.
- H500 reuses H0 authoritative data and is never rerun.
- J1_H = J2_H = H_global; bottom z=0 nm; source z=-250 nm; monitor z=1000 nm; period=432 nm; material=APCD_TIO2_NATIVE_M1.

## Fixed-H summary

- H=400 nm: full-Jones=6, phase-only=6, all-anchor span=39.312615 deg, projector-compatible span=14.118944 deg
- H=450 nm: full-Jones=6, phase-only=6, all-anchor span=39.147748 deg, projector-compatible span=12.916021 deg
- H=500 nm: full-Jones=6, phase-only=6, all-anchor span=44.844206 deg, projector-compatible span=17.564728 deg
- H=550 nm: full-Jones=6, phase-only=6, all-anchor span=41.738882 deg, projector-compatible span=30.096722 deg
- H=600 nm: full-Jones=6, phase-only=6, all-anchor span=26.239342 deg, projector-compatible span=5.505242 deg

## Common-translation residuals

- H=400 nm: C(H)=342.50239170054107, RMS=2.727327153605168, max|r|=4.6256437732411655
- H=450 nm: C(H)=352.2794252781733, RMS=2.5585121945920566, max|r|=4.6434941398048295
- H=500 nm: C(H)=0.0, RMS=0.0, max|r|=0.0
- H=550 nm: C(H)=0.1693747837378304, RMS=8.610431905814359, max|r|=15.288115306595301
- H=600 nm: C(H)=347.85429910326434, RMS=17.152480156154944, max|r|=35.45188973052677

## Flags

- FLAG_60_SECTOR: `False`
- FLAG_120_ML_RESTART: `False`; not an automatic ML start.
- Projector collapse observed: `False`

## Scope-separated references

- H500 dedicated-probe reference: `18.557501177497556` deg.
- H500 historical quantile/reference slice: `27.845019017638` deg.

## Artifacts

- complete_jones_table: `outputs\lp_global_h_h1a\complete_jones_table.csv`
- phase_only_table: `outputs\lp_global_h_h1a\phase_only_table.csv`
- per_anchor_phi_vs_H: `outputs\lp_global_h_h1a\per_anchor_phi_vs_H.csv`
- fixed_H_span_summary: `outputs\lp_global_h_h1a\fixed_H_span_summary.csv`
- H_geometry_interaction_summary: `outputs\lp_global_h_h1a\H_geometry_interaction_summary.csv`
- quarantine_rejection_table: `outputs\lp_global_h_h1a\quarantine_rejection_table.csv`

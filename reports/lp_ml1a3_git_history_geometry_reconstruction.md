# LP-ML1A3 Git History Geometry Reconstruction

Purpose: recover LP dimer numeric geometry from git history and original generator scripts before any LP-ML1B full-wave run.

LP-ML1B is blocked because LP-ML1A2 found zero run-ready source candidates and LP-ML1A rows are default-range-only scaffold rows.

Git-history search method: git log --all --name-only indexed lightweight historical files; current indexed files were grepped for exact candidate IDs and accepted only if the same line contained complete numeric geometry. No checkout was performed.

Unique target IDs searched: 66
Commits scanned: 169
Files scanned: 1331
Recovered exact_candidate_csv_json count: 0
Recovered exact_candidate_script_dict count: 0
Recovered exact_candidate_lsf_assignment count: 0
Recovered generator_rule_candidate_specific count: 0
Unresolved count: 66
Conflicting evidence count: 0
Run-ready count: 0

## Recovered count by H_nm
```json
{}
```
## Recovered count by target_bin_deg
```json
{}
```
## Top recovered B300 sources
No rows.

## Top recovered B240 sources
No rows.

No FDTD was run.
No Lumerical GUI was opened.
No model was trained.
No K=6 was attempted.
# R2-4C Variable DBR Setup-Only FSP Package

Generated setup-only 2D FDTD models for the top 5 R2-4B variable-thickness DBR candidates and the valid MQW dipole pair.

- Lumerical/lumapi was launched only to build layout and save FSP files.
- FDTD solve was not run.
- No `run`, `runanalysis`, far-field calculation, `.ldf`, or raw monitor export was performed.
- Runtime FSP count: 10 / 10.
- Valid dipoles: `center_x` and `center_z_outofplane`.
- Invalid omitted dipole: `center_y` / simulation-y cavity-normal.

Runtime FSP files are under `outputs/r2_4c_variable_dbr_setup_only_fsp/runtime_fsp/` and must not be committed.

## Manual GUI Inspection Result

Status: passed.

- Setup-only FSPs were generated for top 5 R2-4B variable-DBR candidates.
- Priority candidates R2_4B_OPT_06361 and R2_4B_OPT_06176 were inspected.
- 2D FDTD layout was confirmed.
- Top/bottom DBR pair counts were confirmed.
- Variable layer thicknesses were checked against `r2_4c_layer_thickness_manifest.csv`.
- Cavity spacer, source, monitor, and PML placement were acceptable.
- `center_x` orientation is theta=90, phi=0.
- `center_z_outofplane` orientation is theta=0, phi=0.
- No `center_y` / cavity-normal solve candidate was generated.
- No solve was performed.

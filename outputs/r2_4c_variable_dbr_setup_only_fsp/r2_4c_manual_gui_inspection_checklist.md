# R2-4C Manual GUI Inspection Checklist

For each setup-only FSP:

- Confirm 2D FDTD.
- Confirm each candidate has correct top/bottom pair count.
- Confirm variable layer thicknesses match `r2_4c_layer_thickness_manifest.csv`.
- Confirm cavity spacer thickness matches the R2-4B candidate.
- Confirm source is at cavity center and not on a material interface.
- Confirm `center_x` is theta=90, phi=0.
- Confirm `center_z_outofplane` is theta=0, phi=0.
- Confirm there is no `center_y` solve candidate.
- Confirm monitor is above top DBR, outside PML, in homogeneous air.
- Confirm x span is 20 um, device width is 3 um, DBR span is 8 um, and monitor span is 16 um.
- Do not solve until this checklist passes.

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

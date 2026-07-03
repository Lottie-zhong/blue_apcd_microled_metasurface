# R2-4D6 GUI Inspection Checklist

Open only the nine setup-only FSPs under `runtime_fsp/`.

Confirm for every file:

- Candidate is `D5_BASE_13461` only.
- Source is x-oriented only: theta=90 deg, phi=0 deg.
- Source x position matches the manifest row.
- Source is inside the 3.0 um GaN/device cavity aperture and at y=91 nm.
- Top DBR group, bottom reflector group, and GaN cavity group exist.
- Top DBR bottom touches GaN cavity top; bottom DBR top touches GaN cavity bottom.
- Monitor is above top DBR, in air, and outside PML.
- No y dipole, z_outofplane dipole, broadband case, backup candidate, or old failed candidate is present.
- Do not solve during GUI inspection.

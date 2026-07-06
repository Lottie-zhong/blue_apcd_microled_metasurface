# R2-4H1C Stop / Allow Rules

Stop:
- Do not run FDTD.
- Do not call run, runanalysis, mesh, optimize, or sweep.
- Do not open or copy heavy FSP/LDf/MAT/H5 files into git.
- Do not treat text/path evidence as optical success.
- Do not start tri-point FDTD from H1C alone.

Allow:
- Manual GUI screenshot audit of `F:\wc_312\MDC_blue_oujizi.fsp` without running or saving.
- Commit lightweight CSV/JSON/MD/script files and the screenshot intake `.gitignore`.
- Plan H1D only after human GUI evidence is reviewed.

# R2-4H1E Source Isolation Rules

Future dipole validation must:
- Load `F:\wc_312\MDC_blue_oujizi.fsp`.
- Switch to layout in memory only.
- Disable PlaneSource `source` in memory.
- Enable DipoleSource `source_1` in memory.
- Start with 450 nm x-dipole only.
- Avoid saving or overwriting the original FSP.
- Mark any run invalid if both plane and dipole sources are active.
- Keep y-dipole, z-dipole, and broadband disallowed until x-dipole passes.

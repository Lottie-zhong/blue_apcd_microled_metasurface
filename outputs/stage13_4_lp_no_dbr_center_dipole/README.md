# Stage13-4 LP No-DBR Center Dipole Diagnostic

- Runs only `center_x`, then `center_y` after the center_x complex-vector gate.
- Patch: A_small, 3 x 19 tiles, 342 dimers / 684 nanopillars.
- DBR/RCLED: off. No substrate/device-stack object is added; the Stage12 default background is retained.
- Source: (0, 0, -200) nm relative to the Stage12 pillar-base z=0 plane; diagnostic placeholder only.
- Complex-vector Ex/Ey/Ez is required. Ez contributes only to total cone power, not LP projection.
- Cones: 5, 10, 20 degrees; grid: 101.
- x/y dipole powers are combined incoherently; fields are never added.
- `.fsp` files under `_saved_fsp/` are runtime artifacts and must not be committed.

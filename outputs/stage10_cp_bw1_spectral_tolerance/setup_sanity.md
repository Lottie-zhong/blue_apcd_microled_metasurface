# Stage10-CP-BW1 setup sanity

- selected frozen CP candidate id: `B4INT_J1J2_D194_T90_PSI97_H525`
- source base script/FSP path: `scripts/blue_stage10_cp_zprop_validation/stage10_cp_route_b4_integer_plane_wave_screen.py` logic reused; new BW1 script varies wavelength only.
- structure: metasurface-only periodic J1/J2 dimer unit cell.
- absent objects confirmed by construction: no DBR, no RCLED cavity, no MQW, no dipole source, no finite patch.
- boundary conditions: x/y periodic; z min/max PML.
- source: +z plane wave below metasurface; x and y linear inputs are run separately and combined into CP Jones channels.
- monitors: `field_monitor` complex E monitor and `T` power monitor from B4 plane-wave setup.
- exact wavelength list: 447, 448, 449, 450, 451, 452, 453 nm.
- CP channel definitions: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).
- convention audit: formula matches the calibrated Stage10 +z/B4 scripts.
- Physical target: for the current frozen B4INT candidate in the existing Stage10 +z scripts, the calibrated target channel is RCP input -> LCP output, i.e. R_in -> L_out. Therefore BW1 treats R_in_to_L_out as the target channel. Do not use the older L_in -> R_out wording unless an inspected script explicitly proves this setup uses the opposite convention.

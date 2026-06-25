# Stage10-CP-BW1R fresh 448 nm setup sanity

- selected candidate id: `B4INT_J1J2_D194_T90_PSI97_H525`
- geometry: d=194 nm, theta=90 deg, psi=97 deg, H=525 nm, J1=230x100 nm, J2=180x90 nm, period_x=431.907786 nm, period_y=432.0 nm, index=2.6
- base script reused: `scripts/blue_stage10_cp_zprop_validation/stage10_cp_bw1_spectral_tolerance.py`, which reuses `stage10_cp_route_b4_integer_plane_wave_screen.py`
- fresh wavelength list: 447.0, 447.5, 448.0, 448.5, 449.0 nm
- new FDTD simulations are run in this output folder; previous BW1 FSPs are not used for metrics
- old BW1 CSV/FSPs are inspected only for old-vs-fresh comparison
- source: +z periodic plane wave, x/y linear basis runs
- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)
- target convention: R_in_to_L_out
- monitor/extraction: complex Ex/Ey from `field_monitor`, CP Jones reconstruction from x/y linear fields
- excluded by construction: no DBR, no RCLED, no MQW, no dipole, no finite patch, no +/-q, no tolerance geometry

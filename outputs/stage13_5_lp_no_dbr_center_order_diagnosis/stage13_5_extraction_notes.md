# Stage13-5 Extraction Notes

- Input FSPs: existing Stage13-4 `stage13_4_center_x.fsp` and `stage13_4_center_y.fsp`.
- Lifecycle used: open hidden FDTD session, load saved FSP, extract monitor data, close. No `run`, save, or switch-to-layout call.
- API: `farfieldvector3d`, `farfieldux`, `farfielduy` on monitor `stage13_4_top_complex_field`.
- Grid: `101 x 101`.
- Complex extraction debug: `{"center_x": {"fsp": "D:\\project\\blue_apcd_microled_metasurface\\outputs\\stage13_4_lp_no_dbr_center_dipole\\_saved_fsp\\stage13_4_center_x.fsp", "fsp_size_bytes": 34529915, "farfieldvector3d": {"shape": [101, 101, 3], "dtype": "complex128", "is_complex": true, "component_axis": -1}, "ux_shape": [101, 1], "uy_shape": [101, 1], "read_only": true, "run_called": false, "raw_arrays_saved": false}, "center_y": {"fsp": "D:\\project\\blue_apcd_microled_metasurface\\outputs\\stage13_4_lp_no_dbr_center_dipole\\_saved_fsp\\stage13_4_center_y.fsp", "fsp_size_bytes": 34529963, "farfieldvector3d": {"shape": [101, 101, 3], "dtype": "complex128", "is_complex": true, "component_axis": -1}, "ux_shape": [101, 1], "uy_shape": [101, 1], "read_only": true, "run_called": false, "raw_arrays_saved": false}}`.
- LP target/leakage: solid-angle-weighted |Ex|^2 / |Ey|^2.
- Ez: excluded from LP projection; included in total vector power.
- Order-cone masks use true spherical angular distance from each order direction vector.
- Order centers: zero ux=0; plus ux=0.1736481777617225; minus ux=-0.1736481777617225; all uy=0.
- Cone half-angles: [3.0, 5.0, 10.0] deg.
- At 5 deg adjacent cones touch near their midpoint; 10 deg cones overlap strongly, so order-fraction columns are comparative rather than a disjoint power partition.
- Peak positions are global maxima over the valid propagating ux^2+uy^2<=1 region.
- PNG maps show each component normalized to its own peak in dB; raw peak values remain in the peak CSV.
- Raw complex arrays saved: False.
- No intensity-only farfield3d LP inference.
- No coherent addition of center_x and center_y fields; only power sums are used.

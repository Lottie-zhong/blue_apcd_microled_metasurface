# Stage13-4 Extraction Notes

- Required API: `farfieldvector3d` for complex Ex/Ey/Ez plus `farfieldux` and `farfielduy`.
- Far-field grid: `101 x 101`.
- Cone half-angles: `[5.0, 10.0, 20.0]` degrees.
- LP projection: target x-LP uses solid-angle-weighted `|Ex|^2`; leakage y-LP uses solid-angle-weighted `|Ey|^2`.
- LP fraction denominator contains Ex and Ey only.
- Ez handling: excluded from LP projection and included only in `total_cone_power`.
- Total cone power: integral of `|Ex|^2 + |Ey|^2 + |Ez|^2` over the cone.
- Integration grid: direction cosines from `farfieldux/farfielduy`, weighted by `du_x du_y / u_z`.
- Raw complex arrays saved: `False`.
- Intensity-only `farfield3d` is not used to infer LP metrics.
- x/y dipoles are separate simulations; only powers are summed incoherently.
- This finite-patch cone analysis is not an order-resolved Jones/APCD selectivity claim.
- Runtime extraction state: `{"center_x": {"case_id": "center_x", "status": "ok", "extraction_debug": {"api": "farfieldvector3d + farfieldux + farfielduy", "farfieldvector3d": {"shape": [101, 101, 3], "dtype": "complex128", "is_complex": true, "component_axis": -1}, "farfieldux_shape": [101, 1], "farfielduy_shape": [101, 1], "raw_arrays_saved": false, "Ez_handling": "excluded from x/y LP projection; included only in total_cone_power", "integration": "solid-angle weighted integration on farfieldux/farfielduy grid"}}, "center_y": {"case_id": "center_y", "status": "ok", "extraction_debug": {"api": "farfieldvector3d + farfieldux + farfielduy", "farfieldvector3d": {"shape": [101, 101, 3], "dtype": "complex128", "is_complex": true, "component_axis": -1}, "farfieldux_shape": [101, 1], "farfielduy_shape": [101, 1], "raw_arrays_saved": false, "Ez_handling": "excluded from x/y LP projection; included only in total_cone_power", "integration": "solid-angle weighted integration on farfieldux/farfielduy grid"}}}`.

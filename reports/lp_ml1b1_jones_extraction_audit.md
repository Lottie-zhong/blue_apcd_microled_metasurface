# LP-ML1B1 Jones extraction audit

Complex extraction method used: complex Ex/Ey field data from a 2D Z-normal profile monitor at the transmitted side, component-normalized by the power monitor transmission.
farfield3d intensity was not used for phase.

Jones matrix ordering convention: Jt = [[txx, txy], [tyx, tyy]], columns are input polarization and rows are output polarization.
- txx = x_out from x_in
- tyx = y_out from x_in
- txy = x_out from y_in
- tyy = y_out from y_in

Phase wrapping convention: selected_phase_deg = angle(txx) wrapped to [0, 360); phase_error_deg = absolute wrapped distance to the target bin.
selected_Tx = |txx|^2; leakage_xin_to_yout = |tyx|^2; leakage_yin_to_xout = |txy|^2; y_direct_leakage = |tyy|^2.
conversion_to_leakage_ratio = |txx|^2 / max(|txy|^2 + |tyy|^2, eps).
matrix_error = ||J - txx * |x><x|||_F / max(|txx|, eps).

Caveat: this smoke test uses center-field complex monitor extraction rather than far-field order-resolved extraction; use it as a template sanity check, not final LP library evidence.
Caveat: material/template convention uses object-defined dielectric index 2.6 from existing LP dimer scripts; update later only with an explicit material audit.
Next correction needed if values look invalid: replace center-field extraction with validated complex far-field vector extraction, still avoiding intensity-only farfield3d phase.

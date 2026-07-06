# LP-ML1B0 complex Jones extraction spec

Intensity-only farfield3d is forbidden for phase because it returns intensity |E|^2 and loses complex phase.
Use farfieldvector3d or farfieldpolar3d, or equivalent complex-field monitor data, for complex far-field/Jones extraction.
LP-ML1B uses normal-incidence periodic plane-wave dimer simulations. Later angled validation must use Bloch/BFAST rather than plain periodic.
Run x and y input polarizations across 450-454 nm.

Jones convention: Jt = [[txx, txy], [tyx, tyy]], columns are input polarization, rows are output polarization.
txx = x_out from x_in; tyx = y_out from x_in; txy = x_out from y_in; tyy = y_out from y_in.
selected x-channel phase is angle(txx). Phase error uses wrapped/circular angular distance to nearest 60-degree bin.
selected_Tx = |txx|^2; leakage_xin_to_yout = |tyx|^2; leakage_yin_to_xout = |txy|^2; y_direct_leakage = |tyy|^2; ratio and matrix_error follow the LP projection target Jt(lambda) ~= t(lambda) exp(i phi_bin) |x><x|.
Spectral aggregation is over 450-454 nm using the 9-point wavelength grid.
Batch Lumerical commands with lumapi.eval where appropriate.

No FDTD was run.

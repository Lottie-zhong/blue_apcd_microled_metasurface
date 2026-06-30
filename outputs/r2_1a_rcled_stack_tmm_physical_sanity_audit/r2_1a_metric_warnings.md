# R2-1A Metric Warnings

Repeated spectral FWHM values such as 4.959948 nm and 4.360571 nm come from the lightweight proxy formula, not from a dense physical TMM interpolation. Treat them as screening labels, not measured FWHM.

Angular FWHM is computed from the proxy angular curve. It can miss split lobes, broad pedestals, and finite-aperture effects. FDTD validation is required before claiming a true single near-normal lobe.

Normal/off-axis ratio uses the same proxy intensity basis for I_normal_0_5deg_at_453 and I_offaxis_20_30deg_at_453. A high ratio can still be misleading if absolute output is weak.

Top_pair_count >= 10 is marked high extraction risk unless transmitted output strength is independently validated.

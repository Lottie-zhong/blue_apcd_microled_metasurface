# R2-1B Metric Warnings

High-resolution FWHM values are recomputed from proxy curves, but the curves still come from the lightweight STACK/TMM-style proxy rather than a full physical FDTD model.

Multi-lobe detection is based on comparable local maxima in the proxy angular cut and should be confirmed by 2D FDTD.

Normal/off-axis ratios use the same proxy intensity basis. Candidates with low absolute_peak_proxy_at_453 should be treated as weak-output false positives.

Top=12 candidates are high extraction-risk because very high top reflectivity can increase Q while reducing useful upward extraction. Top=6/bottom=6 candidates are better balanced candidates for useful upward extraction in the current proxy.

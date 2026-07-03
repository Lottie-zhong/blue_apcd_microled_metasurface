# R2-4D8 Source-Position Failure Diagnosis / Proxy Redesign

Python-only diagnosis using existing R2-4D7 outputs. No Lumerical, lumapi, FDTD, FSP generation, or runtime FSP reads were used.

## D7 Diagnosis

- Candidate: `D5_BASE_13461`.
- D7 x-line x-dipole verdict: `fail`.
- Center source peak_abs_angle_deg: 0.028662222062435815.
- X-line average peak_abs_angle_deg: 14.041304042576005.
- X-line average angular_FWHM_deg: 8.234008464681507.
- Center normal/offaxis ratio: 0.2304507616040059.
- X-line average normal/offaxis ratio: 0.18235750919538307.
- Source-position instability: peak_abs min/max/std = 0.028662222062435815 / 38.88902008351703 / 13.338528210504743 deg.
- normal/offaxis min/mean = 0.044632783204338576 / 0.20589725689945976.
- edge/unstable flag: True.

## One-line conclusion

`D5_BASE_13461` failed because center-source near-normal behavior does not survive the x-line source-position ensemble; off-axis 30-40 deg channels are re-excited away from center.

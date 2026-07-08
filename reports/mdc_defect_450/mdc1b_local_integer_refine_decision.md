# MDC1B local integer refine decision

Generated: 2026-07-08T14:12:42

## Scope

MDC1B is a pure Python TMM local integer-nm refinement stage. It does not use FMM, FDTD, Lumerical, RCLED, or any FSP file.

Default physical direction remains:

```text
GaN -> reverse(defect-MDC stack) -> Air
```

## Selected candidates

### MDC-Baseline-Fab: MDC1B_FAB_0126

```text
Topology = T1
N = 3
L = SiO2 79 nm
H = TiO2 45 nm
C = SiO2 defect 156 nm
Layer count = 13
peak = 450.00 nm
Tpeak = 0.8293
FWHM = 8.25 nm
T450_0 = 0.8293
T450_20 = 0.1318
normal_to_40_60_ratio = 38.58
robust_peak_span = 12.00 nm
robust_T4500_min = 0.2795
```

Interpretation: This is the current first fabrication-friendly defect-MDC baseline. Compared with A0-INT, it keeps 13 layers, centers the peak at 450 nm, and improves the normal-to-large-angle ratio.

Design-side layer sequence:

```text
Air / (SiO2 79 nm / TiO2 45 nm)^3 / SiO2_defect 156 nm / (TiO2 45 nm / SiO2 79 nm)^3 / GaN
```

Emission-side layer sequence:

```text
GaN / (SiO2 79 nm / TiO2 45 nm)^3 / SiO2_defect 156 nm / (TiO2 45 nm / SiO2 79 nm)^3 / Air
```

### MDC-Performance: MDC1B_PERF_0890

```text
Topology = T1
N = 4
L = SiO2 81 nm
H = TiO2 44 nm
C = SiO2 defect 157 nm
Layer count = 17
peak = 450.00 nm
Tpeak = 0.8304
FWHM = 2.50 nm
T450_0 = 0.8304
T450_20 = 0.0145
normal_to_40_60_ratio = 117.53
robust_peak_span = 12.00 nm
robust_T4500_min = 0.0368
```

Interpretation: This is the high-performance spectral-angular filter anchor. It is not the default fabrication baseline because 17 layers increase accumulated thickness-error risk and the light robust probe suggests high sensitivity.

### MDC-Reference: MDC-A0-INT

```text
Topology = T1
N = 3
L = SiO2 79 nm
H = TiO2 44 nm
C = SiO2 defect 158 nm
Layer count = 13
peak = 449.0 nm
Tpeak = 0.8290
FWHM = 8.0 nm
T450_0 = 0.7882
T450_20 = 0.1130
normal_to_40_60_ratio = 32.33
```

Interpretation: This remains the rounded quarter-wave / half-wave reference and is used to show that local integer tuning improves the 450 nm defect-MDC response.

## T3 interpretation

The top T3 candidates all had Nair=3 and Nled=3, which is layer-equivalent to the symmetric T1 N=3 case. Therefore T3 has not shown an independent asymmetric advantage in MDC1B and is not selected as a primary candidate.

## Next stage recommendation

Next stage should be MDC1C small-point stackrt/RCWA/FMM parity for the selected 2-3 candidates before any FDTD or FSP modification.

Do not freeze a physical device from TMM alone.

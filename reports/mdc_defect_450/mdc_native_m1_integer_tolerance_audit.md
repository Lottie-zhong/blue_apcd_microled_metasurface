# MDC Native-M1 integer thickness tolerance audit

Pure-film Native-M1 TMM tolerance audit; postprocess-only reconstruction from completed metrics. No FDTD/Lumerical.

## Nominal three core metrics

| candidate | spectral peak | spectral FWHM | T450 | 450 max angle | strict | near | angular FWHM | combined |
|---|---:|---:|---:|---:|:---:|:---:|---:|:---:|
| EX_N3_L79_H45_C156 | 450.160 | 7.537 | 0.8278 | -3 | False | True | 26.509 | True |
| ZL1_N3_M3_L78_H46 | 450.300 | 3.366 | 0.9605 | -3 | False | True | 17.726 | True |

## Statistics

Counts: design basin 1452, correlated bias 2662, independent layer MC 1800; independent MC uses fixed seed 20260711.
- design_basin / EX_N3_L79_H45_C156: n=1331; peak 450.215±11.164 nm; FWHM 7.587±0.601 nm; T450 0.2445±0.2391; max-angle mean -14.952 deg, max abs 60.0 deg; strict 0.411; near 0.428; angular FWHM 20.162±10.440 deg; combined 0.076.
- design_basin / ZL1_N3_M3_L78_H46: n=121; peak 450.389±14.347 nm; FWHM 3.421±0.317 nm; T450 0.1191±0.2221; max-angle mean -28.182 deg, max abs 60.0 deg; strict 0.190; near 0.215; angular FWHM 9.074±7.466 deg; combined 0.058.
- correlated_bias / EX_N3_L79_H45_C156: n=1331; peak 450.215±11.164 nm; FWHM 7.587±0.601 nm; T450 0.2445±0.2391; max-angle mean -14.952 deg, max abs 60.0 deg; strict 0.411; near 0.428; angular FWHM 20.162±10.440 deg; combined 0.076.
- correlated_bias / ZL1_N3_M3_L78_H46: n=1331; peak 450.362±7.985 nm; FWHM 3.430±0.242 nm; T450 0.1943±0.2590; max-angle mean -19.953 deg, max abs 60.0 deg; strict 0.290; near 0.318; angular FWHM 10.707±6.820 deg; combined 0.086.
- independent_layer_1nm / EX_N3_L79_H45_C156: n=300; peak 450.035±1.780 nm; FWHM 7.542±0.088 nm; T450 0.7073±0.1259; max-angle mean -3.773 deg, max abs 14.0 deg; strict 0.503; near 0.630; angular FWHM 26.677±4.234 deg; combined 0.500.
- independent_layer_3nm / EX_N3_L79_H45_C156: n=300; peak 450.449±4.557 nm; FWHM 7.609±0.231 nm; T450 0.4796±0.2342; max-angle mean -6.640 deg, max abs 22.0 deg; strict 0.443; near 0.507; angular FWHM 23.019±7.684 deg; combined 0.193.
- independent_layer_5nm / EX_N3_L79_H45_C156: n=300; peak 449.651±6.699 nm; FWHM 7.672±0.350 nm; T450 0.4077±0.2635; max-angle mean -7.143 deg, max abs 60.0 deg; strict 0.507; near 0.543; angular FWHM 23.305±8.594 deg; combined 0.163.
- independent_layer_1nm / ZL1_N3_M3_L78_H46: n=300; peak 450.283±1.257 nm; FWHM 3.374±0.031 nm; T450 0.7083±0.2131; max-angle mean -3.777 deg, max abs 11.0 deg; strict 0.400; near 0.623; angular FWHM 16.235±4.228 deg; combined 0.497.
- independent_layer_3nm / ZL1_N3_M3_L78_H46: n=300; peak 450.256±3.132 nm; FWHM 3.412±0.076 nm; T450 0.4587±0.3140; max-angle mean -4.963 deg, max abs 19.0 deg; strict 0.460; near 0.583; angular FWHM 13.720±5.482 deg; combined 0.270.
- independent_layer_5nm / ZL1_N3_M3_L78_H46: n=300; peak 450.422±4.620 nm; FWHM 3.478±0.117 nm; T450 0.3179±0.2806; max-angle mean -7.860 deg, max abs 60.0 deg; strict 0.447; near 0.487; angular FWHM 12.743±6.379 deg; combined 0.133.

## Robust integer alternatives

| candidate | geometry | peak | FWHM | T450 | 450 angle | angular FWHM | combined |
|---|---|---:|---:|---:|---:|---:|:---:|
| EX_N3_L79_H45_C156 | `[["L",74],["H",44],["L",74],["H",44],["L",74],["H",44],["L",161],["H",44],["L",74],["H",44],["L",74],["H",44],["L",74]]` | 448.200 | 7.419 | 0.6816 | +0 | 22.385 | true |
| EX_N3_L79_H45_C156 | `[["L",79],["H",44],["L",79],["H",44],["L",79],["H",44],["L",157],["H",44],["L",79],["H",44],["L",79],["H",44],["L",79]]` | 448.140 | 7.424 | 0.6642 | +0 | 22.098 | true |
| EX_N3_L79_H45_C156 | `[["L",77],["H",45],["L",77],["H",45],["L",77],["H",45],["L",156],["H",45],["L",77],["H",45],["L",77],["H",45],["L",77]]` | 448.320 | 7.427 | 0.6894 | +0 | 22.339 | true |
| EX_N3_L79_H45_C156 | `[["L",78],["H",44],["L",78],["H",44],["L",78],["H",44],["L",158],["H",44],["L",78],["H",44],["L",78],["H",44],["L",78]]` | 448.380 | 7.427 | 0.6992 | +0 | 22.352 | true |
| EX_N3_L79_H45_C156 | `[["L",76],["H",45],["L",76],["H",45],["L",76],["H",45],["L",157],["H",45],["L",76],["H",45],["L",76],["H",45],["L",76]]` | 448.560 | 7.429 | 0.7238 | +0 | 22.644 | true |
| EX_N3_L79_H45_C156 | `[["L",78],["H",45],["L",78],["H",45],["L",78],["H",45],["L",155],["H",45],["L",78],["H",45],["L",78],["H",45],["L",78]]` | 448.060 | 7.429 | 0.6543 | +0 | 22.116 | true |
| EX_N3_L79_H45_C156 | `[["L",77],["H",44],["L",77],["H",44],["L",77],["H",44],["L",159],["H",44],["L",77],["H",44],["L",77],["H",44],["L",77]]` | 448.640 | 7.435 | 0.7330 | +0 | 22.688 | true |
| EX_N3_L79_H45_C156 | `[["L",75],["H",45],["L",75],["H",45],["L",75],["H",45],["L",158],["H",45],["L",75],["H",45],["L",75],["H",45],["L",75]]` | 448.820 | 7.436 | 0.7562 | +0 | 23.032 | true |
| EX_N3_L79_H45_C156 | `[["L",80],["H",43],["L",80],["H",43],["L",80],["H",43],["L",159],["H",43],["L",80],["H",43],["L",80],["H",43],["L",80]]` | 448.200 | 7.444 | 0.6749 | +0 | 22.135 | true |
| EX_N3_L79_H45_C156 | `[["L",74],["H",45],["L",74],["H",45],["L",74],["H",45],["L",159],["H",45],["L",74],["H",45],["L",74],["H",45],["L",74]]` | 449.060 | 7.447 | 0.7854 | +0 | 23.502 | true |
| ZL1_N3_M3_L78_H46 | `[["H",44],["L",79],["H",44],["L",79],["H",44],["L",316],["H",44],["L",79],["H",44],["L",79],["H",44],["L",79]]` | 449.700 | 3.329 | 0.9606 | +0 | 14.921 | true |
| ZL1_N3_M3_L78_H46 | `[["H",42],["L",80],["H",42],["L",80],["H",42],["L",320],["H",42],["L",80],["H",42],["L",80],["H",42],["L",80]]` | 449.080 | 3.350 | 0.7641 | +0 | 13.767 | true |
| ZL1_N3_M3_L78_H46 | `[["H",46],["L",78],["H",46],["L",78],["H",46],["L",312],["H",46],["L",78],["H",46],["L",78],["H",46],["L",78]]` | 450.300 | 3.366 | 0.9605 | -3 | 17.726 | true |
| ZL1_N3_M3_L78_H46 | `[["H",47],["L",77],["H",47],["L",77],["H",47],["L",308],["H",47],["L",77],["H",47],["L",77],["H",47],["L",77]]` | 448.660 | 3.371 | 0.6100 | +0 | 13.817 | true |
| ZL1_N3_M3_L78_H46 | `[["H",41],["L",81],["H",41],["L",81],["H",41],["L",324],["H",41],["L",81],["H",41],["L",81],["H",41],["L",81]]` | 450.720 | 3.445 | 0.8454 | -5 | 19.444 | true |
| ZL1_N3_M3_L78_H46 | `[["H",49],["L",76],["H",49],["L",76],["H",49],["L",304],["H",49],["L",76],["H",49],["L",76],["H",49],["L",76]]` | 449.340 | 3.504 | 0.8711 | +0 | 14.598 | true |
| ZL1_N3_M3_L78_H46 | `[["H",51],["L",75],["H",51],["L",75],["H",51],["L",300],["H",51],["L",75],["H",51],["L",75],["H",51],["L",75]]` | 450.120 | 3.704 | 0.9874 | -2 | 17.911 | true |
| ZL1_N3_M3_L78_H46 | `[["H",43],["L",78],["H",43],["L",78],["H",43],["L",312],["H",43],["L",78],["H",43],["L",78],["H",43],["L",78]]` | 443.480 | 3.196 | 0.0628 | +0 | 21.784 | false |
| ZL1_N3_M3_L78_H46 | `[["H",46],["L",76],["H",46],["L",76],["H",46],["L",304],["H",46],["L",76],["H",46],["L",76],["H",46],["L",76]]` | 442.440 | 3.225 | 0.0469 | +0 | 23.415 | false |
| ZL1_N3_M3_L78_H46 | `[["H",45],["L",77],["H",45],["L",77],["H",45],["L",308],["H",45],["L",77],["H",45],["L",77],["H",45],["L",77]]` | 444.100 | 3.229 | 0.0739 | +0 | 20.732 | false |

## Boundary and reproducibility audit

- Boundary-clipped/undefined spectral FWHM samples: 9/5914; angular FWHM samples: 543/5914. These are retained as blank values, never converted to zero; nominal and robust shortlist rows are finite and unclipped.
- Integer geometry and full compiled sequences are retained in each metrics row; ZL-1 uses an independent central-layer error in the correlated and MC scans.
- The duplicated design-basin and correlated-bias statistics are intentional: the former is a linked integer basin, the latter applies common H/L/D bias.

## Physical judgment

- Explicit is the wider-bandwidth integer baseline; ZL-1 is the narrow-spectrum candidate and must be judged against its tolerance pass rates.
- TMM maximum-transmission angle is plane-wave angular selection, not dipole far-field.
- No frozen materials or existing TMM/FDTD result files were modified.

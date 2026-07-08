# MDC defect-450 branch freeze: MDC0V + MDC1A integer TMM

Generated: 2026-07-08T13:47:12

## Scope

This freeze records the lightweight code and key results for the 450 nm top defect-MDC branch.

No FSP, no Lumerical run, no FDTD, no RCLED continuation, no push.

Default physical direction for later ranking is:

```text
GaN -> reverse(film stack) -> Air
```

## MDC0V validation result

- TMM validation checks: PASS

- Identity / Fresnel / oblique interface / energy conservation / reciprocity checks passed.

- Integer-nm policy adopted after MDC0V/MDC1A discussion.


## Integer baseline thickness

- SiO2 L = 79 nm

- TiO2 H = 44 nm

- SiO2 defect C0 = 158 nm


## Key candidate comparison

| candidate | topo | N | Nair | Nled | L | H | C | layers | peak | Tpeak | FWHM | T450_0 | T450_20 | ratio | score |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MDC-A0-INT | T1 | 3 |  |  | 79 | 44 | 158 | 13 | 449.0 | 0.8290 | 8.0 | 0.7882 | 0.1130 | 32.33 | 13.76 |
| MDC1A_0202 | T1 | 3 |  |  | 81 | 43 | 160 | 13 | 450.0 | 0.8282 | 8.0 | 0.8282 | 0.1338 | 36.12 | 22.63 |
| MDC1A_0319 | T1 | 4 |  |  | 81 | 43 | 160 | 17 | 450.0 | 0.8164 | 2.0 | 0.8164 | 0.0151 | 99.55 | 33.16 |
| MDC1A_0227 | T1 | 3 |  |  | 81 | 45 | 155 | 13 | 451.0 | 0.8292 | 8.5 | 0.8060 | 0.1497 | 42.81 | 20.64 |
| MDC1A_0577 | T2 | 3 |  |  | 81 | 45 | 150 | 13 | 450.0 | 0.8271 | 6.5 | 0.8271 | 0.0758 | 31.75 | 18.02 |
| MDC1A_0694 | T2 | 4 |  |  | 81 | 45 | 150 | 17 | 450.0 | 0.8275 | 2.0 | 0.8275 | 0.0085 | 89.58 | 24.9 |

## Current interpretation

- `MDC-A0-INT` is the rounded baseline: T1, N=3, L=79, H=44, C=158, 13 layers, peak around 449 nm, FWHM around 8 nm.

- `MDC1A_0202` is the current fabrication-friendly anchor: T1, N=3, L=81, H=43, C=160, 13 layers, peak 450 nm, FWHM 8 nm, high T450_0.

- `MDC1A_0319` is the current performance anchor: T1, N=4, L=81, H=43, C=160, 17 layers, peak 450 nm, FWHM 2 nm, much stronger angular suppression but higher layer-count risk.

- N=3 is preferred for first physical MDC baseline because layer count and thickness-error accumulation are lower.

- N=4 remains a high-performance comparison candidate, not the immediate default fabrication baseline.


## Local output references

- `outputs/mdc0v_tmm_validation_and_baseline_audit/`

- `outputs/mdc1a_integer_nm_defect_mdc_screen/`

- `outputs/mdc1a_integer_shortlist_audit/`


## Files intentionally tracked in this commit

- `scripts/stage_mdc0v_tmm_validation_and_baseline_audit.py`

- `scripts/stage_mdc1a_tmm_defect_mdc_450_screen.py`

- `scripts/stage_mdc1a_integer_shortlist_audit.py`

- this lightweight report under `reports/mdc_defect_450/`


## Files intentionally not tracked

- `.fsp`, `.ldf`, `.mat`, `.h5`, `.npy`, `.npz`, raw monitor data, runtime folders.

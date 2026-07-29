# MDC FDTD source, monitor, and setting audit v1

Status: VALID_WITH_LIMITATION. Read-only audit; FDTD/TMM/Lumerical solve calls = 0.

## Authority and provenance

- Active commit: `92f6b011a6e7dd447986da8a4cf3ad66cd1745cf`.
- Formal 2D dipole builders: `scripts/stage_mdc1d1_native_m1_bare_fab_2d_smoke.py`, `stage_mdc1d2_native_m1_zl1_2d_validation.py`, and `stage_mdc1d3_native_m1_broadband_spectral_angular_validation.py`.
- Canonical material source FSP: `F:\wc_312\MDC_blue_oujizi_m\m_1.fsp`; it loaded read-only through lumapi. v251 rejected the legacy object-enumeration call; no solver or save was called.
- Native-M1 materials are bound by `configs/material_reference_apcd_blue.yaml`: `APCD_GAN_NATIVE_M1`, `APCD_TIO2_NATIVE_M1`, `APCD_SIO2_NATIVE_M1`; manifest sampling covers 420–480 nm and reports no fallback.

## Geometry/source coordinate table

| Evidence path | stack/domain | source | monitor | assessment |
| --- | --- | --- | --- | --- |
| `stage_mdc1d1...py` | GaN y=-1000..0 nm; MDC y=0..900 nm; domain y=-1000..2000 nm | x=0, y=-400 nm; x dipole (`theta=90`, `phi=0`); 450 nm | top linear-X at y=1200 nm | source is 400 nm inside GaN, 400 nm below MDC, 600 nm above bottom PML; center-only x-polarization |
| `stage_mdc1d2...py` | GaN y=-1000..0 nm; 12-layer ZL-1 y=0..978 nm | x=0, y=-400 nm; x dipole; 450 nm | top linear-X y=1278 nm | same center-only limitation |
| `stage_mdc1d3...py` | GaN y=-1000..0 nm; candidate stack y=0..stack top | x=0, y=-400 nm; x dipole; 442–458 nm | top linear-X y=stack top+300 nm; 65 points | spectral/angular label route; not x/y incoherent average |

The code implements propagation GaN → MDC → air. It does not model an explicit MQW; the source is an equivalent in-GaN plane. The code provides no physics evidence that y=-400 nm is an MQW centre. No source overlaps a layer interface, monitor, or PML in the builders inspected.

## Monitor definition and label mapping table

| Monitor/metric | Definition | Label use | audit finding |
| --- | --- | --- | --- |
| `top_monitor` / `top` | Linear-X power monitor, x span 6 µm, top+300 nm | raw upward monitor power; `farfield2d` / `farfieldangle` | power sign/reference aperture insufficiently documented for extraction efficiency |
| angular spectrum | top monitor far-field projection, normalized by angular integral | angular FWHM/cone fractions | air-side angle sign and projection medium are not explicitly frozen in code |
| broadband top monitor | 442–458 nm, 65 points | spectral peak/FWHM and angular metrics | FWHM can be window-truncated; unsuitable as unconditional formal label |
| closed power-box helper | `scripts/mdc_fdtd_2d_monitor_contract_v1.py` | reusable, not evidenced as the formal 11-label route | would be needed for auditable net-power normalization |

## FDTD validation provenance and usability table

| Source | candidate/FSP evidence | usability | reason |
| --- | --- | --- | --- |
| `outputs/mdc_native_m1_2d_dipole_device_comparison_v1/broadband_420_480_simulation_manifest.csv` | 10 x/z subruns; runtime FSP SHA and solver-log SHA retained; source commit `46af823...` | VALID_WITH_LIMITATION | paired x/z sources and fixed r12 box normalization; runtime FSP files are absent from active worktree |
| `ml_candidate_labels_broadband_420_480.csv` | 5 structure labels; geometry/material hashes retained | LEGACY_BASELINE | useful external validation, not current formal OOF input; spectral FWHM may be truncated |
| MDC1D1/D2 outputs | bare/FAB and ZL-1 centre x-dipole | LEGACY_BASELINE | scripts explicitly state raw monitor power is not extraction efficiency |
| canonical `m_1.fsp` | material-reference source FSP | VALID_WITH_LIMITATION | read-only load succeeded; object-level inventory blocked by v251 query incompatibility |

## Findings and minimum repair plan

1. **Medium severity:** formal builder source is a single centre x dipole, not demonstrated MQW emission or x/z(or x/y) noncoherent averaging. A future setup revision should define the equivalent MQW plane and run both 2D polarization channels with frozen averaging.
2. **Medium severity:** top-monitor far-field and raw-power normalization are not enough to establish a single extraction-efficiency label. Freeze a closed power-box/reference-plane convention and air-side angle sign before any relabeling.
3. **High evidence limitation:** runtime FSP SHA is retained, but the actual runtime FSP is unavailable; source/monitor/boundary object readback cannot be independently reproduced from the current worktree.

No files were modified. No formal OOF, model, sealed-test, solver, or prediction activity occurred.

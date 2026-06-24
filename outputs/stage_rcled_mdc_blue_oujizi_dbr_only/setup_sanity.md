# MDC_blue_oujizi DBR-only RCLED setup sanity

- Project base FSP: `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_dbr_1_gan_dbr_only\_setup_fsp\gan_dbr_only_grouped_setup.fsp`
- Read-only DBR reference: `N:\zlt\DBR\MDC_blue_oujizi.fsp`
- Final setup model: `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_dbr_only\rcled_mdc_blue_oujizi_dbr_only_no_metasurface.fsp`
- DBR order: [sio222 100 nm -> tio22 52 nm] x 8 -> terminal sio222 100 nm
- DBR layers: 17; total thickness: 1316.0 nm.
- Metasurface/APCD/B4INT objects absent: True
- Old temporary DBR group absent: True
- Sources: center=(0,0,-200.0 nm); x orientation theta/phi=90.0/0.0 deg; y orientation theta/phi=90.0/90.0 deg.
- Monitor: `top_field_monitor_zprop`, type `2D Z-normal`, z=2316.0 nm, propagation axis +z (`prop_axis=3`).
- Mesh accuracy preserved: 3.0; project GaN, boundaries, wavelength, monitor and source settings are retained.
- GUI colors: tio22 red `[[0.7499961852445258, 0.0, 0.0, 1.0]]`; sio222 yellow `[[1.0, 1.0, 0.0, 1.0]]`.

## Layer table

| # | object | material | z min (nm) | z max (nm) | thickness (nm) |
|---:|---|---|---:|---:|---:|
| 0 | OUJIZI_DBR_00_SiO2 | sio222 | 0.0 | 99.99999999999999 | 99.99999999999999 |
| 1 | OUJIZI_DBR_00_TiO2 | tio22 | 99.99999999999999 | 152.0 | 52.0 |
| 2 | OUJIZI_DBR_01_SiO2 | sio222 | 152.0 | 252.0 | 99.99999999999999 |
| 3 | OUJIZI_DBR_01_TiO2 | tio22 | 252.0 | 304.0 | 52.0 |
| 4 | OUJIZI_DBR_02_SiO2 | sio222 | 304.0 | 404.0 | 99.99999999999999 |
| 5 | OUJIZI_DBR_02_TiO2 | tio22 | 404.0 | 456.0 | 52.0 |
| 6 | OUJIZI_DBR_03_SiO2 | sio222 | 456.0 | 556.0 | 99.99999999999999 |
| 7 | OUJIZI_DBR_03_TiO2 | tio22 | 556.0 | 608.0 | 52.0 |
| 8 | OUJIZI_DBR_04_SiO2 | sio222 | 608.0 | 708.0 | 99.99999999999999 |
| 9 | OUJIZI_DBR_04_TiO2 | tio22 | 708.0 | 760.0 | 52.0 |
| 10 | OUJIZI_DBR_05_SiO2 | sio222 | 760.0 | 860.0 | 99.99999999999999 |
| 11 | OUJIZI_DBR_05_TiO2 | tio22 | 860.0 | 912.0 | 52.0 |
| 12 | OUJIZI_DBR_06_SiO2 | sio222 | 912.0 | 1012.0 | 99.99999999999999 |
| 13 | OUJIZI_DBR_06_TiO2 | tio22 | 1012.0 | 1064.0 | 52.0 |
| 14 | OUJIZI_DBR_07_SiO2 | sio222 | 1064.0 | 1164.0 | 99.99999999999999 |
| 15 | OUJIZI_DBR_07_TiO2 | tio22 | 1164.0 | 1216.0 | 52.0 |
| 16 | OUJIZI_DBR_08_SiO2_terminal | sio222 | 1216.0 | 1316.0 | 99.99999999999999 |

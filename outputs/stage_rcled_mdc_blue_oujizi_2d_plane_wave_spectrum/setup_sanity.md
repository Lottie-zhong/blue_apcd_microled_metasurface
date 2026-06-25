# Setup sanity
source_3d_fsp: D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_dbr_only\rcled_mdc_blue_oujizi_dbr_only_no_metasurface.fsp
final_2d_fsp: D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum\rcled_mdc_blue_oujizi_2d_plane_wave_spectrum.fsp
source_direction: physical +z from GaN/source side to DBR/output side; simulation +y in 2D
source_wavelength_range_nm: 438-468
wavelength_step_nm: 0.5 requested via 61 monitor points
monitors: T_up_monitor, R_down_monitor
boundaries: x periodic, simulation y PML (physical z PML)
mesh_accuracy: 3
polarization_modes: pol0_angle0, pol90_angle90
confirmation: no APCD/B4INT/metasurface/dipole objects
DBR: [sio222 100 nm -> tio22 52 nm] x 8 -> terminal sio222 100 nm


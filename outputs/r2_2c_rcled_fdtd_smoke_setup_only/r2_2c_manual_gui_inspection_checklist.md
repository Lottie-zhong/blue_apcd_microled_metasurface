# R2-2C Coordinate Mapping

- simulation_x = horizontal lateral direction.
- simulation_y = vertical cavity-normal direction / upward emission direction in this 2D x-y layout.
- simulation_z = out-of-plane direction.
- Physical MQW incoherent pair for this 2D smoke test = simulation_x + simulation_z_outofplane.
- simulation_y dipole = cavity-normal dipole and is INVALID_DO_NOT_SOLVE for this MQW smoke test.


# Manual GUI Inspection Checklist

For each setup-only FSP:

- Confirm simulation dimension is 2D.
- Confirm no result data exist and no solve has been run.
- Confirm top DBR has 6 SiO2/TiO2 pairs and no unintended terminal layer.
- Confirm bottom DBR has 6 TiO2/SiO2 pairs and touches the GaN cavity at y=0.
- Confirm GaN/effective cavity spacer thickness is 280 nm.
- Confirm MQW dipole is at y=140 nm, the cavity center.
- Confirm source does not sit on a material interface.
- Confirm x file uses theta=90, phi=0.
- Confirm corrected out-of-plane file uses theta=0, phi=0 and does not display as a vertical y/cavity-normal arrow.
- Confirm old center_y file is marked INVALID_DO_NOT_SOLVE and is not solved.
- Confirm monitor is above the DBR, outside PML, and inside homogeneous air.
- Do not run solve until this checklist passes.

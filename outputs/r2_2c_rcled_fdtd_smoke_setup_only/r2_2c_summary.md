# R2-2C Corrected Setup-Only FDTD Files

Corrected the MQW dipole-pair mapping for the 2D x-y RCLED layout.

No FDTD solve was run. No `run`, `runanalysis`, far-field extraction, `.ldf`, or raw monitor export was performed.

## Valid solve candidates

- `R2_2C_R2_1_00223_453_center_x_setup_only.fsp`: simulation x dipole, theta=90, phi=0.
- `R2_2C_R2_1_00223_453_center_z_outofplane_setup_only.fsp`: simulation z/out-of-plane dipole, theta=0, phi=0.

## Invalid retained file

- `R2_2C_R2_1_00223_453_center_y_setup_only.fsp`: INVALID_DO_NOT_SOLVE. This is a simulation-y cavity-normal dipole in the current 2D x-y layout.

Runtime FSP files are saved under `outputs/r2_2c_rcled_fdtd_smoke_setup_only/runtime_fsp/` and must not be staged.

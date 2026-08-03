# NP K6 mainline M0 training system v1

Status: NP_K6_MAINLINE_M0_TRAINING_SYSTEM_READY_HF_FDTD_LABELS_PENDING

Level-1 NP/MDC coupling is frozen as one-way incoherent power in a 2D x-z MDC steering plane with common k_y=0, primary coordinate u_x, and physical m=+1 equal to +x. NP remains a full 3D K6 supercell and stores p/TM and s/TE separately. Complex feedback is not supported in v1.

The training stack includes a strict FDTD-only dataset loader, circular six-node CNN reference forward pass, structured order/T/R/target/physics loss, metrics, and a deterministic Level-1 power adapter. LF DFT proxies, diagnostic-only data, RCWA labels, constant-epsilon controls, historical sparse FDTD, and sealed-test data are rejected as formal labels.

Validation is synthetic/dry-run only. No FDTD, solver, real fit, checkpoint, active learning, or sealed-test access occurred. Formal HF label count remains zero and production mesh remains unresolved. Pilot scope is 445-455 nm at u_x=0; bulk MDC-compatible training remains unauthorized pending Pilot4, stack, wavelength/angular support, polarization weighting, and production-label-generator decisions.

Evidence: outputs/np_k6_m0_training_system_v1/. The exact next action is AUTHORIZE_NP_K6_FDTD_LABEL_GENERATOR_RECOVERY_AND_PILOT_DATA_ACQUISITION.

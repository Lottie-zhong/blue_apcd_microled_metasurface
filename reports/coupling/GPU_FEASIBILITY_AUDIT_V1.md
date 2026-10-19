# APCD Coupling-ML ZERO-SOLVER GPU Feasibility Audit V1

Audit time: 2026-09-23 16:51 +08:00
Remote host: DESKTOP-NNE313K / desktop-nne313k\dell
Branch: work/mdc-np-coupling-ml-v1
HEAD: b0ec1ad3f92dd093a87b0945fa4cb1aef24321e2

## STATUS

PARTIAL / GPU_STATIC_FEASIBLE_LICENSE_UNCERTAIN

No scientific solver was run. No FAST, MEDIUM, 5 nm, dipole, queue, slot, database, Traditional, or scientific setup mutation occurred.

## GPU HARDWARE

- GPU count: 1
- Model: NVIDIA GeForce RTX 3080
- VRAM: 10,240 MiB
- Audit snapshot: 955 MiB used, 9,099 MiB free
- GPU utilization: 1%; memory utilization: 0%
- nvidia-smi driver/KMD/UMD: 610.60 / 610.60 / 13.3
- Compute capability: 8.6
- PCI bus ID: 00000000:73:00.0
- WMI driver version: 32.0.16.1060
- PCIe generation/link width: not exposed by the collected WDDM fields; not inferred.
- nvidia-smi listed Windows graphics processes with N/A compute memory. No FDTD engine was active after the checker.

GPU hardware satisfies the official Windows driver and compute-capability minimums.

## LUMERICAL INSTALLATION

Actual installation path:

N:\Program Files\ANSYS Inc\v251\Lumerical

VERSION file:

- MAJORRELEASE=2025R1
- MINORRELEASE=0
- BUILDNUMBER=3999
- fdtd-solutions.exe file/product version: 8.33.3999

Installed CPU/MPI engines:

- fdtd-engine.exe
- fdtd-engine-msmpi.exe
- fdtd-engine-impi.exe
- varfdtd-engine*.exe

No separately named fdtd-engine-gpu.exe, CUDA, GPU, or OpenCL backend file was found in the inspected installation root/bin/prerequisite levels. This is not by itself evidence that GPU support is absent; 2025 R1 exposes GPU execution through the FDTD GPU resource/run mode.

The installed fdtd-run-local.bat is CPU-only:

    mpiexec.exe -n PROCS fdtd-engine-msmpi.exe -t 1 FSP

The current 12 MPI x 1 thread path is therefore not a GPU launch path.

Official 2025 R1 documentation confirms 3D FDTD GPU support, dispersive-material support, GUI/GPU memory checking, and the runsystemcheck GPU checker. It also states that GPU parallel-engine options are ignored.

## LICENSE

Read-only evidence:

- ANSYS Licensing Interconnect utility: 2.1.1 (20191113), updated at ANSYS 2020 R1.
- A FlexLM path is configured.
- ansysli_util -printavail and -printusage could not connect to the configured license server.
- The filtered local ansyslmd.lic inspection exposed no usable FEATURE/INCREMENT names.
- No GPU/HPC entitlement was confirmed.
- No checkout, reserve, or license-test checkout was performed.

GPU_LICENSE_READY = UNCERTAIN

The official documentation says Business/Standard and Enterprise licenses support FDTD GPU, while multi-node multi-GPU has additional Business/Enterprise requirements. The current machine evidence does not prove which entitlement is active.

## CURRENT MEDIUM SETUP

Authoritative readback:

D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\FREEZE_V3_RESOURCE_HARDENING_AND_MEDIUM_PW_PREENTRY_V1\W2H_15294_MEDIUM_PW_SETUP_WITH_MON_IN_READBACK.json

Setup-only FSP SHA256:

1907d677c0a35e658ae3595c665e5899d093f97480bc1e79cbecf110f110489b

### Source

- 3D standard plane-wave source.
- Lumerical source property: plane wave type = Bloch/periodic.
- z-axis, Forward, polarization angle 0 degrees.
- theta=0 and phi=0, hence current mainline ux=0.
- 440-460 nm, 21 points.
- Not BFAST.

The separate broadband_fixed_ux_source_contract_v1.json is a BFAST contract for another path and is not used by the authoritative MEDIUM setup.

### Boundaries

- x and y min/max: Periodic
- z min/max: PML
- PML layers: 8
- No legacy uniaxial-anisotropic PML identified.

### Materials

Native sampled materials:

- APCD_GAN_NATIVE_M1
- APCD_TIO2_NATIVE_M1
- APCD_SIO2_NATIVE_M1
- Air background

Static code uses sampled native-material registration, not the Flexible Material Plugin Framework. No anisotropy, gain, nonlinear, or custom material plugin was found in the inspected path. Dispersive materials are supported by the installed 2025 R1 GPU implementation.

### Mesh

- 3D FDTD, mesh accuracy 2.
- Conformal variant 1.
- Default PML mesh refinement.
- Local nonuniform overrides: 5, 10, 15, and 20 nm.
- Medium effective estimated grid: Nx=279, Ny=51, Nz=265, total 3,770,685 cells.

### Monitors and postprocess

- MON_IN, MON_PRENP, MON_POSTNP, MON_REFLECTION: 2D Z-normal frequency monitors.
- Three field planes retain six complex E/H components in the production raw path.
- 21 frequency points.
- No time/movie monitor, 3D volume monitor, partial/total spectral averaging, checkpoint, or time-apodization dependency found.
- Grating/order projection and canonical Floquet projection are postprocess operations, not in-solver GPU features.

CURRENT_MEDIUM_SETUP_GPU_COMPATIBLE = YES

This is conditional on license availability and future CPU/GPU parity.

## OFFICIAL GPU SYSTEM CHECK

The supported non-solver checker was run on the existing setup-only MEDIUM FSP using lumapi. The only FDTD script command evaluated was:

    gpu_check = runsystemcheck('FDTD','GPU');

No run() call was present. Report:

D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\MEDIUM_PW_GPU_SYSTEMCHECK_V1.json

Result:

- checker completed successfully;
- no unsupported-feature warning field was returned;
- minimum GPU memory: 531,908,680 bytes;
- maximum GPU memory: 622,929,568 bytes;
- maximum fields/auxiliary: 184,335,360 bytes;
- maximum grid/material coefficients: 178,947,840 bytes;
- monitors: 258,987,456 bytes;
- sources: 658,912 bytes.

After the checker, no fdtd-engine, mpiexec, or Lumerical solver process remained.

## MEMORY

### MEDIUM

Official checker range: 531,908,680-622,929,568 bytes, approximately 0.50-0.58 GiB, versus 10,240 MiB physical VRAM.

MEDIUM_GPU_MEMORY_FIT = YES

### 5 nm reference

No separate 5 nm GPU checker was run. Saved metadata gives 14,532,480 effective cells versus 3,770,685 for MEDIUM, ratio 3.8541. Scaling field/material components by the cell ratio and monitor storage by the saved in-plane grid ratio gives an offline estimate of approximately:

- 1,417,353,319 bytes minimum;
- 1,768,154,097 bytes maximum;
- approximately 1.32-1.65 GiB.

This is not an official 5 nm checker result, but it is well below 10,240 MiB.

5NM_GPU_MEMORY_FIT = YES

Only one GPU is installed; no multi-GPU memory or scaling claim is made.

## EXECUTION MODEL

A. Can current Shared V3 launch GPU as-is?

No. Current Shared V3 evidence is the CPU/MPI launcher. GPU requires a separate GPU resource/run-mode path. This is an execution-layer change, not a physics-contract change.

B. Does GPU replace 12 MPI x 1 thread?

Yes. GPU mode is not a twelve-rank CPU decomposition. Official documentation says CPU parallel-engine options are ignored in GPU mode.

C. Recommended throughput on this host:

ONE_GPU_SIMULATION_AT_A_TIME

There is one RTX 3080. Official guidance warns that concurrent jobs assigned to the same GPU may have poor performance. Do not mix CPU and GPU jobs concurrently until a separately authorized resource policy exists.

D. CPU/GPU scientific equivalence:

Yes, conditionally, after a one-case parity canary confirms identical geometry, mesh, materials, source, monitors, normalization, R/T, orders, canonical C_PW, and energy closure within predeclared tolerances.

## FINAL VERDICT

    GPU_HARDWARE_READY = YES
    GPU_LICENSE_READY = UNCERTAIN
    CURRENT_MEDIUM_SETUP_GPU_COMPATIBLE = YES
    MEDIUM_GPU_MEMORY_FIT = YES
    GPU_CPU_PARITY_CANARY_READY = NO

The blocker is license entitlement visibility, not hardware, setup compatibility, or VRAM. No production GPU run is authorized.

## PROPOSED NEXT TEST - NOT EXECUTED

GPU_CPU_PARITY_AND_RUNTIME_CANARY_V1

Use one existing case only after license confirmation. Keep identical geometry, native materials, mesh/PML, normal-incidence standard plane wave, monitors, 21-wavelength grid, R/T/order extraction, canonical C_PW, and predeclared numerical tolerances. Compare CPU/GPU runtime, memory, R/T, orders, canonical state, closure, and provenance. Do not execute this canary under the current task.

## COMMANDS USED

    nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,pstate,compute_cap,pci.bus_id --format=csv,noheader,nounits
    nvidia-smi -q
    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits
    Get-CimInstance Win32_VideoController
    Get-Content N:\Program Files\ANSYS Inc\v251\Lumerical\VERSION
    Get-Item N:\Program Files\ANSYS Inc\v251\Lumerical\bin\fdtd-solutions.exe
    Get-Content N:\Program Files\ANSYS Inc\v251\Lumerical\bin\fdtd-run-local.bat
    ansysli_util.exe -version long
    ansysli_util.exe -printlicpath FLEXLM
    ansysli_util.exe -printavail
    ansysli_util.exe -printusage
    lumapi + runsystemcheck('FDTD','GPU') on setup-only FSP

License-server addresses and license keys are intentionally omitted.

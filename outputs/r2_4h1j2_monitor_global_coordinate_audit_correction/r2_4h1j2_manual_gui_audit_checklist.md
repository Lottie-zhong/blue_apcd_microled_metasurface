# R2-4H1J2 manual GUI audit checklist

This stage does not blindly move the DFT monitor based on child-layer local coordinates.

Manual GUI audit must confirm:

- monitor is on the output side of the top MDC;
- monitor is not inside TiO2/SiO2 layers;
- monitor has reasonable spacing from the upper PML;
- far-field settings match the user-approved settings:
  - projection direction = auto
  - material index = auto
  - far field filter = 1
  - 2D resolution = 1001
  - 3D resolution = 1001
  - Assume structure is periodic unchecked
  - override near field mesh unchecked

If GUI confirms the monitor is unsafe, a later explicit correction stage may move the monitor and save a revised runtime FSP. H1J2 does not run FDTD.

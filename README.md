# blue_apcd_microled_metasurface

Blue-light 450 nm APCD-inspired metasurface project for future Micro-LED integration.

This repository is the blue mainline project.  
The old 633 nm red/APCD proof-of-concept project is archived separately as:

- red_plane_wave_metasurface_archive
- tag: v0.9-red-633-archive

## Current stage

Stage 10: blue APCD feasibility scout.

The first task is single-pillar Jones-role lookup under blue-light A/B routes.  
Do not start with full dimer phase-library construction.

## Blue route candidates

Route A:

- wavelength: 450 nm
- K = 5
- target angle: 15 deg
- px ≈ 348 nm
- py ≈ 320 nm
- phase bins: [0, 72, 144, 216, 288]

Route B:

- wavelength: 450 nm
- K = 6
- target angle: 10 deg
- px ≈ 432 nm
- py ≈ 320 nm
- phase bins: [0, 60, 120, 180, 240, 300]

## Materials

Primary:

- TiO2

Backup:

- GaN

## First scout metrics

Single-pillar lookup should extract:

- tx_amp
- ty_amp
- phase_x
- phase_y
- retardance
- common_phase
- trans_mean
- amp_balance

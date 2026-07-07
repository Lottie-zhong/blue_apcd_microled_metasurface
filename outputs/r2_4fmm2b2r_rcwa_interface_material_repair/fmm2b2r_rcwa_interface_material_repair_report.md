# FMM2B2R RCWA interface/material inclusion repair

## ????

stage = `FMM2B2R`; previous_commit = `85aca83`.

?????FMM2B2 created geometry objects but did not explicitly provide RCWA interface positions, so material interfaces were not represented in total_energy.

## TMM oracle

| case | R | T |
|---|---:|---:|
| air_reference | 0.0 | 1.0 |
| single_SiO2_79nm | 0.1160629034346602 | 0.8839370965653396 |
| single_TiO2_45nm | 0.5338667610779264 | 0.4661332389220735 |
| TiO2_SiO2_10pair_QWinteger453_proxy | 0.9999597100342625 | 4.028996573727591e-05 |

## RCWA repaired total_energy

| case | Rs | Ts | Rp | Tp | R_avg | T_avg | status |
|---|---:|---:|---:|---:|---:|---:|---|
| air_reference | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | ok |
| single_SiO2_79nm | 0.0014925087550915531 | 0.9985074912449089 | 0.0009451595981624684 | 0.9990548404018381 | 0.0012188341766270108 | 0.9987811658233735 | ok |
| single_TiO2_45nm | 0.004817798682236295 | 0.9951822013177635 | 0.0033280553702840438 | 0.996671944629715 | 0.00407292702626017 | 0.9959270729737393 | ok |
| TiO2_SiO2_10pair_QWinteger453_proxy | 0.0651899148779494 | 0.9348100851220558 | 0.06314751998984194 | 0.9368524800101549 | 0.06416871743389567 | 0.9358312825661053 | ok |

## Decision

- interface_position_mode: `interface absolute positions`.
- propagation_axis / stacking_axis: `x / RCWA forward` / `x`.
- nontrivial_reflection_recovered: `True`.
- H1J4-like 10-pair stronger than air/single-layer proxies: `True`.
- decision: `rcwa_interface_material_repair_pass`.
- ??????? FDTD???????? H1J4 FSP??? sweep??? broadband??? APCD coupling??? push?

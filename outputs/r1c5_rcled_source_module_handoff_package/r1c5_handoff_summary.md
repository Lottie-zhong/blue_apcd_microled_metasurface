# R1C5 RCLED/MDC Source-Module Handoff

## Decision

Freeze `R1C2_C2_cav230` as the RCLED/MDC source-module baseline for later APCD coupling.

## Why This Route

The old m8 + bottomDBR99 route was rejected because it produced symmetric off-normal 20-30 degree lobes. The R1C0 TMM redesign found the top=6, bottom=0 family; R1C1 validated the top candidates; R1C2 refined C2 and selected `C2_cav230`.

## Frozen Baseline

- top_pair_count: 6
- bottom_pair_count: 0
- cavity_span_nm: 230
- termination: TiO2_50nm
- wavelengths validated: 450, 453, 456 nm
- recommended source_y_offset_nm: 0
- backup source_y_offset_nm: -20

## Evidence

Center source stays near-normal across 450/453/456 nm, with dominant_zone=`abs_5_10`. The -20 nm source offset is a near-center backup and also stays near-normal across 450/453/456 nm.

## Caveat

Do not claim full +/-40 nm vertical robustness. The -40 nm offset fails near-normal behavior at 450/456 nm, and +20 nm has 450 nm dominant_zone=`abs_20_30`.

## Status

APCD integration has not yet been run.

# R1C5 Source-Y Caveat

The frozen source-module baseline is intended for center or near-center source placement.

- Recommended source_y_offset_nm: 0
- Backup source_y_offset_nm: -20
- Full +/-40 nm vertical robustness did not pass.
- -40 nm fails near-normal behavior at 450/456 nm.
- +20 nm has 450 nm dominant_zone=abs_20_30.

Use this module for later APCD coupling with a source-placement caveat. APCD integration has not been run.

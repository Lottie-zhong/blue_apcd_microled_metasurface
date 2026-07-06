# R2-4H1I Lumerical command notes for future H1J/H1K

H1I does not execute Lumerical or lumapi.

Future FSP modification scripts should follow the official command behavior assumed in the project workflow:

- use `layoutmode` to check whether the loaded file is in LAYOUT or ANALYSIS mode;
- call `switchtolayout` before modifying objects;
- use `getnamed`/`setnamed` for named-object property reads and writes;
- call `run` only in explicitly approved FDTD stages;
- never use existing analysis-mode results as validation evidence.

These notes are construction constraints for future approved scripts, not actions taken in H1I.

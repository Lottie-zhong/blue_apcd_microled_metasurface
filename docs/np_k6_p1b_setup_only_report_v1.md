# NP-K6-MDC P1-B setup-only report V1

## Outcome

Two periodic-FDTD setup-only files were created, saved, reloaded, and inspected. solver_run=false and un_count=0; no optical solve or monitor-result extraction occurred.

## Reuse and implementation

- Reused scripts/apcd_native_materials.py::register_lumerical_sampled_material to register the existing Native-M1 sampled TiO2 and SiO2 data. No material model, fallback, or extrapolation policy was rewritten.
- Reused the existing periodic/PML, plane-source, and field-monitor construction pattern as a minimal new direct-circle builder.
- Added one shared builder for blank and pillar; blank only omits TiO2 pillar and its local mesh override.
- Added a fail-closed pure-function extractor skeleton. It does not read setup-only monitor results and rejects unavailable solved data.

## Final frozen setup

- 3D periodic FDTD: x/y period 290 nm; x/y periodic, z PML.
- SiO2 substrate -> Air, +z; interface z=0 nm; no independent spacer.
- Gate: 450 nm x-LP, Forward (+z), source z=-500 nm, R_fields z=-750 nm, T_fields z=900 nm.
- Pillar case: APCD_TIO2_NATIVE_M1 circular cylinder, H=500 nm, D=160 nm; local mesh 5 nm.
- Both cases use the same FDTD region (-1000 to 1200 nm z), source, monitor, and reference-plane coordinates.

## Native-M1 and object audit

Native-M1 registration returned Sampled 3D data with 101x2 sampled tables for APCD_TIO2_NATIVE_M1 and APCD_SIO2_NATIVE_M1. Reload audit confirmed 290 nm x/y spans, Periodic x/y and PML z, 450 nm, x polarization angle 0, Forward source, shared monitor coordinates, blank pillar_count=0, and pillar_count=1. The pillar object audit returned H=500 nm, D=160 nm and canonical material references.

## Extraction convention

Use direct solver-returned zero-order complex amplitude; weighted_G0 is forbidden. With identical blank planes, 	_rel=t_candidate/t_blank and phase_rel=arg(t_rel). Preserve raw complex amplitude/power, relative Re/Im/abs/phase, T0/R/total-T/energy residual, and Jones 	xx,tyx,txy,tyy. Cross-polarized q-input amplitudes normalize by the same-input blank co-polar amplitude, never a blank cross-polar term.
## Validation and minimal fixes

N:\anaconda_envs\RCP_LCP\python.exe passed YAML/JSON parsing, Python py_compile, and pytest (5 passed). AST/text gate confirms neither builder nor extractor contains .run(. Two setup-only API fixes were made: the FDTD object's default stable name cannot be set explicitly, so the inactive name assignment was removed; a remote text-write seam and integer-regex escape were corrected before the passing regression run.

## Runtime FSP artifacts (untracked, never staged)

- untime_fsp/np_k6_p1b_unitcell_v1/np_k6_blank_p290_wl450_polx.fsp: 474,995 bytes; SHA256 3DABBB06E2148FFCEE8DA4B32107D401550EB9042FF38512CC9737C73BD167DC.
- untime_fsp/np_k6_p1b_unitcell_v1/np_k6_pillar_p290_H500_D160_wl450_polx.fsp: 478,552 bytes; SHA256 AC7F746CA8166F9B7AEA8D40C7D29BED63AF2A72FADACBB373272DB986F297CE.

The manifest contains both setup records, input/material/config hashes, geometry and fabrication labels, runtime paths, file hashes/sizes, provenance, and null physical results.

## Next allowed task

P1-C only: one authorized blank/pillar real-solver run followed by direct zero-order extraction and blank-relative normalization. No result is claimed here.
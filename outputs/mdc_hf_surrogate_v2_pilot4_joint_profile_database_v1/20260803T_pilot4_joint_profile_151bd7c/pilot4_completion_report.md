# Pilot4 joint-profile database completion

- Status: `MDC_HF_SURROGATE_V2_BULK_DATABASE_READY_AWAITING_96_GEOMETRY_576_CASE_AUTHORIZATION`
- Authorization: 4 geometries / 24 unique physical cases; DOE96 unauthorized.
- Joint export: native per-wavelength farfield2d tensor, shape `[301, 2000]`, 24/24 accepted.
- Quality: finite ratio 1.0, negative count 0, raw-before-normalization and marginal closure PASS.
- Aggregation: 4 geometry profiles, six raw cases per geometry, no case-level normalization before aggregation.
- Replay: two independent fresh Python processes, all deterministic SHA fields identical.
- NP interface: frozen synthetic consumption fixture PASS; solver calls 0.
- Safety: 24 FDTD entries, 0 recovery solver calls, 0 DOE96/HF15/sealed/TMM/RCWA/model-fit calls.

DOE96 has not been started; no HF15 formal labels or diagnostics were read.

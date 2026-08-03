# LP_ML_DATASET_V1 Attempt-2 smoke and D9 closeout

## Status
`LP_ML_PIPELINE_SMOKE_PASS_READY_FOR_ROUND1_PRODUCTION`

## Root cause and monitor fix
The previous attempt used correct source start/stop but left monitor sampling at the Lumerical default five-point grid. Attempt-2 freezes global and local monitor settings: wavelength-domain spacing, `frequency points=9`, and `use source limits=true`, then verifies persistence after save/reload.

## Historical failed attempt
Attempt-1 remains immutable and excluded: entered=1, accepted=0, returned frequency count=5, admitted physics rows=0. Attempt-2 has a separate attempt ID, staging path, accounting ledger, checkpoints and sentinel.

## New attempt accounting
- planned/entered/accepted: 32/32/32
- failed/missing/duplicate invocations: 0/0/0
- complete Jones geometries: 16/16
- spectral rows: 144

## Broadband full-Jones acceptance
All rows use formal coordinate-weighted periodic G0 at field_monitor z=1000 nm with endpoint deduplication/reclosure and `sqrt(T)/norm(weighted Ex,Ey)`. x/y grids are identical and ordered as 450.0--454.0 nm in 0.5 nm steps. Independent Jones metric recomputation max absolute error: 6.776e-21. No symmetry assumption (`txy` and `tyx` are stored independently).

## QA and constraints
Duplicate physics rows=0; model-filled rows=0; Native-M1 readback passed; protected report SHA256 unchanged. No D9, Batch B, old Batch2, remaining 240 geometries, model training, inverse design, K6, or heavy artifacts were created.

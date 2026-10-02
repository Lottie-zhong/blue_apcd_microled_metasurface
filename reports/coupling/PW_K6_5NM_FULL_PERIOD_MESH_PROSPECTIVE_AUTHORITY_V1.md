# PW_K6_5NM_FULL_PERIOD_MESH_PROSPECTIVE_AUTHORITY_V1

Status: PASS. The prospective 5 nm mesh authority is established, and all 12 approved Stage-1 pre-FSPs passed fresh LOAD-only validation.

Historical builder source provenance is NOT_RECOVERABLE. This implementation is a new authority derived from serialized, validated artifact behavior; it does not claim to recover the lost source.

The integrated scientific contract remains unchanged at 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. Its mesh-convergence declaration is: 5NM_GPU_PRODUCTION_SCHEMA_V3 admitted seed contract; no contract changes. It does not specify the old per-pillar local-mesh extents. The separate W2H-specific mesh-contract artifact is recorded as historical context, not reused as the integrated builder authority.

## Mesh definition

| Object | Step (nm) | Center (nm) | Span (nm) | Bounds (nm) |
|---|---:|---:|---:|---:|
| NP_DERIVED_BASELINE_N2 | 5 x 5 x 5 | (0, 0, 1462) | 1740 x 290 x 700 | x [-870,870], y [-145,145], z [1112,1812] |
| MESH_NP_MDC_SPACER_BASELINE | 10 x 10 x 10 | (0, 0, 1462) | 1740 x 290 x 750 | x [-870,870], y [-145,145], z [1087,1837] |

The historical mesh-bound audit covers 20 seed geometries and 120 pillars: 120/120 covered, with minimum lateral clearance 30 nm and vertical clearance 100 nm. Separately, parity covered all 20 SCIENTIFIC_VALID cases in the 20G dataset freeze: the freeze manifest records solver entry/return, exactly one entry, SCIENTIFIC_VALID PASS, HF archive PASS, and existing LOAD PASS for all 20; candidate LOAD validation 20/20 PASS and semantic comparisons 20/20 PASS with zero mismatches. The two case sets are distinct and named in the JSON evidence.

Parity fields include geometry, Native-M1 materials, source/polarization, boundaries, monitors, wavelength range/spacing, sample/reference planes, mesh resolution, and mesh coverage envelope. Historical time-stop settings differ from the current temporal contract; the new Stage-1 inputs are independently checked against the current temporal contract.

## Stage-1 inputs

All 12 approved cases were generated at the new authority path and fresh-LOAD validated. The checks cover ordered D1-D6, MDC, spacer, Native-M1 materials, source, 440-460 nm at 1 nm spacing, periodic x/y, z PML, monitors and planes, the 5 nm full-period core mesh, and readback-derived pillar coverage. The minimum lateral clearance across these cases ranges from 30 to 50 nm; vertical clearance is 100 nm. Existing local-mesh FSP hashes were unchanged. No reserve cases were generated.

S35 and S39 both pass and are packaged in COUPLING_GPU_RUNNER_CANARY_INPUT_HANDOFF_V2. The remaining ten approved cases already have regenerated, LOAD-valid pre-FSPs. No GPU canary or solver was run.

## Historical and runtime evidence

The prior local-mesh audit recorded 39/72 pillar margin failures and 30/72 pillars outside their local mesh. Those old Stage-1 FSPs remain at their historical paths; their hashes are listed in the new per-case input manifests.

For the selected 20G dataset cases, current on-disk FSP bytes differ from their frozen manifest SHA256 values in 20/20 cases. The current files were freshly LOAD-inspected and semantic parity passed; both frozen and current hashes remain in the parity JSON. A pre-inspection current-disk hash snapshot was unavailable for 19 cases; the report records this limitation and confirms the post-inspection rehash matches each captured inspection hash.

Process snapshots before and after the zero-solver build and LOAD checks show the same eight fdtd-solutions.exe PIDs. Static tests verify that the builder has no solver run call. Scientific entry count: 0. GPU solver entry count: 0.

## Reproducibility

Builder commit: 7a0edbc3d9a9d28e732f35be166efb1fb50cd9b2.
Builder SHA256: fbd3a3e73212568023c47d84223a41b32d5cb3cf8fd48a04d09bef7bb94eded1.
Validator SHA256: b694ecf692376a33673b785774a8ea734c452f11009aad1cfe553f444817e2a8.
Test SHA256: c06c537daae5a6b6620e2a07ed67e593e5bbf651c50aa73fc77bb0a31e3ef284; pytest result: 6 passed.
Input manifest: reports/coupling/PW_K6_5NM_FULL_PERIOD_MESH_INPUT_MANIFEST_V1.json.
20G parity: reports/coupling/PW_K6_5NM_FULL_PERIOD_MESH_20G_SEMANTIC_PARITY_V1.json.
Stage-1 validation: reports/coupling/PW_K6_5NM_FULL_PERIOD_MESH_STAGE1_LOAD_ONLY_VALIDATION_V1.json.
Canary handoff: reports/coupling/COUPLING_GPU_RUNNER_CANARY_INPUT_HANDOFF_V2.json.

NEXT = HANDOFF_COUPLING_GPU_RUNNER_CANARY_INPUT_V2_TO_APCD_GPU_PRODUCTION_RUNNER_V1 (not executed).

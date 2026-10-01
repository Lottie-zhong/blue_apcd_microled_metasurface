# PW_K6_12G_5NM_MESH_CONTRACT_AND_PREFSP_REGEN_V1

Status: BLOCKED_MESH_AUTHORITY_NOT_RECOVERABLE

Root cause classification: D. MESH_CONTRACT_AUTHORITY_NOT_RECOVERABLE.

## Authority and disposition

LOAD-only inspection recovered the serialized 20G core mesh but not its source builder or generating Git commit. The 20G mesh is one NP_DERIVED_BASELINE_N2 Mesh at 5 nm over the full 1740 x 290 x 700 nm region centered at (0, 0, 1462) nm. All 20 historical setups cover all 120 pillars, with at least 30 nm lateral and 100 nm vertical clearance. The 20G setups do not have individual per-pillar 5 nm mesh objects.

The tracked MEDIUM_PW_MESH_CONTRACT_V1.json is a W2H_15294-specific setup instance. It has individual pillar meshes tied to that diameter vector, plus separate 5 nm MDC/spacer and spacer/pillar interface regions. S35/S39 case manifests do not record the FSP-generation commit. The serialized authorities cannot safely be collapsed into one canonical 12G builder. The mismatch looks like stale W2H extents, but provenance is insufficient to classify it as A or B; no builder or FSP was created.

## 20G historical coverage

- Setups audited: 20/20; pillars: 120/120; covered: 120/120.
- Diameter envelope: 100-230 nm; 12G Stage-1 range: 100-230 nm (inside the envelope).
- Minimum observed margin: 30.0 nm lateral and 100.0 nm vertical.

| 20G case | Ordered D1-D6 (nm) | Minimum mesh margin per pillar (nm) |
|---|---:|---:|
| W2H_15294 | 155,105,195,150,180,145 | 67.5,92.5,47.5,70.0,55.0,72.5 |
| W2H_06824 | 135,210,200,105,210,165 | 77.5,40.0,45.0,92.5,40.0,62.5 |
| W2H_19451 | 205,220,100,125,170,110 | 42.5,35.0,95.0,82.5,60.0,90.0 |
| W2H_10588 | 160,170,135,130,130,220 | 65.0,60.0,77.5,80.0,80.0,35.0 |
| K6V1_S01 | 220,230,210,115,120,100 | 35.0,30.0,40.0,87.5,85.0,95.0 |
| K6V1_S02 | 215,105,215,230,105,130 | 37.5,92.5,37.5,30.0,92.5,80.0 |
| K6V1_S03 | 230,100,130,120,230,100 | 30.0,95.0,80.0,85.0,30.0,95.0 |
| K6V1_S04 | 205,215,105,225,180,100 | 42.5,37.5,92.5,32.5,55.0,95.0 |
| K6V1_S05 | 215,225,100,125,110,220 | 37.5,32.5,95.0,82.5,90.0,35.0 |
| K6V1_S06 | 230,100,210,105,100,225 | 30.0,95.0,40.0,92.5,95.0,32.5 |
| K6V1_S07 | 130,225,230,100,120,220 | 80.0,32.5,30.0,95.0,85.0,35.0 |
| K6V1_S08 | 105,225,105,110,210,100 | 92.5,32.5,92.5,90.0,40.0,95.0 |
| K6V1_S09 | 105,200,190,225,110,105 | 92.5,45.0,50.0,32.5,90.0,92.5 |
| K6V1_S10 | 120,145,220,100,230,110 | 85.0,72.5,35.0,95.0,30.0,90.0 |
| K6V1_S11 | 230,125,100,230,130,215 | 30.0,82.5,95.0,30.0,80.0,37.5 |
| K6V1_S12 | 115,220,115,230,105,215 | 87.5,35.0,87.5,30.0,92.5,37.5 |
| K6V1_S13 | 230,225,110,105,225,145 | 30.0,32.5,90.0,92.5,32.5,72.5 |
| K6V1_S14 | 230,140,230,110,230,210 | 30.0,75.0,30.0,90.0,30.0,40.0 |
| K6V1_S15 | 110,135,180,230,230,100 | 90.0,77.5,55.0,30.0,30.0,95.0 |
| K6V1_S16 | 175,230,230,230,100,220 | 57.5,30.0,30.0,30.0,95.0,35.0 |

## Existing Stage-1 pre-FSP mesh matrix

Each cell is diameter / minimum XY margin / result. The checked rule requires >=10 nm XY and >=5 nm z clearance at 5 nm resolution. Current z margin is 10 nm.

| Case | P1 | P2 | P3 | P4 | P5 | P6 | Case |
|---|---:|---:|---:|---:|---:|---:|---|
| K6V1_S35 | 110 / 32.5 / PASS | 145 / -10.0 / FAIL | 225 / -5.0 / FAIL | 105 / 32.5 / PASS | 185 / 7.5 / FAIL | 215 / -25.0 / FAIL | FAIL |
| K6V1_S39 | 175 / 0.0 / FAIL | 100 / 12.5 / PASS | 125 / 45.0 / PASS | 120 / 25.0 / PASS | 100 / 50.0 / PASS | 230 / -32.5 / FAIL | FAIL |
| K6V1_S21 | 120 / 27.5 / PASS | 115 / 5.0 / FAIL | 230 / -7.5 / FAIL | 140 / 15.0 / PASS | 110 / 45.0 / PASS | 115 / 25.0 / PASS | FAIL |
| K6V1_S42 | 195 / -10.0 / FAIL | 210 / -42.5 / FAIL | 165 / 25.0 / PASS | 130 / 20.0 / PASS | 230 / -15.0 / FAIL | 230 / -32.5 / FAIL | FAIL |
| K6V1_S36 | 115 / 30.0 / PASS | 210 / -42.5 / FAIL | 220 / -2.5 / FAIL | 100 / 35.0 / PASS | 150 / 25.0 / PASS | 100 / 32.5 / PASS | FAIL |
| K6V1_S31 | 220 / -22.5 / FAIL | 195 / -35.0 / FAIL | 210 / 2.5 / FAIL | 150 / 10.0 / PASS | 140 / 30.0 / PASS | 210 / -22.5 / FAIL | FAIL |
| K6V1_S45 | 195 / -10.0 / FAIL | 120 / 2.5 / FAIL | 105 / 55.0 / PASS | 210 / -20.0 / FAIL | 220 / -10.0 / FAIL | 215 / -25.0 / FAIL | FAIL |
| K6V1_S32 | 105 / 35.0 / PASS | 190 / -32.5 / FAIL | 105 / 55.0 / PASS | 115 / 27.5 / PASS | 105 / 47.5 / PASS | 225 / -30.0 / FAIL | FAIL |
| K6V1_S47 | 165 / 5.0 / FAIL | 160 / -17.5 / FAIL | 105 / 55.0 / PASS | 100 / 35.0 / PASS | 230 / -15.0 / FAIL | 170 / -2.5 / FAIL | FAIL |
| K6V1_S33 | 170 / 2.5 / FAIL | 175 / -25.0 / FAIL | 155 / 30.0 / PASS | 150 / 10.0 / PASS | 190 / 5.0 / FAIL | 105 / 30.0 / PASS | FAIL |
| K6V1_S37 | 215 / -20.0 / FAIL | 170 / -22.5 / FAIL | 110 / 52.5 / PASS | 180 / -5.0 / FAIL | 105 / 47.5 / PASS | 130 / 17.5 / PASS | FAIL |
| K6V1_S48 | 110 / 32.5 / PASS | 100 / 12.5 / PASS | 225 / -5.0 / FAIL | 205 / -17.5 / FAIL | 195 / 2.5 / FAIL | 175 / -5.0 / FAIL | FAIL |

- Pillars passing: 33/72; failing: 39/72.
- Pillars crossing a local mesh boundary: 30/72; remaining failures have less than 10 nm lateral clearance.
- Interface objects read back as 5 nm with 20 nm z spans centered at z=975 nm and z=1212 nm.
- All 12 FSPs loaded and remained byte-identical; baseline FDTD PID set was unchanged.

## Provenance and outputs

- Physical contract hash preserved: 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.
- Mesh-contract artifact SHA256: 3e8a6eafe2cbb5c8591af381b1f416de35560dc3018ac8ad2cf284528fe16213.
- Mesh validation canonical hash: 7883105bd69ad6f8bff7d9723ebfda10f920f9d2e41f617d683dd3ab5312d93e.
- Builder authority: not created because exact authoritative source and commit are unrecoverable.
- S35/S39 regenerated pre-FSPs: not created; existing FSP hashes remain unchanged.
- Canary handoff V2: not created.
- Reserve cases read or written: none.
- Solver/GPU/entry/FSP-write/DB-mutation count: 0.

Full per-pillar physical and mesh extents, directional margins, FSP paths and hashes are in the companion JSON.

Approved Stage-1 manifest SHA256: 4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f. Per-case case.json SHA256 values are recorded in the companion JSON.

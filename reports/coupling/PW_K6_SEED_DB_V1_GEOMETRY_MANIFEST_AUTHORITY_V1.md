# PW_K6_SEED_DB_V1 geometry manifest authority

Status: FROZEN_ZERO_SOLVER

Selection authority: CASE_A_FROZEN_48_MAXIMIN_CSV_ORDER.
The primary 64G DOE S01-S48 order is consumed as frozen; no new distance metric, seed, normalization, integrated PW label, or manual shortlist was used.

## Contract

- K=6; p=290 nm; Lambda_x=1740 nm; Lambda_y=290 nm; H=500 nm; spacer=237 nm.
- x/y Periodic; z min/max PML; GaN to air, +z, normal-incidence X polarization; 440:1:460 nm.
- Existing admitted 5 nm GPU production monitor/post-processing contract is reused unchanged.

## Zero-solver audit

- Entries: 20 = 4 Core4 + 16 diversity.
- Unique ordered geometry hashes: 20; W2H_15294 count: 1.
- Blind selected: 0; sorted/permuted selection: 0.
- Physical order preserved: True; integrated PW labels used: False.
- Selected cross-source identity conflicts: 0.
- Solver invocations: 0; queue entries created by manifest build: 0.
- M2A legacy source-hash mismatches, cross-check only: 22.

## Entries

| index | case_id | D1..D6 nm | role | hash | source |
|---:|---|---|---|---|---|
| 01 | W2H_15294 | 155,105,195,150,180,145 | Core4 existing valid seed; no rerun | 75df0936fdab6c7431e2b47672614105b900e61b71058c6fdaeb9ada0fb2bd81 | PW_PERIODIC_PILOT_GEOMETRY_MANIFEST row 2 |
| 02 | W2H_06824 | 135,210,200,105,210,165 | Core4 mandatory new production case | e02bbad260272fffcb9dfe22418e4bc05bc5bc52ba3f9bfd446f4cbd49169317 | PW_PERIODIC_PILOT_GEOMETRY_MANIFEST row 3 |
| 03 | W2H_19451 | 205,220,100,125,170,110 | Core4 mandatory new production case | 37073ae0db9410014e0d780942e62249af981b13a778191905f38887d45d540e | PW_PERIODIC_PILOT_GEOMETRY_MANIFEST row 4 |
| 04 | W2H_10588 | 160,170,135,130,130,220 | Core4 mandatory new production case | 27574977186e163a7345ebc8b9c15f6f9df41068c5fdd30c346f6a6965497a51 | PW_PERIODIC_PILOT_GEOMETRY_MANIFEST row 5 |
| 05 | K6V1_S01 | 220,230,210,115,120,100 | 16-case diversity/maximin production candidate | 114eaacd145f2d38942ffb1ea6c5f64a282ae4d4715acd3b1e9ab17cda557664 | K6_V1_64G_DOE_CANDIDATES row 10 |
| 06 | K6V1_S02 | 215,105,215,230,105,130 | 16-case diversity/maximin production candidate | 947cf4b1a3b31e4bb4f5733805286f68335fc5caa2cdf244ad58b4b16312e2d3 | K6_V1_64G_DOE_CANDIDATES row 11 |
| 07 | K6V1_S03 | 230,100,130,120,230,100 | 16-case diversity/maximin production candidate | 5383cc1b85e33126508aaff6f550b9138b83d145c539b919327ecbd3cb266263 | K6_V1_64G_DOE_CANDIDATES row 12 |
| 08 | K6V1_S04 | 205,215,105,225,180,100 | 16-case diversity/maximin production candidate | 269db32fc25f6a85ff9d934aab5c99627265a9f87d8b2ba4b3887c8770a114a9 | K6_V1_64G_DOE_CANDIDATES row 13 |
| 09 | K6V1_S05 | 215,225,100,125,110,220 | 16-case diversity/maximin production candidate | c9214e73410f695ba239c80b39638afa2796b085e3efb062cbd34b6b11c6bd6b | K6_V1_64G_DOE_CANDIDATES row 14 |
| 10 | K6V1_S06 | 230,100,210,105,100,225 | 16-case diversity/maximin production candidate | bac8f402c31d27c14d02a6d2e7572e4679da2daa476ebd943d80c117f21b9ccc | K6_V1_64G_DOE_CANDIDATES row 15 |
| 11 | K6V1_S07 | 130,225,230,100,120,220 | 16-case diversity/maximin production candidate | 171582e576eab75ccd965eb834ca3271cf5b45271756cbbffb6784abc3390bcc | K6_V1_64G_DOE_CANDIDATES row 16 |
| 12 | K6V1_S08 | 105,225,105,110,210,100 | 16-case diversity/maximin production candidate | 3c59274746b67f5a9297bb31d354eb3968625098075fb42a9c8b7d6da4f5f19b | K6_V1_64G_DOE_CANDIDATES row 17 |
| 13 | K6V1_S09 | 105,200,190,225,110,105 | 16-case diversity/maximin production candidate | e8b1c844687bfa3f33b1f1423d2be1c389277c534a250ba621d2a6324db80e7c | K6_V1_64G_DOE_CANDIDATES row 18 |
| 14 | K6V1_S10 | 120,145,220,100,230,110 | 16-case diversity/maximin production candidate | e976508346a172ded25f5cc14dce145c57072ca347d404842e64f9d48896f0f9 | K6_V1_64G_DOE_CANDIDATES row 19 |
| 15 | K6V1_S11 | 230,125,100,230,130,215 | 16-case diversity/maximin production candidate | 95794768c9a2ffcfbe4e7163db4dac6fd18e1621d06a26d30471b1d59ed2fe94 | K6_V1_64G_DOE_CANDIDATES row 20 |
| 16 | K6V1_S12 | 115,220,115,230,105,215 | 16-case diversity/maximin production candidate | 84b013902364884c321b702225d72c4749b68f249b1ded925ec07a9c4a62b671 | K6_V1_64G_DOE_CANDIDATES row 21 |
| 17 | K6V1_S13 | 230,225,110,105,225,145 | 16-case diversity/maximin production candidate | 73f9a00eea23b838ebad51e1b1141747e3bfab89da05609442eee27ce8747791 | K6_V1_64G_DOE_CANDIDATES row 22 |
| 18 | K6V1_S14 | 230,140,230,110,230,210 | 16-case diversity/maximin production candidate | 2ca095e5b5a51691d08b5abb46866e6d67b29ff591ef902988e0ff1cea377b3d | K6_V1_64G_DOE_CANDIDATES row 23 |
| 19 | K6V1_S15 | 110,135,180,230,230,100 | 16-case diversity/maximin production candidate | 44ce888fac542b11c7a88046c937e9bb189cb1b7352c6153e97dee844a274ac1 | K6_V1_64G_DOE_CANDIDATES row 24 |
| 20 | K6V1_S16 | 175,230,230,230,100,220 | 16-case diversity/maximin production candidate | 909d242ab2c06ff40f591603f19a546423cdf12a38e05459e99ff336ef6e69af | K6_V1_64G_DOE_CANDIDATES row 25 |

## Queue authorization

After this manifest is committed and the zero-solver audit passes, enqueue exactly the 19 entries with NEW_PRODUCTION_ENTRY. W2H_15294 is already valid and is not enqueued or rerun.
Shared V3 limits remain GPU physical cap=3, Global=3, Traditional=1, Coupling-ML=2, slot-local autofill, and no cohort barrier.

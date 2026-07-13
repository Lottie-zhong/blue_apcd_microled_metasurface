# MDC database nominal semantic audit v1

HEAD: `50cb7945c376bd14e025211d3c070e83a89447f9`. Database/schema: 1.0.0/1.0.0.

## Finding

`is_nominal_geometry` is not the canonical definition of a nominal TMM sample. The builder writes it as `candidate in NOMINAL_IDS` (line 77), while `build_tmm` independently canonicalizes every coarse/refined scan geometry by geometry hash (lines 109-119) and writes all 2,688 rows to `tmm_nominal_metrics.csv` without consulting that flag.

The field was intended as a curated reference-candidate marker (B), but its implementation also applies to tolerance geometries that retain a reference candidate id. Therefore it is unsafe as a global physical nominal/perturbation predicate (C implementation defect).

## Counts

- geometry_master: 8675 rows / 8675 unique hashes.
- tmm_nominal_metrics: 2688 rows / 2688 unique hashes.
- TMM→geometry hash intersection: 2688; TMM left missing: 0; geometry hashes not in TMM: 5987.
- `is_nominal_geometry` among all geometry rows: {'False': 2687, 'True': 5988}; among the canonical TMM join: {'False': 2686, 'True': 2}.

## Two true canonical-TMM rows

| candidate | topology | geometry_id | H/L/C-or-center | layers / total nm | source / split |
|---|---|---|---|---|---|
| EX_N3_L79_H45_C156 | Explicit | GEO_d44569052e0f3a8a | H=45, L=79, C=156, center=- | 13 / 900 | tmm_refined / train |
| ZL1_N3_M3_L78_H46 | ZL-1 | GEO_ad8cbef5a96144d8 | H=46, L=78, C=-, center=312 | 12 / 978 | tmm_refined / train |

## Tolerance and split boundary

- Canonical TMM sources: {'tmm_coarse': 2673, 'tmm_refined': 15}; all carry simulation_method TMM and usable_for_training true.
- Tolerance sources are stored only in tolerance_samples.csv (8400 rows), with usable_for_training false. TMM record-id overlap with tolerance sample IDs: 0; TMM rows with tolerance source id: 0.
- Existing split contains all 2688 canonical TMM records: {'test': 338, 'train': 1994, 'validation': 356}. Assignment is direct per TMM record, but its constraint graph also includes tolerance parent links to prevent geometry leakage.

## Minimal repair options (not implemented)

1. Recommended C — make `tmm_nominal_metrics` the canonical nominal-sample fact table in task views; use geometry_master only for geometry joins. No reinterpretation of existing `is_nominal_geometry`; no database-v1 rebuild required for a task view. Add explicit join semantics to a future schema/report revision.
2. A — retain the field as curated-reference identity and introduce `sample_role` / `is_nominal_tmm_sample` in a v1.1 database rebuild. This preserves existing field semantics; requires schema version bump and database regeneration, but does not change tolerance/FDTD boundaries.
3. B — regenerate `is_nominal_geometry` for all 2,688 canonical TMM hashes. Not recommended because it changes the field's current curated-reference meaning and still fails to distinguish TMM nominal rows from tolerance geometries sharing candidate identifiers; requires a schema bump and rebuild.

## Recommendation

Use `tmm_nominal_metrics` + its `simulation_method=TMM`, `usable_for_training=true`, and canonical record identity as the nominal training universe. Do not filter on `geometry_master.is_nominal_geometry`. Before future release, add an explicit sample-role field and correct the reference-marker name.

## Freeze conclusions

- `is_nominal_geometry` cannot represent nominal TMM sample identity.
- The canonical nominal identity is the `tmm_nominal_metrics` fact table, joined to geometry only for features.
- Use option C immediately; adopt option A in the next database version.
- Tolerance and FDTD are not mixed into the canonical TMM table.

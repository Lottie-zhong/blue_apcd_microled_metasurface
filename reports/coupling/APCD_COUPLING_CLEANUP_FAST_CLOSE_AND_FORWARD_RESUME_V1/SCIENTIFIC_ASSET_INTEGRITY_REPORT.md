# Scientific asset integrity report

## Scope and preservation

This closeout did not alter native FSP/H5/609D, the production Science Ledger, DOE56 state, Runner source, or the pre-existing tracked edits. No FDTD or GPU Runner invocation occurred. The 272G complex dataset was read as an existing development input; the new derived OOF prediction archive remains ignored in its existing task folder. No broad rehash was run: V1/V2 SHA manifests remain the integrity reference for original large scientific assets.

## K6 science identity and entry accounting

`K6_CASE_EXECUTION_RECONCILIATION.csv` contains the 128-case identity crosswalk. The read-only evidence chain is frozen batch manifest → three initial receipts + 35 legacy run-ID rows + 90 immutable V2 receipt references → final 128-case status. IDs are unique, the 90 receipt references are tied to their source receipt content, and the final status set equals the manifest. Result: 128 entries; 124 truth/label valid; four consumed invalid cases (`K6GDP2_DEV_G023`, `K6GDP2_DEV_G024`, `K6GDP2_DEV_G026`, `K6LDA1_DEV_D6_M05`); replay 0. Eight legacy ledger rows omit attempt ID; each is retained as-is and resolves to the sole `attempt_001` in the frozen manifest plus its unique run ID. No authority ledger was rewritten.

## FAST 272G inputs and outputs

Input used: `reports/coupling/APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50/COMPLEX_DATASET.npz` (272 unique ordered geometries; C_hat 272×21×7×2; P_scale 272×21; target29 272×21×29). Evaluation reused the fixed 124 development geometries and four family-purged folds (32/31/30/31). Wavelengths stayed grouped within geometry. Outer fold preprocessing and P-scale trend fitting used training IDs only; early-stop validation was split from each outer training set by connected local-family components. This does not make the repeatedly used 124 set a final independent test.

The offline run produced 12 NN early-stop fits, 12 P-scale residual MLP fits and four Ridge fits, with no new solver entries. Source and compact metrics are versioned in this folder. `OOF_PREDICTIONS.npz` (3,591,284 bytes) remains ignored and untouched by Git staging.

## Asset and permission boundary

- FAST development data remains 272G; H1 remains HOLD.
- Sealed confirmation was not accessed.
- DOE56 remains HOLD; DIAG2 remains 1/2 and A2 remains HOLD.
- Existing V1/V2 backup and SHA inventories were reused; this pass did not delete source data or treat a SHA listing as a data backup.
- The protected DOE56 ledger with credential-bearing context was not staged or committed. M2I/shared runtime files and unresolved K6/G026 evidence remain in their original paths.

This report certifies preservation actions performed in this task, not a fresh checksum audit of every original data file.

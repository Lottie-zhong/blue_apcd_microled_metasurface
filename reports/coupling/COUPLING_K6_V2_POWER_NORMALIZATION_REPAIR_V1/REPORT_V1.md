# COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1

Status: first-case source-power repair and development ingestion PASS; the remaining 127 development entries are blocked pending a Runner authority-owner reconciliation.

## Scope and authority

Only K6LDA1_DEV_D1_M05/attempt_001 was imported. Its ordered geometry is [215, 195, 210, 150, 140, 210] nm, role DEVELOPMENT_LOCAL_AXIS, physical contract SHA 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. The archived run was already DONE with one historical solver entry. This repair added zero solver entries, zero replay, zero training/P_scale fits, and opened no confirmation responses.

The Runner independent physical audit is MEASURED, not a global physical-closure certification. The original FSP, H5, truth, raw fields, state, metadata, orders JSON, and rejection records remain unchanged.

## Power mapping and ingestion

The frozen mapping is source_fraction[m, lambda] = P_scale[lambda] * eta[m, lambda]. eta remains the seven-order grating fraction of monitor-total transmitted power. P_scale was recomputed from POSTNP full-period E/H flux divided by cell area and frozen IN_REF incident power per area, using actual x/y coordinates and trapezoidal endpoint half weights.

Across 21 wavelengths, raw-E/H P_scale matched Runner independently reported raw-E/H values with max absolute difference 0; monitor transmission times sourcepower matched integrated E/H flux with max relative difference 1.28925e-14. eta-sum max deviation was 2.22045e-16. P_scale ranged 0.0664911579 to 0.562036998. The archived source-normalized order fraction differs from corrected values by max absolute 0.169494001 and max relative 0.991849064; the original orders JSON is preserved.

The explicit, case-scoped supplement binds geometry, physical contract, six source artifact hashes, the recomputed P_scale/eta/source_fraction hashes, and the independent audit SHA. The unchanged default importer remains fail-closed. The first case was reloaded successfully through its explicit supplement; all state and power arrays retained their frozen shapes and provenance.

## H2/H1 consistency and limits

Truth C_hat and corrected truth P_scale passed as diagnostic predictions through unchanged H2 and original H1 attained the applicable one-case numeric checks. Routing RMSE was 7.10927e-05 (Pearson 0.999999835); source-normalized absolute-order RMSE was 1.98310e-05. State and total-power errors are zero by construction. This is not model performance, a dataset-level H1 result, or production admission.

The Runner audit measured a maximum POSTNP surface-flux vs 9x9 H2 modal-sum residual of 2.89567e-04 and an order-source-fraction vs independent modal flux residual of 1.49906e-03. No frozen direct-closure threshold was found; these values remain unclassified and no physical-closure PASS is claimed.

## Validation

Remote RCP_LCP test run: 47 passed. git diff --check passed; Git emitted only its existing LF-to-CRLF working-copy notices for the four modified Python files.

## Runner gate for remaining development cases

The live controlled_admission_authority_v1.json has SHA a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35, status OWNER_ENROLLED_SETUP_ONLY_SOLVER_DENIED, solver_entry_authorized=false, and max_solver_entries_per_case=0; all 160 geometry entries currently deny solver entry. Its linked development budget has SHA e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c and authorizes one entry for each of 128 development cases after the pilot ingestion. This is an unresolved Runner authority conflict. No fresh live owner/fence/startup check was performed and no follow-on case was entered. The GPU authority owner must reconcile the formal controlled authority with the authorized 128-case budget before the 127 remaining entries can be considered.

## Artifacts

See SHA256_INVENTORY_V1.json for hashes of task files, modified code, frozen authorities, and source artifacts. Read CONTINUATION.md first when resuming.

# COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1

Status: first-case source-power repair and development ingestion PASS; the remaining 127 development cases are held pending the main controller's explicit scientific gate conclusion.

## Scope and first-case result

Only K6LDA1_DEV_D1_M05/attempt_001 was ingested. Ordered geometry is [215, 195, 210, 150, 140, 210] nm, role DEVELOPMENT_LOCAL_AXIS, physical contract SHA 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. The archived run was already DONE with one historical solver entry. This repair added zero solver entries, replay, training/P_scale fits, or confirmation response access. The first case was not replayed.

## Power mapping

The frozen mapping is source_fraction[m, lambda] = P_scale[lambda] * eta[m, lambda]. eta remains the seven-order grating fraction of monitor-total transmitted power. P_scale was recomputed from POSTNP full-period E/H flux divided by cell area and frozen IN_REF incident power per area, using actual x/y coordinates and trapezoidal endpoint half weights.

Across 21 wavelengths, raw-E/H P_scale matched Runner's independent raw-E/H values with maximum absolute difference 0; monitor transmission times sourcepower matched integrated E/H flux with maximum relative difference 1.28925e-14. eta-sum maximum deviation was 2.22045e-16. P_scale ranged from 0.0664911579 to 0.562036998. The archived source-normalized order fractions differ from corrected values by maximum absolute 0.169494001 and relative 0.991849064; the original orders JSON is preserved.

The explicit case-scoped supplement binds the geometry, physical contract, six source artifact hashes, numeric P_scale/eta/source_fraction hashes, and independent audit SHA. The default importer remains fail-closed. The first case reloads successfully through the explicit supplement.

## H2/H1 diagnostic and physical gate

Truth C_hat and corrected truth P_scale passed as diagnostic predictions through unchanged H2 and original H1 attained the applicable one-case numeric checks. Routing RMSE was 7.10927e-05 (Pearson 0.999999835); source-normalized absolute-order RMSE was 1.98310e-05. State and total-power errors are zero by construction. This is not model performance, a dataset-level H1 result, or production admission.

The independent Runner audit reports transmission-times-sourcepower against full-period E/H flux within max relative 1.28925e-14. It also reports POSTNP surface flux vs frozen 9x9 H2 modal sum max relative residual 2.89567e-04 and max per-order source-fraction vs independent modal source fraction relative residual 1.49906e-03 (absolute 8.22044e-05). No frozen direct modal-closure threshold was found, and the main controller has not declared physical PASS. These modal residuals remain unclassified pending scientific review; no closure PASS is claimed.

## Runner authorization and stop

GPU owner and main controller confirmed the SHA-pinned K6 V2 development budget overlay is the operative Runner admission basis: exactly 128 unique frozen development identities, attempt_001, at most one entry per case and 128 total, replay=0. The first case consumed one entry; 127 are nominally available. The 32 confirmation entries, confirmation-response access, training and P_scale fitting remain denied. The 160 zero-entry geometry authorities are setup-identity controls, not a conflicting solver budget.

No fresh owner/fence/startup check has been performed for the remaining cases. Per the main controller's scientific gate, do not start them until an explicit conclusion resolves whether the measured modal residuals satisfy a frozen acceptance criterion. After that conclusion, perform fresh live owner/fence/budget/startup checks and formal Runner preflight, then proceed serially only if every check passes.

## Validation and artifacts

RCP_LCP pipeline tests: 47 passed. git diff --check passed with only LF/CRLF notices; this status correction changes records only, not code.

See SHA256_INVENTORY_V1.json for task, source and authority hashes. Read CONTINUATION.md first when resuming.

# V3 independent execution authority and numerical gate

The Coupling-owned V3_EXECUTION_LEDGER_V1.json starts at 0 entered / 0 truth-valid / 0 labels-valid / 56 unentered. Roles are 44 development, 4 numerical diagnostics and 8 sealed evaluation. The 56 scientific entries are approved; this ledger is not an ALLOW release. Never modify the old128 authority.

GPU V3Budget must use authorized_case_count=56 for total reconciliation. authorized_development_case_count=44 is deliberately not56. Preserve write-ahead conservative receipts, request/config/owner binding, one nonrepeatable launch, entry consumption on uncertainty and no replay. The existing V2 SQLite is execution mirror only. No sealed or diagnostic labels may be copied to the ordinary development ledger/report folder. Publish only development labels through the restricted consumer view; record sealed metadata/SHA under custodian ACL.

Diagnostic API: evaluate_ledger(ledger_pin, registry_pin, identity_pin). CLI:

`N:\anaconda_envs\RCP_LCP\python.exe "D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1\v3_execution_authority_v1\v3_diagnostic_gate.py" --input ABS_INPUT_JSON --input-sha256 FULL_SHA --output ABS_NEW_RECEIPT_JSON`

Input schema V3_COUPLING_NUMERICAL_GATE_INPUT_V1; fields ledger, registry, identity_authority each {path,sha256}. Ledger pin is the current post-four-diagnostic ledger SHA, not the initial SHA. Each diagnostic case_records entry must retain entry_consumed=true, phase V2_TRUTH_VALID or V3_TRUTH_VALID, and evidence={bundle,validation} from actual NativeTruthValidator. Bundle includes path/files/receipt_sha256; validation includes verdict/outputs/fresh_load_verified/actual_importer/native_session/record/labels_artifact. Its sibling validation.json must match exactly. Truth and labels must use original frozen scientific role DIAGNOSTIC_REPEAT or DIAGNOSTIC_MESH, not execution-role aliases. All56 registry must preserve original cohort roles.

The gate verifies bundle receipt and all native FSP/H5 hashes, finite six-component native fields, fresh-LOAD receipt, actual importer state reconstruction and exact label parity, baseline G001/G004 artifacts and source/evaluator pins. It compares every wavelength using the already frozen five conjunctive thresholds, no alignment or rescaling. Exit0 PASS, exit3 scientifically HOLD, exception means unverified evidence: never advance. Output is exclusive/create+fsync and SHA printed. It reads only the4 diagnostic identities and2 old approved development baselines, never sealed cases. It opens no Lumerical session and consumes no fit/entry.

No diagnostic receipt is produced now: no real V3 diagnostic truth exists. Consumer interface tested with actual non-elevated restricted token; synthetic fixture only. Final installed engineeringPASS plus independent scientific admission, signed finite release and time gate still required before entry.

# Fixed-v2 historical HF role transition

HF15 (15 geometries / 90 cases) is now `EXPOSED_DEVELOPMENT_ONLY`. Replacement R12 (12 geometries / 72 cases) is `CONSUMED_EXTERNAL_DEVELOPMENT_ONLY`. Together they provide 27 historical geometries / 162 cases for schema audit, profile-extractor development, compression smoke, and a fixed-v2 development seed only.

Neither set is an independent validation set, sealed test, or promotion evidence. Historical identity is preserved. This task read only manifest/schema/role metadata; formal label and diagnostic values read count is zero.

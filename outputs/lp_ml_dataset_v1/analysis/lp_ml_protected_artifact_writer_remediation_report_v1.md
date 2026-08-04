# LP protected-artifact writer-chain remediation
 
 ## Root cause
 
 The post-start drift was produced by explicit report-generator invocations: scripts/lp_ml1/lp_ml1a3_git_history_geometry_reconstruction.py and scripts/stage11_4a20_legacy_fsp_object_inventory.py each had direct Path.write_text calls targeting a protected report. No import-time execution, scheduler, hook, or second writer was identified in the auditable source tree.
 
 ## Remediation
 
 - configs/lp_protected_artifact_manifest_v1.json is the versioned deny-by-default manifest.
 - scripts/lp_protected_artifact_guard_v1.py resolves absolute/case-insensitive Windows paths, realpaths, traversal, and replace targets before every write.
 - Both writers now default to outputs/.../derived_reports/.
 - An explicit protected target fails before any write.
 - Read/hash/stat/inspect operations remain allowed.
 - Static scan and runtime tests cover import, dry-run, case variants, traversal, and temporary replacement.
 
 The existing incident evidence and accepted attestation were not restored or rewritten.
 
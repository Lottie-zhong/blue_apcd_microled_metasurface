# Runner V3.1 read-only defect handoff

Installed runner: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\minimal_batch_runner_v3.1_final.py
Pinned installed SHA: 9d380e62f265cb7ca3d4398a9831dd8358362223d09fc5476a436b4f2582be33 (verified against deployment_manifest).

All tests used isolated cwd and --db under this task fake_runner_fixture; --fake-solver only; no real entries or production writes.

1. Resource gate source checks its file mutex only. It does not independently detect external Lumerical engine/GPU consumers or verify owner/fencing. Current snapshot has multiple FDTD GUI sessions and1805MiB GPU memory;0% utilization is not ownership proof. Production remains HOLD. Please establish/confirm the supported independent fail-closed resource ownership gate; do not kill or adopt unknown processes.
2. CLI run returns process0 even when run_batch returns failed>0. Callers can misread success; scientific acceptance must reconcile DB/output. Please verify/correct exit semantics in a separately owned candidate; do not modify installed platform for this request.
3. submit accepts intentionally wrong input SHA. Evidence: three marked fake manifests. Please clarify platform prelaunch SHA verification contract; Coupling will retain independent source/contract verification.

Scope separation: case/attempt/budget identity registry, immutable sidecar, native H5/EH export,609D and dataset ingestion remain Coupling responsibilities. Cross-batch same input acceptance is evidence that Runner job_id alone is insufficient for science No Replay; we are not requesting a new science platform. No scheduling, installation, enabling, real submission or solver execution is authorized by this handoff.

Reproduction: FAKE_BACKEND_E2E.json (all CLI argv/stdout), RUNNER_V31_INTERFACE_AUDIT.json and RESOURCE_READONLY_SNAPSHOT.json. The two synthetic fake rows are not science entries and must never be merged with production.

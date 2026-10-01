# APCD GPU Production Runner V1

## Authority and scope

This document records the bounded V1 implementation contract and the user's conditional authorization for one S35 canary, followed by S39 only if S35 reaches DONE. Execution is blocked until the approved pre-FSP artifact and its matching SHA-256 are located and pinned; no canary has run. Deployment, database mutation, and release of the existing production hold are outside this authorization. The V1 runner is filesystem-authoritative and isolated from the Shared V3 database, lease, and queue path. The one Shared V3 change rejects GPU work before acquisition; CPU dispatch remains available.

Implementation source: commit `f41f1b6823d04b2ad93f4d95792005fbbf6a1f3e` on branch `codex/apcd-gpu-production-runner-v1`; worktree: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`.

The only approved cases and ordered geometry inputs are:

| Case | Ordered D (nm) |
|---|---|
| `K6V1_S35` | `[110, 145, 225, 105, 185, 215]` |
| `K6V1_S39` | `[175, 100, 125, 120, 100, 230]` |

The manifest must carry physical contract SHA-256 `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5` and expansion manifest SHA-256 `4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f`. S39 is rejected until an S35 attempt is recorded as `DONE` in the V1 registry.

## Input and run behavior

`adapter.py run-one <case_manifest>` accepts the runner manifest fields `case_id`, `attempt_id`, `run_id`, `geometry`, `physical_contract_sha256`, `expansion_manifest_sha256`, `pre_fsp_path`, and `pre_fsp_sha256`, plus required `physical_contract_path`. The contract file bytes must match the frozen contract hash. The pre-FSP must exist and match its declared SHA-256. Missing or mismatched input fails before solver entry; the CLI does not select or invent a pre-FSP.

The adapter imports only the immutable standalone launcher bundle at the path and hash recorded in the authority JSON. It does not call the legacy V3 `validate_config` function. `APCD_GPU_RESOURCE_NAME` is required; `APCD_FDTD_SOLUTIONS_EXE` may select the Lumerical executable. Fresh-load monitor validation and postprocessing must produce canonical state artifacts and pass the launcher’s explicit order-sign, reference-plane de-embedding, and lossy-GaN checks before the V1 state can become `DONE`. Run identity is recorded in manifest, status, logs, validation, and HDF5 metadata.

The V1 production CLI always uses the single global root D:\apcd_runtime\gpu_production_runner_v1; it exposes no output-root override. The root contains one exclusive lock and one active-run marker (slot_count=1, serial execution). Tests may inject temporary roots through the Python API. The V1 runner enforces pre-FSP pinning, durable solver-entry state, retry/no-replay rules, and atomic status/registry files. A run is counted as entered once the durable `SOLVER_ENTERED` record is written. S39 gating and identity are based on registry/status evidence, not Shared V3 state.


## Global root and GPU capacity snapshot

The sole production command is adapter.py run-one <case_manifest>. It always writes under D:\apcd_runtime\gpu_production_runner_v1; a caller cannot select another production lock/output root. The root-level exclusive lock enforces one serial GPU slot.

Before entry, the read-only GPU snapshot records UTC/Unix capture time, requested logical resource name, each visible GPU's index/UUID/name/total-used-free memory/utilization, and visible compute-app PID/name/used memory plus the external-or-unattributed consumer list when available. An unavailable process query is recorded and does not block a run by itself; no process is killed. The existing free-memory gate remains 1369 MiB. Below that threshold, the call returns WAIT_GPU_CAPACITY as a non-scientific result, leaves status and registry PENDING, and records no solver entry. The same immutable run_id may resume when capacity is sufficient; a different run_id cannot bypass that pending attempt.

The 1369 MiB value is retained from the prior V3 authority, which states it is the ceiling of a validated 1.336057 GiB peak. A bounded read-only audit did not verify that peak against clean successful S35/S39 GPU-canary evidence: the cited A3 record has contradictory terminal success/failure markers, and A4 is an infrastructure exception canary rather than S35/S39 GPU execution proof. This V1 retains the existing value without inventing a replacement and records the evidence limitation in the authority JSON.

## Execution boundary

No Lumerical/FDTD solver has run under this V1 implementation. S35 and S39 are NOT_RUN; canary run_id is null, solver_invocations=0, replay_count=0, and production_ready=false. The user conditionally authorized one S35 canary and S39 only after S35 is DONE, but execution remains blocked until the approved S35 pre-FSP path and SHA-256 are located and pinned. Tests use temporary fixtures and injected callbacks only. The V3 GPU guard is covered with a temporary control database and does not alter production control state.

Next action: locate and pin the approved S35 pre-FSP path and exact SHA-256, then verify the physical contract artifact. Do not start S35 before those inputs are verified. Do not retry after any durable solver-entry record; reconcile the existing run evidence first.

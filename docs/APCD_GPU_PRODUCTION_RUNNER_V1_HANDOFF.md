# APCD GPU Production Runner V1 handoff

**Status:** READY

**Frozen Runner HEAD:** `dede87c3aaa210892fd4dcbe67e92fabfe5c9c4c`

**Branch:** `codex/apcd-gpu-production-runner-v1`

## Operational entry point

The Runner is GPU-only, single-slot, and serial. Use the remote Windows host and the pinned runtime:

```powershell
$env:APCD_GPU_RESOURCE_NAME = "GPU license audit"
& "N:naconda_envs\RCP_LCP\python.exe" `
  "D:\project\worktreeslue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1dapter.py" `
  run-one "<immutable-case-manifest.json>"
```

The CLI envelope contains the eight core fields `case_id`, `attempt_id`, `run_id`, `geometry`, `physical_contract_sha256`, `expansion_manifest_sha256`, `pre_fsp_path`, and `pre_fsp_sha256`, plus `physical_contract_path`. The Runner validates the exact core schema, contract hash, and canonical FSP hash before entry. Create one immutable run ID for each logical attempt. Wait for a terminal state before dispatching the next case.

## Input and validation contract

The accepted S39 mesh authority is `PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1`; its canonical setup FSP SHA256 is `23c7d66cf8a73dc838b772c1cae048464451b0cb1584f3305d10938a2ebafe0d`. The PW contract SHA256 is `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5` and the admitted expansion manifest SHA256 is `4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f`.

Before solver entry, the setup validator LOADs the unsolved FSP and checks geometry, ordered pillars, MDC/spacer/materials, source and polarization, wavelength range, boundaries, monitor objects and planes, mesh objects and resolution, and the frozen contract. It does not require result d-cards or call the solver. After solver return, the existing post-run validator stays strict: it requires monitor result data, finite complex E/H, native H5, post-run FSP, C_PW, reflection/transmission/order power, P_scale, closure, truth H5, and a fresh LOAD.

Before each dispatch, dependency preflight verifies `mdc_tmm_complex_incident_power_v1.normal_stack_power` from authority commit `46af82357f269aea0c77105a03e7ca9da645ca8f` at SHA256 `12d2d95bd99fc6e18fec9ac17ab066a5a1fc4a3ddf1a6e5a8c0a625da959ff4b`. Pre-entry also requires free Runner ownership and enough GPU headroom.

## State and failure behavior

Successful cases progress automatically through `PENDING → PRECHECK_PASS → SOLVER_ENTERED → SOLVER_RETURNED → TRUTH_VALID → DONE`. A pre-entry failure is terminal for that dispatch and must be inspected. Once `SOLVER_ENTERED` is durable, never replay the attempt; a post-entry failure remains `FAILED_POSTENTRY` and needs separate authorized recovery.

S35's original execution remains `FAILED_POSTENTRY`; its separate pinned LOAD-only recovery derives `RECOVERED_TRUTH_VALID` without rewriting the original status or inventing process lineage. Only that exact recovery evidence qualifies S35 as a completed predecessor. Other failed post-entry attempts do not qualify automatically.

## Outputs and qualified cases

Runs are stored under `D:\apcd_runtime\gpu_production_runner_v1\runs\<case_id>\<attempt_id>\<run_id>`. The primary artifacts are `run.fsp`, `run/run_output.h5`, `truth.h5`, `validation.json`, and the `gpu_standalone/forensics` process-exit and runtime-timeline sidecars. For a serial batch, dispatch one approved manifest, wait for and verify terminal truth, then continue to the next manifest.

Qualified Coupling Stage-1 cases for this handoff:

- `K6V1_S35`: effective status `RECOVERED_TRUTH_VALID`; original status unchanged.
- `K6V1_S39`: clean end-to-end canary, `DONE`, one solver invocation, zero replay.

No remaining Stage-1 cases were launched in this qualification. The S39 final `status.json` does not retain its `solver_process_lineage` field after `SOLVER_RETURNED`; the matching hashed `process_exit_provenance.json` and `runtime_timeline.jsonl` record the run-specific launcher, MPI, and GPU engine evidence. See the evidence file for their hashes and PIDs.

## Qualification evidence

- Canary: `S39-20261002T075624Z-30a1c44a`
- Evidence: `reports/apcd_gpu_production_runner_v1/S39_CANARY_20261002.json` (SHA256 `06338557e28a473e880d5becd057b4c5b24ccf40b49e6758203bb360bf778a3a`)
- Handoff JSON SHA256: `fdab520bdc15c6131a7838c0ddda5e745952f8f52af0461f88108d416d07ee95`

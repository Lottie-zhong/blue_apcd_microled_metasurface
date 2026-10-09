# Old-platform conflict audit and V2 cleanroom decision

Audit date: 2026-10-09. Scope: installed Runner/Controller/Worker, official current configuration and request chains, pinned backend, Scheduler COM readback, relevant Git history, native result lifecycle, isolated offline replacement. Scientific solver invocations: **0**. Existing truth was read only. Sealed response files were not accessed. Configuration inventory includes authority/budget files and active/historical relevant requests; confirmation identities in policy metadata are not scientific response access.

## A. Configuration and state ownership matrix

Paths below are relative to V1 `scripts/shared_fdtd/gpu_runner_v1`, Coupling `scripts/coupling_ml/k6_v2_pipeline`, or the named runtime. Exact source SHA and full live snapshots are in `reports/final_evidence.json` and the forensic directory in the context document.

| Domain | Authority and actual value | Comparison and evidence | Finding |
|---|---|---|---|
| GPU resource/call | Coupling `serial_queue.py:53`, worker immutable request, user FDTD resource XML: `GPU license audit`; nProc/nThread/capacity 1 | Pinned launcher `pw_scientific_launcher.py:299` emits explicit `run("FDTD","GPU",resource)`; `:292` uses `-nw -hide -trust-script -run script run.fsp` | Three definitions currently agree. GUI `gpu-mode=false` is overridden by explicit run; it is not proof of CPU dispatch. |
| Python/install/env | Installed tasks use N: RCP_LCP Python 3.10.20; N: v251 Lumerical and lumapi | C: path in generic guidance is absent. Process environment has `ANSYSLMD_LICENSE_FILE=1055@DESKTOP-NNE313K`, CUDA toolkit v13 alongside Torch CUDA12.1 | Task actions match current environment. Stale generic paths are documentation drift; mixed CUDA packages need separate backend qualification. |
| Task identity/action | DELL InteractiveToken, PT0S, IgnoreNew, no trigger; controller action points to current Coupling source; worker action `task_scheduler_v1.py worker-once` | COM readback: controller Ready / LastResult2, worker Ready / LastResult0. Current request faa47… / current source 5f6a… | Current action hash agrees. Logout/reboot persistence not qualified. Operational event log disabled; no causal event reconstruction claim. |
| Controller status/report_root | Coupling status constrained to active queue report directory | Coupling `serial_queue.py:357–366`; Runner `task_scheduler_v1.py:1409` accepts broader Coupling root | **Proven differing admissible sets**. Historical bbb7… startup failed `CONTROLLER_STATUS_PATH_OUTSIDE_REPORT_ROOT`; faa47… now has valid report path. This resolved historical incident is not today's self-lock defect. |
| Legacy Scheduler generation | Strict new task contract required PT0S; old omitted value read back PT72H | Git bc5dd05c / d4dc99fd / a8a09213 describe compatibility/rebind; current COM PT0S | Historical mismatch resolved; not a present launch blocker. Versioned migration was required across state/action/config. |
| Worker/Runner/closeout scope | Worker owns `scheduler_worker_v1.lock`; Runner owns `.runner.lock`; closeout receipt should describe past run | Runner `runner.py:290` creates self lock, `:349–350` calls owner probe; Worker creates lock before run_cli; `adapter.py:1204–1252` checks historical failed entries | **Current deterministic cross-state self match** (see reproduction below). Global present-state markers invalidate past terminal receipts. |
| Request/owner/fencing | task request SHA, lock PID, run manifest/status and request result are separate records | `runner.py:_verify_pre_entry_ownership`, Worker immutable request, controller binding | Current request SHAs align. V1 has several independently interpreted owner/state records; only filename locks are not sufficient proof of process ownership. |
| PID/creation identity | Some newer lineage has creation times; older G023 PID42488 and D6M05 PID37252 lineage does not | `adapter.py:1183` ctypes OpenProcess lacks explicit signatures; current census includes creation times and parents | **Coverage gap** for legacy PID reuse; no claim current old PIDs are live. Win64 ctypes handling is a static risk requiring qualification, not a proven present failure. |
| Manifest/receipt/report SHA | faa47… manifest, task binding, live controller source, stopped status | Request source SHA matches live 5f6a…; worker request adapter SHA matches live defab… | Hash pinning works for inspected chain; Coupling's source has existing dirty state and requires snapshot pinning, not just HEAD. |
| Solver-entry/truth/budget | Runner entry records; Coupling label and aggregate ledger | 38 entered / 34 truth / 34 labels / 90 unentered; G026 entry consumed; G027 two entry0 failures | Entry and truth deliberately differ. Immutable starting counters are historical lineage; do not misinterpret them as current budget or refund. V2 cannot migrate/overwrite counters yet. |
| FSP/H5 save/read/recovery | Pinned launcher reads monitor E/H then save; adapter fresh-load reads without layout/save | Native G025 `run.fsp` + `run/run_output.h5`, original hashes match, four full E/H groups readable by HDF5 | Current production pair exists. Current reachable post-run path has no `switchtolayout`. Older helper `gpu_bundle.py` publishes individual files without whole-directory transaction/fsync; it is not the pinned launch path and is only a latent helper risk. |
| GPU pre-entry systemcheck | Existing general report `MEDIUM_PW_GPU_SYSTEMCHECK_V1.json` | Runtime code scan finds no exact-case `runsystemcheck("FDTD","GPU")` call in current admission path; general report reports 531908680–622929568 bytes | Exact G027/pre-FSP hash binding and supported-feature acceptance are **not proven**. No solver/API check was launched to fill the gap. |

### Deterministic current defect

`postentry_failure_closeout_v1.py:29–32` refuses any `active_run.json`, `.runner.lock` or `scheduler_worker_v1.lock`. Both the generic validator (`:138`) and legacy validator (`:221`) call it. `adapter.py` treats false validation of historical `FAILED_POSTENTRY` without lineage as owner activity, even when the only marker is its own current Worker/Runner lock. The direct self-PID exclusion at `adapter.py:1210` is bypassed through this nested historical path.

Actual installed code plus actual G024/G026 receipts was exercised with marker existence and self PID injected **only in memory**:

| Scenario | owner_probe | G024/G026 closeout |
|---|---|---|
| Existing clean runtime | false | true / true |
| Synthetic own Runner lock | true | false / false |
| Synthetic own Worker lock | true | false / false |

Evidence: `reports/self_marker_reproduction.json` (original under V1 forensic diagnostics). No real production marker was created. This proves a pre-entry protocol defect independent of GPU resource/mesh/solver parameters. The past G027 exception did not record its matched object, so exact historical matching lineage is still unknown.

## B. V1 decision

Stop incremental V1 repair under the latest task. A narrowly scoped change could plausibly fix the reproduced owner gate; **evidence does not prove that no single boundary repair is possible**. It also does not prove such a fix would safely restore G027: status path validators, legacy task migration, PID identity coverage and exact-case systemcheck have independent boundaries. The documented present cross-module self match and differing status-root contracts justify a separate minimal implementation and explicit qualification instead of claiming that another gate patch yields production readiness. No V1 patch was applied here.

## C–E. V2 implementation, reuse and verification

Independent code and state are described in README and context. SQLite is the single state/budget/owner authority; separate modules inspect processes and preserve native pairs. Native launch specifications follow the verified official interface, but dispatch is disabled. No old lifecycle/scheduling source is imported. Dependencies are already installed; no production installation occurred.

| Reference | Audited version / condition | Adoption |
|---|---|---|
| Pydantic | installed 2.13.4 | Strict BaseModel/config validation; exact dependency pin |
| pydantic-settings | not installed; [upstream MIT](https://github.com/pydantic/pydantic-settings/blob/main/LICENSE) | Not added. One explicit JSON without automatic env/default precedence satisfies strict config scope. |
| psutil | installed 7.2.2; [BSD 3-Clause](https://github.com/giampaolo/psutil/blob/master/LICENSE) | Process identity/census only; no kill |
| SQLite | Python stdlib runtime; version in acceptance report | Atomic offline task/event/slot ledger |
| h5py / NumPy / pytest | 3.16.0 / 2.2.5 / 9.0.3 | Existing offline integrity and targeted testing |
| [ansys/pylumerical-mcp](https://github.com/ansys/pylumerical-mcp/blob/main/pyproject.toml) | main reports 0.1.dev0, Python >=3.12; local interpreter 3.10 | Not adopted; incompatible current Python requirement. Native vendor lumapi/CLI specification retained. No copied upstream implementation. |
| WinSW | upstream v2 inspected, [MIT](https://github.com/winsw/winsw/blob/v2/LICENSE.txt) | No selected binary version, installation or deployment. Future service wrapper is a separate decision. |
| TorchFDTD | upstream main pyproject 1.1.7; Python >=3.10, Torch >=2.4; [MIT](https://github.com/hyoseokp/TorchFDTD/blob/main/LICENSE) | Read-only assessment; not installed/imported/adopted |

Fault suite covers concurrent real-process duplicate claims, concurrent case registration, a real spawned process `os._exit(73)` after durable entry commit, fake process/network failure, missing/corrupt H5, PID reuse/access denied, wrong request/fence/config/hash, partial save, license preflight failure, forbidden native backend, and reader failure/mutation. Final test count and lint/CLI results are recorded in `reports/acceptance_summary.json`, JUnit, pytest and lint reports. Tests run only the isolated fixture suite. Windows fsync on read-only descriptors and path-separator mismatch were fixed in V2; LOAD-only failure-path hash checking and offline source/root protection were added and tested.

## F. Coupling scientific contract compatibility

Existing G025 development labels were used read only. Source NPZ SHA `09b8953c10d7ce9f35bc33c8fa0d1f3239e5c593a1d070837dfb18381e74cfa8` and consumer source SHA remain unchanged. Complex `(21,7,2)` C_hat plus `(21,)` positive P_scale roundtrips through actual Coupling `contracts.py` as 609 real outputs. This proves representation/packing compatibility. Full production manifest, trusted Runner receipt, importer, reference normalization, monitor-plane/mode convention and native FSP semantic LOAD qualification are not claimed. Fake labels never enter Coupling or gain scientific truth-valid status.

G025 pair: FSP 170552540 bytes SHA `be006f194b07df6d19105812ca49fdce5a8d9660fff983559f91c9d3fc948572`; native H5 76560937 bytes SHA `5e00289a1615d1f102cff0b7ce3fda73e00589be78371934c9c935349de3ec9c`. All Ex/Ey/Ez/Hx/Hy/Hz datasets in four monitor groups remain HDF5-readable and finite. No new native LOAD session was opened during this audit.

## Official mechanism and TorchFDTD feasibility

Official [GPU execution](https://optics.ansys.com/hc/en-us/articles/49708199997971-Running-GPU-simulations) supports explicit GPU run selection and runsystemcheck. Current explicit resource dispatch conforms; per-case pre-entry report binding remains missing. The [single-node resource guidance](https://optics.ansys.com/hc/en-us/articles/49707848532243-Resource-configuration-for-single-node-GPU-simulations) separates GPU resource selection from license capacity; current resource nProc/nThread/capacity is 1. Existing preflight artifacts prove historical checks, not today's transferable license checkout.

Official [GPU results guidance](https://optics.ansys.com/hc/en-us/articles/49708268223251-Accessing-GPU-results) requires preservation of the FSP and external same-stem result directory and warns about layout/save removal of GPU result data. Actual 2025 R1 uses `run/run_output.h5`; the validator preserves that observed name rather than imposing a newer generic name. The inspected launch follows official [Windows CLI flags](https://optics.ansys.com/hc/en-us/articles/360024812334-Running-simulations-using-the-Windows-command-prompt).

[TorchFDTD boundary documentation](https://github.com/hyoseokp/TorchFDTD/blob/main/docs/BOUNDARIES.md) describes 3D periodic/Bloch axes mixed with CPML, dispersive ADE, and different staggered E/H treatment. APCD 3D periodic x/y + z-PML + dispersion + complex E/H DFT is therefore an independently testable research candidate; equivalence to native Lumerical is unproven. Dispersion crossing CPML and matching power/phase/reference normalization need dedicated benchmarks. Changing to absorber or freezing dispersion would change the frozen contract. Installed Torch 2.5.1+cu121 meets coarse minimums, but upstream Windows tested CUDA12.6/Torch2.10 differs; no compatibility/performance claim, installation or second formal Runner was made.

## G–H. Production gates and delivery

**G027 is not READY for official recovery.** First resolve unknown process owners and prove no V1 dispatch/engine can coexist with V2. Current readback has no engine or marker and V1 probe false, but eight API servers remain; two have unidentified stdin Python parents. Another old stdin Python exists. Do not kill them or infer ownership from age alone. This audit process's own stdin PID is transient and must be excluded by PID/creation identity.

Before real entry: separately qualify native LOAD/FSP roundtrip, exact-case GPU systemcheck and actual license resources; validate full Coupling receipt/importer and imported monotonic budget; review exclusive cutover and durable execution/descendant observation; obtain formal scientific first-launch authorization. No production deployment or migration was performed. A service/forced-release/production dispatcher is absent by design in the offline MVP.

Remote final artifacts: `D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1\platform_v2`. Base HEAD `a8a09213d14883349921e5432daacd72f2ee7bb4`; delivery HEAD/status and exact staged allowlist are recorded after commit outside Git in `D:\apcd_runtime\gpu_platform_v2_offline_20261009_v1\delivery_git.json`. V1 and Coupling original Git state is preserved. No large scientific artifacts, credentials or existing unrelated dirty files belong to the V2 commit.

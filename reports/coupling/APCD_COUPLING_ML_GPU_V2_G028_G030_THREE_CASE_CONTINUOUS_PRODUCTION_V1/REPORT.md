# G028–G030 three-case continuous scientific production

Status: PASS. Three real 3D GPU FDTD cases completed on one server Controller; no per-case restart or science recovery.

## Actual results

|Case|Entry/replay|Native + fresh LOAD + 609 importer + dual ledger|Engine observed→return (s)|End-to-end (s)|Fresh LOAD (s)|
|---|---|---|---:|---:|---:|
|K6GDP2_DEV_G028|1 / 0|PASS|561.951|710.392|108.602|
|K6GDP2_DEV_G029|1 / 0|PASS|557.935|710.851|110.529|
|K6GDP2_DEV_G030|1 / 0|PASS|558.300|708.994|110.935|

Baseline39 entered /35 truth /35 labels /89 unentered; final42 /38 /38 /86. Added3 truth-valid and3 labels-valid. Original failed attempts retained; no refunds or replay. G031 entry0; confirmation32 untouched. Training/P_scale fits0.

Controller PID32848, one invocation, instance7351C470-21E0-4786-B066-3D484508A30A, exit0. Runtime remains independent of the launching SSH helper. Controller lifetime 2134.048s.

K6GDP2_DEV_G028 truth terminal → K6GDP2_DEV_G029 owner claim: 0.554156s. The same controller completed next-case preflight and entry without a manual dispatch.
K6GDP2_DEV_G029 truth terminal → K6GDP2_DEV_G030 owner claim: 0.753495s. The same controller completed next-case preflight and entry without a manual dispatch.

## Installed authority / final task

Installed a09655cd577d7618d3080d35b7a5b2a4a5fc52c5; Coupling scientific input at8b8c632296536d8a66d0b9612be10ef5756cc3da. Three-case binding30c2198299f8312cf1f68c627a18abf17bb26c18a45746f4c33a3d791b8844ec; configdigesta680a52857909b417e36b8d048bb24b27b9861534c502b1a5e1a2bf563060423. Finite2hour ALLOW binds exact queue9dddeb94666cb2f478db3104d9f1ed63548db7ee118b6e1cc045e78165af6ca2; historical DENY and consumed G027 never modified.138 installed/scientific source bindings independently checked.

Actual final Scheduler COM readback: Disabled,0 instances, LastTaskResult0, PT0S, IgnoreNew, AllowStartOnDemandfalse, DELL InteractiveToken/HighestAvailable. Action uses RCP_LCP absolute interpreter and installed a09655cd Controller. Default binding restored DENY/requests[]; slotempty. PT0S does not establish logout/reboot durability; interactive login remains a dependency. No logout/reboot/engine termination test performed.

## Science input and output

Only independently pinned D1…D6 changed. Fixed12-layer MDC,237nm spacer, TiO2 K6 height500nm,1740×290nm cell, source/PML/5nm mesh/material/monitor contract unchanged. Physical contract SHA32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. Reference1722nm,440–460nm21 wavelengths, transmitted orders m=-3…3/n=0, output TE/TM. This is one incident polarization full complex state, not a complete Jones or multiport scattering operator.

Each durable label has C_hat_real/imag [21,7,2], actual positive finite P_scale [21], routing and absolute-order [21,7]. All native monitor groups retain Ex/Ey/Ez/Hx/Hy/Hz; vendor42real channel packing corresponds to21complex wavelength channels. Real fresh LOAD and frozen importer executed inside production, not repeated by final audit. Case/attempt/geometry and source/truth/label SHA agree; independent publication receipts record zero fits/replay/confirmation.

## Artifact identity

|Case|Native FSP SHA256|Native H5 SHA256|609D labels SHA256|
|---|---|---|---|
|K6GDP2_DEV_G028|58f0d863049970015df4bbd32f319e6262144fbf93147c38171aee167bff8ad1|f98cc9237169f1f2afccee2c28a7c70e1ec36b4ff4e08b481b6c37f74190137c|d98a91e6f894dd5cf40f6458fbd6c47d5873d4e24da19f52e475dddea8ba1777|
|K6GDP2_DEV_G029|4f63192b178292e180807fbe0deb388501c47ac4c9b049e2cb50f3f3b73b242b|9faf5b448422b011d2d034420b61bc1d87dcc960a300ad1f34a75acca870753f|fa5cd5506ebd0c15e6da65627cb9968da933445f1bb11b34b55a756ef3c78d11|
|K6GDP2_DEV_G030|dbb0a951c676d2d941e6d67030bc7c625730e90e5fd1b921be5267ac12b376a6|be603e2e288da1b6a328fb18c7b50075695bad5e8edad3d8d286996438464e15|1726fc305bec7cc3e2fbdbdc72d9f3d329a4324acb1033b7b27a58e35d82cb24|

Full absolute paths and SHA bindings are in FINAL_SCIENTIFIC_AUDIT.json and SHA_INVENTORY.json. Large scientific files stay in canonical runtime archives; none is added to Git.

## Diagnostics and checks

Read-only final audit PASS: unique engine identity and process-return0 per case; three distinct labels;21λ/order/polarization/orderedgeometry/finite state/P_scale; native field schema; actual importer and fresh LOAD; published labels and ingestion receipts; Coupling/V2 state/entry equivalence; truth-terminal strictly before next entry; oneController; exact42/38/38/86; G031unentered; slotclear; replay0/confirmation0. Private process commands are represented by SHA;3 public-report serialization checks PASS,0 fits/LOAD/entry.

|Case|H2 vs native-grating routing maxabs|Absolute-order maxabs|H2 total vs P_scale maxabs|
|---|---:|---:|---:|
|K6GDP2_DEV_G028|8.56182278e-05|6.18447424e-05|0|
|K6GDP2_DEV_G029|0.000169765089|7.95705698e-05|0|
|K6GDP2_DEV_G030|0.000274758331|0.00013407107|0|

These are descriptive same-run decoder/native-grating differences; they are not an independent solver convergence test or a new gate. Original H2 and scientific thresholds unchanged. No ML H1/production admission claim.

## Engineering issue / limits

One local dispatch bookkeeping helper raised NameError after the successful Scheduler Run. GPU owner reconstructed the receipt from durable dispatch response and the same TaskInstanceGuid; no redispatch. This metadata correction is retained in DISPATCH_RECEIPT_RECOVERY.json. There were0 postsolver HOLD/failures and0 manual scientific recovery for G028–G030. An audit SQL query used the wrong event column id initially; corrected to actual seq without runtime mutation. No production code or frozen authority changed in Coupling.

Engine-observation→launcher-return includes solver/lifecycle/save tail; it is not pure kernel-only solve time. The available instrumentation does not isolate FSP/H5 save duration from that interval. Per-case preflight, launcher, return→LOAD, LOAD and terminal timing are preserved in the owner TERMINAL_AUDIT.json. Three-case continuity and SSH-independent execution are verified; logout/reboot persistence, cross-run repeatability and mesh/monitor numerical convergence remain separate untested claims.

## Recovery / next boundary

Read this report, CONTINUATION.md, source admission/protocol, FINAL_SCIENTIFIC_AUDIT.json, FINAL_TASK_AND_OWNER_RECEIPTS.json and SHA_INVENTORY.json. Owner runtime evidence: D:\apcd_runtime\gpu_v2_g028_g030_three_case_production_20261010_v1. Controller stopped/Disabled/DENY; do not resume consumed cases. This demonstrates three-case continuous production and supports review of a next ten-case batch. A new explicit science authorization and finite owner binding are required; no G031 entry is authorized here. Preserve the unrelated index/workspace.

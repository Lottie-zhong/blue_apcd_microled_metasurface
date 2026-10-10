# G027 first installed-V2 scientific validation
Status: PASS for G027 attempt_001 after zero-solver LOAD-only recovery. This is one-case scientific execution/label validation, not ML H1 admission or continuous-batch qualification.

## Authorization and immutable binding
APPROVED_G027_ATTEMPT001_SINGLE_ENTRY_ONLY. Only K6GDP2_DEV_G027 / attempt_001, DEVELOPMENT_GLOBAL, ordered D=[105,105,220,105,180,135] nm.
New ALLOW release SHA: 8cdab17f77b489b16d08c955f8b1cf89fd20279319deb14c58ff70fb95f030bf
Request digest: 21d704180e0547dc8995d8835438874c0710231012b23ab090948cfe08277d0a
Admission digest: d7761eb54cb4eb74721d12e9d40ea1a04b96718c4302381a2aca5dbe3cfce132
Request file SHA: fd4ff3364445bd8c1f0d3c3430139f5a09c3b461d8daa4905e11976f8cd040fa
Configuration digest: e714c92cf5a8d3f4b136718f5afb3987348042799b4a64f52b50aac7f2cc5425
Queue SHA: fbcac249c59e3f242e48dfa16a8e92298c98bab48f5fe7256900b8feed10bca7
Physical contract SHA: 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5
Pre-FSP SHA: b5c6b41d28e55984d9cebd1f15814f698b408350b2cbeac02336b200bc72271e
Source-manifest SHA: ee378c38a278e5edc52f8c639596b10a055ed4f2afacf8623e8962d0521d9a7c
Old DENY and initial ALLOW were preserved; the consumed request was not rewritten.

## Actual execution
Existing Scheduler task APCD_GPU_V2_SERIAL_CONTROLLER launched installed serial_controller.py with RCP_LCP Python and CONFIG/REQUESTS paths from BINDING.json. Actual task: PT0S, IgnoreNew (2), DELL InteractiveToken (3), existing highest token (RunLevel=1), no triggers. SSH startup helpers returned; a new connection independently observed the matching GPU engine PID26328, ancestry and project path. No Legacy CLI or new dispatch platform.
Unique scientific entry=1, unique matching GPU engine=1, PROCESS_RETURNED returncode=0. Engine log identifies NVIDIA GeForce RTX3080 and successful simulation completion.
Launcher-to-return: 568.169 s. Engine-observed-to-return: 561.889 s (includes final engine/save tail; not a pure kernel timer). New owner claim-to-final truth/label terminal, including dependency diagnosis and LOAD-only recovery: 919.265 s. Zero-solver recovery itself: 122.745 s.
After natural controller exit, task was disabled/demand-start rejected at this one-case boundary. LastTaskResult=1 is preserved from the original postprocessor exception; recovery success is recorded in the formal ledger, not forged Scheduler history. Slot is clear; no active scientific controller/engine remained.

## Truth and Coupling labels
Native FSP: 170552540 bytes; SHA 4c024449de21d53a0103669f377bb83f919335d8ba910c47ef4e0603caeabaab
Native H5: 76465042 bytes; SHA 91202ff6a9ea05bd89fcffeebeab53f9a081ed2e0247513b52ebc279b1438483
All native Monitor groups contain finite Ex/Ey/Ez/Hx/Hy/Hz datasets. Native datasets are float32 with stored last dimension 42; the fresh native LOAD separately verified complex E/H, coordinates and 21 wavelengths for contracted monitors. This is not coordinates-only H5.
Archived pair inventory and fresh LOAD preserved identical SHA. Scientific order-sign, reference-deembedding and lossy-GaN checks PASS. The 609D importer used the frozen H2 hash, actual POSTNP full-period E/H, 21 wavelengths, orders -3..3 and TE/TM. Original order-source-power consistency tolerance rtol=1e-3/atol=1e-9 was unchanged.
Labels: C_hat(21,7,2) complex =588 real coordinates, independent positive finite P_scale(21)=21 outputs. Label SHA 5ef446df8c570ede28902ce8171b443d3b2f9931abac70114323760c5a685766. P_scale range 0.102912396461..0.770850968068.
eta-sum max error 2.22e-16; summed absolute-order versus P_scale max error 1.11e-16. These algebraic factorization checks are not independent absolute-energy/convergence validation.
V2 TRUTH_VALID and Coupling V2_TRUTH_VALID agree on archived bundle. Truth-valid/labels-valid ID sets match.

## Preserved failures and minimum repairs
First start: protected desktop GPU identity AccessDenied under Scheduler RunLevel=0, before entry. Original log/SQLite snapshot and immutable release retained. Explicit preflight-only API requires same admission, dead/reused fenced owner, zero local/Coupling entry, no entry receipt/native artifacts, and exact preflight-only event chain. It archives old task/slot/events before rebind; consumed/unknown/live/later-stage states fail closed.
38 targeted source tests passed after correcting subprocess test PYTHONPATH (37 initial PASS, one test-invocation failure then one PASS). 8 installed recovery tests PASS.
Actual solver returned and native truth was archived, then postprocessor import lacked mdc_tmm_complex_incident_power_v1. Installed recover_load_only used the unchanged consumed config/request with original clean committed helper SHA 12d2d95bd99fc6e18fec9ac17ab066a5a1fc4a3ddf1a6e5a8c0a625da959ff4b explicitly preloaded via pinned_module. Recovery scientific invocations=0/replay=0; old outputs/failure preserved.
Permanent source successor 5c75c90cde0bc6b54f48b1ac8dc954f948d838e9 packages identical helper bytes, relative import and mandatory path/SHA pin. 4 dependency tests PASS (byte/numerical parity, isolated import, absent pin and alternate-path refusal). Successor is committed/pushed but not substituted into this consumed runtime request; future installation/binding must include incident_power_helper pin.

## Budget and boundary
Before: 38 entered /34 truth-valid /34 labels-valid /90 unentered.
After: 39 entered /35 truth-valid /35 labels-valid /89 unentered /128 authorized.
G026 consumed failure unchanged; G028 remains unentered. Replay=0, training fits=0, P_scale fits=0, confirmation response access=0. No attempt_002, no G028–G116 launch, no confirmation/EXT02/queue21 ingestion.
One server-owned read-only monitor captured start and controller exit at 600s cadence/exit wakeup. No foreign API server was terminated. Existing eight FDTD API servers remained untouched.
Interactive logoff/reboot survival is untested. No unresolved license failure in this case. Cross-height consistency and full-domain/mesh convergence are not certified here.

## Next — do not execute
Science-review this first recovered case and bind/install the packaged-dependency successor before separately authorizing the next development cases. First-case conditions are supported; stable automatic continuous 3/10-case production is still unverified. This task does not open remaining 89 cases.

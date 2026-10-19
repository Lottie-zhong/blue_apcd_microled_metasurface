# APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1

Status: PARTIAL — zero-solver bootstrap completed where evidence permits; scientific production HOLD.

## Authority and data

Latest user task gives Coupling-ML Codex full science ownership. Runtime is generic execution only. AGENTS.md now persists reuse/minimal hashing/targeted testing instructions. No unrelated assets were cleaned or staged.

156 valid, unique development geometries:113 global+32 historical+11 local. Frozen loader and H1/H2 pins verified by existing adapter; old32 always train-only;124 distinct new geometries held out once across the frozen four folds. Preprocessing fits only the respective training split; all21 wavelengths stay with the geometry. Confirmation32 responses and DOE56 responses were not read. Prior fit ledgers/models retained.

5nm/3ps HF numerical reliability remains unresolved. This analysis measures learnability of current labels; no final science/H1 pass. Native eta*P_scale differs slightly from H2 truth (maximum recorded in DATA_AUDIT.json). Reduced prediction uses frozen power factorization eta_hat*exp(logP_hat), compared with frozen H2 decoded truth; it does not reconstruct full609D complex amplitudes.

## Initial lightweight models

Fixed parameters before fits; no outer validation tuning. KRR, ExtraTrees128trees (three seeds),6→32→32→42 tanh/Adam MLP ensemble (three seeds), Mean control. GPR was optional and not refit; previous simple-forward GPR evidence retained. Outputs21eta+21natural log(P_scale).104 estimator fits completed,37.89summed CPU fit seconds;39 fixed1000epoch MLP budget warnings, no claim of optimizer convergence.

|Model|eta spectral MAE/RMSE|P_scale MAE/RMSE|H2P+ MAE/RMSE|450nm P+ MAE|450nm P+ mean-fold rho|
|---|---:|---:|---:|---:|---:|
|Mean|0.09874/0.12802|0.05399/0.07308|0.03114/0.04880|0.06549|undefined constant|
|KRR|0.11372/0.14929|0.06336/0.08931|0.03636/0.05613|0.07675|-0.06829652897158459|
|ExtraTrees|0.09979/0.12906|0.04900/0.06990|0.03152/0.04904|0.06745|-0.046486310547072515|
|MLP|0.12337/0.16216|0.06613/0.09356|0.03896/0.06064|0.08426|-0.06647980078875519|

ExtraTrees gives limited P_scale signal (~9.2% spectral MAE improvement against Mean); eta and P+ do not improve. Unknown K6 power ranking is unreliable. MLP raw seed dispersion is substantially larger than ExtraTrees and is not calibrated uncertainty. Learning curves56/88/full124–126 train geometries show no consistent eta gain; do not extrapolate a guaranteed benefit at250/500/1000. Models are acquisition diagnostics, not production optimization surrogates.

A post-fit reload equality assertion lost in-memory OOF arrays; no completed fits were repeated. All per-fold metrics/curves were persisted, so aggregate MAE/RMSE are reconstructed with heldout geometry weights and rho reported as within-fold mean. Pooled OOF ranking and uncertainty-error calibration are unavailable; see RECOVERY_AUDIT.json. Future source checkpoints predictions before model reload checks.

## Coverage and first proposals

Nominal observed grid100..230nm step5 gives27^6=387,420,489 ordered tuples, but it is not an approved Cartesian manufacturing space. Historical domain authority and later DOE56 manifest both explicitly mark manufacturing authority missing. This is a scientific boundary; no acceptance threshold was invented. Physical non-overlap alone is insufficient.

8192 provisional ordered geometries scored;263 protected unique geometries excluded using existing development/failed registry, sealed geometry metadata only, DOE56 all56 and selected manifest metadata. Six-dimensional joint coverage is sparse; D2=130nm and185nm have no156G samples. Selected16 are8coverage+4model-disagreement+4stratified-random, intentionally not top predicted efficiency. Minimum pair distance 0.4551 under historical /130nm metric; minimum periodic Xgap62.5nm,Ygap60nm,half-cell margin30nm. These are physical clearance checks only.

CANDIDATES_PROPOSED_16.csv contains all ordered geometries, reason and scores. IDs are proposal labels, not new scientific identities. PROVISIONAL_CANDIDATE_POOL.npz and EXCLUSION_AUDIT.json retain pool and sources. Production eligible pool is BLOCKED pending manufacturing contract, numerical closure and fresh live queue identity reconciliation; current scan does not claim a complete live scientific registry. No new FSP or admitted AL batch was created.

## DIAG2 and production budget

Original A1/A2, anchors G001/G004,5nm/6ps, max1entry each retained; source/setup checks matched current frozen pins.6ps contract SHA51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36. Autoshutoff1e-6; FDTD physical maximum6ps is unrelated to platform walltime scheduling. No source/contract identity regenerated.

Historical record remains0/2; current read-only DB search found no DIAG2 job evidence in searched Runner DBs. No authenticated V3.1 budget/attempt mapping was found. V3.1 generates attempt IDs and only stores job_id No Replay. DIAG2 is therefore NOT legally executable now; DIAG2_6PS_TRUTH_VALIDATION=NOT_RUN. An unsubmitted manifest and one bounded confirmation request are supplied. No production Admission signed or activated. DOE56 remains4entered/52HOLD.

## Runner and FakeBackend

Installed SHA matches deployment9d380e62...; Python C:\Users\DELL\anaconda3\python.exe3.9.7 confirmed. ML uses existing N:\anaconda_envs\RCP_LCP\python.exe. The requested Chinese guide is absent in installation but found and read in GPU worktree/minimal_runner_candidate. CLI submit/run/status and --fake-solver were exercised with explicit isolated cwd and --db. Production DBs only read via SQLite mode=ro.

Official fake copy transport PASS; two fixture rows only. Same-job No Replay PASS; actual same-mutex conflict HOLD before entry PASS. Wrong SHA acceptance and same input cross-batch submission reproduced. Existing609D numeric core on an analytic synthetic CaseTruth plus mocked receipt/isolated science ledgers PASS; unauthorized profile and fixture replay rejected. This is not native E/H extraction. Real FSP/H5→609D integration is BLOCKED: Runner saves FSP only and supplies no Coupling authorized record sidecar or H5 exporter wiring. Historical native parity PASS evidence is reused from the prior closeout, not presented as newV3.1/6ps validation.

The Runner resource gate checks its local mutex only, not external GPU solver ownership. Snapshot: RTX3080,0% utilization,1805MiB resident; multiple FDTD GUI sessions. This is insufficient evidence of exclusive resource ownership. No processes killed/adopted. Platform defect evidence covers resource gate, CLI failure exit semantics and input SHA contract; scientific sidecar/native exporter/609D remain Coupling-owned. No Runner source/config/locks/productionSQLite edited.

Targeted existing profile/contract/ledger tests:9/9PASS,0.143s. No full regression. FAKE_BACKEND_E2E.json explicitly marks synthetic data and counters. No fake outputs enter the156G dataset.

## Time and next bounded budget

Existing DOE56 timing metadata only:5nm/3ps repeat solver9.40–9.48min/case, end-to-end11.66–11.73min;4nm diagnostics18.92–18.99min solver,22.13–22.19min end-to-end. Responses were not used.6ps DIAG2 and V3.1 K6 timings remain unmeasured. Linear2× planning gives~18.8–19.0min solver/~23.3–23.5min end-to-end per5nm/6ps case; this is a planning assumption, not a guarantee. Reserve30min/case for planning only (2DIAG2~1GPUh,16AL~8GPUh allowance); queue/resource waiting excluded. Currency cost unavailable without tariff. Final future fidelity may change these costs.

Next science authority needed: confirm ONLY original DIAG2 two-entry mapping (one/case,no replay), contingent on resource/identity integrity gates. After DIAG2 comparison fixes future numerical precision and manufacturing domain, consider a separately approved16-entry AL exploration round. No automatic replacement of failed entered jobs; each failure consumes budget.250/500/1000 are planning sizes, not authorization. No formal inverse optimization now.

## Delivery and limitations

Read SCIENCE_AUTHORITY_AUDIT.json, MODEL_METRICS.json, LEARNING_CURVE_SUMMARY.json, CANDIDATES_PROPOSED_16.csv, DIAG2_V31_UNSUBMITTED_MANIFEST_CANDIDATE.json, RUNNER_MAINTAINER_READONLY_HANDOFF.md, SCIENCE_DECISION_REQUEST.md, FINAL_AUDIT.json, EXECUTION_COUNTS.json and CONTINUATION.md. SHA_INVENTORY.json reuses existing identity pins; it does not recursively rehash artifacts.

Git baseline/HEAD2cc687020e90ec4397e6cd4ed31efed59aaaf386; branch work/mdc-np-coupling-ml-v1; ahead/behind0/0. No commit or push performed. Original945dirty rows and4staged paths retained; task files remain additional untracked assets. See FINAL_AUDIT for final status.

Priority: resolve production HOLD with the bounded DIAG2 science confirmation and verified Runner resource/identity bridge. Coupling retains sole science execution responsibility. All this round real entries/FDTD/FMM/RCWA/replay/sealed access are0.

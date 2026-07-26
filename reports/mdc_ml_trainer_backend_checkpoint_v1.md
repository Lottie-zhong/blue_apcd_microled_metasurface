# MDC-ML trainer backend checkpoint v1

## Scope and correction

- Execution mode: `REMOTE_FIRST_CONTROLLED_SSH_EDIT`.
- Canonical repository: `D:\project\blue_apcd_microled_metasurface`.
- Active worktree: `D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1`.
- Branch/upstream: `work/mdc-ml-inverse-v1` / `origin/work/mdc-ml-inverse-v1`.
- Parent harness checkpoint: `9e83d648a2f1fd7e8fbeeb63dc2a92723a212cc3`.
- The previous task text accidentally omitted `dummy_mean`. The frozen config remained correct and is the authority. This checkpoint preserves both `dummy_mean=DummyRegressor(strategy="mean")` and `dummy_median=DummyRegressor(strategy="median")`.
- Scope is backend-only: no `.fit()`, OOF, final retraining, calibration, conformal fitting, bootstrap, promotion, route execution, proposal generation, TMM, FDTD, Lumerical, sealed-test target access, sealed-test prediction, or formal output write.

## Frozen contract

| Item | Frozen value | Result |
|---|---|---|
| Full config SHA-256 | `76e51a802f598e458264c31db5b6024ade4a0e0a65f3ba2cc3c4587fcd74ade6` | PASS |
| Promotion contract SHA-256 | `71b43c40035bb49a0a9647734b8aa4b42f7a089aa9c354de0b2a90f0c93def52` | PASS |
| Training contract SHA-256 | `4cc187dc18f2e18bae32dc659d1ffad6f2baf0fa411c7214fa98db02645ce886` | PASS |
| Fold signature | `1eff4d939bfe1af28964baebac8e33d0cb9953e98d9009921fac1eb3ae841aa7` | PASS |
| Feature signature | `cc49c7b99dcf486f373f1add526c4c23174069dc92bace0dae6b8fabbcc3cd69` | PASS |
| Feature count | `150` | PASS |
| Classification population | `2640` | PASS |
| Regression-eligible population | `837` | PASS |
| Round 1 classification | `128` | PASS |
| Round 1 regression eligible | `100` | PASS |
| Round 1 sealed-test entries | `0` | PASS |

The loader is pure-read and reuses `training_execution_contract`, `validate_source_references`, `validate_training_execution_contract`, and `validate_existing` from the frozen merge builder. It validates source blobs/resolved values, candidate uniqueness, bounded subsets, fixed-baseline membership, target order, seed contract, unresolved placeholders, and `first_training_started=false`.

## Backend package

- `src/mdc_ml/__init__.py`
- `src/mdc_ml/merge_retrain_v1/__init__.py`
- `src/mdc_ml/merge_retrain_v1/contracts.py`
- `src/mdc_ml/merge_retrain_v1/candidates.py`
- `src/mdc_ml/merge_retrain_v1/state.py`
- `src/mdc_ml/merge_retrain_v1/artifacts.py`

`CandidateSpec` is frozen and records the full frozen estimator snapshot, runtime constructor projection, provenance, their independent SHA-256 values, and a canonical candidate-spec SHA-256. Effective sklearn parameters are obtained from `get_params(deep=False)` and compared only on frozen training-relevant fields.

## Candidate factory

Classification candidates (10):

| Candidate | CandidateSpec SHA-256 | Effective parameter SHA-256 |
|---|---|---|
| `dummy_prevalence` | `3d4f89bcd5fc93ffae11a3af7d1500a3586c09a0d29b9fe6ce4be5256603fe4f` | `5ec5b2b6fd4a852a6c8879df279fb64e1802fd934ce96160eecfdba1f4f57dc5` |
| `dummy_stratified` | `b20cf96168496ecfd1040c69c3a47236672e629502c757ecb7b4c6d94dee2c94` | `6924ce282d7ea366f923b5a426dad95fb9e43bfea370367428c3f29e97f8d7d3` |
| `linear_C_0.1` | `0bb934cdb4c0479f723d0cde9f5789fc3b88ad2ffb9cc7da4f6efbdd8046019d` | `9fb66e423d387708b5636a34184c2abb6de1c21aac56646b58fa687d8edb1f09` |
| `linear_C_1.0` | `9437358dff6a874d6e96be57b193487c697000fc1a42e562cb66111b160963c7` | `826d08c78c6b7aeae624d2a97058f0a02242c380a91d745b63b457992580711f` |
| `linear_C_10.0` | `8c1ba2be3084374866ce526603756983cb67ca97f157d8599f02e74f19e48977` | `cc30bd51d5e65404313f8864ff01e1b08775b1a24e73f4323224eadc6d3c440c` |
| `extra_trees_0` | `bdb32012317b530139c665cf479f9416fad7160b2de8d989c28395c82f059a1f` | `dcb598921567d52859a030aeb42b483c8e5a08d5aaaad0853831bbf9f9d55bc7` |
| `extra_trees_1` | `7a5edcfac9069396981029428081ce61a5bd5f083ba3300f3f0faf328ae46d1b` | `22226b53d4853704fa9b2217524051e0b118a991b06d45df75f6420f5e14219c` |
| `hgb_0` | `589c0e0c1ab725b755607200d8bb633db3cce4d34250c5649edc08d133984898` | `a0eb7dae1a1282b558735215ed337058408f8ee2667ceea0442c770ebb8d2b30` |
| `hgb_1` | `211b1f1495a1bb9ff5b5a5c2092255c6c7da1ce282b5efd212118124d3aa6a62` | `baca56d5c5ac5f9a5ca30104a7d3ab6684356e29ef691aebbb964d5d51e75850` |
| `multitask_mlp_3seed` | `ffffce468c4b9e3d31ad2267335b124e2c87b9ce22daa470110cd6d5cfe08d09` | architecture audit |

Regression candidates (10):

| Candidate | CandidateSpec SHA-256 | Effective parameter SHA-256 |
|---|---|---|
| `dummy_mean` | `b8d2c3898be07da9240507f1f6292fad530e8db3c2ee9d40db5568f3ad0a2d00` | `3a65024f90e4b46e60903068a774631c419a13de6591258bd11120fdc029adfc` |
| `dummy_median` | `ef1ca086952cfc1856201ad3fe86eddffc2c59fea58e5e50a0559c263a63d9e0` | `33d1e9610b1ed873e0cdfdcb6aeb202105227a209d42a49ba509a207d8c4ab6f` |
| `ridge_0.1` | `2cbcc69d31f6419bb52dc84e146a63f794e9304da53b292b2c3f92f0107bd199` | `997a6dc1e42ec512acb2861a9cbaae94a8217c7ef63272a3015fd42f6b09b685` |
| `ridge_1.0` | `d2fccae5ac2ba037cb1018f640ab5947704053fc5be8ee5c7f7ce95af7b5c691` | `250677d4dcdab09d98ad1d6371af99cdf6e6c2401b5c11e5e8baba7a5ce1deac` |
| `ridge_10.0` | `8bb6b0caec7f6e2d8ec2ac81f6628b569d167e3d1eb564871d260de7d3324f8f` | `2de40ef54a34eac786fdbdfcfdcb486b27812946496d872809f516cbc4c6ebcd` |
| `extra_trees_0` | `15faae19b8fd5a229e0abc051f1eca60f06df53ffc55ab8f6cd0fb5be67b2b8a` | `ed0babca5296dec903c2cc440234ea53f4c5caf6a24ac7ccd435538a888a6293` |
| `extra_trees_1` | `bb2e7f05d2784c88ac529776f04e0763a516b49d73213116a173f0bbed368842` | `cd3fe80e65ede241b3877d19e7bb1d80327f876d81d2cb2bb96ebfdd69b8b494` |
| `hgb_0` | `b674152c075e4e44d1de4beba3ace4d11866d7195b655555a90039d0998a1bc6` | `67fa5a450ca607d9bfc7c9e6207365d620112e61b0560c8873c6649403ae9ffa` |
| `hgb_1` | `cdb9bd7a89c05b82d42bce2bbe682b89a4205fe74340c52ce794282bf433562c` | `f502a1e1e4d72d63cec6b3f470b4aa4ce8de08a0856dd3bfcf5552ba9c1995a2` |
| `multitask_mlp_3seed` | `c54459dee37b6bd02c0078f8acb5c102698bbdc7662d495205b2ced7941b41d8` | architecture audit |

Fixed baselines are `extra_trees_1` for classification and `multitask_mlp_3seed` for regression. The unfitted MLP construction has hidden layers `[256, 128]`, ReLU, dropout `0.1`, AdamW learning rate `0.0007`, weight decay `1e-5`, batch size `128`, max epochs `240`, two four-dimensional heads, and seeds `20260720/20260721/20260722`. All three `MLPBundle.model` fields remain `None`.

## State, resume, artifacts, and manifest

- State schema: `mdc_ml_training_execution_state_v1`.
- Statuses: `NOT_STARTED`, `RUNNING`, `PARTIAL`, `FAILED`, `COMPLETE`.
- Ten ordered stages are enforced from `PREFLIGHT` through `FINALIZE`.
- Fold/candidate/seed/artifact units have explicit transition and artifact-completion gates.
- `FAILED -> RUNNING` requires explicit resume; `COMPLETE` is terminal.
- Resume compares all eight fields: trainer SHA, execution commit, config SHA, promotion SHA, training-contract SHA, dataset signature, fold signature, and feature signature. Every individual drift case was rejected with field/expected/observed/match evidence.
- Artifact schema: `mdc_ml_artifact_record_v1`; manifest schema: `mdc_ml_artifact_manifest_v1`.
- Atomic bytes/text/JSON/JSONL/CSV/joblib use same-directory temporary files, `fsync`, `os.replace`, and failure cleanup.
- Fixture roots are restricted to system TEMP and rejected inside the worktree/formal root.
- Formal writes require the exact frozen output root and explicit authorization; this task never grants it.
- Traversal, absolute escape, symlink escape, mismatched overwrite, artifact drift, missing artifact, and unregistered artifact cases are covered.
- Manifests sort records deterministically and have a canonical manifest SHA-256.

## Trainer integration and verification

- Trainer SHA-256 after backend integration: `d9cb78c12d45566fa7d1b6da128b9fadbd343b7ba400ec86e35d52fe84d93ff2`.
- Existing `--preflight`, `--status`, `--fixture-smoke`, and formal-mode block remain.
- Fixture evidence remains `INTERFACE_LEVEL_SYNTHETIC_EVIDENCE`.
- The old `run_oof()` is explicitly marked `CLASSIFICATION_ONLY_INCOMPLETE_FORMAL_PATH`.
- New `--backend-audit` is read-only and reports 10/10 candidates, all candidate/spec/effective-parameter evidence, three unfitted MLP seeds, state/artifact schema versions, and all forbidden-call counters.
- `py_compile`: PASS.
- Backend test collection: `106`.
- Backend tests: `106 passed`.
- Existing harness tests: `14 passed`.
- `--preflight`: `PASS`.
- `--status`: `NOT_STARTED`.
- `--backend-audit`: `PASS`.
- `git diff --check`: PASS with no output after line-ending normalization.

Observed execution counters:

```text
fit_calls=0
formal_training_calls=0
formal_output_write_count=0
sealed_test_target_reads=0
sealed_test_prediction_calls=0
proposal_calls=0
TMM_calls=0
FDTD_calls=0
Lumerical_calls=0
```

## Immutable output audit

| Tree | Files | Bytes | Frozen/post-audit fingerprint |
|---|---:|---:|---|
| Combined | 4 | 14,269,751 | `d738ebd5545b2b582b47721cd5c9e02c116d736eb2784caa6019d76488a576c4` |
| Shared | 29 | 23,639,124 | `a0a486e2508ed5da0560947fbd5b2f04f6412d7a81056e1ec3d09bb19b7d597e` |
| Round 1 | 11 | 2,342,096 | `7fff8fa3eef74177b14e27ba1404789a521656eec667bcd1546c30cfe360b054` |
| Merge/retrain pretraining | 10 | 18,082,726 | `31268194235fbd21cb229f4037afb2410e59c835712ac627524739612903ae6f` |

No formal output tree changed.

## Completed work

- Frozen contract loader and immutable contract dataclasses.
- Complete dynamic 10/10 unfitted candidate factory, including corrected `dummy_mean`.
- Effective estimator parameter and MLP architecture audits.
- Ordered training state machine and complete resume signature gate.
- Atomic artifact store, deterministic manifest, and path policy.
- Read-only trainer backend audit.
- Dedicated backend tests and harness regression.

## Key progress

The trainer now has a frozen, tested backend substrate without claiming complete OOF or development training. Candidate provenance, construction parameters, resume safety, and future artifact writes are explicit and auditable.

## Issues encountered

The first backend audit correctly detected that the HGB classification snapshot contains an additional frozen `class_weighting` field. Snapshot hashing was changed from a hand-selected field list to the complete config-derived candidate object. No contract or output was modified.

## Next steps and priorities

1. P0: `MDC_ML_CLASSIFICATION_CROSSFIT_CALIBRATION_AND_THRESHOLD_BACKEND_V1`.
2. P1: keep regression OOF/final training blocked until a separate authorized module.
3. P2: preserve all frozen signatures and continue TEMP-only fixture testing.

## Progress assessment

The backend checkpoint is complete and evidence-backed. Full trainer implementation and formal training remain intentionally incomplete/not started.

`TRAINER_BACKEND_CHECKPOINT_FROZEN=true`

`FULL_TRAINER_IMPLEMENTATION_FROZEN=false`

`FORMAL_TRAINING_STARTED=false`

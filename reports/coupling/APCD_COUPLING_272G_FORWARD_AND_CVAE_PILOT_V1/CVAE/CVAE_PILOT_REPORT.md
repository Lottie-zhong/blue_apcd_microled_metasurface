# CVAE pilot: ordered APCD K6, 272G FAST

## Verdict

OFFLINE_PILOT_COMPLETE. CONDITIONAL_GENERATION_FEASIBLE_AS_AN_EXPLORATORY_PROPOSER; RELIABLE_INVERSE_DESIGN_NOT_DEMONSTRATED. Keep the formal Geometry + wavelength -> complex Floquet + P_scale -> frozen H2 line. Do not replace it with a direct efficiency model. CVAE is a separate small proposal branch, not a production admission tool. It is worth keeping as a low-cost exploratory baseline, but current evidence does not justify making it the main next-50 selector or increasing network complexity.

## Scientific source and leakage contract

272 existing labels-valid FAST geometries; source D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1\STAGE_50\COMPLEX_DATASET.npz. Read only existing small label arrays, no FSP/H5, no sealed response. Four folds preserve exact original family-purged train IDs and original124 heldout geometries (32/31/30/31). Training sizes 216/217/208/217. Old32 remains train-only; no anchor/perturbation local family is split across training/validation. Shared protocol and source identity are owned by root SHARED_SCIENCE_PROTOCOL.json. Each heldout true condition is a retrospective query only; never used for fit, early stopping, scaling, epoch/architecture selection, or checker training. This is not independent sealed-test or outside-domain certification.

Condition = [H2 eta(+1) at450nm, P_scale at450nm, mean21lambda H2 eta(+1), mean21lambda P_scale]. Each value remains tied to that case's official C_hat/P_scale and frozen H2. Conditions are correlated low-dimensional summaries; P(+1) is omitted since eta times P_scale already determines it. Matching these four summaries would not guarantee matching the609D state, all routing, or a full spectrum.

## Fixed network and fitting record

Encoder [ordered D1..D6 normalized to0..1, four standardized conditions] ->64 SiLU ->32 SiLU ->mu3/logvar3. Decoder [four conditions,z3] ->32 SiLU ->64 SiLU ->6 sigmoid. 5740 parameters. Geometry conversion100+130*sigmoid then nearest5nm and clipping to100..230nm; never sort columns. Training-only condition mean/std. AdamW lr.001, weight_decay.0001,400 fixed epochs, batch64, normalized reconstruction mean-square plus KL sum(latent), beta ramp0->.005 over80epochs. Seeds17/29, four folds =8 fits, CPU2threads, CUDA disabled. Four additional fixed train-only B29 ExtraTrees128,minleaf3,seed17 checkers. These are single-seed ranking instruments, not the formal3seed evaluated model. No model/hyperparameter search. Checkpoints, exact train IDs, losses, mu/logvar, generated geometry and proxy conditions are saved per run. All completed fits used once.

Whole worker elapsed 65.50s; summed eight run train+evaluate+save sections 43.80s. These are service timings, not pure training-time benchmarks. A first SSH/Popen CPU worker was reaped before any fit; WMI launch repaired it, with zero repeated completed fits. See STARTUP_RECOVERY.json.

## Posterior reconstruction and latent diagnostics

Posterior reconstruction MAE = 26.30nm continuous, 26.27nm quantized, versus train 17.99nm. Encoder sees the geometry for posterior reconstruction: these errors are not inverse-design generation scores. Per-case geometric answer is nonunique for four optical conditions; reconstruction is a capacity/generalization diagnostic, not a unique inverse correctness target.

Mean validation KL = 3.361 nats; all3 latent dimensions have training posterior-mu variance >.01 in each run. Generated within-condition diversity is substantial; total posterior collapse is not observed under this specific beta. This does not establish an optimal, disentangled or calibrated latent distribution. All mu/logvar and prior z are saved for independent checks. Validation reconstruction remains worse than train, so small-data generalization is incomplete.

## Fair candidate budget and baselines

For every heldout query and each seed:16 CVAE prior z draws,16 independently uniform six-dimensional grid draws,16 nearest training-library geometries by standardized true condition. Each method is scored by the same train-only checker and same best-of16 protocol. Retrieval additionally has independently known true training-library conditions, reported separately below. Duplicate library choices are deliberately retained; retrieval is a strong finite-library baseline, not novel geometry discovery. Uniform random uses no target conditioning and the same legal geometry support. No new geometry has physical truth.

Primary table = original124 distinct heldout geometries weighted by counts32/31/30/31, then averaged across2seeds. There are124 independent geometry targets, not248 independent geometries or8 independent experiments. SUMMARY_WEIGHTED124.json is the primary result; original equal-fold/seed macro SUMMARY.json is preserved. For reference macro best16 errors were CVAE 0.6010, random 0.6432, retrieval 0.2796. Minimum gaps use global minima, not an average. KL and active dimensions have all8 raw run values in weighted JSON; textual KL is heldout-weighted.

|Method|within-query pairwise RMS nm|unique per-run|train exact duplicates|all-candidate proxy condition error|best16 proxy condition error|
|---|---:|---:|---:|---:|---:|
|CVAE_prior|42.85|100.0%|0.0%|1.0423|0.6006|
|uniform_random|53.48|100.0%|0.0%|1.0897|0.6424|
|training_retrieval|61.41|35.8%|100.0%|0.5211|0.2798|

Errors are RMSE of four train-standardized conditions per candidate, then mean over queries; lower is better. CVAE best16 improves 6.51% over random in this checker, 7/8seed-fold runs and all4 fold-averages. Retrieval remains substantially better. These are proxy-only preferences, not FDTD condition satisfaction or a success rate. No scientific target tolerance was invented.

Nearest true-condition library retrieval, with no proxy selection, has TRUE condition error 0.2168; its checker says 0.3820. Proxy-selected best16 library geometry has checker error 0.2798 but TRUE error 0.3266. Thus optimizing even this checker can worsen actual known-library target matching versus direct known-truth retrieval. This directly demonstrates selection risk; the lower checker error cannot certify new CVAE candidates.

## Conditional dependence, diversity and legality

With exactly the same z draws but reversed heldout query conditions, geometry changes by mean 16.38nm; proxy best16 error changes 0.6006->0.6656, worse in 8/8 runs. This supports learned condition dependence under the checker; it does not validate true response control. Prior candidate average proxy error is 1.0423, shuffled 1.0963.

3968 prior candidates across query-seeds, 3968 globally unique, zero exact coincidences with any of272 existing geometries or training geometries. Nearest training geometry RMS distance mean 18.02nm. Six-dimensional generated standard deviation averages 33.83nm versus train 45.56nm; coverage is narrower than random/training, despite zero exact duplicates. Diversity does not establish useful optical novelty.

All three methods have100% bound/step/order-geometry validity by construction. CVAE generated range 100..230nm, minimum ring-neighbor gap 60.0nm under290nm spacing (including D6-D1). This is the ideal circular-pillar geometric gap only; no invented gap/aspect-ratio/process gate. Material/sidewall/real fabrication qualification remains UNRESOLVED. No full protected-set, historical-entry or queue production dedup/admission is claimed: candidate identities are EXPLORATORY_ONLY and not science Case/Execution IDs.

Mean fraction of validation query conditions outside any training per-condition min/max = 2.42%. This small marginal extrapolation count does not establish joint condition coverage or robustness.

## Recommended next step and next50 implications

Keep CVAE as a cheap exploratory proposal source only. First improve and calibrate TM amplitude/routing prediction, compare true-label library retrieval, and diagnose checker selection errors before any claim of reliable inverse design. Do not increase network complexity on these272 labels merely to reduce posterior reconstruction. If a separately authorized future50G batch is developed, favor coverage and complex-model disagreement; CVAE can be a tagged small diversity probe only after ordinary full production dedup/contracts. Do not spend all50 on surrogate-best CVAE points. Root NEXT50 report sets the unified suggested quota; this branch creates no production IDs, manifests, queue jobs, or entries.

## Evidence files / state

PREREGISTRATION.json; FIT_LEDGER.json; EVALUATION_METRICS.json; SUMMARY.json; CONDITION_AND_BASELINE_DIAGNOSTICS.json; PILOT_AUDIT.json; EXPLORATORY_CANDIDATES.csv (11904 method candidates, no production identities); fold*_seed*/MODEL.pt,LOSS.csv,EVALUATION.npz,COMPLETE.json; checker_fold*.joblib. Plot data use these same immutable run results. Parent scientific figures provide visual QA.

NEW_FDTD=0; NEXT_BATCH_AUTHORIZED=0; FAST=272G; DIAG2=1/2; A2=HOLD; DOE56=HOLD. No Runner/source-FSP/H5/production ledger/Git mutation. Official609D, H1/H2 and strict numerical HOLD conclusions unchanged. Reliable inverse-production use remains HOLD.

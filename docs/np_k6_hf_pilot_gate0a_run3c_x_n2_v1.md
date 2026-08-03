# NP K6 HF Pilot Gate-0A RUN3C-x N2

## Decision

`NP_K6_HF_PILOT_GATE0A_BLOCKED_BY_NUMERICAL_FIDELITY`. This was the only authorized RUN3C-x N2 Native-M1 attempt. It is not a production-mesh freeze and produces no HF training label.

## Provenance

- case: `RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE0A`, attempt: `attempt_001`
- setup pre-FSP SHA256: `887d8b89fc8b2cfaefc8d20eb72b9dd33958837c930d0085721a8a3d12f5574a`
- post-FSP: `D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_hf_pilot_gate0a_run3c_x_n2_v1\runtime_runs\RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE0A\attempt_001\RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE0A_attempt_001_post.fsp`
- post-FSP SHA256: `7ab701698d0351e3c11163ec712f68cb33994687d85ea93de41ff4772484bb1b` (stable across independent readback)
- entered / run / engine / controller / post-save: `1 / 1 / 1 / 1 / 1`
- Native-M1 TiO2/SiO2 reload: Sampled 3D data, 101 points each; no constant-epsilon fallback.

## N2 and actual grid

Intended fixed region is origin `(-870,-145,-100) nm`, bounds `x=[-870,870]`, `y=[-145,145]`, `z=[-100,600] nm`, and `dx=dy=dz=5 nm`. Post-FSP XZ index readback has 349 x points and 201 z points. The x axis is nested in N1, but the complete z coordinate sequence is not: N1 has 128 z points versus N2 201 and the largest nearest-distance mismatch is `3.35627 nm`. Therefore the strict actual nesting hard gate fails.

## Numerical results

- 11 wavelengths, all finite.
- max `|1-T-R|` = `0.081266625` > 0.02: `N2_NATIVE_M1_CLOSURE_GATE_FAILED`.
- 449 nm: `T=0.632657334`, `R=0.361551280`, residual `0.005791386`.
- 449 nm structure interval jump max = `5.35818923e-05`; passed.
- order sum max relative error = `2.9e-16`; passed.
- raw-Pz versus monitor normalization max difference = `3.77e-15`; passed.
- N1→N2 max `|Δη+1|` = `0.213416197`, RMS = `0.075425619`; convergence not passed.

## Staging decision

Production mesh remains unfrozen; RUN3C-y/RUN3A/RUN3B and sealed tasks remain untouched. The single evidence-backed next action is `SOURCEPOWER_FREQUENCY_NORMALIZATION_DIAGNOSTIC`; no new solver is authorized by this report.


## Evidence closure audit (v1)

The D0 reconciliation remains content-identical to the committed 27-point authority; the 26-point contract is retained as isolated historical compatibility evidence. The RUN3C geometry is development-pilot geometry `K6X_D130_D145_D155_D180_D195_D230` with canonical hash `4591fc0d081506b1251fb74edd24b3b6fc950b99072ca0f3172b5d50f5951fc1`; no sealed task or other anchor was run.

The single N2 attempt is complete (`entered/run/engine/controller/post-save = 1/1/1/1/1`). The independent post-FSP reload was read-only, the post SHA remained `7ab701698d0351e3c11163ec712f68cb33994687d85ea93de41ff4772484bb1b`, and the runtime reported 104900 iterations on a 176 x 60 x 109 grid. The first scheduler launch was a pre-entry manifest recovery and did not consume a solver call; `attempt_002` is absent.

At 449 nm the six signed normalized boundary fluxes are preserved in `boundary_flux_449nm_audit.json`; the source-slab injection is computed from the measured lower-outside minus lower-PML flux (`0.9991350625` approximately), not assumed to be unity. Order-sum and raw-Pz/sourcepower normalization agree to numerical precision, while full-band closure still fails (`max |1-T-R| = 0.0812666247`).

The actual XZ z coordinates do not form a strict N1 subset of N2, so `HARD_GATE_RUN3C_N2_NOT_STRICTLY_NESTED` remains active. Production mesh, HF training labels, and candidate labels remain false; this result is diagnostic-only. No Gate-0B anchor is authorized. See the machine-readable audit files in this directory, especially `run3c_geometry_authority_audit.json`, `task_ledger_gate0a_audit.json`, `boundary_flux_449nm_audit.json`, `material_provenance_hash_audit.json`, and `runtime_execution_summary.json`.

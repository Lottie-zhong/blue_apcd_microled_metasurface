# APCD MDC-NP Coupling V1 source scope resolution

Task: APCD_MDC_NP_COUPLING_V1_SOURCE_SCOPE_RESOLUTION_AND_READINESS_GATE
Resolved at: 2026-08-08T14:34:02.403390+08:00
Formal state: APCD_MDC_NP_COUPLING_V1_INTERFACE_ONLY_AWAITING_SOURCE_SCOPE_FREEZE
Offline screening authorization: NO

## Resolution matrix

| Source | State | Exact authoritative result | Readiness meaning |
|---|---|---|---|
| MDC | LOCKED | CLOSED_QUANTITATIVE_HF_PROMOTION_REJECTED; normalized interface scope EXPLORATORY_NP_COUPLING_ONLY | Interface registration only |
| NP | NOT_FROZEN | PILOT_ONLY_NOT_FINAL_MDC_NP_SUPPORT; pending MDC/interface decisions | Cannot compute joint scope or authorize screening |

## MDC scope

Locked commit: 489b54e43bbf2c08ce030a945b9d4b70ee7550f2
Model: MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1
Model manifest SHA256: 8153fcb0846d5bb644c1eef0aa04db46f447e05d00addd704fa050d1a334351a
Scope artifact: D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\contracts/mdc_hf_surrogate_v2/fixed_v2_project_scope.json
Scope artifact SHA256: ecb7d1bc7668c849799d11bf6d62ae535743718786a2ad6459512788dbeb1b52
Provenance: LOCKED_AT_COMMIT.

The committed decision closes quantitative HF promotion. The final model card says NOT_YET_EXTERNALLY_EVALUATED; the ensemble manifest supports one-way MDC-NP power-interface use and excludes y dipole, complex phase, bidirectional feedback, and test40/sealed-test performance. Numeric wavelength/kx input bounds are not explicitly frozen in the final package contract, so 450 nm alone is not treated as quantitative authorization.

## NP scope

Locked commit: 6493fae1f9acc636722ae1705c58b208c5cbdbe6
Observed source-tree HEAD during audit: 35b7bfe81c7c28d3e5a97b892d210f9d58c5a629; this external advancement was not adopted.
Package: NP_K6_P1D4_K6X_V1
Package manifest SHA256: 0b7b45e838a0d73b92d63f8a45459bc46206677a91821fa474dacf4bd9028eaa

Locked artifacts state pilot-only scope, provisional 445-455 nm, u_x=0, p/s basis, pending MDC/interface decisions, no formal HF labels, no model training, and a non-frozen production mesh.

- x/y status: BLOCKED; no formal x/y equivalence or averaging evidence.
- angle/kx status: NOT_FROZEN; only u_x=0 is in the pilot scope.
- interface-stack status: NOT_FROZEN; final MDC-K6 stack and standalone SiO2-substrate equivalence are pending.
- quantitative/ranking use: NOT_APPLICABLE until scope freeze.

## Dirty NP source audit

No source files were written by this task. The current dirty/staged paths are recorded exactly in outputs/mdc_np_coupling_v1/source_scope_resolution_v1.json.
Authoritative-path overlap: none
Verdict: EXTERNAL_UNRELATED_DIRTY_STATE

- M docs/np_k6_p1d2_26point_sixbin_exhaustive_ranking_v1.md
-  M docs/np_k6_p1d4b_k6x_run3c_n1_boundary_attribution_v1.md
-  M outputs/np_k6_p1d4b_k6x_run3c_n1_boundary_attribution_v1/n1_449nm_closure_forensic.json
-  M tests/test_np_k6_p1d2b1_broadband_d105_x_v1.py
-  M tests/test_np_k6_p1d2b2_broadband_d110_x_v1.py
-  M tests/test_np_k6_p1d2b3_broadband_d115_x_v1.py
- ?? .tmp_audit27.py
- ?? .tmp_build_27point_offline.py
- ?? .tmp_builder_gate.ps1
- ?? .tmp_commit_only.ps1
- ?? .tmp_debug_rank.ps1
- ?? .tmp_freeze_builder.ps1
- ?? .tmp_recover_d180_attempt2_post.py
- ?? _tmp_np_27point_git_closure_v1.ps1
- ?? _tmp_np_p1d2_batch_d120_d230_foreground_v1.ps1
- ?? _tmp_np_p1d2_batch_d185_d230_continuation_v1.ps1
- ?? _tmp_np_p1d2_d180_explicit_rerun_foreground_v1.ps1
- ?? docs/np_k6_p1d1a_h500_x_report_v1.md
- ?? docs/np_k6_p1d2_27point_handoff_v1.md
- ?? docs/np_k6_p1d2_natureskill_two_core_phase_figures_v1.md
- ?? docs/np_k6_p1d2_single_pillar_phase_figure_v1.md
- ?? runtime_logs/
- ?? scripts/extract_np_k6_p1d2_complex_field_worker_v1.py
- ?? scripts/extract_np_k6_p1d2_complex_txx_v1.py
- ?? scripts/inspect_np_k6_p1d2_post_complex_worker_v1.py
- ?? scripts/np_k6_p0_anchor_v2_extract.py
- ?? scripts/np_k6_p0_anchor_v2_runner.py
- ?? scripts/np_k6_p0_remaining_five_extractor_v1.py
- ?? scripts/np_k6_p0_remaining_five_runner_v1.py
- ?? scripts/np_k6_p0_remaining_five_supervisor_v1.py
- ?? scripts/np_k6_p0_simtime_10ps_final_v1_extract.py
- ?? scripts/np_k6_p0_simtime_10ps_final_v1_finalize.py
- ?? scripts/np_k6_p0_simtime_10ps_final_v1_launcher.py
- ?? scripts/np_k6_p0_simtime_10ps_final_v1_runner.py
- ?? scripts/np_k6_p0_simtime_10ps_final_v1_watch_extract.py
- ?? scripts/np_k6_p0_simtime_10ps_final_v1_watch_launcher.py
- ?? scripts/np_k6_p0_simtime_recovery_v2_post_recover.py
- ?? scripts/np_k6_supervisor_probe_v1.py
- ?? scripts/np_k6_task_scheduler_probe_v1.py
- ?? scripts/plot_np_k6_p1d2_natureskill_two_core_phase_figures_v1.py
- ?? scripts/plot_np_k6_p1d2_single_pillar_nature_figure_v1.py
- ?? scripts/plot_np_k6_p1d2_single_pillar_phase_library_v1.py
- ?? scripts/register_np_k6_task_scheduler_job_v1.ps1
- ?? scripts/run_np_k6_p1d1a_single_case_v1.py
- ?? scripts/run_np_k6_p1d2_27point_sixbin_exhaustive_ranking_v1.py
- ?? scripts/run_np_k6_supervised_case_v3.ps1
- ?? scripts/run_np_k6_task_scheduler_supervisor_v1.ps1
- ?? scripts/tmp_3ps_compact_poll.py
- ?? scripts/tmp_3ps_compile.py
- ?? scripts/tmp_3ps_finalize.py
- ?? scripts/tmp_3ps_log_tail.py
- ?? scripts/tmp_3ps_poll.py
- ?? scripts/tmp_3ps_pre_run_audit.py
- ?? scripts/tmp_3ps_preflight.py
- ?? scripts/tmp_3ps_runtime_files.py
- ?? scripts/tmp_3ps_watch_extract.py
- ?? scripts/tmp_build_3ps_setup.py
- ?? scripts/tmp_commit_recovery.py
- ?? scripts/tmp_compile_recovery_code.py
- ?? scripts/tmp_finalize_recovery_validator_report.py
- ?? scripts/tmp_find_1ps_evidence.py
- ?? scripts/tmp_find_old_metrics.py
- ?? scripts/tmp_git_diff_setup.py
- ?? scripts/tmp_inspect_3ps_sources.py
- ?? scripts/tmp_launch_3ps_watcher.py
- ?? scripts/tmp_list_recovery_tests.py
- ?? scripts/tmp_mark_recovery_git_checks.py
- ?? scripts/tmp_probe_lumapi_save.py
- ?? scripts/tmp_push_recovery.py
- ?? scripts/tmp_read_2ps_setup_audit.py
- ?? scripts/tmp_read_launcher_remote.py
- ?? scripts/tmp_recovery_allowlist_check.py
- ?? scripts/tmp_recovery_boundary_summary.py
- ?? scripts/tmp_recovery_compare_old.py
- ?? scripts/tmp_recovery_evidence_list.py
- ?? scripts/tmp_recovery_final_audit.py
- ?? scripts/tmp_recovery_find_old_metrics.py
- ?? scripts/tmp_recovery_followup_check.py
- ?? scripts/tmp_recovery_followup_commit.py
- ?? scripts/tmp_recovery_followup_tests.py
- ?? scripts/tmp_recovery_old_runtime.py
- ?? scripts/tmp_recovery_post_contract_probe.py
- ?? scripts/tmp_recovery_post_data_probe.py
- ?? scripts/tmp_recovery_post_push_audit.py
- ?? scripts/tmp_recovery_push.py
- ?? scripts/tmp_recovery_run_copy_probe.py
- ?? scripts/tmp_recovery_staged_audit.py
- ?? scripts/tmp_restage_validator_report.py
- ?? scripts/tmp_restore_setup_zero_state.py
- ?? scripts/tmp_run_recovery_tests.py
- ?? scripts/tmp_show_recovery_tests.py
- ?? scripts/tmp_stage_recovery.py
- ?? scripts/tmp_stage_recovery_followup.py
- ?? scripts/tmp_update_recovery_manifest.py
- ?? scripts/tmp_update_recovery_validator_report.py
- ?? scripts/validate_np_k6_p1d4b_run3c_v1.py
- ?? tests/test_np_k6_p1d2_natureskill_two_core_phase_figures_v1.py
- ?? tests/test_np_k6_p1d4b_run3c_v1.py
- ?? tmp_commit_m0.py
- ?? tmp_final_m0_check.py
- ?? tmp_lumapi_attach_probe.py
- ?? tmp_lumapi_open_source.py
- ?? tmp_lumapi_session_source.py
- ?? tmp_lumapi_session_text.py
- ?? tmp_lumapi_source_probe.py
- ?? tmp_m0_status.py
- ?? tmp_p0_inspect_remote.py
- ?? tmp_p0_list_cases.py
- ?? tmp_recovery_compact_poll.py
- ?? tmp_recovery_engine_metrics.py
- ?? tmp_recovery_engine_poll.py
- ?? tmp_recovery_failure_probe.py
- ?? tmp_recovery_log_probe.py
- ?? tmp_recovery_lumapi_preflight.py
- ?? tmp_recovery_mesh_probe.py
- ?? tmp_recovery_process_parent.py
- ?? tmp_recovery_run_preflight_record.py
- ?? tmp_recovery_runlog_tail.py
- ?? tmp_recovery_runner_compile.py
- ?? tmp_run_m0_dry.py
- ?? tmp_run_m0_tests2.py
- ?? tmp_stage_m0.py
- ?? tmp_write_m0_evidence.py

## Coupling readiness

- Joint scope: NOT_FROZEN; weaker-scope calculation is withheld because NP has no frozen scope enum.
- No-extrapolation policy: LOCKED.
- Polarization gate: HARD_GATE_NP_POLARIZATION_AVERAGING_NOT_JUSTIFIED.
- Missing exact evidence: final NP model-card/external-validation scope, y-polarization equivalence, oblique/nonzero-kx support, final interface stack/reference medium, and cross-branch common-convention freeze.
- No joint screening was run.

## Verification

- Contract validator: PASS.
- Coupling pytest: 13 passed in 0.46s.
- Provenance replay: PASS.
- No-extrapolation: PASS.
- Coordinate/order sign: PASS.
- Power/normalization fixtures: PASS.
- Solver, training, joint screening, sealed-test, and Test40 actions: none.

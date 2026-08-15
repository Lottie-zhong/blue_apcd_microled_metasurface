# CONCURRENCY_3_OBSERVATION

- section: CONCURRENCY_3_OBSERVATION
- classification: CONCURRENCY_3_PRODUCTION_OBSERVATION_PASS
- peak_simultaneous_real_fdtd_jobs: 3
- concurrent_rcwa_jobs_observed_max: 1
- lp_mpi_configuration: {'processes_per_case': 4, 'threads_per_process': 1, 'dedupe_rule': 'MPI children counted as one FDTD physics job'}
- lp_wall_time_throughput: unavailable: no reliable solver telemetry field exposed
- cpu_ram_observations: unavailable: no low-overhead time series recorded
- observable_peer_job_behavior: NP peer FDTD groups remained present; no peer abnormal exit observed in scheduler audits
- license_behavior: no license denial/failure recorded in case accounting
- controller_messaging_stability: stable for all 8 accepted cases; no IPC/messaging failure recorded
- cross_branch_failure: False
- permanent_validated_production_fdtd_concurrency: 2
- promotion: PENDING_CHART_DECISION

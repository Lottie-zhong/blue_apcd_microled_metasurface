# NP K6 HF Pilot Gate-0 N2 production-mesh candidate

Status: `HARD_GATE_K6_GATE0_SETUP_CONTRACT_DRIFT`

The authoritative N2 pre-FSP SHA256 is `5847aadcc4da2279e71de85c952287442b21e9ca2fae552f5ae1b6eeca05ac51`. Read-only object inspection found the FDTD solver, six pillars, source, four formal DFT monitors, and `RUN3C_FIXED_NESTED_N2`. The frozen contract additionally requires six boundary-power planes and a 449 nm XZ index monitor; all seven required object names were absent.

Six independent setup FSPs were generated and reloaded, but no scheduler task was registered and no solver was entered. All six attempt ledgers remain `entered=false`, `run_invocation_count=0`; production mesh is not frozen, HF labels are not promoted, and sealed-test data was not touched.

The six setup FSPs and runtime artifacts remain diagnostic-only and are intentionally not staged.

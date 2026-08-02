# NP K6 HF Pilot Gate-0 corrected N2 monitor contract

Status: `READY_FOR_GATE0_SOLVER_AUTHORIZATION` (setup-only; no solver entered).

The original N2 source is preserved with SHA256 `5847aadcc4da2279e71de85c952287442b21e9ca2fae552f5ae1b6eeca05ac51` and remains documented as contract-drift evidence. A new source was derived without modifying geometry, source, materials, boundary/PML, mesh, or formal T/R/order monitors. It adds exactly the six frozen N1 diagnostic power monitors and `N1_DIAG_XZ_INDEX_449`, using the independently read-back positions and 449 nm single-frequency contract.

Corrected source SHA256: `887d8b89fc8b2cfaefc8d20eb72b9dd33958837c930d0085721a8a3d12f5574a`. Six geometry/polarization setup cases were independently reloaded; all setup diffs are allowlisted, Native-M1 materials remain sampled, and all ledgers remain `entered=false`, `run_invocation_count=0`. No scheduler was registered, no solver was called, no HF dataset was created, and production mesh remains unfrozen.

# BF08 source/convergence replay closeout

Verdict: `PAPER_A_LP_BF08_REPLAY_SOURCE_NORMALIZATION_OR_PARENT_FSP_STATE_UNRESOLVED`.

Both explicitly authorized attempt-002 FDTD jobs entered and returned. The replay retained BF08 geometry, Native-M1 materials, mesh accuracy 2, periodic x/y and PML z boundaries, the 430-470 nm source span, and the 435-465 nm / 31-point formal window. It tightened only simulation time (1 to 5 ps), auto shutoff (1e-5 to 1e-7), and native monitor sampling (41 to 81 points).

Source power through 435-465 nm was positive with min/max 0.9941976488. However, the formal non-negative-transmission acceptance gate failed: BF08_x had 31 negative formal points and BF08_y had 4 (435-438 nm). No clipping, interpolation, or renormalization was applied.

The original current pre-FSP hashes no longer match the attempt-001 entry records. The replay therefore used each immutable returned run-FSP as its parent; both parent hashes match their attempt ledgers. The replay still did not restore a valid source-normalized spectrum, so it is inconclusive as a physical convergence confirmation and must not be used to promote or reject BF08 geometry.

Solver accounting: authorized/entered/accepted = 2/2/0. RCWA=0; ML=0; scheduler active FDTD after completion=0. No further solver work is authorized by this contract.

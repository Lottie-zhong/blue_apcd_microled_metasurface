# NP K6 M10B P -0.482758 closure forensic v1

- Case: `NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE`; geometry hash `00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1`; attempt_001 only.
- Read-only post-FSP reload; no `run()` and no `save()`. Post SHA remained `60c6f668b0f9fdc64b00b10fa00699314d4f377ac711ed6142290ac7020e67fc`.
- Raw frozen gate remains FAIL: max `|1-R-T| = 0.0214212198722` at 445 nm; all 11 residuals are positive, range [0.0108529612078, 0.0214212198722], mean 0.014897469245, median 0.0137401593994.
- Native-M1 TiO2/SiO2 are lossless in the saved sampled tables (`k_max_abs=0`), but no saved volume-absorption or six-face flux ledger exists; `A` is not directly observable.
- Fixed source `u_x=-0.48275862068965514` reconstructs from `sin(theta)` with max error below 1e-16. Raw/sourcepower and order-sum checks remain at machine precision.
- Reference planes are reflection z=-300 nm in substrate and transmission/order z=900 nm in air; no structure-interval or lateral boundary flux dataset is saved.
- Classification: **MULTIPLE_CAUSES_POSSIBLE_INSUFFICIENT_SAVED_EVIDENCE** (medium confidence).
- Recommendation: `P_ATTEMPT001_REMAINS_REJECTED`, `S_REMAINS_BLOCKED`, `CHART_REVIEW_REQUIRED`; no new solver is executed.

Evidence files are in `outputs/np_k6_m10b_p_neg0482_closure_forensic_v1/`.

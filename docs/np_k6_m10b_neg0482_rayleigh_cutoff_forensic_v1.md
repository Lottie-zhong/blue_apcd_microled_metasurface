NP K6 M10B negative-u_x Rayleigh cutoff and spatial numerical forensic v1

Status: READY_FOR_CHART_REVIEW_NO_SOLVER_AUTHORIZED

Primary classification: F_MULTIPLE_SPATIAL_GRAZING_EFFECTS_PLAUSIBLE (confidence MEDIUM). This is a diagnostic classification, not a new performance label.

Frozen identity and governance

Case ALT1 / B, ordered diameters [100,115,130,145,155,185] nm; geometry hash 00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1.
u_x=-0.48275862068965514, P_XLIKE; attempt 001 and attempt 002 remain rejected and immutable.
Attempt-001 post SHA256: 60c6f668b0f9fdc64b00b10fa00699314d4f377ac711ed6142290ac7020e67fc. Attempt-002 post SHA256: 8f5da182c892c3602b9e29c6ea221324d15bc853a7a0e2f59da5a7ff16497e46.
This forensic used only offline tables and independent read-only evidence. New solver calls=0; S_YLIKE entered=0; RCWA rerun=0; thresholds and geometry were not changed.

Rayleigh / cutoff result

The saved Lumerical order identity is verified by u_m(lambda)=u_0(lambda)+m*lambda/Lambda_x, with u_0(lambda)=n_incident_effective(lambda)*u_x; maximum API reconstruction error is 6.661e-16. The exact 445-455 nm scan contains no propagating-to-evanescent crossing.
At 450 nm the tempting direct-air m=-2 shortcut gives u_x-2 lambda/Lambda=-1.0, but the formal API convention gives m=-2 air kx/k0=-1.205827995728 (EVANESCENT), so the Rayleigh-at-450 classification is not supported. The nearest target channel is air m=-1 with distance_to_cutoff=0.052792693927, while substrate m=-3 is evanescent with distance 0.038090694233.
Full per-wavelength/order table: order_cutoff_table.csv; named 11-row summary: NP_NEG0482_DIFFRACTION_CUTOFF_DISTANCE_TABLE_V1.csv.

Closure correlation

Attempt 001 max/mean/median absolute closure: 0.021421219872 / 0.014897469245 / 0.013740159399.
Attempt 002 max/mean/median absolute closure: 0.021752170018 / 0.013383727933 / 0.013171094953.
Absolute residual difference mean/median/max: 0.002049409858 / 0.002580715751 / 0.003735360165.
Pearson closure-vs-nearest-distance: attempt 001 -0.195800, attempt 002 -0.517628; Spearman: -0.200000 and -0.427273. The trend is weak/non-monotonic and is not interpreted causally.

Order schema and power

All eight air-propagating transmitted orders [-1,0,1,2,3,4,5,6] are present at all 11 wavelengths in the formal transmitted schema.
The saved reflection API returned substrate orders [-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8]; reflection completeness is recorded separately and is not silently folded into the transmitted order-sum gate.
order_sum_mismatch approximately 1.11e-16 means the currently tracked transmitted order sum equals the separately defined T total; it is not proof about any untracked reflected-order bookkeeping.

Spatial / PML / reference-plane audit

Attempt 001: mesh accuracy 2, no saved core dx/dy/dz, no override: SPATIAL_MESH_CONTRACT_DEVIATION for that historical run.
Attempt 002: mesh accuracy 4 with RUN3C_FIXED_NESTED_NP_FORMAL_5NM, core [5,5,5] nm, conformal variant 0: SPATIAL_CONTRACT_MATCHED.
Both attempts use z PML [-600,1200] nm, 8 layers; source z=-250 nm, reflection z=-300 nm, transmission z=900 nm, structure z=0..500 nm. PML profile is not exposed in saved readback; risk is MEDIUM, not a confirmed PML defect.
Reflection and transmission planes are in uniform SiO2 and air respectively, each 300 nm from the nearest PML. Near-cutoff longitudinal scale makes monitor/reference-plane risk MEDIUM; no relocation was performed.

Good angular comparisons and anchor role

plus 0.22413793103448276 S: nearest air order m=-5 at 455 nm, distance 0.015781897228, HF max closure 0.00333643, mean 0.00217340.
plus 0.37868939998860307 P: nearest air m=-6 at 445 nm, distance 0.000337736248, minimum propagating kz/k0 0.543995108, HF max closure 0.00356147, mean 0.00320439.
plus 0.37868939998860307 S: same cutoff location, HF max closure 0.00297422, mean 0.00158085.
The good plus 0.3787 cases are closer to a theoretical air cutoff yet have much smaller closure residuals; this is contradicting evidence against a single Rayleigh cutoff explanation for the target's approximately 2% closure. The negative target remains physically high-information but numerically ill-conditioned, so it is recommended as RAYLEIGH_STRESS_TEST_ONLY, not as a primary quantitative FDTD calibration anchor. The already-frozen -0.37869 node is the preferred alternative quantitative anchor candidate; no new angular node is introduced.

Next recommendation

No solver is authorized by this forensic. If Chart authorizes one follow-up, first use ONE_CONTROLLED_REFERENCE_PLANE_OR_BOUNDARY_FLUX_DIAGNOSTIC_AT_NEG0482 (single diagnostic dimension, not attempt 003, not S). Otherwise defer -0.48275862068965514 as a stress point and use the already-frozen better-conditioned anchor. S remains blocked.

Evidence: outputs/np_k6_m10b_neg0482_rayleigh_cutoff_forensic_v1/.

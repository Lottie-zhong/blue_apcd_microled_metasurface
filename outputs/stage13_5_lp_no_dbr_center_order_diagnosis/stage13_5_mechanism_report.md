# Stage13-5 LP No-DBR Center Order-Resolved Mechanism Diagnosis

## Boundary

- No new FDTD simulation was run; Stage13-4 center_x/center_y FSPs were reopened read-only for extraction.
- No +/-q cases, DBR, RCLED, geometry change, or optimization.
- Complex Ex/Ey/Ez from farfieldvector3d was used; intensity-only farfield3d was not used.
- Ez is excluded from LP projection and included only in total vector power.

## Expected orders

- lambda = `450.0` nm; Lambda_x = `2591.446716` nm.
- |u_target| = lambda/Lambda_x = `0.1736481777617225`.
- |theta_target| = `10.000000005514975` deg; uy = 0.
- Angular centers analyzed: zero, +target, and -target; half-angle cones 3, 5, and 10 deg.

## Peak diagnosis

- center_x Ex peak: ux `-0.33999999999999997`, uy `-0.11999999999999995`, theta_x `-19.876874070078827` deg, nearest `other`.
- center_y Ey leakage peak: ux `-0.58`, uy `0.0`, theta_x `-35.45054263917541` deg, nearest `other`.
- Steering present within 3 deg: `False`.
- Actual target-order sign: `unresolved`; sign flip: `False`.

## Incoherent LP fraction at expected order centers

- The actual target-order sign is unresolved because the center_x Ex global peak is not within 3 deg of either expected order center.
- Therefore no actual-target LP_fraction is claimed; both expected centers are reported below.

| order center | cone half-angle | LP_fraction_incoherent | pass >0.60 | failed <0.50 |
| --- | ---: | ---: | --- | --- |
| plus_target_order | 3.0 | 0.5924613993693476 | False | False |
| plus_target_order | 5.0 | 0.5797810893872927 | False | False |
| plus_target_order | 10.0 | 0.5438952135433864 | False | False |
| minus_target_order | 3.0 | 0.618714427012973 | True | False |
| minus_target_order | 5.0 | 0.6060803457005977 | True | False |
| minus_target_order | 10.0 | 0.48878405672933817 | False | True |

## Mechanism classification

- Primary class: `class_C_no_steering`.
- target_order_contaminated: `None` (not classifiable while the actual target order is unresolved).
- y-Ey/x-Ex contamination ratios at both expected centers, 3/5 deg: `{"plus_target_order": {"3": 0.49169893222231015, "5": 0.5263346240979275}, "minus_target_order": {"3": 0.5997593804804665, "5": 0.6198283596707982}}`.
- order_resolved_center_may_continue: `False`.
- order_resolved_center_failed: `None`.
- Recommendation: Diagnose finite-patch phase-ramp/source coupling and coordinate mapping; do not run +/-q or add DBR/RCLED.

## Jones/APCD evidence boundary

- Orders were analyzed as finite-patch angular centers (zero, +target, -target), not periodic grating-order amplitudes.
- An incident-wave order-resolved J_xy matrix was not constructed: center_x/center_y are independent dipole-source simulations and are combined incoherently.
- alpha/beta -> alpha*/beta* conversion was not performed.
- t_{alpha*<-alpha}^{order}: unavailable/not claimed.
- Therefore this report diagnoses angular LP-power routing only; it does not claim full APCD Jones selectivity.

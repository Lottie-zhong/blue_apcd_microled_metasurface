# Next-stage scientific decision

## Current decision

- Keep the existing NN3 as the strongest current 29D development reference; the inner-group early-stopped rerun did not improve its full 609D/H2 metrics.
- Retain `mu_train(lambda) + Ridge residual(D, lambda)` as a low-cost Pscale diagnostic candidate, not as a promoted production head. Its Pscale MAE gain is small and high-P underprediction remains.
- Do not promote the residual MLP: it increased predicted geometry variance without a consistent reduction in Pscale or peak errors.
- H1 remains HOLD. The 124 fixed geometries have been used repeatedly for development choices; no independent final generalization claim follows from these results.

## Is another 50G justified?

More data remains scientifically reasonable because state, routing, thresholded order, and total-power H1 gates still fail. This experiment does not show that simply adding 50 cases will close those gates. It supports prioritizing cases that expose Pscale geometry residuals, powered TM-mode amplitude/routing errors, and sparse six-dimensional regions, while preserving a random-control slice. A new batch remains unauthorized; this task created no case IDs, jobs, manifests, or solver budget.

If a later 50G batch is separately authorized, use a proposed starting allocation of 24G joint geometry coverage (including D2/D3 sparse combinations), 10G power-weighted TM amplitude/routing disagreement, 10G Pscale peak/high-value residual disagreement, and 6G stratified random controls. Select disagreement only from train-fold models and coverage metadata; do not select solely by predicted efficiency. Keep all local-family groups intact across evaluation splits. Review after 16/32/50 valid labels, with Mean baseline and unchanged 124G development protocol, and treat the metrics as development until the independently frozen final confirmation procedure is executed.

## Boundaries

`FAST=272G`; `H1=HOLD`; `NEW_FDTD=0`; `NEXT_BATCH_AUTHORIZED=0`; `DIAG2=1/2`; `A2=HOLD`; `DOE56=HOLD`; CVAE remains paused. Sealed confirmation was not accessed; the GPU Runner was neither called nor changed.

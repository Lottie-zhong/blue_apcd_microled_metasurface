# IAR-C2 orientation continuation control contract

Status: PASS — zero-solver pre-admission geometry audit.

## Decision

IAR-C2 is read from the canonical conditional registry. With all IAR-C2 geometry frozen, the current inherited polygon-validity rule was scanned from 80.00° to 90.00° in 0.01° increments. All 1001 grid points pass; 80.00° is legal and is the domain lower bound.

IAR-C2-OC80 is frozen as a prospective angle-only continuation control: only delta_theta changes from 82.818204313° to 80.000000000° (difference -2.818204313°). It is not solver-authorized in this task.

## Exact geometry and clearance

IAR-C2: L1/W1/L2/W2=258/88/198/78 nm, D=217 nm, delta_theta=82.818204313°, centers y=+108.5/-108.5 nm, H=525.0 nm, Px=Py=432.0 nm.
IAR-C2-OC80: direct=68.731753522781118517475492121633944602591666669557 nm; periodic-image=66.731753522781118517475492121633944602591666669557 nm; global polygon minimum=66.731753522781118517475492121633944602591666669557 nm.
OC80 headroom over the inherited 60 nm gate: direct=8.731753522781 nm; periodic=6.731753522781 nm.
Both exact audits pass containment, integer lateral dimensions, half-grid centers, no direct overlap/touch, and no periodic overlap/touch. No new fabrication threshold was introduced.

## Control comparison

IAR4-CR1 changes D and delta_theta relative to IAR4 and remains a clearance-compensated continuation probe, not a strict orientation-only control. IAR-C2-OC80 is preferred for bounded validation because it preserves IAR-C2 dimensions and D and changes only relative orientation.

## Prospective solver plan

Plan only, no current authorization: IAR-C2_x, IAR-C2_y, IAR-C2-OC80_x, IAR-C2-OC80_y; maximum four future FDTD jobs and maximum two active jobs. No automatic admission is enabled. After that bounded batch, make a GO/STOP decision without expanding the domain.

## Accounting

NEW_FDTD_BUDGET=0; solver_run_called=false; solver_entered=0; RCWA=0; ML=0; active fdtd-engine processes=0; DOE unchanged.

See `iar_c2_angle_clearance_frontier.csv` for all 1001 scan points and `matched_control_record.json` for the exact control relationship.

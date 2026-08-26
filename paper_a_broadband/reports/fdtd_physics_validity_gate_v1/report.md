# Paper A FDTD physics validity gate v1

## Motivation

A solver process returning normally does not by itself establish physics-truth validity. This gate is read-only and evaluates only completed post-FSP/log outputs.

## Logic

1. Gate 1 reads final, peak and late-window auto-shutoff trajectory.
2. Gate 2 treats that trajectory as the available time-resolved energy/residual proxy; it never invents a field-energy history.
3. Gate 3 reads unmodified `transmission(T)` at exact formal monitor coordinates and checks finite values, negative persistence and the frozen BF01–BF07 control envelope.
4. Gate 4 reads unmodified `sourcepower` and applies the pre-registered 0.99 min/max rule.

The late-time invalid condition is grounded in the solver's initial normalized auto-shutoff reference of 1.0: a trajectory which first decays below 1.0 and later grows above 1.0 with positive late-window slope is invalid.

## BF08 deterministic regression

Both BF08 attempt_003 cases are correctly classified `INVALID_FOR_PHYSICS_TRUTH`. BF08_x: final auto-shutoff `2367.4`, 31 negative formal transmission values. BF08_y: final auto-shutoff `1.64048`, 4 negative formal values. Source normalization passes for both.

## Compatibility

The gate did not modify BF01–BF04 setup-only artifacts and did not make a scheduler admission. Future completed truth cases can call the gate with a post-FSP and immutable p0 log.

## Result

`PASS`. No solver, FSP generation, FSP save, raw-data transformation or promotion occurred.

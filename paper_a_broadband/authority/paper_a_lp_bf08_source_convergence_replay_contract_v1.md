# Paper A BF08 source/convergence replay contract

Status: `USER_AUTHORIZED_PENDING_SETUP_ONLY_GATE`

This is the sole authorized BF08 replay: `BF08_x_attempt_002` and
`BF08_y_attempt_002`. It exists because both immutable attempt-001 run-FSPs
returned with a negative formal net transmission at 436 nm.

The BF08 geometry is taken from the immutable attempt-001 returned run-FSPs,
whose hashes match the attempt ledger. The Native-M1 material identity, mesh accuracy, boundary
conditions, 430-470 nm source span, x/y inputs, order-(0,0) extraction and
435-465 nm formal window remain fixed. The replay strengthens only temporal
and spectral sampling controls: simulation time 1 to 5 ps, auto shutoff
1e-5 to 1e-7, and native monitor samples 41 to 81 (0.5 nm). The 31 formal
points remain exact integer-nm samples; no interpolation, clipping or
renormalization is permitted.

The source gate requires positive `sourcepower` through 435-465 nm and
min/max at least 0.99. A returned case is valid only if all 31 formal
transmission values are non-negative. This contract authorizes no further
replay or other solver work.

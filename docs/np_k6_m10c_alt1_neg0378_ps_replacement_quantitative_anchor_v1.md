# NP K6 M10C ALT1 negative-u_x replacement quantitative anchor v1

## Decision

`NP_K6_M10C_ALT1_NEG0378_PS_ANGULAR_HF_COMPLETE_M11_CALIBRATION_READY`

The exact replacement node is `u_x = -0.3786893999886029` for ALT1/B,
ordered diameters `[100, 115, 130, 145, 155, 185] nm`, geometry hash
`00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1`.
The earlier `u_x=-0.48275862068965514` P attempts remain immutable stress-only
evidence; they were not replayed or reused.

## Execution and resource governance

P/XLIKE `attempt_001` ran first, then released `GLOBAL_SLOT_1` before
S/YLIKE `attempt_001` was admitted. Both cases used the production resource
contract `12 MPI x 1 thread`; task-local active-FDTD peak was one and P/S
solver overlap was zero. Total new solver entries were exactly two. No
attempt_002/003, CONTROL0, external HF, training, or inverse-design action was
started. Runtime FSPs and logs remain outside Git.

## Quality gates

| case | post-FSP SHA256 | max |1-T-R| | max order-sum mismatch | max normalization mismatch | result |
|---|---|---:|---:|---:|---|
| P/XLIKE | `cec3a0a04f82adfd00dd2039d3917149e1a2aca77c15eb4e627d6b87c7e5274e` | 0.006763587889811129 | 2.220446049250313e-16 | 1.1102230246251565e-16 | PASS |
| S/YLIKE | `92d78129c366aa31db0dc99bb1692e5056744fe026061148e1621d54a5a9e58f` | 0.0036991019227169963 | 1.1102230246251565e-16 | 1.1102230246251565e-16 | PASS |

Both post-FSPs independently reloaded and yielded exactly 11 finite points.
The dominant transmitted order was `n=+1` at all 11 wavelengths for both
polarizations. Structure-interval anomaly was not observable in this formal
monitor contract and was therefore not invented or used as a pass surrogate.

At 450 nm, P has `T=0.7092578344421673`, `R=0.29750575344764385`,
`eta(+1)=0.5398816134613701`; S has `T=0.7373144047055932`,
`R=0.2627813363601391`, `eta(+1)=0.6848963548171816`. The exact post-FSP
extraction gives a maximum absolute P-S `eta(+1)` difference of
`0.21428375089655943` across the band. The +1 air-side angle is negative and lies
approximately between `-16.5382°` and `-16.1646°` across the band.

## Five-case registry and RCWA audit boundary

The 55-row registry contains the three previously accepted positive-u_x
cross-reference cases (`+0.224 S`, `+0.3787 P`, `+0.3787 S`) plus the new
negative-u_x P/S pair. The 33 historical rows are explicitly marked
`EXACT_HF_CROSS_REFERENCE` with aggregate-only metrics; no missing spectral
values were fabricated. The 22 new rows are independently extracted
`M10C_NEW_FDTD_ACCEPTED` rows.

The NP authority contains aggregate HF closure comparisons for the positive
anchors but no matching RCWA spectral rows for the new negative node. No RCWA
solver was authorized or run. Consequently, the RCWA/FDTD residual artifact
records `RCWA_MATCHING_ROW_NOT_AVAILABLE_IN_NP_AUTHORITY` for the negative
node and remains an explicit partial audit, rather than an invented residual.

## Governance and next gate

This is an angular calibration anchor, not a training label or a final
candidate-performance release. The M10C evidence supports M11 calibration
handoff review. `CONTROL0_MATCHED_ANCHOR_NEEDED` remains a recommendation only;
it was not run automatically. The next action is user review of the M11
calibration handoff.

Evidence directory:

`outputs/np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1/`

# Physics provider interface V1

## Purpose

Define the minimum versioned boundary between a Physics Codex provider and Coupling ML. This is a proposed interface, not evidence that a physics provider currently exists or has been validated. The current model API is geometry-only.

## Provider result record

Each result should carry:

- contract_id, physics_model_version and contract_version;
- provider_status: UNAVAILABLE, UNVERIFIED, POWER_ONLY, PARTIAL_COMPLEX, or VALIDATED_COMPLEX;
- immutable result_id, geometry_id and geometry dimensions D1-D6 in nm;
- wavelength axis and units;
- incident mode axis, including port, diffraction order, polarization, propagation direction, and normalization reference;
- output mode axis, with the same explicit fields and a stable ordering;
- complex coefficient array with declared output-by-input axis order;
- propagating/evanescent mask over the declared axes;
- separate P_scale values and their physical definition, when available;
- reference plane, phase convention and power normalization;
- provenance: solver/version, material configuration, mesh, boundaries, run identifier, input_asset_sha, pre/post artifact hashes, and extraction code/version;
- validation evidence and known limitations.

Do not rely on array position alone to identify a port or channel. Unknown fields, axis ambiguity, incompatible dimensions, non-finite values, or an unknown status must fail closed.

## Coupling ML acceptance modes

### Frozen H1 full-state mode

For the existing H1 basis, accept only VALIDATED_COMPLEX with C_hat shape (21,7,2), complex dtype, finite real and imaginary parts, and a propagating mask that explicitly covers every frozen channel. Require the exact frozen wavelength and order/polarization axes and compatible source gauge. A missing provider or any non-full status raises an explicit error. Do not substitute zeros, interpolate unknown channels, or fabricate phase.

P_scale is independently validated as a real, finite, strictly positive vector of shape (21,). It remains separate from C_hat.

### General scattering-matrix mode

Represent the input and output axes as ordered ModeKey records. Matrix dimensions are determined from those axes; do not assume a universal S-matrix size. Record whether entries are transmission or reflection and the direction of each port. Partial matrices may be stored as partial evidence but cannot satisfy the H1 full-state contract.

## Model integration patterns

1. Provider-conditioned prediction: model input contains geometry plus validated provider features; output remains the frozen C_hat and P_scale target.
2. Residual correction: compute a validated physics baseline and learn a residual in a declared complex representation. Preserve source phase gauge and normalization.
3. Component composition: accept component scattering matrices with compatible mode axes and compose them using the independently validated cascade convention.

These patterns are design options. The current production model does not implement them.

## Failure behavior and provenance

Unavailable or unverified physics must remain explicitly unavailable. Power-only data can support only power-level comparisons. A partial complex response can support only its covered channels. Every derived feature must retain provider result_id, contract version and source hashes. Never use labels or a model output to claim independent validation of the same provider result.

## Backward compatibility

Provider consumption is optional. If status is UNAVAILABLE, the legacy geometry-only Cartesian KRR/MLP path can still run without provider features. Selecting the provider-required path must surface an explicit unavailable error; it must not inject zeros or report a physics-conditioned prediction.

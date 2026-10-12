# Physics-guided network architecture comparison

## Frozen data boundary

The 156G dataset maps six geometry dimensions to one documented incident state: +z order (0,0) TM. Its target has 294 complex output coefficients and one P_scale value per wavelength. It does not identify a full bidirectional S-matrix. No new model was fit for this preparation.

## Route comparison

| Route | Scientific necessity and supervision | Parameters and inference cost | Interpretability and identifiability | Implementation, risk and expected benefit |
|---|---|---|---|---|
| Model A: Direct ML baseline | Required fair comparator. Uses the frozen 156G labels for geometry-to-C_hat and log(P_scale). | Existing frozen Cartesian KRR/MLP configurations; exact parameter counts and inference latency belong to their saved fit packages. No additional provider cost. | Observable for the documented single incident state; cannot identify a full NP S-matrix. | Already implemented, but both historical models fail H1. Lowest implementation risk; establishes whether physics actually adds value. |
| Model B: Physics baseline plus residual ML | Preferred physics-guided route. Supervision is frozen HF label minus validated C_physics, with a separate log(P_scale) target. Requires matched geometry/wavelength/mode axes and common phase gauge. | Candidate only: shared modal residual MLP with input [D1-D6, wavelength, order m, TE/TM one-hot, Re/Im(C_physics)] (12 inputs), hidden widths 32/32, two real outputs: 1,538 trainable scalars. Separate log(P_scale) head [D1-D6, wavelength], widths 16/16, one output: 417 scalars. Total 1,955, including biases and excluding train-only normalizers. If provider runs RCWA at each new geometry, report provider plus network end-to-end latency. | Residual has direct physical meaning only with identical phase and normalization conventions. It remains identifiable only for the supplied +z TM incident state. If the physics baseline and HF cannot be aligned in one complex reference, this route is BLOCKED. | One compact shared network could remove deterministic feedback from the target. Main risks are provider mismatch, near-zero phase, small geometry count and overfit. Parameter count is a proposed budget, not evidence that 156 groups suffice. |
| Model C: Physics-conditioned shared modal network | Uses legal provider descriptors with geometry, wavelength and mode labels; target remains the frozen C_hat and P_scale. | Share weights over wavelength and order. Parameter budget must be capped to the Model B scale; exact count depends on the provider descriptor schema. Inference cost includes any runtime RCWA required to produce descriptors. | Can share structure across wavelengths and modes, but cannot infer unobserved incident columns or a unique NP S-matrix from integrated single-input labels. | More flexible than a residual but easier to overfit and harder to attribute. Compare only if provider features are available at unknown-geometry inference time. |
| Analytic component composition | Physical operator, not an ML model: compose validated MDC T/R, spacer P and NP S data. It may supply C_physics to Model B. | No ML parameters; matrix cost scales with retained mode count and cascade operations. Provider solve cost and modal truncation cost must be measured. | Most physically interpretable if ports and bases are complete. Matrix entries cannot be uniquely learned from 156G integrated single-input data alone. | High convention and validation burden. Synthetic adapter is not a physical implementation. Benefit is removing deterministic internal feedback from ML targets. |

## Residual representation

Use real and imaginary residual components under the same source-referenced gauge as H2; this avoids explicit 2-pi phase wrapping. Gate phase metrics below a preregistered amplitude floor and report the excluded fraction. Do not use oracle phase alignment, independent channel rotations, or oracle power rescaling. If provider and HF reference planes or gauges differ, do not calculate the residual.

Keep P_scale as a separate positive output, with train-only log normalization and exp inversion. Do not merge it into C_hat or count decoded total_power=P_scale as an independent check.

## Minimum first implementation

After provider validation and separate training authorization, prefer one compact Model B shared modal residual MLP, not three large networks. It shares across wavelength/order/polarization, predicts real/imaginary C residuals, and uses a separate small log(P_scale) head. Compare against Model A under the same geometry-group split, role composition, H1/H2 decoder and budget accounting.

Whether the 156G sample supports even this small model is UNRESOLVED. The 11 local-axis cases do not establish a stable general residual law. No fitting or hyperparameter search is authorized by this preparation.

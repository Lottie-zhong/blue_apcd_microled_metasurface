# Final scientific recommendation

## Decision

Preparation status: PARTIAL. Data contract: PASS for the frozen single-incident 156G target. Physics provider interface: READY as a proposal, not backed by a validated provider. Network architecture: READY as a design. Real physics validation: NOT_RUN.

## A. What can the current 156G support?

It supports geometry-only prediction of the documented +z (0,0) TM incident state's complex output channels and separate P_scale, plus future provider-only or provider-residual comparisons if a convention-matched provider is available for the same geometries. It does not identify a full bidirectional NP S-matrix. The adequacy of 156 geometry groups for a small shared residual network is UNRESOLVED.

## B. Which provider result should come first?

Prioritize an immutable integrated C_physics state and independent P_scale for the frozen H1 axes, using the same input mode, wavelengths, reference plane, normalization and source phase gauge as H2. Include provenance, validity domain, uncertainty and end-to-end cost. Supply the component NP S, MDC T/R and spacer P alongside it when possible; the integrated result unlocks a residual comparison, while component results enable independent cascade validation.

## C. Is complex phase suitable for direct residual learning?

Only conditionally. Re/Im residuals avoid explicit 2-pi wrapping, but require the same physical reference plane, source gauge and normalization. Near-zero-amplitude phase is undefined and must be masked below a preregistered floor. If provider and HF gauges cannot be aligned by the frozen contract itself, Model B is BLOCKED. No oracle alignment is allowed.

## D. How do we preserve 609D and H1/H2?

Keep existing pack_model_target/unpack_model_target, the 588 real/imaginary state scalars, 21 log(P_scale) scalars, H2 decoder and H1 gates unchanged. Add provider inputs as a separate optional feature path. When no provider is present, legacy KRR/MLP remain geometry-only and runnable. Missing provider data raises an explicit status; never zero-fill it. Keep P_scale separate and prohibit oracle power rescaling.

## E. Which small network should be first?

After provider validation and new training authorization, choose one shared modal residual MLP (Model B), with geometry, wavelength, order, polarization and C_physics Re/Im features; output Re/Im residuals and use a separate log(P_scale) head. The proposed widths use about 1,955 trainable scalars. This is a candidate size, not a demonstrated fit. Compare it to the original KRR/MLP on identical geometry-group splits before considering any larger network.

## F. What minimum scientific validation is needed?

Freeze provider schema and axes; verify source/phase/power conventions; compare against independent trusted physics; establish spatial, temporal and modal-truncation convergence; validate independent power closure; test provider validity-domain and uncertainty; report provider plus model runtime; then run authorized geometry-grouped development evaluation against both historical baselines using train-only normalization and unchanged H1/H2. Keep confirmation responses sealed.

## G. How does the unresolved 5 nm / 3 ps condition limit conclusions?

It leaves a temporal-convergence confound in the historical numerical evidence. It prevents attributing past ML failure to model architecture alone or claiming a converged physical target for new physics-guided gains. It does not prove that the confound caused those failures. The 5 nm/4 nm diagnostics must not be added to training data. Conclusions remain conditional until the appropriate authorized convergence evidence exists.

## H. What can be fully checked offline before a real solve?

Provider status and mode-axis schemas; shape, complex dtype, finite-value and P_scale guards; missing-provider fail-closed behavior; 609D target round-trip; H2 decoding and routing identities; synthetic cascade algebra, broadcasting and ill-conditioning rejection; deterministic hashes and manifest linkage. These checks cannot establish physical port conventions, APCD accuracy, solver convergence or formal admission.

## Evidence and stop condition

The H2 routing recomputation over 156 labels had median absolute difference 3.62025e-5 and maximum 3.41991e-4; this is decoder consistency only. Both historical 124G KRR and Cartesian MLP fail the frozen conjunctive H1 gate. Ten offline adapter tests passed. No solver entry, new model fit, confirmation/sealed access or truth modification occurred.

After reporting this preparation, stop and wait for the next Chat-dispatched scientific decision.

# MDC-HF surrogate v2 standalone model card

- Model ID: `MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1`
- Commit: `631080fcb6a5ed8626fba412bb19366b8b291d33`
- Capability: ranking/screening only.
- Frozen model consumes geometry-conditioned inputs and predicts source-normalized joint spectral-angular profiles and derived power/auxiliary quantities.
- It is not a calibrated uncertainty model, not a generative model, and not a replacement for direct FDTD.
- Test40 metrics are frozen external screening evidence; no retraining or metric recomputation is part of this asset task.

# Cyclic equivariance and model diagnostics

## Main comparison

Means below are the arithmetic mean of the four fixed-fold metrics and three seeds, on the same 124 development geometries. Lower is better except ranking metrics. Full fold × seed rows are in `CYCLIC_AUGMENTATION_MODEL_COMPARISON.csv`; the per-order/per-polarization breakdown is `CYCLIC_ORDER_POLARIZATION_METRICS.csv`.

| Model | 609D complex NRMSE ↓ | TM magnitude MAE ↓ | Routing MAE ↓ | relative phase (deg) ↓ | P_scale MAE ↓ | η(+1) MAE ↓ | P(+1) MAE ↓ | 450 nm Spearman ↑ | Top20 recall ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A · 原始 NN3 | 0.5998 | 0.1255 | 0.0724 | 43.8336 | 0.0654 | 0.0736 | 0.0234 | 0.6628 | 0.6270 |
| B · 训练循环增强 | 0.4624 | 0.0961 | 0.0558 | 30.5650 | 0.0539 | 0.0584 | 0.0197 | 0.7664 | 0.7123 |
| C · 六视图推理集成 | 0.5204 | 0.1170 | 0.0620 | 35.2617 | 0.0548 | 0.0635 | 0.0201 | 0.7784 | 0.7163 |
| D · 增强 + 六视图集成 | 0.4439 | 0.0928 | 0.0533 | 28.9975 | 0.0507 | 0.0547 | 0.0184 | 0.8102 | 0.7619 |


The B training augmentation improved all 12 paired fold-seed results for complex NRMSE, TM magnitude MAE, routing MAE, weighted relative phase, P_scale MAE, η(+1) MAE, P(+1) MAE and 450 nm Spearman. Top20 recall improved in 4/12 paired runs although its fold/seed mean increased. D vs C improved every paired fold-seed loss metric; ranking improved in 9/12 runs and Top20 in 4/12, while both mean ranking metrics increased.

- `B_minus_A`：12 个 fold-seed 配对中，complex NRMSE 12/12 改善，P(+1) MAE 12/12 改善，η(+1) MAE 12/12 改善；Spearman 改善 12/12、Top20 改善 4/12。配对平均差：complex NRMSE -0.1374，P(+1) MAE -0.0037，Spearman +0.1035。
- `D_minus_C`：12 个 fold-seed 配对中，complex NRMSE 12/12 改善，P(+1) MAE 12/12 改善，η(+1) MAE 12/12 改善；Spearman 改善 9/12、Top20 改善 4/12。配对平均差：complex NRMSE -0.0765，P(+1) MAE -0.0018，Spearman +0.0319。

## Equivariance residuals

Raw model equivariance residual is relative L2 across k=1…5, computed on the same validation geometries. Group-averaged C/D satisfy equivariance to floating precision by construction.

| Model | Mean raw complex residual | Max complex residual | Max P_scale rotation residual |
|---|---:|---:|---:|
| A raw NN3 | 1.2996 | 1.4077 | 0.2294 |
| B raw augmented NN3 | 1.3184 | 1.4579 | 0.1221 |
| C six-view group average | 7.976e-16 | 9.095e-16 | 1.361e-16 |
| D augmented + group average | 7.650e-16 | 8.521e-16 | 1.312e-16 |

Training augmentation alone did not reduce the raw network's complex equivariance residual in this fixed-budget fit; it did reduce predicted P_scale's rotation residual. Six-view inference projects the prediction onto the group-equivariant output by construction and reduces both residuals to numerical precision. D had the best mean complex and H2-target metrics, but requires both augmentation training and sixfold forward inference.

## Training and H1

New fits: 12 independent augmented NN3 fits (4 folds × 3 seeds), 903.1 s total; 300 epochs each. All emitted the expected sklearn max-iteration convergence warning. No extra epochs or best-seed selection were used. A/C reused the previously saved original NN3 checkpoints, whose recomputed predictions matched saved validation predictions exactly (`max |ΔC|=0`, `max |ΔP|=0`).

| Model | State | Routing | Absolute order | Thresholded order | Total power | H1 production admission |
|---|---|---|---|---|---|---|
| A · 原始 NN3 | False | False | True | False | False | **False** |
| B · 训练循环增强 | True | False | True | False | False | **False** |
| C · 六视图推理集成 | False | False | True | False | False | **False** |
| D · 增强 + 六视图集成 | True | False | True | False | False | **False** |

Every candidate has `production_admission=false`; H1 remains **HOLD**. B and D clear the state gate, but routing, thresholded absolute order, and total power gates remain failed. These results are still development evidence only; the 124 development cases are not an independent final test.

The per-seed frozen-H1 replay is in `CYCLIC_H1_PER_SEED_GATE_RESULTS.json`: the same gate pattern holds across all three seeds for each of A–D, and production admission is false for all 12 model/seed combinations.

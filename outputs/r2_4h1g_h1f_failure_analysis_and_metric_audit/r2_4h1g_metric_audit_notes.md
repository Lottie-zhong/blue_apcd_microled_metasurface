# R2-4H1G metric audit notes

Python-side recalculation status: `available`.

Original H1F metrics are preserved unchanged. The audit found: original average leakage20-40 exceeds eta20, inconsistent under simple total-normalized disjoint-window interpretation; x_0_nm original leakage20-40 exceeds eta20; recalculated normalized window metrics differ from original H1F metrics by more than 0.05.

Future angular-window integration should be verified against the official Ansys/Lumerical 2D far-field conventions. In particular, `farfield2d` returns a field/intensity-like quantity, `farfieldangle` can provide a non-uniform angle vector, and window integration should use a clearly documented method such as `farfield2dintegrate` or explicitly weighted numerical integration on the actual angle grid.

Original vs recalculated average metrics:

| metric | original H1F | recalculated audit |
|---|---:|---:|
| eta10 | 0.293481 | 0.2934811715566548 |
| eta20 | 0.679621 | 0.6796214780331167 |
| leakage20-40 | 0.766286 | 0.16590983227365963 |
| leakage40-60 | 0.227203 | 0.07753351102592027 |

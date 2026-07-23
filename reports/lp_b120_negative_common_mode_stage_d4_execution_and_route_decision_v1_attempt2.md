# APCD LP B120 negative common-mode Stage D4 execution and route decision v1

- Formal execution attempt: `ATTEMPT2_LP_ML_SCHEMA_V1.20`
- Status: `PASS`
- Frozen source order: A−1, A−2, A−3, A−4, A−5, B−1, B−2, B−3; each x/y at 450 nm.
- Solver calls: `16`; all checkpoint reloads and ML-row reloads passed.

## Audit gates

- Candidate-contract audit: `PASS`, `CASE_A_SUMMARY_ONLY_MISMATCH`.
- Erratum route: `D4_V1_FORMAL_PLAN_VALID_SUMMARY_ERRATUM_RECORDED`.
- Canonical v1.19 remained at 108 full-dimer geometries, 108 450-nm Jones rows, 192 wavelength Jones rows, and 384 formal subruns.
- Protected report SHA256 values remained unchanged. No FSP/FSPX/LDF/H5/MAT/NPY/NPZ artifact remains.
- Formal observable: full-period coordinate-weighted complex-field G0, duplicate-endpoint handling/reclosure, and sqrt(T)/norm(weighted Ex, weighted Ey). Jones ordering is [[txx,txy],[tyx,tyy]].

## Sequence result

| candidate | phase(deg) | Txx | Tyy | sigma2/sigma1 | R_total | projector preserved |
|---|---:|---:|---:|---:|---:|---|
| A−1 | 89.1044 | 0.99787 | 0.19023 | 0.43662 | 5.24555 | no |
| A−2 | 85.1483 | 0.99525 | 0.35012 | 0.59312 | 2.84260 | no |
| A−3 | 81.1709 | 1.00125 | 0.49986 | 0.70657 | 2.00305 | no |
| A−4 | 77.2109 | 0.99873 | 0.64363 | 0.80277 | 1.55172 | no |
| A−5 | 72.7072 | 0.99221 | 0.72308 | 0.85367 | 1.37220 | no |
| B−1 | 91.0720 | 1.00804 | 0.17677 | 0.41876 | 5.70263 | no |
| B−2 | 86.9283 | 1.01154 | 0.35250 | 0.59032 | 2.86964 | no |
| B−3 | 82.9632 | 1.01038 | 0.48468 | 0.69260 | 2.08464 | no |

Negative common mode gives a monotonic phase decrease of about 3.96–4.50 degrees per 1-nm negative step in both sequences, but each first negative point has already lost the projector state relative to its canonical backbone. The phase sign is therefore usable but this geometric coordinate is not a projector-manifold tangent.

## Decision

- Route: `GEOMETRIC_COMMON_MODE_NOT_A_PROJECTOR_PRESERVING_PHASE_COORDINATE`.
- Projector collapse step: `BACKBONE_TO_MINUS1` for both A and B.
- Recommended D4 anchor: none.
- D5 authorization: full-dimer Jacobian/joint-compensation planning is authorized; no D5 execution is part of this task.
- Spectral authorization remains `NOT_AUTHORIZED`; no spectrum, training, or canonical v1.20 merge was run.

Attempt-1 is retained as a no-solver provenance failure. Attempt-2 is the only formal 16-subrun dataset package.

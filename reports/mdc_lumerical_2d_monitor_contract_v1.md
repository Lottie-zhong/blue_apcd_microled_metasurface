# MDC Lumerical 2D monitor contract v1

Status: `contract_pass`.

## Official monitor contract

- Linear X integrates `Re(Py)` along x; Linear Y integrates `Re(Px)` along y.
- Closed-box outward flux is `F_right - F_left + F_top - F_bottom`; no absolute-value correction is used.
- Direct Poynting integration is canonical. `transmission * sourcepower` is diagnostic only; `dipolepower` is unused.

## Field channels

| dipole | dominant fields | dominant energy | leakage fraction | status |
|---|---|---:|---:|---|
| x | Ex, Ey, Hz | 4.142241e6 | 0 | pass |
| z | Ez, Hx, Hy | 5.810349e4 | 0 | pass |

The 2D solver returned all six named field components. Forbidden components were returned at numerical zero; no missing component was fabricated.

## Source-local mesh

Both cases reopened with `source_local_mesh` present at `(0, -400 nm)`, spans `100 nm x 100 nm`, `dx=dy=2 nm`, and x/y override enabled.

## Box outward flux

| dipole | inner | middle | outer |
|---|---:|---:|---:|
| x | 1.080503e-8 | 1.002862e-8 | 9.574545e-9 |
| z | 1.912331e-8 | 1.865308e-8 | 1.818321e-8 |

Every side has the expected raw sign: top/right positive and bottom/left negative. All outward contributions and all net box fluxes are positive. Flux decreases monotonically with box size, as expected for lossy GaN. This task validates the contract and trend; it does not select a canonical box.

## Homogeneous y=0 reference

| dipole | direct flux | diagnostic scalar | relative difference |
|---|---:|---:|---:|
| x | 1.184160e-9 | 1.184160e-9 | 1.75e-16 |
| z | 1.339988e-9 | 1.339988e-9 | 1.54e-16 |

Only the two homogeneous Native-M1 GaN x/z contract cases were run. No Bare, MDC, Wan proxy, broadband, material-policy, database, or frozen-TMM operation was performed.

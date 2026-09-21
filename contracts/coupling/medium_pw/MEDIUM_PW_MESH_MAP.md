# MEDIUM_PW mesh map

This is a setup-only, pre-entry contract for `W2H_15294`. It does not authorize
`run()` and does not replace the recovered 5 nm reference truth.

| Priority | Override | Span `(x,y,z)` nm | Step `(dx,dy,dz)` nm | Coverage |
|---:|---|---|---|---|
| 100 | `mesh_pillar_01..06_5nm` | pillar-specific xy box, z `1202..1722` | `5,5,5` | each finite cylinder plus 10 nm xy / 5 nm z margin |
| 90 | `mesh_mdc_spacer_interface_5nm` | `1740,290,20`, center z `975` | `5,5,5` | MDC/spacer interface |
| 90 | `mesh_spacer_pillar_interface_5nm` | `1740,290,20`, center z `1212` | `5,5,5` | spacer/pillar interface |
| 70 | `mesh_mdc_background_10nm` | `1740,290,975`, z `0..975` | `10,10,10` | MDC body |
| 70 | `mesh_spacer_background_10nm` | `1740,290,237`, z `975..1212` | `10,10,10` | spacer |
| 40 | `mesh_gan_homogeneous_15nm` | `1740,290,600`, z `-600..0` | `15,15,15` | homogeneous GaN |
| 30 | `mesh_air_homogeneous_20nm` | `1740,290,1288`, z `1712..3000` | `20,20,20` | homogeneous air |

The 5 nm boxes are not a full integrated-domain override: only the two thin
interface bands span the full periodic cell, and the remaining 5 nm regions
are six pillar-centered boxes. No override reaches either z-domain boundary.
The builder sets `override x/y/z mesh=1` and `set maximum mesh step=1` on each
region. Lumerical's conformal setting is frozen as `conformal variant 1` and
the PML uses its default mesh refinement.

The cell and RAM figures are pre-run estimates. They are not a substitute for
the later scientific validation gate.

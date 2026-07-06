# R2-4H1J2 monitor correction policy

Do not compare monitor y directly against top MDC child-layer local coordinates. Many objects use relative coordinates, so local child values such as y=1216-1316 nm are not automatically global coordinates.

H1J2 keeps the monitor unchanged unless one of these is clearly confirmed in global/effective coordinates:

1. the monitor is inside the top MDC stack;
2. the monitor is too close to the top PML;
3. the monitor is below the output-side structure.

If only local coordinates are accessible, monitor safety is `requires_manual_gui_audit`.

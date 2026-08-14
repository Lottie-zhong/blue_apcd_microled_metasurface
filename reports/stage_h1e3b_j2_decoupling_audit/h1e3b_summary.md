# H1E-3B J2 orientation-displacement decoupling audit

- J2_length/J2_width were already independent coordinates in the H500/H550 grammar; constant-mean d2 is a local search direction, not a new grammar DOF.
- Current coupling is `theta_J2=Psi` while centers use D/Psi.
- Route: `DECOUPLE_J2_ORIENTATION_FROM_DISPLACEMENT_FIRST`.
- Proposed DOF: `delta_theta_J2_deg`, recommended +/-1 deg, 6 geometries / 12 formal subruns, proposed only.
- Registry remains 506; ML admitted false; solver entered delta 0.

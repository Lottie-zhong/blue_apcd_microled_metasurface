# H1E-3A J1 rotation audit

- Psi is a coupled displacement azimuth and J2 rotation parameter; it is not a whole-dimer rotation.
- J1 rotation is implementation-independent of Psi/D/J2 orientation, but its analytic first-order response is off-diagonal Jones mixing: dJxx/dtheta=0 and dJxy/dtheta=a-b at theta=0.
- Rotation classification: `J1_ROTATION_PROJECTOR_RISK_DOMINANT`; +/-15 deg is not justified.
- Recommended first J1 angle scale if ever revisited: +/-2 deg, but no J1 rotation probe is approved here.
- Preferred alternative: `independent_J2_anisotropy_d_nm`, proposed only as 6 geometries / 12 subruns.
- Registry remains 506 rows; ML remains not admitted; solver_entered_delta=0.

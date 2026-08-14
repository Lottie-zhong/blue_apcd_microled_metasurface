# Rotated anisotropic J1 Jones model

For `J1(theta)=R(theta) diag(a,b) R(-theta)` with `R=[[cos,-sin],[sin,cos]]`,

- `Jxx = a cos^2(theta) + b sin^2(theta)`
- `Jxy = Jyx = (a-b) sin(theta) cos(theta)`
- `Jyy = a sin^2(theta) + b cos^2(theta)`

At theta=0:

- `dJxx/dtheta = 0`
- `dJxy/dtheta = dJyx/dtheta = a-b`
- `dJyy/dtheta = 0`

Therefore a non-isotropic J1 rotation is first-order projector-basis mixing, while its diagonal common-phase response starts at second order. It is not assumed to be a PB/geometric phase knob. The response becomes dependent on near-isotropy only when `a-b` is itself small; near an anisotropic resonance, cross-polarization risk can dominate.

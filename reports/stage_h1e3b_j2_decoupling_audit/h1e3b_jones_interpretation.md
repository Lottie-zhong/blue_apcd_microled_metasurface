# H1E-3B J2 orientation decoupling

The existing builder uses `theta_J2 = Psi`. For `J2(theta)=R(theta)diag(a,b)R(-theta)`, a decoupled `delta_theta_J2` gives, evaluated at `theta=Psi`,

- `dJxx/d(delta_theta)=(b-a) sin(2 Psi)`
- `dJxy/d(delta_theta)=(a-b) cos(2 Psi)`
- `dJyx/d(delta_theta)=(a-b) cos(2 Psi)`
- `dJyy/d(delta_theta)=(a-b) sin(2 Psi)`

Thus the plausible benefit is compensation/selection: spatial coupling can be changed through Psi without being forced to rotate the J2 eigenaxis by the same amount. This is not a claim that delta-theta directly supplies scalar common phase.

from pathlib import Path
import numpy as np
import r1_angular_spectrum as r

def run():
    out={}
    n=32;L=3.2e-6;x=np.linspace(-L/2,L/2-L/n,n);y=x.copy()
    f=6.0e14;k0=2*np.pi*f/r.C0;kx0=2*np.pi*3/L;ky0=2*np.pi*2/L
    rho=np.hypot(kx0,ky0)/k0;w=np.sqrt(1-rho*rho);qx=kx0/(k0*rho);qy=ky0/(k0*rho)
    p=np.array([w*qx,w*qy,-rho]);s=np.array([-qy,qx,0.])
    e=p+0.4j*s;kh=np.array([rho*qx,rho*qy,w]);h=np.cross(kh,e)/r.ETA0
    phase=np.exp(1j*(kx0*x[:,None]+ky0*y[None,:]));field=np.stack([e[i]*phase for i in range(3)]+[h[i]*phase for i in range(3)])
    kx,ky=r.kgrid(x,y);spec=np.zeros((6,n,n),complex);ix=int(np.argmin(abs(kx-kx0)));iy=int(np.argmin(abs(ky-ky0)))
    spec[:3,ix,iy]=e;spec[3:,ix,iy]=h
    _,prop,evan,graz=r.classify(kx,ky,k0);m=r.maxwell(spec,kx,ky,f,prop)['best_fixed']
    assert m['temporal_sign']==1 and m['fixed_residual']<1e-8,m
    out['maxwell_temporal_sign']='PASS'
    assert not np.any(prop & evan) and np.any(graz)
    out['classification']='PASS'
    xn=np.sort(np.r_[x[:8]+np.linspace(-1e-10,1e-10,8),x[8:]])
    assert np.all(np.diff(xn)>0)
    u=r.uniform_grid(xn,n);q=np.exp(.3j*xn[:,None])*np.ones((n,n));qi=r.interpolate(q,xn,xn,u,u)
    assert np.all(np.isfinite(qi))
    out['complex_interpolation']='PASS'
    assert abs(r.flux(field,x,y)-r.flux(field,x,y))<1e-30
    out['real_flux_deterministic']='PASS'
    return out

if __name__=='__main__': print(run())

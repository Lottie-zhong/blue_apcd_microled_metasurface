import cmath, math, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
import apcd_native_materials as native
import mdc_dipole_tmm as d

def test_native_materials_and_range_guard():
    for mid in ('APCD_GAN_NATIVE_M1','APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1'):
      data=native.load_native_sampled_epsilon(mid); assert len(data['frequency_hz']) >= 101; assert np.isfinite(data['epsilon']).all()
    assert native.get_complex_epsilon('APCD_GAN_NATIVE_M1',450).imag > 0
    try: native.get_complex_epsilon('APCD_GAN_NATIVE_M1',100)
    except ValueError: pass
    else: assert False

def test_identity_fresnel_and_smatrix():
    eps=native.get_complex_epsilon('APCD_GAN_NATIVE_M1',450)
    r=d.rt_smatrix(eps,eps,(),450,12,'TE'); assert r['R'] < 1e-12 and abs(r['T']-1)<1e-12
    one=d.rt_smatrix(eps,1+0j,(),450,0,'TE'); n=cmath.sqrt(eps); assert abs(one['R']-abs((n-1)/(n+1))**2)<1e-10
    from mdc_tmm_core import tmm_complex
    old=tmm_complex(n,1+0j,[(cmath.sqrt(native.get_complex_epsilon('APCD_TIO2_NATIVE_M1',450)),44)],450,0,'TE')
    new=d.rt_smatrix(eps,1+0j,(("APCD_TIO2_NATIVE_M1",44),),450,0,'TE'); assert abs(old['T']-new['T'])<0.003

def test_symmetry_depth_phase_and_polarization():
    c=d.P1_ZL1_ALTERNATIVE_G3_A3
    a=d.dipole_channel(c,450,35,-400,'x'); b=d.dipole_channel(c,450,-35,-400,'x'); assert abs(a['I_air_relative']-b['I_air_relative'])<1e-12
    p1=d.dipole_channel(c,450,10,-400,'z')['source_phase']; p2=d.dipole_channel(c,450,10,-401,'z')['source_phase']; assert abs(p1-p2)<.1
    assert d.dipole_channel(c,450,10,-400,'x')['T_plane_wave'] != d.dipole_channel(c,450,10,-400,'z')['T_plane_wave']

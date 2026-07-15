import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import mdc_fdtd_2d_monitor_contract_v1 as C
import numpy as np
def test_outward_signs_no_abs():
 r=C.calculate_box_outward_flux({'right':4,'left':-3,'top':2,'bottom':-1});assert r['net_outward']==10
def test_monitor_types_and_direct_poynting_present():
 t=(ROOT/'scripts'/'mdc_fdtd_2d_monitor_contract_v1.py').read_text();assert "'Linear X'" in t and "'Linear Y'" in t and 'np.trapezoid' in t
def test_noncanonical_sources_not_used():
 t=(ROOT/'scripts'/'validate_mdc_lumerical_2d_monitor_contract_v1.py').read_text().lower();assert 'dipolepower(' not in t
 assert "'canonical_flux':'direct_poynting_integral'" in t
def test_broadband_line_flux_integrates_spatial_axis_only():
 x=np.array([0.,1.,2.]);fields={'x':x,'y':None,'Ex':np.ones((3,2)),'Ey':None,'Ez':None,'Hx':None,'Hy':None,'Hz':-2*np.ones((3,2))}
 value=C.integrate_line_poynting_flux(fields,'Linear X');assert np.allclose(value,[2,2])
def test_broadband_monitor_uses_validated_source_limits_contract():
 t=(ROOT/'scripts'/'mdc_fdtd_2d_monitor_contract_v1.py').read_text();assert "'use wavelength spacing',True" in t
 assert "fdtd.set('wavelength start'" not in t and "fdtd.set('wavelength stop'" not in t

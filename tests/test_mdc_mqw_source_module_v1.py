import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from mdc_mqw_source_module import load
import mdc_dipole_tmm as d
def test_primary_coordinates_weights_and_centroid():
 c=load(); assert c['primary_mqw']['well_centers_nm'][0]==-171.5; assert c['primary_mqw']['well_centers_nm'][-1]==-380.5; assert abs(sum(c['primary_mqw']['weights'])-1)<1e-12; assert c['strain_release_mqw']['formal_primary_emission_weight']==0
def test_incoherent_average_and_symmetry():
 c=d.P1_ZL1_ALTERNATIVE_G3_A3;x=d.dipole_channel(c,450,20,-276,'x')['I_air_relative'];z=d.dipole_channel(c,450,20,-276,'z')['I_air_relative']; assert .5*(x+z)>0; assert abs(d.dipole_channel(c,450,20,-276,'x')['I_air_relative']-d.dipole_channel(c,450,-20,-276,'x')['I_air_relative'])<1e-12

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_mdc_minimal_2d_fdtd_dipole_tmm_validation_v1 as r
def test_plan_is_exactly_bounded_and_oriented():
 p=r.plan();assert len(p)==18;assert sum(x['stage']=='A' for x in p)==2;assert {x['orientation'] for x in p}=={'x','z'};assert {x['theta_deg'] for x in p if x['orientation']=='x'}=={90};assert {x['theta_deg'] for x in p if x['orientation']=='z'}=={0}
def test_candidate_and_geometry_contract():
 c=r.candidates();assert len(c)==3;assert c[1]['geometry_hash']=='c38694d6f162c04322ae8a87def91622d4fd4f272e4ec286e85acc978f74d888'

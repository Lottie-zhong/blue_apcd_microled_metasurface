import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs'/'np_k6_p1d0_contract_v1'
def test_contract():
 g=json.loads((O/'coarse_grid_contract.json').read_text());assert len(g['candidates'])==15 and all(x['fabrication_valid']for x in g['candidates']);assert next(x for x in g['candidates']if x['candidate_id']=='NP_P1D_H600_D110')['near_aspect_ratio_limit'];assert next(x for x in g['candidates']if x['candidate_id']=='NP_P1D_H400_D230')['gap_nm']==60
def test_reference_and_audit():
 r=json.loads((O/'reference_plane_contract.json').read_text());a=json.loads((O/'blank_equivalence_audit.json').read_text());s=json.loads((O/'setup_validation.json').read_text());assert not r['phase_deembedding_used'] and r['reference_plane_quality']=='pass';assert not a['equivalent'] and a['blank_strategy'].startswith('run_one');assert s['solver_run_count']==0 and s['corner_setups_validated']==2

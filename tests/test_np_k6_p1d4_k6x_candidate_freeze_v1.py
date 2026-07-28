import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_candidate_freeze():
 p=ROOT/'scripts'/'build_np_k6_p1d4_k6x_candidate_freeze_v1.py';assert 'import lumapi' not in p.read_text();runpy.run_path(str(p),run_name='__main__')
 c=json.loads((ROOT/'outputs/np_k6_p1d4_k6x_candidate_freeze_v1'/'selected_k6x_candidates.json').read_text())['candidates'];assert len(c)==3 and len({x['candidate_id'] for x in c})==3 and all(x['engineering_pass'] and x['minimum_edge_gap_nm']>=60 and x['max_aspect_ratio']<=5.5 for x in c)
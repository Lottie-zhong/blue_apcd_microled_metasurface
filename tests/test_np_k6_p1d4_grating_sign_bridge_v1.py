import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def test_sign_bridge_and_proxy():
 o=R/'outputs/np_k6_p1d4_k6x_candidate_freeze_v1';b=json.loads((o/'grating_sign_bridge.json').read_text());assert b['monitor_plane']=='XY' and b['gratingn_axis']=='x' and b['target_gratingn']==1 and b['target_u_x_sign']=='positive'
 p=json.loads((o/'local_period_dft_proxy.json').read_text())['candidates'];assert len(p)==3 and all(x['proxy_dominant_order_450']==1 for x in p)
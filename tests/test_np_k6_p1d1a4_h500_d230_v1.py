import json
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
def test_closure():
 o=R/'outputs/np_k6_p1d1a4_h500_d230_v1';r=json.loads((o/'results.json').read_text());l=json.loads((o/'phase_line_analysis.json').read_text());c=json.loads((R/'outputs/np_k6_p1d2_broadband_contract_v1/broadband_library_contract.json').read_text());assert r['candidate_id']=='NP_P1D_H500_D230' and r['source_post_fsp']==r['post_fsp_readonly_after'] and len(l['diameters_nm'])==5 and l['provisional_five_point_unwrap'] and l['usable_coarse_2pi_candidate'] and c['selected_height_nm']==500 and c['P1D2_SOLVER_RELEASE'] is True

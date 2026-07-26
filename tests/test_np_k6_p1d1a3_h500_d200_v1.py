import json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
def test_d200_and_spectral_readiness():
 out=ROOT/'outputs/np_k6_p1d1a3_h500_d200_v1';r=json.loads((out/'results.json').read_text());a=json.loads((out/'spectral_availability_audit.json').read_text());c=json.loads((ROOT/'outputs/np_k6_p1d2_broadband_contract_v1/broadband_library_contract.json').read_text())
 assert r['candidate_id']=='NP_P1D_H500_D200' and r['new_solver_runs_started_this_thread']==0 and r['source_post_fsp']==r['post_fsp_readonly_after'] and r['R_total']==-r['R_raw']
 assert a['target_wavelength_grid_nm']==list(range(445,456)) and a['PROVISIONAL_10NM_SPECTRAL_AUDIT']=='not_available'
 assert c['wavelength_grid_nm']==list(range(445,456)) and c['dense_diameter_grid_nm']==list(range(100,231,5))
 assert (c['selected_height_nm'],c['P1D2_SOLVER_RELEASE']) in {(None,False),(500,True)}

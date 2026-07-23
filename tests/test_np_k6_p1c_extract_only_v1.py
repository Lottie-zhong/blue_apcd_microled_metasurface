import csv, hashlib, json, math
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs'/'np_k6_p1c_singlepoint_v1'
def j(n):return json.loads((O/n).read_text())
def test_extract_only_gates():
 r,m=j('results.json'),j('run_manifest.json')
 assert r['solver_run_count_this_thread']==0 and r['fsp_save_count_this_thread']==0 and not r['weighted_G0_used'] and r['read_existing_postrun_only']
 assert r['fsp_integrity_start']==r['fsp_integrity_final'] and r['data_quality']=='pass' and r['candidate_quality']=='pass'
 for x in r['subruns'].values():
  assert x['monitor_data_present'] and x['monitor_data_finite'] and x['E_shape'][-1]==3 and x['energy_residual']<=.03
  assert all(math.isfinite(x[p][q]) for p in ('ax','ay') for q in ('real','imag','amplitude'))
 c=r['combined_candidate'];assert c['single_propagating_order_gate'] and c['jones_relative_residual_x']<=.03 and c['jones_relative_residual_y']<=.03
 assert c['copol_amplitude_mismatch']<=.02 and c['copol_power_mismatch']<=.02 and abs(c['copol_phase_mismatch_deg'])<=3
 assert c['cross_pol_fraction_x']<=.01 and c['cross_pol_fraction_y']<=.01
 with (O/'results.csv').open() as f:rows=list(csv.DictReader(f))
 assert [x['case_id'] for x in rows]==['blank_x','pillar_x','blank_y','pillar_y','combined']
 assert math.isclose(float(rows[-1]['txx_real']),c['jones']['txx']['real'])
 assert m['results_json_sha256']==hashlib.sha256((O/'results.json').read_bytes()).hexdigest()

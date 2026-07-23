import csv,hashlib,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs'/'np_k6_p1d0b_corner_pilot_v1'
def load(n):return json.loads((O/n).read_text())
def test_recovered_data_gate():
 r,m=load('results.json'),load('run_manifest.json');assert r['new_solver_runs_this_thread']==0 and r['recovered_unique_completed_case_count']==3 and r['minimum_prior_completed_solver_runs']==3 and r['exact_prior_solver_run_started_count']is None and r['solver_run_accounting_quality']=='recovered_lower_bound_only' and r['fsp_read_only_gate']=='pass'
 b=r['blank'];assert b['kind']=='blank'and b['audit']['pillar_count']==0 and math.isclose(b['audit']['T_z'],9e-7,rel_tol=0,abs_tol=1e-18) and b['polarization']=='x'
 assert len(r['pillars'])==2
 for x,h,d in zip(r['pillars'],(600,400),(110,230)):
  assert x['H_nm']==h and x['D_nm']==d and x['audit']['pillar_base']==0 and math.isclose(x['audit']['T_z'],9e-7,rel_tol=0,abs_tol=1e-18) and x['recovery_status']=='trusted_recovered_postrun' and x['reference_blank_hash']==b['post_fsp']['sha256'] and x['polarization_completeness']=='x_only'
  assert math.isclose(x['R_total'],-x['R_raw']) and x['monitor_data_finite'] and all(math.isfinite(x[k])for k in('T','R_raw','R_total','energy_residual','cross_pol_fraction','x_input_jones_power_reconstruction_residual'))
  den=complex(b['ax']['real'],b['ax']['imag']);assert abs(complex(x['txx']['real'],x['txx']['imag'])-complex(x['ax']['real'],x['ax']['imag'])/den)<1e-12
  assert 'txy' not in x and 'tyy' not in x
 with (O/'results.csv').open()as f:rows=list(csv.DictReader(f))
 assert [x['candidate_id']for x in rows]==['NP_P1D_H600_D110','NP_P1D_H400_D230']
 assert m['results_json_sha256']==hashlib.sha256((O/'results.json').read_bytes()).hexdigest()


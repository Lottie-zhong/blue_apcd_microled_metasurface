import csv,hashlib,json,math
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
EV=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2'
CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2'
def j(name): return json.loads((EV/name).read_text(encoding='utf-8-sig'))
def main():
 c=j('classification.json'); b=j('closure_audit.json'); l=j('entered_ledger.json'); r=j('runtime_execution_audit.json'); p=j('post_fsp_checksum.json'); q=j('provenance_audit.json'); d=j('data_gate.json'); raw=j('raw_power_and_grid_audit.json')
 rows=list(csv.DictReader((EV/'spectral_metrics_11points.csv').open(encoding='utf-8')))
 assert c['classification']=='SIMULATION_TIME_EXTENSION_CLOSURE_PASS_DECAY_CONVERGENCE_UNRESOLVED'
 assert len(rows)==11 and [int(x['wavelength_nm']) for x in rows]==list(range(445,456))
 assert all(math.isfinite(float(x['T_total'])) and math.isfinite(float(x['R_total'])) and math.isfinite(float(x['raw_transmitted_power_W'])) and math.isfinite(float(x['raw_reflected_power_W'])) and math.isfinite(float(x['sourcepower_W'])) for x in rows)
 assert b['max_abs_residual_2ps']>0.02 and b['max_abs_residual_2ps']<b['old_1ps_max_abs_residual']
 assert b['order_sum_mismatch_max']<=1e-8 and c['G2_pass'] is True and c['A2_pass'] is False
 assert l['entered'] is True and l['run_invocation_count']==1 and l['attempt_002_forbidden'] is True
 assert r['engine_completed'] and r['post_saved'] and r['controller_returned'] is False and r['controller_recovery_completed']
 assert p['sha256']=='f0119e256cf64e4875d82c0c5cca3dbc854936fc429aca4643577d7b2b1005d7'
 assert q['source_setup_immutable'] and q['old_1ps_attempt_immutable'] and not q['external_mdc_accessed']
 assert d['formal_hf_labels']==0 and d['candidate_performance_labels']==0 and d['checkpoint_count']==0 and d['remaining_five_cases_untouched']
 assert raw['direct_power_available'] and raw['normalization_gate_pass'] and raw['max_transmission_normalization_mismatch']<=1e-8 and raw['max_reflection_normalization_mismatch']<=1e-8
 assert raw['coordinate_hashes']['transmission_monitor']['x']['sha256'] and raw['coordinate_hashes']['transmission_monitor']['y']['sha256'] and raw['coordinate_hashes']['N1_DIAG_XZ_INDEX_449']['z']['sha256']
 assert not list(EV.glob('*.fsp')) and not list(EV.glob('*.log'))
 print(json.dumps({'pass':True,'case_id':CASE,'classification':c['classification'],'entered':1,'run_invocation_count':1,'post_sha256':p['sha256'],'closure_max':b['max_abs_residual_2ps'],'order_mismatch_max':b['order_sum_mismatch_max']},indent=2))
if __name__=='__main__': main()

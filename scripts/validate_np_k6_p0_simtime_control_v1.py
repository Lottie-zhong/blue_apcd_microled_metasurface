import argparse, csv, hashlib, json
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); STAGE=ROOT/'outputs/np_k6_p0_simulation_time_extension_control_v1'; CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_CONTROL_V1'; CDIR=STAGE/'cases'/CASE; RUN=STAGE/'runtime_runs'/CASE/'attempt_001'
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b):h.update(b)
 return h.hexdigest()
def main():
 errors=[]; c=json.loads((CDIR/'setup_contract.json').read_text()); l=json.loads((CDIR/'attempt_ledger.json').read_text()); setup=Path(c['source_prefsp_path'])
 if c.get('simulation_time_s')!=2e-12: errors.append('simulation_time')
 if abs(c.get('auto_shutoff_min',0)-1e-5)>1e-12: errors.append('auto_shutoff')
 if c.get('unexpected_differences')!=[]: errors.append('unexpected_differences')
 if not setup.exists() or sha(setup)!=c.get('source_prefsp_sha256'): errors.append('setup_sha')
 if not l.get('entered') or l.get('run_invocation_count')!=1: errors.append('ledger_once')
 for k in ['engine_completed','post_saved','controller_returned']:
  if not l.get(k): errors.append(k)
 post=Path(l.get('post_fsp_path',''))
 if not post.exists() or sha(post)!=l.get('post_fsp_sha256'): errors.append('post_sha')
 ex=STAGE/'runtime_extraction_summary.json'
 if not ex.exists(): errors.append('extraction_missing')
 else:
  e=json.loads(ex.read_text()); rows=list(csv.DictReader((STAGE/'cases'/CASE/'spectral_metrics_11points.csv').open(encoding='utf-8')))
  if len(rows)!=11: errors.append('wavelength_count')
  if [int(float(x['wavelength_nm'])) for x in rows]!=list(range(445,456)): errors.append('wavelength_grid')
  for w in [448,449,450]:
   if not any(int(float(x['wavelength_nm']))==w for x in rows): errors.append(f'missing_{w}')
  if e.get('quality_gates',{}).get('order_mismatch_pass') is False: errors.append('order_mismatch')
 result={'validator':'np_k6_p0_simtime_control_v1','case_id':CASE,'errors':errors,'pass':not errors,'entered':l.get('entered'),'run_invocation_count':l.get('run_invocation_count'),'no_partial_promotion':True,'training_label':False,'candidate_performance_label':False,'old_case_immutable_required':True}
 (STAGE/'standalone_validator_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2)); raise SystemExit(0 if not errors else 1)
if __name__=='__main__':main()

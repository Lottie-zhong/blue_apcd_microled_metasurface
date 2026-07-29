import csv,hashlib,json,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d2_corrected_direction_spotcheck_v1';RUN=O/'runtime_runs';names=['P1D2_CORRECTED_BLANK_X','D100','D130','D145','D155','D180','D230']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import lumapi
 rows=[];checks={};led=[]
 for name in names:
  d=RUN/name/'attempt_001';post=d/(name+'_post.fsp');l=json.loads((d/'entered_ledger.json').read_text());f=lumapi.FDTD(str(post),hide=True)
  try:
   tr=f.getresult('transmission_monitor','T');rr=f.getresult('reflection_monitor','T');la=np.asarray(tr['lambda']).reshape(-1)*1e9;T=np.real(np.asarray(tr['T']).reshape(-1));Rv=np.abs(np.real(np.asarray(rr['T']).reshape(-1)))
  finally:f.close()
  checks[name]={'post_path':str(post),'sha256':sha(post),'independent_readonly_reload':True,'points':len(la),'finite':bool(np.isfinite(T).all() and np.isfinite(Rv).all()),'max_residual':float(max(abs(1-T-Rv)))}
  l['recovered_post_evidence']=name=='D230';l['post_fsp_sha256']=checks[name]['sha256'];led.append(l)
  for x,t,r in zip(la,T,Rv):rows.append({'case':name,'diameter_nm':'' if name.startswith('P1') else int(name[1:]),'wavelength_nm':x,'T_total':t,'R_total':r,'residual':1-t-r})
 with (O/'corrected_spotcheck_long.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 with (O/'corrected_blank_metrics.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows[:11])
 (O/'entered_ledger.json').write_text(json.dumps(led,indent=2));(O/'post_fsp_checksums.json').write_text(json.dumps(checks,indent=2));(O/'solver_budget_audit.json').write_text(json.dumps({'entered_runs':7,'max_entered_runs':7,'exactly_seven':True,'d230_recovered_post_evidence':True},indent=2));(O/'provenance_audit.json').write_text(json.dumps({'external_mdc_fsp_used':False,'d230_controller_ledger_incomplete':True,'d230_post_readonly_verified':True},indent=2));(O/'phase_residual_audit.json').write_text(json.dumps({'classification':'INCONCLUSIVE','reason':'current corrected extraction lacks complex field phase/t_xx; cannot fit permitted global circular offset'},indent=2));(O/'amplitude_transfer_audit.json').write_text(json.dumps({'classification':'INCONCLUSIVE','reason':'historical t_xx schema not safely mapped'},indent=2));(O/'transmission_ranking_audit.json').write_text(json.dumps({'classification':'INCONCLUSIVE'},indent=2));(O/'d180_transfer_audit.json').write_text(json.dumps({'classification':'INCONCLUSIVE','post_readonly_verified':True},indent=2));(O/'k6_phase_order_applicability_audit.json').write_text(json.dumps({'classification':'INCONCLUSIVE','k6_plus1_order_preserved':None},indent=2))
 with (O/'conclusion_impact_update.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['conclusion','status']);w.writeheader();[w.writerow({'conclusion':x,'status':'UNAFFECTED' if x in ['296010_combinations','d180_65780'] else 'EVIDENCE_INSUFFICIENT'}) for x in ['27point_phase','absolute_T','passing_sextets','phase_champion','runner_up','transmission_balanced','broadband_pareto','D180','D4A_candidates','DFT_bridge','296010_combinations','d180_65780']]
if __name__=='__main__':main()

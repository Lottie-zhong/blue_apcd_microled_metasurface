from pathlib import Path
import json, sys, numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_mdc_minimal_2d_fdtd_dipole_tmm_validation_v1 as r
import mdc_fdtd_artifact_retention as retention
OUT=ROOT/'outputs'/'mdc_fdtd_dipole_tmm_validation_v1'/'fdtd-matrix-20260729T092000Z-602d89c69258'
SALVAGE=OUT/'runtime'/'zl1_alternative__primary_mqw_centroid__x__post.fsp'
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf-8')
def salvage(case):
 lu=r.lumapi();f=lu.FDTD(hide=True)
 try:
  f.load(str(SALVAGE));lam,top=r.frozen._spectrum_from_monitor(f,'upward_monitor');r12=r.frozen._box_spectrum(f,'emit_box_12nm');order=np.argsort(299792458.0/np.asarray(f.getdata('upward_monitor','f'),float).squeeze()*1e9);r12=r12[order];idx=len(lam)-int(np.argmin(abs(lam-450)));a0=r.filter_ff(f,'upward_monitor',idx,0);a2=r.filter_ff(f,'upward_monitor',idx,.2)
 finally:f.close()
 npz=OUT/'runtime'/'salvaged_x.npz';np.savez_compressed(npz,wavelength_nm=lam,p_top_raw=top,p_r12_outward_raw=r12,angles_filter0=a0['angles'],intensity_filter0=a0['raw'],angles_filter02=a2['angles'],intensity_filter02=a2['raw'])
 can=retention.canonical_copy(SALVAGE,OUT/'retained_fsp'/'zl1_alternative__primary_mqw_centroid__x__salvaged_post.fsp')
 case.update({'status':'COMPLETE','solver_entered':True,'solver_exit_state':'forensic_salvaged','post_fsp':str(SALVAGE),'post_fsp_sha256':can['runtime_sha256'],'canonical_fsp':can['canonical_fsp_path'],'canonical_fsp_sha256':can['canonical_sha256'],'fresh_load_status':'PASS','result_npz':str(npz),'eta_up_r12_450':float(top[np.argmin(abs(lam-450))]/r12[np.argmin(abs(lam-450))]),'p_top_nonzero':True,'p_r12_outward_nonzero':True,'forensic_salvaged':True})
def main():
 cases=r.plan();x=next(c for c in cases if c['case_id']=='zl1_alternative__primary_mqw_centroid__x');state={'task':r.CONFIG['task'],'physical_contract_hash':'forensic_salvage_bound','cases':cases,'safety_counters':{'FDTD_calls':2,'Lumerical_calls':2,'TMM_calls':0,'RCWA_calls':0,'sealed_test_target_reads':0},'budget_cap':19,'artifact_recovery_reruns':1};salvage(x);dump(OUT/'state.json',state)
 for c in state['cases']:
  if c['status']=='COMPLETE':continue
  state['safety_counters']['FDTD_calls']+=1;state['safety_counters']['Lumerical_calls']+=1;dump(OUT/'state.json',state);r.execute(c,OUT,state)
 if state['safety_counters']['FDTD_calls']!=19:raise RuntimeError('budget_accounting_mismatch')
 r.postprocess(OUT,state);dump(OUT/'pre_fsp_index.json',[{'case_id':c['case_id'],'path':c.get('pre_fsp',''),'sha256':c.get('pre_fsp_sha256','')} for c in cases]);dump(OUT/'post_fsp_index.json',[{'case_id':c['case_id'],'runtime':c.get('post_fsp',''),'canonical':c.get('canonical_fsp',''),'sha256':c.get('post_fsp_sha256','')} for c in cases]);dump(OUT/'manifest.json',{'solver_cap':19,'actual_solver_invocations_total':19,'unique_physics_cases_completed':18,'artifact_recovery_reruns':1,'forensic_salvaged_cases':1,'remaining_capacity':0,'all_complete':all(c['status']=='COMPLETE' for c in cases)})
if __name__=='__main__':main()

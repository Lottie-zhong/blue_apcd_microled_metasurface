import csv, gzip, hashlib, itertools, json, math, os
from pathlib import Path
import numpy as np

R=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
LIB=R/'outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv'
OUT=R/'outputs/np_k6_ml_d0_database_foundation_v1'; OUT.mkdir(parents=True,exist_ok=True)
DS=tuple(range(100,231,5)); WL=np.arange(445,456,dtype=np.int16); M=np.arange(-3,4,dtype=np.int8); K=6; P=290; H=500; LX=1740; LY=290
POS=np.array([-725,-435,-145,145,435,725],dtype=np.int16); EXP=np.exp(-2j*np.pi*np.outer(M,np.arange(6))/6).astype(np.complex64)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def jwrite(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
def canonical_payload(d):
 return {'schema_version':'canonical_k6_geometry_v1','geometry_id':'K6X_'+'_'.join(f'D{x}' for x in d),'diameters_nm':list(map(int,d)),'phase_bin_mapping':{'phase_bin':[0,1,2,3,4,5],'x_nm':POS.tolist(),'ideal_phase_deg':[0,60,120,180,240,300]},'period_x_nm':LX,'period_y_nm':LY,'pillar_height_nm':H,'material_contract_ids':['APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1'],'target_order':1,'target_direction':'+x'}
def geom_hash(payload): return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load():
 rows=list(csv.DictReader(LIB.open(encoding='utf-8'))); assert len(rows)==297
 arr={k:np.empty((27,11),np.float64) for k in ['T','R','txx_real','txx_imag','amp','phase','tyx','cross','energy','recon']}; di={d:i for i,d in enumerate(DS)}
 for r in rows:
  d=int(r['diameter_nm']); w=int(r['wavelength_nm']); i=di[d]; j=w-445
  arr['T'][i,j]=float(r['T']); arr['R'][i,j]=float(r['R']); arr['txx_real'][i,j]=float(r['txx_real']); arr['txx_imag'][i,j]=float(r['txx_imag']); arr['amp'][i,j]=float(r['txx_amplitude']); arr['phase'][i,j]=float(r['txx_wrapped_phase_deg']); arr['tyx'][i,j]=float(r['tyx_amplitude']); arr['cross'][i,j]=float(r['cross_pol']); arr['energy'][i,j]=float(r['energy_residual']); arr['recon'][i,j]=float(r['reconstruction_residual'])
 assert all(np.isfinite(x).all() for x in arr.values()); return arr
def gap_features(d):
 d=np.asarray(d,float); gaps=P-(d+np.roll(d,-1))/2; jumps=np.diff(d); return {'gap_01_nm':float(gaps[0]),'gap_12_nm':float(gaps[1]),'gap_23_nm':float(gaps[2]),'gap_34_nm':float(gaps[3]),'gap_45_nm':float(gaps[4]),'gap_50_periodic_nm':float(gaps[5]),'min_gap_nm':float(gaps.min()),'mean_gap_nm':float(gaps.mean()),'gap_std_nm':float(gaps.std()),'max_adjacent_diameter_jump_nm':float(jumps.max()),'mean_adjacent_diameter_jump_nm':float(jumps.mean()),'periodic_edge_diameter_jump_nm':float(abs(d[-1]-d[0])),'diameter_range_nm':float(d.max()-d.min()),'diameter_mean_nm':float(d.mean()),'diameter_std_nm':float(d.std())}
def dft_chunk(ix,arr):
 t=(arr['txx_real'][ix].transpose(0,2,1)+1j*arr['txx_imag'][ix].transpose(0,2,1)).astype(np.complex64) # n,w,j
 A=np.einsum('nwj,mj->nwm',t,EXP,optimize=True); power=np.abs(A)**2; eta=power/power.sum(axis=2,keepdims=True); prop=eta[:,:,2:5].sum(axis=2); plus=eta[:,:,4]/np.maximum(prop,1e-12); ph=np.angle(t); delta=np.angle(np.exp(1j*(ph-np.radians(np.arange(6)*60)[None,None,:]))); off=np.angle(np.mean(np.exp(1j*delta),axis=2)); err=np.angle(np.exp(1j*(delta-off[:,:,None]))); rmse=np.sqrt(np.mean(np.degrees(err)**2,axis=2)); flat=np.std(np.abs(t),axis=2)/np.maximum(np.mean(np.abs(t),axis=2),1e-12)
 return {'A_real':A.real.astype(np.float32),'A_imag':A.imag.astype(np.float32),'A_abs':np.abs(A).astype(np.float32),'A_phase':np.angle(A).astype(np.float32),'eta_m_proxy':eta.astype(np.float32),'propagating_sum_proxy':prop.astype(np.float32),'plus1_fraction_proxy':plus.astype(np.float32),'phase_rmse_deg':rmse.astype(np.float32),'amplitude_flatness':flat.astype(np.float32),'T_single':arr['T'][ix].astype(np.float32),'R_single':arr['R'][ix].astype(np.float32),'geometry_index':np.asarray(ix,dtype=np.int32),'wavelength_nm':WL}
def feature_row(i,d,hashv,split,arr,lf):
 p=lf['plus1_fraction_proxy'][i]; eta=lf['eta_m_proxy'][i]; didx=[list(DS).index(x) for x in d]; amp=arr['amp'][didx]
 return {'geometry_id':'K6X_'+'_'.join(f'D{x}' for x in d),'geometry_hash':hashv,'split':split,'D0':d[0],'D1':d[1],'D2':d[2],'D3':d[3],'D4':d[4],'D5':d[5],**gap_features(d),'lf_plus1_fraction_proxy_450':float(p[5]),'lf_plus1_fraction_proxy_band_min':float(p.min()),'lf_plus1_fraction_proxy_band_mean':float(p.mean()),'lf_plus1_fraction_proxy_band_max':float(p.max()),'lf_zero_order_fraction_proxy_450':float(eta[5,3]),'lf_minus1_fraction_proxy_450':float(eta[5,2]),'lf_leakage_fraction_proxy_450':float(1-eta[5,2:5].sum()),'lf_directionality_proxy_450':float(eta[5,4]/max(eta[5,4]+eta[5,2],1e-12)),'lf_phase_rmse_450_deg':float(lf['phase_rmse_deg'][i,5]),'lf_phase_rmse_band_max_deg':float(lf['phase_rmse_deg'][i].max()),'lf_amplitude_flatness_450':float(lf['amplitude_flatness'][i,5]),'min_single_pillar_T':float(arr['T'][didx].min()),'mean_single_pillar_T':float(arr['T'][didx].mean()),'single_pillar_T_std':float(arr['T'][didx].std()),'broadband_robustness_proxy':float(p.min())}
def main():
 arr=load(); combos=list(itertools.combinations(DS,6)); assert len(combos)==296010
 payloads=[canonical_payload(d) for d in combos]; hashes=[geom_hash(p) for p in payloads]
 protected={'100,115,130,145,155,185','125,135,150,175,190,210','130,145,155,180,195,230','100,115,130,145,155,185','110,125,135,150,175,190','110,125,135,150,175,195','110,125,135,155,175,195','115,125,135,155,180,195','125,135,150,175,190,210'}
 order=sorted(range(len(combos)),key=lambda i:hashes[i]); prot=[i for i,d in enumerate(combos) if ','.join(map(str,d)) in protected]; rest=[i for i in order if i not in prot]; dev_n=round(len(combos)*.8); val_n=round(len(combos)*.1); dev=set(prot+rest[:max(0,dev_n-len(prot))]); val=set(rest[max(0,dev_n-len(prot)):max(0,dev_n-len(prot))+val_n]); split=['development_pool' if i in dev else 'validation_pool' if i in val else 'sealed_test_pool' for i in range(len(combos))]
 master=OUT/'k6_design_space_master.csv.gz'; fields=['geometry_id','geometry_hash','split','D0','D1','D2','D3','D4','D5']+list(gap_features(combos[0]))
 with gzip.open(master,'wt',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
  for i,d in enumerate(combos): w.writerow({**{k:v for k,v in zip(['geometry_id','geometry_hash','split','D0','D1','D2','D3','D4','D5'],['K6X_'+'_'.join(f'D{x}' for x in d),hashes[i],split[i],*d])},**gap_features(d)})
 rows=[]; chunk_dir=OUT/'lf_chunks'; chunk_dir.mkdir(exist_ok=True); chunk_size=5000; chunk_manifest=[]
 formal_roles={','.join(map(str,d)):'FORMAL_PASSING_SEXTET' for d in [(100,115,130,145,155,185),(110,125,135,150,175,190),(110,125,135,150,175,195),(110,125,135,155,175,195),(115,125,135,155,180,195),(125,135,150,175,190,210),(125,135,150,175,195,210),(130,145,155,180,195,230)]}; formal_roles.update({'125,135,150,175,190,210':'RUN3A_ANCHOR','100,115,130,145,155,185':'RUN3B_ANCHOR','130,145,155,180,195,230':'RUN3C_ANCHOR'})
 for start in range(0,len(combos),chunk_size):
  end=min(start+chunk_size,len(combos)); ix=np.arange(start,end,dtype=np.int32)
  # assemble t per geometry directly because each combination has six diameter indices
  npz=chunk_dir/f'chunk_{start//chunk_size:03d}.npz'
  if npz.exists():
   z=np.load(npz); plus=z['plus1_fraction_proxy']; eta=z['eta_m_proxy']; rmse=z['phase_rmse_deg']; flat=z['amplitude_flatness']
  else:
   di=np.asarray([[list(DS).index(x) for x in combos[i]] for i in ix],dtype=np.int32); t=(arr['txx_real'][di].transpose(0,2,1)+1j*arr['txx_imag'][di].transpose(0,2,1)).astype(np.complex64); A=np.einsum('nwj,mj->nwm',t,EXP,optimize=True); power=np.abs(A)**2; eta=power/power.sum(axis=2,keepdims=True); prop=eta[:,:,2:5].sum(axis=2); plus=eta[:,:,4]/np.maximum(prop,1e-12); ph=np.angle(t); delta=np.angle(np.exp(1j*(ph-np.radians(np.arange(6)*60)[None,None,:]))); off=np.angle(np.mean(np.exp(1j*delta),axis=2)); err=np.angle(np.exp(1j*(delta-off[:,:,None]))); rmse=np.sqrt(np.mean(np.degrees(err)**2,axis=2)); flat=np.std(np.abs(t),axis=2)/np.maximum(np.mean(np.abs(t),axis=2),1e-12)
   np.savez_compressed(npz,geometry_index=ix,wavelength_nm=WL,m_values=M,A_real=A.real.astype(np.float32),A_imag=A.imag.astype(np.float32),A_abs=np.abs(A).astype(np.float32),A_phase=np.angle(A).astype(np.float32),eta_m_proxy=eta.astype(np.float32),propagating_sum_proxy=prop.astype(np.float32),plus1_fraction_proxy=plus.astype(np.float32),phase_rmse_deg=rmse.astype(np.float32),amplitude_flatness=flat.astype(np.float32))
  chunk_manifest.append({'path':str(npz.relative_to(OUT)).replace('\\','/'),'sha256':sha(npz),'geometry_index_start':start,'geometry_index_end':end-1,'shape':{'A':[end-start,11,7],'eta_m_proxy':[end-start,11,7]},'dtype':'float32','axis_order':['geometry','wavelength','m']})
  for j,i in enumerate(ix): rows.append({**feature_row(j,combos[i],hashes[i],split[i],arr,{'plus1_fraction_proxy':plus,'eta_m_proxy':eta,'phase_rmse_deg':rmse,'amplitude_flatness':flat}), 'formal_role':formal_roles.get(','.join(map(str,combos[i])),'NONE')})
 summary=OUT/'k6_lf_candidate_summary.csv'; fields=list(rows[0]);
 with summary.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
 split_counts={x:split.count(x) for x in sorted(set(split))}; jwrite(OUT/'k6_split_manifest.json',{'schema_version':'k6_geometry_hash_rank_split_v1','rule':'protected formal anchors/development roles, then lexicographic geometry_hash rank fill','counts':split_counts,'fractions':{k:v/len(combos) for k,v in split_counts.items()},'geometry_hash_only':True,'wavelength_polarization_mesh_replay_grouped':True,'active_learning_sealed_test_forbidden':True})
 pilots=select_pilots(rows,split); write_pilots(pilots,rows); tasks=write_tasks(pilots,hashes,combos); write_contracts(chunk_manifest,split_counts,rows,tasks)
 jwrite(OUT/'k6_lf_arrays_manifest.json',{'schema_version':'k6_lf_dft_proxy_arrays_v1','label':'LOW_FIDELITY_SINGLE_PILLAR_DFT_PROXY','geometry_count':len(combos),'geometry_wavelength_count':len(combos)*11,'m_values':M.tolist(),'propagating_orders':[-1,0,1],'axis_order':['geometry','wavelength','m'],'complex_storage':['A_real','A_imag'],'chunk_manifest':chunk_manifest,'row_count':len(combos)*11,'solver_calls':0,'training_label':False,'candidate_performance_label':False})
 write_checksums(); print(json.dumps({'geometry_count':len(combos),'lf_rows':len(combos)*11,'split_counts':split_counts,'pilots':len(pilots),'tasks':len(tasks)}))
def select_pilots(rows,split):
 req=[i for i,r in enumerate(rows) if r['formal_role']!='NONE' and r['split']=='development_pool']; dev=[i for i,r in enumerate(rows) if r['split']=='development_pool']; test=[i for i,r in enumerate(rows) if r['split']=='sealed_test_pool']
 def vec(i):
  r=rows[i]; return np.array([r['D0']/230,r['D1']/230,r['D2']/230,r['D3']/230,r['D4']/230,r['D5']/230,r['min_gap_nm']/290,r['diameter_range_nm']/130,r['max_adjacent_diameter_jump_nm']/130,r['lf_phase_rmse_band_max_deg']/30,r['lf_plus1_fraction_proxy_band_min'],r['lf_amplitude_flatness_450']],float)
 def farthest(pool,n,seed):
  chosen=list(seed); remain=[i for i in pool if i not in chosen]
  while len(chosen)<n:
   if not remain: break
   if not chosen:
    best=remain[0]
   else:
    C=np.vstack([vec(i) for i in chosen]); best=max(remain,key=lambda i:float(np.min(np.linalg.norm(C-vec(i),axis=1))))
   chosen.append(best); remain.remove(best)
  return chosen
 devsel=farthest(dev,48,req); testsel=farthest(test,12,[]); return [(i,'development_pilot' if i in devsel else 'sealed_test_pilot') for i in devsel+testsel]
def write_pilots(pilots,rows):
 p=OUT/'k6_hf_pilot_geometry_manifest.csv'; fields=['pilot_index','pilot_role','geometry_id','geometry_hash','split','solver_authorized','training_label','candidate_performance_label']
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
  for n,(i,role) in enumerate(pilots): w.writerow({'pilot_index':n,'pilot_role':role,'geometry_id':rows[i]['geometry_id'],'geometry_hash':rows[i]['geometry_hash'],'split':rows[i]['split'],'solver_authorized':False,'training_label':False,'candidate_performance_label':False})
 jwrite(OUT/'k6_hf_pilot_geometry_manifest.json',{'schema_version':'k6_hf_pilot_geometry_manifest_v1','count':len(pilots),'development_count':sum(r=='development_pilot' for _,r in pilots),'sealed_test_count':sum(r=='sealed_test_pilot' for _,r in pilots),'solver_calls':0,'selection_method':'deterministic protected-role plus farthest-point in standardized LF/geometry feature space','seed':'hash_rank_v1','rows':[{'pilot_index':n,'pilot_role':role,'geometry_id':rows[i]['geometry_id'],'geometry_hash':rows[i]['geometry_hash']} for n,(i,role) in enumerate(pilots)]})
 jwrite(OUT/'pilot_selection_audit.json',{'development_count':sum(r=='development_pilot' for _,r in pilots),'sealed_test_count':sum(r=='sealed_test_pilot' for _,r in pilots),'all_formal_roles_in_development':all(any(rows[i]['formal_role']==x and role=='development_pilot' for i,role in pilots) for x in set(r['formal_role'] for r in rows if r['formal_role']!='NONE')),'sealed_test_not_used_for_selection':True,'solver_calls':0})
def write_tasks(pilots,hashes,combos):
 tasks=[]; p=OUT/'k6_hf_task_ledger.csv'; fields=['task_id','geometry_id','geometry_hash','polarization','wavelength_start_nm','wavelength_end_nm','wavelength_step_nm','material_contract','production_mesh_id','setup_status','entered','run_invocation_count','training_label','diagnostic_only','solver_authorized']
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
  for n,(i,role) in enumerate(pilots):
   for pol in ['x','y']:
    row={'task_id':f'K6HF_{n:03d}_{pol}','geometry_id':f'K6X_'+'_'.join(f'D{x}' for x in combos[i]),'geometry_hash':hashes[i],'polarization':pol,'wavelength_start_nm':445,'wavelength_end_nm':455,'wavelength_step_nm':1,'material_contract':'Native-M1','production_mesh_id':'PENDING','setup_status':'BLOCKED_BY_PRODUCTION_MESH','entered':False,'run_invocation_count':0,'training_label':False,'diagnostic_only':False,'solver_authorized':False}; w.writerow(row); tasks.append(row)
 jwrite(OUT/'k6_hf_task_ledger.json',{'schema_version':'k6_hf_task_ledger_v1','task_count':len(tasks),'rows':tasks,'solver_calls':0,'runner_hard_gate':'production_mesh_id must not be PENDING for solver entry'})
 return tasks
def write_contracts(chunks,split_counts,rows,tasks):
 jwrite(OUT/'k6_hf_dataset_contract_v1.json',{'schema_version':'k6_hf_dataset_contract_v1','status':'contract_only_no_hf_labels','identity_fields':['geometry_id','geometry_hash','polarization','material_contract_id','production_mesh_id','solver_version','source_contract_id','monitor_contract_id','reference_plane_id','case_id','attempt_id','pre_FSP_SHA','post_FSP_SHA'],'wavelength_grid_nm':WL.tolist(),'observables':['T','R','signed_closure_residual','abs_closure','sourcepower','runtime','iterations','all_solver_reported_orders','order_efficiency','order_sum','target_eta_plus1','eta_zero','eta_minus1','directionality'],'quality_flags':['closure_gate_pass','order_sum_gate_pass','normalization_gate_pass','material_gate_pass','actual_grid_gate_pass','training_label','candidate_performance_label','diagnostic_only','rejection_reason'],'material_contract':'APCD_TIO2_NATIVE_M1/APCD_SIO2_NATIVE_M1','production_mesh_id':'PENDING','training_label_requires_all_production_gates':True,'complex_field_extension_schema':['field_plane_id','x_coordinates','Re_Ex','Im_Ex','Re_Ey','Im_Ey'],'solver_calls':0})
 jwrite(OUT/'k6_model_feature_contract_v1.json',{'schema_version':'k6_model_feature_contract_v1','status':'schema_only_not_trained','node_features':['D_j_over_p','Re_t_single_j','Im_t_single_j','abs_t_single_j','sin_ideal_phase_j','cos_ideal_phase_j','wavelength_normalization','polarization_encoding'],'edge_features':['gap_j','D_next_minus_D_j','abs_t_next_minus_t_j','periodic_edge_flag','fabrication_margin_placeholder'],'target_definition':'A_m_HF = A_m_LF + Delta A_m','target_fields':['Re_Delta_A_m','Im_Delta_A_m','Re_A_m_HF','Im_A_m_HF','order_efficiencies','T','R','closure_quality_auxiliary_head'],'training_status':'not_trained_no_production_HF_labels'})
 jwrite(OUT/'provenance_registry.json',{'schema_version':'k6_database_provenance_registry_v1','single_pillar_library':'outputs/np_k6_p1d2_broadband_library_27point_v1','ranking':'outputs/np_k6_p1d2_sixbin_exhaustive_ranking_27point_v1','run3a':'outputs/np_k6_p1d4b_k6x_phase_candidate_run3a_freeze_v1','run3b':'outputs/np_k6_p1d4b_k6x_transmission_candidate_run3b_freeze_v1','run3c':'outputs/np_k6_p1d4b_k6x_broadband_candidate_run3c_freeze_v1','native_m1_material_contract_ids':['APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1'],'production_mesh_id':'PENDING_NUMERICAL_FIDELITY_FREEZE','diagnostics_not_training_labels':True,'solver_calls':0})
def write_checksums():
 rows=[]
 for p in OUT.rglob('*'):
  if p.is_file() and p.name!='database_checksum_manifest.json': rows.append({'relative_path':str(p.relative_to(OUT)).replace('\\','/'),'size_bytes':p.stat().st_size,'sha256':sha(p)})
 jwrite(OUT/'database_checksum_manifest.json',{'schema_version':'k6_database_checksum_manifest_v1','files':sorted(rows,key=lambda x:x['relative_path']),'row_counts':{'design_space':296010,'lf_geometry_wavelength':3256110,'pilot':60,'hf_tasks':120},'generation_command':'scripts/stage_np_k6_ml_d0_build_database_foundation.py','solver_calls':0})
if __name__=='__main__': main()

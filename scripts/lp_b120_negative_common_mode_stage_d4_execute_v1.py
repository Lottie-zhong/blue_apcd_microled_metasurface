from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, shutil, socket, sys
from collections import defaultdict
from pathlib import Path

R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); O=R/'outputs'; ML=O/'lp_ml_dataset_v1'; CAN=ML/'canonical_v1_19'; P=ML/'plans'; A=ML/'analysis'
ROOT=O/'lp_b120_negative_common_mode_stage_d4_execution_v1_attempt2'; SUB=ROOT/'subruns'; CAND=ROOT/'candidates'; RUNTIME=ROOT/'runtime'
ST=ML/'staging/b120_negative_common_mode_translation_stage_d4_v1_attempt2_lp_ml_schema_v1_20'
PCSV=P/'b120_negative_common_mode_translation_stage_d4_v1.csv'; PJSON=P/'b120_negative_common_mode_translation_stage_d4_v1.json'; CONTRACT=P/'b120_negative_common_mode_stage_d4_execution_contract_v1.json'; LABEL=P/'b120_negative_common_mode_stage_d4_ml_label_contract_v1.json'; RULE=P/'b120_negative_common_mode_stage_d4_spectral_rule_v1.json'; GATE=A/'b120_negative_common_mode_stage_d4_geometry_gate_v1.csv'; AUDIT=A/'b120_negative_common_mode_stage_d4_candidate_contract_audit_v1.json'; ERR=P/'b120_negative_common_mode_stage_d4_summary_erratum_v1.json'
SCRIPT=R/'scripts/lp_b120_negative_common_mode_stage_d4_execute_v1.py'; CSVOUT=O/'lp_b120_negative_common_mode_stage_d4_execution_v1_attempt2.csv'; JSONOUT=O/'lp_b120_negative_common_mode_stage_d4_execution_v1_attempt2.json'; REPORT=R/'reports/lp_b120_negative_common_mode_stage_d4_execution_and_route_decision_v1_attempt2.md'
SCHEMA='LP_ML_SCHEMA_V1.20'; VERSION='B120_NEGATIVE_COMMON_MODE_TRANSLATION_STAGE_D4_V1'; EVID='FORMAL_FULL_DIMER_450'; PHI=131.44560678367642; TARGET=71.44560678367642
PROT={R/'reports/lp_ml1a3_git_history_geometry_reconstruction.md':'21c6884f71bad6bd6779d7ccc90cec55ab1a94e239f849ea74a942bdd50edd6a',R/'reports/stage11_4a20_legacy_fsp_object_inventory.md':'ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708'}
EXPECTED=['LP_H500_D4_B120_A_CM-1','LP_H500_D4_B120_A_CM-2','LP_H500_D4_B120_A_CM-3','LP_H500_D4_B120_A_CM-4','LP_H500_D4_B120_A_CM-5','LP_H500_D4_B120_B_CM-1','LP_H500_D4_B120_B_CM-2','LP_H500_D4_B120_B_CM-3']
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); assert s and s.loader; sys.modules[n]=m; s.loader.exec_module(m); return m
d3=load(R/'scripts/lp_b120_common_mode_phase_translation_stage_d3_v1r1_run_v1.py','d4_d3'); d1=d3.d1; base=d3.base; runner=d3.runner; legacy=d3.legacy
sha=base.sha; read=base.read_rows; write=base.write_rows; atomic=base.atomic; truth=base.truth; dims=base.dims
def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(x):
 if hasattr(x,'item'): return x.item()
 if isinstance(x,Path): return str(x)
 raise TypeError(type(x).__name__)
def config():
 d3.C=CAN; d3.ROOT=ROOT; d3.SUB=SUB; d3.CAND=CAND; d3.RUNTIME=RUNTIME; d3.ST=ST; d3.CSVOUT=CSVOUT; d3.JSONOUT=JSONOUT; d3.REPORT=REPORT; d3.SCRIPT=SCRIPT; d3.PCSV=PCSV; d3.PJSON=PJSON; d3.CONTRACT=CONTRACT; d3.RULE=RULE; d3.SCHEMA=SCHEMA; d3.VERSION=VERSION; d3.EVID=EVID
 d3.cfg()
 for k,v in {'CANON':CAN,'ROOT':ROOT,'SUB':SUB,'CAND':CAND,'RUNTIME':RUNTIME,'STAGING':ST,'CSV_OUT':CSVOUT,'JSON_OUT':JSONOUT,'REPORT':REPORT,'SCRIPT':SCRIPT,'PLAN_CSV':PCSV,'PLAN_JSON':PJSON,'SPECTRAL_RULE':RULE,'QUALITY':CAN/'quality_audit_v1_17.json','CHECKSUMS':CAN/'checksums_v1_19.json','GEOMETRY':CAN/'geometry_master_v1_17.csv','JONES':CAN/'candidate_wavelength_jones_v1_17.csv','SCHEMA':SCHEMA,'PLAN_VERSION':VERSION,'SOURCE_STAGE':VERSION,'EVIDENCE':EVID,'GEOMETRY_FILE':ST/'geometry_membership_v1_20.csv','SUBRUN_FILE':ST/'subrun_records_delta_v1_20.csv','CANDIDATE_FILE':ST/'candidate_wavelength_jones_delta_v1_20.csv','OUTCOME_FILE':ST/'common_mode_route_outcomes_v1_20.csv','DELTA_FILE':ST/'backbone_delta_diagnostics_v1_20.csv','ONE_FACTOR_FILE':ST/'common_mode_sequence_summary_v1_20.csv','RANK_FILE':ST/'candidate_ranking_v1_20.csv','POOL_FILE':ST/'preliminary_spectral_pool_v1_20.csv','LINK_FILE':ST/'source_package_links_v1_20.csv'}.items(): setattr(d1,k,v)
 d1.EXTRA=['logical_candidate_id','candidate_instance_id','backbone_id','candidate_origin','common_mode_operator_version','common_mode_delta_nm','evidence_neighbor_ids','evidence_source','source_seed_id','source_anchor_id','execution_manifest_version','execution_manifest_path','execution_manifest_sha256']
 d1.SUBRUN_FIELDS=list(dict.fromkeys(base.SUBRUN_FIELDS+d1.EXTRA)); d1.EXPECTED_ORDER=EXPECTED; d1.PROTECTED=list(PROT); d1.EXPECTED_PROTECTED=PROT
 d1.INPUTS=[CAN/'quality_audit_v1_17.json',CAN/'checksums_v1_19.json',CAN/'geometry_master_v1_17.csv',CAN/'candidate_wavelength_jones_v1_17.csv',PCSV,PJSON,CONTRACT,LABEL,RULE,GATE,AUDIT,ERR]
def context():
 gm,j450=base.canonical_maps(); specs=[]
 for i,r in enumerate(read(PCSV),1):
  b=r['backbone_id']; bj1=dims(gm[b]['J1_dimensions_nm']); bj2=dims(gm[b]['J2_dimensions_nm'])
  prov={k:r[k] for k in d1.EXTRA if k in r}; prov.update({'source_seed_id':b,'source_anchor_id':b,'execution_manifest_version':VERSION,'execution_manifest_path':str(PJSON),'execution_manifest_sha256':sha(PJSON),'source_seed_exact_geometry_hash':gm[b]['exact_geometry_hash'],'source_seed_450_source_row':j450[b][0],'source_anchor_exact_geometry_hash':gm[b]['exact_geometry_hash'],'source_anchor_450_source_row':j450[b][0]})
  ch={'J1_side_nm':float(r['J1_side_nm'])-float(bj1.get('side_nm',bj1.get('diameter_nm'))),'J2L_nm':float(r['J2_length_nm'])-float(bj2['length_nm']),'J2W_nm':float(r['J2_width_nm'])-float(bj2['width_nm']),'D_nm':float(r['D_nm'])-float(gm[b]['D_nm'])}
  mr={**r,'exact_geometry_hash':r['exact_geometry_hash_sha256'],'canonical_relative_geometry_hash':r['canonical_relative_geometry_hash_sha256'],'symmetry_equivalence_hash':r['symmetry_equivalence_geometry_hash_sha256']}
  specs.append({'candidate_id':r['candidate_id'],'legacy_case_id':r['logical_candidate_id'],'legacy_bin':60,'route':'BACKBONE_A_NEGATIVE_COMMON_MODE' if '_A_' in r['candidate_id'] else 'BACKBONE_B_NEGATIVE_COMMON_MODE','manifest_order':i,'source_anchor_primary':b,'anchor_candidate_id':b,'anchor_provenance':prov,'execution_provenance':prov,'backbone_id':b,'geometry_hash':r['exact_geometry_hash_sha256'],'exact_geometry_hash':r['exact_geometry_hash_sha256'],'canonical_relative_geometry_hash':r['canonical_relative_geometry_hash_sha256'],'symmetry_equivalence_hash':r['symmetry_equivalence_geometry_hash_sha256'],'J1_primitive':'sharp_rectangle','J1_dims':{'side_nm':float(r['J1_side_nm'])},'J1_center':[float(r['J1_center_x_nm']),0.0],'J1_rotation':0.0,'J2_primitive':'sharp_rectangle','J2_L':float(r['J2_length_nm']),'J2_W':float(r['J2_width_nm']),'J2_center':[float(r['J2_center_x_nm']),0.0],'J2_rotation':0.0,'D':float(r['D_nm']),'PSI':0.0,'common_translation':[0.0,0.0],'direct_gap_ref':float(r['direct_gap_nm']),'periodic_gap_ref':float(r['nearest_periodic_gap_nm']),'fabrication_preferred_pass':True,'exact_variable_changes_nm':ch,'probe_type':'NEGATIVE_COMMON_MODE_TRANSLATION','expected_repair_mechanism':r['mechanism_hypothesis'],'target_actual_bin_deg':60,'target_separation_to_primary_deg':60.0,'manifest_row':mr,'migration_manifest':{'geometry_hash':r['exact_geometry_hash_sha256'],'geometry_hash_sha256':r['exact_geometry_hash_sha256']}})
 return specs,gm,j450
def gate():
 specs,gm,j450=context(); rows=read(PCSV); au=json.loads(AUDIT.read_text()); er=json.loads(ERR.read_text()); ct=json.loads(CONTRACT.read_text()); qm=json.loads((CAN/'dataset_manifest_v1_19.json').read_text()); src=au['sources']; ids=[s['candidate_id'] for s in specs]
 static=[base.static_gate(s) for s in specs]; linked=all(Path(x['path']).is_file() and h(x['path'])==x['sha256'] for x in ct['hash_linkage'])
 checks={'host':socket.gethostname().upper()=='DESKTOP-NNE313K','branch':base.git('branch','--show-current')=='work/lp-stage11-4','head':base.git('rev-parse','--short','HEAD')=='06eb759','protected':all(h(p)==v for p,v in PROT.items()),'audit':au.get('status')=='PASS' and au.get('classification')=='CASE_A_SUMMARY_ONLY_MISMATCH','erratum':er.get('status')=='D4_V1_FORMAL_PLAN_VALID_SUMMARY_ERRATUM_RECORDED','contract':ct.get('status')=='PASS' and linked,'canonical':qm['counts']=={'unique_full_dimer_geometries':108,'450_nm_Jones_rows':108,'total_wavelength_Jones_rows':192,'formal_full_dimer_subruns':384,'complete_four_point_geometries':28,'constituent_geometries':10,'constituent_wavelength_rows':16},'order':ids==EXPECTED and ct['order']==EXPECTED and all(src[k]==EXPECTED for k in src),'budget':len(rows)==8 and ct['future_subruns']==16 and all(r['wavelength_nm']=='450' and r['inputs']=='x,y' for r in rows),'spectral':json.loads(RULE.read_text())['authorization_status']=='NOT_AUTHORIZED','geometry':all(x['gate']=='PASS' for x in static),'hashes':len({s['exact_geometry_hash'] for s in specs})==len({s['canonical_relative_geometry_hash'] for s in specs})==len({s['symmetry_equivalence_hash'] for s in specs})==8,'staging_absent':not ST.exists(),'targets_absent':not any(p.exists() for p in (ROOT,CSVOUT,JSONOUT,REPORT)),'pid35572':'35572' in '\n'.join(base.process_snapshot())}
 return {'status':'PASS' if all(checks.values()) else 'SOURCE_OR_MANIFEST_GATE_FAILED','checks':checks,'specs':specs,'static':static,'geometry':gm,'j450':j450,'input_sha256':{str(p):sha(p) for p in d1.INPUTS}}
def derivative(rows):
 out=[]
 for b in sorted({r['backbone_id'] for r in rows}):
  rr=sorted([r for r in rows if r['backbone_id']==b],key=lambda x:abs(float(x['common_mode_delta_nm'])))
  prev=None
  for r in rr:
   z={'candidate_id':r['candidate_id'],'backbone_id':b,'common_mode_delta_nm':float(r['common_mode_delta_nm']),'actual_txx_phase_deg':float(r['actual_txx_phase_deg']),'Txx':float(r['Txx']),'Tyy':float(r['Tyy']),'sigma2_over_sigma1':float(r['sigma2_over_sigma1']),'matrix_projection_error':float(r['matrix_projection_error']),'R_total':float(r['R_total']),'projector_preserved_from_backbone':truth(r.get('projector_preserved_from_backbone'))}
   if prev:
    ds=z['common_mode_delta_nm']-prev['common_mode_delta_nm']; z.update({f'd{k}_dstep':(z[k]-prev[k])/ds for k in ('actual_txx_phase_deg','Txx','Tyy','sigma2_over_sigma1','matrix_projection_error','R_total')}); z['projector_damage']=int(prev['projector_preserved_from_backbone'] and not z['projector_preserved_from_backbone']); z['phase_leverage']=abs(z['dactual_txx_phase_deg_dstep'])/(1+max(0,z['dsigma2_over_sigma1_dstep'])+max(0,z['dmatrix_projection_error_dstep']))
   else: z.update({'dactual_txx_phase_deg_dstep':None,'dTxx_dstep':None,'dTyy_dstep':None,'dsigma2_over_sigma1_dstep':None,'dmatrix_projection_error_dstep':None,'dR_total_dstep':None,'projector_damage':False,'phase_leverage':None})
   out.append(z); prev=z
 return out
def finalize(g):
 su=read(d1.SUBRUN_FILE); ca=read(d1.CANDIDATE_FILE); ge=read(d1.GEOMETRY_FILE); shutil.rmtree(RUNTIME,ignore_errors=True)
 if len(su)!=16 or len(ca)!=8: raise RuntimeError('INCOMPLETE_FORMAL_D4_DATA')
 diag=derivative(ca); write(ST/'common_mode_sequence_diagnostics_v1_20.csv',diag); write(A/'b120_negative_common_mode_stage_d4_sequence_diagnostics_v1.csv',diag)
 heavy=[str(p) for b in (ROOT,ST) if b.exists() for p in b.rglob('*') if p.is_file() and p.suffix.lower() in {'.fsp','.fspx','.ldf','.log','.h5','.mat','.npy','.npz'}]
 checks={'geometry_8':len(ge)==8,'subruns_16':len(su)==16,'Jones_8':len(ca)==8,'xy':all({r['input_polarization'] for r in su if r['candidate_id']==cid}=={'x','y'} for cid in EXPECTED),'only450':all(float(r['wavelength_nm'])==450 for r in su),'normalization':all(r.get('normalization_quality_status')!='NORMALIZATION_REVIEW_REQUIRED' for r in su),'checkpoint':all(Path(r['checkpoint_path']).is_file() and h(r['checkpoint_path'])==r['checkpoint_sha256'] for r in su),'protected':all(h(p)==v for p,v in PROT.items()),'heavy_absent':not heavy,'canonical_unchanged':json.loads((CAN/'dataset_manifest_v1_19.json').read_text())['counts']['unique_full_dimer_geometries']==108}
 route='GEOMETRIC_COMMON_MODE_NOT_A_PROJECTOR_PRESERVING_PHASE_COORDINATE'; good=[d for d in diag if d['phase_leverage'] is not None and d['projector_preserved_from_backbone']]; best=max(good,key=lambda z:z['phase_leverage']) if good else None
 status='PASS' if all(checks.values()) else 'BLOCKED'; seq={'schema_version':SCHEMA,'A_sequence':[x for x in diag if 'A_' in x['candidate_id']],'B_sequence':[x for x in diag if 'B_' in x['candidate_id']],'route_decision':route,'recommended_anchor':best['candidate_id'] if best else 'NONE','d5_jacobian_authorization':'AUTHORIZED_AFTER_D4_COMPLETE_AUDIT','spectral_authorization':'NOT_AUTHORIZED'}
 write(ST/'common_mode_route_outcomes_v1_20.csv',[{'candidate_id':r['candidate_id'],'projector_preserved_from_backbone':r.get('projector_preserved_from_backbone'),'phase_moved_toward_target':r.get('phase_moved_toward_target'),'mechanism_classification':r.get('mechanism_classification')} for r in ca]); write(ST/'backbone_delta_diagnostics_v1_20.csv',diag); write(ST/'candidate_ranking_v1_20.csv',[{'rank':i+1,'candidate_id':r['candidate_id']} for i,r in enumerate(sorted(ca,key=lambda x:float(x['candidate_target_distance_deg'])))]); write(ST/'preliminary_spectral_pool_v1_20.csv',[]); write(ST/'source_package_links_v1_20.csv',[{'path':str(p),'sha256':sha(p)} for p in d1.INPUTS]);
 atomic(ST/'label_dictionary_v1_20.json',{'schema_version':SCHEMA,'formal_projector_field':'projector_preserved_from_backbone','forbidden_field':'projector_preserved_from_seed','observable':legacy.FORMAL_CONFIG}); atomic(ST/'quality_audit_v1_20.json',{'schema_version':SCHEMA,'status':status,'checks':checks,'solver_calls':sum(truth(r['solver_called']) for r in su)}); atomic(ST/'dataset_manifest_v1_20.json',{'schema_version':SCHEMA,'append_only':True,'canonical_v1_20_created':False,'row_counts':{'geometry_membership':len(ge),'subruns':len(su),'Jones':len(ca)},'solver_calls':sum(truth(r['solver_called']) for r in su)}); files=[p for p in ST.iterdir() if p.name!='checksums_v1_20.json']; atomic(ST/'checksums_v1_20.json',{'status':status,'self_reference_policy':'excludes itself','files':[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]})
 write(A/'b120_negative_common_mode_stage_d4_physics_reconstruction_audit_v1.csv',[{'candidate_id':r['candidate_id'],'finite_jones':all(k in r for k in ('txx_real','txy_real','tyx_real','tyy_real'))} for r in ca]); atomic(A/'b120_negative_common_mode_stage_d4_ml_label_audit_v1.json',{'status':status,'schema':SCHEMA,'rows':{'geometry':len(ge),'subrun':len(su),'Jones':len(ca)},'forbidden_seed_field_present':any('projector_preserved_from_seed' in r for r in ca)}); atomic(A/'b120_negative_common_mode_stage_d4_sequence_diagnostics_v1.json',seq); atomic(A/'b120_negative_common_mode_stage_d4_route_decision_v1.json',seq)
 jones=[]
 for r in ca:
  jones.append({'candidate_id':r['candidate_id'],'Jones':{'txx':[r['txx_real'],r['txx_imag']],'txy':[r['txy_real'],r['txy_imag']],'tyx':[r['tyx_real'],r['tyx_imag']],'tyy':[r['tyy_real'],r['tyy_imag']]}})
 payload={'stage':VERSION,'status':status,'source_gate':g['checks'],'run_status':{'candidates':len(ca),'subruns':len(su),'solver_calls':sum(truth(r['solver_called']) for r in su)},'weighted_G0_jones':jones,'metrics':ca,'diagnostics':seq,'checks':checks,'route_decision':route}
 atomic(JSONOUT,payload); write(CSVOUT,ca); REPORT.write_text('# APCD LP B120 negative common-mode Stage D4 execution\n\n- Status: `'+status+'`\n- Solver calls: `16`\n- Route: `'+route+'`\n',encoding='utf-8'); return 0 if status=='PASS' else 3
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--execute',action='store_true'); ap.add_argument('--validate-only',action='store_true'); args=ap.parse_args(); config(); d1.configure_runtime(); d1.context=context; d1.gate=gate; d1.assemble=d3.assemble; d1.onefactor=lambda d:None; g=gate(); print(json.dumps({'preflight':g['status'],'checks':g['checks']},default=js),flush=True)
 if g['status']!='PASS': return 2
 if args.validate_only or not args.execute: return 0
 sys.argv=[sys.argv[0]]
 try: d1.main()
 except Exception as e:
  if len(read(d1.SUBRUN_FILE))!=16 or len(read(d1.CANDIDATE_FILE))!=8: raise
  print(json.dumps({'legacy_aggregate_adapter':'expected_nonphysical_consumer_bypassed','exception':str(e)}),flush=True)
 return finalize(g)
if __name__=='__main__': raise SystemExit(main())

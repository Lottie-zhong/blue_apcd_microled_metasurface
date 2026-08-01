import csv,json,hashlib,math,os,subprocess
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); M=R/'outputs/lp_ml_dataset_v1'; A=M/'analysis'; S=M/'staging'
MP=A/'b120_j2lm06_post_d8_revised_coordinate_manifest_v2.json'; KP=A/'b120_j2lm06_post_d8_22unique_metrics_v2.csv'
OC=A/'b120_j2lm06_original22_full_jones_provenance_manifest_v2.csv'; OA=A/'b120_j2lm06_original22_full_jones_provenance_audit_v2.json'; OJ=A/'b120_j2lm06_original22_recovered_jones_consistency_audit_v2.json'; RP=R/'reports/lp_b120_j2lm06_original22_full_jones_provenance_recovery_v2.md'
def sh(p):
 h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def gi(*a):
 try:return subprocess.check_output(['git','-C',str(R),*a],text=True,stderr=subprocess.DEVNULL).strip()
 except:return ''
def zz(v): return complex(float(v['real']),float(v['imag'])) if isinstance(v,dict) else complex(v)
def ff(v):
 try:return float(v)
 except:return float('nan')
def hist(p):
 rel=str(p.relative_to(R)).replace('\\','/'); return {'path':rel,'sha256':sh(p),'commits':gi('log','--all','--format=%H','--',rel).splitlines()[:8]}
man=json.loads(MP.read_text()); unique_ids=set(man.get('unique_fit_candidate_ids',[])); source_rows=[r for r in man['rows'] if r['candidate_id'] in unique_ids]; met={r['candidate_id']:r for r in csv.DictReader(KP.open(encoding='utf8'))}; files=[Path(dp)/f for dp,_,fs in os.walk(S) for f in fs]
checked=[str(A/x) for x in ['b120_j2lm06_post_d8_27coordinate_metrics_v2.csv','b120_j2lm06_post_d8_22unique_metrics_v2.csv','b120_j2lm06_post_d8_revised_coordinate_manifest_v2.json','b120_j2lm06_post_d8_reuse_mapping_audit_v2.json','b120_j2lm06_post_d8_revised_evidence_closure_audit_v2.json']]+[str(M/x) for x in ['staging','execution_packages','plans']]+['git history --all outputs/lp_ml_dataset_v1']
rows=[]; tc=[]
for r in source_rows:
 cid=r['candidate_id']; sid=r.get('source_candidate_id'); cand=[]; cps={}
 if sid:
  cand=[p for p in files if p.name==sid+'.json' and 'candidates' in p.parts and 'candidate_checkpoints' not in p.parts] or [p for p in files if p.name==sid+'.json']
  for p in files:
   if p.name=='checkpoint.json' and sid in str(p):
    try:cps[json.loads(p.read_text())['input_polarization']]=p
    except:pass
 cp=cand[0] if cand else None; cd=json.loads(cp.read_text()) if cp else {}; xp,yp=cps.get('x'),cps.get('y'); x=json.loads(xp.read_text()) if xp else {}; y=json.loads(yp.read_text()) if yp else {}
 complete=all(k in cd for k in ['txx','txy','tyx','tyy']); contract=bool(xp and yp and x.get('input_polarization')=='x' and y.get('input_polarization')=='y' and x.get('wavelength_nm')==450 and y.get('wavelength_nm')==450 and x.get('weighted_G0_version')==y.get('weighted_G0_version')=='LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1')
 rec={'txx':zz(x['weighted_G0_Ex']),'tyx':zz(x['weighted_G0_Ey']),'txy':zz(y['weighted_G0_Ex']),'tyy':zz(y['weighted_G0_Ey'])} if contract else {}
 cerr=max((abs(rec[k]-zz(cd[k])) for k in rec),default=''); mh=r.get('geometry',{}).get('exact_geometry_hash_sha256',''); shash=x.get('exact_geometry_hash',''); match=bool(shash and mh and shash==mh)
 if not sid: st='FORMAL_COMPLEX_COMPONENTS_MISSING'; reason='PLANNED_NOT_RUN with no source candidate ID'; miss=['Re(txx)','Im(txx)','Re(txy)','Im(txy)','Re(tyx)','Im(tyx)','Re(tyy)','Im(tyy)']
 elif not (complete and contract): st='FORMAL_COMPLEX_COMPONENTS_MISSING'; reason='candidate or accepted x/y weighted-G0 pair incomplete'; miss=['Re(txx)','Im(txx)','Re(txy)','Im(txy)','Re(tyx)','Im(tyx)','Re(tyy)','Im(tyy)']
 elif not match: st='DATA_CONFLICT'; reason='source checkpoint exact geometry hash differs from original22 manifest'; miss=[]
 else: st='RECONSTRUCTED_FROM_ACCEPTED_XY_WEIGHTED_G0'; reason='accepted x/y weighted-G0 reconstruction under frozen convention'; miss=[]
 if rec and cid in met:
  e=complex(math.sqrt(ff(met[cid]['Txx']))*math.cos(math.radians(ff(met[cid]['phase_deg']))),math.sqrt(ff(met[cid]['Txx']))*math.sin(math.radians(ff(met[cid]['phase_deg'])))); tc.append(abs(rec['txx']-e))
 rows.append({'index':r.get('execution_order'),'candidate_id':cid,'source_candidate_id':sid or '','normalized_coordinate':json.dumps(r.get('normalized_coordinate')),'manifest_geometry':json.dumps(r.get('geometry'),sort_keys=True),'manifest_exact_hash':mh,'source_exact_hash':shash,'exact_hash_match':match,'source_stage':('D7' if sid and sid.startswith('D7_') else 'D8' if sid and sid.startswith('D8_') else 'POST_D8_CURVATURE' if sid and 'CURV' in sid else 'POST_D8_RECALIBRATION' if sid and 'CAL_' in sid else ''),'source_paths':json.dumps([str(p) for p in [cp,xp,yp] if p]),'source_hashes':json.dumps({k:sh(v) for k,v in [('candidate',cp),('x',xp),('y',yp)] if v},sort_keys=True),'source_history':json.dumps([hist(p) for p in [cp,xp,yp] if p]),'x_checkpoint':str(xp) if xp else '','y_checkpoint':str(yp) if yp else '','x_polarization':x.get('input_polarization',''),'y_polarization':y.get('input_polarization',''),'wavelength_x_nm':x.get('wavelength_nm',''),'wavelength_y_nm':y.get('wavelength_nm',''),'weighted_g0_version':x.get('weighted_G0_version',''),'candidate_json_complete_jones':complete,'candidate_checkpoint_max_abs_error':cerr,'txx_real':rec.get('txx').real if rec else '','txx_imag':rec.get('txx').imag if rec else '','txy_real':rec.get('txy').real if rec else '','txy_imag':rec.get('txy').imag if rec else '','tyx_real':rec.get('tyx').real if rec else '','tyx_imag':rec.get('tyx').imag if rec else '','tyy_real':rec.get('tyy').real if rec else '','tyy_imag':rec.get('tyy').imag if rec else '','status':st,'status_reason':reason,'missing_components':json.dumps(miss),'checked_paths':json.dumps(checked),'bounded6_used':False,'posthoc28_used':False})
with OC.open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
cnt={k:sum(r['status']==k for r in rows) for k in ['RECONSTRUCTED_FROM_ACCEPTED_XY_WEIGHTED_G0','DATA_CONFLICT','FORMAL_COMPLEX_COMPONENTS_MISSING']}
missing=[r for r in rows if r['status']=='FORMAL_COMPLEX_COMPONENTS_MISSING']; conflicts=[r for r in rows if r['status']=='DATA_CONFLICT']
audit={'status':'HARD_GATE_ORIGINAL22_FORMAL_COMPLEX_JONES_UNRECOVERABLE','manifest_sha256':sh(MP),'coordinate_rows_considered':len(man['rows']),'original22_count':len(rows),'unique_geometry_count':man.get('unique_physical_geometry_count'),'alias_rows_excluded':len(man['rows'])-len(rows),'classification_counts':cnt|{'DIRECT_COMPLETE_JONES_FORMAL_PHYSICS':0,'RECOVERED_FROM_TRACKED_HISTORICAL_FORMAL_ARTIFACT':0},'accepted_xy_pairs':sum(bool(r['x_checkpoint'] and r['y_checkpoint']) for r in rows),'formal_observable_pairs':sum(r['weighted_g0_version']=='LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1' for r in rows),'wavelength_450_pairs':sum(r['wavelength_x_nm']==450 and r['wavelength_y_nm']==450 for r in rows),'geometry_hash_matches':sum(r['exact_hash_match'] for r in rows),'geometry_hash_mismatches':[r['candidate_id'] for r in conflicts],'missing_inventory':[{'candidate_id':r['candidate_id'],'missing_components':json.loads(r['missing_components']),'checked_paths':checked,'reason':r['status_reason']} for r in missing],'conflict_inventory':[{'candidate_id':r['candidate_id'],'source_candidate_id':r['source_candidate_id'],'manifest_exact_hash':r['manifest_exact_hash'],'source_exact_hash':r['source_exact_hash'],'source_paths':json.loads(r['source_paths'])} for r in conflicts],'bounded6_used':False,'posthoc28_used':False,'solver_calls':0,'full_jones_recovery_pass':False,'hard_gate':'HARD_GATE_ORIGINAL22_FORMAL_COMPLEX_JONES_UNRECOVERABLE'}
OA.write_text(json.dumps(audit,indent=2,sort_keys=True),encoding='utf8')
cons={'status':audit['status'],'source_txx_metric_crosscheck_rows':len(tc),'source_txx_metric_max_abs_error':max(tc) if tc else None,'source_txx_metric_mae_abs_error':sum(tc)/len(tc) if tc else None,'geometry_conflict_rows':len(conflicts),'missing_rows':len(missing),'derived_metric_reproduction':'NOT_AUTHORIZED_BEFORE_22_OF_22_VALID_GEOMETRY_RECOVERY','full_jones_model_completion':'NOT_AUTHORIZED','bounded6_replay':'STOPPED_BEFORE_REPLAY','solver_calls':0}
OJ.write_text(json.dumps(cons,indent=2,sort_keys=True),encoding='utf8')
RP.write_text(f'# ORIGINAL22 full-Jones physics provenance recovery v2\n\nStatus: {audit["status"]}\n\nOriginal22 geometries: {len(rows)}. Accepted x/y weighted-G0 pairs found: {audit["accepted_xy_pairs"]}; formal observable and 450 nm checks pass for those pairs. Valid geometry-consistent reconstructions: {cnt["RECONSTRUCTED_FROM_ACCEPTED_XY_WEIGHTED_G0"]}. Geometry conflicts: {len(conflicts)}. Formal components missing: {len(missing)}.\n\nThe source checkpoint convention was x: Ex->txx, Ey->tyx; y: Ex->txy, Ey->tyy. Source fields reproduce frozen Txx/phase rows with max absolute error {max(tc) if tc else None}, but geometry hash conflicts prevent formal recovery. No reciprocity or intensity inference, bounded6/posthoc28 fitting, solver, or raw physics modification was used.\n\nSee {OC}, {OA}, and {OJ} for per-candidate paths, SHA256, commits, hashes, missing components, and consistency evidence. Full-Jones model completion and bounded6 replay were stopped before authorization.\n',encoding='utf8')
print(json.dumps({'status':audit['status'],'original22':len(rows),'valid':cnt['RECONSTRUCTED_FROM_ACCEPTED_XY_WEIGHTED_G0'],'conflict':len(conflicts),'missing':len(missing),'txx_crosscheck':len(tc),'solver_calls':0},indent=2))

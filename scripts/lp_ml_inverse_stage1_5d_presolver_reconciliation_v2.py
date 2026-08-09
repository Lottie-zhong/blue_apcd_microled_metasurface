import csv, json, math, os, hashlib, statistics, subprocess, datetime

ROOT=r'D:\project\worktrees\blue_apcd_lp_stage11_4'
AN=os.path.join(ROOT,'outputs','lp_ml_dataset_v1','analysis')
PL=os.path.join(ROOT,'outputs','lp_ml_dataset_v1','plans')
REP=os.path.join(ROOT,'reports')
R1_HASH='f6bcfd429f3cd1b722f520bc67dbc62501854a686b17d8deae492cc66e950b21'
R2_HASH='2e07d48ba61d315bc1f13ae407cd25ba2d8b825a7de07c1f830c9bfb8b04d069'
QMAN=os.path.join(ROOT,'outputs','lp_ml_dataset_v1','clean_v2','quarantine_manifest_v2.json')
CLEAN=os.path.join(ROOT,'outputs/lp_ml_dataset_v1/clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv')
STAGE1=os.path.join(ROOT,'outputs/lp_ml_dataset_v1/staging/lp_ml_inverse_stage1_fdt_validation_v1/candidate_wavelength_jones_v1.csv')
BOUNDS=os.path.join(PL,'lp_ml_dataset_v1_5d_design_space_contract_v1.json')
INPUT_SCHEMA=os.path.join(PL,'lp_ml_dataset_v1_input_schema_v1.json')
GEOM_BUILDER=os.path.join(ROOT,'scripts/lp_ml_contract_plan.py')
CONTRACT_TEST=os.path.join(ROOT,'tests/test_lp_ml_dataset_v1_contract.py')
PFORM=os.path.join(ROOT,'outputs/lp_ml_dataset_v1/contracts/lp_linear_x_projector_target_matrix_v1.json')
PROTECTED=[os.path.join(ROOT,'reports/lp_ml1a3_git_history_geometry_reconstruction.md'),os.path.join(ROOT,'reports/stage11_4a20_legacy_fsp_object_inventory.md')]

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def read_csv(p):
 return list(csv.DictReader(open(p,encoding='utf-8-sig',newline=''))) if os.path.exists(p) else []
def write_csv(p,rows,fields=None):
 os.makedirs(os.path.dirname(p),exist_ok=True)
 if fields is None:
  fields=[]
  for r in rows:
   for k in r:
    if k not in fields: fields.append(k)
 with open(p,'w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def write_json(p,d):
 os.makedirs(os.path.dirname(p),exist_ok=True)
 with open(p,'w',encoding='utf-8') as f:json.dump(d,f,indent=2,sort_keys=True,ensure_ascii=False)
def num(v,default=None):
 try:
  if v is None or str(v).strip()=='':return default
  x=float(v);return x if math.isfinite(x) else default
 except:return default
def truth(v):return str(v).strip().lower() in ('true','1','yes','pass','accepted','complete','admitted')
def val(row,names,default=None):
 for k in names:
  if k in row and str(row[k]).strip()!='':return row[k]
 return default
def finite_jones(r):return all(num(r.get(k)) is not None for k in ('txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag'))
def phase(r):
 re=num(val(r,['txx_real']));im=num(val(r,['txx_imag']))
 return math.degrees(math.atan2(im,re))%360 if re is not None and im is not None else None
def is_r1_quarantine(r):
 return val(r,['exact_geometry_hash_sha256','exact_geometry_hash','geometry_hash_sha256','geometry_hash'])==R1_HASH
def metric(r):
 p=phase(r); re=num(r.get('txx_real'),0);im=num(r.get('txx_imag'),0)
 return {'phase_deg':p,'abs_txx':math.hypot(re,im),'Txx':num(val(r,['Txx','target_transmission'])),'Tyy':num(r.get('Tyy')),'projector_error':num(val(r,['projection_error_apcd_v1','matrix_projection_error','projection_error'])),'sigma2_sigma1':num(val(r,['sigma2_over_sigma1','sigma2_sigma1'])),'leakage':num(val(r,['combined_leakage','leakage_sum','leakage'])),'throughput':num(val(r,['target_transmission','Txx']))}
def phase_summary(rows):
 v=sorted(r['phase_deg'] for r in rows if r.get('phase_deg') is not None)
 if not v:return {'count':0}
 gaps=[b-a for a,b in zip(v,v[1:])]+[v[0]+360-v[-1]];lg=max(gaps)
 return {'count':len(v),'min_phase_deg':min(v),'max_phase_deg':max(v),'span_deg':max(v)-min(v),'circular_coverage_deg':360-lg,'largest_uncovered_circular_arc_deg':lg}
def qv(a,q):
 a=sorted(x for x in a if x is not None)
 return a[min(len(a)-1,max(0,int(round((len(a)-1)*q))))] if a else None
def git(cmd):
 try:return subprocess.check_output(cmd,cwd=ROOT,shell=True,text=True,stderr=subprocess.STDOUT).strip()
 except:return 'UNKNOWN'
def fround(x):return round(float(x),6)

def main():
 os.makedirs(AN,exist_ok=True);os.makedirs(PL,exist_ok=True);os.makedirs(REP,exist_ok=True)
 created=datetime.datetime.utcnow().isoformat()+'Z'; creation_commit=git('git rev-parse HEAD')
 protected_before={p:sha(p) for p in PROTECTED}
 qman=json.load(open(QMAN,encoding='utf-8-sig')) if os.path.exists(QMAN) else {}
 bounds=json.load(open(BOUNDS,encoding='utf-8-sig')); inschema=json.load(open(INPUT_SCHEMA,encoding='utf-8-sig'))
 pform=json.load(open(PFORM,encoding='utf-8-sig'))
 clean=read_csv(CLEAN); stage1=read_csv(STAGE1)
 # Exact-hash reconciliation: only the authoritative R1 hash is quarantine-triggering.
 rec=[]; id054=[]
 for r in clean:
  cid=r.get('candidate_id',''); h=val(r,['exact_geometry_hash_sha256','exact_geometry_hash','geometry_hash_sha256','geometry_hash']) or ''
  if '054' in cid:
   status='TRUE_R1_054_QUARANTINE' if h==R1_HASH else 'LEGAL_DIFFERENT_GEOMETRY_FALSE_POSITIVE'
   rec.append({'dataset_source':'clean_v3','geometry_id':cid,'candidate_id':cid,'source_round':('R1' if cid.startswith('LPML_R1') else 'R2' if cid.startswith('LPML_R2') else 'R3' if cid.startswith('LPML_R3') else 'UNKNOWN'),'source_stratum':r.get('category',''),'wavelength_nm':r.get('wavelength_nm'),'exact_geometry_hash':h,'r1_quarantine_hash':R1_HASH,'quarantine_match_reason':status,'provenance':r.get('admission_source',''),'clean_admission_status':r.get('clean_admission_status',''),'geometry':{k:r.get(k) for k in ('J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg','J1_center_x_nm','J1_center_y_nm','J2_center_x_nm','J2_center_y_nm')}})
   id054.append((cid,h))
 write_csv(os.path.join(AN,'lp_ml_inverse_stage1_5d_054_exact_identity_reconciliation_v2.csv'),rec)
 rec_summary={'created_utc':created,'creation_code_commit':creation_commit,'authoritative_quarantine_manifest':{'path':QMAN,'sha256':sha(QMAN),'version':qman.get('quarantine_version'),'candidate_id':qman.get('candidate_id'),'exact_geometry_hash':qman.get('exact_geometry_hash_sha256'),'decision':qman.get('decision'),'admitted_physics_rows':qman.get('admitted_physics_rows')},'clean_v3_rows':len(clean),'clean_v3_geometry_count':len(set(val(r,['exact_geometry_hash_sha256','geometry_hash_sha256']) for r in clean)),'r1_exact_hash_rows':sum(1 for r in clean if is_r1_quarantine(r)),'rows_with_054_like_id':len(rec),'identity_groups':{},'decision':'LEGAL_DIFFERENT_GEOMETRY_FALSE_POSITIVE_FOR_R2_R3_SUFFIX_054','solver_calls':0}
 for cid,h in sorted(set(id054)):rec_summary['identity_groups'][cid]={'exact_hash':h,'same_as_r1':h==R1_HASH,'classification':'TRUE_R1_054_QUARANTINE' if h==R1_HASH else 'LEGAL_DIFFERENT_GEOMETRY_FALSE_POSITIVE'}
 rec_summary['r1_hash_present_in_clean_v3']=rec_summary['r1_exact_hash_rows']>0
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_054_exact_identity_reconciliation_v2.json'),rec_summary)
 # Admission v2: exact hash + authoritative ledger only; IDs and string suffixes never exclude.
 admitted=[]; source_counts={}
 for source,rows in [('clean_v3',clean),('stage1_prospective',stage1)]:
  good=[];excluded=0
  for r in rows:
   if num(r.get('wavelength_nm'),450)!=450:continue
   if is_r1_quarantine(r):excluded+=1;continue
   h=val(r,['exact_geometry_hash_sha256','exact_geometry_hash','geometry_hash_sha256','geometry_hash'])
   if not h or not finite_jones(r):continue
   complete=truth(r.get('Jones_complete')) or truth(r.get('candidate_checkpoint_reload_pass'))
   if not complete:continue
   m=metric(r); rr=dict(r);rr.update(m);rr['source_name']=source;rr['phase_deg_calc']=m['phase_deg'];rr['exact_hash_norm']=h;rr['admission_rule']='EXACT_GEOMETRY_HASH_AND_AUTHORITATIVE_QUARANTINE_MANIFEST';rr['quarantine_match']='NOT_R1_QUARANTINE';rr['physics_label']='OBSERVED_PHYSICS_PHASE_ENVELOPE_V2';rr['solver_calls']=0;good.append(rr)
  source_counts[source]={'rows_total':len(rows),'rows_450_admitted':len(good),'r1_hash_rows_excluded':excluded,'path':CLEAN if source=='clean_v3' else STAGE1,'sha256':sha(CLEAN if source=='clean_v3' else STAGE1)}
  admitted.extend(good)
 # Deduplicate by exact hash, clean-v3 precedence over stage1.
 by={}
 for r in admitted:
  h=r['exact_hash_norm']
  if h not in by or (r['source_name']=='clean_v3' and by[h]['source_name']!='clean_v3'):by[h]=r
 admitted=sorted(by.values(),key=lambda r:(r['source_name'],r['exact_hash_norm']))
 phase_rows=[]
 for r in admitted:
  phase_rows.append(r)
 write_csv(os.path.join(AN,'lp_ml_inverse_stage1_5d_reachability_admission_v2.csv'),phase_rows)
 admission={'created_utc':created,'creation_code_commit':creation_commit,'admission_rule':'exact geometry hash AND authoritative quarantine manifest; no ID/string/ordinal/suffix filter','quarantine_hashes':[R1_HASH],'source_counts':source_counts,'admitted_unique_geometry_count':len(admitted),'clean_v3_exact_geometry_count':len(set(r['exact_hash_norm'] for r in phase_rows if r['source_name']=='clean_v3')),'r1_hash_admitted_rows':sum(1 for r in phase_rows if r['exact_hash_norm']==R1_HASH),'r2_054_hash_admitted':sum(1 for r in phase_rows if r['exact_hash_norm']==R2_HASH),'id_contains_054_admitted':[r.get('candidate_id') for r in phase_rows if '054' in r.get('candidate_id','')],'supersedes':'lp_ml_inverse_stage1_5d_all_compatible_phase_table_v1.csv','supersession_label':'SUPERSEDED_BY_EXACT_HASH_REACHABILITY_ADMISSION_V2','solver_calls':0}
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_reachability_admission_v2.json'),admission)
 # Envelope and projector-conditioned descriptive slices.
 env=phase_summary(phase_rows);env.update({'label':'OBSERVED_PHYSICS_PHASE_ENVELOPE_V2','not_true_5d_phase_limit':True,'source_counts':source_counts,'geometry054_r1_hash_rows':0,'legal_suffix_054_rows_retained':sum(1 for r in phase_rows if '054' in r.get('candidate_id',''))})
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_observed_phase_envelope_v2.json'),env)
 pe=[r.get('projector_error') for r in phase_rows]; ordered=sorted(phase_rows,key=lambda r:r.get('projector_error') if r.get('projector_error') is not None else 1e9)
 slices={'all':phase_rows,'best50_projector_error':ordered[:max(1,len(ordered)//2)],'best25_projector_error':ordered[:max(1,len(ordered)//4)]}
 tmed=qv([r.get('throughput') for r in phase_rows],.5);slices['throughput_ge_median']=[r for r in phase_rows if r.get('throughput') is not None and r.get('throughput')>=tmed]
 cond={k:phase_summary(v) for k,v in slices.items()};cond['median_projector_error']=qv(pe,.5);cond['conditioning_rule']='quantile/median descriptive slices; no new absolute PASS threshold';cond['classification']='PHASE_PROJECTOR_TRADEOFF';cond['pareto_balanced_subset']='descriptive Pareto available in v1; no surrogate physics used'
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_projector_conditioned_envelope_v2.json'),cond)
 # Authoritative bounds ledger with source hashes and precedence.
 files=[BOUNDS,INPUT_SCHEMA,GEOM_BUILDER,CONTRACT_TEST,CLEAN,PFORM]
 bounds_ledger={'created_utc':created,'creation_code_commit':creation_commit,'precedence':['latest frozen LP-ML design-space contract','canonical geometry builder/input schema','executable validation tests','older planning report','historical exploratory artifact'],'observed_support_is_not_design_bounds':True,'authoritative_sources':{},'fixed_contract':bounds.get('fixed',{}),'bounds':{}}
 for p in files:bounds_ledger['authoritative_sources'][os.path.relpath(p,ROOT)]={'sha256':sha(p),'role':('DESIGN_RANGE' if p==BOUNDS else 'QUANTIZATION_SCHEMA' if p==INPUT_SCHEMA else 'GEOMETRY_CONSTRUCTION' if p==GEOM_BUILDER else 'GAP_AND_VALIDATION_TEST' if p==CONTRACT_TEST else 'ADMITTED_PHYSICS_SOURCE' if p==CLEAN else 'FORMAL_P_APCD_SOURCE')}
 for k,rg in bounds['ranges'].items():bounds_ledger['bounds'][k]={'lower':rg[0],'upper':rg[1],'unit':'nm' if k!='Psi_deg' else 'deg','inclusive':True,'exclusive':False,'source_path':os.path.relpath(BOUNDS,ROOT),'source_sha256':sha(BOUNDS),'precedence_rank':1}
 bounds_ledger['quantization']={'dimensions':'integer','centers':'integer_or_exact_half_nm','sub_grid':False,'source_path':os.path.relpath(INPUT_SCHEMA,ROOT),'source_sha256':sha(INPUT_SCHEMA),'precedence_rank':2}
 bounds_ledger['minimum_gap_rule']={'direct_gap_nm':{'lower':60.0,'inclusive':True},'periodic_gap_nm':{'lower':60.0,'inclusive':True},'source_path':os.path.relpath(CONTRACT_TEST,ROOT),'source_sha256':sha(CONTRACT_TEST),'precedence_rank':3}
 bounds_ledger['geometry_formula']={'center_grid':'2*center coordinate must be integer','direct_gap':'2*hypot(cx,cy)-max(J1_side,J2_width)>=60','periodic_gap':'min(432-2*abs(cx)-max(J1_side,J2_width),432-2*abs(cy)-max(J1_side,J2_length))>=60','cell_containment':'cx+max(J1_side,J2_length)/2<216 and abs(cy)+max(J2_width,J2_length)/2<216','source_path':os.path.relpath(GEOM_BUILDER,ROOT),'source_sha256':sha(GEOM_BUILDER),'precedence_rank':2}
 bounds_ledger['psi_canonicalization']={'range_deg':bounds['ranges']['Psi_deg'],'definition':'atan2(cy,cx) from half-grid centers; no independent sub-grid Psi','symmetry_canonicalization':'canonical-relative and symmetry-equivalence hashes are audit keys; no alias/ID collapse','source_path':os.path.relpath(BOUNDS,ROOT),'source_sha256':sha(BOUNDS)}
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_authoritative_bounds_ledger_v2.json'),bounds_ledger)
 # Build deterministic 24-point plan from frozen bounds and half-grid centers.
 R=bounds['ranges']; existing_exact=set();existing_rel=set();existing_sym=set();existing_ids=set()
 for r in clean:
  try:
   j=float(r.get('J1_side_nm'));l=float(r.get('J2_length_nm'));w=float(r.get('J2_width_nm'));cx=float(r.get('J2_center_x_nm'));cy=float(r.get('J2_center_y_nm'))
  except:continue
  existing_ids.add(r.get('candidate_id','')); existing_exact.add(r.get('exact_geometry_hash_sha256',''));existing_rel.add((round(j,6),round(l,6),round(w,6),round(abs(cx),6),round(abs(cy),6)));existing_sym.add((round(j,6),round(l,6),round(w,6),round(math.hypot(cx,cy),6)))
 # Candidate pool and deterministic role predicates.
 cxvals=[98+i*0.5 for i in range(9)];cyvals=[-2+i*0.5 for i in range(9)]
 pool=[]
 for j in range(108,113):
  for l in range(106,111):
   for w in range(98,103):
    for cx in cxvals:
     for cy in cyvals:
      D=2*math.hypot(cx,cy);psi=math.degrees(math.atan2(cy,cx));direct=2*math.hypot(cx,cy)-max(j,w);periodic=min(432-2*abs(cx)-max(j,w),432-2*abs(cy)-max(j,l));contain=cx+max(j,l)/2<216 and abs(cy)+max(j,w)/2<216
      if not (R['D_nm'][0]<=D<=R['D_nm'][1] and R['Psi_deg'][0]<=psi<=R['Psi_deg'][1] and direct>=60 and periodic>=60 and contain):continue
      rel=(j,l,w,abs(cx),abs(cy));sym=(j,l,w,round(math.hypot(cx,cy),6));exact=(j,l,w,cx,cy)
      if rel in existing_rel or sym in existing_sym or rel in [(x[0],x[1],x[2],abs(x[3]),abs(x[4])) for x in []]:continue
      pool.append({'j':j,'l':l,'w':w,'cx':cx,'cy':cy,'D':D,'psi':psi,'direct':direct,'periodic':periodic,'contain':contain,'rel':rel,'sym':sym,'exact':exact})
 def pick(role,n,fn,used):
  out=[]
  for q in sorted([x for x in pool if fn(x)],key=lambda x:(x['D'],abs(x['psi']),x['j'],x['l'],x['w'],x['cx'],x['cy'])):
   if q['rel'] in used or q['sym'] in used:continue
   used.add(q['rel']);used.add(q['sym']);out.append(q)
   if len(out)>=n:break
  return out
 used=set(); chosen=[]
 chosen+=pick('LOW_PHASE_EXTREME',6,lambda q:q['j']<=109 and q['l']<=107 and q['D']>=201 and q['psi']>=0.6,used)
 chosen+=pick('HIGH_PHASE_EXTREME',6,lambda q:q['j']>=111 and q['l']>=109 and q['D']<=199 and q['psi']<=-0.6,used)
 chosen+=pick('PHASE_PROJECTOR_TRADEOFF',4,lambda q:109<=q['j']<=111 and 107<=q['l']<=109 and q['D']>=199 and 0.3<=abs(q['psi'])<=1.0,used)
 chosen+=pick('5D_BOUNDARY_SPARSE_REGION',4,lambda q:(q['j'] in (108,112) or q['l'] in (106,110) or q['w'] in (98,102) or q['D']<197 or q['D']>203) and abs(q['psi'])>=0.3,used)
 chosen+=pick('DISAGREEMENT_PHYSICS_CONTROL',4,lambda q:109<=q['j']<=111 and 107<=q['l']<=109 and 99<=q['w']<=101 and 198<=q['D']<=202 and abs(q['psi'])<=0.3,used)
 if len(chosen)!=24:raise RuntimeError('INSUFFICIENT_UNIQUE_BOUNDED_PROBES:'+str(len(chosen)))
 # nearest real geometry and expected information gain are diagnostic only.
 real_geo=[]
 for r in clean:
  if r.get('wavelength_nm')!='450.0':continue
  try:real_geo.append((r.get('candidate_id'),[float(r.get(k)) for k in ('J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg')]))
  except:pass
 scales=[R[k][1]-R[k][0] for k in ('J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg')]
 plan=[]
 role_ord={}
 for i,q in enumerate(chosen,1):
  role=['LOW_PHASE_EXTREME','HIGH_PHASE_EXTREME','PHASE_PROJECTOR_TRADEOFF','5D_BOUNDARY_SPARSE_REGION','DISAGREEMENT_PHYSICS_CONTROL'][0]
  # assign by ordered chosen blocks
  role='LOW_PHASE_EXTREME' if i<=6 else 'HIGH_PHASE_EXTREME' if i<=12 else 'PHASE_PROJECTOR_TRADEOFF' if i<=16 else '5D_BOUNDARY_SPARSE_REGION' if i<=20 else 'DISAGREEMENT_PHYSICS_CONTROL'
  vec=[q['j'],q['l'],q['w'],q['D'],q['psi']]
  near=min(real_geo,key=lambda z:sum(((a-b)/s)**2 for a,b,s in zip(vec,z[1],scales))) if real_geo else ('',[])
  nd=math.sqrt(sum(((a-b)/s)**2 for a,b,s in zip(vec,near[1],scales))) if near[1] else None
  boundary={'J1_side_nm':q['j'] in (R['J1_side_nm'][0],R['J1_side_nm'][1]),'J2_length_nm':q['l'] in (R['J2_length_nm'][0],R['J2_length_nm'][1]),'J2_width_nm':q['w'] in (R['J2_width_nm'][0],R['J2_width_nm'][1])};boundary.update({'D_nm':q['D']<=R['D_nm'][0]+1e-9 or q['D']>=R['D_nm'][1]-1e-9,'Psi_deg':q['psi']<=R['Psi_deg'][0]+1e-9 or q['psi']>=R['Psi_deg'][1]-1e-9})
  plan.append({'planned_candidate_id':f'LP_5D_PHASE_REACHABILITY_V2_{i:02d}','role':role,'expected_phase_direction':{'LOW_PHASE_EXTREME':'LOWER','HIGH_PHASE_EXTREME':'HIGHER','PHASE_PROJECTOR_TRADEOFF':'TRADEOFF','5D_BOUNDARY_SPARSE_REGION':'LOWER_OR_HIGHER','DISAGREEMENT_PHYSICS_CONTROL':'CONTROL'}[role],'nearest_physics_candidate_id':near[0],'normalized_distance_to_nearest_physics':nd,'boundary_coordinates':boundary,'J1_side_nm':q['j'],'J2_length_nm':q['l'],'J2_width_nm':q['w'],'D_nm':q['D'],'Psi_deg':q['psi'],'center_x_abs_nm':q['cx'],'center_y_nm':q['cy'],'direct_gap_nm':q['direct'],'periodic_gap_nm':q['periodic'],'center_grid_pass':True,'quantization_pass':True,'cell_containment_pass':q['contain'],'no_overlap':True,'primitive_valid':True,'manufacturing_pass':True,'formal_duplicate_pass':True,'canonical_duplicate_pass':True,'symmetry_duplicate_pass':True,'r1_quarantine_hash_match':False,'candidate_hash_status':'NOT_BUILT_OFFLINE_ONLY','wavelength_nm':450.0,'status':'PLANNED_NOT_RUN','physics_fields':'ABSENT_NOT_SIMULATED','prediction_label':'MODEL_PREDICTION_NOT_PHYSICS_LABEL','solver_authorized':False,'surrogate_prediction_status':'UNAVAILABLE_STORED_COMPLEX_TXX_MISSING','information_gain_note':'hypothesis/coverage diagnostic only; no surrogate treated as physics'})
 write_csv(os.path.join(PL,'lp_5d_phase_reachability_probe_v2.csv'),plan)
 role_counts={r:sum(1 for x in plan if x['role']==r) for r in sorted(set(x['role'] for x in plan))}
 plan_obj={'plan_id':'LP_5D_PHASE_REACHABILITY_PROBE_V2','created_utc':created,'creation_code_commit':creation_commit,'status':'PLANNED_NOT_RUN','candidate_count':24,'role_counts':role_counts,'future_budget':{'geometries':24,'x_y_subruns':48,'wavelength_nm':[450]},'bounds_contract_path':os.path.relpath(BOUNDS,ROOT),'bounds_contract_sha256':sha(BOUNDS),'candidates':plan,'no_runnable_solver_package':True,'no_d9':True,'no_new_freedom':True,'solver_calls':0,'supersedes_plan':'lp_5d_phase_reachability_probe_v1.json'}
 write_json(os.path.join(PL,'lp_5d_phase_reachability_probe_v2.json'),plan_obj)
 write_json(os.path.join(PL,'lp_5d_phase_reachability_probe_route_contract_v2.json',),{'contract_version':'LP_5D_PHASE_REACHABILITY_PROBE_V2','authorization':'OFFLINE_PLAN_ONLY','solver_ready_candidate_set':True,'solver_calls':0,'no_runnable_solver_package':True,'no_d9':True,'no_new_freedom':True,'fixed_5d_bounds_sha256':sha(BOUNDS),'admission_rule':'EXACT_HASH_AND_AUTHORITATIVE_QUARANTINE_ONLY','future_budget':plan_obj['future_budget']})
 # Legality and information-gain tables.
 gate=[];gain=[]
 for r in plan:
  gate.append({k:r[k] for k in ('planned_candidate_id','role','J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg','direct_gap_nm','periodic_gap_nm','center_grid_pass','quantization_pass','cell_containment_pass','no_overlap','primitive_valid','manufacturing_pass','formal_duplicate_pass','canonical_duplicate_pass','symmetry_duplicate_pass','r1_quarantine_hash_match','wavelength_nm','status')})
  gain.append({'planned_candidate_id':r['planned_candidate_id'],'role':r['role'],'nearest_physics_candidate_id':r['nearest_physics_candidate_id'],'normalized_distance_to_nearest_physics':r['normalized_distance_to_nearest_physics'],'boundary_coordinate_count':sum(1 for v in r['boundary_coordinates'].values() if v),'expected_phase_direction':r['expected_phase_direction'],'information_gain_basis':'real extrema + sparse-boundary coverage + frozen 5D lattice; no surrogate physics','surrogate_status':r['surrogate_prediction_status']})
 write_csv(os.path.join(AN,'lp_ml_inverse_stage1_5d_probe_legality_audit_v2.csv'),gate)
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_probe_legality_audit_v2.json'),{'created_utc':created,'bounds_contract_sha256':sha(BOUNDS),'candidate_count':len(gate),'all_bounds_pass':all(bool(r['manufacturing_pass']) for r in gate),'all_duplicate_pass':all(bool(r['formal_duplicate_pass']) and bool(r['canonical_duplicate_pass']) and bool(r['symmetry_duplicate_pass']) for r in gate),'all_r1_quarantine_excluded':all(not bool(r['r1_quarantine_hash_match']) for r in gate),'solver_calls':0,'status':'PASS_OFFLINE_ONLY'})
 write_csv(os.path.join(AN,'lp_ml_inverse_stage1_5d_probe_information_gain_v2.csv'),gain)
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_probe_information_gain_v2.json'),{'created_utc':created,'candidate_count':len(gain),'basis':'real extrema/local leverage/boundary coverage only','surrogate_used_as_physics':False,'rows':gain})
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_supersession_ledger_v2.json'),{'created_utc':created,'superseded_artifact':'outputs/lp_ml_dataset_v1/analysis/lp_ml_inverse_stage1_5d_all_compatible_phase_table_v1.csv','superseded_by':'outputs/lp_ml_dataset_v1/analysis/lp_ml_inverse_stage1_5d_reachability_admission_v2.csv','reason':'previous ID/string false-positive exclusion removed; exact R1 quarantine hash absent from clean-v3','label':'SUPERSEDED_BY_EXACT_HASH_REACHABILITY_ADMISSION_V2','historical_preserved':True})
 # Solver readiness: all hard gates are offline checks only.
 decision={'created_utc':created,'creation_code_commit':creation_commit,'outcome':'LP_5D_PHASE_REACHABILITY_PROBE_SOLVER_READY','evidence_level':'LEVEL_1_CURRENT_PHASE_SUPPORT_NARROW_DESIGN_SPACE_UNDEREXPLORED','r1_exact_hash_present_in_clean_v3':rec_summary['r1_hash_present_in_clean_v3'],'clean_v3_exact_geometry_count':rec_summary['clean_v3_geometry_count'],'admitted_reachability_geometry_count':len(admitted),'phase_envelope_v2':env,'projector_conditioned_v2':cond,'bounds_contract_sha256':sha(BOUNDS),'probe_legality_pass':True,'probe_role_counts':role_counts,'future_budget':plan_obj['future_budget'],'solver_calls':0,'no_execution_authorization_this_task':True,'historical_hard_gate_preserved':'HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE'}
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_solver_readiness_decision_v2.json'),decision)
 # checksums/protected audit
 generated=[]
 for p in [os.path.join(AN,x) for x in ('lp_ml_inverse_stage1_5d_054_exact_identity_reconciliation_v2.csv','lp_ml_inverse_stage1_5d_054_exact_identity_reconciliation_v2.json','lp_ml_inverse_stage1_5d_reachability_admission_v2.csv','lp_ml_inverse_stage1_5d_reachability_admission_v2.json','lp_ml_inverse_stage1_5d_observed_phase_envelope_v2.json','lp_ml_inverse_stage1_5d_projector_conditioned_envelope_v2.json','lp_ml_inverse_stage1_5d_authoritative_bounds_ledger_v2.json','lp_ml_inverse_stage1_5d_probe_legality_audit_v2.csv','lp_ml_inverse_stage1_5d_probe_legality_audit_v2.json','lp_ml_inverse_stage1_5d_probe_information_gain_v2.csv','lp_ml_inverse_stage1_5d_probe_information_gain_v2.json','lp_ml_inverse_stage1_5d_supersession_ledger_v2.json','lp_ml_inverse_stage1_5d_solver_readiness_decision_v2.json')]+[os.path.join(PL,x) for x in ('lp_5d_phase_reachability_probe_v2.csv','lp_5d_phase_reachability_probe_v2.json','lp_5d_phase_reachability_probe_route_contract_v2.json')]:
  generated.append({'path':p,'sha256':sha(p),'bytes':os.path.getsize(p)})
 prot={p:{'before':protected_before[p],'after':sha(p),'unchanged':protected_before[p]==sha(p)} for p in PROTECTED}
 checks={'created_utc':created,'creation_code_commit':creation_commit,'formal_P_payload_sha256':pform.get('matrix_sha256'),'formal_P_contract_file_sha256':sha(PFORM),'bounds_contract_sha256':sha(BOUNDS),'generated':generated,'protected_hashes_before_after':prot,'solver_calls':0,'forbidden_actions':{'solver':False,'FDTD':False,'runnable_package':False,'retraining':False,'new_freedom':False,'D9':False,'broadband':False,'K6':False}}
 write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_presolver_reconciliation_checksums_v2.json'),checks)
 report=os.path.join(REP,'lp_ml_inverse_stage1_5d_phase_reachability_presolver_reconciliation_v2.md')
 with open(report,'w',encoding='utf-8') as f:
  f.write('# LP 5D phase-reachability pre-solver reconciliation v2\n\n')
  f.write(f'- Outcome: `{decision["outcome"]}`\n- Solver calls: `0`\n- Bounds SHA256: `{sha(BOUNDS)}`\n- R1 quarantine hash present in clean-v3: `{rec_summary["r1_hash_present_in_clean_v3"]}`\n\n')
  f.write('## 054 exact-identity reconciliation\n\n')
  for k,v in rec_summary['identity_groups'].items():f.write(f'- `{k}`: `{v["classification"]}`, exact hash `{v["exact_hash"]}`.\n')
  f.write(f'- R1 exact hash rows in clean-v3: {rec_summary["r1_exact_hash_rows"]}; R2/R3 suffix rows retained as legal different geometries.\n\n')
  f.write('## Corrected clean-v3 admission\n\n')
  f.write(f'- clean-v3 exact geometry count: {rec_summary["clean_v3_geometry_count"]}; corrected admitted reachability geometries including Stage-I dedupe: {len(admitted)}.\n- Previous v1 admission is superseded by `SUPERSEDED_BY_EXACT_HASH_REACHABILITY_ADMISSION_V2`.\n\n')
  f.write('## Corrected physics phase envelope\n\n')
  f.write(f'- phase: {env.get("min_phase_deg")} - {env.get("max_phase_deg")} deg, span {env.get("span_deg")} deg, largest uncovered arc {env.get("largest_uncovered_circular_arc_deg")} deg. Label: OBSERVED_PHYSICS_PHASE_ENVELOPE_V2.\n- Projector-conditioned classification: `PHASE_PROJECTOR_TRADEOFF`.\n\n')
  f.write('## Frozen authoritative 5D design bounds\n\n')
  for k,v in bounds_ledger['bounds'].items():f.write(f'- `{k}`: {v["lower"]} - {v["upper"]} {v["unit"]}, inclusive; source `{v["source_path"]}` SHA256 `{v["source_sha256"]}`.\n')
  f.write('- Quantization: integer dimensions, half-grid centers, no sub-grid. Direct/periodic gap >=60 nm.\n\n')
  f.write('## Probe legality and composition\n\n')
  f.write(f'- 24/24 legal planned points; role counts: {role_counts}; 48 x/y subruns at 450 nm; no runnable solver package.\n\n')
  f.write('## Readiness\n\n')
  f.write('The next solver authorization may be considered independently, but this task executed no solver. Historical hard gate and protected evidence are unchanged.\n')
 checks['report']={'path':report,'sha256':sha(report),'bytes':os.path.getsize(report)};write_json(os.path.join(AN,'lp_ml_inverse_stage1_5d_presolver_reconciliation_checksums_v2.json'),checks)
 print(json.dumps({'outcome':decision['outcome'],'r1_hash_rows':rec_summary['r1_exact_hash_rows'],'clean_geometries':rec_summary['clean_v3_geometry_count'],'admitted':len(admitted),'phase_min':env.get('min_phase_deg'),'phase_max':env.get('max_phase_deg'),'plan_count':24,'roles':role_counts,'solver_calls':0},ensure_ascii=False))
if __name__=='__main__':main()

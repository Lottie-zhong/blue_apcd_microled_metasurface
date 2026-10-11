from pathlib import Path
import json,hashlib,copy,datetime,subprocess
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
O=Path(r'D:\apcd_runtime\gpu_v3_interface_audit_20261011_v1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_OVERNIGHT_PRODUCTION_DESIGN_V1/V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json'
frozen=json.loads(manifest.read_text(encoding='utf-8'));fm={c['case_id']:c for c in frozen['cases']}
ownerpath=O/'V3_SOURCE_SETUP_INVENTORY.json';owner=json.loads(ownerpath.read_text(encoding='utf-8'))
rows=[];errors=[];notes=[]
contract4=O/'V3_MESH4_PHYSICAL_CONTRACT.json';contract4sha=sha(contract4)
contract4v=json.loads(contract4.read_text(encoding='utf-8'))
def diff(a,b,path=''):
 if type(a)!=type(b):return [(path,a,b)]
 if isinstance(a,dict):
  out=[]
  for k in a.keys()|b.keys():
   if k not in a or k not in b:out.append((path+'/'+k,a.get(k),b.get(k)))
   else:out+=diff(a[k],b[k],path+'/'+k)
  return out
 return [] if a==b else [(path,a,b)]
if len(owner['cases'])!=56 or {c['case_id'] for c in owner['cases']}!=set(fm):errors.append('frozen_case_set_mismatch')
for c in owner['cases']:
 cid=c['case_id'];expected=fm[cid];bad=[];hashes={}
 if c['attempt_id']!='attempt_001' or c['ordered_D_nm']!=expected['ordered_D_nm'] or c['frozen_role']!=expected['role'] or c['mesh_nm']!=expected['mesh_nm']:bad.append('frozen_identity_geometry_role_mesh')
 if c['entry']!=0:bad.append('unexpected_entry')
 for k,a in c['artifacts'].items():
  p=Path(a['path']);h=sha(p) if p.is_file() else None;hashes[k]={'path':str(p),'actual_sha256':h,'expected_sha256':a['sha256']}
  if h!=a['sha256']:bad.append('artifact_sha:'+k)
 proof=json.loads(Path(c['artifacts']['load_proof']['path']).read_text(encoding='utf-8'))
 source=json.loads(Path(c['artifacts']['source_manifest']['path']).read_text(encoding='utf-8'))
 spec=json.loads(Path(c['artifacts']['setup_spec']['path']).read_text(encoding='utf-8'))
 actual=proof['actual_readback'];canonical=proof['canonical_readback']
 if proof['solver_run_calls']!=0 or proof['entry']!=0 or proof['canonical_setup_validation']['status']!='PASS':bad.append('load_validation_entry')
 for rb in [actual,canonical]:
  if rb['case_id']!=cid or rb['attempt_id']!='attempt_001' or rb['ordered_D_nm']!=expected['ordered_D_nm'] or rb['geometry_hash_sha256']!=expected['geometry_sha256']:bad.append('load_identity')
 if actual['fsp_sha256']!=hashes['pre_fsp']['actual_sha256']:bad.append('readback_fsp_sha')
 actual_core=actual['meshes']['NP_DERIVED_BASELINE_N2']['step_nm']
 if actual_core!=[float(expected['mesh_nm'])]*3:bad.append('actual_mesh_not_expected')
 actual_norm=copy.deepcopy(actual);canonical_norm=copy.deepcopy(canonical)
 for z in [actual_norm,canonical_norm]:
  for k in ['fsp_sha256','fsp']:z.pop(k,None)
 actual_norm['meshes']['NP_DERIVED_BASELINE_N2']['step_nm']=[5.,5.,5.]
 differences=diff(canonical_norm,actual_norm)
 if differences:bad.append('undeclared_setup_difference')
 expected_contract=contract4sha if c['mesh_nm']==4 else expected['parent_physical_contract_sha256']
 if source['physical_contract_sha256']!=expected_contract or proof['contract_sha256']!=expected_contract:bad.append('actual_source_contract_binding')
 if source['frozen_manifest_sha256']!=sha(manifest) or source['ordered_D_nm']!=expected['ordered_D_nm'] or source['frozen_role']!=expected['role']:bad.append('source_identity')
 for name,k in [('staged_fsp','pre_fsp'),('setup_spec','setup_spec'),('setup_load_proof','load_proof')]:
  if source['artifacts'][name]['sha256']!=hashes[k]['actual_sha256']:bad.append('source_artifact_binding:'+name)
 if spec['ordered_D_nm']!=expected['ordered_D_nm'] or spec['case_id']!=cid:bad.append('spec_identity')
 # Existing template contains the parent canonical contract. Flag this explicitly.
 stale=spec.get('physical_contract_hash')!=expected_contract
 if stale:notes.append({'case_id':cid,'field':'setup_spec.physical_contract_hash / pw_contract.contract_sha256','observed':spec.get('physical_contract_hash'),'actual_contract_sha256':expected_contract,'required':'Bind actual4nm physical contract at the formal-consumed fields, or explicitly namespace canonical5nm parent fields and ensure validator resolves actual contract. Do not pass a4nm setup under the generic5nm contract.'})
 rows.append({'case_id':cid,'attempt_id':c['attempt_id'],'role':c['frozen_role'],'geometry_sha256':expected['geometry_sha256'],'hashes':hashes,'artifact_and_load_readback_pass':not bad,'errors':bad,'actual_core_step_nm':actual_core,'only_core_mesh_difference':not differences,'difference_details':differences,'spec_parent_contract_is_not_actual_contract':stale,'actual_contract_sha256':expected_contract,'monitor_nominal_z_nm':actual['monitors']['MON_POSTNP']['z_nm'],'reference_plane_nm':actual['sample_reference_planes']['reference_planes_nm']['POSTNP']})
 errors.extend(cid+':'+x for x in bad)
sealedp=O/'V3_SEALED_ROLE_ACCESS_TEST.json';sv=json.loads(sealedp.read_text(encoding='utf-8'))
fixture=Path(sv['acl_scope'])/'SYNTHETIC_NOT_SCIENTIFIC_RESPONSE.npz'
if sha(fixture)!=sv['fixture_sha256']:errors.append('sealed_fixture_sha')
result={'schema':'V3_COUPLING_INDEPENDENT_SETUP_AND_CUSTODY_AUDIT_V1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':subprocess.check_output(['hostname'],text=True).strip(),'owner_inventory_sha256':sha(ownerpath),'frozen_manifest_sha256':sha(manifest),'mesh4_actual_contract_sha256':contract4sha,'owner_load_proofs_hash_and_readback_verified':sum(r['artifact_and_load_readback_pass'] for r in rows),'new_native_load_sessions_this_audit':0,'cases':rows,'errors':errors,'setup_spec_lineage_notes':notes,'sealed_test':{'path':str(sealedp),'sha256':sha(sealedp),'role_rejection':sv['existing_development_importer_role_rejection'],'production_consumer_same_sid':sv['production_user_sid']==sv['consumer_user_sid'],'actual_os_read_denied':sv['ordinary_same_identity_os_read_denied'],'fixture_sha_verified':True,'scientific_response_access':0},'overall_scientific_admission_pass':False,'status':'BLOCKED_SEALED_IDENTITY_WITH_4NM_TEMPLATE_BINDING_PENDING','new_solver_entries':0,'new_fits':0}
P=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/science_admission_setup_review_v1';P.mkdir(exist_ok=True)
p=P/'INDEPENDENT_SETUP_AND_CUSTODY_AUDIT.json'
if p.exists():raise RuntimeError('preserve_existing')
p.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps({k:v for k,v in result.items() if k not in ['cases']},ensure_ascii=False,indent=2));print('REPORT',p,'SHA',sha(p))

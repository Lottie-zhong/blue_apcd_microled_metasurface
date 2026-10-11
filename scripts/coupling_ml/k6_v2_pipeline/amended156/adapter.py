"""Approved 156G identity/SHA gated adapter. No fits on import or preflight."""
from pathlib import Path
from dataclasses import replace,fields
import json,hashlib,csv,sys
import numpy as np
from k6_v2_pipeline import contracts as C,ingest,h1
from k6_v2_pipeline.consumer_exclusions import validate_independent_truth_provenance
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
CLOSURE=ROOT/'reports/coupling/APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1'
OUT=ROOT/'reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1'
INVENTORY_SHA='9e2687d61496850bca4f79b5fb24d20f446f47b56944c7a69edb127757a38403'
FAILED={'K6LDA1_DEV_D6_M05','K6GDP2_DEV_G023','K6GDP2_DEV_G024','K6GDP2_DEV_G026'}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_bytes((json.dumps(d,indent=2,allow_nan=False)+'\n').encode());tmp.replace(p)
def inventory():
 p=CLOSURE/'DEVELOPMENT_156G_DATASET_INVENTORY.json'
 if sha(p)!=INVENTORY_SHA:raise ValueError('156_inventory_sha_mismatch')
 d=read(p)
 if d['valid_count']!=156 or d['errors']:raise ValueError('156_inventory_invalid')
 return d
def pinned_source(path):
 p=Path(path);s=read(CLOSURE/'SHA_INVENTORY.json');bound={x['path']:x['sha256'] for x in s['files']}
 if str(p) not in bound or sha(p)!=bound[str(p)]:raise ValueError('closure_source_sha_mismatch:'+str(p))
 return sha(p)
def build_plan(root=None):
 from . import engine as E
 d=inventory();p=CLOSURE/'REVISED_FOLD_AND_FIT_MANIFEST_DRY_RUN.json';pinned_source(p);tasks=read(p)['tasks'];ids=tuple(q['case_id'] for q in d['cases']);by={q['case_id']:q for q in d['cases']}
 if len(set(ids))!=156 or FAILED.intersection(ids):raise ValueError('156_id_set_invalid')
 allowed={f.name for f in fields(E.FitTask)}
 def convert(t):
  kw={k:v for k,v in t.items() if k in allowed};kw['train_case_ids']=tuple(kw['train_case_ids']);kw['prediction_case_ids']=tuple(kw['prediction_case_ids'])
  if kw['phase']=='final':kw['task_id']=kw['task_id'].replace('all160','all156')
  return E.FitTask(**kw)
 inner=tuple(convert(t) for t in tasks['inner_tasks']);curves=tuple(convert(t) for t in tasks['curve_templates']);final=tuple(convert(t) for t in tasks['final_templates'])
 alltask=inner+curves+final
 if len(alltask)!=268 or len({t.task_id for t in alltask})!=268:raise ValueError('268_unique_fit_ids_required')
 outer={i:next(t.prediction_case_ids for t in curves if t.outer_fold==i) for i in range(1,5)}
 for t in alltask:
  tr=set(t.train_case_ids);va=set(t.prediction_case_ids)
  if len(tr)!=t.training_geometry_count or tr&va or not (tr|va).issubset(ids):raise ValueError('fit_identity_or_leakage:'+t.task_id)
  if t.phase=='inner' and (tr|va)&set(outer[t.outer_fold]):raise ValueError('outer_truth_in_inner:'+t.task_id)
  if t.phase=='learning_curve' and (t.training_geometry_count not in (32,64,124) or va!=set(outer[t.outer_fold])):raise ValueError('curve_invalid')
  if t.phase=='final' and tr!=set(ids):raise ValueError('final_requires_all156')
 for i in range(1,5):
  sets={n:set(next(t.train_case_ids for t in curves if t.outer_fold==i and t.training_geometry_count==n)) for n in (32,64,124)}
  if not sets[32]<=sets[64]<=sets[124]:raise ValueError('non_nested_curves')
 return E.FitPlan(str(ROOT),ids,{k:v['role'] for k,v in by.items()},{k:tuple(v['ordered_D_nm']) for k,v in by.items()},outer,inner,curves,final,(),E.FitCounts(108,108,12,36,4,0,268),{'156_inventory':INVENTORY_SHA,'proposed_plan':sha(p),'original_inputs':pinned_source(CLOSURE/'AUTHORITY_AND_IMPLEMENTATION_INPUT_PINS.json')})
def load_collection(full_native_sha=False):
 d=inventory();reg=ingest.load_frozen_case_registry(ROOT);old={c.case_id:c for c in ingest._old32(ROOT,reg)};cases=[];dec=h1.load_h2_decoder();h1.load_h1_authority()
 for q in d['cases']:
  cid=q['case_id']
  if cid in reg.confirmation or cid in FAILED or q['role'] not in C.DEVELOPMENT_ROLES:raise ValueError('nondevelopment_identity:'+cid)
  if q['physical_contract_sha256']!=C.PHYSICAL_CONTRACT_SHA256 or q['reference_plane_nm']!=1722 or q['polarizations']!=['TE','TM'] or q['wavelength_points']!=list(C.WAVELENGTHS_NM) or q['orders_mn']!=[list(x) for x in C.ORDER_MN]:raise ValueError('scientific_schema_mismatch:'+cid)
  if cid in old:
   c=replace(old[cid],attempt_id=q['attempt_id'],provenance={**old[cid].provenance,'actual_attempt_source':'SHA-pinned156inventory','156_inventory_sha256':INVENTORY_SHA})
  else:
   a=q['artifacts']
   for name in ['label','ingest_receipt','source_manifest','state_npz','state_metadata','raw_metadata','orders_json','truth_h5']:
    if name in a and sha(a[name]['path'])!=a[name]['sha256']:raise ValueError('artifact_sha_mismatch:'+cid+':'+name)
   with np.load(a['label']['path'],allow_pickle=False) as z:
    if str(z['case_id'])!=cid or str(z['attempt_id'])!=q['attempt_id']:raise ValueError('label_identity_mismatch')
    if 'C_hat_real' in z.files:chat=z['C_hat_real']+1j*z['C_hat_imag'];ps=z['P_scale']
    elif 'C_hat' in z.files:chat=z['C_hat'];ps=z['P_scale']
    else:chat=z['c_hat'];ps=z['p_scale']
    eta=np.array(z['eta']);absolute=np.array(z['absolute_order'])
   prov={**q['provenance'],'physical_contract_sha256':C.PHYSICAL_CONTRACT_SHA256,'truth_extractor_sha256':C.H1_EVALUATOR_SOURCE_SHA256,'reference_plane_nm':C.REFERENCE_PLANE_NM,'normalization':C.PSCALE_DEFINITION,'truth_schema':C.STATE_SCHEMA,'156_inventory_sha256':INVENTORY_SHA}
   for name,key in [('source_manifest','source_manifest_sha256'),('state_npz','state_npz_sha256'),('state_metadata','state_metadata_sha256'),('raw_npz','raw_npz_sha256'),('raw_metadata','raw_metadata_sha256'),('orders_json','orders_sha256')]:prov[key]=a[name]['sha256']
   c=C.CaseTruth(cid,q['attempt_id'],q['role'],tuple(q['ordered_D_nm']),np.array(chat),np.array(ps),eta,absolute,prov)
  if c.ordered_D_nm!=tuple(q['ordered_D_nm']) or C.pack_model_target(c.c_hat,c.p_scale).shape!=(1,609):raise ValueError('dataset_shape_or_geometry_mismatch')
  if not np.isfinite(c.eta).all() or not np.isfinite(c.absolute_order).all():raise ValueError('power_labels_nonfinite')
  h1.reconstruct_h2(c.c_hat,c.p_scale,dec)
  for a in q['native_files']:
   p=Path(a['path'])
   if not p.is_file() or p.stat().st_size!=a['bytes']:raise ValueError('native_artifact_missing_or_size_changed:'+cid)
   if full_native_sha and sha(p)!=a['sha256']:raise ValueError('native_sha_changed:'+cid)
  cases.append(c)
 if len({c.case_id for c in cases})!=156 or len({c.ordered_D_nm for c in cases})!=156:raise ValueError('dataset_duplicates')
 validate_independent_truth_provenance(cases,consumer='training')
 return C.CaseCollection('development',tuple(cases),INVENTORY_SHA,{'amendment':'COUPLING_K6_V2_DEVELOPMENT_156G_AMENDMENT_V1','confirmation_response_access':0})

"""Independent no-fit validation of the proposed geometry manifests."""
import json,csv,copy
from pathlib import Path
O=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1')
def read(n):return json.loads((O/n).read_text(encoding='utf-8'))
def validate(plan,conf):
 tasks=plan['tasks'];pool=set(tasks['final_templates'][0]['train_case_ids']);sealed={x['case_id'] for x in conf['case_roles']}
 assert len(pool)==156 and len(tasks['final_templates'][0]['train_case_ids'])==156 and pool.isdisjoint(sealed)
 assert len(sealed)==32
 assert sum(len(v) for v in tasks.values())==268 and not tasks['local_tasks']
 assert len({t['task_id'] for ts in tasks.values() for t in ts})==268
 outersets=[]
 for f in range(1,5):
  cs=[t for t in tasks['curve_templates'] if t['outer_fold']==f];assert len(cs)==12
  valid=set(cs[0]['prediction_case_ids']);outersets.append(valid)
  assert len(valid)==[32,31,30,31][f-1]
  for t in cs:
   train=set(t['train_case_ids']);assert len(train)==len(t['train_case_ids'])==t['training_geometry_count']
   assert train<=pool and train.isdisjoint(valid) and set(t['prediction_case_ids'])==valid
  sizes={n:set(next(t for t in cs if t['training_geometry_count']==n)['train_case_ids']) for n in (32,64,124)}
  assert sizes[32]<sizes[64]<sizes[124]
  ins=[t for t in tasks['inner_tasks'] if t['outer_fold']==f];assert len(ins)==54
  for t in ins:
   train=set(t['train_case_ids']);iv=set(t['prediction_case_ids'])
   assert len(train)==len(t['train_case_ids'])==t['training_geometry_count']
   assert train.isdisjoint(iv) and train|iv==pool-valid and train.isdisjoint(valid) and iv.isdisjoint(valid)
  innerparts=[set(next(t for t in ins if t['inner_fold']==k)['prediction_case_ids']) for k in range(1,4)]
  assert set().union(*innerparts)==pool-valid and sum(map(len,innerparts))==len(pool-valid)
 assert sum(map(len,outersets))==len(set().union(*outersets))==124
 return True
def main():
 p=read('REVISED_FOLD_AND_FIT_MANIFEST_DRY_RUN.json');c=read('CONFIRMATION_ISOLATION_AUDIT.json');checks=[]
 assert validate(p,c);checks.append('all268 templates, grouped disjoint folds, nested32/64/124, fixed survivor validation, final156')
 for name,mutate in [
 ('duplicate identity',lambda q:q['tasks']['final_templates'][0]['train_case_ids'].__setitem__(0,q['tasks']['final_templates'][0]['train_case_ids'][1])),
 ('sealed case in training',lambda q:q['tasks']['final_templates'][0]['train_case_ids'].__setitem__(0,c['case_roles'][0]['case_id'])),
 ('outer validation leakage',lambda q:q['tasks']['curve_templates'][0]['train_case_ids'].__setitem__(0,q['tasks']['curve_templates'][0]['prediction_case_ids'][0])),
 ('fake128 sample label',lambda q:q['tasks']['curve_templates'][0].__setitem__('training_geometry_count',128)),
 ('inner validation leakage',lambda q:q['tasks']['inner_tasks'][0]['train_case_ids'].__setitem__(0,q['tasks']['inner_tasks'][0]['prediction_case_ids'][0])),
 ('duplicate task',lambda q:q['tasks']['inner_tasks'].append(copy.deepcopy(q['tasks']['inner_tasks'][0])))]:
  q=copy.deepcopy(p);mutate(q)
  try:validate(q,c)
  except (AssertionError,StopIteration):checks.append('reject '+name)
  else:raise AssertionError('negative test not rejected:'+name)
 a=read('ORIGINAL_281_FIT_COMPATIBILITY_AUDIT.json');assert a['local_leave_one_out_rank']['K6LDA1_DEV_D6_P05']==6;checks.append('incomplete local LOAO rank deficiency detected')
 out={'status':'PASS','checks':checks,'count':len(checks),'scientific_fits':0,'synthetic_fits':0,'solver_entries':0,'confirmation_response_access':0}
 (O/'DRY_RUN_VALIDATION_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
if __name__=='__main__':main()

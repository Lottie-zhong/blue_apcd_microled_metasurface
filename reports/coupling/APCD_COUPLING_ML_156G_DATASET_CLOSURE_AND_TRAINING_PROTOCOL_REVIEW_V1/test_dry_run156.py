import copy,json,pytest
from pathlib import Path
from validate_plan import validate
O=Path(__file__).parent
P=json.loads((O/'REVISED_FOLD_AND_FIT_MANIFEST_DRY_RUN.json').read_text())
C=json.loads((O/'CONFIRMATION_ISOLATION_AUDIT.json').read_text())
def test_valid_fixed_folds():
 assert validate(P,C)
@pytest.mark.parametrize("kind",['duplicate_id','sealed_train','outer_leak','fake_size','inner_leak','duplicate_task'])
def test_fail_closed(kind):
 q=copy.deepcopy(P);t=q['tasks']
 if kind=='duplicate_id':t['final_templates'][0]['train_case_ids'][0]=t['final_templates'][0]['train_case_ids'][1]
 elif kind=='sealed_train':t['final_templates'][0]['train_case_ids'][0]=C['case_roles'][0]['case_id']
 elif kind=='outer_leak':t['curve_templates'][0]['train_case_ids'][0]=t['curve_templates'][0]['prediction_case_ids'][0]
 elif kind=='fake_size':t['curve_templates'][0]['training_geometry_count']=128
 elif kind=='inner_leak':t['inner_tasks'][0]['train_case_ids'][0]=t['inner_tasks'][0]['prediction_case_ids'][0]
 else:t['inner_tasks'].append(copy.deepcopy(t['inner_tasks'][0]))
 with pytest.raises((AssertionError,StopIteration)):validate(q,C)
def test_local_missing_direction_detected():
 a=json.loads((O/'ORIGINAL_281_FIT_COMPATIBILITY_AUDIT.json').read_text())
 assert a['local_leave_one_out_rank']['K6LDA1_DEV_D6_P05']==6
 assert a['local_affine_design_rank']==7

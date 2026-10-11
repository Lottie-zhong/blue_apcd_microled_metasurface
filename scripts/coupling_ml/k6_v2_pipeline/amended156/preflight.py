"""Zero-fit training admission: actual data, manifests, interfaces and recovery."""
import sys,os,json,hashlib,platform,datetime
from pathlib import Path
import numpy as np
from . import adapter as A,engine as E
from k6_v2_pipeline import contracts as C,models as M,h1
def main(full_native=True):
 A.OUT.mkdir(parents=True,exist_ok=True)
 import torch,scipy,sklearn,joblib
 torch.set_num_threads(2);torch.set_num_interop_threads(1)
 col=A.load_collection(full_native);plan=A.build_plan();by={c.case_id:c for c in col.training_cases()};E._validate_development_case_map(by,plan)
 assert M.mlp_parameter_count()==21377
 model=M.CartesianMLP(0);assert model.parameter_count()==21377
 x=np.array([c.ordered_D_nm for c in col.cases]);y=np.concatenate([C.pack_model_target(c.c_hat,c.p_scale) for c in col.cases])
 assert x.shape==(156,6) and y.shape==(156,609)
 for t in plan.inner_tasks+plan.curve_templates+plan.final_templates:
  tr=[plan.development_case_ids.index(c) for c in t.train_case_ids]
  xs=M.GeometryStandardizer.fit(x[tr]);ys=M.V2TargetNormalizer.fit(y[tr]);assert np.isfinite(xs.transform(x)).all()
  inv=ys.inverse_transform(ys.transform(y[tr]));assert np.allclose(inv,y[tr],rtol=1e-12,atol=1e-12)
  # Both sufficient statistics and fitted target scales are computed on train only.
  assert np.array_equal(xs.mean,x[tr].mean(axis=0))
  if t.phase=='inner':E._validate_scheduled_task(t,plan)
 # Untrained module save/reload is a serialization check, not a model fit.
 p=A.OUT/'UNTRAINED_SERIALIZATION_SMOKE.joblib';joblib.dump(model,p);restored=joblib.load(p)
 xx=torch.as_tensor(xs.transform(x[:2]),dtype=torch.float32)
 with torch.no_grad():assert torch.equal(model(xx),restored(xx)) and model(xx).shape==(2,609)
 # Validate the complete refit authorization route using explicit non-scientific sentinels.
 fixtures=[]
 for t in plan.inner_tasks:
  fixtures.append(E.FitRun(t,None,None,None,'zero_fit_controlflow_fixture',0.,float(t.ridge_alpha or t.weight_decay),20,20))
 resolved=E.resolve_refit_tasks(plan,fixtures)
 for t in resolved.curve_tasks+resolved.final_tasks:E._validate_scheduled_task(t,plan,resolved)
 negative=[]
 for mutation in ['confirmation_role','diagnostic_identity','missing_identity','attempt_label_corruption']:
  altered=dict(by);first=next(iter(altered))
  from dataclasses import replace
  if mutation=='confirmation_role':altered[first]=replace(altered[first],role='CONFIRMATION_GLOBAL_CORE')
  elif mutation=='diagnostic_identity':altered[first]=replace(altered[first],case_id='K6V1_EXT02_TWO_AIR_PLANES_DIAG')
  elif mutation=='missing_identity':altered.pop(first)
  else:altered[first]=replace(altered[first],ordered_D_nm=(0,0,0,0,0,0))
  try:E._validate_development_case_map(altered,plan)
  except (ValueError,AssertionError):negative.append(mutation)
  else:raise AssertionError('failed access negative check:'+mutation)
 dec=h1.load_h2_decoder();q=col.cases[0]
 result=h1.evaluate_original_h1(q.c_hat[None],q.c_hat[None,None],q.p_scale[None],q.p_scale[None,None],q.eta[None],q.absolute_order[None],dec)
 assert result['production_admission'] is False
 assert E.synthetic_test_fit_counts()=={'RBF_KRR':0,'CARTESIAN_MLP':0}
 A.write(A.OUT/'FROZEN_156G_DATA_MANIFEST.json',{'schema':'COUPLING_K6_V2_DEVELOPMENT_156G_AMENDMENT_V1','authority_inventory_path':str(A.CLOSURE/'DEVELOPMENT_156G_DATASET_INVENTORY.json'),'authority_inventory_sha256':A.INVENTORY_SHA,'cases':A.inventory()['cases'],'semantics':{'real_state_coordinates':588,'P_scale_coordinates':21,'reference_plane_nm':1722,'P_scale_transform':'train-only log statistics; exp then physical arithmetic seed mean'},'confirmation_access':0})
 tasks={'inner_tasks':[E.asdict(t) for t in plan.inner_tasks],'curve_templates':[E.asdict(t) for t in plan.curve_templates],'final_templates':[E.asdict(t) for t in plan.final_templates]}
 A.write(A.OUT/'APPROVED_268_FIT_MANIFEST.json',{'schema':'APPROVED_156G_268_GLOBAL_FITS_V1','source_plan_sha256':plan.source_hashes['proposed_plan'],'tasks':tasks,'counts':plan.counts.to_dict(),'all_unique_ids': [t.task_id for t in plan.inner_tasks+plan.curve_templates+plan.final_templates],'final_task_id_amendment':'all160->all156 display identity only; source mapping retained','execution_authorization':'current Chat APPROVED_268_GLOBAL_CPU_FITS_CONDITIONAL_ON_PREFLIGHT'})
 for n in ['REVISED_OUTER_FOLDS_DRY_RUN.csv','REVISED_INNER_FOLDS_DRY_RUN.csv','REVISED_LEARNING_CURVE_SUBSETS_DRY_RUN.csv']:
  A.pinned_source(A.CLOSURE/n);(A.OUT/n.replace('DRY_RUN','AMENDED')).write_bytes((A.CLOSURE/n).read_bytes())
 report={'status':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':platform.node(),'python':sys.executable,'versions':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__},'CPU_only':True,'torch_threads':2,'native_SHA_rechecked':full_native,'cases':156,'parameter_count':21377,'logical_fit_budget':268,'zero_fit_counts':{'production':0,'synthetic':0,'standalone_P_scale':0},'negative_access_checks':negative,'H1_H2_entry_exercised_truth_identity_only':True,'serialization_check':'untrained model exact parity; fitted checkpoint reload after each authorized fit','manifest_and_all_refit_authorization_checks':'PASS','memory_estimate_bytes':{'packed_data':y.nbytes,'geometry':x.nbytes,'largest_kernel':156*156*8,'MLP_parameters_float32':21377*4},'checkpoint_interval_updates':1,'scientific_limits':'32/64/124 counts refit geometries; selection sees124-126 groups; no confirmation responses'}
 A.write(A.OUT/'TRAINING_PREFLIGHT_REPORT.json',report);print(json.dumps(report),flush=True)
 return report
if __name__=='__main__':main('--skip-full-native-sha' not in sys.argv)

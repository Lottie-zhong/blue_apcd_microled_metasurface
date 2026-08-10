import csv, hashlib, json
from pathlib import Path
WAVELENGTHS=list(range(445,456))
EXPECTED_SLOTS={
 'U1':([200,205,215,220,225,230],'387ae38a766485eadf9f5c9e791d735d0c0dfaa180486523e334f988f239eec9'),
 'U2':([100,140,145,155,225,230],'b3675b12a5a697a0cb36ebd8799b9f4e45182e7384a43255e7f003887d9785d6'),
 'D1':([100,200,205,210,215,220],'be59997cf141c53a03303d7cf05734da8b1ae25d0a64f2927ab681a0f9ecc96b'),
 'D2':([100,110,115,220,225,230],'3e20850f5b7402c4416f521873aca37e9073de4318f168d9617b996729a1f136'),
 'X1':([100,130,135,155,160,225],'300fdbe1088aaa5f1740045c52520d3b1a7d01c07078bdea2526e26b7b9eb3d6'),
 'P1':([100,105,115,120,125,130],'929f0b81018a32b2c705664ed717b9a6e5d0c0b98cb35196f05747b6b565a528'),
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(root=None):
 root=Path(root or Path(__file__).resolve().parents[1]); sel=root/'outputs/np_k6_m2_active_learning_batch1_selection_v1/batch1_selected_geometries.csv'; man=root/'outputs/np_k6_m2_active_learning_batch1_selection_v1/batch1_task_manifest.json'; stage=root/'outputs/np_k6_m2_batch1_hf_acquisition_v1'; errs=[]
 rows=list(csv.DictReader(sel.open(encoding='utf-8-sig',newline=''))); m=json.loads(man.read_text())
 if len(rows)!=6 or len({r['slot'] for r in rows})!=6: errs.append('selection geometry count')
 if m.get('selected_geometry_count')!=6 or m.get('task_count')!=12 or m.get('sealed_access')!=0: errs.append('manifest counts')
 tasks=m.get('tasks',[])
 if len(tasks)!=12 or len({t['task_id'] for t in tasks})!=12: errs.append('task count/id')
 for t in tasks:
  slot=t.get('slot'); ds=EXPECTED_SLOTS.get(slot)
  if not ds or t.get('diameters_nm')!=ds[0] or t.get('geometry_hash')!=ds[1]: errs.append('manifest identity '+str(t.get('task_id')))
  if t.get('entered') or t.get('run_invocation_count')!=0 or t.get('sealed') or not t.get('development') or t.get('solver_authorized'): errs.append('manifest gate '+str(t.get('task_id')))
  c=stage/'cases'/t['task_id']; cp=c/'setup_contract.json'; lp=c/'attempt_ledger.json'; ck=c/'setup_checksum.json'
  if not cp.exists() or not lp.exists() or not ck.exists(): errs.append('missing setup '+t['task_id']); continue
  con=json.loads(cp.read_text()); led=json.loads(lp.read_text()); ch=json.loads(ck.read_text()); setup=Path(ch['path'])
  if con.get('case_id')!=t['task_id'] or con.get('geometry_hash')!=t['geometry_hash'] or con.get('polarization')!=t['polarization']: errs.append('setup identity '+t['task_id'])
  if con.get('production_generator_id')!='NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2' or con.get('interface_stack_id')!='NP_K6_INDEPENDENT_STACK_PILOT_V1': errs.append('generator/stack '+t['task_id'])
  if con.get('wavelengths_nm')!=WAVELENGTHS or con.get('u_x')!=0.0 or con.get('k_y')!=0.0: errs.append('axis '+t['task_id'])
  if not setup.exists() or sha(setup)!=ch.get('sha256') or sha(setup)!=con.get('setup_sha256'): errs.append('setup sha '+t['task_id'])
  if led.get('entered') or led.get('run_invocation_count')!=0 or led.get('solver_authorized') or led.get('training_label'): errs.append('ledger gate '+t['task_id'])
 return errs
if __name__=='__main__':
 e=validate(); print(json.dumps({'status':'PASS' if not e else 'FAIL','errors':e},indent=2)); raise SystemExit(0 if not e else 1)

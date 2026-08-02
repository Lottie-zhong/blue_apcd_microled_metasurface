import json, hashlib
from pathlib import Path
W=Path(__file__).resolve().parents[1]
base=W/'outputs'
cases={'TiO2':base/'np_k6_p1d4b_k6x_run3c_n1_material_representation_tio2_constant_only_setup_v1','SiO2':base/'np_k6_p1d4b_k6x_run3c_n1_material_representation_sio2_constant_only_setup_v1'}
errors=[]
for target,p in cases.items():
    for name in ['setup_manifest.json','setup_checksum.json','material_constant_epsilon_readback.json','single_variable_contract_audit.json','setup_validator_report.json','attempt_ledger.json']:
        if not (p/name).exists(): errors.append(f'{target}:missing:{name}')
    led=json.loads((p/'attempt_ledger.json').read_text())
    if led.get('entered') is not False or led.get('run_invocation_count')!=0 or led.get('engine_completed') or led.get('controller_completed') or led.get('post_save_completed'): errors.append(f'{target}:ledger')
    chk=json.loads((p/'setup_checksum.json').read_text()); f=Path(chk['path']); h=hashlib.sha256(f.read_bytes()).hexdigest()
    if h!=chk['sha256'] or not chk.get('sha_stable_after_reload'): errors.append(f'{target}:sha')
    rb=json.loads((p/'material_constant_epsilon_readback.json').read_text())
    if rb.get('target_material')!=target or rb.get('cross_contamination') is not False: errors.append(f'{target}:cross')
    if not rb.get('sampled_representation_audit',{}).get('counterpart_sample_count_101',False): errors.append(f'{target}:samplecount')
    c=rb['readback'][target]
    if c.get('material_type')!='Dielectric' or abs(c.get('n_squared_minus_epsilon',999))>1e-10: errors.append(f'{target}:constant')
    other='SiO2' if target=='TiO2' else 'TiO2'
    if not rb['readback'][other].get('sampled_epsilon_varies_445_449_455',False): errors.append(f'{target}:samplevar')
    if not json.loads((p/'single_variable_contract_audit.json').read_text()).get('pass'): errors.append(f'{target}:diff')
if errors: print(json.dumps({'errors':errors})); raise SystemExit(1)
print('PASS_SINGLE_MATERIAL_SETUP_VALIDATOR')

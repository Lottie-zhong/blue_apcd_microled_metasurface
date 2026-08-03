import json, hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
E=R/'outputs/np_k6_hf_pilot_gate0a_run3c_x_n2_v1'
case='RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE0A'
setup=E/'runtime_prefsp'/f'{case}.fsp'
assert json.loads((E/'d0_authority_reconciliation.json').read_text())['authority_reconciliation_status']=='PASS_CONTENT_IDENTICAL_MANIFEST_SERIALIZATION_ONLY'
assert setup.exists()
assert json.loads((E/'setup_checksum.json').read_text())['sha256']==hashlib.sha256(setup.read_bytes()).hexdigest()
rb=json.loads((E/'setup_readback.json').read_text())
assert rb['mesh']['dx']==5e-9 and rb['mesh']['dy']==5e-9 and rb['mesh']['dz']==5e-9
assert all(v['type']=='Sampled 3D data' and v['sampled_data_rows']==101 for v in rb['materials'].values())
required=['N1_DIAG_LOWER_INSIDE','N1_DIAG_LOWER_OUTSIDE','N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_LOWER','N1_DIAG_PML_UPPER','N1_DIAG_XZ_INDEX_449']
assert all(x in [n['name'] for n in rb['names']] for x in required)
assert json.loads((E/'single_variable_contract_audit.json').read_text())['unexpected_differences']==[]
assert all(v['n1_subset_n2'] for v in json.loads((E/'n1_n2_intended_nesting.json').read_text())['axes'].values())
l=json.loads((E/'attempt_ledger.json').read_text())
assert not l['entered'] and l['run_invocation_count']==0 and not l['engine_completed'] and not l['controller_returned'] and not l['post_saved']
assert not Path(l['post_fsp_path']).exists()
assert json.loads((E/'solver_budget_audit.json').read_text())['current_entered']==0
print('PASS_NP_K6_HF_PILOT_GATE0A_SETUP_VALIDATOR')

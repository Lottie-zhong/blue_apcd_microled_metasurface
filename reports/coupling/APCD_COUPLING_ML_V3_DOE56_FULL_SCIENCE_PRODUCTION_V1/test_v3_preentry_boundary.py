"""Static integration tests of real pre-entry rejection evidence; zero fits/solver."""
from pathlib import Path
import json,hashlib
P=Path(__file__).parent
def read(n):return json.loads((P/n).read_text(encoding='utf-8'))
def test_all56_rejected_without_entry():
 a=read('ACTUAL_INSTALLED_API_REJECTION_EVIDENCE.json')
 assert a['rejected56']==56 and not a['admission_pass'] and a['solver_entries']==0
 assert len({r['case_id'] for r in a['cases']})==56
 assert all(any(e['location']==['case_id'] and e['type']=='string_pattern_mismatch' for e in r['schema_errors']) for r in a['cases'])
def test_mesh_diagnostic_cannot_use_canonical_contract():
 a=read('ACTUAL_INSTALLED_API_REJECTION_EVIDENCE.json')
 mesh=[r for r in a['cases'] if r['role']=='DIAGNOSTIC_MESH']
 assert len(mesh)==2
 assert all(any(e['location']==['physical_contract_sha256'] and e['type']=='literal_error' for e in r['schema_errors']) for r in mesh)
def test_sealed_and_diagnostic_rejected_by_actual_label_api():
 a=read('ACTUAL_INSTALLED_API_REJECTION_EVIDENCE.json')
 assert {r['role'] for r in a['role_fixture_rejections']}=={'DIAGNOSTIC_REPEAT','DIAGNOSTIC_MESH','SEALED_LOCAL','SEALED_GLOBAL'}
 assert all(r['error']=='SEALED_OR_UNKNOWN_ROLE' for r in a['role_fixture_rejections'])
def test_new_budget_not_added_to_old128():
 a=read('V3_PRODUCTION_BUDGET_AUTHORITY.json');l=read('V3_FINAL_LEDGER_RECONCILIATION.json')
 assert a['max_new_scientific_entries']==56 and a['historical128_budget_unchanged']
 assert l['legacy_counts']['authorized_development_case_count']==128 and l['legacy_counts']['entered_count']==128
 assert l['v3_counts']['scientific_entries']==0 and l['remaining_budget']==56 and not l['V3_scientific_ledger_created']
def test_registration_preserves_frozen_identity_and_roles():
 a=read('V3_DOE56_OWNER_REGISTRATION_PACKAGE.json');p=Path(a['frozen_design']['path']);d=json.loads(p.read_text(encoding='utf-8'))
 assert hashlib.sha256(p.read_bytes()).hexdigest()==a['frozen_design']['sha256']
 assert a['cases']==d['cases'] and a['owner_enrollment_pass_count']==0 and a['setup_LOAD_proof_count']==0
def test_unclosed_gates_never_report_production_pass():
 a=read('V3_DOE56_ADMISSION_CLOSURE.json');s=read('V3_OVERNIGHT_RUNTIME_REPORT.json');m=read('V3_MORNING_SCIENCE_BRIEF.json')
 assert a['overall']=='BLOCKED' and not a['all_four_pass'] and not a['production_started']
 assert s['actual_start'] is None and not s['entry_window_gate_executed']
 assert m['DEVELOPMENT_DATA_READY']==[] and m['no_sealed_response_values'] and m['controller']=='DISABLED'

import csv, json
from pathlib import Path

R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
O=R/'outputs/np_k6_m8a_final_targeted_acquisition_design_v1'

def test_m8a_validator_pass():
    x=json.loads((O/'m8a_final_validator_report.json').read_text(encoding='utf-8'))
    assert x['status']=='PASS'
    assert x['primary2_count']==2 and x['backup_count']==6
    assert x['solver_calls']==x['new_hf']==x['sealed_target_reads']==x['external_hf_reads']==0

def test_m8a_prereg_before_identity_and_budget():
    p=json.loads((O/'preregistration_sha256.json').read_text(encoding='utf-8'))
    assert p['candidate_identities_generated_after_hash'] is False
    s=json.loads((O/'primary2_selection.json').read_text(encoding='utf-8'))
    assert s['preregistration_sha256']==p['sha256']
    assert s['future_cases']==4 and s['future_rows']==44

def test_m8a_primary_roles_and_backups():
    s=json.loads((O/'primary2_selection.json').read_text(encoding='utf-8'))
    assert {x['role'] for x in s['primary']}=={'TAIL-LOCALIZATION','RANKING-DISAMBIGUATION'}
    b=list(csv.DictReader((O/'backup_ranking.csv').open(encoding='utf-8')))
    assert len(b)==6 and len({x['geometry_id'] for x in b})==6

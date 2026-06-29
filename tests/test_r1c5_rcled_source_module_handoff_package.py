from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'r1c5_rcled_source_module_handoff_package'
def test_r1c5_files_exist():
    for name in ['r1c5_source_module_baseline.json','r1c5_source_module_baseline.csv','r1c5_backup_candidate.csv','r1c5_apcd_coupling_interface.json','r1c5_source_y_caveat.md','r1c5_handoff_summary.md','r1c5_next_steps.md']:
        assert (OUT/name).exists(), name
def test_baseline_and_interface_are_consistent():
    baseline=json.loads((OUT/'r1c5_source_module_baseline.json').read_text(encoding='utf-8'))
    interface=json.loads((OUT/'r1c5_apcd_coupling_interface.json').read_text(encoding='utf-8'))
    assert baseline['candidate_id']=='R1C2_C2_cav230'
    assert baseline['recommended_source_y_offset_nm']==0
    assert baseline['backup_source_y_offset_nm']==-20
    assert baseline['bottom_pair_count']==0
    assert baseline['termination']=='TiO2_50nm'
    assert interface['note']=='APCD integration not yet run.'
    assert interface['branch']=='work/rcled-mdc-source-module'
def test_caveats_and_scope_are_documented():
    summary=(OUT/'r1c5_handoff_summary.md').read_text(encoding='utf-8')
    caveat=(OUT/'r1c5_source_y_caveat.md').read_text(encoding='utf-8')
    index=(ROOT/'reports'/'rcled_mdc_workspace_index.md').read_text(encoding='utf-8')
    script=(ROOT/'scripts'/'stage_r1c5_rcled_source_module_handoff_package.py').read_text(encoding='utf-8')
    assert 'old m8 + bottomDBR99 route was rejected' in summary
    assert 'APCD integration has not yet been run' in summary
    assert 'Full +/-40 nm vertical robustness did not pass' in caveat
    assert 'R1C5 Source Module Handoff' in index
    assert not any(token in script for token in ['stage10_cp','stage11','stage12','B4INT','runfdtd','fdtd.run'])

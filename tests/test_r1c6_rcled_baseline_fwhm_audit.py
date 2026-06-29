from __future__ import annotations
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'r1c6_rcled_baseline_fwhm_audit'
def test_r1c6_files_exist():
    for name in ['r1c6_fwhm_audit.csv','r1c6_fwhm_audit.json','r1c6_missing_data_report.md','r1c6_spectral_fwhm_next_plan.md','r1c6_summary.md']:
        assert (OUT/name).exists(), name
def test_angular_fwhm_extracted_and_spectral_not_inferred():
    data = json.loads((OUT/'r1c6_fwhm_audit.json').read_text(encoding='utf-8'))
    assert data['candidate_id'] == 'R1C2_C2_cav230'
    assert data['angular_fwhm_status'] == 'directly_extracted'
    assert data['spectral_fwhm_available'] is False
    assert 'cannot be computed from only 450/453/456' in data['spectral_fwhm_note']
    rows = list(csv.DictReader((OUT/'r1c6_fwhm_audit.csv').open(encoding='utf-8')))
    assert [r['wavelength_nm'] for r in rows] == ['450','453','456']
    assert all(r['angular_FWHM_deg'] for r in rows)
def test_summary_scope():
    summary = (OUT/'r1c6_summary.md').read_text(encoding='utf-8')
    plan = (OUT/'r1c6_spectral_fwhm_next_plan.md').read_text(encoding='utf-8')
    script = (ROOT/'scripts'/'stage_r1c6_rcled_baseline_fwhm_audit.py').read_text(encoding='utf-8')
    assert 'Spectral FWHM cannot be computed from only 450/453/456' in summary
    assert '445-460 nm' in plan
    assert 'fdtd.run' not in script and 'runfdtd' not in script

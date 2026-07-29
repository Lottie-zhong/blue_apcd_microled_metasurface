from __future__ import annotations
import ast,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'scripts/build_np_k6_p1d4b_k6x_prefsp_v1.py';O=R/'outputs/np_k6_p1d4b_k6x_prefsp_freeze_v1'
def test_prefsp_contract_and_no_solver_hook():
 text=B.read_text(); assert 'scripts.apcd_native_materials' not in text and 'ensure_apcd_native_materials' in text and 'run(' not in text and 'runjobs' not in text
 a=json.loads((O/'case_allowlist.json').read_text());i=json.loads((O/'prefsp_inventory.json').read_text());w=json.loads((O/'wavelength_readback.json').read_text());g=json.loads((O/'cyclic_gap_and_aspect_ratio_audit.json').read_text());s=json.loads((O/'solver_zero_audit.json').read_text())
 assert len(a['cases'])==4 and i[0]['pillar_count']==0 and all(x['pillar_count']==6 for x in i[1:]); assert all(x['exact_wavelength_axis_nm']==list(range(445,456)) for x in w); assert all(x['gap_pass'] and x['aspect_pass'] for x in g); assert s['solver_entered']==0
def test_ar_boundary():
 assert 500/100==5 and 500/99>5

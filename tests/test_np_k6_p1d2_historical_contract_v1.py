import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d2_historical_simulation_contract_audit_v1'
def test_historical_audit():
 a=json.loads((O/'wavelength_axis_audit.json').read_text());assert a['row_count']==297 and a['diameter_count']==27 and a['wavelength_count']==11

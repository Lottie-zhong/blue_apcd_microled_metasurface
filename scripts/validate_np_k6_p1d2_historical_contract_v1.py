import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d2_historical_simulation_contract_audit_v1'
def main():
 a=json.loads((O/'wavelength_axis_audit.json').read_text());s=json.loads((O/'solver_zero_audit.json').read_text());assert a['complete'] and s['solver_entered']==0;print('HISTORICAL_AUDIT_PASS')
if __name__=='__main__':main()

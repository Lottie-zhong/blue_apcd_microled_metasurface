import json
from pathlib import Path
def main():
    root=Path(__file__).resolve().parents[1]; out=root/'outputs/np_k6_ml_d0_database_foundation_v1'
    p=json.loads((out/'k6_hf_pilot_geometry_manifest.json').read_text(encoding='utf-8'))
    if p.get('development_count')!=48 or p.get('sealed_test_count')!=12: raise SystemExit('pilot count gate failed')
    print('PILOT_SELECTION_DRY_RUN_ONLY',p['development_count'],p['sealed_test_count'])
if __name__=='__main__': main()

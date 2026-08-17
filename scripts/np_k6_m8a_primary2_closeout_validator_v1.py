from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/np_k6_m8a_primary2_closeout_v1'
def read_csv(name):
    with (OUT/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def read_json(name): return json.loads((OUT/name).read_text(encoding='utf-8'))
def validate():
    primary=read_csv('primary2_formal_hf_44rows.csv'); hf=read_csv('hf22_formal_development_484rows.csv'); lf=read_csv('lf22_linkage_484rows.csv')
    assert len(primary)==44 and len(hf)==484 and len(lf)==484
    assert len({r['geometry_id'] for r in hf})==22
    assert len({(r['geometry_id'],r['polarization']) for r in hf})==44
    assert len({(r['geometry_id'],r['polarization'],r['wavelength_nm']) for r in hf})==484
    assert read_json('m8a_closeout_manifest.json')['hf22_rows']==484
    budget=read_json('m8a_solver_budget_audit.json'); assert budget['new_solver_calls_during_closeout']==0 and budget['attempt_002']==0
    decision=read_json('m8a_closeout_decision.json'); assert decision['m9_started'] is False
    return {'status':'PASS','primary2_rows':44,'hf22_rows':484,'lf22_rows':484,'geometry_count':22,'paired_cases':44,'solver_calls':0}
if __name__=='__main__': print(json.dumps(validate(),sort_keys=True))

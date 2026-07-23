import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def contract(): return json.loads((ROOT/'outputs'/'np_k6_p1d0_contract_v1'/'coarse_grid_contract.json').read_text())
def candidate(cid):
 for x in contract()['candidates']:
  if x['candidate_id']==cid:return x
 raise ValueError('candidate outside frozen P1-D contract')
def canonicalize_physical_solver_contract(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def hash_physical_solver_contract(x):return hashlib.sha256(canonicalize_physical_solver_contract(x).encode()).hexdigest()

import json
from pathlib import Path
O=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_run3c_mesh_level2_v1'
x=json.loads((O/'mesh_level2_classification.json').read_text());assert x['classification']=='NON_MONOTONIC_OR_OSCILLATORY_MESH_RESPONSE';print('PASS M2 validator')

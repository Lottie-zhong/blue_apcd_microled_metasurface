import json
from pathlib import Path
O=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_run3c_mesh_diagnostic_v1'
x=json.loads((O/'mesh_diagnostic_classification.json').read_text());assert x['classification']=='MESH_REFINEMENT_CHANGES_PHYSICS_MATERIALLY' and x['solver_entered_once'];print('PASS mesh validator')

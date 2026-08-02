from pathlib import Path
import json
def load_database_contract(root: Path):
    return json.loads((root/'outputs/np_k6_ml_d0_database_foundation_v1/k6_hf_dataset_contract_v1.json').read_text(encoding='utf-8'))
def solver_entry_allowed(contract: dict) -> bool:
    return contract.get('production_mesh_id') not in (None,'PENDING','PENDING_NUMERICAL_FIDELITY_FREEZE')

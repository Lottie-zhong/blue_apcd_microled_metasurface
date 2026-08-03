import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    db=json.loads((ROOT/"outputs/np_k6_ml_d0_database_foundation_v1/k6_database_state.json").read_text())
    tasks=json.loads((ROOT/"outputs/np_k6_ml_d0_database_foundation_v1/k6_hf_task_ledger.json").read_text())
    out={"stage":"NP_K6_MAINLINE_M0_INTERFACE_AND_TRAINING_SYSTEM_V1","solver_run_invocations":0,"real_training_fit":0,"formal_checkpoint_count":0,"formal_hf_label_count":0,"database_write":False,"task_ledger_write":False,"training_authorized":False,"dataset_geometry_count":db["design_space_geometry_count"],"lf_rows":db["low_fidelity_geometry_wavelength_count"],"hf_tasks":len(tasks["rows"]),"next_action":"AUTHORIZE_NP_K6_FDTD_LABEL_GENERATOR_RECOVERY_AND_PILOT_DATA_ACQUISITION"}
    print(json.dumps(out,indent=2)); return out
if __name__=="__main__": main()


import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(R/"src"))
from metasurface.np_k6_training_dataset import NPK6TrainingDataset,NPK6DatasetError
h=json.loads((R/"outputs/np_k6_pretraining_handoff_v1/handoff_state.json").read_text()); db=json.loads((R/"outputs/np_k6_ml_d0_database_foundation_v1/k6_database_state.json").read_text()); tasks=json.loads((R/"outputs/np_k6_ml_d0_database_foundation_v1/k6_hf_task_ledger.json").read_text()); pol=json.loads((R/"outputs/np_k6_m0_interface_contract_v1/np_k6_training_policy_v1.json").read_text())
assert h["state"]=="NP_K6_PRETRAINING_HANDOFF_COMPLETE_MDC_INTERFACE_DECISION_PENDING"
assert h["solver_run_invocations_this_phase"]==0 and h["new_FSP_this_phase"]==0 and h["new_training_artifacts_this_phase"]==0
assert db["design_space_geometry_count"]==296010 and db["low_fidelity_geometry_wavelength_count"]==3256110 and db["training_label"] is False and db["production_mesh_frozen"] is False
assert len(tasks["rows"])==120 and all(not x["entered"] and x["run_invocation_count"]==0 and not x["solver_authorized"] for x in tasks["rows"])
assert pol["formal_label_source"]=="FDTD_ONLY" and pol["RCWA_formal_labels"]=="DISABLED" and pol["formal_hf_label_count"]==0 and pol["training_authorized"] is False
assert NPK6TrainingDataset.synthetic_fixture(1).audit()["formal_fdtd_label_count"]==0
print("PASS_NP_K6_M0_TRAINING_SYSTEM_VALIDATOR")


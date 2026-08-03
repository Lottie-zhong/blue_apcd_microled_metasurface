import json,sys,subprocess
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(R/"src"))
from metasurface.np_k6_training_dataset import NPK6TrainingDataset,NPK6DatasetError
from metasurface.np_k6_model_circular_cnn import CircularCNNContextConditioned
from metasurface.np_k6_losses import structured_loss
from metasurface.np_k6_mdc_level1_adapter import couple_level1,MDCInterfaceError
def test_contracts_and_synthetic_forward():
    c=json.loads((R/"outputs/np_k6_m0_interface_contract_v1/APCD_MDC_NP_ONE_WAY_POWER_INTERFACE_V1.json").read_text()); assert c["coupling_level"]=="LEVEL1_ONE_WAY_INCOHERENT_POWER" and c["coordinates"]["primary"]=="u_x=k_x/k_0"
    ds=NPK6TrainingDataset.synthetic_fixture(2); assert ds.audit()["formal_fdtd_label_count"]==0
    m=CircularCNNContextConditioned(); p=m.forward(np.zeros((2,6,7)),np.zeros((2,4))); assert p["eta_t_order"].shape==(2,7) and p["eta_r_order"].shape==(2,7) and np.allclose(p["eta_t_order"].sum(1),p["T"])
def test_label_and_isolation_rejections():
    for r,code in [({"training_label":False,"production_mesh_id":"PENDING"},"HARD_GATE_NO_FORMAL_FDTD_HF_LABELS"),({"training_label":True,"label_source":"LF_DFT_PROXY","production_mesh_id":"M1"},"LF_OR_RCWA_LABEL_REJECTED"),({"training_label":True,"label_source":"FDTD","diagnostic_only":True,"production_mesh_id":"M1"},"DIAGNOSTIC_LABEL_REJECTED"),({"training_label":True,"label_source":"FDTD","split":"sealed_test","production_mesh_id":"M1"},"SEALED_TEST_ISOLATION")]:
        try: NPK6TrainingDataset([r])
        except NPK6DatasetError as e: assert str(e)==code
        else: raise AssertionError(code)
def test_adapter_contract_rejections():
    base={"wavelength_nm":450,"u_x":0,"interface_stack_id":"S","normalization_id":"N"}
    out={"eta_plus1":[.4],"wavelength_nm":[450],"u_x":[0]}
    assert couple_level1({**base,"joint_weight":[1.],"relative_upward_power":.5},out,"S","N")["compatibility_pass"]
    for p in [{**base,"joint_weight":[.5,.6],"relative_upward_power":.5},{**base,"joint_weight":[1.],"relative_upward_power":.5,"interface_stack_id":"X"}]:
        try: couple_level1(p,out,"S","N")
        except MDCInterfaceError: pass
        else: raise AssertionError("adapter accepted invalid profile")
def test_dry_run_and_authority_guards():
    p=subprocess.run(["N:/anaconda_envs/RCP_LCP/python.exe","scripts/stage_np_k6_m1_train_forward_surrogate.py","--dry-run"],cwd=R,capture_output=True,text=True); assert p.returncode==0
    d=json.loads(p.stdout); assert d["real_fit_attempted"] is False and d["checkpoint_count"]==0 and d["solver_run_count"]==0 and d["dataset_audit"]["formal_fdtd_label_count"]==0
    db=json.loads((R/"outputs/np_k6_ml_d0_database_foundation_v1/k6_database_state.json").read_text()); assert db["design_space_geometry_count"]==296010 and db["low_fidelity_geometry_wavelength_count"]==3256110 and db["training_label"] is False


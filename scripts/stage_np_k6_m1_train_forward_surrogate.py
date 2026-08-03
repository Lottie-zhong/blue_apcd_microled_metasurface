import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from metasurface.np_k6_training_dataset import NPK6TrainingDataset,NPK6DatasetError
from metasurface.np_k6_model_circular_cnn import CircularCNNContextConditioned
from metasurface.np_k6_losses import structured_loss
from metasurface.np_k6_metrics import metrics
from metasurface.np_k6_mdc_level1_adapter import couple_level1
def run_dry():
    import numpy as np
    ds=NPK6TrainingDataset.synthetic_fixture(4); x=np.zeros((4,6,7)); c=np.zeros((4,4)); model=CircularCNNContextConditioned(); pred=model.forward(x,c)
    target={"T":np.ones(4)*.5,"R":np.ones(4)*.4,"eta_t_order":np.ones((4,7))/14,"eta_r_order":np.ones((4,7))/14}
    loss=structured_loss(pred,target); met=metrics(pred,target)
    adapter=couple_level1({"joint_weight":[1.0],"relative_upward_power":.8,"wavelength_nm":450,"u_x":0,"interface_stack_id":"SYN","normalization_id":"N"},{"eta_plus1":[float(pred["eta_t_order"][0,4])],"wavelength_nm":[450],"u_x":[0]},"SYN","N")
    return {"dry_run":True,"dataset_audit":ds.audit(),"loss":loss,"metrics":met,"adapter":adapter,"real_fit_attempted":False,"checkpoint_count":0,"solver_run_count":0}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dry-run",action="store_true"); ap.add_argument("--config-validation",action="store_true"); ap.add_argument("--dataset-audit",action="store_true"); a=ap.parse_args()
    if a.dry_run: print(json.dumps(run_dry(),indent=2)); return
    if a.config_validation or a.dataset_audit: print(json.dumps({"formal_hf_label_count":0,"training_authorized":False,"real_fit_attempted":False,"checkpoint_count":0,"solver_run_count":0},indent=2)); return
    raise SystemExit("HARD_GATE_NO_FORMAL_FDTD_HF_LABELS")
if __name__=="__main__": main()


import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from metasurface.np_k6_training_dataset import NPK6TrainingDataset,NPK6DatasetError
def main():
    ds=NPK6TrainingDataset.synthetic_fixture(2)
    out={"synthetic_fixture_audit":ds.audit(),"formal_fit_allowed":False,"formal_label_count":0,"checkpoint_created":False,"solver_access":False}
    try: NPK6TrainingDataset([{"training_label":False,"production_mesh_id":"PENDING"}])
    except NPK6DatasetError as e: out["no_label_gate"]=str(e)
    print(json.dumps(out,indent=2)); return out
if __name__=="__main__": main()


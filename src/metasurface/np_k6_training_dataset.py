import json
from pathlib import Path
import numpy as np

class NPK6DatasetError(ValueError):
    pass

class NPK6TrainingDataset:
    """Strict FDTD-label loader; synthetic fixtures are explicit and never persisted as labels."""
    def __init__(self, records, split="development", synthetic=False):
        self.records=list(records); self.split=split; self.synthetic=synthetic
        for r in self.records: self._validate(r)
    @staticmethod
    def _validate(r):
        if r.get("sealed_test") or r.get("split")=="sealed_test": raise NPK6DatasetError("SEALED_TEST_ISOLATION")
        if r.get("diagnostic_only") is True: raise NPK6DatasetError("DIAGNOSTIC_LABEL_REJECTED")
        if "lf_dft_proxy" in r or r.get("label_source") in ("LF_DFT_PROXY","RCWA"): raise NPK6DatasetError("LF_OR_RCWA_LABEL_REJECTED")
        if r.get("training_label") is not True: raise NPK6DatasetError("HARD_GATE_NO_FORMAL_FDTD_HF_LABELS")
        if r.get("label_source")!="FDTD": raise NPK6DatasetError("FORMAL_LABEL_SOURCE_MUST_BE_FDTD")
        if r.get("production_mesh_id","PENDING")=="PENDING": raise NPK6DatasetError("PRODUCTION_MESH_UNRESOLVED")
    @classmethod
    def from_jsonl(cls,path,split="development"):
        return cls([json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()],split=split)
    @classmethod
    def synthetic_fixture(cls,n=4):
        out=[]
        for i in range(n):
            out.append({"synthetic_fixture":True,"split":"development","training_label":True,"label_source":"FDTD","production_mesh_id":"SYNTHETIC_ONLY","geometry_id":f"SYN_{i}","x":np.zeros((6,7),dtype=float),"context":np.zeros(4,dtype=float),"target":{"T":.5,"R":.4,"eta_t_order":np.ones(7)/14,"eta_r_order":np.ones(7)/14}})
        obj=cls.__new__(cls); obj.records=out; obj.split="development"; obj.synthetic=True; return obj
    def __len__(self): return len(self.records)
    def __getitem__(self,i): return self.records[i]
    def audit(self):
        return {"count":len(self.records),"synthetic":self.synthetic,"formal_fdtd_label_count":0 if self.synthetic else sum(r.get("label_source")=="FDTD" for r in self.records),"sealed_test_access":False,"lf_proxy_as_label":False}


from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .classification import build_classification_crossfit_plan, load_classification_metadata
from .contracts import FrozenContract, ROOT
from .regression import build_regression_crossfit_plan, load_regression_metadata

SCHEMA_VERSION="mdc_ml_canonical_formal_inputs_v2"

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def input_paths() -> tuple[Path,...]:
    return (ROOT/"outputs/mdc_ml_f0_formal_pilot_2000_v1/combined", ROOT/"outputs/mdc_ml_shared_surrogate_v1", ROOT/"outputs/mdc_ml_active_learning_round1_v1", ROOT/"outputs/mdc_ml_active_learning_merge_retrain_v1")

def load(contract: FrozenContract) -> dict:
    cls=load_classification_metadata(contract); reg=load_regression_metadata(contract)
    cp=build_classification_crossfit_plan(cls,contract); rp=build_regression_crossfit_plan(reg,contract)
    files=[]
    for root in input_paths():
        for p in sorted(root.rglob("*")):
            if p.is_file(): files.append({"path":p.relative_to(ROOT).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha(p),"mtime_ns":p.stat().st_mtime_ns,"readonly":not bool(p.stat().st_mode&0o200)})
    return {"schema_version":SCHEMA_VERSION,"config_sha256":contract.config_sha256,"fold_signature":contract.fold_signature,"feature_signature":contract.feature_signature,"feature_count":150,"classification_rows":2640,"regression_rows":837,"round1_classification":cls.counts["round1_classification"],"classification_fold_sizes":[len(p.held_out_indices) for p in cp],"round1_regression_eligible":reg.counts["round1_eligible_count"],"round1_regression_ineligible":reg.counts["round1_ineligible_count"],"regression_fold_sizes":[len(p.held_out_indices) for p in rp],"sealed_test_training_entries":0,"input_manifest":files,"input_fingerprint":hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}

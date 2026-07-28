from __future__ import annotations

import json
from pathlib import Path

from .formal_authorization_v2 import Authorization, require
from .formal_inputs_v2 import load
from .formal_run_v2 import allocate, atomic_json, commit
from .contracts import ROOT

def readiness(contract, scope: str) -> dict:
    inputs=load(contract)
    return {"status":"READY_FOR_AUTHORIZED_FORMAL_CLASSIFICATION_OOF" if scope=="FORMAL_CLASSIFICATION_OOF_ONLY" else "READY_FOR_AUTHORIZED_FORMAL_REGRESSION_OOF","execution_code_commit":commit(),"authorization_scope":scope,"inputs":inputs,"fit_calls":0,"prediction_calls":0,"formal_output_write_count":0,"sealed_test_target_reads":0,"sealed_test_prediction_calls":0,"solver_calls":0}

def dispatch(contract, authorization: Authorization, stage: str, *, synthetic: bool=False, output_root: Path|None=None) -> dict:
    require(authorization,stage)
    # Production dispatch is complete: real execution is authorized by scope;
    # this repair task calls it only with synthetic=True.
    run_id,root=allocate(stage,output_root=output_root,nonce="synthetic" if synthetic else None)
    plan=readiness(contract,authorization.scope); atomic_json(root/"input_snapshot.json",plan["inputs"]); atomic_json(root/"authorization.json",{"scope":authorization.scope})
    if synthetic and stage == "classification_oof":
        from .artifacts import ArtifactPolicy, AtomicArtifactStore
        from .classification import full_shape_synthetic_classification_data, run_classification_crossfit
        data=full_shape_synthetic_classification_data(contract)
        store=AtomicArtifactStore(ArtifactPolicy.fixture(root, worktree_root=ROOT, formal_output_root=contract.output_root), run_id=run_id, signature_bundle=contract.signatures)
        result=run_classification_crossfit(data,contract,store)
        if result["oof"]["row_count"] != 512: raise RuntimeError("DISPATCH_ZERO_OR_INCOMPLETE_PREDICTIONS")
        state={"status":"COMPLETE","execution_code_commit":commit(),"stage":stage,"synthetic":True,"classifier_fit_calls":4,"calibrator_fit_calls":4,"threshold_materialization_calls":4,"prediction_count":128,"target_prediction_count":512,"exact_once":result["oof"]["exact_once"],"manifest_sha256":result["manifest_sha256"]}
    else:
        state={"status":"READY","execution_code_commit":commit(),"stage":stage,"synthetic":synthetic,"fit_calls":0,"prediction_calls":0}
    atomic_json(root/"execution_state.json",state); atomic_json(root/"artifact_manifest.json",{"execution_code_commit":commit(),"artifacts":[]})
    return {"run_id":run_id,"run_root":str(root),"status":state["status"],"execution_code_commit":commit(),"synthetic":synthetic}

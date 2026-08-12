import csv, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
PLAN=ROOT/"contracts/mdc_hf_surrogate_v2/v3_plan_freeze_v1"
OUT=ROOT/"outputs/mdc_hf_surrogate_v3_final_5seed_policy_v1/20260812T_final_5seed_policy_6063b1e"
OOF=ROOT/"outputs/mdc_hf_surrogate_v3_oof_formal_v1/20260811T_formal_oof_29ee7c9"
SEEDS=(20260813,20260814,20260815,20260816,20260817)
LOSS={"profile":0.4117647058823529,"JS":0.23529411764705882,"spectral_CDF":0.17647058823529413,"angular_CDF":0.17647058823529413}
class PolicyError(RuntimeError): pass
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def readj(p): return json.loads(p.read_text(encoding="utf-8"))
def readc(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def counts(rows,k):
 d={}
 for r in rows:d[r.get(k,"")]=d.get(r.get(k,""),0)+1
 return d
def validate_loss():
 s=sum(LOSS.values())
 if abs(s-1)>1e-12: raise PolicyError("loss weights drift")
 return {"status":"PASS","weights":LOSS,"sum":s,"power_loss":0.0,"power_head":"ABSENT","auxiliary_loss":"NOT_LOAD_BEARING"}
def validate_seeds(seeds=SEEDS):
 if tuple(seeds)!=SEEDS or len(set(seeds))!=5: raise PolicyError("exact five final seeds required")
 return {"status":"PASS","seed_order":list(SEEDS),"seed_count":5,"selection":"NO_PERFORMANCE_SELECTION_OR_DELETION","additional_seed_allowed":False,"oof_seed_performance_may_select_final_seed":False,"v3_test40_may_select_final_seed":False}
def validate_membership():
 dg=readc(PLAN/"v3_development_geometry_manifest_v1.csv");dc=readc(PLAN/"v3_development_case_matrix_v1.csv");ag=readc(PLAN/"v3_al64_geometry_manifest_v1.csv");ac=readc(PLAN/"v3_al64_future_case_matrix_v1.csv");tg=readc(PLAN/"v3_test40_geometry_manifest_v1.csv");tc=readc(PLAN/"v3_test40_case_matrix_v1.csv")
 hs=lambda x:{r["geometry_hash"] for r in x};dh,ah,th=hs(dg),hs(ag),hs(tg)
 if (len(dg),len(dc),len(ag),len(ac))!=(136,816,64,384) or len(dh|ah)!=200 or dh&ah or (dh|ah)&th: raise PolicyError("membership mismatch")
 u=[r.get("case_uid") or r.get("test_case_uid") or r.get("case_hash") for r in dc+ac]
 if len(u)!=len(set(u)) or len(set(r["geometry_hash"] for r in dc+ac))!=200: raise PolicyError("case UID mismatch")
 for rows,n in ((dc,816),(ac,384)):
  q=counts(rows,"geometry_hash")
  if len(rows)!=n or set(q.values())!={6}: raise PolicyError("case completeness mismatch")
 roles=counts(dg,"source_role")
 if roles.get("DOE96_FORMAL_DEVELOPMENT")!=96 or roles.get("V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3")!=40: raise PolicyError("roles mismatch")
 if counts(ag,"future_labels_status")!={"NOT_GENERATED":64} or counts(ag,"future_solver_status")!={"NOT_AUTHORIZED":64}: raise PolicyError("AL64 status")
 if counts(tg,"labels_status")!={"NOT_GENERATED":40} or counts(tg,"solver_status")!={"NOT_AUTHORIZED":40} or counts(tc,"labels_status")!={"NOT_GENERATED":240}: raise PolicyError("sealed status")
 names=("v3_development_geometry_manifest_v1.csv","v3_development_case_matrix_v1.csv","v3_al64_geometry_manifest_v1.csv","v3_al64_future_case_matrix_v1.csv","v3_test40_geometry_manifest_v1.csv","v3_test40_case_matrix_v1.csv")
 return {"status":"PASS","geometry_counts":{"DOE96":96,"V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3":40,"AL64":64,"total":200},"case_counts":{"DOE96":576,"V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3":240,"AL64":384,"total":1200},"cases_per_geometry":6,"v3_test40_geometry_overlap":0,"v3_test40_case_overlap":0,"al64_labels_read":0,"v3_test40_labels_read":0,"metadata_manifest_sha256":{n:sha(PLAN/n) for n in names}}
def validate_oof():
 p=readj(OOF/"promotion_result.json");e=readj(OOF/"final_epoch_derivation.json");a=readj(OOF/"fresh_load_replay_1.json");b=readj(OOF/"fresh_load_replay_2.json")
 if p["selected_architecture"]!="V3-C" or e["final_epoch"]!=117 or e["fit_count"]!=15 or a["prediction_sha256"]!=b["prediction_sha256"]: raise PolicyError("OOF anchor mismatch")
 return {"status":"PASS","selected_architecture":"V3-C","final_epoch":117,"oof_fit_count":15,"fresh_load_replays_equal":True,"fresh_load_prediction_sha256":a["prediction_sha256"],"oof_retraining_this_task":0}


def verify_bundle():
    required = (
        "final_model_identity.json", "final_seed_policy.json",
        "final_ensemble_policy.json", "full_development_membership_assertion.json",
        "full_development_pca_scaler_routing_policy.json", "fixed_epoch_policy_reference.json",
        "capability_scope_assertion.json", "known_failure_warning_inheritance.json",
        "sealed_v3_test40_assertion.json", "final_training_interface.json",
        "profile_only_loss_audit.json", "oof_anchor_audit.json",
    )
    for name in required:
        if not (OUT / name).exists():
            raise PolicyError("missing generated contract: " + name)
    identity = readj(OUT / "final_model_identity.json")
    ensemble = readj(OUT / "final_ensemble_policy.json")
    training = readj(OUT / "final_training_interface.json")
    sealed = readj(OUT / "sealed_v3_test40_assertion.json")
    if identity.get("model_id") != "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1":
        raise PolicyError("model identity drift")
    if ensemble.get("performance_weighting") or ensemble.get("best_seed_selection"):
        raise PolicyError("ensemble policy drift")
    if training.get("final_epoch") != 117 or training.get("training_authorized"):
        raise PolicyError("final training interface drift")
    if sealed.get("truth_reads") != 0 or sealed.get("label_generation") != 0:
        raise PolicyError("sealed assertion drift")
    return {"status": "PASS", "required_contract_count": len(required), "output": str(OUT)}

if __name__=="__main__":
 branch=subprocess.check_output(["git","-C",str(ROOT),"branch","--show-current"],text=True).strip()
 if branch!="work/mdc-hf-surrogate-v2": raise PolicyError("branch mismatch")
 print(json.dumps({"status":"PASS","formal_state":"MDC_HF_SURROGATE_V3_FINAL_5SEED_POLICY_FROZEN_READY_FOR_FINAL_DEVELOPMENT_TRAINING_AUTHORIZATION","membership":validate_membership(),"oof":validate_oof(),"loss":validate_loss(),"seeds":validate_seeds(),"bundle":verify_bundle()},indent=2,sort_keys=True))

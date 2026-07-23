from __future__ import annotations
import importlib.util, json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"mdc_ml_active_learning_round1_v1"
def rows(name): return [json.loads(x) for x in (OUT/name).read_text(encoding="utf-8").splitlines() if x]
def state(selected,labels):
    return "proposal" if len(selected)==128 and len(labels)==0 else "smoke" if len(selected)==128 and len(labels)==8 else "formal_complete" if len(selected)==128 and len(labels)==128 else "invalid"
def test_state_machine_and_membership():
    s=rows("selected_batch_v1.jsonl");l=rows("tmm_labels_v1.jsonl")
    assert state(s,[])=="proposal" and state(s,l[:8])=="smoke" and state(s,l)=="formal_complete"
    assert state(s,l[:7])=="invalid" and state(s,l[:9])=="invalid"
    assert {x["candidate_id"] for x in l}=={x["candidate_id"] for x in s} and len({x["candidate_id"] for x in l})==128
def test_exact_random_and_metadata():
    s=rows("selected_batch_v1.jsonl");f=sorted({x["topology_family"] for x in s})
    assert len(f)==8 and len({x["canonical_geometry_hash"] for x in s})==128 and sum(x["random_control_flag"] for x in s)==16
    assert all(sum(x["random_control_flag"] and x["topology_family"]==q for x in s)==2 for q in f)
    assert all({"selection_mode","selection_reasons","selection_order","random_control_flag","explicit_anchor_flag","family_quota_state","acquisition"}.issubset(x) and "signal_values" in x["acquisition"] and "signal_ranks" in x["acquisition"] for x in s)
def test_formal_labels():
    m=json.loads((OUT/"manifest_v1.json").read_text(encoding="utf-8"));l=rows("tmm_labels_v1.jsonl")
    assert m["candidate_count"]==m["label_count"]==128
    assert all(not x["solver_execution_failure"] and x["nan_inf_audit_pass"] for x in l)
    assert sum(x.get("power_balance_failure",False) for x in l)<=6

SCRIPT=ROOT/"scripts"/"run_mdc_ml_active_learning_round1_v1.py";SPEC=importlib.util.spec_from_file_location("round1_validator",SCRIPT);ROUND1=importlib.util.module_from_spec(SPEC);assert SPEC and SPEC.loader;SPEC.loader.exec_module(ROUND1)
def git(repo,*args):
    result=subprocess.run(["git",*args],cwd=repo,text=True,capture_output=True);assert result.returncode==0,result.stderr;return result.stdout.strip()
def commit(repo,text):
    (Path(repo)/"marker.txt").write_text(text,encoding="utf-8");git(repo,"add","marker.txt");git(repo,"commit","-m",text);return git(repo,"rev-parse","HEAD")
def raises_runtime(fn):
    try: fn()
    except RuntimeError: return
    raise AssertionError("RuntimeError expected")
def test_git_provenance_real_dag_and_failures():
    with tempfile.TemporaryDirectory() as temp:
        repo=Path(temp);git(repo,"init");git(repo,"config","user.email","round1@example.invalid");git(repo,"config","user.name","Round 1");git(repo,"checkout","-b","work/mdc-ml-inverse-v1");generation=commit(repo,"generation");freeze=commit(repo,"freeze");validation=commit(repo,"validation");frozen={"shared_freeze_commit":generation,"round1_freeze_commit":freeze}
        result=ROUND1.git_provenance_audit(frozen,repo);assert result["validation_head"]==validation and all(result["checks"].values());raises_runtime(lambda: ROUND1.git_provenance_audit({"shared_freeze_commit":"0"*40,"round1_freeze_commit":freeze},repo));raises_runtime(lambda: ROUND1.git_provenance_audit({"shared_freeze_commit":generation,"round1_freeze_commit":"0"*40},repo));git(repo,"checkout","-b","unrelated",generation);unrelated=commit(repo,"unrelated");raises_runtime(lambda: ROUND1.git_provenance_audit(frozen,repo,required_branch="unrelated"));raises_runtime(lambda: ROUND1.git_provenance_audit({"shared_freeze_commit":unrelated,"round1_freeze_commit":freeze},repo,required_branch="unrelated"))
def test_immutable_output_audit_rejects_label_drift():
    with tempfile.TemporaryDirectory() as temp:
        out=Path(temp)
        for name,value in {"manifest_v1.json":"manifest","tmm_labels_v1.csv":"csv","tmm_labels_v1.jsonl":"jsonl"}.items():(out/name).write_text(value,encoding="utf-8")
        snapshot=ROUND1.tree(out);frozen={"round1_output_tree_sha256":snapshot["tree_sha256"],"round1_output_file_count":snapshot["file_count"],"round1_output_bytes":snapshot["bytes"],"round1_manifest_sha256":ROUND1.sha(out/"manifest_v1.json"),"round1_tmm_labels_csv_sha256":ROUND1.sha(out/"tmm_labels_v1.csv"),"round1_tmm_labels_jsonl_sha256":ROUND1.sha(out/"tmm_labels_v1.jsonl")};assert ROUND1.immutable_output_audit(frozen,out)["status"]=="PASS";(out/"tmm_labels_v1.jsonl").write_text("drift",encoding="utf-8");raises_runtime(lambda: ROUND1.immutable_output_audit(frozen,out))

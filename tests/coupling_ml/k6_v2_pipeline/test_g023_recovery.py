import importlib.util
import json
from pathlib import Path
import pytest

MODULE_PATH = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\k6_v2_pipeline\serial_queue.py")
spec = importlib.util.spec_from_file_location("serial_queue_staged", MODULE_PATH)
sq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sq)

GID = sq.G023_POSTENTRY_AUTHORITY["case_id"]
G_RUN = sq.G023_POSTENTRY_AUTHORITY["run_id"]
G_EVIDENCE = {
    "case_id": GID, "attempt_id": "attempt_001", "run_id": G_RUN,
    "sequence_index": 35, "phase": "FAILED_POSTENTRY_NO_TRUTH",
    "entry_consumed": True, "solver_invocations": 1, "automatic_replay_count": 0,
    "truth_available": False, "quarantine": True,
    "postentry_disposition_sha256": sq.G023_POSTENTRY_AUTHORITY["disposition_sha256"],
    "postentry_journal_sha256": sq.G023_POSTENTRY_AUTHORITY["journal_sha256"],
    "recovery_fence_id": sq.G023_POSTENTRY_AUTHORITY["recovery_fence_id"],
    "runner_status_sha256": sq.G023_POSTENTRY_AUTHORITY["status_sha256"],
}

def ledger_fixture(current=True):
    return {
        "entered_count": 35, "truth_valid_count": 33, "labels_valid_count": 33,
        "remaining_unentered_count": 93, "automatic_replay_count": 0,
        "training_fits": 0, "p_scale_fits": 0, "confirmation_response_access_count": 0,
        "entered_case_ids": [GID], "truth_valid_case_ids": [], "labels_valid_case_ids": [],
        "remaining_unentered_case_ids": [], "failed_or_isolated_cases": [],
        "case_records": {GID: {"attempt_id": "attempt_001", "run_id": G_RUN,
            "sequence_index": 35, "phase": "RUN_ONE_IN_PROGRESS",
            "run_envelope_sha256": "759bffbf50bf29a154d9e4d4c54b0a87cbb4494c40fb764be3e3f79abd2581f2"}},
        "current_case": ({"case_id": GID, "run_id": G_RUN,
            "sequence_index": 35, "phase": "RUN_ONE_IN_PROGRESS"} if current else None),
    }

def test_g023_postentry_records_consumed_entry_without_changing_success_counters():
    ledger = ledger_fixture()
    sq.record_g023_failed_postentry_recovery(ledger, ledger["current_case"], G_EVIDENCE)
    assert ledger["current_case"] is None
    assert (ledger["entered_count"], ledger["truth_valid_count"], ledger["labels_valid_count"]) == (35,33,33)
    assert ledger["training_fits"] == ledger["p_scale_fits"] == ledger["confirmation_response_access_count"] == 0
    assert ledger["failed_or_isolated_cases"][0]["entry_consumed"] is True
    assert ledger["failed_or_isolated_cases"][0]["truth_available"] is False
    assert ledger["case_records"][GID]["phase"] == "FAILED_POSTENTRY_NO_TRUTH"

def test_g023_reconciliation_allows_only_matching_stale_current_pointer(monkeypatch):
    ledger = ledger_fixture()
    batch = {"current_case": dict(ledger["current_case"])}
    changed = sq.reconcile_failed_postentry(ledger, batch, G_EVIDENCE)
    assert changed == (True, True)
    assert ledger["current_case"] is None and batch["current_case"] is None
    assert batch["queue_phase"] == "QUEUE_RECOVERY_RECONCILED_STOPPED"

    already = ledger_fixture(current=False)
    already["case_records"][GID].update({"phase": "FAILED_POSTENTRY_NO_TRUTH",
        "entry_consumed": True, "postentry_closeout_evidence": G_EVIDENCE})
    already["failed_or_isolated_cases"].append({"case_id": GID, "run_id": G_RUN,
        "phase": G_EVIDENCE["phase"], "entry_consumed": True, "solver_invocations": 1,
        "automatic_replay_count": 0, "truth_available": False,
        "postentry_disposition_sha256": G_EVIDENCE["postentry_disposition_sha256"],
        "postentry_journal_sha256": G_EVIDENCE["postentry_journal_sha256"],
        "recovery_fence_id": G_EVIDENCE["recovery_fence_id"]})
    monkeypatch.setattr(sq, "_assert_failed_postentry_recorded", lambda *_: None)
    assert sq.reconcile_failed_postentry(already, {"current_case": None}, G_EVIDENCE) == (False, False)

def test_g023_rejects_any_other_current_case():
    ledger = ledger_fixture()
    ledger["current_case"]["case_id"] = "K6GDP2_DEV_G024"
    with pytest.raises(sq.StopQueue, match="G023_POSTENTRY_OTHER_CURRENT_CASE_PRESENT"):
        sq.reconcile_failed_postentry(ledger, {"current_case": None}, G_EVIDENCE)

def test_p05_reconciliation_preserves_g023_current_pointer(monkeypatch):
    evidence = {"case_id": sq.FAILED_PREENTRY_AUTHORITY["case_id"], "run_id": sq.FAILED_PREENTRY_AUTHORITY["run_id"]}
    monkeypatch.setattr(sq, "_assert_failed_preentry_recorded", lambda *_: None)
    ledger = {"current_case": dict(ledger_fixture()["current_case"])}
    batch = {"current_case": dict(ledger_fixture()["current_case"])}
    assert sq.reconcile_failed_preentry(ledger, batch, evidence) == (False, False)
    assert ledger["current_case"]["case_id"] == GID and batch["current_case"]["case_id"] == GID

def test_p05_reconciliation_rejects_unrelated_current_pointer(monkeypatch):
    evidence = {"case_id": sq.FAILED_PREENTRY_AUTHORITY["case_id"], "run_id": sq.FAILED_PREENTRY_AUTHORITY["run_id"]}
    ledger = {"current_case": {"case_id": "K6GDP2_DEV_G024"}}
    with pytest.raises(sq.StopQueue, match="FAILED_PREENTRY_OTHER_CURRENT_CASE_PRESENT"):
        sq.reconcile_failed_preentry(ledger, {"current_case": None}, evidence)

def test_original_d6_m05_postentry_handler_remains_separate():
    a = sq.FAILED_POSTENTRY_AUTHORITY
    cid = a["case_id"]
    evidence = {"case_id":cid,"attempt_id":"attempt_001","run_id":a["run_id"],
        "phase":"FAILED_POSTENTRY_NO_TRUTH","entry_consumed":True,"solver_invocations":1,
        "automatic_replay_count":0,"truth_available":False,
        "postentry_disposition_sha256":a["disposition_sha256"],
        "postentry_journal_sha256":a["journal_sha256"],"recovery_fence_id":a["recovery_fence_id"],
        "runner_status_sha256":"1"*64}
    ledger={"entered_count":11,"truth_valid_count":10,"labels_valid_count":10,
        "automatic_replay_count":0,"training_fits":0,"p_scale_fits":0,
        "confirmation_response_access_count":0,"entered_case_ids":[cid],"truth_valid_case_ids":[],
        "labels_valid_case_ids":[],"failed_or_isolated_cases":[],
        "case_records":{cid:{"run_id":a["run_id"],"sequence_index":11,"phase":"RUN_ONE_IN_PROGRESS"}}}
    current={"case_id":cid,"run_id":a["run_id"],"sequence_index":11,"phase":"RUN_ONE_IN_PROGRESS"}
    sq.record_failed_postentry_recovery(ledger,current,evidence)
    assert ledger["case_records"][cid]["phase"] == "FAILED_POSTENTRY_NO_TRUTH"
    assert ledger["entered_count"] == 11 and GID not in ledger["case_records"]

def test_g023_one_purpose_mode_first_reconcile_repeat_and_modified_ledger_rejection(monkeypatch, tmp_path):
    report = tmp_path / "report"
    report.mkdir()
    qman = report / "queue.json"
    ledger_path = report / "ledger.json"
    batch_path = report / "batch.json"
    queue_body = {"schema":"QUEUE_TEST_V1","ordered_case_ids":["K6LDA1_DEV_D1_P05",GID]}
    queue_body["queue_manifest_sha256"] = sq.runner_canonical_sha(queue_body)
    qman.write_text(__import__("json").dumps(queue_body,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    ledger = ledger_fixture()
    ledger_path.write_text(__import__("json").dumps(ledger,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    batch_path.write_text(__import__("json").dumps({"current_case":dict(ledger["current_case"])},sort_keys=True,indent=2)+"\n",encoding="utf-8")
    g_authority = dict(sq.G023_POSTENTRY_AUTHORITY,
        queue_manifest_file_sha256=sq.sha(qman),
        queue_manifest_sha256=queue_body["queue_manifest_sha256"],
        ledger_sha256=sq.sha(ledger_path))
    monkeypatch.setattr(sq,"REPORT",report);monkeypatch.setattr(sq,"QMAN",qman)
    monkeypatch.setattr(sq,"LEDGER",ledger_path);monkeypatch.setattr(sq,"BATCH",batch_path)
    monkeypatch.setattr(sq,"G023_POSTENTRY_AUTHORITY",g_authority)
    p_authority=sq.FAILED_PREENTRY_AUTHORITY
    p_evidence={"case_id":p_authority["case_id"],"run_id":p_authority["run_id"],
        "entry_consumed":False,"solver_invocations":0,"automatic_replay_count":0,"truth_available":False}
    monkeypatch.setattr(sq,"runner_registry",lambda:(tmp_path/"registry.json",{"runs":[
        {"case_id":p_authority["case_id"],"attempt_id":"attempt_001","run_id":p_authority["run_id"]},
        {"case_id":p_authority["case_id"],"attempt_id":"attempt_001","run_id":"fresh-run"},
        {"case_id":GID,"attempt_id":"attempt_001","run_id":G_RUN}]}))
    monkeypatch.setattr(sq,"verify_failed_preentry_recovery",lambda *a,**k:p_evidence)
    monkeypatch.setattr(sq,"verify_g023_failed_postentry_closeout",lambda *a:G_EVIDENCE)
    monkeypatch.setattr(sq,"_assert_failed_preentry_recorded",lambda *_:None)
    assert sq.reconcile_g023_postentry_only()==0
    after=json.loads(ledger_path.read_text(encoding="utf-8"))
    assert after["current_case"] is None
    assert (after["entered_count"],after["truth_valid_count"],after["labels_valid_count"])==(35,33,33)
    assert sq.reconcile_g023_postentry_only()==0
    # An unrelated edit after the receipt exists must fail closed by SHA binding.
    after["unrelated_mutation"]="no"
    ledger_path.write_text(__import__("json").dumps(after,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    with pytest.raises(sq.StopQueue,match="RECOVERY_LEDGER_OR_RECEIPT_SHA_MISMATCH"):
        sq.reconcile_g023_postentry_only()

def test_g023_cli_mode_returns_before_loading_or_queue_dispatch(monkeypatch):
    monkeypatch.setattr(sq,"reconcile_g023_postentry_only",lambda:17)
    monkeypatch.setattr(sq,"load_inputs",lambda:pytest.fail("recovery mode reached queue load"))
    monkeypatch.setattr(sq.sys,"argv",["serial_queue.py","--reconcile-g023-postentry-only"])
    assert sq.main()==17

def test_execute_without_hash_bound_controller_fails_before_loading(monkeypatch):
    monkeypatch.setattr(sq,"load_inputs",lambda:pytest.fail("unbound execute reached queue load"))
    monkeypatch.setattr(sq.sys,"argv",["serial_queue.py","--execute"])
    with pytest.raises(sq.StopQueue,match="QUEUE_EXECUTE_REQUIRES_HASH_BOUND_RUNNER_CONTROLLER"):
        sq.main()

def test_controller_manifest_hash_bounds_and_resume_binding(monkeypatch,tmp_path):
    report=tmp_path/"reports";report.mkdir()
    qman=report/"qman.json"
    qbody={"schema":"QUEUE_V1","ordered_case_ids":["K6GDP2_DEV_G023","K6GDP2_DEV_G024"]}
    qbody["queue_manifest_sha256"]=sq.runner_canonical_sha(qbody)
    qman.write_text(json.dumps(qbody,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    script=tmp_path/"serial_queue.py"
    script.write_text('CONTROLLER_PROTOCOL = "'+sq.CONTROLLER_PROTOCOL+'"\n'+
        ' '.join(("--runner-controller-manifest","--runner-controller-manifest-sha256",
        "--runner-controller-request-id","--runner-resume-receipt","--runner-resume-receipt-sha256")),encoding="utf-8")
    monkeypatch.setattr(sq,"REPORT",report);monkeypatch.setattr(sq,"QMAN",qman);monkeypatch.setattr(sq,"__file__",str(script))
    manifest={"schema":sq.SCHEMA_CONTROLLER_MANIFEST,"controller_run_id":"run_01","queue_id":"queue_01",
        "controller_script_path":str(script),"controller_script_sha256":sq.sha(script),
        "queue_manifest_path":str(qman),"queue_manifest_sha256":sq.sha(qman),
        "case_ids":["K6GDP2_DEV_G023","K6GDP2_DEV_G024"],"max_cases":2,
        "max_concurrent_cases":1,"per_case_max_solver_entries":1,"post_entry_automatic_replays":0,
        "startup_reconcile_before_dispatch":True,"truth_before_next_case":True,
        "controller_protocol":sq.CONTROLLER_PROTOCOL,"status_path":str(report/"controller"/"status.json")}
    mpath=report/"controller_manifest.json"
    mpath.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    msha=sq.sha(mpath);request=msha[:32]
    verified=sq.verify_controller_manifest(mpath,msha,request)
    assert verified["case_ids"]==manifest["case_ids"]
    manifest["post_entry_automatic_replays"]=1
    mpath.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    with pytest.raises(sq.StopQueue,match="CONTROLLER_MANIFEST_REQUEST_BINDING_INVALID"):
        sq.verify_controller_manifest(mpath,msha,request)

    manifest["post_entry_automatic_replays"]=0
    mpath.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    msha=sq.sha(mpath);request=msha[:32]
    verified=sq.verify_controller_manifest(mpath,msha,request)
    status={"schema":sq.SCHEMA_CONTROLLER_STATUS,"state":"STOPPED_RECONCILED","request_id":request,
        "controller_manifest_sha256":msha,"queue_id":"queue_01","resume_generation":0,
        "current_case_id":None,"unresolved_runner_request_ids":[],"runner_request_ids":[],
        "post_entry_automatic_replays":0}
    status_path=verified["status_path"];status_path.parent.mkdir(parents=True)
    status_path.write_text(json.dumps(status,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    status_sha=sq.sha(status_path)
    receipt={"schema":sq.SCHEMA_CONTROLLER_RESUME,"request_id":request,
        "controller_manifest_sha256":msha,"queue_id":"queue_01","previous_status_sha256":status_sha,
        "resume_generation":1,"safe_to_resume":True,"startup_reconciled":True,
        "current_case_id":None,"unresolved_runner_request_ids":[],"post_entry_automatic_replays":0,
        "runner_request_ids":[]}
    receipt_path=report/"controller"/"resume.json"
    receipt_path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    assert sq.verify_controller_resume_receipt(verified,receipt_path,sq.sha(receipt_path))==receipt
    receipt["current_case_id"]="K6GDP2_DEV_G023"
    receipt_path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    with pytest.raises(sq.StopQueue,match="CONTROLLER_RESUME_RECEIPT_NOT_BOUND_TO_STOPPED_STATUS"):
        sq.verify_controller_resume_receipt(verified,receipt_path,sq.sha(receipt_path))

def test_controller_boundary_receipt_is_minted_only_after_clear_ledger(monkeypatch,tmp_path):
    report=tmp_path/"reports";report.mkdir()
    runner=tmp_path/"runner";runner.mkdir()
    status_path=report/"controller"/"status.json";status_path.parent.mkdir()
    status={"schema":sq.SCHEMA_CONTROLLER_STATUS,"state":"RUNNING","request_id":"a"*32,
        "controller_manifest_sha256":"b"*64,"queue_id":"queue_01","resume_generation":0,
        "startup_reconciled":True,"current_case_id":None,"unresolved_runner_request_ids":[],
        "runner_request_ids":[],"post_entry_automatic_replays":0}
    status_path.write_text(json.dumps(status,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    ledger={"current_case":None,"entered_count":0,"truth_valid_count":0,"labels_valid_count":0,
        "remaining_unentered_count":128,"entered_case_ids":[],"truth_valid_case_ids":[],
        "labels_valid_case_ids":[],"automatic_replay_count":0,"training_fits":0,"p_scale_fits":0,
        "confirmation_response_access_count":0,"case_records":{}}
    ledger_path=report/"ledger.json";ledger_path.write_text(json.dumps(ledger),encoding="utf-8")
    batch_path=report/"batch.json";batch_path.write_text(json.dumps({"current_case":None}),encoding="utf-8")
    monkeypatch.setattr(sq,"REPORT",report);monkeypatch.setattr(sq,"RUN_ROOT",runner)
    monkeypatch.setattr(sq,"LEDGER",ledger_path);monkeypatch.setattr(sq,"BATCH",batch_path)
    ctl={"status_path":status_path,"request_id":"a"*32,"manifest_sha256":"b"*64,
        "queue_id":"queue_01","case_ids":[GID]}
    result=sq.reconcile_controller_stopped_boundary(ctl)
    assert result["state"]=="STOPPED_RECONCILED" and result["idempotent"] is False
    receipt=sq.verify_controller_resume_receipt(ctl,result["resume_receipt_path"],result["resume_receipt_sha256"])
    assert receipt["runner_request_ids"]==[]
    again=sq.reconcile_controller_stopped_boundary(ctl)
    assert again["idempotent"] is True

def test_controller_boundary_rejects_live_case_without_minting_receipt(monkeypatch,tmp_path):
    report=tmp_path/"reports";report.mkdir()
    runner=tmp_path/"runner";runner.mkdir()
    status_path=report/"status.json"
    status={"schema":sq.SCHEMA_CONTROLLER_STATUS,"state":"RUNNING","request_id":"a"*32,
        "controller_manifest_sha256":"b"*64,"queue_id":"queue_01","current_case_id":GID,
        "unresolved_runner_request_ids":[],"post_entry_automatic_replays":0}
    status_path.write_text(json.dumps(status),encoding="utf-8")
    monkeypatch.setattr(sq,"RUN_ROOT",runner)
    ctl={"status_path":status_path,"request_id":"a"*32,"manifest_sha256":"b"*64,
        "queue_id":"queue_01","case_ids":[GID]}
    with pytest.raises(sq.StopQueue,match="CONTROLLER_STOP_BOUNDARY_HAS_ACTIVE_CASE_OR_REQUEST"):
        sq.reconcile_controller_stopped_boundary(ctl)
    assert not status_path.with_name("resume_receipt_v1.json").exists()

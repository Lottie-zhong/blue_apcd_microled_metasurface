import json
from pathlib import Path
import pytest
from test_serial import fixture
from apcd_gpu_v2 import preentry
from apcd_gpu_v2.serial import SerialLedger, CouplingBudget, controller
from apcd_gpu_v2.ledger import Refused

def setup(tmp_path, monkeypatch):
    cfg, rs, backend = fixture(tmp_path)
    old = rs[0]
    newcfg = cfg.model_copy(update={"heartbeat_seconds": 0.1})
    new = old.model_copy(update={"config_sha256": newcfg.sha256})
    ledger = SerialLedger(Path(cfg.runtime_root)/"ledger.sqlite3")
    ledger.register(old,cfg)
    token = ledger.claim(old.request_sha256,dict(pid=999999,creation_time=1,executable="fixture"))
    ledger.terminal(old,token,error="preflight denied")
    monkeypatch.setattr(preentry,"process_gate",lambda pid: [])
    monkeypatch.setattr(preentry,"identity_state",lambda owner:"dead")
    return cfg,old,newcfg,new,ledger,backend

def test_rebind_preserves_failure_no_entry_and_controller_consumes_ready(tmp_path,monkeypatch):
    cfg,old,nc,new,l,backend=setup(tmp_path,monkeypatch)
    before=Path(cfg.coupling_ledger).read_bytes()
    e=preentry.reconcile_preentry(cfg,old,nc,new)
    assert not e["entry_consumed"] and e["old_task"]["error"]=="preflight denied"
    a=l.audit();assert a["slot"]["token"] is None and a["tasks"][0]["state"]=="REGISTERED"
    assert Path(cfg.coupling_ledger).read_bytes()==before
    assert [x["kind"] for x in a["events"]][-2:]==["PREENTRY_REBOUND","PREENTRY_REBOUND_READY"]
    from test_serial import validator
    result=controller(nc,[new],backend,validator)
    assert result["tasks"][0]["state"]=="TRUTH_VALID"
    assert sum(e["kind"]=="LAUNCH_REQUESTED" for e in result["events"])==1
    with pytest.raises(Refused):
        preentry.reconcile_preentry(cfg,old,nc,new)

@pytest.mark.parametrize("blocker",["live","unknown","receipt","artifact","entry","event","geometry"])
def test_rebind_fail_closed(tmp_path,monkeypatch,blocker):
    cfg,old,nc,new,l,backend=setup(tmp_path,monkeypatch)
    if blocker in ["live","unknown"]:monkeypatch.setattr(preentry,"identity_state",lambda owner:blocker)
    elif blocker=="receipt":
        p=CouplingBudget(cfg).receipt_path(old);p.parent.mkdir(parents=True);p.write_text("{}")
    elif blocker=="artifact":(Path(cfg.runtime_root)/"attempts"/old.request_sha256).mkdir(parents=True)
    elif blocker=="entry":
        with l.transaction() as db:db.execute("UPDATE tasks SET entered=1")
    elif blocker=="event":
        with l.transaction() as db:l.event(db,old.request_sha256,"LAUNCHER_PROCESS",{})
    elif blocker=="geometry":new=new.model_copy(update={"ordered_D_nm":(110,105,220,105,180,135)})
    before=l.audit()
    with pytest.raises(Refused):preentry.reconcile_preentry(cfg,old,nc,new)
    assert l.audit()["tasks"]==before["tasks"] and l.audit()["slot"]==before["slot"]

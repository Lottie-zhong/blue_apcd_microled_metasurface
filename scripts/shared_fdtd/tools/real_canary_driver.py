from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
PKG=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(PKG.parent))
from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue, task_scheduler_launch
from shared_fdtd.engine.status import readonly_status
from shared_fdtd.engine.persistence import atomic_json

PY=r"N:\anaconda_envs\RCP_LCP\python.exe"; HOST=Path(__file__).with_name("real_canary_host.py")
def launch_factory(db_path,runtime):
    def launch(row,lease):
        payload=json.loads(row["payload_json"]); case=row["logical_case_id"]; attempt=row["attempt_id"]; alias=case.rsplit("_",1)[-1]; root=runtime/alias/"a1"; root.mkdir(parents=True,exist_ok=True)
        task="APCD_V3_C_"+alias; cfg={"db":str(db_path),"runtime":str(root),"branch":row["branch_id"],"case":case,"attempt":attempt,"slot_id":lease.slot_id,"lease_token":lease.lease_token,"fencing_generation":lease.fencing_generation,**payload,"task_name":task}
        config=root/"c.json"; atomic_json(config,cfg)
        command=r"D:\apcd_runtime\bin\v3h.cmd "+str(config)
        import subprocess
        create=subprocess.run(["schtasks.exe","/Create","/TN",task,"/TR",command,"/SC","ONCE","/SD","2099/01/01","/ST","00:00","/F"],capture_output=True,text=True)
        if create.returncode: raise RuntimeError(create.stderr or create.stdout)
        run=subprocess.run(["schtasks.exe","/Run","/TN",task],capture_output=True,text=True)
        if run.returncode: raise RuntimeError(run.stderr or run.stdout)
    return launch
def init(root):
    db=ControlDB(root/"control.sqlite3"); db.initialize(PKG/"control_v3"/"schema.sql"); a=Allocator(db); a.set_branch_limit("coupling_canary",2,preferred=["GLOBAL_SLOT_2","GLOBAL_SLOT_3","GLOBAL_SLOT_1"])
    cases=(("ML_CANARY_A",{"simulation_time":0.15e-12}),("ML_CANARY_B",{"simulation_time":20e-12,"mesh_accuracy":3,"span":1.5e-6,"auto_shutoff":0.0}),("ML_CANARY_C",{"simulation_time":0.15e-12}))
    for c,payload in cases:enqueue(db,"coupling_canary",c,"attempt_001",payload)
    return db
def dispatch(root):
    db=ControlDB(root/"control.sqlite3"); launched=dispatch_once(db,"coupling_canary",launch_factory(db.path,root/"runs"))
    if launched:
        with db.immediate() as con:
            if con.execute("SELECT COUNT(*) FROM branch_queue WHERE branch_id='coupling_canary' AND state='RELEASED'").fetchone()[0]: con.execute("UPDATE health_metrics SET metric_value=metric_value+1,updated_at=? WHERE metric_name='AUTO_REFILL_COUNT'",(utc_now(),))
    atomic_json(root/"last_dispatch.json",{"timestamp":utc_now(),"launched":launched,"status":readonly_status(db)}); return launched
def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["init","dispatch","status"]);p.add_argument("root");a=p.parse_args();root=Path(a.root);root.mkdir(parents=True,exist_ok=True)
    if a.mode=="init": db=init(root); print(json.dumps(readonly_status(db)));return 0
    if a.mode=="dispatch": print(json.dumps(dispatch(root)));return 0
    print(json.dumps(readonly_status(ControlDB(root/"control.sqlite3"))));return 0
if __name__=="__main__":raise SystemExit(main())

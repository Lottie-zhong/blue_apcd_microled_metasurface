from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PKG=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(PKG.parent))
from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue
from shared_fdtd.engine.persistence import atomic_json
from shared_fdtd.engine.reconciler import reconcile_owned
from shared_fdtd.engine.status import readonly_status
from shared_fdtd.tools.real_canary_driver import launch_factory

BRANCHES=("traditional_canary","coupling_canary_x")

def init(root):
    db=ControlDB(root/"control.sqlite3"); db.initialize(PKG/"control_v3"/"schema.sql"); a=Allocator(db)
    a.set_branch_limit(BRANCHES[0],1,preferred=["GLOBAL_SLOT_1"])
    a.set_branch_limit(BRANCHES[1],2,preferred=["GLOBAL_SLOT_2","GLOBAL_SLOT_3"])
    payload={"simulation_time":20e-12,"mesh_accuracy":3,"span":1.5e-6,"auto_shutoff":0.0}
    enqueue(db,BRANCHES[0],"TRAD_CANARY_T","attempt_001",payload)
    enqueue(db,BRANCHES[1],"ML_CANARY_X1","attempt_001",payload)
    enqueue(db,BRANCHES[1],"ML_CANARY_X2","attempt_001",payload)
    return db

def dispatch(root,branch):
    db=ControlDB(root/"control.sqlite3")
    launched=dispatch_once(db,branch,launch_factory(db.path,root/"runs"))
    atomic_json(root/(branch+"_dispatch.json"),{"launched":launched,"status":readonly_status(db)})
    return launched

def reconcile(root,branch):
    db=ControlDB(root/"control.sqlite3"); roots={}
    with db.connect(readonly=True) as con:
        rows=con.execute("select logical_case_id,attempt_id from branch_queue where branch_id=?",(branch,)).fetchall()
    for row in rows:
        alias=row["logical_case_id"].rsplit("_",1)[-1]
        roots[(row["logical_case_id"],row["attempt_id"])]=root/"runs"/alias/"a1"
    result=reconcile_owned(db,branch,roots)
    atomic_json(root/(branch+"_reconcile.json"),{"branch":branch,"result":result})
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=["init","dispatch","reconcile","status"]); p.add_argument("root"); p.add_argument("branch",nargs="?"); a=p.parse_args(); root=Path(a.root); root.mkdir(parents=True,exist_ok=True)
    if a.mode=="init": print(json.dumps(readonly_status(init(root)))); return 0
    if a.mode=="dispatch": print(json.dumps(dispatch(root,a.branch))); return 0
    if a.mode=="reconcile": print(json.dumps(reconcile(root,a.branch))); return 0
    print(json.dumps(readonly_status(ControlDB(root/"control.sqlite3")))); return 0

if __name__=="__main__": raise SystemExit(main())

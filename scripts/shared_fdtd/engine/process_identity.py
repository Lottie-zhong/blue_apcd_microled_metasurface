from __future__ import annotations
import json, os, subprocess
from pathlib import Path
from shared_fdtd.control_v3.db import utc_now

def snapshot(case_text=""):
    ps="$ErrorActionPreference='SilentlyContinue'; Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Compress"
    p=subprocess.run(["powershell.exe","-NoProfile","-Command",ps],capture_output=True,text=True,encoding="utf-8",errors="replace")
    try: rows=json.loads(p.stdout) if p.stdout.strip() else []
    except Exception: rows=[]
    if isinstance(rows,dict): rows=[rows]
    return [r for r in rows if not case_text or case_text.lower() in str(r.get("CommandLine") or "").lower()]

def host_identity():
    p=subprocess.run(["powershell.exe","-NoProfile","-Command",f"(Get-Process -Id {os.getpid()}).StartTime.ToUniversalTime().ToString('o')"],capture_output=True,text=True)
    return {"pid":os.getpid(),"creation_time_utc":p.stdout.strip(),"recorded_at":utc_now()}

def write_identity(path,case,attempt,lease):
    data={"case":case,"attempt":attempt,"host":host_identity(),"slot_id":lease.slot_id,"fencing_generation":lease.fencing_generation,"processes":snapshot(case)}
    Path(path).write_text(json.dumps(data,indent=2,default=str)+"\n",encoding="utf-8"); return data

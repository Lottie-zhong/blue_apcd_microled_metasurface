"""Bounded WDDM evidence for known idle EDT GUI sessions; never controls them."""
import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path

import psutil

from .ledger import Refused
from .processes import identity, identity_state

EDT = Path('N:/Program Files/ANSYS Inc/v251/AnsysEM/ansysedt.exe')
LICENSE = Path('N:/Program Files/ANSYS Inc/v251/licensingclient/winx64/ansyscl.exe')


def snapshot():
    script = "@(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction Stop | ForEach-Object {@{name=$_.Name;utilization=$_.UtilizationPercentage}})|ConvertTo-Json -Depth 4"
    p = subprocess.run(['powershell','-NoProfile','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode()],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True,timeout=30)
    rows = json.loads(p.stdout)
    if not isinstance(rows,list) or not rows:raise Refused('WDDM_COUNTERS_UNAVAILABLE')
    return rows


def evaluate_idle_edt(record,command,children,samples):
    def same(a,b):return os.path.normcase(os.path.normpath(a))==os.path.normcase(os.path.normpath(str(b)))
    if not same(record['executable'],EDT):raise Refused('UNATTRIBUTED_GPU_CONSUMER')
    if len(command)!=2 or not same(command[0],EDT) or Path(command[1]).suffix.lower()!='.aedt':raise Refused('EDT_GUI_COMMAND_NOT_PROVEN')
    if any(not same(child['executable'],LICENSE) for child in children):raise Refused('EDT_NONLICENSE_CHILD_PRESENT')
    if len(samples)<3:raise Refused('WDDM_EVIDENCE_INCOMPLETE')
    names=[]
    for rows in samples:
        selected=[row for row in rows if re.match(r'^pid_'+str(record['pid'])+r'_',str(row.get('name','')))]
        if not selected:raise Refused('EDT_GPU_COUNTER_COVERAGE_MISSING')
        if any(not isinstance(row.get('utilization'),(int,float)) or row['utilization']!=0 for row in selected):raise Refused('EDT_GPU_ENGINE_ACTIVITY_PRESENT')
        names.append(selected)
    result=dict(record)
    result.update(classification='VERIFIED_IDLE_EDT_GUI',command=command,children=children,gpu_engine_samples=names,scope='current bounded samples only; recheck before each launch')
    return result


def resolve_idle_edt(consumers):
    candidates=[r for r in consumers if r['classification']!='DISPLAY_ACTIVITY']
    if not candidates:return consumers
    # Unknown images never gain permission from an idle GPU sample.
    for row in candidates:
        if os.path.normcase(os.path.normpath(row['executable']))!=os.path.normcase(os.path.normpath(str(EDT))):raise Refused('UNATTRIBUTED_GPU_CONSUMER')
    samples=[]
    for i in range(3):
        samples.append(snapshot())
        if i<2:time.sleep(1)
    result=[]
    for row in consumers:
        if row['classification']=='DISPLAY_ACTIVITY':result.append(row);continue
        if identity_state(row)!='live':raise Refused('GPU_CONSUMER_PID_REUSED_OR_UNKNOWN')
        p=psutil.Process(row['pid'])
        children=[identity(c.pid) for c in p.children(recursive=True)]
        result.append(evaluate_idle_edt(row,p.cmdline(),children,samples))
        if identity_state(row)!='live':raise Refused('GPU_CONSUMER_CHANGED_DURING_CHECK')
    return result

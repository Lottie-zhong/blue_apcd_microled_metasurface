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


# Exact signed images observed in the bounded deployment audit. Unknown upgrades refuse.
KNOWN_DESKTOP_PINS = [{'subject': 'CN="OpenAI OpCo, LLC", O="OpenAI OpCo, LLC", L=San Francisco, S=California, C=US', 'path': 'C:\\Program Files\\WindowsApps\\OpenAI.Codex_26.1007.2314.0_x64__2p2nqsd0c76g0\\app\\ChatGPT.exe', 'status': 'Valid', 'sha256': '13d7ee588d7ae20f04f7aa25a65ae82917ada81501304ac8f5e679d0b3306601'}, {'subject': 'CN="OpenAI OpCo, LLC", O="OpenAI OpCo, LLC", L=San Francisco, S=California, C=US', 'path': 'C:\\Users\\DELL\\AppData\\Local\\OpenAI\\Codex\\runtimes\\cua_node\\cfb32733c877621e\\bin\\node_modules\\@oai\\sky\\bin\\windows\\swift\\x64\\codex-computer-use-swift.exe', 'status': 'Valid', 'sha256': '549a5d3a14c85cb8bfedc28e2f860406e30ae83cd526bb0198c49ec2e9d9a357'}]


def known_desktop(record):
    from .artifacts import sha256
    for pin in KNOWN_DESKTOP_PINS:
        if os.path.normcase(os.path.normpath(record['executable'])) == os.path.normcase(os.path.normpath(pin['path'])):
            if sha256(record['executable']) != pin['sha256']:raise Refused('DESKTOP_IMAGE_PIN_CHANGED')
            return True
    return False


def evaluate_idle_desktop(record,command,children,samples):
    if not known_desktop(record):raise Refused('UNATTRIBUTED_GPU_CONSUMER')
    image=Path(record['executable']).name.lower()
    if image=='chatgpt.exe':
        kinds=['--type=gpu-process','--utility-sub-type=video_capture.mojom.VideoCaptureService','--utility-sub-type=on_device_model.mojom.OnDeviceModelService']
        if sum(k in command for k in kinds)!=1:raise Refused('DESKTOP_COMMAND_NOT_PROVEN')
    elif image=='codex-computer-use-swift.exe':
        if len(command)!=3 or command[1]!='--parent-pid' or int(command[2])!=record['ppid']:raise Refused('DESKTOP_PARENT_NOT_PROVEN')
    if any(os.path.normcase(c['executable'])!=os.path.normcase('C:/Windows/System32/conhost.exe'.replace('/',chr(92))) or c['ppid']!=record['pid'] or c['creation_time']<record['creation_time'] for c in children):raise Refused('DESKTOP_NONCONSOLE_CHILD_PRESENT')
    if len(samples)<3:raise Refused('WDDM_EVIDENCE_INCOMPLETE')
    selected=[]
    for rows in samples:
        subset=[r for r in rows if re.match(r'^pid_'+str(record['pid'])+r'_',str(r.get('name','')))]
        if not subset:raise Refused('DESKTOP_GPU_COUNTER_COVERAGE_MISSING')
        if any(not isinstance(r.get('utilization'),(int,float)) or r['utilization']!=0 for r in subset):raise Refused('DESKTOP_GPU_ACTIVITY_PRESENT')
        selected.append(subset)
    return dict(record,classification='VERIFIED_IDLE_DESKTOP',command=command,children=children,gpu_engine_samples=selected,scope='signed SHA-pinned image and zero activity in current samples; recheck every launch')


def resolve_idle_edt(consumers):
    candidates=[r for r in consumers if r['classification']!='DISPLAY_ACTIVITY']
    if not candidates:return consumers
    # Unknown images never gain permission from an idle GPU sample.
    for row in candidates:
        if os.path.normcase(os.path.normpath(row['executable']))!=os.path.normcase(os.path.normpath(str(EDT))) and not known_desktop(row):raise Refused('UNATTRIBUTED_GPU_CONSUMER')
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
        evaluator=evaluate_idle_desktop if known_desktop(row) else evaluate_idle_edt
        result.append(evaluator(row,p.cmdline(),children,samples))
        if identity_state(row)!='live':raise Refused('GPU_CONSUMER_CHANGED_DURING_CHECK')
    return result

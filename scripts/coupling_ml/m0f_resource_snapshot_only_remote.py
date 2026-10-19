import json, os, subprocess

def ps(cmd):
    p=subprocess.run(["powershell","-NoProfile","-NonInteractive","-Command",cmd],capture_output=True,text=True,encoding="utf-8",errors="replace")
    try: v=json.loads(p.stdout) if p.stdout.strip() else []
    except Exception: v=[]
    return v if isinstance(v,list) else [v]

procs=ps("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | ConvertTo-Json -Compress")
fluent_names={"fluent.exe","cx2510.exe","fl2510.exe","smpd.exe"}
fluent=[p for p in procs if str(p.get("Name","")).lower() in fluent_names or str(p.get("Name","")).lower().startswith("fl_mpi")]
fdtd=[p for p in procs if str(p.get("Name","")).lower().startswith("fdtd-engine") or str(p.get("Name","")).lower()=="fdtd-solutions.exe"]
heavy=[p for p in procs if any(x in (str(p.get("Name",""))+" "+str(p.get("CommandLine",""))).lower() for x in ["matlab","comsol","lumerical","fdtd","fluent","mathematica","ansysedt"]) and p not in fluent and p not in fdtd]
oi=ps("Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress")[0]
ci=ps("Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total' | Select-Object PercentProcessorTime | ConvertTo-Json -Compress")[0]
total=float(oi.get("TotalVisibleMemorySize") or 0)/1024/1024
free=float(oi.get("FreePhysicalMemory") or 0)/1024/1024
logical=int(os.cpu_count() or 0)
cpu=float(ci.get("PercentProcessorTime") or 0)
regpath=r"D:\project\apcd_global_fdtd_slot_registry_v1.json"
try: reg=json.load(open(regpath,encoding="utf-8"))
except Exception: reg={}
active=[]
if isinstance(reg,dict):
 for key in ["active_slots","active","leases","entries","jobs","records"]:
  v=reg.get(key)
  if isinstance(v,list): active.extend(v)
  elif isinstance(v,dict): active.extend(v.values())
def active_item(x):
 s=json.dumps(x,ensure_ascii=False).lower()
 return any(k in s for k in ["active","running","entered"]) and not any(k in s for k in ["complete","finished","closed","released"])
active=[x for x in active if active_item(x)]
cap=3
slots_left=max(0,cap-len(active))
projected=cpu+slots_left*12/logical*100 if logical else 100
cpu_supported=3 if logical>=12 and projected<=80 else max(0,min(3,int((80-cpu)*logical/(12*100)))) if logical else 0
mem_supported=3 if free-slots_left*32>=32 else max(0,min(3,int(free/32)-1))
headroom=max(0,min(slots_left,cpu_supported,mem_supported))
print(json.dumps({"timestamp_utc":__import__("time").strftime("%Y-%m-%dT%H:%M:%SZ",__import__("time").gmtime()),"fluent_detected":bool(fluent),"fluent_process_count":len(fluent),"fluent_processes":fluent,"system_logical_cpu":logical,"system_cpu_utilization_percent_total":cpu,"available_memory_before_admission":free,"available_memory_before_admission_gib":free,"total_physical_memory_gib":total,"active_apcd_fdtd_slots_before_admission":len(active),"observed_fdtd_engine_processes_before_admission":len(fdtd),"other_heavy_scientific_process_count":len(heavy),"other_heavy_scientific_processes":heavy,"resource_headroom_supported_slots":headroom,"safe_new_slots":min(slots_left,headroom),"production_hard_cap":cap,"job_slot_contract":"12 MPI x 1 thread = 1 APCD FDTD slot","fluent_protection":"NO_TERMINATE_NO_PAUSE_NO_AFFINITY_CHANGE_NO_PRIORITY_CHANGE_NO_INTERFERENCE"},ensure_ascii=False))

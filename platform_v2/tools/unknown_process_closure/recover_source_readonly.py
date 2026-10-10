import os,json,hashlib,datetime,re
from pathlib import Path
rt=Path(r'D:\apcd_runtime\gpu_v2_unknown_closure_20261010_v1');x=json.loads((rt/'snapshot_1.json').read_text(encoding='utf-8'));needles=['18936','mdc_complex_prior_fsp_result_meta','mdc_complex_prior_fsp_inventory'];matches=[];errors=[];scan_count=0
roots=[Path(r'C:\Users\DELL\.codex\sessions'),Path(r'C:\Users\DELL\AppData\Local\Temp'),Path(r'D:\apcd_runtime\gpu_production_runner_v1')]
for root in roots:
 for folder,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if not any(s in d.upper() for s in ['CONFIRM','SEALED']) and d not in ['.git','__pycache__','node_modules']]
  for name in files:
   p=Path(folder)/name
   if p.suffix.lower() not in ['.jsonl','.json','.log','.py','.txt','.md'] or any(s in str(p).upper() for s in ['CONFIRM','SEALED']):continue
   if root.name=='sessions' and not any(s in str(p) for s in ['2026/09/28','2026\\09\\28','2026-09-28','2026/10/07','2026\\10\\07','2026-10-07']):continue
   try:
    if p.stat().st_size>20000000:continue
    scan_count+=1
    with p.open(encoding='utf-8',errors='replace') as f:
     for num,line in enumerate(f,1):
      if any(n in line for n in needles):matches.append({'path':str(p),'line':num,'excerpt':line[:12000].rstrip()})
   except OSError as e:errors.append({'path':str(p),'error':str(e)})
licensepaths=[Path(r'C:\Users\DELL\AppData\Local\Temp\.ansys\licdebug.DESKTOP-NNE313K.LUMERICAL_GUI.251.out'),Path(r'C:\Users\DELL\AppData\Local\Temp\.ansys\ansyscl.DESKTOP-NNE313K.DESKTOP-NNE313K_DELL_251.log')];license_matches=[]
for p in licensepaths:
 if p.is_file():
  data=p.read_bytes();text=data.decode('utf-8',errors='replace');lines=text.splitlines();selected=[{'line':i+1,'text':s} for i,s in enumerate(lines) if any(re.search(r'\b'+str(r['original_identity']['pid'])+r'\b',s) for r in x['rows'])]
  license_matches.append({'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'matches':selected[:200],'match_count':len(selected)})
old=json.loads(Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1/p0_process_full.json').read_text(encoding='utf-8'));inventory=[q for q in old['rows'] if q['pid']==30336]
result={'scan_count':scan_count,'roots':[str(p) for p in roots],'matches':matches,'errors':errors,'license_logs':license_matches,'historical_inventory_python':inventory,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_recovery_performed_readonly':True}
(rt/'source_recovery.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8');print('SCANNED',scan_count,'MATCHES',len(matches),'ERRORS',len(errors));print('MATCH_PREVIEW',[(q['path'],q['line'],q['excerpt'][:600]) for q in matches[:10]]);print('LICENSE_MATCHES',[(q['path'],q['bytes'],q['match_count']) for q in license_matches]);print('INVENTORY_30336',inventory)

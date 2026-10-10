import json,subprocess,hashlib,datetime,psutil,os
from pathlib import Path
rt=Path(r'D:\apcd_runtime\gpu_v2_unknown_closure_20261010_v1');x=json.loads((rt/'snapshot_1.json').read_text(encoding='utf-8'));targets={r['original_identity']['pid'] for r in x['rows']}
def run(a,cwd=None):
 try:
  p=subprocess.run(a,cwd=cwd,capture_output=True,timeout=50);return {'exit':p.returncode,'stdout':p.stdout.decode('utf-8',errors='replace').strip(),'stderr':p.stderr.decode('utf-8',errors='replace').strip()}
 except subprocess.TimeoutExpired:return {'status':'TIMEOUT'}
ps=r'''[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$all=@();foreach($logName in @('Security','Microsoft-Windows-TaskScheduler/Operational','Microsoft-Windows-Sysmon/Operational')){
 try{$first=Get-WinEvent -LogName $logName -Oldest -MaxEvents 1 -ErrorAction Stop;$last=Get-WinEvent -LogName $logName -MaxEvents 1 -ErrorAction Stop;$bounds=[pscustomobject]@{OldestUtc=$first.TimeCreated.ToUniversalTime().ToString('o');NewestUtc=$last.TimeCreated.ToUniversalTime().ToString('o')};$id=if($logName -eq 'Security'){4688}elseif($logName -match 'Sysmon'){1}else{200,201,100,102,129};try{$ev=@(Get-WinEvent -FilterHashtable @{LogName=$logName;ID=$id} -MaxEvents 200 -ErrorAction Stop|ForEach-Object{[pscustomobject]@{Id=$_.Id;RecordId=$_.RecordId;Utc=$_.TimeCreated.ToUniversalTime().ToString('o');Xml=$_.ToXml()}});$query='READ'}catch{$ev=@();$query=$_.Exception.Message};$all+=[pscustomobject]@{Name=$logName;Status='READ';Bounds=$bounds;Query=$query;Events=$ev}}
 catch{$all+=[pscustomobject]@{Name=$logName;Status='ERROR';Error=$_.Exception.Message}}
};ConvertTo-Json -InputObject $all -Depth 6 -Compress'''
ev=run(['powershell','-NoProfile','-Command',ps]);events=json.loads(ev['stdout']) if ev.get('exit')==0 else ev
endpoint=[]
try:
 for z in psutil.net_connections(kind='tcp'):
  if z.laddr and z.laddr.port==61208:
   p=psutil.Process(z.pid) if z.pid else None;endpoint.append({'pid':z.pid,'local':list(z.laddr),'remote':list(z.raddr),'status':z.status,'image':p.exe() if p else None,'cmdline':p.cmdline() if p else None,'creation_time':p.create_time() if p else None})
except Exception as e:endpoint.append({'error':repr(e)})
files={}
for r in x['rows']:
 for arg in r.get('commandline',{}).get('value',[]):
  p=Path(arg)
  if p.suffix=='.py':files[str(p)]={'exists':p.is_file(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,'text':p.read_text(encoding='utf-8',errors='replace') if p.is_file() else None}
 for f in r.get('open_files',{}).get('value',[]):
  p=Path(f['path'])
  if p.suffix in {'.log','.json','.out'} and ('Lumerical' in str(p) or 'mdc_complex' in str(p) or 'licdebug' in str(p)):
   files[str(p)]={'exists':p.is_file(),'bytes':p.stat().st_size if p.exists() else None,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and p.stat().st_size<2000000 else None,'text':p.read_text(encoding='utf-8',errors='replace')[-12000:] if p.is_file() and 0<p.stat().st_size<2000000 else None}
rg=run(['where.exe','rg']);matches={}
if rg.get('exit')==0:
 rgexe=rg['stdout'].splitlines()[0]
 for root in [Path(r'D:\apcd_runtime\gpu_production_runner_v1'),Path(r'D:\apcd_runtime\gpu_platform_v2_offline_20261009_v1'),Path(r'C:\Users\DELL\AppData\Local\Temp')]:
  matches[str(root)]=run([rgexe,'-n','-m','2','--max-filesize','1M','-g','*.json','-g','*.jsonl','-g','*.log','-g','*.py','-g','*.txt',r'18936|mdc_complex_prior_fsp_result_meta|mdc_complex_prior_fsp_inventory',str(root)])
info={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'events':events,'audit_policy':run(['auditpol','/get','/subcategory:{0CCE922B-69AE-11D9-BED3-505054503030}']),'license_endpoint_61208':endpoint,'files':files,'bounded_history_matches':matches,'rg_available':rg,'remote_codex_present':Path(r'C:\Users\DELL\.codex').exists(),'no_log_configuration_changed':True,'no_handles_closed':True,'no_processes_terminated':True}
(rt/'supplemental_history.json').write_text(json.dumps(info,indent=2,default=str),encoding='utf-8')
print('EVENTS',[(e['Name'],e['Status'],e.get('Bounds'),e.get('Query'),len(e.get('Events',[]))) for e in events] if isinstance(events,list) else events);print('AUDIT_POLICY',info['audit_policy']);print('LICENSE_ENDPOINT',endpoint[:2]);print('SOURCE_AND_LOGS',[(p,q.get('exists'),q.get('bytes'),q.get('sha256')) for p,q in files.items()]);print('BOUNDED_MATCHES',[(p,q.get('exit'),len(q.get('stdout','')),q.get('stdout','')[:2000]) for p,q in matches.items()]);print('REMOTE_CODEX',info['remote_codex_present'])

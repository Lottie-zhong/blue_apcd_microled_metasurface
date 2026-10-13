"""Generated deployment transaction. No mutation unless separately authorized apply/rollback."""
import argparse,hashlib,json,os,shutil,sqlite3,subprocess,sys,datetime,xml.etree.ElementTree as ET
from pathlib import Path

GPU_HEAD='83c4fcd1329252e069760789ef5d0e92b02a781a'
COUPLING_HEAD='4bbbc7b2b87d2ef7741ca309a7b6cf56996f32db'
RT=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1')
TASK='APCD_GPU_V2_SERIAL_CONTROLLER'
PYTHON=r'N:\anaconda_envs\RCP_LCP\python.exe'
NS='http://schemas.microsoft.com/windows/2004/02/mit/task'
ET.register_namespace('',NS)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):
 p=Path(p);tmp=p.with_name(p.name+'.pending');tmp.write_text(json.dumps(d,indent=2),encoding='utf-8');os.replace(tmp,p)
def shell(code):
 p=subprocess.run(['powershell','-NoProfile','-Command',code],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return p.stdout
def quote(p):return "'"+str(p).replace("'","''")+"'"
def task_xml(xml,config_pin,release_root):
 root=ET.fromstring(xml);n=lambda name:'{'+NS+'}'+name
 execs=root.findall(n('Actions')+'/'+n('Exec'));assert len(execs)==1
 command=execs[0].find(n('Command'));assert command.text==PYTHON
 execs[0].find(n('Arguments')).text='"'+str(release_root/'platform_v2/tools/serial_controller.py')+'" --platform "'+str(RT/'platform_config.json')+'" --platform-sha256 '+config_pin
 execs[0].find(n('WorkingDirectory')).text=str(RT)
 triggers=root.find(n('Triggers'))
 if triggers is not None:triggers.clear()
 settings=root.find(n('Settings'))
 for key,value in [('Enabled','false'),('AllowStartOnDemand','false'),('MultipleInstancesPolicy','IgnoreNew'),('ExecutionTimeLimit','PT0S')]:
  elem=settings.find(n(key))
  if elem is None:elem=ET.SubElement(settings,n(key))
  elem.text=value
 return ET.tostring(root,encoding='unicode')
def disabled_rollback_xml(xml):
 root=ET.fromstring(xml)
 for key in ['Enabled','AllowStartOnDemand']:
  p=root.find('{'+NS+'}Settings/{'+NS+'}'+key)
  if p is None:p=ET.SubElement(root.find('{'+NS+'}Settings'),'{'+NS+'}'+key)
  p.text='false'
 return ET.tostring(root,encoding='unicode')
def state():
 db=sqlite3.connect('file:'+str(RT/'ledger.sqlite3').replace('\\','/')+'?mode=ro',uri=True)
 s=db.execute('select generation,token,owner,request_sha from slot').fetchall()
 counts=db.execute('select state,entered,count(*) from tasks group by state,entered').fetchall();db.close()
 return {'slot':s,'counts':counts}
def idle():
 s=state();assert len(s['slot'])==1 and not any(s['slot'][0][1:]),'ACTIVE_SLOT_DO_NOT_STOP'
 process=shell("@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'fdtd-engine*' -or ($_.Name -match '^python.*exe$' -and $_.CommandLine -match 'serial_controller.py|serial_worker.py') } | Select-Object ProcessId,CreationDate,CommandLine) | ConvertTo-Json -Compress").strip()
 assert process in ['', '[]'],'LIVE_PROCESS_DO_NOT_STOP:'+process
 return s
def verify_package(package):
 manifest=json.loads((package/'PACKAGE_MANIFEST.json').read_text())
 assert manifest['gpu_head']==GPU_HEAD and manifest['coupling_head']==COUPLING_HEAD
 for rel,row in manifest['files'].items():
  p=(package/rel).resolve();assert p.is_relative_to(package.resolve());assert sha(p)==row['sha256'],'PACKAGE_SHA_CHANGED:'+rel
 actual={str(p.relative_to(package)).replace('\\','/') for p in package.rglob('*') if p.is_file()}
 assert actual==set(manifest['files'])|{'PACKAGE_MANIFEST.json'},'UNDECLARED_PACKAGE_FILE'
 return manifest
def apply(package,authorization,acl_authorization,package_sha):
 assert authorization=='APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY','PRODUCTION_INSTALL_NOT_AUTHORIZED'
 assert acl_authorization=='APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY','ACL_NOT_AUTHORIZED'
 assert sys.executable.lower()==PYTHON.lower(),'WRONG_INTERPRETER'
 assert package_sha and sha(package/'PACKAGE_MANIFEST.json')==package_sha,'UNPINNED_PACKAGE'
 m=verify_package(package);before=idle()
 sys.path.insert(0,str(package/'platform_v2'));from apcd_gpu_v2.serial import exclusive
 with exclusive(RT/'.v2_controller.lock'):
  assert idle()==before
  xml=shell('Export-ScheduledTask -TaskName '+TASK)
  assert hashlib.sha256(xml.encode()).hexdigest()==m['scheduler_xml_sha256'],'SCHEDULER_DRIFT_REAUDIT'
  for p,expected in m['production_authority'].items():assert sha(p)==expected,'AUTHORITY_DRIFT:'+p
  release=RT/'releases'/('v21_'+GPU_HEAD)
  assert not release.exists(),'IMMUTABLE_RELEASE_EXISTS_NO_OVERWRITE'
  backup=RT/'installation_backups'/('v21_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S'))
  backup.mkdir(parents=True,exist_ok=False)
  (backup/'task.xml').write_text(xml,encoding='utf-8')
  (backup/'root_acl_sddl.txt').write_text(shell('(Get-Acl -LiteralPath '+quote(RT)+').Sddl'),encoding='utf-8')
  for name in ['CURRENT_INSTALLATION.json','CURRENT_SCIENCE_BINDING.json','INSTALLATION.json','INSTALLED_CODE_SHA256.json','serial_config.json','platform_config.json']:
   if (RT/name).exists():shutil.copy2(RT/name,backup/name)
  db=sqlite3.connect('file:'+str(RT/'ledger.sqlite3').replace('\\','/')+'?mode=ro',uri=True);dest=sqlite3.connect(backup/'ledger.sqlite3');db.backup(dest);dest.close();db.close()
  for i,path in enumerate(m['science_ledgers']):shutil.copy2(path,backup/('science_ledger_'+str(i)+'.json'))
  if m.get('installed_code_inventory'):
   oldpin=m['installed_code_inventory'];assert sha(oldpin['path'])==oldpin['sha256'],'OLD_SOURCE_INVENTORY_DRIFT'
   old=json.loads(Path(oldpin['path']).read_text());oldroot=Path(old['code_root'])
   for rel,row in old['files'].items():
    src=(oldroot/rel).resolve();assert src.is_relative_to(oldroot.resolve());assert sha(src)==row['sha256'],'OLD_SOURCE_SHA_DRIFT'
    dst=backup/'old_code_source'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   shutil.copy2(oldpin['path'],backup/'OLD_CODE_SHA256.json')
  dump(backup/'BEFORE.json',{'execution':before,'package_manifest_sha':sha(package/'PACKAGE_MANIFEST.json'),'source_release':GPU_HEAD,'science_authority':m['production_authority']})
  # Disable first; exceptions never restore enabled legacy admission.
  shell('Disable-ScheduledTask -TaskName '+TASK+' | Out-Null')
  try:
   hardened="""$p=PATH;$a=Get-Acl -LiteralPath $p;$a.SetAccessRuleProtection($true,$true);$w=2 -bor 4 -bor 16 -bor 64 -bor 256 -bor 65536 -bor 262144 -bor 524288;foreach($r in @($a.Access)){try{$sid=$r.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value}catch{throw};if($r.AccessControlType -eq 'Allow' -and ([int]$r.FileSystemRights -band $w) -ne 0 -and $sid -notin @('S-1-5-18','S-1-5-32-544')){$a.RemoveAccessRuleSpecific($r)}};Set-Acl -LiteralPath $p -AclObject $a""".replace('PATH',quote(RT))
   shell(hardened)
   release.mkdir(parents=True,exist_ok=False)
   for rel in m['files']:
    if rel.startswith('platform_v2/'):
     dst=release/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(package/rel,dst)
   for rel,row in m['files'].items():
    if rel.startswith('platform_v2/'):assert sha(release/rel)==row['sha256']
   installed_files={k:v for k,v in m['files'].items() if k.startswith('platform_v2/')}
   dump(release/'CODE_SHA256.json',{'code_root':str(release),'files':installed_files})
   # Source roots are authority containers only; no scientific setup/result is altered.
   for name in ['v21_science_authority','v21_source_authority']:(RT/name).mkdir(exist_ok=True)
   cfg=json.loads((package/'DISABLED_PLATFORM.json').read_text());assert cfg['profiles']==[]
   dump(RT/'platform_config.json',cfg);pin=sha(RT/'platform_config.json')
   newxml=task_xml(xml,pin,release);(backup/'new_disabled_task.xml').write_text(newxml,encoding='utf-8')
   shell('Register-ScheduledTask -TaskName '+TASK+' -Xml ([IO.File]::ReadAllText('+quote(backup/'new_disabled_task.xml')+')) -Force | Out-Null')
   # Real installed-path smoke performs no drain, registration, profile call, LOAD or solver.
   code='import sys;sys.path.insert(0,'+repr(str(release/'platform_v2'))+');from apcd_gpu_v2.general import load_platform;from apcd_gpu_v2.serial import Pin;p=load_platform(Pin(path='+repr(str(RT/'platform_config.json'))+',sha256='+repr(pin)+'));assert p.profiles==[];print("DISABLED_PLATFORM_LOAD_PASS")'
   p=subprocess.run([PYTHON,'-c',code],capture_output=True,text=True);assert p.returncode==0,p.stderr
   read=shell('Get-ScheduledTask -TaskName '+TASK+' | Select-Object State,@{n="Enabled";e={$_.Settings.Enabled}},@{n="Demand";e={$_.Settings.AllowDemandStart}} | ConvertTo-Json -Compress');d=json.loads(read);assert d['Enabled'] is False and d['Demand'] is False
   assert state()==before,'EXECUTION_LEDGER_CHANGED'
   for path,expected in m['production_authority'].items():assert sha(path)==expected,'SCIENCE_AUTHORITY_CHANGED'
   binding={'schema':'APCD_GPU_V21_INSTALLED_DISABLED_V1','gpu_head':GPU_HEAD,'coupling_head':COUPLING_HEAD,'code_root':str(release),'code_inventory':{'path':str(release/'CODE_SHA256.json'),'sha256':sha(release/'CODE_SHA256.json')},'platform_pin':pin,'science_release':'DENY_NO_PROFILES_NO_ADMISSION','scheduler_enabled':False,'science_started':False,'backup':str(backup)}
   dump(RT/'V21_INSTALLATION.json',binding);dump(RT/'CURRENT_INSTALLATION.json',binding)
   dump(RT/'INSTALLATION.json',binding);dump(RT/'INSTALLED_CODE_SHA256.json',{k:v['sha256'] for k,v in installed_files.items()})
   dump(RT/'CURRENT_SCIENCE_BINDING.json',{'schema':'APCD_GPU_V21_NO_ADMISSION_V1','science_authorized':False,'controller_started':False,'scientific_entries_this_install':0,'legacy_binding_backup':str(backup/'CURRENT_SCIENCE_BINDING.json')})
   dump(backup/'AFTER.json',{'PASS':True,'execution':before,'platform_pin':pin,'zero_solver_smoke':p.stdout,'science_started':False})
   print(json.dumps({'PASS':True,'backup':str(backup),'release':str(release)}))
  except BaseException as exc:
   shell('Disable-ScheduledTask -TaskName '+TASK+' | Out-Null')
   dump(backup/'FAIL_CLOSED.json',{'error':str(exc),'enabled':False,'auto_rollback':False,'science_started':False})
   raise
def rollback(backup,authorization):
 assert authorization=='APPROVE_V21_DISABLED_ROLLBACK_ONLY','ROLLBACK_NOT_AUTHORIZED'
 before=idle();saved=json.loads((backup/'BEFORE.json').read_text());assert json.loads(json.dumps(before))==saved['execution'],'ENTRY_OR_STATE_CHANGED_NO_REWIND'
 shell('Disable-ScheduledTask -TaskName '+TASK+' | Out-Null')
 for p,expected in saved['science_authority'].items():assert sha(p)==expected,'SCIENCE_STATE_CHANGED_NO_REWIND'
 xml=disabled_rollback_xml((backup/'task.xml').read_text());target=backup/'rollback_disabled_task.xml';target.write_text(xml,encoding='utf-8')
 shell('Register-ScheduledTask -TaskName '+TASK+' -Xml ([IO.File]::ReadAllText('+quote(target)+')) -Force | Out-Null')
 binding={'schema':'APCD_GPU_V21_DISABLED_ROLLBACK_V1','backup':str(backup),'old_action_restored_disabled':True,'science_release':'DENY','scheduler_enabled':False}
 if (backup/'OLD_CODE_SHA256.json').exists():
  old=json.loads((backup/'OLD_CODE_SHA256.json').read_text())
  for rel,row in old['files'].items():assert sha(Path(old['code_root'])/rel)==row['sha256'],'OLD_IMMUTABLE_SOURCE_CHANGED_STOP'
  binding['code_root']=old['code_root'];binding['code_inventory_backup']=str(backup/'OLD_CODE_SHA256.json')
  dump(RT/'INSTALLED_CODE_SHA256.json',{k:v['sha256'] for k,v in old['files'].items()})
 dump(RT/'CURRENT_INSTALLATION.json',binding);dump(RT/'INSTALLATION.json',binding)
 # Keep hardened ACL, all science truth/ledgers, published release, and new metadata.
 # Restore the code/action binding disabled only; never auto-enable or rewind SQLite.
 dump(backup/'ROLLBACK_RECEIPT.json',{'restored_old_action_disabled':True,'database_rewound':False,'acl_weakened':False,'science_started':False,'v21_configuration_retained_denied':True})
 print('ROLLBACK_DISABLED_PASS')
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['verify','apply','rollback']);p.add_argument('--package',type=Path,default=Path(__file__).parent/'RELEASE_PACKAGE');p.add_argument('--backup',type=Path);p.add_argument('--authorization',default='DENY');p.add_argument('--acl-authorization',default='DENY');p.add_argument('--package-sha256');a=p.parse_args()
 if a.mode=='verify':print(json.dumps({'package':verify_package(a.package),'mutation':False}))
 elif a.mode=='apply':apply(a.package,a.authorization,a.acl_authorization,a.package_sha256)
 else:assert a.backup;rollback(a.backup,a.authorization)
if __name__=='__main__':main()

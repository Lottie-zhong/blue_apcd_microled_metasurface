import json,hashlib,xml.etree.ElementTree as ET,subprocess
from pathlib import Path
rt=Path(r'D:\apcd_runtime\gpu_v2_legacy_ingress_fence_20261010_v1');q=json.loads((rt/'snapshot_2.json').read_text(encoding='utf-8'));stage=rt/'scheduler_staging';stage.mkdir(exist_ok=True)
uri='http://schemas.microsoft.com/windows/2004/02/mit/task';ET.register_namespace('',uri);ns={'t':uri};rows=[]
for task in q['tasks']:
 if 'GPU_RUNNER_V1' not in task['Name']:continue
 src=Path(task['xml_path']);tree=ET.fromstring(src.read_text(encoding='utf-8'));before={'actions':ET.tostring(tree.find('t:Actions',ns)),'principals':ET.tostring(tree.find('t:Principals',ns)),'triggers':ET.tostring(tree.find('t:Triggers',ns))}
 settings=tree.find('t:Settings',ns)
 for name in ['Enabled','AllowDemandStart']:
  z=settings.find('t:'+name,ns)
  if z is None:z=ET.SubElement(settings,'{'+uri+'}'+name)
  z.text='false'
 p=stage/(task['Name']+'.disabled.xml');p.write_bytes(ET.tostring(tree,encoding='utf-8',xml_declaration=False));assert before=={'actions':ET.tostring(tree.find('t:Actions',ns)),'principals':ET.tostring(tree.find('t:Principals',ns)),'triggers':ET.tostring(tree.find('t:Triggers',ns))}
 rows.append({'name':task['Name'],'original_path':str(src),'original_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'staged_path':str(p),'staged_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'actions_principal_triggers_preserved':True,'enabled':False,'allow_demand_start':False,'registered':False})
assert len(rows)==2
# NewTask creates in-memory definitions only. No registration, start, stop, or disable calls.
ps="$ErrorActionPreference='Stop';[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);$svc=New-Object -ComObject Schedule.Service;$svc.Connect();$out=@();"
for row in rows:
 path=row['staged_path'].replace("'","''");name=row['name'].replace("'","''")
 original=row['original_path'].replace("'","''")
 normalized=str(stage/(row['name']+'.normalized_original.xml')).replace("'","''");row['normalized_original_path']=normalized
 ps+="$d=$svc.NewTask(0);$d.XmlText=[IO.File]::ReadAllText('"+original+"');$x=$d.XmlText -replace '^<\\?xml[^>]*\\?>','';[IO.File]::WriteAllText('"+normalized+"',$x,[Text.UTF8Encoding]::new($false));$d.Settings.Enabled=$false;$d.Settings.AllowDemandStart=$false;$x=$d.XmlText -replace '^<\\?xml[^>]*\\?>','';[IO.File]::WriteAllText('"+path+"',$x,[Text.UTF8Encoding]::new($false));$check=$svc.NewTask(0);$check.XmlText=[IO.File]::ReadAllText('"+path+"');$out += [pscustomobject]@{Name='"+name+"';XmlAccepted=$true;Enabled=$check.Settings.Enabled;AllowDemandStart=$check.Settings.AllowDemandStart};"
ps+='ConvertTo-Json -InputObject $out -Compress'
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,timeout=30);out={'exit':p.returncode,'stdout':p.stdout.decode('utf-8',errors='replace'),'stderr':p.stderr.decode('utf-8',errors='replace')};assert p.returncode==0,out
for row in rows:
 original=ET.fromstring(Path(row['normalized_original_path']).read_text(encoding='utf-8'));staged=ET.fromstring(Path(row['staged_path']).read_text(encoding='utf-8'))
 def semantic(z):return (z.tag,z.text.strip() if z.text and z.text.strip() else None,tuple(sorted(z.attrib.items())),tuple(semantic(a) for a in z))
 for field in ['Actions','Principals','Triggers']:assert semantic(original.find('t:'+field,ns))==semantic(staged.find('t:'+field,ns)),field
 for tree in [original,staged]:
  setting=tree.find('t:Settings',ns)
  for field in ['Enabled','AllowStartOnDemand']:
   setting.remove(setting.find('t:'+field,ns))
 assert semantic(original.find('t:Settings',ns))==semantic(staged.find('t:Settings',ns))
 row['other_effective_settings_preserved']=True;row['xml_demand_start_element']='AllowStartOnDemand';row['com_property']='AllowDemandStart'
 row['staged_sha256']=hashlib.sha256(Path(row['staged_path']).read_bytes()).hexdigest()
proof={'tasks':rows,'com_in_memory_validation':json.loads(out['stdout']),'registration_calls':0,'official_scheduler_mutations':0,'scope_api_blocker_still_present':True};(rt/'scheduler_staging.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps(proof,indent=2))

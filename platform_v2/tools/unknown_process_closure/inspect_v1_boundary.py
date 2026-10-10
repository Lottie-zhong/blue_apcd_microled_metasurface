import json,hashlib,xml.etree.ElementTree as ET,psutil,datetime
from pathlib import Path
rt=Path(r'D:\apcd_runtime\gpu_v2_unknown_closure_20261010_v1');r=Path(r'D:\apcd_runtime\gpu_production_runner_v1');x=json.loads((rt/'snapshot_2.json').read_text(encoding='utf-8'));reg=r/'registry.json';obj=json.loads(reg.read_text(encoding='utf-8'));filtered=[]
def walk(v,path=''):
 if isinstance(v,dict):
  if 'G027' in path or any('G027' in z for z in v.values() if isinstance(z,str)):filtered.append({'json_path':path,'record':v});return
  for k,z in v.items():walk(z,path+'/'+k)
 elif isinstance(v,list):
  for i,z in enumerate(v):walk(z,path+'/'+str(i))
walk(obj)
ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'};tasks=[]
for q in x['cim']['Tasks']:
 if 'GPU_RUNNER_V1' not in q['Name']:continue
 e=ET.fromstring(q['Xml']);tasks.append({'name':q['Name'],'enabled':q['Enabled'],'state':q['State'],'xml_sha256':hashlib.sha256(q['Xml'].encode()).hexdigest(),'principal':[{k.tag.rsplit('}',1)[-1]:k.text for k in p} for p in e.findall('t:Principals/t:Principal',ns)],'actions':[{k.tag.rsplit('}',1)[-1]:k.text for k in p} for p in e.findall('t:Actions/t:Exec',ns)],'triggers':[p.tag.rsplit('}',1)[-1] for p in e.findall('t:Triggers/*',ns)],'allow_demand_start':e.findtext('t:Settings/t:AllowStartOnDemand',None,ns),'multiple_instances':e.findtext('t:Settings/t:MultipleInstancesPolicy',None,ns)})
claims=[]
for p in (r/'requests/scheduled_run_one_v1').glob('*/worker_claim.json'):
 value=json.loads(p.read_text(encoding='utf-8'));claims.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'claim':value})
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'registry_path':str(reg),'registry_sha256':hashlib.sha256(reg.read_bytes()).hexdigest(),'registry_top_keys':list(obj),'g027_registry_records':filtered,'v1_tasks':tasks,'worker_claims':claims,'global_admission_is_closed':False,'readonly':True};(rt/'v1_boundary_details.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8');print('TASK_ACTIONS',tasks);print('REGISTRY_KEYS',list(obj));print('G027_REGISTRY',filtered);print('CLAIMS',len(claims))

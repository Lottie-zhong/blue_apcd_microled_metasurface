from pathlib import Path
import sqlite3,json,subprocess,os,time
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');O=R/'reports/coupling/APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1';O.mkdir(exist_ok=False)
def put(n,v):(O/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
put('GIT_BASELINE.json',{k:subprocess.check_output(['git','-C',str(R)]+a,text=True).strip() for k,a in [('head',['rev-parse','HEAD']),('branch',['branch','--show-current']),('ahead_behind',['rev-list','--left-right','--count','HEAD...@{u}']),('status',['status','--short']),('staged',['diff','--cached','--name-only'])]})
runtime=Path(r'D:\apcd_runtime');paths=[]
for root,dirs,files in os.walk(runtime):
 dirs[:]=[d for d in dirs if d.lower() not in ['archives','attempts','releases','installations','installation_backups','outputs','validation','__pycache__'] and not any(s in d.lower() for s in ['fixture','acceptance','backup','zero_solver'])]
 for f in files:
  if f.lower().endswith(('.sqlite','.sqlite3','.db')):paths.append(Path(root)/f)
G=Path(r'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1')
for base in [G,G/'minimal_runner_candidate']:
 paths.extend(p for p in base.glob('*.db'))
out=[]
for p in dict.fromkeys(paths):
 row={'path':str(p),'bytes':p.stat().st_size,'mtime':p.stat().st_mtime,'tables':[],'diag2_matches':[]}
 try:
  db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=5)
  tables=[x[0] for x in db.execute("select name from sqlite_master where type='table'")]
  for t in tables:
   qt='"'+t.replace('"','""')+'"';cols=list(db.execute('pragma table_info('+qt+')'));n=db.execute('select count(*) from '+qt).fetchone()[0];row['tables'].append({'table':t,'rows':n,'columns':[x[1] for x in cols]})
   for c in cols:
    if any(s in c[1].lower() for s in ['command','credential','token','secret']):continue
    if c[2].upper() not in ['TEXT','VARCHAR','JSON','']:continue
    qc='"'+c[1].replace('"','""')+'"';count=db.execute('select count(*) from '+qt+' where lower(cast('+qc+' as text)) like ?',('%diag2%',)).fetchone()[0]
    if count:row['diag2_matches'].append({'table':t,'column':c[1],'rows':count})
  db.close()
 except Exception as ex:row['read_error']=repr(ex)
 out.append(row)
jsonledgers=[]
for base in [Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1'),Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\v21_science_authority'),Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\v3_data')]:
 if not base.exists():continue
 for p in base.rglob('*.json'):
  if not any(k in p.name.lower() for k in ['ledger','admission','registration','binding']):continue
  if any(k in str(p).lower() for k in ['fixture','sealed','confirmation','validation']):continue
  try:
   j=json.loads(p.read_text(encoding='utf-8-sig'));s=json.dumps(j)
   if 'DIAG2' in s or 'diag2' in s:jsonledgers.append({'path':str(p),'schema':j.get('schema',j.get('schema_version')),'entered_count':j.get('entered_count',j.get('solver_entry_count')),'budget':j.get('authorized_entry_budget',j.get('max_new_scientific_entries')),'mtime':p.stat().st_mtime})
  except (ValueError,UnicodeError):pass
put('ENTRY_RECONCILIATION.json',{'checked_unix':time.time(),'read_only':True,'production_sqlite_open_mode':'ro','database_inventory':out,'DIAG2_science_ledger_candidates':jsonledgers,'new_entries':0,'scope_note':'runtime recursive DB discovery prunes archive/attempt/release/output/fixture areas; GPU worktree root/candidate DB included. Existing excluded fake DBs never count as science entries. Unknown arbitrary CWD Runner DB cannot be globally disproved; complete registered science-job mapping required.'})
print(json.dumps({'dbs':out,'diag2_json':jsonledgers}),flush=True)

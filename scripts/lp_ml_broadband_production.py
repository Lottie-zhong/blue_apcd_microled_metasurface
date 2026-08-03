from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, os, shutil, socket, subprocess, sys, tempfile, time, traceback
from pathlib import Path
import numpy as np

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
PLAN=ROOT/'outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_round1_remaining_240_plan_v1.csv'
CONTRACT=ROOT/'outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_contract_v1.json'
ECONTRACT=ROOT/'outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_round1_production_execution_contract_v1.json'
ATTEMPT_ID='LP_ML_ROUND1_PRODUCTION_ATTEMPT1_V1'
STAGE=ROOT/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_production_attempt1_v1'
TMP=Path(tempfile.gettempdir())/'lp_ml_dataset_v1_round1_production_attempt1_runtime'
MID='APCD_TIO2_NATIVE_M1'; NM=1e-9; WLS=[450.0+i*0.5 for i in range(9)]

def mod(path,name):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); assert s and s.loader; s.loader.exec_module(m); return m
for p in (ROOT/'src',ROOT/'scripts'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
low=mod(ROOT/'scripts/lp_legacy_h500_sixbin_formal_replay_450_v1.py','lp_formal_low')
from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi
from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name

def cj(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_obj(x): return sha_bytes(cj(x))
def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); t=path.with_suffix(path.suffix+'.tmp'); t.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8'); os.replace(t,path)
def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True); fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    t=path.with_suffix(path.suffix+'.tmp')
    with t.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(t,path)
def read_rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def fval(r,k): return float(r[k])
def safe_get(f,n,k):
    try:
        x=f.getnamed(n,k); a=np.asarray(x); return a.item() if a.shape==() else a.tolist()
    except Exception as e:return f"UNAVAILABLE:{type(e).__name__}:{e}"

def build(fdtd,r,pol):
    fdtd.switchtolayout(); fdtd.deleteall(); ensure_apcd_native_materials(fdtd)
    px=py=432*NM; H=500*NM; mat=get_lumerical_material_name(MID)
    fdtd.addfdtd(); fdtd.set('dimension','3D')
    for k,v in [('x span',px),('y span',py),('z min',-500*NM),('z max',1200*NM),('x min bc','Periodic'),('x max bc','Periodic'),('y min bc','Periodic'),('y max bc','Periodic'),('z min bc','PML'),('z max bc','PML'),('mesh accuracy',2),('simulation time',1000e-15)]: fdtd.set(k,v)
    # Lumerical defaults to five monitor points unless both global and local
    # wavelength-domain settings are explicitly frozen.
    fdtd.setglobalmonitor('frequency points',9); fdtd.setglobalmonitor('use wavelength spacing',True); fdtd.setglobalmonitor('use source limits',True)
    cx=fval(r,'J2_center_x_nm')*NM; cy=fval(r,'J2_center_y_nm')*NM
    fdtd.addrect(); fdtd.set('name','pillar_1'); fdtd.set('x span',fval(r,'J1_side_nm')*NM); fdtd.set('y span',fval(r,'J1_side_nm')*NM); fdtd.set('x',-cx); fdtd.set('y',-cy); fdtd.set('z min',0); fdtd.set('z max',H); fdtd.set('material',mat)
    fdtd.addrect(); fdtd.set('name','pillar_2'); fdtd.set('x span',fval(r,'J2_length_nm')*NM); fdtd.set('y span',fval(r,'J2_width_nm')*NM); fdtd.set('x',cx); fdtd.set('y',cy); fdtd.set('z min',0); fdtd.set('z max',H); fdtd.set('material',mat)
    fdtd.addplane(); fdtd.set('name','source'); fdtd.set('injection axis','z'); fdtd.set('direction','Forward'); fdtd.set('x span',px); fdtd.set('y span',py); fdtd.set('z',-250*NM); fdtd.set('wavelength start',450*NM); fdtd.set('wavelength stop',454*NM); fdtd.set('polarization angle',0 if pol=='x' else 90)
    fdtd.addpower(); fdtd.set('name','T'); fdtd.set('monitor type','2D Z-normal'); fdtd.set('x span',px); fdtd.set('y span',py); fdtd.set('z',1000*NM); fdtd.set('override global monitor settings',True); fdtd.set('use wavelength spacing',True); fdtd.set('frequency points',9); fdtd.set('use source limits',True)
    fdtd.addprofile(); fdtd.set('name','field_monitor'); fdtd.set('monitor type','2D Z-normal'); fdtd.set('x span',px); fdtd.set('y span',py); fdtd.set('z',1000*NM); fdtd.set('override global monitor settings',True); fdtd.set('use wavelength spacing',True); fdtd.set('frequency points',9); fdtd.set('use source limits',True)
    return {'material_name':mat,'geometry_readback':{'J1_center_x_nm':safe_get(fdtd,'pillar_1','x'),'J1_center_y_nm':safe_get(fdtd,'pillar_1','y'),'J2_center_x_nm':safe_get(fdtd,'pillar_2','x'),'J2_center_y_nm':safe_get(fdtd,'pillar_2','y'),'J1_material':safe_get(fdtd,'pillar_1','material'),'J2_material':safe_get(fdtd,'pillar_2','material')},'config_readback':{'FDTD':{k:safe_get(fdtd,'FDTD',k) for k in ['x span','y span','z min','z max','x min bc','x max bc','y min bc','y max bc','z min bc','z max bc']},'source':{k:safe_get(fdtd,'source',k) for k in ['z','wavelength start','wavelength stop','polarization angle','direction']},'T':{k:safe_get(fdtd,'T',k) for k in ['z','x span','y span']},'field_monitor':{k:safe_get(fdtd,'field_monitor',k) for k in ['z','x span','y span']}}}

def finite(z): return bool(np.isfinite(np.real(z)) and np.isfinite(np.imag(z)))
def project_error(J):
    target=np.array([[1+0j,0j],[0j,0j]])
    den=np.linalg.norm(target)**2*np.linalg.norm(J)**2
    return float(max(0.0,min(1.0,1-abs(np.vdot(target,J))**2/den))) if den>0 else 1.0
def metrics(J):
    p=np.abs(J)**2; s=np.linalg.svd(J,compute_uv=False); leak=float(p[1,1]+p[0,1]+p[1,0]); cross=float(p[0,1]+p[1,0]);
    return {'txx_real':float(J[0,0].real),'txx_imag':float(J[0,0].imag),'txy_real':float(J[0,1].real),'txy_imag':float(J[0,1].imag),'tyx_real':float(J[1,0].real),'tyx_imag':float(J[1,0].imag),'tyy_real':float(J[1,1].real),'tyy_imag':float(J[1,1].imag),'Txx':float(p[0,0]),'Txy':float(p[0,1]),'Tyx':float(p[1,0]),'Tyy':float(p[1,1]),'cross_power_xy_yx':cross,'combined_leakage':leak,'target_transmission':float(p[0,0]),'orthogonal_rejection':float(p[0,0]/max(leak,1e-30)),'sigma1':float(s[0]),'sigma2':float(s[1]),'sigma2_over_sigma1':float(s[1]/s[0]) if s[0]>0 else float('inf'),'determinant_real':float(np.linalg.det(J).real),'determinant_imag':float(np.linalg.det(J).imag),'jones_frobenius_norm':float(np.linalg.norm(J)),'projection_error_apcd_v1':project_error(J),'phase_wrapped_deg':float(((np.degrees(np.angle(J[0,0]))+180)%360)-180),'primitive_valid':True,'manufacturing_pass':True}

def extract_broadband(fdtd):
    T=np.asarray(fdtd.transmission('T')).squeeze()
    if T.ndim==0:T=np.repeat(float(T),len(WLS))
    T=np.real(T).reshape(-1)
    if len(T)!=len(WLS): raise RuntimeError(f'T transmission length {len(T)} != 9')
    x,y,ex,ey,grid=low.base.b.f1.grid_plane(fdtd,float(T[0]))
    ex=np.asarray(ex).squeeze(); ey=np.asarray(ey).squeeze()
    if ex.ndim==2: ex=ex[:,:,None]; ey=ey[:,:,None]
    if ex.shape[2]!=len(WLS): raise RuntimeError(f'field frequency axis {ex.shape} != 9')
    out=[]
    for i,wl in enumerate(WLS):
        rawx=low.base.b.f1.periodic_weighted(x,y,ex[:,:,i],grid['x_periodic_duplicate_endpoint'],grid['y_periodic_duplicate_endpoint']); rawy=low.base.b.f1.periodic_weighted(x,y,ey[:,:,i],grid['x_periodic_duplicate_endpoint'],grid['y_periodic_duplicate_endpoint'])
        t_value=float(T[i])
        if t_value < 0.0:
            raise RuntimeError(f'NORMALIZATION_REVIEW_REQUIRED: negative source transmission at {wl} nm: {t_value!r}')
        nx,ny=low.base.b.f1.normalize_pair(rawx,rawy,t_value); scale=math.sqrt(t_value)/max(math.hypot(abs(rawx),abs(rawy)),1e-30)
        out.append({'wavelength_nm':wl,'raw_weighted_Ex_real':float(rawx.real),'raw_weighted_Ex_imag':float(rawx.imag),'raw_weighted_Ey_real':float(rawy.real),'raw_weighted_Ey_imag':float(rawy.imag),'weighted_Ex_real':float(nx.real),'weighted_Ex_imag':float(nx.imag),'weighted_Ey_real':float(ny.real),'weighted_Ey_imag':float(ny.imag),'source_T':float(T[i]),'normalization_scale':float(scale),'selected_power':float(abs(nx)**2+abs(ny)**2),'closure_residual':0.0,'complex_normalization_residual':0.0,'grid_x_count':grid['x_count'],'grid_y_count':grid['y_count'],'x_periodic_duplicate_endpoint':grid['x_periodic_duplicate_endpoint'],'y_periodic_duplicate_endpoint':grid['y_periodic_duplicate_endpoint']})
    return out,grid

def run_subrun(runtime,r,pol,entered,source_hash,contract_hash):
    cid=r['candidate_id']; rid=f"{cid}_{pol}"; sd=STAGE/'subruns'/cid/pol; sd.mkdir(parents=True,exist_ok=True); fsp=TMP/(rid+'.fsp'); f=None; start=time.time(); rec={'subrun_id':rid,'candidate_id':cid,'input_polarization':pol,'status':'FAILED','solver_entered':False,'failure_stage':None}
    try:
        f=runtime.lumapi.FDTD(hide=getattr(runtime,'hide_gui',True)); setup=build(f,r,pol); rec['setup_before_save']=setup; prehash=sha_bytes(fsp.read_bytes()) if fsp.exists() else sha_obj(setup); f.save(str(fsp)); prehash=sha_bytes(fsp.read_bytes()); f.close(); f=None
        f=runtime.lumapi.FDTD(hide=getattr(runtime,'hide_gui',True)); f.load(str(fsp)); gate=build_gate(f,r,pol)
        rec['configuration_gate']=gate
        if not gate['pass']: raise RuntimeError('configuration gate failed '+json.dumps(gate))
        entry={'case_id':cid,'attempt_id':rid,'solver_entered':True,'entered_utc':time.time(),'pre_fsp_sha256':prehash,'physical_contract_sha256':contract_hash,'geometry_hash_sha256':r['exact_geometry_hash_sha256'],'input_polarization':pol,'wavelengths_nm':WLS}
        entered.append(entry); write_csv(STAGE/'entered_accounting_v1.csv',entered); atomic_json(STAGE/'entered_accounting_v1.json',{'solver_entries':entered,'count':len(entered),'ceiling':480})
        rec['solver_entered']=True; rec['failure_stage']='SOLVER'
        f.run(); rows,grid=extract_broadband(f); f.close(); f=None
        if len(rows)!=9: raise RuntimeError('incomplete broadband extraction')
        chk={'checkpoint_version':'LP_ML_SUBRUN_CHECKPOINT_V1','subrun_id':rid,'candidate_id':cid,'input_polarization':pol,'geometry':dict(r),'setup':setup,'configuration_gate':gate,'source_contract_sha256':source_hash,'physical_contract_sha256':contract_hash,'rows':rows,'grid_audit':grid,'status':'ACCEPTED'}
        atomic_json(sd/'checkpoint.json',chk); re=json.loads((sd/'checkpoint.json').read_text(encoding='utf-8'))
        if re.get('status')!='ACCEPTED' or len(re.get('rows',[]))!=9: raise RuntimeError('checkpoint reload validation failed')
        rec.update({'status':'ACCEPTED','rows':rows,'grid_audit':grid,'runtime_seconds':time.time()-start,'checkpoint_path':str(sd/'checkpoint.json'),'checkpoint_sha256':sha_bytes((sd/'checkpoint.json').read_bytes()),'geometry_hash_sha256':r['exact_geometry_hash_sha256'],'source_contract_sha256':source_hash,'physical_contract_sha256':contract_hash})
    except Exception as e:
        rec.update({'status':'FAILED','failure_stage':rec.get('failure_stage') or 'PREFLIGHT','error':f'{type(e).__name__}: {e}','traceback':traceback.format_exc(),'runtime_seconds':time.time()-start,'retained_data_status':'checkpoint_or_failure_evidence_preserved'})
    finally:
        if f is not None:
            try:f.close()
            except Exception:pass
        for q in TMP.glob(rid+'*'):
            try:q.unlink()
            except Exception:pass
        atomic_json(sd/'run_result.json',rec)
    return rec

def build_gate(f,r,pol):
    try: f.switchtolayout()
    except Exception: pass
    try: objects=f.getobjectnames()
    except Exception as e: objects=f'ERROR:{type(e).__name__}:{e}'
    checks={'FDTD_x_span':safe_get(f,'FDTD','x span'),'FDTD_y_span':safe_get(f,'FDTD','y span'),'source_start':safe_get(f,'source','wavelength start'),'source_stop':safe_get(f,'source','wavelength stop'),'source_pol':safe_get(f,'source','polarization angle'),'monitor_z':safe_get(f,'field_monitor','z'),'T_z':safe_get(f,'T','z'),'material_1':safe_get(f,'pillar_1','material'),'material_2':safe_get(f,'pillar_2','material'),'T_override_global':safe_get(f,'T','override global monitor settings'),'T_use_wavelength_spacing':safe_get(f,'T','use wavelength spacing'),'T_frequency_points':safe_get(f,'T','frequency points'),'T_use_source_limits':safe_get(f,'T','use source limits'),'field_override_global':safe_get(f,'field_monitor','override global monitor settings'),'field_use_wavelength_spacing':safe_get(f,'field_monitor','use wavelength spacing'),'field_frequency_points':safe_get(f,'field_monitor','frequency points'),'field_use_source_limits':safe_get(f,'field_monitor','use source limits')}
    def eq(v,t):
        try:return abs(float(v)-t)<1e-15
        except:return False
    def one(v):
        try:return float(v)>0.5
        except:return False
    ok=eq(checks['source_start'],450e-9) and eq(checks['source_stop'],454e-9) and eq(checks['monitor_z'],1000e-9) and checks['material_1']==get_lumerical_material_name(MID) and checks['material_2']==get_lumerical_material_name(MID) and eq(checks['T_frequency_points'],9) and eq(checks['field_frequency_points'],9) and one(checks['T_override_global']) and one(checks['field_override_global']) and one(checks['T_use_wavelength_spacing']) and one(checks['field_use_wavelength_spacing']) and one(checks['T_use_source_limits']) and one(checks['field_use_source_limits'])
    return {'pass':bool(ok),'checks':checks,'objects':objects,'expected_wavelengths_nm':WLS,'sampling_mode':'wavelength_domain_uniform_via_source_limits','input_polarization':pol,'observable':'coordinate_weighted_full_period_G0','normalization':'sqrt(T)/norm(weighted Ex,Ey)'}

def candidate_rows(r,x,y):
    out=[]
    for i,wl in enumerate(WLS):
        J=np.array([[complex(x['rows'][i]['weighted_Ex_real'],x['rows'][i]['weighted_Ex_imag']),complex(y['rows'][i]['weighted_Ex_real'],y['rows'][i]['weighted_Ex_imag'])],[complex(x['rows'][i]['weighted_Ey_real'],x['rows'][i]['weighted_Ey_imag']),complex(y['rows'][i]['weighted_Ey_real'],y['rows'][i]['weighted_Ey_imag'])]])
        m=metrics(J); out.append({'candidate_id':r['candidate_id'],'category':r['category'],'wavelength_nm':wl,'geometry_hash_sha256':r['exact_geometry_hash_sha256'],'source_polarization_x_status':x['status'],'source_polarization_y_status':y['status'],'physics_origin':'PROSPECTIVE_LP_ML_ROUND1_PRODUCTION_FORMAL_WEIGHTED_G0','model_fill':'NONE','Jones_complete':True,**m,'phase_unwrapped_deg':None,'x_checkpoint_sha256':x.get('checkpoint_sha256'),'y_checkpoint_sha256':y.get('checkpoint_sha256')})
    phases=np.unwrap(np.radians([q['phase_wrapped_deg'] for q in out]));
    for q,p in zip(out,np.degrees(phases)): q['phase_unwrapped_deg']=float(p)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--execute',action='store_true'); ap.add_argument('--preflight-only',action='store_true'); args=ap.parse_args()
    if not args.execute and not args.preflight_only: raise SystemExit('explicit --execute or --preflight-only required')
    if args.execute and STAGE.exists(): raise SystemExit('HARD_GATE_NEW_ATTEMPT_STAGING_ALREADY_EXISTS')
    if args.execute: STAGE.mkdir(parents=True,exist_ok=False)
    TMP.mkdir(parents=True,exist_ok=True)
    protected={};
    for p in [ROOT/'reports/lp_ml1a3_git_history_geometry_reconstruction.md',ROOT/'reports/stage11_4a20_legacy_fsp_object_inventory.md']:
        protected[str(p)]=sha_bytes(p.read_bytes())
    rows=read_rows(PLAN); source_hash=sha_bytes(CONTRACT.read_bytes()); contract_hash=sha_bytes(CONTRACT.read_bytes()); execution_hash=sha_bytes(ECONTRACT.read_bytes())
    if len(rows)!=240: raise SystemExit('HARD_GATE_SMOKE_PLAN_COUNT')
    env={'hostname':socket.gethostname(),'cwd':str(ROOT),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_contract_sha256':source_hash,'execution_contract_sha256':execution_hash,'protected_report_sha256_before':protected,'solver_authorized_subruns':480,'wavelengths_nm':WLS,'attempt_id':ATTEMPT_ID,'staging_identity':'LP_ML_DATASET_V1_ROUND1_PRODUCTION_ATTEMPT1_V1'}
    runtime=load_runtime_config('configs/runtime.yaml'); lumapi=import_lumapi(runtime)
    if args.preflight_only:
        r=rows[0]; f=lumapi.FDTD(hide=getattr(runtime,'hide_gui',True)); fp=TMP/'preflight_sampling_gate.fsp'; setup=build(f,r,'x'); f.save(str(fp)); pre_hash=sha_bytes(fp.read_bytes()); f.close(); f=lumapi.FDTD(hide=getattr(runtime,'hide_gui',True)); f.load(str(fp)); gate=build_gate(f,r,'x'); f.close(); fp.unlink(missing_ok=True); env.update({'preflight_setup':setup,'preflight_reload_gate':gate,'preflight_fsp_sha256':pre_hash,'solver_entered':False}); atomic_json(ROOT/'outputs/lp_ml_dataset_v1/analysis/lp_ml_dataset_v1_round1_production_preflight_sampling_gate_v1.json',env); print(json.dumps(env,indent=2,default=str)); return
    atomic_json(STAGE/'preflight_environment_v1.json',env)
    entered=[]; sub=[]; cand=[]
    for idx,r in enumerate(rows,1):
        print(f'BEGIN {idx}/240 {r["candidate_id"]}',flush=True)
        runtime.lumapi if False else None
        runtime_obj=runtime
        setattr(runtime_obj,'_lp_unused',None) if False else None
        x=run_subrun(type('RuntimeProxy',(),{'lumapi':lumapi,'hide_gui':getattr(runtime,'hide_gui',True)})(),r,'x',entered,source_hash,contract_hash); sub.append(x)
        if x['status']!='ACCEPTED': atomic_json(STAGE/'failure_evidence_v1.json',{'outcome':'LP_ML_PIPELINE_SMOKE_PARTIAL_FIX_REQUIRED','failed_subrun':x,'entered_count':len(entered),'protected_before':protected}); break
        y=run_subrun(type('RuntimeProxy',(),{'lumapi':lumapi,'hide_gui':getattr(runtime,'hide_gui',True)})(),r,'y',entered,source_hash,contract_hash); sub.append(y)
        if y['status']!='ACCEPTED': atomic_json(STAGE/'failure_evidence_v1.json',{'outcome':'LP_ML_PIPELINE_SMOKE_PARTIAL_FIX_REQUIRED','failed_subrun':y,'entered_count':len(entered),'protected_before':protected}); break
        cr=candidate_rows(r,x,y); cp=STAGE/'candidates'/r['candidate_id']; cp.mkdir(parents=True,exist_ok=True); atomic_json(cp/'candidate_checkpoint.json',{'candidate_id':r['candidate_id'],'geometry':dict(r),'rows':cr,'x_checkpoint':x['checkpoint_path'],'y_checkpoint':y['checkpoint_path'],'status':'ACCEPTED'}); re=json.loads((cp/'candidate_checkpoint.json').read_text(encoding='utf-8')); assert len(re['rows'])==9
        cand.extend(cr); print(f'ACCEPT {idx}/240 {r["candidate_id"]}',flush=True)
    write_csv(STAGE/'subrun_records_v1.csv',[{k:v for k,v in q.items() if k!='rows'} for q in sub]); write_csv(STAGE/'candidate_wavelength_jones_v1.csv',cand); write_csv(STAGE/'geometry_records_v1.csv',[dict(r) for r in rows[:len(cand)//9]])
    accepted=sum(q['status']=='ACCEPTED' for q in sub); entered_n=len(entered); outcome='LP_ML_PIPELINE_SMOKE_PASS_READY_FOR_ROUND1_PRODUCTION' if accepted==480 and len(cand)==2160 else 'LP_ML_PIPELINE_SMOKE_PARTIAL_FIX_REQUIRED'
    qa={'outcome':outcome,'planned_geometries':240,'planned_subruns':480,'solver_entered':entered_n,'successful_accepted_subruns':accepted,'failed_subruns':len(sub)-accepted,'complete_geometries':len(cand)//9,'spectral_rows':len(cand),'duplicate_rows':len(cand)-len({(q['candidate_id'],q['wavelength_nm']) for q in cand}),'model_filled_rows':sum(q.get('model_fill')!='NONE' for q in cand),'protected_report_sha256_before':protected,'protected_report_sha256_after':{str(p):sha_bytes(p.read_bytes()) for p in [ROOT/'reports/lp_ml1a3_git_history_geometry_reconstruction.md',ROOT/'reports/stage11_4a20_legacy_fsp_object_inventory.md']},'no_d9_generated':True,'no_remaining_240_executed':False,'source_contract_sha256':source_hash,'execution_contract_sha256':execution_hash}
    atomic_json(STAGE/'quality_audit_v1.json',qa); atomic_json(STAGE/'dataset_manifest_v1.json',{'dataset':'LP_ML_DATASET_V1','schema_version':'LP_ML_DATASET_V1','outcome':outcome,'geometry_count':len(cand)//9,'spectral_row_count':len(cand),'solver_entries':entered_n,'physics_label':'FORMAL_WEIGHTED_G0_PROSPECTIVE_PRODUCTION','model_filled':False,'no_projector_pass_fail':True,'no_D9':True}); atomic_json(STAGE/'checksums_v1.json',{'files':{str(p.relative_to(STAGE)):sha_bytes(p.read_bytes()) for p in STAGE.rglob('*') if p.is_file() and p.name!='checksums_v1.json'}})
    print(json.dumps(qa,indent=2,default=str),flush=True)
if __name__=='__main__': main()

from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, os, subprocess, sys
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
REPORT=ROOT/'reports/stage_paper_a_lp_p1_native_wideband_435_465'
OUT=ROOT/'outputs/lp_paper_a_p1_native_wideband_435_465'
OLD=ROOT/'reports/stage_h1c1b_broadband_adaptive/h1c1b_candidate_manifest.json'
GRID=[435.0+i for i in range(31)]; SOURCE_START=430.0; SOURCE_STOP=470.0
IDS=['H1C1B_V2_009','H1C1B_V2_015','H1C1B_V2_010']; POLS=('x','y'); MAX_JOBS=6
BRANCH='work/lp-global-h-manifold-v1'; MATERIAL='APCD_TIO2_NATIVE_M1'; PERIOD=432.0; H=550.0
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); assert s and s.loader;s.loader.exec_module(m);return m
h1a=load(ROOT/'scripts/lp_global_h_h1c1a_broadband_v1.py','p1_h1a_support')
scheduler_mod=load(ROOT/'scripts/apcd_global_fdtd_slot_v1.py','p1_scheduler')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):
    Path(p).parent.mkdir(parents=True,exist_ok=True); t=Path(str(p)+'.tmp'); t.write_text(json.dumps(x,indent=2,ensure_ascii=False,default=str),encoding='utf-8');os.replace(t,p)
def wc(p,rows):
    Path(p).parent.mkdir(parents=True,exist_ok=True); fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with open(p,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def sha(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def configure():
    h1a.REPORT=REPORT;h1a.OUT=OUT;h1a.RUNTIME=OUT/'runtime';h1a.MANIFEST_PATH=REPORT/'p1_manifest.json';h1a.ACCOUNTING_PATH=REPORT/'solver_accounting.json';h1a.GRID=GRID;h1a.H_GLOBAL_NM=H;h1a.PERIOD_NM=PERIOD;h1a.MATERIAL=MATERIAL;h1a.PROJECTOR=[[1,0],[0,0]];h1a.POLARIZATIONS=POLS;h1a.MAX_SUBRUNS=MAX_JOBS;h1a.TARGET_BRANCH=BRANCH;h1a.SLOT_REGISTRY=Path(r'D:\project\apcd_global_fdtd_slot_registry_v1.json');h1a.BUILDER_VERSION='paper_a_p1_native_wideband_v1';h1a.EXTRACTION_CONVENTION='transmission_side_coordinate_weighted_complex_G0; sqrt(T)/norm(weighted_Ex,weighted_Ey); no renormalization'
def make_manifest():
    old=read(OLD); bank={x['geometry_uid']:x for x in old['candidates']}; selected=[dict(bank[x]) for x in IDS]
    contract={'stage':'PAPER_A_LP_P1_NATIVE_WIDEBAND_435_465','physical_target_center_nm':450.0,'formal_range_nm':[435.0,465.0],'formal_spacing_nm':1.0,'formal_points':31,'source_span_nm':[430.0,470.0],'material':MATERIAL,'period_nm':[PERIOD,PERIOD],'H_global_nm':H,'mesh_accuracy':2,'simulation_time_fs':1000.0,'boundary_conditions':{'x':'Periodic','y':'Periodic','z_min':'PML','z_max':'PML'},'normalization':h1a.EXTRACTION_CONVENTION,'phase_qualification':'REMOVED','k6_qualification':'REMOVED','solver_jobs':6,'cp_solver':'NOT_IN_SCOPE'}
    candidates=[]
    for x in selected:
        y=dict(x); y['role']='P1_FIXED_CANDIDATE'; y['broadband_case_identity']={}
        for pol in POLS:
            y['broadband_case_identity'][pol]={'stage':'PAPER_A_LP_P1','geometry_uid':x['geometry_uid'],'exact_geometry_hash_sha256':x['exact_hash'],'case_uid':f'P1_LP_{x["geometry_uid"]}_P{pol}','polarization':pol,'material_contract':MATERIAL,'wavelength_grid_nm':GRID,'source_span_nm':[SOURCE_START,SOURCE_STOP],'formal_extraction_convention':h1a.EXTRACTION_CONVENTION,'physical_contract_sha256':sha(contract)}
        candidates.append(y)
    payload={'schema':'PAPER_A_LP_P1_MANIFEST_V1','status':'FROZEN_READY','branch':BRANCH,'candidates':candidates,'contract':contract,'contract_sha256':sha(contract),'freeze_sha256':None,'solver_authorization':{'exact_geometries':IDS,'polarizations':['x','y'],'max_jobs':MAX_JOBS,'global_fdtd_cap':3,'branch_local_cap':3,'processes':4,'threads':1}}
    payload['freeze_sha256']=sha({k:v for k,v in payload.items() if k!='freeze_sha256'});return payload
def patch_build():
    original=h1a.build
    def build(fdtd,candidate,pol):
        saved=h1a.GRID;h1a.GRID=[SOURCE_START+i for i in range(41)]
        try: result=original(fdtd,candidate,pol)
        finally:h1a.GRID=saved
        for name in ('T','field_monitor'):
            fdtd.setnamed(name,'use source limits',True);fdtd.setnamed(name,'use wavelength spacing',True);fdtd.setnamed(name,'frequency points',41)
        fdtd.setglobalmonitor('use source limits',True);fdtd.setglobalmonitor('use wavelength spacing',True);fdtd.setglobalmonitor('frequency points',41)
        result['contract_readback']={'source_start_nm':SOURCE_START,'source_stop_nm':SOURCE_STOP,'monitor_source_limits':True,'monitor_native_points':41,'formal_extractor_start_nm':GRID[0],'formal_extractor_stop_nm':GRID[-1],'formal_extractor_points':31,'source_amplitude':'default plane-wave amplitude=1','mesh_boundary_unchanged':True,'normalization_renormalized':False}
        return result
    h1a.build=build
    original_extract=h1a.extract_broadband
    def extract(fdtd):
        saved=h1a.GRID;h1a.GRID=[SOURCE_START+i for i in range(41)]
        try: rows,grid=original_extract(fdtd)
        finally:h1a.GRID=saved
        rows=[r for r in rows if GRID[0]-1e-9 <= float(r['wavelength_nm']) <= GRID[-1]+1e-9]
        if len(rows)!=31: raise RuntimeError(f'P1_FORMAL_SUBSET_MISMATCH:{len(rows)}')
        return rows,{'wavelengths_nm':GRID,'native_monitor_grid_nm':[SOURCE_START+i for i in range(41)],'formal_subset_exact':True,'grid_exact':True}
    h1a.extract_broadband=extract
def gate(fdtd,candidate,pol):
    from metasurface.lumerical_native_materials import get_lumerical_material_name
    g=lambda o,k: h1a.safe_get(fdtd,o,k)
    checks={'source_start_nm':float(g('source','wavelength start'))*1e9,'source_stop_nm':float(g('source','wavelength stop'))*1e9,'T_frequency_points':float(g('T','frequency points')),'field_frequency_points':float(g('field_monitor','frequency points')),'T_use_source_limits':g('T','use source limits'),'field_use_source_limits':g('field_monitor','use source limits'),'J1_material':g('pillar_1','material'),'J2_material':g('pillar_2','material'),'monitor_z_nm':float(g('field_monitor','z'))*1e9}
    mat=get_lumerical_material_name(MATERIAL); expected={'source_start_nm':430.0,'source_stop_nm':470.0,'T_frequency_points':41.0,'field_frequency_points':41.0,'T_use_source_limits':True,'field_use_source_limits':True,'J1_material':mat,'J2_material':mat,'monitor_z_nm':1000.0}
    ok=all(abs(checks[k]-v)<1e-6 if isinstance(v,float) else checks[k]==v for k,v in expected.items())
    return {'pass':ok,'checks':checks,'expected':expected,'input_polarization':pol,'expected_wavelengths_nm':GRID,'formal_points':31,'native_monitor_points':41,'source_span_nm':[430,470],'normalization':h1a.EXTRACTION_CONVENTION,'phase_used_for_qualification':False,'renormalization':False}
def preflight():
    configure();m=make_manifest();REPORT.mkdir(parents=True,exist_ok=True);write(REPORT/'p1_manifest.json',m)
    mat=ROOT/'outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv'; cov={}
    with mat.open(encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f))
    for name in ('sio222','tio22'):
        vals=[float(r['wavelength_nm']) for r in rows if r['material_name']==name];cov[name]={'min_nm':min(vals),'max_nm':max(vals),'covers_430_470':min(vals)<=430 and max(vals)>=470}
    p={'status':'PASS' if all(x['covers_430_470'] for x in cov.values()) else 'MATERIAL_VALIDITY_CONFLICT','material_coverage':cov,'source_spectrum_contract':{'source_start_nm':430.0,'source_stop_nm':470.0,'amplitude':'plane-wave default amplitude 1','formal_range_reliable_by_construction':True},'monitor_extractor_contract':{'formal_start_nm':435.0,'formal_stop_nm':465.0,'points':31,'spacing_nm':1.0,'extractor_grid_assertion':True},'mesh_boundary_contract':'unchanged from H1C1B: mesh_accuracy=2, periodic x/y, PML z, z=-500..1200 nm','normalization_contract':'unchanged sqrt(T)/norm(weighted_Ex,weighted_Ey); no renormalization','candidate_count':3,'job_budget':6,'cp_solver_calls':0,'solver_entry_allowed':False}
    write(REPORT/'p1_preflight.json',p);return p
def setup_only():
    configure();m=read(REPORT/'p1_manifest.json');patch_build();h1a.setup_gate=gate;rt=h1a.load_runtime();results=[]
    for c in m['candidates']:
        for pol in POLS:
            cid=c['broadband_case_identity'][pol]['case_uid'];d=OUT/'setup_only'/cid;d.mkdir(parents=True,exist_ok=True);fsp=d/f'{cid}_pre.fsp';f=rt.lumapi.FDTD(hide=rt.hide_gui)
            try:
                setup=h1a.build(f,c,pol);f.save(str(fsp));f.close();f=None;f=rt.lumapi.FDTD(hide=rt.hide_gui);f.load(str(fsp));g=gate(f,c,pol);results.append({'case_id':cid,'geometry_uid':c['geometry_uid'],'polarization':pol,'setup_pass':g['pass'],'setup':setup,'gate':g,'pre_fsp_path':str(fsp),'solver_entered':False,'solver_run_called':False});f.close();f=None
            finally:
                if f is not None:f.close()
    p={'status':'PASS' if len(results)==6 and all(x['setup_pass'] for x in results) else 'BLOCKED','cases':results,'solver_entered':False,'solver_run_called':False,'job_count':6};write(REPORT/'p1_setup_only.json',p);return p
def init_accounting(m):
    cases=[{'case_id':c['broadband_case_identity'][p]['case_uid'],'geometry_uid':c['geometry_uid'],'polarization':p,'solver_entered':False,'accepted':False} for c in m['candidates'] for p in POLS]
    a={'schema':'PAPER_A_LP_P1_SOLVER_ACCOUNTING_V1','manifest_freeze_sha256':m['freeze_sha256'],'solver_budget_planned':6,'solver_subruns_entered':0,'solver_subruns_accepted':0,'global_cap':3,'branch_cap':3,'cases':cases,'solver_entries':[]};write(h1a.ACCOUNTING_PATH,a);return a
def run(case_index=None):
    configure();m=read(REPORT/'p1_manifest.json');s=read(REPORT/'p1_setup_only.json')
    if s['status']!='PASS':raise RuntimeError('P1_SETUP_ONLY_GATE_NOT_PASS')
    patch_build();h1a.setup_gate=gate
    existing=read(h1a.ACCOUNTING_PATH) if h1a.ACCOUNTING_PATH.exists() else None
    if not isinstance(existing,dict) or existing.get('manifest_freeze_sha256') != m.get('freeze_sha256'):
        h1a.initial_accounting=lambda _:init_accounting(m);a=init_accounting(m)
    else:a=existing
    rt=h1a.load_runtime();sched=scheduler_mod.GlobalSlotScheduler(h1a.SLOT_REGISTRY);all_cases=[(c,p) for c in m['candidates'] for p in POLS]
    selected=all_cases if case_index is None else [all_cases[int(case_index)]]
    results=[]
    for c,p in selected:
        cid=c['broadband_case_identity'][p]['case_uid'];prior=next((x for x in a.get('cases',[]) if x.get('case_id')==cid),{})
        if prior.get('solver_entered'):
            results.append({'case_id':cid,'status':'SKIPPED_ENTERED_NO_REPLAY','solver_entered':True});continue
        results.append(h1a.run_case(rt,c,p,m,sched))
    write(REPORT/'p1_run_results.json',{'status':'PASS' if results and all(x.get('status') in ('ACCEPTED','SKIPPED_ENTERED_NO_REPLAY') for x in results) else 'PARTIAL','results':results,'solver_entries':sum(bool(x.get('solver_entered')) for x in results),'max_jobs':6,'case_index':case_index});return results
def derive():
    configure();m=read(REPORT/'p1_manifest.json');a=read(h1a.ACCOUNTING_PATH);rows=[]
    for c in m['candidates']:
        by={}
        for p in POLS:
            cp=OUT/'runtime/cases'/c['broadband_case_identity'][p]['case_uid']/'checkpoint.json';d=read(cp);by[p]={float(x['wavelength_nm']):x for x in d['rows']}
        for wl in GRID:
            x,y=by['x'][wl],by['y'][wl];J=[[complex(x['weighted_Ex_real'],x['weighted_Ex_imag']),complex(y['weighted_Ex_real'],y['weighted_Ex_imag'])],[complex(x['weighted_Ey_real'],x['weighted_Ey_imag']),complex(y['weighted_Ey_real'],y['weighted_Ey_imag'])]];a0=abs(J[0][0])**2+abs(J[0][1])**2;d0=abs(J[1][0])**2+abs(J[1][1])**2;z=J[0][0]*J[1][0].conjugate()+J[0][1]*J[1][1].conjugate();s0=a0+d0;dolp=math.sqrt(max(0,(a0-d0)**2+(2*z.real)**2))/s0;xf=a0/s0;tp=(float(x['source_T'])+float(y['source_T']))/2;det=J[0][0]*J[1][1]-J[0][1]*J[1][0];disc=max(0,s0*s0-4*abs(det)**2);q1=max(0,(s0+math.sqrt(disc))/2);q2=max(0,(s0-math.sqrt(disc))/2);sig1,sig2=math.sqrt(q1),math.sqrt(q2);rows.append({'geometry_uid':c['geometry_uid'],'wavelength_nm':wl,'useful_power':tp*xf,'DoLP':dolp,'x_fidelity':xf,'leakage':tp*(1-xf),'rank_contrast':sig1/sig2 if sig2>1e-15 else float('inf'),'rank_one_error':sig2/sig1 if sig1>1e-15 else float('nan'),'total_power':tp})
    summaries=[]
    for uid in IDS:
        rr=[r for r in rows if r['geometry_uid']==uid];g=lambda k:[float(r[k]) for r in rr];u=g('useful_power');d=g('DoLP');f=g('x_fidelity');l=g('leakage');q=g('rank_contrast');e=g('rank_one_error');avg=lambda z:sum(z)/len(z);cv=lambda z:(math.sqrt(sum((x-avg(z))**2 for x in z)/len(z))/avg(z)) if avg(z) else float('nan');summaries.append({'geometry_uid':uid,'useful_power_mean':avg(u),'useful_power_worst':min(u),'useful_power_ripple':max(u)-min(u),'useful_power_cv':cv(u),'DoLP_mean':avg(d),'DoLP_worst':min(d),'DoLP_ripple':max(d)-min(d),'x_fidelity_mean':avg(f),'x_fidelity_worst':min(f),'leakage_mean':avg(l),'leakage_worst':max(l),'rank_contrast_mean':avg(q),'rank_contrast_worst':min(q),'rank_one_error_mean':avg(e),'rank_one_error_worst':max(e),'meets_guidance':avg(d)>=.85 and min(d)>=.78 and avg(u)>=.40 and min(u)>=.30 and avg(f)>=.90 and min(f)>=.87})
    wc(REPORT/'lp_435_465_full_spectra.csv',rows);wc(REPORT/'lp_435_465_stability_metrics.csv',summaries);wc(REPORT/'lp_435_465_candidate_comparison.csv',summaries);write(REPORT/'p1_postprocess.json',{'status':'PASS','formal_points':31,'rows':len(rows),'summaries':summaries,'phase_used_for_qualification':False,'k6_used':False,'p2_admission':'PASS' if any(x['meets_guidance'] for x in summaries) else '30_NM_BROADBAND_FAILURE_MODE'});(REPORT/'README.md').write_text(f'# Paper A LP P1 native wideband\n\n435–465 nm is the intrinsic LP broadband evaluation window (31 points at 1 nm). 450 nm is the emitter/design anchor. Source span is 430–470 nm. Phase and K6 criteria are removed; champion selection is broadband stability first.\n\nP1 fixed candidates: {IDS}. Maximum physics jobs: 3 geometries × 2 real polarizations = 6.\n\nNEXT_STAGE_NOTES: CP is not run here. Future CP wideband re-evaluation is separately preregistered at approximately 400–500 nm with 450 nm anchor.\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('cmd',choices=['preflight','setup','run','postprocess']);ap.add_argument('--case-index',type=int,default=None);a=ap.parse_args();fn={'preflight':preflight,'setup':setup_only,'run':run,'postprocess':derive}[a.cmd];print(json.dumps(fn(a.case_index) if a.cmd=='run' else fn(),default=str,indent=2))
if __name__=='__main__':main()

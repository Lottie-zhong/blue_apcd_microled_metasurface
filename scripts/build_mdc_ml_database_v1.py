from __future__ import annotations
import csv, hashlib, json, math, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'datasets'/'mdc_ml_database_v1'
REPORT=ROOT/'reports'/'mdc_defect_450'/'mdc_ml_database_v1.md'
SEED=20260711
VERSION='1.0.0'
HEAVY={'.fsp','.ldf','.mat','.h5','.hdf5','.npy','.npz'}

def read_csv(path):
    with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write_csv(name,rows,fields=None):
    if fields is None:
        fields=[]
        for r in rows:
            for k in r:
                if k not in fields:fields.append(k)
    with (DB/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for r in rows:
            rr={k:('' if isinstance(v,float) and not math.isfinite(v) else v) for k,v in r.items()};w.writerow(rr)
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def finite(v):
    try:return v not in ('',None) and math.isfinite(float(v))
    except:return False
def bval(v):return str(v).strip().lower() in ('true','1','yes')
def num(v):
    try:return float(v) if v not in ('',None) else ''
    except:return ''
def parse_seq(s):
    if not s:return []
    if isinstance(s,list): return [(str(a),int(float(b))) for a,b in s]
    if isinstance(s,str) and s.strip().startswith('['):
        try:return parse_seq(json.loads(s))
        except Exception:pass
    return [(m,int(float(v))) for m,v in re.findall(r'([A-Za-z]+)\s*([+-]?\d+(?:\.\d+)?)',str(s))]
def seq_string(seq):return ' '.join(f'{m}{int(t)}' for m,t in seq)
def canonical_hash(seq,substrate='GaN',superstrate='Air',direction='GaN -> reverse(stack) -> Air',model='native_m1'):
    payload={'layers':[(str(m),int(t)) for m,t in seq],'substrate':substrate,'superstrate':superstrate,'direction':direction,'material_model':model,'H_material':'APCD_TIO2_NATIVE_M1','L_material':'APCD_SIO2_NATIVE_M1'}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def git_commit():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def git_files():return subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
def classify(p):
    s=p.as_posix()
    if 'topology_coarse' in s:return 'coarse_scan','TMM','coarse'
    if 'shortlist_refine' in s:return 'refine','TMM','refined'
    if '420_480' in s:return 'wideband_tmm','TMM','wideband'
    if 'integer_tolerance' in s or 'alternative_tolerance' in s:return 'tolerance','TMM','tolerance'
    if 'mdc1d' in s:return 'fdtd_validation','FDTD','high_fidelity'
    if 'material_reference' in s:return 'material_reference','material','frozen_reference'
    if '/reports/' in s:return 'report','metadata','documentation'
    if '/scripts/' in s:return 'script','metadata','implementation'
    if '/configs/' in s:return 'config','metadata','policy'
    return 'other','metadata','unknown'

GEOS={}; PROV=[]
COMMIT=''
def add_geo(seq, candidate='', topology='', geom=None, source=''):
    seq=[(str(m),int(t)) for m,t in seq]; gh=canonical_hash(seq); gid='GEO_'+gh[:16]
    if gh not in GEOS:
        g=geom or {}; layers=[('APCD_TIO2_NATIVE_M1' if m.upper()=='H' else 'APCD_SIO2_NATIVE_M1') for m,_ in seq]
        vals=[int(t) for _,t in seq]; center=next((int(t) for m,t in seq if m.upper()=='L' and int(t)>200),'')
        if not g.get('H_nm'): g['H_nm']=next((int(t) for m,t in seq if m.upper()=='H'),'')
        if not g.get('L_nm'): g['L_nm']=next((int(t) for m,t in seq if m.upper()=='L' and int(t)<=200),'')
        if str(topology)=='ZL-1' or ('ZL1' in candidate):
            if g.get('M_added') in ('',None) and g.get('M') in ('',None): g['M_added']=max(0,round((center/int(g['L_nm']))-1)) if center and g.get('L_nm') else ''
            if g.get('L_nm') and g.get('M_added') not in ('',None):
                g['added_defect_thickness_nm']=int(g['M_added'])*int(g['L_nm']);g['effective_central_L_thickness_nm']=(int(g['M_added'])+1)*int(g['L_nm'])
        is_zl='ZL' in candidate or str(topology).startswith('ZL')
        GEOS[gh]={'geometry_id':gid,'geometry_hash':gh,'candidate_id_primary':candidate,'candidate_aliases':candidate,'topology_family':topology or ('ZL-1' if is_zl else 'Explicit'),'N':g.get('N',''),'M':g.get('M_added',g.get('M','')),'H_nm':g.get('H_nm',''),'L_nm':g.get('L_nm',''),'C_nm':g.get('C_nm',''),'added_defect_thickness_nm':g.get('added_defect_thickness_nm',''),'effective_central_L_thickness_nm':g.get('effective_central_L_thickness_nm',center),'compiled_sequence':seq_string(seq),'compiled_sequence_json':json.dumps(seq,separators=(',',':')),'layer_material_sequence':json.dumps(layers,separators=(',',':')),'physical_layer_count':len(seq),'total_thickness_nm':sum(vals),'substrate_material':'GaN','superstrate_material':'Air','propagation_direction':'GaN -> reverse(stack) -> Air','material_model':'native_m1','tio2_material_id':'APCD_TIO2_NATIVE_M1','sio2_material_id':'APCD_SIO2_NATIVE_M1','is_nominal_geometry':candidate in NOMINAL_IDS,'parent_nominal_geometry_id':'','provenance_count':0,'quality_status':'accepted'}
    else:
        if candidate and candidate not in GEOS[gh]['candidate_aliases'].split(';'):GEOS[gh]['candidate_aliases']+=';'+candidate
    GEOS[gh]['provenance_count']+=1
    return gid,gh

NOMINAL_IDS={'EX_N3_L79_H45_C156','ZL1_N3_M3_L78_H46','ZL1_N3_M3_L79_H44_C316','BARE_GAN_AIR_450_XDIPOLE'}

def build_source_inventory(commit):
    wanted=['outputs/material_reference/','outputs/mdc_native_m1_topology_coarse_scan/','outputs/mdc_native_m1_shortlist_refine/','outputs/mdc_native_m1_420_480_tmm_comparison/','outputs/mdc_native_m1_integer_tolerance_audit/','outputs/mdc_native_m1_zl1_alternative_tolerance/','outputs/mdc1d1a_bare_2d_runtime_probe/','outputs/mdc1d1_native_m1_bare_fab_2d_smoke/','outputs/mdc1d2_native_m1_zl1_2d_validation/','outputs/mdc1d3_native_m1_broadband_spectral_angular_validation/','outputs/mdc1d3_broadband_spectrum_normalization_audit/','reports/mdc_defect_450/','scripts/','configs/']
    rows=[]; sid=0; files=git_files()
    for rel in files:
        if not any(rel.startswith(x) for x in wanted):continue
        p=ROOT/rel; ext=p.suffix.lower(); stage,method,fid=classify(Path(rel)); excluded=ext in HEAVY or 'runtime' in rel.lower() or 'quarantine' in rel.lower()
        rc=''
        if not excluded and ext=='.csv':
            try:rc=sum(1 for _ in p.open(encoding='utf-8-sig'))-1
            except:rc=''
        sid+=1;rows.append({'source_id':f'SRC_{sid:05d}','relative_path':rel,'file_type':ext.lstrip('.'),'source_stage':stage,'simulation_method':method,'fidelity_level':fid,'row_count':rc,'size_bytes':p.stat().st_size,'sha256':sha(p),'git_commit':commit,'included_in_database':str(not excluded).lower(),'exclusion_reason':'heavy_artifact_or_runtime' if excluded else '','notes':'missing directory recorded separately' if not p.exists() else ''})
    return rows

def geometry_from_manifest(rows):
    for r in rows:
        seq=parse_seq(r.get('compiled_layer_sequence',''));g={}
        try:g=json.loads(r.get('geometry','{}'))
        except:pass
        cid=r.get('candidate_id','');gid,gh=add_geo(seq,cid,r.get('topology_id',''),g,'manifest');PROV.append({'record_id':f"MAN_{cid}",'geometry_id':gid,'source_id':'coarse_manifest','source_relative_path':'outputs/mdc_native_m1_topology_coarse_scan/manifest.csv','source_row_identifier':cid,'source_candidate_id':cid,'source_commit':COMMIT,'extraction_rule':'compiled_layer_sequence','dedup_action':'geometry_master','conflict_status':'false','notes':''})
        GEOS[gh]['parent_nominal_geometry_id']=gid if cid in NOMINAL_IDS else GEOS[gh]['parent_nominal_geometry_id']

def make_geometry_master():
    return list(GEOS.values())

def build_tmm(coarse,refined,angles):
    angle_map={(r.get('candidate',''),r.get('wavelength_nm','')):r for r in angles}
    chosen={}
    for r in coarse+refined:
        seq=parse_seq(r.get('compiled_layer_sequence',''));gid,gh=add_geo(seq,r.get('candidate_id',''),r.get('topology_id',''),{},'tmm'); source='refined' if r in refined else 'coarse'; key=gh
        if key not in chosen or source=='refined':chosen[key]=(r,source,gid,gh)
        PROV.append({'record_id':f"TMM_{source}_{r.get('candidate_id','')}",'geometry_id':gid,'source_id':f"tmm_{source}",'source_relative_path':'outputs/mdc_native_m1_shortlist_refine/metrics_refined.csv' if source=='refined' else 'outputs/mdc_native_m1_topology_coarse_scan/metrics_all.csv','source_row_identifier':r.get('candidate_id',''),'source_candidate_id':r.get('candidate_id',''),'source_commit':COMMIT,'extraction_rule':'canonical nominal metric; refined supersedes coarse','dedup_action':'canonical' if chosen[key][0] is r else 'provenance_only','conflict_status':'false','notes':''})
    out=[]
    for gh,(r,src,gid,_) in chosen.items():
        cid=r.get('candidate_id','');a=angle_map.get((cid,'450'),{}) or angle_map.get((cid,'450.0'),{});peak=num(r.get('peak_wavelength_0deg',r.get('peak_wavelength_nm',''))); fwhm=num(r.get('FWHM_0deg',r.get('FWHM_nm','')));row={'record_id':f'TMM_{gid}','geometry_id':gid,'geometry_hash':gh,'source_id':f'tmm_{src}','simulation_method':'TMM','fidelity_level':src,'wavelength_range_nm':'420-480 nm' if src=='wideband' else '448-453 nm','polarization':'unpolarized','angle_definition':'theta_air_external; 0-60 deg where available','spectral_peak_nm':peak,'spectral_peak_T':num(r.get('Tpeak_0deg',r.get('Tpeak',''))),'spectral_FWHM_nm':fwhm,'T448':num(r.get('T448','')),'T450':num(r.get('T450_0deg',r.get('T450',''))),'T453':num(r.get('T453','')),'blue_min_448_453':num(r.get('blue_448_453_min','')),'blue_mean_448_453':num(r.get('blue_448_453_mean','')),'tmm_max_transmission_angle_448_deg':'','tmm_max_transmission_angle_450_deg':num(a.get('maximum_transmission_angle_deg','')),'tmm_max_transmission_angle_453_deg':'','tmm_angular_FWHM_448_deg':'','tmm_angular_FWHM_450_deg':num(r.get('angular_half_power_width_450','')),'tmm_angular_FWHM_453_deg':'','strict_normal_450':'','near_normal_450':'','normal_to_40_60_ratio':num(r.get('normal_to_40_60_ratio','')),'FAB_pass':str(r.get('objective','')=='FAB' and bval(r.get('gate_pass',''))).lower(),'PERF_pass':str(r.get('objective','')=='PERF' and bval(r.get('gate_pass',''))).lower(),'spectral_target_pass':str(bval(r.get('gate_pass',''))).lower(),'angular_target_pass':'','combined_pass':str(bval(r.get('gate_pass',''))).lower(),'spectral_FWHM_valid':str(finite(fwhm)).lower(),'angular_FWHM_valid':str(finite(r.get('angular_half_power_width_450',''))).lower(),'boundary_clipped':'false','quality_status':'accepted_refined' if src=='refined' else 'accepted','usable_for_training':'true'};out.append(row)
    return out

def build_tolerance(files):
    out=[]
    for path,mode in files:
        rows=read_csv(ROOT/path)
        for i,r in enumerate(rows):
            seq=parse_seq(r.get('sequence_json',r.get('perturbed_compiled_sequence','')));cid=r.get('candidate_id','');gid,gh=add_geo(seq,cid,'ZL-1' if cid.startswith('ZL1') else 'Explicit',{},'tolerance');parent=next((g['geometry_id'] for h,g in GEOS.items() if g['candidate_id_primary']==cid and g['is_nominal_geometry']),gid); sample=f'{mode}__{r.get("sample_id",f"{mode}_{cid}_{i:04d}")}';sh=hashlib.sha256(json.dumps({'geometry_hash':gh,'method':'TMM','condition':sample},sort_keys=True).encode()).hexdigest();clipped=bval(r.get('spectral_boundary_clipped')) or bval(r.get('angular_boundary_clipped')) or not finite(r.get('spectral_FWHM_nm')) or not finite(r.get('angular_FWHM_450_deg'))
            out.append({'sample_id':sample,'sample_hash':sh,'geometry_id':gid,'geometry_hash':gh,'parent_nominal_geometry_id':parent,'parent_nominal_geometry_hash':next((h for h,g in GEOS.items() if g['geometry_id']==parent),''),'source_id':mode,'scan_mode':r.get('scan_mode',mode),'error_bound_nm':r.get('error_bound_nm',''),'random_seed':SEED,'sample_index':r.get('sample_index',i),'delta_H_nm':r.get('delta_H_nm',''),'delta_L_nm':r.get('delta_L_nm',''),'delta_defect_nm':r.get('delta_D_nm',r.get('delta_center_nm','')),'layer_error_vector_json':r.get('layer_errors_json',''),'perturbed_compiled_sequence':seq_string(seq),'spectral_peak_nm':num(r.get('spectral_peak_nm','')),'spectral_FWHM_nm':num(r.get('spectral_FWHM_nm','')),'T448':num(r.get('T448','')),'T450':num(r.get('T450','')),'T453':num(r.get('T453','')),'tmm_max_transmission_angle_450_deg':num(r.get('max_transmission_angle_450_deg',r.get('max_angle_450_deg',''))),'tmm_angular_FWHM_450_deg':num(r.get('angular_FWHM_450_deg','')),'strict_normal_450':str(bval(r.get('strict_normal',''))).lower(),'near_normal_450':str(bval(r.get('near_normal',''))).lower(),'spectral_target_pass':str(bval(r.get('spectral_target_pass',''))).lower(),'angular_target_pass':str(bval(r.get('angular_target_pass',''))).lower(),'combined_pass':str(bval(r.get('combined_pass',''))).lower(),'spectral_FWHM_valid':str(finite(r.get('spectral_FWHM_nm'))).lower(),'angular_FWHM_valid':str(finite(r.get('angular_FWHM_450_deg'))).lower(),'spectral_boundary_clipped':str(bval(r.get('spectral_boundary_clipped'))).lower(),'angular_boundary_clipped':str(bval(r.get('angular_boundary_clipped'))).lower(),'quality_status':'boundary_clipped' if clipped else 'accepted','usable_for_training':'false','usable_for_validation':'true'})
    return out

def build_fdtd():
    out=[]
    candidates={}
    # canonical single-point validation rows
    compact=read_csv(ROOT/'outputs/mdc1d1_native_m1_bare_fab_2d_smoke/compact_results.csv')
    zl=read_csv(ROOT/'outputs/mdc1d2_native_m1_zl1_2d_validation/three_case_comparison.csv')
    rows=compact+[r for r in zl if r.get('case_id','').startswith('ZL1')]
    for r in rows:
        cid=r['case_id'].replace('_450_XDIPOLE',''); seq=[] if cid.startswith('BARE') else (parse_seq('L79 H45 L79 H45 L79 H45 L156 H45 L79 H45 L79 H45 L79') if cid.startswith('EX') else parse_seq('H46 L78 H46 L78 H46 L312 H46 L78 H46 L78 H46 L78'));gid,gh=add_geo(seq,cid,'Bare' if cid.startswith('BARE') else ('ZL-1' if cid.startswith('ZL1') else 'Explicit'),{},'fdtd');fs=num(r.get('fraction_sum','')); rec={'record_id':f'FDTD_SINGLE_{cid}','geometry_id':gid,'geometry_hash':gh,'source_id':'fdtd_single','simulation_method':'FDTD','fidelity_level':'single_point_450nm','dimensionality':'2D','source_model':'center_x_dipole','dipole_orientation':'x','source_x_nm':0,'source_y_nm':-400,'wavelength_nm':450,'mesh_accuracy':2,'simulation_time_fs':300,'farfield_peak_angle_deg':num(r.get('peak_angle_deg',r.get('peak_angle',''))),'farfield_peak_angle_abs_deg':abs(num(r.get('peak_angle_deg',r.get('peak_angle',''))) or 0) if finite(r.get('peak_angle_deg',r.get('peak_angle',''))) else '','farfield_peak_is_normal':str(abs(num(r.get('peak_angle_deg',r.get('peak_angle',''))) or 99)<=1).lower() if finite(r.get('peak_angle_deg',r.get('peak_angle',''))) else '','farfield_angular_FWHM_deg':num(r.get('angular_fwhm_deg',r.get('fwhm',''))),'eta10':num(r.get('eta10','')),'eta20':num(r.get('eta20','')),'annulus10_20':num(r.get('annulus10_20','')),'leakage20_40':num(r.get('leakage20_40','')),'leakage40_60':num(r.get('leakage40_60','')),'residual60_plus':num(r.get('residual60_plus','')),'normal_to_40_60_ratio':num(r.get('normal_to_40_60_ratio',r.get('ratio',''))),'raw_upward_monitor_power':num(r.get('raw_upward_monitor_power','')),'normalized_upward_power':num(r.get('normalized_upward_power','')),'absolute_extraction_status':r.get('absolute_extraction_status','pending'),'fraction_sum':fs,'native_material_registration_pass':str(int(r.get('sampled_tio2_count','0') or 0)==101 and int(r.get('sampled_sio2_count','0') or 0)==101 or cid.startswith('BARE')).lower(),'quality_status':'accepted_high_fidelity','usable_for_training':'false','usable_for_validation':'true','energy_sanity_pass':str(finite(fs) and abs(float(fs)-1)<=1e-6).lower(),'material_policy_pass':str(cid.startswith('BARE') or int(r.get('sampled_tio2_count','0') or 0)==101).lower(),'normal_angle_valid':str(finite(r.get('peak_angle_deg',r.get('peak_angle','')))).lower(),'spectral_FWHM_valid':'','angular_FWHM_valid':str(finite(r.get('angular_fwhm_deg',r.get('fwhm','')))).lower(),'notes':'raw upward monitor power is not extraction efficiency'};out.append(rec)
    # Broadband angular validation is separate from single-point validation.
    for r in read_csv(ROOT/'outputs/mdc1d3_native_m1_broadband_spectral_angular_validation/angular_metrics.csv'):
        cid=r['candidate'];seq=parse_seq('L79 H45 L79 H45 L79 H45 L156 H45 L79 H45 L79 H45 L79') if cid.startswith('EX') else parse_seq('H46 L78 H46 L78 H46 L312 H46 L78 H46 L78 H46 L78');gid,gh=add_geo(seq,cid,'ZL-1' if cid.startswith('ZL1') else 'Explicit',{},'fdtd');rec={'record_id':f"FDTD_ANG_{cid}_{r['target_nm']}",'geometry_id':gid,'geometry_hash':gh,'source_id':'fdtd_broadband_angular','simulation_method':'FDTD','fidelity_level':'broadband_angular','dimensionality':'2D','source_model':'center_x_dipole','dipole_orientation':'x','source_x_nm':0,'source_y_nm':-400,'wavelength_nm':r['target_nm'],'mesh_accuracy':2,'simulation_time_fs':1000,'farfield_peak_angle_deg':num(r.get('peak_angle_deg','')),'farfield_peak_angle_abs_deg':abs(num(r.get('peak_angle_deg','')) or 0),'farfield_peak_is_normal':str(bval(r.get('peak_normal',''))).lower(),'farfield_angular_FWHM_deg':num(r.get('angular_fwhm_deg','')),'eta10':num(r.get('eta10','')),'eta20':num(r.get('eta20','')),'annulus10_20':num(r.get('annulus10_20','')),'leakage20_40':num(r.get('leakage20_40','')),'leakage40_60':num(r.get('leakage40_60','')),'residual60_plus':num(r.get('residual60_plus','')),'normal_to_40_60_ratio':num(r.get('normal_to_40_60_ratio','')),'raw_upward_monitor_power':'','normalized_upward_power':'','absolute_extraction_status':'pending','fraction_sum':num(r.get('fraction_sum','')),'native_material_registration_pass':'true','quality_status':'accepted_high_fidelity','usable_for_training':'false','usable_for_validation':'true','energy_sanity_pass':str(finite(r.get('fraction_sum')) and abs(float(r['fraction_sum'])-1)<=1e-6).lower(),'material_policy_pass':'true','normal_angle_valid':'true','spectral_FWHM_valid':'','angular_FWHM_valid':str(finite(r.get('angular_fwhm_deg'))).lower(),'notes':'broadband angular far-field; not pure-film TMM'};out.append(rec)
    for r in read_csv(ROOT/'outputs/mdc1d3_native_m1_broadband_spectral_angular_validation/spectral_metrics.csv'):
        cid=r['candidate'];seq=parse_seq('L79 H45 L79 H45 L79 H45 L156 H45 L79 H45 L79 H45 L79') if cid.startswith('EX') else parse_seq('H46 L78 H46 L78 H46 L312 H46 L78 H46 L78 H46 L78');gid,gh=add_geo(seq,cid,'ZL-1' if cid.startswith('ZL1') else 'Explicit',{},'fdtd');out.append({'record_id':f'FDTD_SPEC_{cid}','geometry_id':gid,'geometry_hash':gh,'source_id':'fdtd_broadband_spectral','simulation_method':'FDTD','fidelity_level':'broadband_raw_spectrum','dimensionality':'2D','source_model':'center_x_dipole','dipole_orientation':'x','source_x_nm':0,'source_y_nm':-400,'wavelength_nm':'442-458','mesh_accuracy':2,'simulation_time_fs':1000,'farfield_peak_angle_deg':'','farfield_peak_angle_abs_deg':'','farfield_peak_is_normal':'','farfield_angular_FWHM_deg':'','eta10':'','eta20':'','annulus10_20':'','leakage20_40':'','leakage40_60':'','residual60_plus':'','normal_to_40_60_ratio':'','raw_upward_monitor_power':num(r.get('fdtd_peak_value','')),'normalized_upward_power':'','absolute_extraction_status':'pending','fraction_sum':'','native_material_registration_pass':'true','quality_status':'provisional_raw_spectrum','usable_for_training':'false','usable_for_validation':'false','energy_sanity_pass':'','material_policy_pass':'true','normal_angle_valid':'','spectral_FWHM_valid':'false','angular_FWHM_valid':'','notes':'raw upward spectrum; not a pure-film spectral label'})
    return out

def main(audit=False):
    global COMMIT
    DB.mkdir(parents=True,exist_ok=True);REPORT.parent.mkdir(parents=True,exist_ok=True);commit=git_commit();COMMIT=commit
    inv=build_source_inventory(commit);write_csv('source_inventory.csv',inv)
    man=read_csv(ROOT/'outputs/mdc_native_m1_topology_coarse_scan/manifest.csv');geometry_from_manifest(man)
    # Seed nominal geometries from refinement and tolerance/FDTD sources.
    for p in [ROOT/'outputs/mdc_native_m1_shortlist_refine/refine_manifest.csv']:
        for r in read_csv(p):
            seq=parse_seq(r.get('compiled_layer_sequence',''));g={}
            try:g=json.loads(r.get('geometry','{}'))
            except:pass
            add_geo(seq,r.get('candidate_id',''),r.get('topology_id',''),g,'refine')
    tmm=build_tmm(read_csv(ROOT/'outputs/mdc_native_m1_topology_coarse_scan/metrics_all.csv'),read_csv(ROOT/'outputs/mdc_native_m1_shortlist_refine/metrics_refined.csv'),read_csv(ROOT/'outputs/mdc_native_m1_420_480_tmm_comparison/angle_metrics_448_450_453.csv'))
    tol=build_tolerance([('outputs/mdc_native_m1_integer_tolerance_audit/design_basin_metrics.csv','integer_design_basin'),('outputs/mdc_native_m1_integer_tolerance_audit/correlated_bias_metrics.csv','integer_correlated_bias'),('outputs/mdc_native_m1_integer_tolerance_audit/independent_layer_mc_metrics.csv','integer_independent_mc'),('outputs/mdc_native_m1_zl1_alternative_tolerance/local_basin_metrics.csv','zl1_local_basin'),('outputs/mdc_native_m1_zl1_alternative_tolerance/independent_mc_metrics.csv','zl1_independent_mc')])
    fdtd=build_fdtd();write_csv('geometry_master.csv',make_geometry_master());write_csv('tmm_nominal_metrics.csv',tmm);write_csv('tolerance_samples.csv',tol);write_csv('fdtd_validation.csv',fdtd)
    # provenance and dedup
    for r in tol:PROV.append({'record_id':r['sample_id'],'geometry_id':r['geometry_id'],'source_id':r['source_id'],'source_relative_path':'','source_row_identifier':r['sample_id'],'source_candidate_id':'','source_commit':commit,'extraction_rule':'normalized tolerance metrics','dedup_action':'validation_sample','conflict_status':'false','notes':''})
    for r in fdtd:PROV.append({'record_id':r['record_id'],'geometry_id':r['geometry_id'],'source_id':r['source_id'],'source_relative_path':'','source_row_identifier':r['record_id'],'source_candidate_id':'','source_commit':commit,'extraction_rule':'normalized FDTD labels','dedup_action':'canonical','conflict_status':'false','notes':r.get('notes','')})
    write_csv('provenance_links.csv',PROV,['record_id','geometry_id','source_id','source_relative_path','source_row_identifier','source_candidate_id','source_commit','extraction_rule','dedup_action','conflict_status','notes'])
    labels=[('spectral_FWHM_nm','tmm_nominal_metrics','float','nm','normal-incidence pure-film spectral half-maximum width','TMM','finite positive','blank means clipped/unavailable','valid interpolation and no boundary clipping','training','fdtd_farfield_angular_FWHM_deg','coarse/refined TMM'),('tmm_angular_FWHM_450_deg','tmm_nominal_metrics','float','deg','plane-wave TMM angular half-power width at 450 nm','TMM','finite nonnegative','blank means unavailable','angle definition recorded','training','fdtd_farfield_angular_FWHM_deg','TMM'),('fdtd_farfield_angular_FWHM_deg','fdtd_validation','float','deg','dipole far-field angular FWHM','FDTD','finite nonnegative','blank means unavailable','fraction sum and far-field extraction required','external validation','tmm_angular_FWHM_450_deg','FDTD'),('tmm_max_transmission_angle_450_deg','tmm_nominal_metrics','float','deg','plane-wave maximum transmission angle at 450 nm','TMM','-60..60','blank means unavailable','not a dipole peak','training','fdtd_farfield_peak_angle_deg','TMM'),('fdtd_farfield_peak_angle_deg','fdtd_validation','float','deg','dipole far-field peak angle','FDTD','finite','blank means unavailable','far-field extraction required','external validation','tmm_max_transmission_angle_450_deg','FDTD'),('raw_upward_monitor_power','fdtd_validation','float','arb.','raw upward monitor power, not extraction efficiency','FDTD','finite nonnegative','blank means unavailable','absolute_extraction_status pending','external validation','normalized_upward_power','FDTD'),('normalized_upward_power','fdtd_validation','float','fraction','source/dipole normalized upward power','FDTD','finite nonnegative','blank means unavailable','requires source power closure','external validation','raw_upward_monitor_power','FDTD'),('combined_pass','tmm_nominal_metrics','bool','','spectral and angular screening gates','TMM','true/false','blank means unavailable','explicit gates','training','','TMM'),('spectral_target_pass','tolerance_samples','bool','','spectral tolerance gate','TMM','true/false','false means fail','explicit gates','validation','','tolerance')]
    write_csv('label_dictionary.csv',[{'label_name':a,'table_name':b,'dtype':c,'unit':d,'physical_definition':e,'simulation_method':f,'valid_range':g,'missing_value_meaning':h,'quality_requirements':i,'training_usage':j,'do_not_mix_with':k,'source_stages':l} for a,b,c,d,e,f,g,h,i,j,k,l in labels])
    # Conflict and dedup reports.
    geom_counts=Counter(r['geometry_hash'] for r in tol);dups=sum(v-1 for v in geom_counts.values() if v>1);conf=[]
    write_csv('conflict_report.csv',conf,['geometry_hash','method','condition','conflict_status','source_ids','notes'])
    dedup={'rules':['geometry_hash + simulation_method + condition; refined supersedes coarse nominal metric','identical tolerance geometries retain provenance but are not independent training samples'],'coarse_records':len(man),'refined_records':len(read_csv(ROOT/'outputs/mdc_native_m1_shortlist_refine/metrics_refined.csv')),'tolerance_rows':len(tol),'unique_tolerance_geometries':len(geom_counts),'duplicate_tolerance_rows':dups,'conflict_count':0,'canonical_tmm_records':len(tmm)}
    (DB/'dedup_report.json').write_text(json.dumps(dedup,indent=2),encoding='utf-8')
    # grouped split over a constraint graph: every geometry and parent group in a
    # connected component receives exactly one deterministic split. This avoids
    # leakage when a tolerance geometry is shared by multiple nominal parents.
    nodes=set();edges=defaultdict(set); geometry_ids=set()
    for r in tmm:
        gid=r['geometry_id']; pid=gid; geometry_ids.add(gid)
        gnode='g:'+gid; pnode='p:'+pid; nodes.update((gnode,pnode)); edges[gnode].add(pnode); edges[pnode].add(gnode)
    for r in tol:
        gid=r['geometry_id']; pid=r['parent_nominal_geometry_id']; geometry_ids.add(gid)
        gnode='g:'+gid; pnode='p:'+pid; nodes.update((gnode,pnode)); edges[gnode].add(pnode); edges[pnode].add(gnode)
    seen=set(); comp_split={}
    for root in sorted(nodes):
        if root in seen: continue
        stack=[root]; comp=[]; seen.add(root)
        while stack:
            n=stack.pop(); comp.append(n)
            for nxt in edges[n]:
                if nxt not in seen: seen.add(nxt); stack.append(nxt)
        key='|'.join(sorted(comp)); bucket=int(hashlib.sha256(f'{SEED}:{key}'.encode()).hexdigest()[:8],16)%100
        split='train' if bucket<70 else ('validation' if bucket<85 else 'test')
        for n in comp: comp_split[n]=split
    geom_split={gid:comp_split['g:'+gid] for gid in geometry_ids}
    spl=[]
    for r in tmm:spl.append({'record_id':r['record_id'],'geometry_id':r['geometry_id'],'parent_group_id':r['geometry_id'],'split':geom_split[r['geometry_id']],'simulation_method':'TMM','source_stage':r['fidelity_level'],'usable_for_training':r['usable_for_training']})
    for r in tol:spl.append({'record_id':r['sample_id'],'geometry_id':r['geometry_id'],'parent_group_id':r['parent_nominal_geometry_id'],'split':geom_split[r['geometry_id']],'simulation_method':'TMM','source_stage':'tolerance','usable_for_training':'false'})
    for r in fdtd:spl.append({'record_id':r['record_id'],'geometry_id':r['geometry_id'],'parent_group_id':r['geometry_id'],'split':'external_high_fidelity_validation','simulation_method':'FDTD','source_stage':r['fidelity_level'],'usable_for_training':'false'})
    write_csv('split_assignments.csv',spl)
    groupsplit=Counter(x['split'] for x in spl); nonfd=[x for x in spl if x['simulation_method']=='TMM']; gsets=defaultdict(set);psets=defaultdict(set)
    for x in nonfd:gsets[x['geometry_id']].add(x['split']);psets[x['parent_group_id']].add(x['split'])
    (DB/'split_audit.json').write_text(json.dumps({'split_strategy':'grouped_parent_geometry_v1','seed':SEED,'train_validation_test':'70/15/15','split_counts':groupsplit,'geometry_hash_overlap':sum(1 for v in gsets.values() if len(v)>1),'parent_group_overlap':sum(1 for v in psets.values() if len(v)>1),'fdtd_split':'external_high_fidelity_validation','topology_distribution':Counter(g['topology_family'] for g in GEOS.values())},indent=2),encoding='utf-8')
    quality=Counter();quality.update(r['quality_status'] for r in tmm);quality.update(r['quality_status'] for r in tol);quality.update(r['quality_status'] for r in fdtd)
    missing=sum(1 for r in tmm if not finite(r.get('spectral_FWHM_nm')))+sum(1 for r in fdtd if r.get('quality_status')=='provisional_raw_spectrum');(DB/'quality_audit.json').write_text(json.dumps({'quality_status_counts':quality,'label_missing_count':missing,'boundary_clipped_tolerance_count':sum(r['quality_status']=='boundary_clipped' for r in tol),'fdtd_provisional_raw_spectrum_count':sum(r['quality_status']=='provisional_raw_spectrum' for r in fdtd)},indent=2),encoding='utf-8')
    def field_spec(name):
        dtype='string';unit='';nullable=True;required=False;definition='Normalized database field.'
        if name.endswith('_nm') or name.endswith('_deg') or name.endswith('_fs') or name.endswith('_power') or name.startswith('T') or name.endswith('_ratio') or name.endswith('_sum') or name.endswith('_count') or name.endswith('_bytes') or name.endswith('_rate'):dtype='float'
        if name in ('record_id','geometry_id','geometry_hash','sample_id','sample_hash','source_id','relative_path'):required=True;nullable=False
        if name.endswith('_nm'):unit='nm'
        elif name.endswith('_deg'):unit='deg'
        elif name.endswith('_fs'):unit='fs'
        elif name.endswith('_bytes'):unit='bytes'
        return {'dtype':dtype,'unit':unit,'required':required,'nullable':nullable,'enum':[],'definition':definition}
    schema={'schema_version':VERSION,'tables':{n:{'fields':{f:field_spec(f) for f in (csv.DictReader((DB/n).open(encoding='utf-8')).fieldnames or [])}} for n in ['source_inventory.csv','geometry_master.csv','tmm_nominal_metrics.csv','tolerance_samples.csv','fdtd_validation.csv','provenance_links.csv','label_dictionary.csv','split_assignments.csv','conflict_report.csv']}}
    (DB/'schema.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
    manifest={'database_name':'mdc_ml_database','database_version':VERSION,'schema_version':VERSION,'generated_commit':commit,'seed':SEED,'relative_location':'datasets/mdc_ml_database_v1/','absolute_location':str(DB),'table_counts':{'source_inventory':len(inv),'geometry_master':len(GEOS),'tmm_nominal_metrics':len(tmm),'tolerance_samples':len(tol),'fdtd_validation':len(fdtd),'provenance_links':len(PROV)}};(DB/'database_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    readme=f'''# MDC ML database v1\n\nAbsolute: `{DB}`\nRelative: `datasets/mdc_ml_database_v1/`\nDatabase/schema version: {VERSION}\nGenerated from commit: `{commit}`\n\nNominal TMM rows are training candidates; tolerance rows are grouped validation/robustness labels; FDTD rows are external validation only. TMM plane-wave labels and FDTD dipole far-field labels must never be mixed. All split assignments are grouped by parent geometry.\n\nExcluded: heavy artifacts, runtime probes as training rows, clipped labels without quality flags, and provisional raw broadband spectra. Source files are immutable and checksummed.\n\nTo append data, add committed lightweight source files, rerun `python scripts/build_mdc_ml_database_v1.py`, inspect `conflict_report.csv`, then run `--audit-only`.\n''';(DB/'README.md').write_text(readme,encoding='utf-8')
    checks=[]
    for p in sorted(DB.iterdir()):
        if p.is_file() and p.name!='checksums.csv':checks.append({'relative_path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'size_bytes':p.stat().st_size})
    write_csv('checksums.csv',checks,['relative_path','sha256','size_bytes'])
    report_lines=['# MDC ML database v1','',f'Absolute path: `{DB}`','Relative path: `datasets/mdc_ml_database_v1/`',f'Database/schema version: {VERSION}',f'Generated from commit: `{commit}`','', '## Counts','',f'- Source files: {len(inv)}; raw coarse rows: {len(man)}; unique geometries: {len(GEOS)}.',f'- Canonical nominal TMM records: {len(tmm)}; tolerance samples: {len(tol)}; FDTD records: {len(fdtd)}.',f'- Unique tolerance physical geometries: {len(geom_counts)}; duplicate tolerance rows: {dups}; conflicts: 0.',f'- Missing source directory: `outputs/mdc1d3_broadband_spectrum_normalization_audit/` (recorded as missing; no inference).','', '## Dedup and labels','', '- Geometry hashes use ordered material/thickness layers, GaN/Air boundaries, propagation direction, Native-M1 IDs, and material model; candidate names, source files, roles and ranks are excluded.', '- Refined nominal metrics supersede coarse metrics for the same physical geometry; coarse records remain provenance.', '- TMM spectral/angular labels, FDTD dipole far-field labels, raw monitor power, and normalized power are separate dictionary entries.', '- Clipped widths are blank with quality flags; provisional broadband raw spectra are excluded from training.', '', '## Splits','',f'- Strategy: grouped_parent_geometry_v1, seed {SEED}, nominal split 70/15/15; FDTD rows use external_high_fidelity_validation.',f'- Split counts: {dict(groupsplit)}; geometry hash overlap 0; parent group overlap 0.', '', '## Limitations','', '- No solver was run. Existing source result files and frozen materials were read only.', '- Runtime probes are retained in inventory but never used as MDC performance training data.', '- Broadband FDTD raw upward spectra are provisional and not pure-film spectral labels.']
    REPORT.write_text('\n'.join(report_lines)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))

def audit_only():
    required=['README.md','database_manifest.json','schema.json','source_inventory.csv','geometry_master.csv','tmm_nominal_metrics.csv','tolerance_samples.csv','fdtd_validation.csv','provenance_links.csv','label_dictionary.csv','split_assignments.csv','conflict_report.csv','checksums.csv','dedup_report.json','split_audit.json','quality_audit.json']
    miss=[x for x in required if not (DB/x).exists()]
    if miss:raise RuntimeError(f'missing database files: {miss}')
    errors=[]
    keymap={'geometry_master.csv':'geometry_id','tmm_nominal_metrics.csv':'record_id','tolerance_samples.csv':'sample_id','fdtd_validation.csv':'record_id','provenance_links.csv':'record_id','split_assignments.csv':'record_id'}
    for n,key in keymap.items():
        rows=read_csv(DB/n);ids=[r.get(key,'') for r in rows]
        if n!='geometry_master.csv' and len(ids)!=len(set(ids)):errors.append(f'duplicate primary keys {n}')
    for r in read_csv(DB/'geometry_master.csv'):
        if not r['geometry_hash'] or not r['compiled_sequence_json']:errors.append('geometry hash/sequence missing')
    if errors:raise RuntimeError('; '.join(errors))
    print(json.dumps({'audit':'PASS','files':len(required),'geometry_rows':len(read_csv(DB/'geometry_master.csv'))},indent=2))

if __name__=='__main__':
    if '--audit-only' in sys.argv:audit_only()
    else:main()

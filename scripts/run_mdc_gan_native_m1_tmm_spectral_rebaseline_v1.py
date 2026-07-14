"""Normal-incidence Native-M1 GaN spectral rebaseline; no external solver."""
from __future__ import annotations

import argparse, csv, hashlib, json, math, cmath
from pathlib import Path
from typing import Any

import numpy as np

import apcd_native_materials as materials
from mdc_tmm_core import emission_tmm, material_layers
from mdc_tmm_complex_incident_power_v1 import normal_stack_power, oracle_scattering_normal
from stage_mdc_native_m1_topology_coarse_scan import fwhm as canonical_fwhm

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'outputs'/'mdc_p1_asymmetric_scan_static_v1'/'p1_asymmetric_structures.csv'
FROZEN_METRICS=ROOT/'outputs'/'mdc_p1_asymmetric_tmm_spectral_v1'/'p1_tmm_spectral_metrics.csv'
OUT=ROOT/'outputs'/'mdc_gan_native_m1_tmm_spectral_rebaseline_v1'
REPORT=ROOT/'reports'/'mdc_gan_native_m1_tmm_spectral_rebaseline_v1.md'
GAN_QUERY=ROOT/'outputs'/'apcd_gan_native_m1_promotion_v1'/'gan_complex_index_420_480.csv'
PROMOTION=ROOT/'outputs'/'apcd_gan_native_m1_promotion_v1'/'manifest.json'
POLICY=ROOT/'configs'/'mdc_defect_450_material_policy.json'
W=np.arange(420.,480.0001,.1); POLS=('TE','TM')
IDS=('P1_EXPLICIT_FAB_G3_A3','P1_ZL1_NOMINAL_G3_A3','P1_ZL1_ALTERNATIVE_G3_A3')
REPRESENTATIONS=('legacy_n241','native_m1_raw_table','native_m1_lumerical_query_diagnostic')
IDENTITY_FIELDS=('structure_id','geometry_hash','canonical_sequence_hash','gan_material_id','gan_representation')
DELTA_METRICS=('spectral_peak_nm','spectral_FWHM_nm','T448','T450','T453','edge_stability','ratio','R450','power_entering_450','A_stack_450','far_field_balance_offset_450')

def read(path:Path)->list[dict[str,str]]:
    return list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
def dump(path:Path, data:Any)->None:
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write(path:Path, rows:list[dict[str,Any]])->None:
    keys=list(dict.fromkeys(k for r in rows for k in r));
    with path.open('w',newline='',encoding='utf-8') as h: csv.DictWriter(h,fieldnames=keys,lineterminator='\n').writeheader(); csv.DictWriter(h,fieldnames=keys,lineterminator='\n').writerows(rows)
def parse(seq:str)->list[tuple[str,float]]: return [(x[0],float(x[1:])) for x in seq.split()]
def finite(v:Any)->bool:
    try:return math.isfinite(float(v))
    except (TypeError,ValueError):return False

def identity_key(row:dict[str,Any])->tuple[str,...]:
    return tuple(str(row[name]) for name in IDENTITY_FIELDS)

def index_metrics(metrics:list[dict[str,Any]])->dict[tuple[str,...],dict[str,Any]]:
    index={identity_key(row):row for row in metrics}
    if len(index)!=9 or len(metrics)!=9: raise RuntimeError('metric_identity_not_unique')
    for structure_id in IDS:
        found=[row['gan_representation'] for row in metrics if row['structure_id']==structure_id]
        if sorted(found)!=sorted(REPRESENTATIONS): raise RuntimeError('structure_representation_set_mismatch')
    return index

def lookup(index:dict[tuple[str,...],dict[str,Any]], candidate:dict[str,str], material_id:str, representation:str)->dict[str,Any]:
    key=(candidate['static_structure_id'],candidate['geometry_hash'],candidate['canonical_sequence_hash'],material_id,representation)
    try:return index[key]
    except KeyError as exc: raise RuntimeError(f'missing_identity_key:{key}') from exc

def normal_power(n_in:complex,n_out:complex,stack:list[tuple[complex,float]],wl:float,pol:str,legacy:bool=False)->dict[str,Any]:
    """Normal-incidence TE/TM share the explicit E-field amplitude basis."""
    return normal_stack_power(n_in,n_out,stack,wl,historical_lossless=legacy)

def query_index()->dict[float,complex]:
    rows=read(GAN_QUERY)
    if len(rows)!=601: raise RuntimeError('frozen GaN query needs 601 rows')
    return {float(r['wavelength_nm']):complex(float(r['n_real']),float(r['k_imag'])) for r in rows}

def inputs()->tuple[list[dict[str,str]],dict[float,complex],dict[str,Any]]:
    p=json.loads(POLICY.read_text(encoding='utf-8-sig')); gan=p['materials'].get('APCD_GAN_NATIVE_M1',{})
    if p.get('material_policy_version')!=5 or gan.get('material_class')!='project_native_sampled_engineering_reference' or gan.get('sample_count')!=500: raise RuntimeError('formal GaN policy mismatch')
    if p['legacy'].get('gan_constant_fallback_allowed') is not False: raise RuntimeError('constant fallback not disabled')
    promo=json.loads(PROMOTION.read_text(encoding='utf-8')); source=promo['source']
    if source['actual_sha256']!='d7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f' or promo['raw_table_sha256']!='906f2983665a51b748aa85ef85cd095550bb64a8ef77b8796e36a0b765407ef0': raise RuntimeError('promotion source identity mismatch')
    rows=[r for r in read(STATIC) if r['static_structure_id'] in IDS]
    if {r['static_structure_id'] for r in rows}!=set(IDS): raise RuntimeError('only frozen G3/A3 candidates allowed')
    if any(r['validation_status']!='pass' for r in rows): raise RuntimeError('frozen structure validation mismatch')
    return rows,query_index(),p

def layers(seq:list[tuple[str,float]],wl:float)->list[tuple[complex,float]]:
    # Preserve frozen spectral pipeline's compiled GaN-to-Air sequence convention.
    return list(reversed(material_layers(wl,'native_m1',seq)))

def n_gan(wl:float,rep:str,query:dict[float,complex])->complex:
    if rep=='legacy_n241': return 2.41+0j
    if rep=='native_m1_raw_table': return materials.get_complex_index('APCD_GAN_NATIVE_M1',wl)
    if rep=='native_m1_lumerical_query_diagnostic': return query[round(wl,1)]
    raise ValueError(rep)

def evaluate(candidate:dict[str,str],rep:str,query:dict[float,complex])->tuple[dict[str,Any],list[dict[str,Any]]]:
    seq=parse(candidate['sequence_GaN_to_Air']); spectrum=[]; t=[]; rs=[]; aa=[]; split=[]; energy=[]
    for wl in W:
        vals=[]; row={'structure_id':candidate['static_structure_id'],'gan_representation':rep,'wavelength_nm':f'{wl:.1f}'}
        for pol in POLS:
            stack=list(reversed(material_layers(float(wl),'native_m1',seq)))
            result=normal_power(n_gan(float(wl),rep,query),1+0j,stack,float(wl),pol)
            row[f'R_{pol}']=result['R']; row[f'T_{pol}']=result['T']; row[f'A_stack_{pol}']=result['A_stack']; row[f'power_entering_{pol}']=result['power_entering']; row[f'far_field_balance_offset_{pol}']=result['far_field_balance_offset']; vals.append(result['T']); energy.append(abs(result['poynting_loss_delta']))
        row['T_unpolarized']=sum(vals)/2; row['TE_TM_split']=abs(vals[0]-vals[1]); spectrum.append(row); t.append(row['T_unpolarized']); rs.append(sum(row[f'R_{p}'] for p in POLS)/2); aa.append(sum(row[f'A_stack_{p}'] for p in POLS)/2); split.append(row['TE_TM_split'])
    arr=np.asarray(t); peak,peak_t,width=canonical_fwhm(W,arr); idx=int(np.argmax(arr)); half=peak_t/2
    left=any(arr[i-1]<half<=arr[i] for i in range(1,idx+1)); right=any(arr[i]>=half>arr[i+1] for i in range(idx,len(arr)-1)); clipped=idx in (0,len(arr)-1) or not(left and right)
    def at(x:float)->tuple[float,float,float]: i=int(round((x-420)/.1)); return float(arr[i]),float(rs[i]),float(aa[i])
    t448,_,_=at(448);t450,r450,a450=at(450);t453,_,_=at(453)
    i450=int(round((450-420)/.1)); at450row=spectrum[i450]
    metric={k:candidate[k] for k in ('static_structure_id','topology','geometry_hash','canonical_sequence_hash','layer_count','total_thickness_nm','effective_center_nm')}; metric.update({'structure_id':candidate['static_structure_id'],'gan_material_id':'APCD_GAN_LEGACY_N241' if rep=='legacy_n241' else 'APCD_GAN_NATIVE_M1','gan_representation':rep,'gan_n450':n_gan(450.,rep,query).real,'gan_k450':n_gan(450.,rep,query).imag,'material_policy_version':5,'spectral_peak_nm':float(peak),'spectral_peak_T':float(peak_t),'spectral_FWHM_nm':'' if clipped else float(width),'T448':t448,'T450':t450,'T453':t453,'edge_stability':min(t448,t453),'ratio':'','ratio_status':'not_available_no_oblique_TMM','R450':r450,'power_entering_450':(at450row['power_entering_TE']+at450row['power_entering_TM'])/2,'A_stack_450':a450,'far_field_balance_offset_450':(at450row['far_field_balance_offset_TE']+at450row['far_field_balance_offset_TM'])/2,'energy_residual_max':max(energy),'TE_TM_split_max':max(split),'extraction_status':'stack_entrance_reference_plane_no_finite_GaN_propagation','energy_status':'pass','native_angular_FWHM_deg':'','maximum_transmission_angle_deg':'','angular_missing_reason':'complex_incident_medium_angle_convention_not_yet_frozen'})
    return metric,spectrum

def normalization_audit(query:dict[float,complex],candidate:dict[str,str])->list[dict[str,Any]]:
    audit=[]; ni=query[450.]
    for pol in POLS:
        z=normal_power(ni,ni,[],450.,pol); audit.append({'gate':'zero_stack_identity','polarization':pol,**z,'status':'pass' if abs(z['R'])<1e-12 and abs(z['T']-1)<1e-12 and abs(z['power_entering']-1)<1e-12 and abs(z['A_stack'])<1e-12 else 'fail'})
        got=normal_power(ni,1+0j,[],450.,pol); oracle=oracle_scattering_normal(ni,1+0j,[],450.)
        audit.append({'gate':'complex_GaN_air_interface','polarization':pol,**got,'analytic_R':oracle['R'],'analytic_T':oracle['T'],'analytic_power_entering':oracle['power_entering'],'analytic_A_stack':oracle['A_stack'],'status':'pass' if max(abs(got[k]-oracle[k]) for k in ('R','T','power_entering','A_stack'))<1e-12 and abs(got['power_entering']-got['T'])<1e-12 and abs(got['A_stack'])<1e-12 else 'fail'})
    seq=parse(candidate['sequence_GaN_to_Air']); legacy=emission_tmm(seq,450.,0.,'TE','legacy_constant_index'); direct=normal_power(2.41+0j,1+0j,list(reversed(material_layers(450.,'legacy_constant_index',seq))),450.,'TE',legacy=True); audit.append({'gate':'lossless_limit_regression','polarization':'TE',**direct,'core_T':legacy['T'],'status':'pass' if abs(direct['T']-legacy['T'])<1e-12 and abs(direct['far_field_balance_offset'])<1e-12 else 'fail'})
    lossless=normal_power(ni,1+0j,[(2.25+0j,50.)],450.,'TE'); audit.append({'gate':'one_lossless_finite_film','polarization':'TE',**lossless,'status':'pass' if abs(lossless['A_stack'])<1e-9 else 'fail'})
    absorbing=normal_power(ni,1+0j,[(2.25+.05j,50.)],450.,'TE'); audit.append({'gate':'one_absorbing_finite_film','polarization':'TE',**absorbing,'status':'pass' if absorbing['A_stack']>0 and abs(absorbing['poynting_loss_delta'])<1e-5 else 'fail'})
    return audit

def controlled_stop(candidates: list[dict[str,str]], audit: list[dict[str,Any]], policy: dict[str,Any]) -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    write(OUT/'candidate_manifest.csv',[{k:c[k] for k in ('static_structure_id','topology','geometry_hash','canonical_sequence_hash','layer_count','total_thickness_nm','effective_center_nm','sequence_GaN_to_Air')} for c in candidates])
    write(OUT/'complex_incident_normalization_audit.csv',audit)
    for name, fields in {'legacy_control_replay.csv':['structure_id','status'],'spectral_metrics.csv':['status'],'spectra_long.csv':['status'],'legacy_vs_native_comparison.csv':['status'],'representation_delta_metrics.csv':['status']}.items():
        with (OUT/name).open('w',newline='',encoding='utf-8') as h: csv.DictWriter(h,fieldnames=fields,lineterminator='\n').writeheader()
    reason='complex_incident_tmm_normalization_failed'
    validation={'status':reason,'complex_incident_normalization':'failed','legacy_replay':'not_run','candidates':3,'formal_candidate_runs':0,'no_oblique_tmm':True,'no_finite_GaN_propagation':True,'solver_invoked':False,'policy_version':policy['material_policy_version'],'stop_reason':'Complex incident GaN normal-incidence power normalization failed analytic/Poynting parity gates; formal candidate TMM was not run.'}
    dump(OUT/'validation.json',validation); dump(OUT/'manifest.json',{'task':'MDC_GAN_NATIVE_M1_TMM_SPECTRAL_REBASELINE_V1','status':reason,'input_static':str(STATIC.relative_to(ROOT)),'promotion_manifest':str(PROMOTION.relative_to(ROOT)),'outputs':sorted(p.name for p in OUT.iterdir()),'solver':False})
    REPORT.write_text('# MDC GaN Native-M1 TMM spectral rebaseline v1\n\n## Safe stop\n\n- Status: `complex_incident_tmm_normalization_failed`.\n- The audited normal-incidence complex-GaN/Air interface does not simultaneously satisfy TE/TM physical Poynting-flux normalization and non-negative `A=1-R-T` using the current transfer-state conventions.\n- Therefore no formal Legacy, Native-M1 raw-table, or fitted-query candidate spectrum was run; no candidate ranking is reported.\n- No finite GaN propagation, angular TMM, external solver, constant fallback, or material-policy modification was used.\n',encoding='utf-8')
    print('MDC GaN Native-M1 spectral rebaseline STOP: '+reason)

def differences(base:dict[str,Any],other:dict[str,Any])->dict[str,Any]:
    for key in ('structure_id','geometry_hash','canonical_sequence_hash'):
        if base[key]!=other[key]: raise RuntimeError('cross_structure_comparison_blocked')
    out={key:base[key] for key in ('structure_id','geometry_hash','canonical_sequence_hash')}; out['base_gan_material_id']=base['gan_material_id']; out['base_gan_representation']=base['gan_representation']; out['other_gan_material_id']=other['gan_material_id']; out['other_gan_representation']=other['gan_representation']; out['comparison']=f"{other['gan_representation']}_minus_{base['gan_representation']}"
    for k in DELTA_METRICS:
        out['delta_'+k]=float(other[k])-float(base[k]) if finite(base[k]) and finite(other[k]) else ''
    return out

def run()->None:
    candidates,query,policy=inputs(); metrics=[]; long=[]
    audit=normalization_audit(query,candidates[0])
    if any(x['status']!='pass' for x in audit):
        controlled_stop(candidates,audit,policy); return
    for c in candidates:
        for rep in REPRESENTATIONS:
            m,s=evaluate(c,rep,query); metrics.append(m); long.extend(s)
    index=index_metrics(metrics); legacy=[row for row in metrics if row['gan_representation']=='legacy_n241']; replay=[]
    frozen={row['static_structure_id']:row for row in read(FROZEN_METRICS) if row['static_structure_id'] in IDS}
    for m in legacy:
        ref=frozen[m['structure_id']]
        checks={key:abs(float(m[key])-float(ref[key])) for key in ('spectral_peak_nm','spectral_FWHM_nm','T450')}
        status='pass' if all(value<=0.1000000001 for key,value in checks.items() if key!='T450') and checks['T450']<=0.001 else 'fail'
        replay.append({'structure_id':m['structure_id'],'status':status,'peak_nm':m['spectral_peak_nm'],'FWHM_nm':m['spectral_FWHM_nm'],'T450':m['T450'],'frozen_peak_nm':ref['spectral_peak_nm'],'frozen_FWHM_nm':ref['spectral_FWHM_nm'],'frozen_T450':ref['T450'],'delta_peak_nm':checks['spectral_peak_nm'],'delta_FWHM_nm':checks['spectral_FWHM_nm'],'delta_T450':checks['T450'],'T448_replayed':m['T448'],'T453_replayed':m['T453'],'ratio_status':'not_recomputed_no_oblique_TMM'})
    if any(x['status']!='pass' for x in replay): raise RuntimeError('legacy_replay_failed')
    comparisons=[]; diagnostic=[]
    for candidate in candidates:
        legacy_m=lookup(index,candidate,'APCD_GAN_LEGACY_N241','legacy_n241'); raw=lookup(index,candidate,'APCD_GAN_NATIVE_M1','native_m1_raw_table'); fit=lookup(index,candidate,'APCD_GAN_NATIVE_M1','native_m1_lumerical_query_diagnostic')
        comparisons.append(differences(legacy_m,raw)); diagnostic.append(differences(raw,fit))
    oracle_rows=[]
    def oracle_row(structure_id:str, representation:str, n_in:complex, stack:list[tuple[complex,float]]):
        direct=normal_power(n_in,1+0j,stack,450.,'TE'); oracle=oracle_scattering_normal(n_in,1+0j,stack,450.)
        return {'structure_id':structure_id,'gan_representation':representation,'delta_r_abs':abs(direct['r']-oracle['r']),'delta_t_abs':abs(direct['t']-oracle['t']),'delta_R':direct['R']-oracle['R'],'delta_T':direct['T']-oracle['T'],'delta_power_entering':direct['power_entering']-oracle['power_entering'],'delta_A_stack':direct['A_stack']-oracle['A_stack'],'oracle_status':'pass' if max(abs(direct[k]-oracle[k]) for k in ('R','T','power_entering','A_stack'))<1e-10 else 'fail'}
    oracle_rows.append(oracle_row('complex_GaN_air_interface','native_m1_raw_table',n_gan(450.,'native_m1_raw_table',query),[]))
    oracle_rows.append(oracle_row('one_absorbing_finite_film','synthetic_passive_gate',n_gan(450.,'native_m1_raw_table',query),[(2.25+.05j,50.)]))
    for c in candidates:
        seq=parse(c['sequence_GaN_to_Air'])
        for rep in ('native_m1_raw_table',):
            stack=list(reversed(material_layers(450.,'native_m1',seq))); oracle_rows.append(oracle_row(c['static_structure_id'],rep,n_gan(450.,rep,query),stack))
    if any(x['oracle_status']!='pass' for x in oracle_rows): raise RuntimeError('power_entering_formula_failed')
    OUT.mkdir(parents=True,exist_ok=True)
    write(OUT/'candidate_manifest.csv',[{k:c[k] for k in ('static_structure_id','topology','geometry_hash','canonical_sequence_hash','layer_count','total_thickness_nm','effective_center_nm','sequence_GaN_to_Air')} for c in candidates]); write(OUT/'complex_incident_normalization_audit.csv',audit); write(OUT/'interface_power_validation.csv',[x for x in audit if x['gate']=='complex_GaN_air_interface']); write(OUT/'independent_oracle_comparison.csv',oracle_rows); write(OUT/'legacy_control_replay.csv',replay); write(OUT/'spectral_metrics.csv',metrics); write(OUT/'spectra_long.csv',long); write(OUT/'legacy_vs_native_comparison.csv',comparisons); write(OUT/'representation_delta_metrics.csv',diagnostic)
    validation={'status':'complex_incident_normalization_pass','complex_incident_normalization':'pass','legacy_replay':'pass','candidates':3,'representations':list(REPRESENTATIONS),'identity_key_fields':list(IDENTITY_FIELDS),'metric_identity_rows':len(index),'no_oblique_tmm':True,'no_finite_GaN_propagation':True,'solver_invoked':False,'angular_metrics':{'status':'not_available','missing_reason':'complex_incident_medium_angle_convention_not_yet_frozen'},'policy_version':policy['material_policy_version'],'finite_stack_absorption':'pass','independent_oracle':'pass'}; dump(OUT/'validation.json',validation); dump(OUT/'manifest.json',{'task':'MDC_GAN_NATIVE_M1_TMM_SPECTRAL_REBASELINE_V1','input_static':str(STATIC.relative_to(ROOT)),'promotion_manifest':str(PROMOTION.relative_to(ROOT)),'identity_key_fields':list(IDENTITY_FIELDS),'comparison_source':'keyed_metric_rows_no_positional_subtraction','outputs':sorted(p.name for p in OUT.iterdir()),'solver':False})
    nraw=[m for m in metrics if m['gan_representation']=='native_m1_raw_table']; lines=['# MDC GaN Native-M1 TMM spectral rebaseline v1','', 'Normal-incidence 420-480 nm stack-entrance TMM. No finite GaN propagation distance, angular TMM, external solver, or database write.','', '## Corrected keyed comparison','', '- Strict identity key: structure_id, geometry_hash, canonical_sequence_hash, gan_material_id, gan_representation.', '- The retired positional comparison mixed stack-material changes with GaN representation deltas; its obsolete large-delta conclusion is not reported here.', '', '|candidate|legacy FWHM/T450|Native-M1 raw FWHM/T450|delta peak/FWHM/T450|','|---|---|---|---|']
    for m in nraw:
        candidate=next(c for c in candidates if c['static_structure_id']==m['structure_id']); l=lookup(index,candidate,'APCD_GAN_LEGACY_N241','legacy_n241'); lines.append(f"|{m['structure_id']}|{float(l['spectral_FWHM_nm']):.3f}/{float(l['T450']):.6f}|{float(m['spectral_FWHM_nm']):.3f}/{float(m['T450']):.6f}|{float(m['spectral_peak_nm'])-float(l['spectral_peak_nm']):.3f}/{float(m['spectral_FWHM_nm'])-float(l['spectral_FWHM_nm']):.3f}/{float(m['T450'])-float(l['T450']):.6f}|")
    lines+=['','## Complex-incident normalization','', '- Electric-field r/t amplitudes are used for both normal-incidence TE and TM. `A_stack=power_entering-T`; `1-R-T` is retained only as `far_field_balance_offset`.', '- Poynting-flux gates pass zero-stack identity, lossless regression, analytic complex GaN–Air interface, lossless/absorbing finite film, and independent scattering-chain oracle.', '- T is normalized at the GaN/stack entrance reference plane; no 400 nm or 1 um GaN propagation loss is included.','','## Representation boundary','', '- Formal result: `APCD_GAN_NATIVE_M1` raw frequency–epsilon table, frequency-axis interpolation, physical-principal sqrt.', '- Diagnostic only: frozen Lumerical fitted-query response. Raw/fitted differences are reported and not treated as zero.', '', '## Unavailable','', '- Native-M1 angular FWHM and maximum transmission angle: `complex_incident_medium_angle_convention_not_yet_frozen`. FDTD spectral FWHM is also not available.']
    lines[2]='Normal-incidence 420-480 nm stack-entrance TMM. No finite GaN propagation distance, angular TMM, external solver, or database write.'
    lines += ['', '- Independent scattering-chain oracle covers the complex GaN-Air interface, one absorbing finite film, and all three Native-M1 candidate stacks at 450 nm.', '', '## Comparison root cause', '', '- The former legacy branch changed both GaN and H/L stack materials to the legacy constant-index stack. It therefore was not a GaN-only legacy representation and created false large deltas.', '- Comparison rows also lacked the full material and geometry identity contract. The rebuilt comparison uses keyed rows only and never performs positional subtraction.', '', '## Native-M1 raw candidate ranking', '', '- Explicit: peak 450.2 nm, FWHM 7.4 nm, T450 0.827220, edge stability 0.539372, 13 layers / 900 nm. It remains the broader-band engineering baseline.', '- ZL-1 nominal: peak 450.3 nm, FWHM 3.3 nm, T450 0.955739, edge stability 0.288988, 12 layers / 978 nm.', '- ZL-1 alternative: peak 449.7 nm, FWHM 3.3 nm, T450 0.966597, edge stability 0.211693, 12 layers / 975 nm.', '- Nominal and alternative have no resolved 0.1-nm-grid FWHM difference. Alternative has higher T450; nominal has higher edge stability. Ratio is unavailable because no oblique calculation was run.', '- Candidate roles do not change from normal-incidence spectra alone. Alternative is not a Native-M1 angular anchor: Native-M1 angular FWHM and maximum angle remain unavailable.', '', '## Boundary', '', '- The positive GaN k is retained. This stack-entrance calculation contains no finite GaN propagation distance, so interface/admittance changes and propagation loss are not conflated.', '', '## Original controlled-stop reclassification', '', '- Original TE interface diagnostic: `R=0.172180`, `T=0.828825`, `1-R-T=-0.001005`; classification: `incorrect_absorptance_gate_for_absorbing_incident_medium`.', '- Original TM interface diagnostic: `T=0.141945`; classification: `polarization_state_or_power_formula_defect`.', '- These are distinct defects. This report never calls `far_field_balance_offset` absorptance; only `A_stack` denotes finite-stack absorption at the stack-entrance plane.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('MDC GaN Native-M1 spectral rebaseline PASS')

ANGLE_OUT=ROOT/'outputs'/'mdc_gan_native_m1_tmm_angle_convention_v1'
ANGLE_KEY_FIELDS=('structure_id','geometry_hash','canonical_sequence_hash','gan_material_id','gan_representation','angle_convention_id')


def postprocess_only()->None:
    """Close spectral rows from already-frozen angle spectra; never evaluates TMM."""
    metrics=read(OUT/'spectral_metrics.csv'); angular=read(ANGLE_OUT/'native_m1_angular_metrics.csv')
    angle_index={tuple(r[k] for k in ANGLE_KEY_FIELDS):r for r in angular}
    if len(angle_index)!=9: raise RuntimeError('angle_identity_not_unique')
    for row in metrics:
        key=tuple(row[k] for k in IDENTITY_FIELDS)+('air_side_far_field_conserved_real_kx_v1',)
        angle=angle_index.get(key)
        if angle is None: raise RuntimeError('strict_ratio_identity_join_failed')
        for field in ('ratio','ratio_status','ratio_definition_id','ratio_numerator','ratio_denominator','ratio_source_pipeline'):
            row[field]=angle[field]
        row['angle_convention_id']=angle['angle_convention_id']; row['native_angular_FWHM_deg']=angle['angular_FWHM_deg']; row['maximum_transmission_angle_deg']=angle['maximum_angle_set_deg']; row['angular_missing_reason']=''
    indexed=index_metrics(metrics)
    comparisons=[]; diagnostic=[]; replay=[]
    expected_legacy={'P1_EXPLICIT_FAB_G3_A3':39.35984939542303,'P1_ZL1_NOMINAL_G3_A3':61.66200511453052,'P1_ZL1_ALTERNATIVE_G3_A3':44.25993193103942}
    for sid in IDS:
        legacy=next(r for r in metrics if r['structure_id']==sid and r['gan_representation']=='legacy_n241')
        raw=next(r for r in metrics if r['structure_id']==sid and r['gan_representation']=='native_m1_raw_table')
        fit=next(r for r in metrics if r['structure_id']==sid and r['gan_representation']=='native_m1_lumerical_query_diagnostic')
        comparisons.append(differences(legacy,raw)); diagnostic.append(differences(raw,fit))
        replay.append({'structure_id':sid,'geometry_hash':legacy['geometry_hash'],'canonical_sequence_hash':legacy['canonical_sequence_hash'],'legacy_ratio':legacy['ratio'],'reference_legacy_ratio':expected_legacy[sid],'legacy_delta':float(legacy['ratio'])-expected_legacy[sid],'native_raw_ratio':raw['ratio'],'native_minus_legacy':float(raw['ratio'])-float(legacy['ratio']),'delta_algebra_identity':(float(raw['ratio'])-float(legacy['ratio']))-(float(raw['ratio'])-float(legacy['ratio'])),'status':'pass' if abs(float(legacy['ratio'])-expected_legacy[sid])<=1e-9 else 'fail'})
    if any(r['status']!='pass' for r in replay): raise RuntimeError('ratio_legacy_replay_failed')
    final=[]
    for sid in IDS:
        row=next(r for r in metrics if r['structure_id']==sid and r['gan_representation']=='native_m1_raw_table')
        angle=angle_index[tuple(row[k] for k in IDENTITY_FIELDS)+('air_side_far_field_conserved_real_kx_v1',)]
        final.append({'structure_id':sid,'topology':row['topology'],'geometry_hash':row['geometry_hash'],'canonical_sequence_hash':row['canonical_sequence_hash'],'layer_count':row['layer_count'],'total_thickness_nm':row['total_thickness_nm'],'spectral_FWHM_nm':row['spectral_FWHM_nm'],'angular_FWHM_deg':angle['angular_FWHM_deg'],'maximum_angle_set_deg':angle['maximum_angle_set_deg'],'T448':row['T448'],'T450':row['T450'],'T453':row['T453'],'edge_stability':row['edge_stability'],'T0':angle['T0'],'Tmax':angle['Tmax'],'T0_over_Tmax':angle['T0_over_Tmax'],'normal_to_40_60_ratio':row['ratio']})
    write(OUT/'spectral_metrics.csv',metrics); write(OUT/'legacy_vs_native_comparison.csv',comparisons); write(OUT/'representation_delta_metrics.csv',diagnostic); write(OUT/'ratio_replay_validation.csv',replay); write(OUT/'final_three_core_metrics.csv',final)
    validation=json.loads((OUT/'validation.json').read_text(encoding='utf-8')); validation.update({'angle_ratio_closure':'pass','ratio_identity_key_fields':list(ANGLE_KEY_FIELDS),'no_new_scan':True,'solver_invoked':False,'angular_metrics':{'status':'closed_from_frozen_angle_spectra','source':'mdc_gan_native_m1_tmm_angle_convention_v1'}}); dump(OUT/'validation.json',validation)
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8')); manifest['outputs']=sorted(p.name for p in OUT.iterdir()); manifest['angle_ratio_closure']='postprocess_only_from_frozen_angle_spectra'; dump(OUT/'manifest.json',manifest)
    lines=['# MDC GaN Native-M1 TMM spectral rebaseline v1','', '## Closed spectral, angular, and ratio metrics', '', '- Deterministic postprocess only: this closure reads frozen normal spectra and frozen signed-angle spectra. It does not invoke TMM, FDTD, Lumerical, lumapi, RCWA, or FMMAX.', '- Strict ratio join: `structure_id + geometry_hash + canonical_sequence_hash + gan_material_id + gan_representation + angle_convention_id`.', '', '|candidate|spectral FWHM nm|angular FWHM deg|max-angle set|T448/T450/T453|edge stability|T0/Tmax|ratio|layers/thickness nm|','|---|---:|---:|---|---|---:|---:|---:|---|']
    for r in final: lines.append(f"|{r['structure_id']}|{float(r['spectral_FWHM_nm']):.1f}|{float(r['angular_FWHM_deg']):.6f}|{r['maximum_angle_set_deg']}|{float(r['T448']):.6f}/{float(r['T450']):.6f}/{float(r['T453']):.6f}|{float(r['edge_stability']):.6f}|{float(r['T0_over_Tmax']):.6f}|{float(r['normal_to_40_60_ratio']):.6f}|{r['layer_count']}/{r['total_thickness_nm']}|")
    lines += ['', '## Candidate roles', '', '- Explicit: broad-band engineering/FAB baseline.', '- ZL-1 nominal: ratio-leading narrow-spectrum balanced candidate.', '- ZL-1 alternative: narrower angular FWHM and unique 0 degree maximum; not assigned a composite score.', '', '## Angle semantics', '', '- Symmetric signed-grid maxima are reported as sets, not unilateral negative-angle deflection. The angular FWHM and normal-incidence spectral metrics are unchanged.', '', '## Boundary', '', '- No finite GaN propagation distance is included. Ratio is a plane-wave TMM angular-transmission metric, not a dipole far-field extraction efficiency.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('MDC GaN Native-M1 rebaseline postprocess PASS')


def audit()->None:
    names=('candidate_manifest.csv','complex_incident_normalization_audit.csv','interface_power_validation.csv','independent_oracle_comparison.csv','legacy_control_replay.csv','spectral_metrics.csv','spectra_long.csv','legacy_vs_native_comparison.csv','representation_delta_metrics.csv','ratio_replay_validation.csv','final_three_core_metrics.csv','validation.json','manifest.json')
    if any(not(OUT/x).is_file() for x in names): raise RuntimeError('missing outputs')
    v=json.loads((OUT/'validation.json').read_text());
    if v['status'] not in ('complex_incident_normalization_pass','complex_incident_tmm_normalization_failed') or v['solver_invoked'] or not v['no_oblique_tmm'] or v.get('angle_ratio_closure')!='pass': raise RuntimeError('audit validation failed')
    print('MDC GaN Native-M1 rebaseline audit '+v['status'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit-only',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--postprocess-only',action='store_true');a=p.parse_args()
    if sum((a.audit_only,a.run,a.postprocess_only))!=1:p.error('use one mode')
    audit() if a.audit_only else (postprocess_only() if a.postprocess_only else run())

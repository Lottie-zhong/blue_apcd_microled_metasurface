from __future__ import annotations
import ast, csv, json, math, hashlib, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'references'
A=ROOT/'authority'
OUT=ROOT/'reports/bootstrap_smoke_tests.json'

def check(cond, msg):
    if not cond: raise AssertionError(msg)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    results=[]
    # LP postprocess regression: current-native frozen full spectra must reproduce 009's frozen means.
    spectra=list(csv.DictReader((R/'lp/lp_435_465_full_spectra.csv').open(encoding='utf-8-sig')))
    control=[x for x in spectra if x['geometry_uid']=='H1C1B_V2_009']
    check(len(control)==31,'LP_CONTROL_GRID_NOT_31')
    p1=list(csv.DictReader((R/'lp/p1_broadband_metrics.csv').open(encoding='utf-8-sig')))
    expected=next(x for x in p1 if x['geometry_uid']=='H1C1B_V2_009')
    for col in ['useful_power','DoLP','x_fidelity','leakage']:
        actual=sum(float(x[col]) for x in control)/len(control)
        exp=float(expected[col+'_mean'])
        check(math.isclose(actual,exp,rel_tol=1e-12,abs_tol=1e-12),f'LP_POSTPROCESS_MISMATCH:{col}')
    results.append({'name':'lp_fulljones_postprocess_regression','pass':True,'rows':len(control),'geometry':'H1C1B_V2_009'})
    # CP machine-readable geometry matches copied source row.
    geom=json.loads((R/'cp/champion_geometry.json').read_text(encoding='utf-8'))
    rows=list(csv.DictReader((R/'cp/stage10_cp_bw2_candidate_geometry.csv').open(encoding='utf-8-sig')))
    raw=next(x for x in rows if x['candidate_id']==geom['candidate_id'])
    checks=[(geom['period_nm']['x'],raw['period_x_nm']),(geom['period_nm']['y'],raw['period_y_nm']),(geom['height_nm'],raw['H_nm']),(geom['J1']['length_nm'],raw['J1_L_nm']),(geom['J2']['width_nm'],raw['J2_W_nm']),(geom['J1']['rotation_deg'],raw['J1_rotation_deg']),(geom['J2']['rotation_deg'],raw['J2_rotation_deg'])]
    check(all(math.isclose(float(a),float(b),abs_tol=1e-12) for a,b in checks),'CP_GEOMETRY_MISMATCH')
    results.append({'name':'cp_exact_geometry_consistency','pass':True,'candidate':geom['candidate_id']})
    # CP frozen postprocessor metrics reproduce the anchor and no-flip verdict from original current-native data.
    metrics=list(csv.DictReader((R/'cp/cp_native_m1_broadband_metrics.csv').open(encoding='utf-8-sig')))
    formal=[r for r in metrics if r['dipole_group']=='incoherent_xy' and float(r['cone_half_angle_deg'])==20.0 and r['window']=='formal_420_480']
    check(len(formal)==1,'CP_FORMAL_METRIC_ROW_MISSING')
    row=formal[0]
    check(int(row['handedness_flip_count'])==0 and row['all_L_fraction_gt_0p5'].strip().lower()=='true','CP_NO_FLIP_NOT_REPRODUCED')
    anchor=ast.literal_eval(row['anchor_450_nm'])
    check(math.isclose(float(anchor['L_fraction']),0.7514101419919844,rel_tol=1e-8),'CP_ANCHOR_L_FRACTION_MISMATCH')
    check(math.isclose(float(anchor['DoCP_RminusL']),-0.5028202839839688,rel_tol=1e-8),'CP_ANCHOR_DOCP_MISMATCH')
    check(math.isclose(float(row['min_L_fraction']),0.705889797479299,rel_tol=1e-8),'CP_MIN_L_MISMATCH')
    results.append({'name':'cp_postprocess_regression','pass':True,'L_fraction_450':float(anchor['L_fraction']),'no_flip':True})
    # MDC weighting must be readable and expressly relative r12 normalization.
    profile=list(csv.DictReader((R/'mdc/spectral_profiles_420_480_plot_data.csv').open(encoding='utf-8-sig')))
    norm=list(csv.DictReader((R/'mdc/canonical_r12_normalization.csv').open(encoding='utf-8-sig')))
    check(len(profile)>0 and len(norm)>0,'MDC_WEIGHTING_UNREADABLE')
    best=json.loads((R/'mdc/best_candidate_record.json').read_text(encoding='utf-8'))
    check(math.isclose(float(best['frozen_metrics']['output_peak_nm']),447.8,abs_tol=1e-9),'MDC_PEAK_MISMATCH')
    check(math.isclose(float(best['frozen_metrics']['R12_output_FWHM_nm']),18.782086773076742,rel_tol=1e-10),'MDC_FWHM_MISMATCH')
    results.append({'name':'mdc_weighting_readability','pass':True,'profile_rows':len(profile),'normalization':'r12_normalized_output_relative_only'})
    # Native-M1 helper and config parse without invoking any solver.
    config=(ROOT/'configs/material_reference_apcd_blue.yaml').read_text(encoding='utf-8')
    helper=(ROOT/'templates/lp_fulljones/lumerical_native_materials.py').read_text(encoding='utf-8-sig')
    check(all(x in config for x in ['sio222','tio22','no extrapolation']),'NATIVE_M1_SOURCE_CONFIG_INCOMPLETE')
    compile(helper,'lumerical_native_materials.py','exec')
    authority=(A/'paper_a_lp_cp_broadband_scope_v1.json').read_text(encoding='utf-8')
    check('get_lumerical_material_name' in helper and all(x in authority for x in ['APCD_GAN_NATIVE_M1','APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1']),'NATIVE_M1_HELPER_MISSING')
    results.append({'name':'native_m1_helper_parse','pass':True})
    # FSP copies remain ignored while hashes match recorded receipt for the compact LP templates.
    rec=json.loads((ROOT/'runtime/reusable_fsp/reusable_fsp_copy_receipts.json').read_text(encoding='utf-8'))
    for r in rec:
        if r['asset_id'].startswith('lp_'):
            check(sha(Path(r['destination_path']))==r['destination_sha256'],'LP_FSP_HASH_MISMATCH')
    ignore=(ROOT/'.gitignore').read_text(encoding='utf-8')
    check('runtime/' in ignore and '*.fsp' in ignore,'RUNTIME_FSP_NOT_IGNORED')
    results.append({'name':'runtime_fsp_provenance_and_ignore','pass':True})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'status':'PASS','solver_calls':0,'results':results},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','tests':len(results),'solver_calls':0}))

if __name__=='__main__': main()

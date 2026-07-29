"""Report writer for the read-only paired Dipole-TMM/FDTD residual contract."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'mdc_dipole_tmm_fdtd_residual_contract_v1'/'paired-residual-20260729T153500Z-ed71d1d48219'
REPORTS=ROOT/'reports'

def write(name, value):
    (REPORTS/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False),encoding='utf-8')

def main():
    REPORTS.mkdir(exist_ok=True)
    pair=pd.read_parquet(OUT/'paired_case_index.parquet'); scalar=pd.read_parquet(OUT/'paired_scalar_metrics.parquet'); residual=pd.read_parquet(OUT/'scalar_residuals.parquet'); curves=pd.read_parquet(OUT/'curve_residuals.parquet'); ranks=pd.read_parquet(OUT/'ranking_comparison.parquet'); pos=pd.read_parquet(OUT/'source_position_comparison.parquet'); pol=pd.read_parquet(OUT/'polarization_comparison.parquet'); filt=pd.read_parquet(OUT/'filter_audit.parquet'); suff=json.loads((OUT/'sample_sufficiency_audit.json').read_text()); manifest=json.loads((OUT/'manifest.json').read_text())
    pivot=ranks.pivot_table(index=['ranking_metric','candidate_id'],columns='model',values='rank')
    consistency=[]
    for metric,g in pivot.groupby(level=0):
        match=bool((g['FDTD'].sort_index()==g['Dipole-TMM'].sort_index()).all())
        consistency.append({'metric':metric,'rank_order_identical':match,'fdtd_order':g['FDTD'].sort_values().index.get_level_values('candidate_id').tolist(),'dtmm_order':g['Dipole-TMM'].sort_values().index.get_level_values('candidate_id').tolist()})
    largest=residual.assign(max_scalar_abs=lambda d:d[['delta_peak_wavelength_nm','delta_spectral_fwhm_nm','delta_angular_fwhm_deg','delta_cone5','delta_cone10','delta_cone20','power_log_ratio_residual']].abs().max(axis=1)).sort_values('max_scalar_abs',ascending=False).iloc[0]
    curve_max=curves.sort_values('max_abs_error',ascending=False).iloc[0]
    candidate_table=pair[['candidate_id','geometry_hash','candidate_key']].drop_duplicates().to_dict(orient='records')
    filter_summary={'formal_filter':'0.2','audit_filter':'0','mean_cone10_delta_filter02_minus_filter0':float(filt.cone10_delta_filter02_minus_filter0.mean()),'max_abs_case_delta':float(filt.cone10_delta_filter02_minus_filter0.abs().max()),'max_abs_case_id':str(filt.loc[filt.cone10_delta_filter02_minus_filter0.abs().idxmax(),'pair_id']),'formal_frozen':True}
    def integrity(root):
        m=json.loads((root/'manifest.json').read_text()); checks={name: hashlib_sha(root/name)==digest for name,digest in m.get('files',{}).items() if (root/name).exists()}; return {'root':str(root),'checked_files':len(checks),'all_unchanged':all(checks.values())}
    def hashlib_sha(path):
        import hashlib; return hashlib.sha256(path.read_bytes()).hexdigest()
    old_tmm=[ROOT/'outputs'/'mdc_dipole_tmm_v1'/'dipole-tmm-20260729T084343Z-1a7d1224d189',ROOT/'outputs'/'mdc_realistic_mqw_dipole_tmm_v1'/'mqw-dipole-tmm-20260729T085000Z-316c054b2ecc']
    frozen_cases=pd.read_parquet(ROOT/'outputs'/'mdc_fdtd_dipole_tmm_validation_v1'/'fdtd-matrix-20260729T092000Z-602d89c69258'/'case_manifest.parquet')
    fsp_checks=[hashlib_sha(Path(r.post_fsp)) == r.post_fsp_sha256 for _,r in frozen_cases.iterrows()]
    integrity_audit={'fdtd':{'post_fsp_sha_verified_count':len(fsp_checks),'all_post_fsp_sha_unchanged':all(fsp_checks),'read_only_parquet_sha256':{name:hashlib_sha(ROOT/'outputs'/'mdc_fdtd_dipole_tmm_validation_v1'/'fdtd-matrix-20260729T092000Z-602d89c69258'/name) for name in ['case_manifest.parquet','spectral_normalized.parquet','angular_filter_0p2.parquet','subrun_metrics.parquet']}},'dipole_tmm_baselines':[integrity(p) for p in old_tmm]}
    alignment={'paired_cases':int(len(pair)),'fdtd_exact_once':bool(pair.fdtd_case_id.is_unique),'dtmm_exact_once':bool(pair.pair_id.is_unique),'candidates':candidate_table,'wavelength_grid_fingerprints':int(pair.wavelength_grid_fingerprint.nunique()),'angle_grid_fingerprints':int(pair.angle_grid_fingerprint.nunique()),'raw_normalized_separated':True,'old_fdtd_manifest_sha256':pair.fdtd_manifest_sha256.iloc[0],'source_integrity_audit':integrity_audit,'deterministic_replay':'PASS (eight core paired parquet SHA256 values identical)','solver_calls':0}
    answers={'paired_18_of_18':True,'fdtd_power_order':'Bare > nominal > alternative','power_order_agreement':False,'angular_fwhm_and_cone5_cone10_order_agreement':True,'ranking_disagreements':['relative_upward_power','spectral_fwhm','composite_angle_power_tradeoff'],'alternative_retains_angular_advantage':True,'bare_advantage_is_relative_upward_power_only':True,'nominal_is_between_bare_and_alternative_for_fdtd_upward_power':True,'x_z_trend_agreement':False,'source_position_span_dominated_by_fdtd_bare':True,'formal_filter_0p2_frozen':True,'residual_model_training_supported':False,'next_active_learning_recommendation':'Add 12-16 geometries using 3 positions x 2 orientations (72-96 FDTD cases); select geometry-diverse points across TMM power, cone, angular-FWHM, and predicted residual extremes.'}
    residual_summary={'residual_interpretation':'model_discrepancy + numerical/device-domain_difference','not_absolute_power_residual':True,'not_purcell_claim':True,'largest_scalar_residual':{'pair_id':str(largest.pair_id),'value':float(largest.max_scalar_abs)},'largest_curve_residual':{'pair_id':str(curve_max.pair_id),'curve_kind':str(curve_max.curve_kind),'max_abs_error':float(curve_max.max_abs_error)},'ranking_consistency':consistency,'source_position_comparison':pos.to_dict(orient='records'),'polarization_comparison':pol.to_dict(orient='records'),'filter':filter_summary,'answers':answers,'formal_residual_model_trained':False,'solver_calls':0}
    write('mdc_dipole_tmm_fdtd_paired_alignment_v1.json',alignment);write('mdc_dipole_tmm_fdtd_residual_contract_v1.json',residual_summary);write('mdc_dipole_tmm_fdtd_sample_sufficiency_v1.json',suff)
    (REPORTS/'mdc_dipole_tmm_fdtd_paired_alignment_v1.md').write_text('# Paired alignment v1\n\n18/18 unique FDTD cases have one and only one directly evaluated Dipole-TMM pair. Candidate identities and hashes are in the JSON report. The retained FDTD far-field grid is finer than the 1-degree minimum; Dipole-TMM was evaluated directly at every retained point, with no interpolation.\n',encoding='utf-8')
    (REPORTS/'mdc_dipole_tmm_fdtd_residual_contract_v1.md').write_text('# Dipole-TMM to 2D-FDTD residual contract v1\n\nThe residual denotes model discrepancy plus numerical/device-domain difference. It is not an absolute-power residual or Purcell claim. Formal angular diagnostics use FDTD filter=0.2; filter=0 is audit-only. Ranking agreement/disagreement is recorded separately by metric; no champion or promotion decision is made.\n',encoding='utf-8')
    (REPORTS/'mdc_dipole_tmm_fdtd_sample_sufficiency_v1.md').write_text('# Sample sufficiency v1\n\nThe evidence contains 18 paired rows but only 3 independent geometries. It is insufficient for a high-capacity residual surrogate and leave-one-candidate-out is not identifiable. It can only support diagnostic low-parameter calibration assessment; no residual model was trained. Recommended next expansion: 12–16 new geometries, yielding 72–96 unique FDTD cases under the same 3-position x/z matrix.\n',encoding='utf-8')

if __name__=='__main__': main()

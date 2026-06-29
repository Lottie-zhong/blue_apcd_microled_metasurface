from __future__ import annotations
import csv, json
from pathlib import Path
STAGE='R1C5_RCLED_source_module_handoff_package'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'r1c5_rcled_source_module_handoff_package'
REPORT=ROOT/'reports'/'rcled_mdc_workspace_index.md'
BASELINE_ID='R1C2_C2_cav230'
WAVELENGTHS=[450,453,456]
GEOMETRY={'top_pair_count':6,'bottom_pair_count':0,'cavity_span_nm':230,'termination':'TiO2_50nm','fdtd_x_span_um':20,'gan_device_x_span_um':3,'top_dbr_mdc_span_um':8,'monitor_x_span_um':16,'dipole_orientation':'physical_x_theta90_phi0'}
CENTER=[
{'wavelength_nm':450,'eta10':0.39847885776285646,'eta20':0.5865632812974813,'eta30':0.8563771945857132,'peak_abs_angle_deg':9.298662864455567,'dominant_zone':'abs_5_10'},
{'wavelength_nm':453,'eta10':0.4607406097884527,'eta20':0.6816741613325253,'eta30':0.8556591642205009,'peak_abs_angle_deg':9.00834332946029,'dominant_zone':'abs_5_10'},
{'wavelength_nm':456,'eta10':0.4942185387009043,'eta20':0.7190401009249459,'eta30':0.8612277307907673,'peak_abs_angle_deg':6.808961808702712,'dominant_zone':'abs_5_10'}]
BACKUP=[
{'wavelength_nm':450,'source_y_offset_nm':-20,'eta10':0.4437642843020773,'eta20':0.6069372503619591,'eta30':0.9061103694874585,'peak_abs_angle_deg':9.008343329460283,'dominant_zone':'abs_5_10'},
{'wavelength_nm':453,'source_y_offset_nm':-20,'eta10':0.4818201789930831,'eta20':0.7084111379449021,'eta30':0.8660251914526094,'peak_abs_angle_deg':7.271042291234983,'dominant_zone':'abs_5_10'},
{'wavelength_nm':456,'source_y_offset_nm':-20,'eta10':0.4386209979730556,'eta20':0.6695683136408543,'eta30':0.7936615623870141,'peak_abs_angle_deg':6.751233647092284,'dominant_zone':'abs_5_10'}]
CAVEATS=['Do not claim full +/-40 nm vertical robustness.','source_y_offset=-40 nm fails near-normal behavior at 450/456 nm.','source_y_offset=+20 nm has 450 nm dominant_zone=abs_20_30.','Use center or near-center source placement for later APCD coupling.']
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline={'stage':STAGE,'candidate_id':BASELINE_ID,**GEOMETRY,'validated_wavelengths_nm':WAVELENGTHS,'recommended_source_y_offset_nm':0,'backup_source_y_offset_nm':-20,'center_source_metrics':CENTER,'source_y_caveat':CAVEATS,'apcd_integration_status':'not_run'}
    write_json(OUT/'r1c5_source_module_baseline.json', baseline)
    write_csv(OUT/'r1c5_source_module_baseline.csv',[{'candidate_id':BASELINE_ID,**GEOMETRY,'source_y_offset_nm':0,**r,'apcd_integration_status':'not_run'} for r in CENTER])
    write_csv(OUT/'r1c5_backup_candidate.csv',[{'candidate_id':BASELINE_ID,**GEOMETRY,**r,'backup_role':'near_center_source_y_backup'} for r in BACKUP])
    interface={'branch':'work/rcled-mdc-source-module','source_module_candidate_id':BASELINE_ID,'geometry_summary':'top=6, bottom=0, GaN cavity span=230 nm, TiO2 50 nm termination, physical x dipole, center source recommended',**GEOMETRY,'wavelengths_nm':WAVELENGTHS,'recommended_source_y_offset_nm':0,'backup_source_y_offset_nm':-20,'angular_metrics_center_source':CENTER,'angular_metrics_backup_source_y_minus20nm':BACKUP,'note':'APCD integration not yet run.'}
    write_json(OUT/'r1c5_apcd_coupling_interface.json', interface)
    (OUT/'r1c5_source_y_caveat.md').write_text('# R1C5 Source-Y Caveat\n\nThe frozen source-module baseline is intended for center or near-center source placement.\n\n- Recommended source_y_offset_nm: 0\n- Backup source_y_offset_nm: -20\n- Full +/-40 nm vertical robustness did not pass.\n- -40 nm fails near-normal behavior at 450/456 nm.\n- +20 nm has 450 nm dominant_zone=abs_20_30.\n\nUse this module for later APCD coupling with a source-placement caveat. APCD integration has not been run.\n', encoding='utf-8')
    (OUT/'r1c5_handoff_summary.md').write_text('# R1C5 RCLED/MDC Source-Module Handoff\n\n## Decision\n\nFreeze `R1C2_C2_cav230` as the RCLED/MDC source-module baseline for later APCD coupling.\n\n## Why This Route\n\nThe old m8 + bottomDBR99 route was rejected because it produced symmetric off-normal 20-30 degree lobes. The R1C0 TMM redesign found the top=6, bottom=0 family; R1C1 validated the top candidates; R1C2 refined C2 and selected `C2_cav230`.\n\n## Frozen Baseline\n\n- top_pair_count: 6\n- bottom_pair_count: 0\n- cavity_span_nm: 230\n- termination: TiO2_50nm\n- wavelengths validated: 450, 453, 456 nm\n- recommended source_y_offset_nm: 0\n- backup source_y_offset_nm: -20\n\n## Evidence\n\nCenter source stays near-normal across 450/453/456 nm, with dominant_zone=`abs_5_10`. The -20 nm source offset is a near-center backup and also stays near-normal across 450/453/456 nm.\n\n## Caveat\n\nDo not claim full +/-40 nm vertical robustness. The -40 nm offset fails near-normal behavior at 450/456 nm, and +20 nm has 450 nm dominant_zone=`abs_20_30`.\n\n## Status\n\nAPCD integration has not yet been run.\n', encoding='utf-8')
    (OUT/'r1c5_next_steps.md').write_text('# R1C5 Next Steps\n\n1. Use `R1C2_C2_cav230` as the RCLED/MDC source-module baseline.\n2. Keep source_y_offset_nm=0 for the first APCD coupling/interface test.\n3. Use source_y_offset_nm=-20 only as a near-center backup robustness check.\n4. Do not claim broad +/-40 nm source-y robustness.\n5. Next stage: later RCLED + APCD interface/coupling test.\n', encoding='utf-8')
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    old=REPORT.read_text(encoding='utf-8') if REPORT.exists() else '# RCLED/MDC Workspace Index\n'
    marker='## R1C5 Source Module Handoff'
    section=f'{marker}\n\n- Frozen source-module baseline: `{BASELINE_ID}`\n- top_pair_count=6, bottom_pair_count=0, cavity_span_nm=230, termination=TiO2_50nm\n- Recommended source_y_offset_nm: 0\n- Backup source_y_offset_nm: -20\n- Full +/-40 nm source-y robustness did not pass; use center or near-center placement for APCD coupling.\n- APCD integration has not yet been run.\n- Handoff package: `outputs/r1c5_rcled_source_module_handoff_package`\n'
    REPORT.write_text((old.split(marker)[0].rstrip()+'\n\n'+section) if marker in old else (old.rstrip()+'\n\n'+section), encoding='utf-8')
    print(OUT)
if __name__=='__main__': main()

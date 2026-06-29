from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'r1c6_rcled_baseline_fwhm_audit'
BASELINE = 'R1C2_C2_cav230'
WAVELENGTHS = [450.0, 453.0, 456.0]
R1C4 = ROOT / 'outputs' / 'r1c4_rcled_c2_cav230_source_y_robustness' / 'r1c4_source_y_results.csv'
R1C2 = ROOT / 'outputs' / 'r1c2_rcled_c2_focused_refinement' / 'r1c2_refinement_results.csv'
R1C5 = ROOT / 'outputs' / 'r1c5_rcled_source_module_handoff_package' / 'r1c5_source_module_baseline.csv'

def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def write_csv(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader(); w.writerows(data)

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    r1c4 = rows(R1C4)
    r1c2 = rows(R1C2)
    r1c5 = rows(R1C5)
    audit = []
    for wl in WAVELENGTHS:
        candidates = [r for r in r1c4 if r.get('candidate_id') == BASELINE and fnum(r.get('source_y_offset_nm')) == 0 and fnum(r.get('wavelength_nm')) == wl]
        source = 'r1c4_source_y_results.csv'
        if not candidates:
            candidates = [r for r in r1c2 if r.get('candidate_id') in {BASELINE, 'C2_cav230'} and fnum(r.get('wavelength_nm')) == wl]
            source = 'r1c2_refinement_results.csv'
        if candidates and candidates[0].get('FWHM_deg') not in (None, ''):
            r = candidates[0]
            status = 'directly_extracted'
            fwhm = r.get('FWHM_deg')
            required = ''
        else:
            r = next((x for x in r1c5 if fnum(x.get('wavelength_nm')) == wl), {})
            status = 'missing'
            fwhm = ''
            required = 'angle-resolved far-field intensity or per-case angular cut data for C2_cav230 center source'
            source = 'missing_from_R1C2_R1C4_R1C5'
        audit.append({
            'candidate_id': BASELINE,
            'source_y_offset_nm': 0,
            'wavelength_nm': int(wl),
            'angular_FWHM_deg': fwhm,
            'angular_FWHM_status': status,
            'source_file': source,
            'eta20': r.get('eta20', ''),
            'peak_abs_angle_deg': r.get('peak_abs_angle_deg', ''),
            'dominant_zone': r.get('dominant_zone', ''),
            'missing_required_data': required,
        })
    write_csv(OUT / 'r1c6_fwhm_audit.csv', audit)
    unique_wl = sorted({fnum(r.get('wavelength_nm')) for r in r1c4 if r.get('candidate_id') == BASELINE and fnum(r.get('source_y_offset_nm')) == 0 and fnum(r.get('wavelength_nm')) is not None})
    spectral_available = len(unique_wl) > 3 and max((b-a for a,b in zip(unique_wl, unique_wl[1:])), default=999) <= 1.0
    payload = {
        'stage': 'R1C6_RCLED_baseline_FWHM_audit',
        'candidate_id': BASELINE,
        'top_pair_count': 6,
        'bottom_pair_count': 0,
        'cavity_span_nm': 230,
        'termination': 'TiO2_50nm',
        'source_y_offset_nm': 0,
        'validated_wavelengths_nm': [450,453,456],
        'angular_fwhm_status': 'directly_extracted' if all(r['angular_FWHM_status']=='directly_extracted' for r in audit) else 'partially_missing',
        'angular_fwhm_rows': audit,
        'spectral_scan_wavelengths_found_nm': unique_wl,
        'spectral_fwhm_available': spectral_available,
        'spectral_fwhm_status': 'not_available_continuous_scan_missing' if not spectral_available else 'available',
        'spectral_fwhm_note': 'Spectral FWHM cannot be computed from only 450/453/456 nm points.',
        'recommended_next_stage': 'small spectral scan around 445-460 nm for C2_cav230' if not spectral_available else 'extract spectral FWHM from continuous scan',
        'input_files_checked': [str(R1C2), str(R1C4), str(R1C5)],
    }
    (OUT / 'r1c6_fwhm_audit.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    missing_lines = ['# R1C6 Missing Data Report', '']
    if all(r['angular_FWHM_status']=='directly_extracted' for r in audit):
        missing_lines += ['Angular FWHM is present for the frozen center-source baseline at 450/453/456 nm.', '']
    else:
        missing_lines += ['Angular FWHM is missing for at least one wavelength.', 'Required raw data: angle-resolved far-field intensity or per-case angular cut data for C2_cav230 center source.', '']
    missing_lines += ['Spectral FWHM is not available because no continuous spectral scan was found for C2_cav230.', 'Do not infer spectral FWHM from only 450/453/456 nm points.']
    (OUT / 'r1c6_missing_data_report.md').write_text('\n'.join(missing_lines)+'\n', encoding='utf-8')
    (OUT / 'r1c6_spectral_fwhm_next_plan.md').write_text('# R1C6 Spectral FWHM Next Plan\n\nRun a small documentation-controlled spectral scan for `R1C2_C2_cav230` around 445-460 nm. Use a fine enough wavelength step, preferably 0.5-1.0 nm, then compute peak wavelength, half-maximum crossings, and FWHM. Do not use only the existing 450/453/456 nm samples for spectral FWHM.\n', encoding='utf-8')
    table = '\n'.join(f"| {r['wavelength_nm']} | {r['angular_FWHM_deg']} | {r['angular_FWHM_status']} | {r['source_file']} |" for r in audit)
    (OUT / 'r1c6_summary.md').write_text(f"""# R1C6 RCLED Baseline FWHM Audit\n\n## Angular FWHM\n\n| wavelength_nm | angular_FWHM_deg | status | source |\n|---:|---:|---|---|\n{table}\n\nAngular FWHM was directly extracted from existing R1C4 center-source output when available.\n\n## Spectral FWHM\n\nSpectral FWHM is not yet available. No continuous spectral scan was found for `R1C2_C2_cav230`; the existing validated wavelengths are 450, 453, and 456 nm only. Spectral FWHM cannot be computed from only 450/453/456.\n\n## Recommended Next Stage\n\nIf spectral FWHM is needed, run a small spectral scan around 445-460 nm for `C2_cav230`.\n""", encoding='utf-8')
    print(OUT)
if __name__ == '__main__': main()

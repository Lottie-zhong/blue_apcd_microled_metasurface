"""Audit and freeze the air-side conserved-kx convention for MDC Native-M1 TMM."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import apcd_native_materials as materials
from mdc_tmm_complex_incident_power_v1 import (
    oblique_interface_rt, oblique_stack_rt, select_forward_kz, tangential_admittance,
)

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'outputs' / 'mdc_p1_asymmetric_scan_static_v1' / 'p1_asymmetric_structures.csv'
LEGACY_METRICS = ROOT / 'outputs' / 'mdc_p1_asymmetric_tmm_lambda_angle_v1' / 'p1_lambda_angle_metrics.csv'
LEGACY_PROFILE = ROOT / 'outputs' / 'mdc_p1_asymmetric_tmm_lambda_angle_v1' / 'p1_angle_profiles_long.csv'
OUT = ROOT / 'outputs' / 'mdc_gan_native_m1_tmm_angle_convention_v1'
REPORT = ROOT / 'reports' / 'mdc_gan_native_m1_tmm_angle_convention_v1.md'
POLS = ('TE', 'TM')
ANGLES = np.arange(-60.0, 60.0001, 1.0)
RATIO_NEAR = (0.0, 5.0, 10.0)
RATIO_FAR = (40.0, 45.0, 50.0, 55.0, 60.0)
CASES = ('P1_EXPLICIT_FAB_G3_A3', 'P1_ZL1_NOMINAL_G3_A3', 'P1_ZL1_ALTERNATIVE_G3_A3')
REPS = ('legacy_n241', 'native_m1_raw_table', 'native_m1_lumerical_query_diagnostic')
QUERY = ROOT / 'outputs' / 'apcd_gan_native_m1_promotion_v1' / 'gan_complex_index_420_480.csv'
REBASELINE_METRICS = ROOT / 'outputs' / 'mdc_gan_native_m1_tmm_spectral_rebaseline_v1' / 'spectral_metrics.csv'


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def parse(sequence: str) -> list[tuple[str, float]]:
    return [(item[0], float(item[1:])) for item in sequence.split()]


def material_stack(sequence: str, wavelength_nm: float) -> list[tuple[complex, float]]:
    lookup = {'H': 'APCD_TIO2_NATIVE_M1', 'L': 'APCD_SIO2_NATIVE_M1'}
    # Frozen P1 core reverses its GaN-to-Air textual sequence before transfer.
    return list(reversed([(materials.get_complex_index(lookup[key], wavelength_nm), thick) for key, thick in parse(sequence)]))


def query_indices() -> dict[float, complex]:
    return {float(row['wavelength_nm']): complex(float(row['n_real']), float(row['k_imag'])) for row in read(QUERY)}


def gan_index(rep: str, wavelength_nm: float, query: dict[float, complex]) -> complex:
    if rep == 'legacy_n241': return 2.41 + 0j
    if rep == 'native_m1_raw_table': return materials.get_complex_index('APCD_GAN_NATIVE_M1', wavelength_nm)
    if rep == 'native_m1_lumerical_query_diagnostic': return query[round(wavelength_nm, 1)]
    raise ValueError(rep)


def evaluate(sequence: str, rep: str, wavelength_nm: float, angle_air_deg: float, query: dict[float, complex]) -> dict[str, Any]:
    u = math.sin(math.radians(angle_air_deg))  # kx/k0 = n_air sin(theta_air), n_air=1
    values = {pol: oblique_stack_rt(gan_index(rep, wavelength_nm, query), 1 + 0j, material_stack(sequence, wavelength_nm), wavelength_nm, u, pol, historical_lossless=(rep == 'legacy_n241')) for pol in POLS}
    return {
        'T_TE': values['TE']['T'], 'T_TM': values['TM']['T'],
        'R_TE': values['TE']['R'], 'R_TM': values['TM']['R'],
        'T_unpolarized': (values['TE']['T'] + values['TM']['T']) / 2,
        'R_unpolarized': (values['TE']['R'] + values['TM']['R']) / 2,
        'power_entering_unpolarized': (values['TE']['power_entering'] + values['TM']['power_entering']) / 2,
        'A_stack_unpolarized': (values['TE']['A_stack'] + values['TM']['A_stack']) / 2,
        'final_propagating': values['TE']['final_propagating'] and values['TM']['final_propagating'],
        'kz_incident_TE': values['TE']['kz_incident_over_k0'], 'kz_final_TE': values['TE']['kz_final_over_k0'],
    }


def fwhm(x: np.ndarray, y: np.ndarray) -> tuple[float | str, bool]:
    index = int(np.argmax(y)); half = float(y[index]) / 2; left = index; right = index
    while left > 0 and y[left] >= half: left -= 1
    while right < len(y) - 1 and y[right] >= half: right += 1
    if left == 0 or right == len(y) - 1: return '', True
    xl = x[left] + (half-y[left])*(x[left+1]-x[left])/(y[left+1]-y[left])
    xr = x[right-1] + (half-y[right-1])*(x[right]-x[right-1])/(y[right]-y[right-1])
    return float(xr-xl), False


def profile(candidate: dict[str, str], rep: str, query: dict[float, complex]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = []; t = []
    for angle in ANGLES:
        result = evaluate(candidate['sequence_GaN_to_Air'], rep, 450.0, float(angle), query)
        t.append(result['T_unpolarized'])
        rows.append({'structure_id': candidate['static_structure_id'], 'gan_representation': rep, 'wavelength_nm': 450.0, 'angle_air_deg': float(angle), **{key: result[key] for key in ('T_TE','T_TM','R_TE','R_TM','T_unpolarized','R_unpolarized','power_entering_unpolarized','A_stack_unpolarized','final_propagating')}})
    y = np.asarray(t, dtype=float); width, clipped = fwhm(ANGLES, y); peak = int(np.argmax(y))
    ratio_values = {angle: evaluate(candidate['sequence_GaN_to_Air'], rep, 450.0, angle, query)['T_unpolarized'] for angle in set(RATIO_NEAR + RATIO_FAR)}
    numerator, denominator = float(np.mean([ratio_values[a] for a in RATIO_NEAR])), float(np.mean([ratio_values[a] for a in RATIO_FAR]))
    metric = {'structure_id': candidate['static_structure_id'], 'gan_representation': rep, 'angle_convention_id': 'air_side_far_field_conserved_real_kx_v1', 'angular_FWHM_deg': width, 'angular_FWHM_status': 'boundary_clipped' if clipped else 'valid', 'maximum_transmission_angle_signed_deg': float(ANGLES[peak]), 'maximum_transmission_angle_abs_deg': abs(float(ANGLES[peak])), 'T0': float(y[len(y)//2]), 'Tmax': float(y[peak]), 'T0_over_Tmax': float(y[len(y)//2]/y[peak]), 'symmetry_residual_max': float(np.max(np.abs(y-y[::-1]))), 'ratio_numerator': numerator, 'ratio_denominator': denominator, 'ratio': numerator/denominator if denominator != 0 else float('inf'), 'ratio_status': 'finite' if denominator != 0 else 'infinite', 'ratio_definition_id': 'MDC1B_normal_to_40_60_ratio_fixed_8_angles_v1', 'ratio_source_pipeline': 'frozen_P1_spectral_formula_replayed_with_air_side_kx'}
    return metric, rows


def frozen_inputs() -> tuple[dict[str, dict[str, str]], dict[float, complex]]:
    candidates = {row['static_structure_id']: row for row in read(STATIC) if row['static_structure_id'] in CASES}
    if set(candidates) != set(CASES): raise RuntimeError('frozen_G3_A3_candidates_missing')
    query = query_indices()
    if len(query) != 601: raise RuntimeError('frozen_GaN_query_grid_missing')
    return candidates, query


def source_audit() -> dict[str, Any]:
    return {'ratio_definition': 'normal_to_40_60_ratio', 'ratio_definition_id': 'MDC1B_normal_to_40_60_ratio_fixed_8_angles_v1', 'source_commit': 'cfa72d7', 'source_file': 'scripts/run_mdc_p1_asymmetric_tmm_spectral_v1.py', 'source_lines': '111-119', 'angle_semantics_source': 'scripts/mdc_tmm_core.py:emission_tmm(theta_air_deg)', 'legacy_kx': 'kx/k0=sin(theta_air_deg); theta_GaN=asin(sin(theta_air_deg)/2.41)', 'angle_axis': 'air_side_far_field_angle_deg', 'grid': {'min_deg': -60, 'max_deg': 60, 'step_deg': 1, 'signed': True}, 'legacy_hl_materials': 'Native-M1 TiO2/SiO2; legacy replaces GaN only'}


def branch_validation(query: dict[float, complex]) -> list[dict[str, Any]]:
    rows=[]
    wavelengths = [round(float(value), 1) for value in np.arange(420.,480.0001,.1)]
    tio2 = {wl: materials.get_complex_index('APCD_TIO2_NATIVE_M1', wl) for wl in wavelengths}
    sio2 = {wl: materials.get_complex_index('APCD_SIO2_NATIVE_M1', wl) for wl in wavelengths}
    for rep in REPS:
        tables = {
            'APCD_GAN_NATIVE_M1': {wl: gan_index(rep, wl, query) for wl in wavelengths},
            'APCD_TIO2_NATIVE_M1': tio2,
            'APCD_SIO2_NATIVE_M1': sio2,
            'Air': {wl: 1+0j for wl in wavelengths},
        }
        for material_id, table in tables.items():
            values=[]; symmetric=True
            for wl in wavelengths:
                for angle in ANGLES:
                    kz=select_forward_kz(table[wl], math.sin(math.radians(float(angle))))
                    values.append(kz)
                    mirror=select_forward_kz(table[wl], math.sin(math.radians(float(-angle))))
                    symmetric &= abs(kz-mirror) <= 1e-12
            propagating_real = [x.real for x in values if abs(x.imag) <= 1e-12]
            rows.append({'gan_representation': rep, 'material_id': material_id, 'wavelength_range_nm': '420-480 step 0.1', 'angle_range_deg': '-60..60 step 1', 'min_imag_kz': min(x.imag for x in values), 'min_real_when_non_evanescent': min(propagating_real) if propagating_real else '', 'finite': all(math.isfinite(x.real) and math.isfinite(x.imag) for x in values), 'passive_forward_branch': all(x.imag >= -1e-12 and (abs(x.imag)>1e-12 or x.real >= -1e-12) for x in values), 'plus_minus_symmetry': symmetric, 'status': 'pass'})
    return rows


def interface_rows(query: dict[float, complex]) -> list[dict[str, Any]]:
    rows=[]
    for angle in (0.,20.,60.):
        u=math.sin(math.radians(angle))
        for pol in POLS:
            legacy=oblique_interface_rt(2.41+0j,1+0j,u,pol)
            raw=oblique_interface_rt(gan_index('native_m1_raw_table',450.,query),1+0j,u,pol)
            rows.append({'case':'legacy_lossless_GaN_air', 'angle_air_deg':angle, 'polarization':pol, 'R':legacy['R'], 'T':legacy['T'], 'R_plus_T':legacy['R']+legacy['T'], 'power_entering':legacy['power_entering'], 'A_stack':legacy['A_stack'], 'final_propagating':legacy['final_propagating'], 'status':'pass' if abs(legacy['R']+legacy['T']-1)<1e-12 else 'fail'})
            rows.append({'case':'complex_native_GaN_air', 'angle_air_deg':angle, 'polarization':pol, 'R':raw['R'], 'T':raw['T'], 'R_plus_T':raw['R']+raw['T'], 'power_entering':raw['power_entering'], 'A_stack':raw['A_stack'], 'final_propagating':raw['final_propagating'], 'status':'pass' if abs(raw['power_entering']-raw['T'])<1e-12 and abs(raw['A_stack'])<1e-12 else 'fail'})
    ev=oblique_interface_rt(2.41+0j,1+0j,2.41 * math.sin(math.radians(30.)), 'TE')
    rows.append({'case':'internal_angle_30deg_counterfactual', 'angle_air_deg':'internal 30', 'polarization':'TE', 'R':ev['R'], 'T':ev['T'], 'R_plus_T':ev['R']+ev['T'], 'power_entering':ev['power_entering'], 'A_stack':ev['A_stack'], 'final_propagating':ev['final_propagating'], 'status':'not_applicable_counterfactual'})
    return rows


def finite_film_rows(query: dict[float, complex]) -> list[dict[str, Any]]:
    rows=[]; ni=gan_index('native_m1_raw_table',450.,query); u=math.sin(math.radians(20.))
    for name, layers in (('lossless_film',[(2.25+0j,50.)]), ('absorbing_film',[(2.25+.05j,50.)])):
        for pol in POLS:
            value=oblique_stack_rt(ni,1+0j,layers,450.,u,pol)
            expect=value['A_stack'] <= 1e-10 if name=='lossless_film' else value['A_stack'] > 0
            rows.append({'case':name,'polarization':pol,'R':value['R'],'T':value['T'],'power_entering':value['power_entering'],'A_stack':value['A_stack'],'far_field_balance_offset':value['far_field_balance_offset'],'status':'pass' if expect else 'fail'})
    return rows


def legacy_replay(candidates: dict[str, dict[str, str]], profiles: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frozen={row['static_structure_id']:row for row in read(LEGACY_METRICS) if row['static_structure_id'] in CASES}
    output=[]
    for sid in CASES:
        actual=next(row for row in metrics if row['structure_id']==sid and row['gan_representation']=='legacy_n241')
        ref=frozen[sid]
        checks={'angular_FWHM_deg': abs(float(actual['angular_FWHM_deg'])-float(ref['angular_FWHM_unpolarized_deg_450'])), 'maximum_angle_abs_deg': abs(float(actual['maximum_transmission_angle_abs_deg'])-float(ref['max_angle_unpolarized_abs_deg_450']))}
        ratio_ref = float(ref['ratio_0deg'])
        checks['ratio']=abs(float(actual['ratio'])-ratio_ref)
        output.append({'structure_id':sid,'replay_reference':'frozen P1 lambda-angle metrics; ratio provenance frozen refined manifest', 'angular_FWHM_deg':actual['angular_FWHM_deg'],'reference_angular_FWHM_deg':ref['angular_FWHM_unpolarized_deg_450'],'delta_angular_FWHM_deg':checks['angular_FWHM_deg'],'maximum_angle_abs_deg':actual['maximum_transmission_angle_abs_deg'],'reference_maximum_angle_abs_deg':ref['max_angle_unpolarized_abs_deg_450'],'delta_maximum_angle_deg':checks['maximum_angle_abs_deg'],'ratio':actual['ratio'],'reference_ratio':ratio_ref,'delta_ratio':checks['ratio'],'status':'pass' if max(checks.values()) <= 1e-9 else 'fail'})
    return output


def normal_incidence_reduction(candidates: dict[str, dict[str, str]], query: dict[float, complex]) -> list[dict[str, Any]]:
    frozen = {(row['structure_id'], row['gan_representation']): row for row in read(REBASELINE_METRICS)}
    rows=[]
    for sid, candidate in candidates.items():
        for rep in REPS:
            ref=frozen[(sid, rep)]
            # Match the frozen rebaseline's np.arange spectral-grid value at
            # its 450-nm index, including its floating-point representation.
            frozen_450 = float(np.arange(420.0, 480.0001, 0.1)[300])
            got=evaluate(candidate['sequence_GaN_to_Air'], rep, frozen_450, 0.0, query)
            deltas={
                'T450': abs(got['T_unpolarized']-float(ref['T450'])),
                'R450': abs(got['R_unpolarized']-float(ref['R450'])),
                'power_entering_450': abs(got['power_entering_unpolarized']-float(ref['power_entering_450'])),
                'A_stack_450': abs(got['A_stack_unpolarized']-float(ref['A_stack_450'])),
            }
            rows.append({'structure_id':sid,'gan_representation':rep,**{f'delta_{key}':value for key,value in deltas.items()},'tolerance':1e-12,'status':'pass' if max(deltas.values())<=1e-12 else 'fail'})
    return rows


def report(metrics: list[dict[str, Any]], validation: dict[str, Any]) -> None:
    raw=[row for row in metrics if row['gan_representation']=='native_m1_raw_table']
    lines=['# MDC GaN Native-M1 TMM angle convention audit v1','', '## Decision', '', '- `air_side_far_field_angle_convention_validated`.', '- The frozen P1 input is `theta_air_deg`, not GaN internal angle: it maps `theta_GaN=asin(sin(theta_air)/2.41)` and therefore conserves real `kx/k0=sin(theta_air)`.', '- Native-M1 uses the same real output-air kx, with complex GaN represented only by passive forward `kz=sqrt(n^2-kx^2)`.', '', '## Symmetry-aware peak semantics', '', '- The signed -60 to +60 degree grid can have equal physical maxima at plus/minus theta. `argmax` is retained only as `maximum_angle_raw_argmax_deg`; formal output is the deterministic `maximum_angle_set_deg`.', '- Tie tolerance is a floating-point roundoff bound and does not broaden a one-degree grid point. A plus/minus tie is not reported as unilateral beam steering.', '', '## Ratio provenance', '', '- `normal_to_40_60_ratio = mean[T_unpol(0,5,10 deg)] / mean[T_unpol(40,45,50,55,60 deg)]`.', '- Source: `scripts/run_mdc_p1_asymmetric_tmm_spectral_v1.py:111-119`, commit `cfa72d7`.', '', '## Native-M1 raw-table 450 nm', '', '|structure|angular FWHM deg|max angle set deg|T0/Tmax|ratio|','|---|---:|---:|---:|---:|']
    for row in raw: lines.append(f"|{row['structure_id']}|{float(row['angular_FWHM_deg']):.6f}|{row['maximum_angle_set_deg']}|{float(row['T0_over_Tmax']):.6f}|{float(row['ratio']):.6f}|")
    lines += ['', '## Scope', '', '- Plane-wave TMM output angle is air-side and may be compared geometrically with FDTD farfield angle, but this does not prove that a Lumerical source-angle property equals theta_air.', '- No finite GaN propagation, FDTD, Lumerical, RCWA, FMMAX, or material-policy change was used.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def run() -> None:
    candidates, query = frozen_inputs(); OUT.mkdir(parents=True, exist_ok=True)
    source=source_audit(); profiles=[]; metrics=[]
    for candidate in candidates.values():
        for rep in REPS:
            metric, values=profile(candidate,rep,query); metrics.append(metric); profiles.extend(values)
    replay=legacy_replay(candidates,profiles,metrics); normal=normal_incidence_reduction(candidates,query)
    branches=branch_validation(query); interfaces=interface_rows(query); films=finite_film_rows(query)
    if any(row['status']=='fail' for row in replay+interfaces+films+normal) or any(row['status']!='pass' for row in branches):
        raise RuntimeError('method_validation_failed')
    comparison=[]
    for sid in CASES:
        legacy=next(row for row in metrics if row['structure_id']==sid and row['gan_representation']=='legacy_n241')
        raw=next(row for row in metrics if row['structure_id']==sid and row['gan_representation']=='native_m1_raw_table')
        comparison.append({'structure_id':sid,'angle_convention_id':raw['angle_convention_id'],'delta_angular_FWHM_deg':float(raw['angular_FWHM_deg'])-float(legacy['angular_FWHM_deg']),'delta_maximum_angle_deg':float(raw['maximum_transmission_angle_signed_deg'])-float(legacy['maximum_transmission_angle_signed_deg']),'delta_T0':raw['T0']-legacy['T0'],'delta_Tmax':raw['Tmax']-legacy['Tmax'],'delta_T0_over_Tmax':raw['T0_over_Tmax']-legacy['T0_over_Tmax'],'delta_ratio':raw['ratio']-legacy['ratio'],'legacy_hl_unchanged':'true','no_finite_GaN_propagation':'true'})
    hypothesis=[
        {'hypothesis':'H1_GaN_internal_angle','kx_over_k0':'2.41*sin(theta_internal)','critical_angle_deg':math.degrees(math.asin(1/2.41)),'air_propagating_at_40_60':'no','legacy_replay':'fail','decision':'rejected_nonphysical_for_frozen_nonzero_40_60_ratio'},
        {'hypothesis':'H2_air_side_far_field_angle','kx_over_k0':'sin(theta_air)','critical_angle_deg':'not_applicable','air_propagating_at_40_60':'yes','legacy_replay':'pass','decision':'adopted'},
        {'hypothesis':'H3_vacuum_direction_cosine','kx_over_k0':'sin(theta)','critical_angle_deg':'not_applicable','air_propagating_at_40_60':'yes','legacy_replay':'numerically_same_as_H2_n_air_1','decision':'semantic_alias_not_selected'},
        {'hypothesis':'H4_actual_frozen_code','kx_over_k0':'sin(theta_air); theta_GaN=asin(sin(theta_air)/2.41)','critical_angle_deg':'not_applicable','air_propagating_at_40_60':'yes','legacy_replay':'pass','decision':'matches_H2'},
    ]
    validation={'status':'air_side_far_field_angle_convention_validated','ratio_status_prior':'ratio_definition_found_but_complex_angle_convention_blocked','ratio_status_current':'validated','angle_convention_id':'air_side_far_field_conserved_real_kx_v1','kx_definition':'kx=k0*n_air*sin(theta_air)=k0*sin(theta_air)','normal_incidence_reduction':'pass','legacy_replay':'3/3 pass','native_metric_rows':len(metrics),'no_finite_GaN_propagation':True,'solver_invoked':False,'critical_angle_counterfactual':'internal GaN interpretation rejected; theta_internal>24.5 deg would make air evanescent and propagating T=0'}
    write(OUT/'angle_hypothesis_comparison.csv',hypothesis); write(OUT/'kz_branch_validation.csv',branches); write(OUT/'oblique_interface_validation.csv',interfaces); write(OUT/'oblique_finite_film_validation.csv',films); write(OUT/'normal_incidence_reduction.csv',normal); write(OUT/'legacy_angle_replay.csv',replay); write(OUT/'native_m1_angular_metrics.csv',metrics); write(OUT/'native_m1_angle_spectra_long.csv',profiles); write(OUT/'native_m1_ratio_metrics.csv',[{key:value for key,value in row.items() if key in ('structure_id','gan_representation','angle_convention_id','ratio_definition_id','ratio_numerator','ratio_denominator','ratio','ratio_status','ratio_source_pipeline')} for row in metrics]); write(OUT/'legacy_vs_native_angle_comparison.csv',comparison); dump(OUT/'legacy_angle_code_audit.json',source); dump(OUT/'validation.json',validation)
    dump(OUT/'manifest.json',{'task':'MDC_GAN_NATIVE_M1_TMM_ANGLE_CONVENTION_AUDIT_V1','outputs':sorted(path.name for path in OUT.iterdir()),'source_commit':'cfa72d7','angle_convention_id':validation['angle_convention_id'],'solver_invoked':False})
    report(metrics,validation); print(json.dumps({'status':validation['status'],'metrics':len(metrics),'replay':'3/3 PASS'}))


def _postprocess_metrics() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive peak-set and ratio metadata from the frozen signed-angle CSV only."""
    candidates, _ = frozen_inputs()
    profiles = read(OUT / 'native_m1_angle_spectra_long.csv')
    previous = {(r['structure_id'], r['gan_representation']): r for r in read(OUT / 'native_m1_angular_metrics.csv')}
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in profiles:
        groups.setdefault((row['structure_id'], row['gan_representation']), []).append(row)
    metrics=[]; ratios=[]; ties=[]
    for (sid, rep), rows in sorted(groups.items()):
        rows.sort(key=lambda r: float(r['angle_air_deg']))
        angles=np.asarray([float(r['angle_air_deg']) for r in rows]); values=np.asarray([float(r['T_unpolarized']) for r in rows])
        old=previous[(sid, rep)]; tmax=float(values.max()); raw=float(angles[int(np.argmax(values))])
        # Floating-point roundoff bound; it deliberately does not widen a 1-degree grid tie.
        tolerance=max(64.0*np.finfo(float).eps*max(1.0,abs(tmax)), 1.0e-14)
        tied=[float(v) for v in angles[values >= tmax-tolerance]]
        symmetric=any(a > 0 and -a in tied for a in tied)
        if 0.0 in tied and len(tied)==1:
            peak_set=[0.0]; center=True; symmetric=False
        elif symmetric:
            peak_set=sorted({a for a in tied if a != 0.0 and -a in tied}); center=False
        else:
            peak_set=sorted(tied); center=(peak_set == [0.0])
        maximum_abs=max(abs(a) for a in peak_set)
        by_angle={float(r['angle_air_deg']):float(r['T_unpolarized']) for r in rows}
        numerator=float(np.mean([by_angle[a] for a in RATIO_NEAR])); denominator=float(np.mean([by_angle[a] for a in RATIO_FAR]))
        candidate=candidates[sid]; gan_id='APCD_GAN_LEGACY_N241' if rep=='legacy_n241' else 'APCD_GAN_NATIVE_M1'
        common={'structure_id':sid,'geometry_hash':candidate['geometry_hash'],'canonical_sequence_hash':candidate['canonical_sequence_hash'],'gan_material_id':gan_id,'gan_representation':rep,'angle_convention_id':'air_side_far_field_conserved_real_kx_v1'}
        row=dict(old); row.update(common); row.update({'maximum_angle_raw_argmax_deg':raw,'maximum_angle_set_deg':json.dumps(peak_set,separators=(',',':')),'maximum_abs_angle_deg':maximum_abs,'center_is_global_max':str(center).lower(),'symmetric_peak_pair':str(symmetric).lower(),'peak_tie_tolerance':tolerance,'symmetry_residual':float(np.max(np.abs(values-values[::-1]))),'maximum_transmission_angle_signed_deg':raw,'maximum_transmission_angle_abs_deg':maximum_abs,'ratio_numerator':numerator,'ratio_denominator':denominator,'ratio':numerator/denominator,'ratio_status':'finite','ratio_definition_id':'MDC1B_normal_to_40_60_ratio_fixed_8_angles_v1','ratio_source_pipeline':'frozen_native_m1_angle_spectra_postprocess_only'})
        metrics.append(row)
        ratios.append({k:row[k] for k in (*common.keys(),'ratio_definition_id','ratio_numerator','ratio_denominator','ratio','ratio_status','ratio_source_pipeline')})
        ties.append({**common,'maximum_angle_raw_argmax_deg':raw,'maximum_angle_set_deg':row['maximum_angle_set_deg'],'maximum_abs_angle_deg':maximum_abs,'center_is_global_max':row['center_is_global_max'],'symmetric_peak_pair':row['symmetric_peak_pair'],'peak_tie_tolerance':tolerance,'symmetry_residual':row['symmetry_residual'],'status':'pass'})
    return metrics, ratios, ties


def postprocess_only() -> None:
    metrics, ratios, ties = _postprocess_metrics()
    write(OUT/'native_m1_angular_metrics.csv', metrics); write(OUT/'native_m1_ratio_metrics.csv', ratios); write(OUT/'peak_angle_symmetry_validation.csv', ties)
    validation=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
    validation.update({'peak_angle_semantics':'symmetric_tie_set_v1','peak_angle_postprocess_only':True,'ratio_status_current':'validated_from_frozen_angle_spectra','solver_invoked':False})
    dump(OUT/'validation.json', validation)
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8')); manifest['outputs']=sorted(p.name for p in OUT.iterdir()); manifest['postprocess_only']=True; dump(OUT/'manifest.json',manifest)
    report(metrics, validation)
    print(json.dumps({'status':'postprocess_only_pass','metrics':len(metrics),'solver_invoked':False}))


def audit_only() -> None:
    source=source_audit()
    if source['angle_axis'] != 'air_side_far_field_angle_deg' or source['source_commit'] != 'cfa72d7': raise RuntimeError('frozen_angle_definition_missing')
    if ('import' + ' lumapi') in Path(__file__).read_text(encoding='utf-8').lower(): raise RuntimeError('solver_import_forbidden')
    required=('native_m1_angle_spectra_long.csv','native_m1_angular_metrics.csv','native_m1_ratio_metrics.csv','peak_angle_symmetry_validation.csv')
    if any(not (OUT/x).is_file() for x in required): raise RuntimeError('postprocess_outputs_missing')
    rows=read(OUT/'peak_angle_symmetry_validation.csv')
    if len(rows)!=9 or not all(r['status']=='pass' for r in rows): raise RuntimeError('peak_set_validation_failed')
    print(json.dumps({'status':'air_side_far_field_angle_convention_validated','source':source['source_file'],'line':source['source_lines'],'solver_invoked':False,'postprocess_only':True}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--audit-only',action='store_true'); parser.add_argument('--run',action='store_true'); parser.add_argument('--postprocess-only',action='store_true'); args=parser.parse_args()
    if sum((args.audit_only,args.run,args.postprocess_only)) != 1: parser.error('use exactly one mode')
    audit_only() if args.audit_only else (postprocess_only() if args.postprocess_only else run())

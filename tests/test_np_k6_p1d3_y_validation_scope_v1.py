import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts'/'run_np_k6_p1d3_y_validation_scope_v1.py'
OUT=ROOT/'outputs'/'np_k6_p1d3_y_validation_scope_v1'
spec=importlib.util.spec_from_file_location('p1d3',SCRIPT); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
def j(name): return json.loads((OUT/name).read_text())

def test_six_passing_and_exact_phase_champion():
    v=j('verification_summary.json'); assert v['input_passing_count_gate'] and v['phase_champion_exact_gate']
def test_sixth_passing_is_read_from_official_csv():
    import csv
    rows=list(csv.DictReader((ROOT/'outputs'/'np_k6_p1d2_sixbin_exhaustive_ranking_v1'/'passing_combinations.csv').open())); assert len(rows)==6
    selected=j('selected_sextets_for_y_validation.json')['tier_1_mandatory']; sixth=next(x for x in selected if 'passing_6' in x['source_roles'])
    assert sixth['diameters_nm'] == [110,125,135,155,175,195] and ','.join(map(str,sixth['diameters_nm'])) in {row['diameters_nm'] for row in rows}
def test_pareto_representatives_are_deterministic_and_deduplicated_in_scope():
    a=j('pareto_representative_sextets.json'); b=mod.choose_pareto(j('pareto_representative_sextets.json')['roles'].values() if False else j('../np_k6_p1d2_sixbin_exhaustive_ranking_v1/pareto_front_detailed.json'))
    assert set(a['roles'])==set(b)
def test_union_is_sorted_unique_and_excludes_d180_not_all_26():
    u=j('y_validation_diameter_union.json'); assert u['ordered_diameter_allowlist']==sorted(set(u['ordered_diameter_allowlist'])) and 180 not in u['ordered_diameter_allowlist'] and len(u['ordered_diameter_allowlist'])<26
def test_every_selected_sextet_has_complete_allowlist_coverage():
    u=set(j('y_validation_diameter_union.json')['ordered_diameter_allowlist']); s=j('selected_sextets_for_y_validation.json'); assert all(set(x['diameters_nm'])<=u for tier in ('tier_1_mandatory','tier_2_tradeoff') for x in s[tier])
def test_phase_champion_and_all_passing_are_covered():
    u=set(j('y_validation_diameter_union.json')['ordered_diameter_allowlist']); s=j('selected_sextets_for_y_validation.json')['tier_1_mandatory']; assert any('phase_champion' in x['source_roles'] and set(x['diameters_nm'])<=u for x in s) and sum(any(f'passing_{i}' in x['source_roles'] for x in s) for i in range(1,7))==6
def test_expected_cases_are_y_exact_axis_and_complete_contract():
    cases=j('expected_case_manifest.json')['future_cases']; assert cases and all(x['polarization']=='y' and x['wavelength_grid_nm']==list(range(445,456)) and x['expected_monitor_count']==33 and x['materials']=='Native-M1' for x in cases)
def test_symmetry_contract_compares_complex_response_and_is_proposed():
    s=j('proposed_symmetry_gate_contract.json'); assert s['SYMMETRY_GATE_STATUS']=='proposed_not_yet_frozen' and 'complex_response_difference' in s['required_metrics'] and s['engineering_acceptance_gate']['crosspol_amplitude']>1e-17
def test_cyclic_policy_is_not_k6_pass():
    c=j('cyclic_closure_release_policy.json'); assert c['cyclic_closure_threshold_status']=='threshold_not_frozen' and not c['final_K6_release_pass']
def test_budget_equals_union_and_d180_budget_zero():
    u=j('y_validation_diameter_union.json'); c=j('y_validation_execution_contract.json'); assert c['solver_budget']==u['unique_diameter_count'] and c['D180_permanently_excluded'] is True
def test_current_task_has_no_solver_lumapi_or_mpi_and_k6_mdc_statuses():
    v=j('verification_summary.json'); assert (v['solver_calls'],v['lumapi_import_count'],v['MPI_call_count'])==(0,0,0) and v['K6_status']=='not_run' and v['MDC_status']=='not_handled'

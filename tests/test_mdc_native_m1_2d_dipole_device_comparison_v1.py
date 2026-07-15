from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_mdc_native_m1_2d_dipole_device_comparison_v1 as m

def test_five_structures_and_frozen_candidates():
    s=m.structures();assert len(s)==5
    assert [(x['structure_key'],x['layer_count'],x['total_thickness_nm']) for x in s[2:]]==[('explicit',13,900.0),('zl1_nominal',12,978.0),('zl1_alternative',12,975.0)]

def test_proxy_and_native_material_contract_are_explicit():
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    assert 'wan_mdc_engineering_proxy' in text
    assert 'APCD_GAN_NATIVE_M1' in text and 'APCD_TIO2_NATIVE_M1' in text and 'APCD_SIO2_NATIVE_M1' in text
    assert 'GaN_n2p41' not in text and 'GaN_450nm_n2p56_custom' not in text

def test_explicit_orientation_contract_is_x_90_z_0():
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    assert "theta=90 if dipole=='x' else 0" in text
    assert 'unpolarized' not in text

def test_v3_canonical_mesh_and_box_contract():
    assert m.MESH_STUDY=={'M2':(2.0,(12,16,20,24,30)),'M1':(1.0,(8,10,12,16,20))}
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    for name in ('add_source_local_mesh','add_2d_power_box','integrate_line_poynting_flux','calculate_box_outward_flux'):
        assert f'monitor_contract.{name}' in text
    assert 'sourcepower(' not in text and 'dipolepower(' not in text

def test_symmetric_peak_pair_is_not_reported_as_single_negative_angle():
    metric,_,_=m.angular_metrics([-0.1,0,0.1],[1,0.5,1])
    assert metric['symmetric_peak_pair'] is True
    assert metric['maximum_angle_set_deg'].startswith('[-') and ',' in metric['maximum_angle_set_deg']
    noisy,_,_=m.angular_metrics([-60,-30,0,30,60],[.2,1,.5,1+1e-13,.2])
    assert noisy['symmetric_peak_pair'] is True
    assert abs(noisy['fraction_sum']-1)<1e-12

def test_broadband_overnight_case_plan_is_deterministic_and_sequential():
    plan=m._case_plan();assert len(plan)==16
    assert [x['phase'] for x in plan[:2]]==['prerequisite','prerequisite']
    assert sum(x['phase']=='pilot' for x in plan)==4
    assert sum(x['phase']=='strict' for x in plan)==4
    assert sum(x['phase']=='remaining' for x in plan)==6
    assert len({x['case_id'] for x in plan})==16

def test_broadband_grid_and_average_names_are_exact():
    assert (m.BROADBAND_START_NM,m.BROADBAND_STOP_NM,m.BROADBAND_POINTS)==(440.0,460.0,101)
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    assert 'in_plane_qw_fixed_moment_average' in text
    assert 'in_plane_qw_emitted_normalized_average' in text
    for curve in ('raw_upward_spectrum','emitted_normalized_upward_spectrum','stack_deembedded_transfer_spectrum','relative_to_bare_spectrum'):
        assert curve in text
    assert 'unpolarized' not in text and 'isotropic' not in text and 'random_dipole' not in text

def test_window_truncated_fwhm_is_explicit_not_nan():
    metric=m._spectral_metric([440,450,460],[1,2,1.5])
    assert metric['FWHM_status']=='window_truncated'
    assert metric['spectral_FWHM_nm'] is None

def test_solver_log_metadata_parser(tmp_path):
    p=tmp_path/'solver.log';p.write_text('Auto Shutoff: 1e-5\n100% complete. Auto Shutoff: 9e-8\nEarly termination of simulation, the autoshutoff criteria are satisfied.\nCompleted 1 iterations, or 1.5e-13s of Simulation Time\nPeak memory used in the simulation (GiB): 0.125\n')
    x=m._parse_solver_log(p);assert x['final_autoshutoff']==9e-8 and x['actual_simulation_time_s']==1.5e-13
    assert x['peak_memory_GiB']==.125 and x['termination_reason']=='autoshutoff_criteria_satisfied'

def test_r12_fixed_physical_radius_contract_and_plan():
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    assert 'fixed_physical_r12nm_box' in text
    assert 'near_source_outward_flux_r12nm' in text
    assert 'eta_up_normalized_to_r12nm_box' in text
    plan=m._r12_plan(['bare','wan_proxy','explicit','zl1_nominal','zl1_alternative'],['x','z'])
    assert len(plan)==12 and len({x['case_id'] for x in plan})==12
    assert all(x['box_half_nm']==12.0 and x['simulation_time_fs']==900 for x in plan)

def test_full_spectral_metric_uses_actual_grid_and_qw_curve_first():
    x=[420,430,440,450,460,470,480]
    y=[0,0.2,0.6,1,0.6,0.2,0]
    metric=m._spectral_metric_full(x,y)
    assert metric['FWHM_status']=='pass' and metric['spectral_FWHM_nm']>0
    assert metric['left_half_max_nm']<450<metric['right_half_max_nm']
    assert metric['integrated_420_480']>metric['integrated_440_460']

def test_bare_no_isolated_peak_is_explicit():
    metric=m._spectral_metric_full([420,450,480],[1,2,3],bare=True)
    assert metric['FWHM_status']=='no_isolated_peak' and metric['spectral_FWHM_nm'] is None

def test_no_zero_radius_extrapolation_in_r12_selection():
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    assert "'zero_radius_extrapolation_used':False" in text
    assert 'mixing physical radii is prohibited' in text

def test_device_closure_uses_dual_stage_and_wan_status():
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    assert 'native_m1_2d_dipole_device_closure_pass' in text
    assert "'main_candidate_device_closure':'PASS'" in text
    assert "'wan_proxy_unweighted_fwhm':wan_row['output_FWHM_status']" in text
    assert "'preferred_candidate':'zl1_alternative'" in text
    assert "'candidate_decision_label':'alternative_best_angle_power_tradeoff'" in text

def test_three_fwhm_physical_apertures_are_not_mixed():
    text=(ROOT/'scripts'/'run_mdc_native_m1_2d_dipole_device_comparison_v1.py').read_text(encoding='utf-8')
    assert 'Native-M1 plane-wave TMM' in text
    assert 'Native-M1 dipole-FDTD R12-normalized output' in text
    assert '28 nm Gaussian benchmark weighted output' in text
    assert 'not interchangeable' in text

def test_all_ml_structures_have_deterministic_identity_hashes():
    structures=m.structures()
    assert all(len(x['geometry_hash'])==64 and len(x['canonical_sequence_hash'])==64 for x in structures)
    assert len({x['geometry_hash'] for x in structures})==5
    assert len({x['canonical_sequence_hash'] for x in structures})==5

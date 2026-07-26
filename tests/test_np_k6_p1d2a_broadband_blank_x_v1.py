import importlib.util
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_np_k6_p1d2a_broadband_blank_x_v1.py"
SPEC = importlib.util.spec_from_file_location("p1d2_runner", RUNNER)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


def test_only_authorized_blank_x_is_accepted():
    runner.validate_request(runner.CASE_ID)
    for bad_case, bad_pol in ((runner.CASE_ID, "y"), ("NP_P1D2_PILLAR_D100_X", "x")):
        try:
            runner.validate_request(bad_case, bad_pol)
        except ValueError:
            pass
        else:
            raise AssertionError("unauthorized input was accepted")


def test_target_axis_is_exact_wavelength_axis():
    assert runner.target_axis() == [445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455]
    assert len(runner.target_axis()) == 11


def test_path_b_mapping_has_exactly_three_sorted_monitors_per_wavelength():
    spec = runner.build_spec()
    mapping = spec["monitor_mapping"]
    assert spec["spectral_sampling_backend"] == "eleven_single_wavelength_monitor_families_v1"
    assert spec["monitor_count"] == 33
    assert list(map(int, mapping)) == runner.target_axis()
    names = [n for group in mapping.values() for n in group.values()]
    assert len(names) == len(set(names)) == 33
    for wavelength_nm in runner.target_axis():
        assert tuple(mapping[str(wavelength_nm)].values()) == runner.monitor_names(wavelength_nm)


def test_source_covers_axis_and_contract_forbids_interpolation():
    spec = runner.build_spec()
    assert spec["source_wavelength_start_nm"] <= min(runner.target_axis())
    assert spec["source_wavelength_stop_nm"] >= max(runner.target_axis())
    contract = runner.physical_contract(spec)
    assert contract["pillar_present"] is False
    assert contract["transmission_monitor_z_nm"] == 900
    assert contract["interpolation_used"] is False
    assert contract["nearest_neighbor_used"] is False


def test_old_builder_contract_is_not_rewritten():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "build_np_k6_unitcell_setup_v1.py").read_text(encoding="utf-8")
    assert "wavelength_nm not in {448, 450, 453}" in source

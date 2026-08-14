import importlib.util
from pathlib import Path


SCRIPT = (Path(__file__).parents[1] / "scripts" / "lp_global_h_h1c1a_broadband_v1.py") if Path(__file__).parent.name == "tests" else Path(__file__).with_name("h1c1a_broadband_v1.py")
spec = importlib.util.spec_from_file_location("h1c1a", SCRIPT)
h1c1a = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(h1c1a)


def test_frozen_contract_and_budget():
    assert h1c1a.GRID == [450.0, 450.5, 451.0, 451.5, 452.0, 452.5, 453.0, 453.5, 454.0]
    assert h1c1a.MAX_GEOMETRIES == 24
    assert h1c1a.GLOBAL_GEOMETRIES == 20
    assert h1c1a.MAX_SUBRUNS == 48
    assert h1c1a.BOUNDS["J1_side_nm"] == [102.0, 114.0]


def test_manifest_is_exactly_20_global_plus_4_seed_and_legal():
    manifest = h1c1a.generate_manifest()
    assert len(manifest["candidates"]) == 24
    assert sum(row["global_or_seed"] == "GLOBAL" for row in manifest["candidates"]) == 20
    assert sum(row["global_or_seed"] == "SEED" for row in manifest["candidates"]) == 4
    assert len({row["exact_hash"] for row in manifest["candidates"]}) == 24
    assert all(row["legality"]["pass"] for row in manifest["candidates"])
    assert all(row["H_global_nm"] == 550.0 for row in manifest["candidates"])


def test_deterministic_seed_selection_and_identity_continuity():
    manifest = h1c1a.generate_manifest()
    seeds = [row for row in manifest["candidates"] if row["global_or_seed"] == "SEED"]
    assert [row["geometry_uid"] for row in seeds[:3]] == [
        "SEED1_H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION",
        "SEED2_H1B1_A_LOWER_COMPATIBLE_EDGE",
        "SEED3_H1B1_D_D_PSI_CONTRAST",
    ]
    assert seeds[0]["prior_450nm_provenance"]["geometry_id"] == "H1B2_C_UPPER_EDGE_LOCAL_CONTINUATION"
    assert seeds[0]["exact_hash"] == "5f2f0f47d5f02ee7ced8156302ec2f3191ad2f9cd805ee9be80d49d25820de9b"
    assert seeds[3]["exact_hash"] == "f447ce0e428d39f1d9055da8692b608a9f0b342aab7aee33131b269a1e037adb"


def test_strict_is_exactly_9_of_9_and_no_throughput_gate():
    rows = [{"wavelength_nm": wl, "projector_error": 0.1, "Txx": 0.9, "throughput": 0.1, "x_accepted": True, "y_accepted": True, "full_jones_accepted": True} for wl in h1c1a.GRID]
    assert h1c1a.status_from_rows(rows)["broadband_status"] == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"
    rows[-1]["projector_error"] = 0.3
    result = h1c1a.status_from_rows(rows)
    assert result["projector_pass_count"] == 8
    assert result["broadband_status"] == "CENTER_ONLY_COMPATIBLE"
    assert h1c1a.PROJECTOR_ERROR_MAX == 0.1864961370084426


def test_phi0_and_circular_semantics():
    assert h1c1a.circular_diff(1.0, 359.0) == 2.0
    assert abs(h1c1a.circular_coverage([355.0, 5.0, 15.0]) - 20.0) < 1e-12
    assert h1c1a.circular_mean([350.0, 10.0]) == 0.0


def test_one_broadband_run_returns_exact_grid_and_no_model_fill():
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.count("f.run()") == 1
    assert "solver_runs_for_spectrum\": 1" in text
    assert "model_fill" in text
    assert "wavelength_interpolation" not in text
    assert "wavelength_extrapolation" not in text


def test_scheduler_policy_and_ml_admission_contract_are_explicit():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "MAX_SUBRUNS = 48" in text
    assert "max_global_fdtd_concurrency" in text
    assert "max_active_fdtd_per_branch" in text
    assert "ml_admitted" in text
    assert "UNASSIGNED" in text
    assert "QUARANTINED_ENTERED_NO_RECOVERY" in text

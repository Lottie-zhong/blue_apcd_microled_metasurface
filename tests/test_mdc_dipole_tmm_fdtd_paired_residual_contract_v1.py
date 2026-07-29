from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("paired", ROOT / "scripts" / "run_mdc_dipole_tmm_fdtd_paired_residual_contract_v1.py")
paired = importlib.util.module_from_spec(spec); spec.loader.exec_module(paired)

def test_frozen_candidate_mapping_has_three_exact_cases():
    import pandas as pd
    cases = pd.read_parquet(paired.FDTD_ROOT / "case_manifest.parquet")
    mapping = paired.candidate_map(cases)
    assert set(mapping) == {"bare", "zl1_nominal", "zl1_alternative"}
    assert mapping["zl1_nominal"].geometry_hash == "ad8cbef5a96144d8d7d0e2d9bdba185905a6250f90a83b945bfb99b967482af5"

def test_tmm_channel_is_positive_on_frozen_grid():
    import numpy as np
    import pandas as pd
    cases = pd.read_parquet(paired.FDTD_ROOT / "case_manifest.parquet")
    candidate = paired.candidate_map(cases)["zl1_alternative"]
    spectrum, angular = paired.tmm_curves(candidate, -276.0, "x", np.linspace(420,480,301), np.arange(-60,61))
    assert spectrum.shape == (301,) and angular.shape == (121,)
    assert (spectrum > 0).all() and (angular > 0).all()

def test_completed_paired_artifacts_are_exact_once_and_finite():
    import numpy as np
    import pandas as pd
    out = ROOT / 'outputs' / 'mdc_dipole_tmm_fdtd_residual_contract_v1' / 'paired-residual-20260729T153500Z-ed71d1d48219'
    required = ['paired_case_index.parquet','paired_scalar_metrics.parquet','paired_spectral_curves.parquet','paired_angular_curves.parquet','scalar_residuals.parquet','curve_residuals.parquet','power_reference_ratios.parquet','ranking_comparison.parquet','source_position_comparison.parquet','polarization_comparison.parquet','filter_audit.parquet']
    assert all((out / name).exists() for name in required)
    pairs = pd.read_parquet(out / 'paired_case_index.parquet')
    power = pd.read_parquet(out / 'power_reference_ratios.parquet')
    residual = pd.read_parquet(out / 'scalar_residuals.parquet')
    assert len(pairs) == 18 and pairs.pair_id.is_unique and pairs.fdtd_case_id.is_unique
    assert (power.loc[power.candidate_key.eq('bare'), 'power_log_ratio_residual'] == 0).all()
    for frame in (pairs, power, residual):
        assert np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all()

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_mdc_p1_asymmetric_tmm_spectral_v1 as runner


def test_frozen_input_and_metric_schema():
    rows = runner.verify_static_inputs()
    assert len(rows) == 15
    assert len({r["canonical_sequence_hash"] for r in rows}) == 15
    assert len({r["geometry_hash"] for r in rows}) == 15
    assert all(int(r["N_GaN"]) + int(r["N_Air"]) == 6 for r in rows)


def test_native_m1_policy_and_solver_free_source():
    metadata = runner.material_policy()
    assert all(v["sample_count"] == 101 and v["extrapolation"] == "forbidden" for v in metadata.values())
    source = (ROOT / "scripts" / "run_mdc_p1_asymmetric_tmm_spectral_v1.py").read_text(encoding="utf-8").lower()
    assert "import lumapi" not in source and "fdtd.run" not in source and "rcwa" not in source and "fmmax" not in source

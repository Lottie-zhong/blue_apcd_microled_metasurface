import importlib.util
import json
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[1]
P = R / "scripts" / "run_np_k6_p1d2b_broadband_pillar_x_v1.py"
S = importlib.util.spec_from_file_location("p1d2b", P)
m = importlib.util.module_from_spec(S)
S.loader.exec_module(m)


def test_d110_allowlisted_geometry_only():
    m.configure(110)
    s = m.spec("NP_P1D2_BROADBAND_PILLAR_H500_D110_X", 110)
    assert (s["diameter_nm"], s["radius_nm"], s["gap_nm"], s["aspect_ratio"]) == (110, 55, 180, 500 / 110)
    m.configure(115)
    with pytest.raises(ValueError):
        m.configure(120)


def test_d105_d110_pair_and_cross_audit_schema():
    rows = json.loads((R / "outputs/np_k6_p1d2b1_broadband_d105_x_v1/results.json").read_text())["rows"]
    m.configure(110)
    pair = m.pair_dispersion(rows, 105, 110)
    cross = m.cross_contract_450_audit(rows)
    assert pair["pair"] == "D105_to_D110" and len(pair["rows"]) == 11
    assert pair["summary"]["pair_relative_phase_stability"] in {"stable", "mildly_dispersive", "strongly_dispersive"}
    assert cross["status"] in {"consistent", "warning_review", "inconsistent_investigate"}
    assert "minimal_wrapped_difference_deg" in cross["comparison"]["wrapped_phase_deg"]


def test_d110_post_artifacts_if_present():
    out = R / "outputs/np_k6_p1d2b2_broadband_d110_x_v1"
    if not (out / "results.json").exists():
        pytest.skip("post-run not available during preflight")
    assert len(json.loads((out / "results.json").read_text())["rows"]) == 11
    assert json.loads((out / "partial_line_d100_d105_d110.json").read_text())["provisional_three_diameter_broadband_line"]

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from mdc_tmm_complex_2port_prior_v1 import (  # noqa: E402
    EXTRA_SPACER_NM,
    MDC_THICKNESS_NM,
    RIGHT_PORT_MATERIAL,
    WAVELENGTHS_NM,
    evaluate_prior,
    verify_normal_incidence_degeneracy,
)


def test_prior_grid_and_port_contract():
    prior = evaluate_prior()
    assert prior["grid"]["wavelength_nm"] == {"start": 440.0, "stop": 460.0, "step": 1.0, "count": 21}
    assert prior["port_media"]["right"]["material"] == RIGHT_PORT_MATERIAL
    assert prior["port_media"]["right_medium_is_air"] is False
    assert prior["port_media"]["extra_spacer"]["thickness_nm"] == EXTRA_SPACER_NM
    assert prior["reference_planes"]["included_mdc_thickness_nm"] == MDC_THICKNESS_NM
    assert len(prior["rows"]) == len(WAVELENGTHS_NM) == 21


def test_two_port_fields_are_finite_and_directional():
    prior = evaluate_prior()
    required = (
        "r_L_Re", "r_L_Im", "t_LR_Re", "t_LR_Im",
        "r_R_Re", "r_R_Im", "t_RL_Re", "t_RL_Im",
        "R_L", "T_LR", "R_R", "T_RL",
    )
    for row in prior["rows"]:
        for key in required:
            assert math.isfinite(row[key]), (row["wavelength_nm"], key, row[key])
        assert row["R_L"] >= 0.0 and row["T_LR"] >= 0.0
        assert row["R_R"] >= 0.0 and row["T_RL"] >= 0.0
    assert any(abs(row["r_L_Re"] - row["r_R_Re"]) > 1e-9 or abs(row["r_L_Im"] - row["r_R_Im"]) > 1e-9 for row in prior["rows"])


def test_normal_incidence_te_tm_degeneracy_is_verified():
    result = verify_normal_incidence_degeneracy()
    assert result["exact_at_normal_incidence"] is True
    assert result["max_abs_difference"] == 0.0


def test_power_closure_and_reciprocity_are_audited_without_forcing_r_plus_t_one():
    prior = evaluate_prior()
    assert prior["power_consistency"]["max_abs_power_closure"] < 1e-10
    assert prior["power_consistency"]["max_abs_reciprocity_residual"] < 1e-8
    # Native-M1 port loss is retained; the contract must not silently force
    # R+T=1 for an absorbing incident medium.
    assert any(abs(row["R_plus_T_L"] - 1.0) > 1e-8 for row in prior["rows"])


def test_spacer_phase_is_excluded_from_mdc_prior():
    prior = evaluate_prior()
    assert prior["reference_planes"]["excluded_spacer_thickness_nm"] == 237.0
    assert "exactly once" in prior["reference_planes"]["spacer_phase_rule"]
    assert prior["future_component_compositor_interface"]["spacer_thickness_nm"] == 237.0

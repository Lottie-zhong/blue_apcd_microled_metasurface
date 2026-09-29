from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from np_k6_coupling_forward_feature_interface_v1 import FrozenAuthority

def test_order_and_exact_hf22_provenance():
    a = FrozenAuthority(ROOT)
    r = a.request({"geometry": [200,205,215,220,225,230], "wavelength_nm": 450, "polarization": "P"})
    assert r["status"] == "OK"
    assert r["input"]["geometry"] == [200.0,205.0,215.0,220.0,225.0,230.0]
    assert r["features"]["hf_truth"]["provenance"] == "FROZEN_HF_TRUTH"
    assert r["features"]["lf"]["provenance"] == "LF_ONLY"

def test_p_s_explicit_and_no_averaging():
    a = FrozenAuthority(ROOT)
    for p in ("P", "S"):
        r = a.request({"geometry": [200,205,215,220,225,230], "wavelength_nm": 450, "polarization": p})
        assert r["input"]["polarization"] in ("P_XLIKE", "S_YLIKE")
        assert r["features"]["lf"]["requested_polarization"] == r["input"]["polarization"]
        assert r["features"]["lf"]["polarization_scope"] == "POLARIZATION_BLIND_UX0"

def test_wavelength_bounds():
    a = FrozenAuthority(ROOT)
    for w in (444, 456):
        try:
            a.request({"geometry": [200,205,215,220,225,230], "wavelength_nm": w, "polarization": "P"})
        except ValueError:
            pass
        else:
            raise AssertionError("out-of-contract wavelength accepted")

def test_complex_fails_closed():
    a = FrozenAuthority(ROOT)
    r = a.request({"geometry": [200,205,215,220,225,230], "wavelength_nm": 450, "polarization": "P", "complex_scattering_state": True})
    assert r["status"] == "UNSUPPORTED"
    assert r["error_code"] == "COMPLEX_SCATTERING_STATE_UNAVAILABLE"
    assert r["features"] == {}
    assert not r["capability"]["FULL_2x2_JONES_MATRIX"]

def test_angular_unresolved_and_stress_only():
    a = FrozenAuthority(ROOT)
    unresolved = a.request({"geometry": [200,205,215,220,225,230], "wavelength_nm": 450, "polarization": "P", "ux": 0.22413793103448276})
    stress = a.request({"geometry": [200,205,215,220,225,230], "wavelength_nm": 450, "polarization": "P", "ux": -0.48275862069})
    assert unresolved["angular"]["status"] == "UNRESOLVED_NOT_TRUTH_NO_ATTEMPT_003"
    assert stress["angular"]["status"] == "RAYLEIGH_STRESS_TEST_ONLY_NOT_QUANTITATIVE_ANCHOR"
    assert not unresolved["angular"]["interpolation_performed"]
    assert not unresolved["angular"]["symmetry_substitution"]

def test_support_ood_for_coupling_case():
    a = FrozenAuthority(ROOT)
    s = a.support_audit([215,105,215,230,105,130])
    assert not s["exact_HF22_match"]
    assert s["classification"] == "extrapolation"
    assert s["training_domain_warning"] == "OOD_EXTRAPOLATIVE"

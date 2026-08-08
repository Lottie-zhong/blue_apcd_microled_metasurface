import json
from pathlib import Path

from apcd_coupling.joint_case_schema import canonical_hash
from apcd_coupling.joint_stack_builder import build_joint_case
from apcd_coupling.result_schema import REQUIRED_RESULT_FIELDS

ROOT = Path(__file__).resolve().parents[2]

def fixture():
    return json.loads((ROOT / "configs/coupling/stage_a_golden_fixture_v1.json").read_text(encoding="utf-8"))

def test_generic_golden_fixture_loading_and_hash_replay():
    f = fixture()
    case = build_joint_case(f["mdc_candidate"], f["np_candidate"], 0, 450, "x", 0)
    assert case["mdc_candidate"]["candidate_id"] == "P1_ZL1_ALTERNATIVE_G3_A3"
    assert case["np_candidate"]["candidate_id"] == "NP_K6X_125_135_150_175_190_210"
    assert case["mdc_geometry_hash"] == canonical_hash({"candidate": f["mdc_candidate"], "layers": f["mdc_candidate"]["layers"]})
    assert case["joint_geometry_hash"] == build_joint_case(f["mdc_candidate"], f["np_candidate"], 0, 450, "x", 0)["joint_geometry_hash"]

def test_zl1_layers_and_run3a_ordering_and_reference_plane():
    f = fixture(); case = build_joint_case(f["mdc_candidate"], f["np_candidate"], 0, 450, "x", 0)
    layers = [x for x in case["objects"] if x["role"] == "mdc_layer"]
    assert len(layers) == 12
    assert [x["thickness_nm"] for x in layers] == [44,79,44,79,44,316,44,79,44,79,44,79]
    pillars = [x for x in case["objects"] if x["role"] == "np_pillar"]
    assert [x["x_nm"] for x in pillars] == [-725,-435,-145,145,435,725]
    assert [x["diameter_nm"] for x in pillars] == [125,135,150,175,190,210]
    assert case["coordinates"]["mdc_top_nm"] == 975
    assert case["coordinates"]["np_pillar_bottom_nm"] == 975
    assert case["coordinates"]["np_pillar_top_nm"] == 1475

def test_t_extra_zero_has_no_extra_spacer_and_no_overlap():
    f = fixture(); case = build_joint_case(f["mdc_candidate"], f["np_candidate"], 0, 450, "x", 0)
    assert not any(x["role"] == "extra_spacer" for x in case["objects"])
    assert not any(x["role"] == "air_gap" for x in case["objects"])
    assert case["coordinates"]["np_pillar_bottom_nm"] == case["coordinates"]["mdc_top_nm"]

def test_result_schema_declares_required_machine_fields():
    assert {"R_total", "T_total", "eta_t_orders", "eta_r_orders", "power_closure", "order_closure", "pre_fsp_sha256", "post_fsp_sha256"}.issubset(REQUIRED_RESULT_FIELDS)

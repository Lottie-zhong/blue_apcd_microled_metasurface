import importlib.util
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TARGET = ROOT / "scripts/coupling_ml/k6_finite_pml_10um_model_precheck_v1.py"
spec = importlib.util.spec_from_file_location("finite_pml_precheck", TARGET)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

def test_static_contract_is_solver_free():
    result = module.static_contract_audit()
    assert result["pass"] is True
    assert result["solver_entry_delta"] == 0
    assert result["training_entry_delta"] == 0
    assert result["rerun_delta"] == 0

def test_usable_monitor_and_offaxis_geometry():
    assert module.FDTD_X_SPAN_NM == 14000.0
    assert module.MONITOR_X_SPAN_NM == 10000.0
    assert module.MONITOR_TO_PML_MARGIN_NM > 0
    audit = module.offaxis_audit()
    assert audit["all_necessary_geometry_checks_pass"] is True
    assert all(row["target_ray_before_side_pml"] for row in audit["rows"])

def test_three_contracts_are_finite_pml_and_provisional_mapping():
    for name in ("SOURCE_ONLY", "CONTROL0", "ALT1"):
        contract = module.model_contract(name)
        assert contract["domain"]["periodic"] is False
        assert contract["domain"]["bloch"] is False
        assert contract["domain"]["all_exterior_boundaries"] == "PML"
        assert contract["geometry"]["mapping_flag"] == "BAR_WIDTH_EQUALS_DIAMETER_PROVISIONAL_MAPPING"
        assert contract["source"]["position_nm"]["physical_z"] == -276.0

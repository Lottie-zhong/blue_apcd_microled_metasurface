import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_spectral_data_inventory_stage11_3b0.py"
spec = importlib.util.spec_from_file_location("stage11_3b0", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_infer_450_from_status_line_without_claiming_spectrum():
    line = "- 120 deg: loose usable, H500DIMER2C_004_B120_x_pair_swap_G60_O-20"
    assert mod.infer_wavelengths_from_line(line, default_450_when_measured=True) == {450}


def test_explicit_wavelengths_parse_from_candidate_line():
    line = "H500DIMER2C_004_B120_x_pair_swap_G60_O-20 WL449NM ratio 7 wavelength_nm 451"
    assert mod.infer_wavelengths_from_line(line) == {449, 451}


def test_collect_inventory_selects_frozen_status_candidate(tmp_path):
    p = tmp_path / "status.md"
    p.write_text("- 0 deg: strict usable, H500DIMER2C_029_B240_x_pair_noswap_G60_O-20, ratio 10, Tx 1\n", encoding="utf-8")
    old_root = mod.REPO_ROOT
    try:
        mod.REPO_ROOT = tmp_path
        inv = mod.collect_inventory([p])
    finally:
        mod.REPO_ROOT = old_root
    rows = list(inv.values())
    assert len(rows) == 1
    assert rows[0].phase_bin_deg == 0
    assert rows[0].available_wavelengths_nm == {450}
    assert rows[0].row()["missing_449_450_451_nm"] == "449;451"


def test_conclusion_for_only_450_data_is_explicit():
    rows = [
        {"status": "only 450 nm single-point data exists"},
        {"status": "only 450 nm single-point data exists"},
    ]
    assert mod.conclusion(rows) == "Only single-wavelength 450 nm LP H500 data is available; true narrow-spectrum robustness cannot be concluded yet."


def test_select_frozen_six_prefers_latest_status_evidence():
    old = mod.CandidateInventory(240, "OLD", {450}, {"reports/stage11_lp_apcd_status_summary.md"}, {"frozen library/status report evidence"}, evidence_order=1)
    new = mod.CandidateInventory(240, "NEW", {450}, {"reports/stage11_lp_apcd_status_summary.md"}, {"frozen library/status report evidence"}, evidence_order=2)
    selected = mod.select_frozen_six({(240, "OLD"): old, (240, "NEW"): new})
    assert next(row for row in selected if row.phase_bin_deg == 240).candidate_id == "NEW"

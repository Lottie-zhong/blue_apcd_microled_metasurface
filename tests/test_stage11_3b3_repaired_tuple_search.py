import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_repaired_tuple_search_stage11_3b3.py"
spec = importlib.util.spec_from_file_location("stage11_3b3", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_phase_diff_wraps():
    assert mod.phase_diff(350, 10) == -20
    assert mod.phase_dist(10, 350) == 20


def test_candidate_aggregation_complete_and_gates():
    rows = []
    for wl, phase in [(449, 1), (450, 2), (451, 3)]:
        rows.append({"candidate_id": "A", "wavelength_nm": wl, "original_target_bin_deg": 0, "selected_phase_deg": phase, "Tx": 0.8, "ratio": 7, "matrix_error": 0.2})
    c = mod.aggregate_candidates(rows)[0]
    assert c["candidate_pass_flag"] == "true"
    assert c["wavelengths_available"] == "449;450;451"
    assert c["phase_span_deg"] == "2.000000"


def test_tuple_scoring_rejects_duplicates():
    cand = {"candidate_id": "A", "worst_ratio": "10", "worst_Tx": "1", "worst_matrix_error": "0.1", "phase_span_deg": "1", "candidate_pass_flag": "true", "_by_wl": {449: {"selected_phase_deg": 0}, 450: {"selected_phase_deg": 0}, 451: {"selected_phase_deg": 0}}}
    row = mod.tuple_row("t", "synthetic", {s: cand for s in mod.SLOTS}, 0)
    assert row["tuple_pass_flag"] == "false"
    assert "duplicate_candidate" in row["failed_gates"]


def test_relabeling_offset_search_synthetic_passes():
    cands = []
    for slot in mod.SLOTS:
        cands.append({"candidate_id": f"C{slot}", "original_target_bin_deg": slot, "mean_selected_phase_deg": f"{slot}", "phase_span_deg": "0", "worst_ratio": "8", "worst_Tx": "0.8", "worst_matrix_error": "0.2", "candidate_pass_flag": "true", "_by_wl": {449: {"selected_phase_deg": slot}, 450: {"selected_phase_deg": slot}, 451: {"selected_phase_deg": slot}}})
    rows = mod.relabel_tuples(cands)
    assert rows[0]["tuple_pass_flag"] == "true"
    assert len({rows[0][f"slot_{s}_candidate_id"] for s in mod.SLOTS}) == 6

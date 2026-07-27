import csv, importlib.util, json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts"/"synthesize_np_k6_p1d2_broadband_library_x_v1.py"; S=importlib.util.spec_from_file_location("syn",P); syn=importlib.util.module_from_spec(S); S.loader.exec_module(syn)
def test_offline_synthesis_outputs_26_by_11_library(tmp_path):
    manifest=syn.synthesize(tmp_path)
    assert manifest["offline_only"] and manifest["row_count"] == 286 and 180 in manifest["missing_diameters_nm"]
    with (tmp_path/"library_long.csv").open() as f: assert len(list(csv.DictReader(f))) == 286
    m=json.loads((tmp_path/"library_matrix.json").read_text()); assert len(m["diameters_nm"]) == 26 and len(m["T"]) == 26 and len(m["T"][0]) == 11
    audit=json.loads((tmp_path/"d180_failure_audit.json").read_text()); assert audit["status"] == "sealed_failed_case_local" and audit["excluded_from_library"]
    ranking=json.loads((tmp_path/"candidate_sextet_ranking.json").read_text()); assert ranking["K6_SUPERCELL_VALIDATION_STATUS"] == "not_run"
    contract=json.loads((tmp_path/"surrogate_dataset_contract.json").read_text()); assert contract["status"] == "data_contract_only_not_trained" and not contract["interpolation_or_imputation_used"]
    assert (tmp_path/"geometry_table.csv").exists() and (tmp_path/"quality_table.csv").exists()
    assert json.loads((tmp_path/"phase_gap_analysis.json").read_text())["crosses_missing_D180"]
    assert json.loads((tmp_path/"surrogate_forward_contract.json").read_text())["physical_solver_calls"] == 0

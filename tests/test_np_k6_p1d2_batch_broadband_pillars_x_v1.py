import importlib.util
import json
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/"scripts"/"run_np_k6_p1d2_batch_broadband_pillars_x_v1.py"
SPEC=importlib.util.spec_from_file_location("batch",PATH); batch=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(batch)

def test_authorized_batch_is_exact_23_five_nm_cases():
    assert batch.AUTHORIZED_BATCH_DIAMETERS_NM == tuple(range(120,231,5))
    assert batch.allowed(list(batch.AUTHORIZED_BATCH_DIAMETERS_NM))
    assert not batch.allowed([120,125])

def test_contract_freezes_x_only_monitor_and_solver_limits():
    c=batch.contract()
    assert c["maximum_new_solver_runs"] == 23 and c["one_solver_run_max_per_diameter"]
    assert c["monitor_count"] == 33 and c["polarization"] == "x"
    assert c["protected_evidence_diameters_nm"] == [100,105,110,115]

def test_initial_checkpoint_has_only_pending_authorized_cases():
    p=batch.initial_progress(list(batch.AUTHORIZED_BATCH_DIAMETERS_NM))
    assert list(map(int,p["cases"])) == list(batch.AUTHORIZED_BATCH_DIAMETERS_NM)
    assert {x["status"] for x in p["cases"].values()} == {"pending"}

def test_single_runner_rejects_off_contract_diameter():
    try: batch.single.configure(117)
    except ValueError: pass
    else: raise AssertionError("off-contract diameter accepted")

def test_dynamic_batch_cases_have_expected_identity_geometry_and_output_path():
    for diameter in (120, 125, 130):
        batch.single.configure(diameter)
        s = batch.single.spec(f"NP_P1D2_BROADBAND_PILLAR_H500_D{diameter}_X", diameter)
        assert s["case_id"] == f"NP_P1D2_BROADBAND_PILLAR_H500_D{diameter}_X"
        assert (s["diameter_nm"], s["radius_nm"], s["gap_nm"], s["aspect_ratio"]) == (diameter, diameter / 2, 290 - diameter, 500 / diameter)
        assert batch.single.OUT.name == f"np_k6_p1d2b_broadband_d{diameter}_x_v1"

def test_default_d100_and_checkpoint_ledger_identity_remain_frozen():
    batch.single.configure(100)
    s = batch.single.spec()
    assert s["case_id"] == "NP_P1D2_BROADBAND_PILLAR_H500_D100_X"
    assert (s["diameter_nm"], s["radius_nm"], s["gap_nm"], s["aspect_ratio"]) == (100, 50, 190, 5)
    p = batch.initial_progress(list(batch.AUTHORIZED_BATCH_DIAMETERS_NM))
    for diameter in batch.AUTHORIZED_BATCH_DIAMETERS_NM:
        row = p["cases"][str(diameter)]
        assert row["case_id"] == f"NP_P1D2_BROADBAND_PILLAR_H500_D{diameter}_X"
        assert row["diameter_nm"] == diameter and row["attempt_count"] == row["solver_entered_count"] == 0

def test_d180_seal_is_terminal_and_forensic_while_later_cases_stay_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "OUT", tmp_path / "out")
    progress=batch.initial_progress(list(batch.AUTHORIZED_BATCH_DIAMETERS_NM)); ledger=tmp_path/"ledger.jsonl"; heartbeat=tmp_path/"heartbeat.json"; checkpoint=tmp_path/"progress.json"
    progress["cases"]["180"].update(status="solver_entered",attempt_count=1,solver_entered_count=1)
    assert batch.seal_failed_case_local(progress,ledger,heartbeat,180,"post-FSP absent","foreground evidence retained",checkpoint)
    sealed=progress["cases"]["180"]
    assert sealed["status"] == "sealed_failed_case_local" and sealed["forensic_provenance"]["retry_prohibited"]
    assert progress["cases"]["185"]["status"] == "pending"
    assert not batch.seal_failed_case_local(progress,ledger,heartbeat,180,"ignored","ignored",checkpoint)
    entries=[json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(entries) == 1 and entries[0]["previous_status"] == "solver_entered"
    assert json.loads(checkpoint.read_text())["cases"]["180"]["status"] == "sealed_failed_case_local"

def test_sealed_case_is_skipped_without_setup_or_solver(monkeypatch, tmp_path):
    progress=batch.initial_progress(list(batch.AUTHORIZED_BATCH_DIAMETERS_NM)); progress["cases"]["180"]["status"]="sealed_failed_case_local"
    monkeypatch.setattr(batch, "trusted", lambda _: (_ for _ in ()).throw(AssertionError("sealed case was retried")))
    batch.execute_case(180,progress,tmp_path/"ledger",tmp_path/"heartbeat",True)

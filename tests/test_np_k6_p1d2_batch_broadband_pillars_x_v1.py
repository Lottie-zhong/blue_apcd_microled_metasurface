import importlib.util
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

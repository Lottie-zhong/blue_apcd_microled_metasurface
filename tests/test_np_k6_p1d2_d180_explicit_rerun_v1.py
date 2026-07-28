from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_explicit_d180_runner_is_single_case_only():
    text = (ROOT / "scripts" / "run_np_k6_p1d2_d180_explicit_rerun_v1.py").read_text(encoding="utf-8")
    for token in ('"--explicit-user-authorization"', 'a.diameter_nm,a.polarization,a.maximum_new_solver_runs', '(180,"x",1,True)', 'explicit_user_authorized_independent_rerun_v1', 'automatic_retry_prohibited'):
        assert token in text
    assert 'FDTD(hide=True)' in text
    assert 'fdtd.run()' in text
    assert 'batch.write_case(180' in text

from types import SimpleNamespace

import numpy as np
import pytest

from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.serial import (
    _diag2_time_convergence_telemetry,
    _require_diag2_terminal_evidence,
)


RESULT_NAMES = "x\ny\nz\nstatus\nautoshutoff level\ninitialization time\nsimulation run time\nsimulation checkpoint time\nmiscellaneous time\nsolver speed\ntotal solver speed\ntotal processes\ntotal threads\npeak memory usage\ntotal gpu sms"


class FakeFDTD:
    def __init__(self, status=1.0, final=2e-6, gpu_sms=68.0):
        self.results = {
            'status': status,
            'autoshutoff level': {
                't': np.array([[1e-17, 2e-12, 4e-12, 5.97e-12]]),
                'wall clock time': np.array([[1.0, 20.0, 40.0, 60.0]]),
                'autoshutoff': np.array([[1.0, 1e-3, 3e-6, final]]),
            },
            'simulation run time': 60.0,
            'initialization time': 7.0,
            'total gpu sms': gpu_sms,
        }

    def getresult(self, obj, name=None):
        assert obj == 'FDTD'
        return RESULT_NAMES if name is None else self.results[name]


def request(**overrides):
    fields = dict(
        dataset_id='APCD_COUPLING_V3_TIME_DIAG2_V1',
        case_id='K6V3_TIME_DIAG2_A1_5NM_6PS', attempt_id='attempt_001',
        role='TIME_CONVERGENCE_DIAGNOSTIC_ONLY', simulation_time_s=6e-12,
        auto_shutoff_min=1e-6, request_sha256='a' * 64,
        physical_contract_sha256='b' * 64)
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_time_limit_records_unresolved_and_full_physical_duration():
    evidence = _diag2_time_convergence_telemetry(FakeFDTD(), request(), np)
    assert evidence['status_code'] == 1
    assert evidence['stop_reason'] == 'SIMULATION_TIME_LIMIT'
    assert evidence['time_convergence_status'] == 'TIME_CONVERGENCE_UNRESOLVED'
    assert evidence['simulation_physical_time_s'] == 6e-12
    assert evidence['autoshutoff_sampled_last_time_s'] == 5.97e-12
    assert evidence['final_autoshutoff_value'] == 2e-6
    assert evidence['solver_simulation_run_time_s'] == 60.0
    assert evidence['solver_initialization_time_s'] == 7.0
    assert evidence['total_gpu_sms'] == 68.0
    assert evidence['gpu_engine_result_confirmed'] is True
    _require_diag2_terminal_evidence(evidence, 'evidence.json')


def test_auto_shutoff_below_frozen_threshold_is_terminal_pass_evidence():
    evidence = _diag2_time_convergence_telemetry(FakeFDTD(status=2.0, final=8e-7), request(), np)
    assert evidence['stop_reason'] == 'AUTO_SHUTOFF'
    assert evidence['time_convergence_status'] == 'AUTO_SHUTOFF_THRESHOLD_MET'
    _require_diag2_terminal_evidence(evidence, 'evidence.json')


def test_auto_shutoff_status_threshold_conflict_fails_closed():
    evidence = _diag2_time_convergence_telemetry(FakeFDTD(status=2.0, final=2e-6), request(), np)
    with pytest.raises(Refused, match='AUTO_SHUTOFF_STATUS_CONFLICT'):
        _require_diag2_terminal_evidence(evidence, 'evidence.json')


def test_diverged_unknown_and_missing_gpu_evidence_fail_closed():
    diverged = _diag2_time_convergence_telemetry(FakeFDTD(status=3.0), request(), np)
    with pytest.raises(Refused, match='FDTD_DIVERGED'):
        _require_diag2_terminal_evidence(diverged, 'evidence.json')
    unknown = _diag2_time_convergence_telemetry(FakeFDTD(status=4.0), request(), np)
    with pytest.raises(Refused, match='TERMINAL_STATUS_INVALID'):
        _require_diag2_terminal_evidence(unknown, 'evidence.json')
    no_gpu = _diag2_time_convergence_telemetry(FakeFDTD(gpu_sms=0.0), request(), np)
    with pytest.raises(Refused, match='GPU_ENGINE_RESULT_UNCONFIRMED'):
        _require_diag2_terminal_evidence(no_gpu, 'evidence.json')


@pytest.mark.parametrize('overrides, message', [
    ({'role': 'DOE56'}, 'ROLE_NOT_ALLOWLISTED'),
    ({'case_id': 'DOE56_G001'}, 'CASE_NOT_ALLOWLISTED'),
    ({'attempt_id': 'attempt_002'}, 'ATTEMPT_NOT_ALLOWLISTED'),
    ({'simulation_time_s': 8e-12}, 'TIME_CONTRACT_NOT_6PS_1E6'),
    ({'auto_shutoff_min': 1e-5}, 'TIME_CONTRACT_NOT_6PS_1E6'),
])
def test_non_diag2_role_or_time_contract_refused(overrides, message):
    with pytest.raises(Refused, match=message):
        _diag2_time_convergence_telemetry(FakeFDTD(), request(**overrides), np)


def test_non_diag2_request_is_not_interpreted_as_time_diagnostic():
    assert _diag2_time_convergence_telemetry(
        FakeFDTD(), request(dataset_id='APCD_V2_OTHER'), np) is None


def test_malformed_curve_and_missing_telemetry_are_refused():
    fd = FakeFDTD()
    fd.results['autoshutoff level']['wall clock time'] = np.array([[1.0, 0.0, 40.0, 60.0]])
    with pytest.raises(Refused, match='CURVE_ORDER_INVALID'):
        _diag2_time_convergence_telemetry(fd, request(), np)
    fd = FakeFDTD()
    del fd.results['total gpu sms']
    with pytest.raises(KeyError):
        _diag2_time_convergence_telemetry(fd, request(), np)

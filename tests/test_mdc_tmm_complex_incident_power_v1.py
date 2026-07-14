from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mdc_tmm_complex_incident_power_v1 import normal_stack_power, oracle_scattering_normal


NI = 2.414946476353578 + 0.08415346869326513j


def assert_close(a, b, tol=1e-10):
    assert abs(a - b) < tol, (a, b)


def test_zero_stack_identity_same_complex_medium():
    got = normal_stack_power(NI, NI, [], 450.0)
    assert_close(got['R'], 0.0)
    assert_close(got['T'], 1.0)
    assert_close(got['power_entering'], 1.0)
    assert_close(got['A_stack'], 0.0)


def test_lossless_interface_energy_and_normal_parity_basis():
    got = normal_stack_power(2.41 + 0j, 1 + 0j, [], 450.0)
    assert_close(got['R'] + got['T'], 1.0)
    assert_close(got['power_entering'], 1.0 - got['R'])
    # Both polarizations intentionally call the same normal-incidence E basis.
    te = normal_stack_power(2.41 + 0j, 1 + 0j, [(2.25 + 0j, 50)], 450.0)
    tm = normal_stack_power(2.41 + 0j, 1 + 0j, [(2.25 + 0j, 50)], 450.0)
    for key in ('r', 't', 'R', 'T', 'power_entering', 'A_stack'):
        assert_close(te[key], tm[key])


def test_complex_interface_entering_not_far_field_offset():
    got = normal_stack_power(NI, 1 + 0j, [], 450.0)
    assert_close(got['power_entering'], got['T'])
    assert_close(got['A_stack'], 0.0)
    assert_close(got['far_field_balance_offset'], -0.0010052291456, 2e-10)
    assert got['far_field_balance_offset'] < 0


def test_finite_layer_absorption_and_independent_oracle():
    lossless = normal_stack_power(NI, 1 + 0j, [(2.25 + 0j, 50)], 450.0)
    absorbing = normal_stack_power(NI, 1 + 0j, [(2.25 + 0.05j, 50)], 450.0)
    assert abs(lossless['A_stack']) < 1e-10
    assert absorbing['A_stack'] > 0
    assert abs(absorbing['poynting_loss_delta']) < 1e-5
    oracle = oracle_scattering_normal(NI, 1 + 0j, [(2.25 + 0.05j, 50)], 450.0)
    for key in ('r', 't', 'R', 'T', 'power_entering', 'A_stack'):
        assert_close(absorbing[key], oracle[key], 1e-10)

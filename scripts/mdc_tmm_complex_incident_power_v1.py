"""Normal-incidence complex-incident-medium TMM power in an E-field basis."""
from __future__ import annotations

import cmath
import math
from typing import Any

import numpy as np


def _matrix(n: complex, thickness_nm: float, wavelength_nm: float, historical_lossless: bool = False) -> np.ndarray:
    delta = 2 * math.pi * n * thickness_nm / wavelength_nm
    # [E,H] on the incident side equals this matrix times [E,H] on the
    # exit side. With n+i*k and exp(+i*k0*n*z) forward propagation this
    # produces physical attenuation for k>0. The historical branch is for
    # exactly lossless replay only.
    sign = 1j if historical_lossless else -1j
    return np.array([[cmath.cos(delta), sign * cmath.sin(delta) / n], [sign * n * cmath.sin(delta), cmath.cos(delta)]], dtype=complex)


def _power_entering(n_in: complex, r: complex) -> float:
    denom = float(np.real(n_in))
    if denom <= 0: raise ValueError('incident forward Poynting flux is non-positive')
    # Equivalent real parts of the TE and TM definitions at normal incidence.
    return float(np.real(n_in * (1 + r.conjugate()) * (1 - r)) / denom)


def normal_stack_power(n_in: complex, n_out: complex, layers: list[tuple[complex, float]], wavelength_nm: float, loss_samples: int = 257, historical_lossless: bool = False) -> dict[str, Any]:
    """E-field r/t amplitudes and stack-entrance power bookkeeping.

    No finite propagation in the incident medium is present.  ``A_stack`` is
    finite-layer absorption, while ``far_field_balance_offset`` is deliberately
    retained as a non-absorptance diagnostic for an absorbing incident medium.
    """
    if np.imag(n_in) < -1e-12 or any(np.imag(n) < -1e-12 for n, _ in layers): raise ValueError('non-passive branch')
    if historical_lossless and (abs(np.imag(n_in)) > 1e-12 or any(abs(np.imag(n)) > 1e-12 for n, _ in layers)): raise ValueError('historical convention is lossless controls only')
    matrix = np.eye(2, dtype=complex)
    matrices = []
    for n, d in layers:
        m = _matrix(n, d, wavelength_nm, historical_lossless); matrices.append(m); matrix = matrix @ m
    a,b,c,d = matrix.ravel(); den = n_in*a + n_in*n_out*b + c + n_out*d
    r = (n_in*a+n_in*n_out*b-c-n_out*d)/den; t = 2*n_in/den
    R = float(abs(r)**2); T = float(abs(t)**2 * np.real(n_out)/np.real(n_in))
    entering = _power_entering(n_in, r); A = entering - T
    # Independent finite-layer loss measurement: integrate -dS/dz in every layer.
    state = np.array([1+r, n_in*(1-r)], dtype=complex); integrated = 0.0
    for (n, thickness), m in zip(layers, matrices):
        ep = (state[0] + state[1]/n)/2; em = (state[0] - state[1]/n)/2
        z = np.linspace(0.0, thickness, loss_samples); phase = 2*math.pi*n*z/wavelength_nm
        e = ep*np.exp(1j*phase)+em*np.exp(-1j*phase); h = n*(ep*np.exp(1j*phase)-em*np.exp(-1j*phase))
        flux = np.real(e*np.conjugate(h))/np.real(n_in)
        integrated += float(np.trapz(-np.gradient(flux,z),z))
        state = np.linalg.solve(m,state)
    return {'r':r,'t':t,'R':R,'T':T,'power_entering':entering,'A_stack':A,'far_field_balance_offset':1-R-T,'incident_interference_offset':entering-(1-R),'poynting_loss_integral':integrated,'poynting_loss_delta':integrated-A}


def oracle_scattering_normal(n_in: complex, n_out: complex, layers: list[tuple[complex, float]], wavelength_nm: float) -> dict[str, complex]:
    """Minimal independent scattering-chain oracle; not a runtime dependency."""
    media=[n_in]+[n for n,_ in layers]+[n_out]
    def iface(a:complex,b:complex):
        r=(a-b)/(a+b); return (r,-r,2*a/(a+b),2*b/(a+b)) # rL,rR,tLR,tRL
    def cascade(x,y):
        r1l,r1r,t1lr,t1rl=x; r2l,r2r,t2lr,t2rl=y; den=1-r2l*r1r
        return (r1l+t1rl*r2l*t1lr/den, r2r+t2lr*r1r*t2rl/den, t2lr*t1lr/den, t1rl*t2rl/den)
    if not layers:
        s=iface(n_in,n_out)
        r,_,t,_=s; R=abs(r)**2; T=abs(t)**2*np.real(n_out)/np.real(n_in); entering=_power_entering(n_in,r)
        return {'r':r,'t':t,'R':R,'T':T,'power_entering':entering,'A_stack':entering-T}
    s=iface(media[0],media[1])
    for i,(n,thick) in enumerate(layers):
        phase=cmath.exp(1j*2*math.pi*n*thick/wavelength_nm); s=cascade(s,(0j,0j,phase,phase)); s=cascade(s,iface(media[i+1],media[i+2]))
    r,_,t,_=s; R=abs(r)**2; T=abs(t)**2*np.real(n_out)/np.real(n_in); entering=_power_entering(n_in,r)
    return {'r':r,'t':t,'R':R,'T':T,'power_entering':entering,'A_stack':entering-T}


def select_forward_kz(index: complex, kx_over_k0: float, tolerance: float = 1e-12) -> complex:
    """Return kz/k0 on the passive forward branch for a real conserved kx/k0."""
    if not math.isfinite(float(kx_over_k0)):
        raise ValueError('kx_over_k0 must be finite and real')
    if float(kx_over_k0) == 0.0:
        # Preserve bit-for-bit normal-incidence reduction to the frozen helper.
        return index
    kz = cmath.sqrt(index * index - float(kx_over_k0) ** 2)
    if kz.imag < -tolerance or (abs(kz.imag) <= tolerance and kz.real < -tolerance):
        kz = -kz
    if kz.imag < -tolerance or (abs(kz.imag) <= tolerance and kz.real < -tolerance):
        raise ValueError('forward kz branch selection failed')
    return kz


def tangential_admittance(kz_over_k0: complex, index: complex, polarization: str) -> complex:
    """Tangential E-field admittance: TE=kz/k0; TM=n^2/(kz/k0)."""
    if polarization == 'TE':
        return kz_over_k0
    if polarization == 'TM':
        if abs(kz_over_k0) <= 1e-15:
            raise ValueError('TM admittance undefined at grazing incidence')
        return index * index / kz_over_k0
    raise ValueError('polarization must be TE or TM')


def power_entering_from_r_oblique(y_incident: complex, reflection: complex) -> float:
    denom = float(np.real(y_incident))
    if denom <= 0:
        raise ValueError('incident forward Poynting flux is non-positive')
    return float(np.real(y_incident.conjugate() * (1 + reflection) * (1 - reflection.conjugate())) / denom)


def oblique_interface_rt(n_incident: complex, n_final: complex, kx_over_k0: float, polarization: str) -> dict[str, Any]:
    return oblique_stack_rt(n_incident, n_final, [], 1.0, kx_over_k0, polarization)


def oblique_stack_rt(n_incident: complex, n_final: complex, layers: list[tuple[complex, float]], wavelength_nm: float, kx_over_k0: float, polarization: str, historical_lossless: bool = False) -> dict[str, Any]:
    """Oblique E-field-basis transfer matrix with real conserved output-air kx.

    ``kx_over_k0`` is dimensionless and real.  A final medium with evanescent
    kz carries no propagating transmitted power, so ``T`` is exactly zero.
    """
    if historical_lossless and (abs(n_incident.imag) > 1e-12 or abs(n_final.imag) > 1e-12 or any(abs(n.imag) > 1e-12 for n, _ in layers)):
        raise ValueError('historical convention is lossless controls only')
    if float(kx_over_k0) == 0.0:
        # Delegate exactly to the frozen normal implementation, including its
        # floating-point operation order, rather than merely algebraically
        # reproducing it through the oblique matrix.
        normal = normal_stack_power(n_incident, n_final, layers, wavelength_nm, historical_lossless=historical_lossless)
        normal.update({
            'kx_over_k0': 0.0,
            'kz_incident_over_k0': n_incident,
            'kz_final_over_k0': n_final,
            'Y_incident': n_incident,
            'Y_final': n_final,
            'final_propagating': abs(n_final.imag) <= 1e-12 and n_final.real > 1e-12,
        })
        return normal
    kz_i = select_forward_kz(n_incident, kx_over_k0)
    kz_f = select_forward_kz(n_final, kx_over_k0)
    y_i = tangential_admittance(kz_i, n_incident, polarization)
    y_f = tangential_admittance(kz_f, n_final, polarization)
    matrix = np.eye(2, dtype=complex)
    for index, thickness in layers:
        kz = select_forward_kz(index, kx_over_k0)
        y = tangential_admittance(kz, index, polarization)
        delta = 2 * math.pi * kz * thickness / wavelength_nm
        sign = 1j if historical_lossless else -1j
        matrix = matrix @ np.array([[cmath.cos(delta), sign * cmath.sin(delta) / y], [sign * y * cmath.sin(delta), cmath.cos(delta)]], dtype=complex)
    a, b, c, d = matrix.ravel()
    denominator = y_i * a + y_i * y_f * b + c + y_f * d
    r = (y_i * a + y_i * y_f * b - c - y_f * d) / denominator
    t = 2 * y_i / denominator
    R = float(abs(r) ** 2)
    final_propagating = abs(kz_f.imag) <= 1e-12 and kz_f.real > 1e-12
    T = float(abs(t) ** 2 * np.real(y_f) / np.real(y_i)) if final_propagating else 0.0
    entering = power_entering_from_r_oblique(y_i, r)
    return {
        'r': r, 't': t, 'R': R, 'T': T,
        'power_entering': entering, 'A_stack': entering - T,
        'far_field_balance_offset': 1 - R - T,
        'incident_interference_offset': entering - (1 - R),
        'kx_over_k0': float(kx_over_k0), 'kz_incident_over_k0': kz_i,
        'kz_final_over_k0': kz_f, 'Y_incident': y_i, 'Y_final': y_f,
        'final_propagating': final_propagating,
    }

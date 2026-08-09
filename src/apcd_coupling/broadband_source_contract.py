from __future__ import annotations

import math
from typing import Iterable

C0 = 299_792_458.0
EXACT_WAVELENGTH_GRID_NM = tuple(float(value) for value in range(445, 456))


def real_kx(wavelength_nm: float, ux: float) -> float:
    return 2.0 * math.pi / (float(wavelength_nm) * 1e-9) * float(ux)


def fixed_ux_target_rows(ux: float, wavelengths_nm: Iterable[float] = EXACT_WAVELENGTH_GRID_NM) -> list[dict[str, float]]:
    return [{"wavelength_nm": float(wavelength), "ux": float(ux), "real_kx": real_kx(float(wavelength), ux)} for wavelength in wavelengths_nm]


def validate_fixed_ux_rows(rows: Iterable[dict[str, float]], ux: float, tolerance: float = 1e-9) -> bool:
    rows = list(rows)
    if [round(float(row["wavelength_nm"]), 6) for row in rows] != [round(value, 6) for value in EXACT_WAVELENGTH_GRID_NM]:
        return False
    return all(abs(float(row["ux"]) - float(ux)) <= tolerance and abs(float(row["real_kx"]) - real_kx(float(row["wavelength_nm"]), ux)) <= max(abs(real_kx(float(row["wavelength_nm"]), ux)), 1.0) * tolerance for row in rows)


def fixed_absolute_kx_is_not_fixed_ux(kx: float, ux: float, wavelengths_nm: Iterable[float] = EXACT_WAVELENGTH_GRID_NM) -> bool:
    return any(abs(kx / (2.0 * math.pi / (float(wavelength) * 1e-9)) - float(ux)) > 1e-6 for wavelength in wavelengths_nm)

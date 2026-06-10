from __future__ import annotations

import csv
from pathlib import Path
from typing import Union

from metasurface.config import PlaneWaveSweepConfig


SUMMARY_FIELDS = [
    "h_nm",
    "wavelength_nm",
    "atom_period_nm",
    "supercell_period_um",
    "target_angle_deg",
    "incident_polarization",
    "output_polarization",
    "rcp_plus1_efficiency",
    "transmission",
    "phase_delay_error",
    "status",
    "note",
]


def build_h_sweep_values(config: PlaneWaveSweepConfig) -> list[int]:
    sweep = config.thickness_sweep
    if sweep.h_step_nm <= 0:
        raise ValueError("thickness_sweep.h_step_nm must be positive")
    if sweep.h_min_nm > sweep.h_max_nm:
        raise ValueError("thickness_sweep.h_min_nm must be <= h_max_nm")

    values = list(range(sweep.h_min_nm, sweep.h_max_nm + 1, sweep.h_step_nm))
    if not values or values[-1] != sweep.h_max_nm:
        values.append(sweep.h_max_nm)
    return values


def build_dry_run_rows(config: PlaneWaveSweepConfig) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for h_nm in build_h_sweep_values(config):
        rows.append(
            {
                "h_nm": h_nm,
                "wavelength_nm": config.target.wavelength_nm,
                "atom_period_nm": config.geometry.atom_period_nm,
                "supercell_period_um": config.geometry.supercell_period_um,
                "target_angle_deg": config.target.deflection_angle_deg,
                "incident_polarization": config.target.incident_polarization,
                "output_polarization": config.target.output_polarization,
                "rcp_plus1_efficiency": "",
                "transmission": "",
                "phase_delay_error": "",
                "status": "dry_run",
                "note": "dry-run only; lumapi was not imported",
            }
        )
    return rows


def write_h_sweep_summary(rows: list[dict[str, object]], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path

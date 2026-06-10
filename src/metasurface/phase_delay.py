from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Union


PHASE_DELAY_FIELDS = [
    "phase_x_rad",
    "phase_y_rad",
    "phase_delay_rad",
    "phase_delay_error_to_pi",
    "transmission_x",
    "transmission_y",
    "status_x",
    "status_y",
    "status",
    "note",
]


def compute_xy_phase_delay_from_files(
    x_summary_path: Union[str, Path],
    y_summary_path: Union[str, Path],
    output_path: Union[str, Path],
) -> Path:
    x_row = _read_single_summary_row(x_summary_path)
    y_row = _read_single_summary_row(y_summary_path)
    result = compute_xy_phase_delay(x_row, y_row)
    return write_phase_delay_summary(result, output_path)


def compute_xy_phase_delay(x_row: dict[str, str], y_row: dict[str, str]) -> dict[str, object]:
    status_x = x_row.get("status", "")
    status_y = y_row.get("status", "")
    transmission_x = x_row.get("transmission", "")
    transmission_y = y_row.get("transmission", "")

    try:
        phase_x = float(x_row["phase_rad"])
        phase_y = float(y_row["phase_rad"])
        phase_delay = wrap_phase_rad(phase_x - phase_y)
        error_to_pi = abs(abs(phase_delay) - math.pi)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "phase_x_rad": x_row.get("phase_rad", ""),
            "phase_y_rad": y_row.get("phase_rad", ""),
            "phase_delay_rad": "",
            "phase_delay_error_to_pi": "",
            "transmission_x": transmission_x,
            "transmission_y": transmission_y,
            "status_x": status_x,
            "status_y": status_y,
            "status": "error",
            "note": f"{type(exc).__name__}: {exc}",
        }

    status = "ok" if status_x == "ok" and status_y == "ok" else "error"
    note = "" if status == "ok" else "x/y summary status is not ok"
    return {
        "phase_x_rad": phase_x,
        "phase_y_rad": phase_y,
        "phase_delay_rad": phase_delay,
        "phase_delay_error_to_pi": error_to_pi,
        "transmission_x": transmission_x,
        "transmission_y": transmission_y,
        "status_x": status_x,
        "status_y": status_y,
        "status": status,
        "note": note,
    }


def wrap_phase_rad(value: float) -> float:
    return math.atan2(math.sin(value), math.cos(value))


def write_phase_delay_summary(row: dict[str, object], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PHASE_DELAY_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    return path


def _read_single_summary_row(path: Union[str, Path]) -> dict[str, str]:
    summary_path = Path(path)
    with summary_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one row in {summary_path}, got {len(rows)}")
    return rows[0]

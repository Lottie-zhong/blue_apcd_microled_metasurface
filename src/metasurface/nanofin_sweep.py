from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import yaml


XY_SWEEP_PLAN_FIELDS = [
    "case_id",
    "length_nm",
    "width_nm",
    "height_nm",
    "rotation_deg",
    "x_config",
    "y_config",
    "x_fsp",
    "y_fsp",
    "x_summary",
    "y_summary",
    "phase_delay_summary",
    "status",
    "note",
]


XY_SWEEP_RESULT_FIELDS = [
    "case_id",
    "length_nm",
    "width_nm",
    "height_nm",
    "rotation_deg",
    "phase_delay_rad",
    "phase_delay_error_to_pi",
    "transmission_x",
    "transmission_y",
    "status",
    "phase_delay_summary",
    "note",
]


@dataclass(frozen=True)
class NanofinXYSweepConfig:
    x_base_config: Path
    y_base_config: Path
    length_nm: list[float]
    width_nm: list[float]
    height_nm: list[float]
    rotation_deg: list[float]
    result_dir: Path


def load_xy_sweep_config(path: Union[str, Path]) -> NanofinXYSweepConfig:
    data = _read_yaml_mapping(path)
    base_configs = _required_mapping(data, "base_configs")
    sweep = _required_mapping(data, "sweep")
    output = _required_mapping(data, "output")
    return NanofinXYSweepConfig(
        x_base_config=Path(base_configs["x"]),
        y_base_config=Path(base_configs["y"]),
        length_nm=_number_list(sweep, "length_nm"),
        width_nm=_number_list(sweep, "width_nm"),
        height_nm=_number_list(sweep, "height_nm"),
        rotation_deg=_number_list(sweep, "rotation_deg"),
        result_dir=Path(output["result_dir"]),
    )


def build_xy_sweep_plan_rows(config: NanofinXYSweepConfig) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for height_nm in config.height_nm:
        for rotation_deg in config.rotation_deg:
            for length_nm in config.length_nm:
                for width_nm in config.width_nm:
                    case_id = _case_id(length_nm, width_nm, height_nm, rotation_deg)
                    case_dir = config.result_dir / case_id
                    rows.append(
                        {
                            "case_id": case_id,
                            "length_nm": _format_number(length_nm),
                            "width_nm": _format_number(width_nm),
                            "height_nm": _format_number(height_nm),
                            "rotation_deg": _format_number(rotation_deg),
                            "x_config": case_dir / f"{case_id}_x.yaml",
                            "y_config": case_dir / f"{case_id}_y.yaml",
                            "x_fsp": case_dir / f"{case_id}_x.fsp",
                            "y_fsp": case_dir / f"{case_id}_y.fsp",
                            "x_summary": case_dir / f"{case_id}_x_summary.csv",
                            "y_summary": case_dir / f"{case_id}_y_summary.csv",
                            "phase_delay_summary": case_dir / f"{case_id}_phase_delay.csv",
                            "status": "planned",
                            "note": "",
                        }
                    )
    return rows


def write_xy_sweep_plan(rows: list[dict[str, object]], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=XY_SWEEP_PLAN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_xy_case_configs(config: NanofinXYSweepConfig, rows: list[dict[str, object]]) -> None:
    x_base = _read_yaml_mapping(config.x_base_config)
    y_base = _read_yaml_mapping(config.y_base_config)
    for row in rows:
        length_nm = float(row["length_nm"])
        width_nm = float(row["width_nm"])
        height_nm = float(row["height_nm"])
        rotation_deg = float(row["rotation_deg"])
        _write_case_config(x_base, Path(row["x_config"]), length_nm, width_nm, height_nm, rotation_deg)
        _write_case_config(y_base, Path(row["y_config"]), length_nm, width_nm, height_nm, rotation_deg)


def collect_xy_sweep_result_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result_rows: list[dict[str, object]] = []
    for row in rows:
        phase_delay_path = Path(row["phase_delay_summary"])
        if not phase_delay_path.exists():
            result_rows.append(_missing_result_row(row, "phase delay summary missing"))
            continue
        try:
            phase_delay = _read_csv_single_row(phase_delay_path)
            status = phase_delay.get("status", "")
            note = phase_delay.get("note", "")
            result_rows.append(
                {
                    "case_id": row["case_id"],
                    "length_nm": row["length_nm"],
                    "width_nm": row["width_nm"],
                    "height_nm": row["height_nm"],
                    "rotation_deg": row["rotation_deg"],
                    "phase_delay_rad": phase_delay.get("phase_delay_rad", ""),
                    "phase_delay_error_to_pi": phase_delay.get("phase_delay_error_to_pi", ""),
                    "transmission_x": phase_delay.get("transmission_x", ""),
                    "transmission_y": phase_delay.get("transmission_y", ""),
                    "status": status,
                    "phase_delay_summary": phase_delay_path,
                    "note": note,
                }
            )
        except (OSError, ValueError) as exc:
            result_rows.append(_missing_result_row(row, f"{type(exc).__name__}: {exc}"))

    return sorted(result_rows, key=_result_sort_key)


def write_xy_sweep_results(rows: list[dict[str, object]], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=XY_SWEEP_RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def filter_xy_sweep_rows(
    rows: list[dict[str, object]],
    case_ids: list[str] | None = None,
    include_all: bool = False,
) -> list[dict[str, object]]:
    if include_all:
        return rows
    if not case_ids:
        raise ValueError("Provide at least one case_id or use include_all=True")
    requested = set(case_ids)
    selected = [row for row in rows if str(row["case_id"]) in requested]
    found = {str(row["case_id"]) for row in selected}
    missing = sorted(requested - found)
    if missing:
        raise ValueError(f"Unknown case_id(s): {', '.join(missing)}")
    return selected


def _missing_result_row(row: dict[str, object], note: str) -> dict[str, object]:
    return {
        "case_id": row["case_id"],
        "length_nm": row["length_nm"],
        "width_nm": row["width_nm"],
        "height_nm": row["height_nm"],
        "rotation_deg": row["rotation_deg"],
        "phase_delay_rad": "",
        "phase_delay_error_to_pi": "",
        "transmission_x": "",
        "transmission_y": "",
        "status": "missing",
        "phase_delay_summary": row["phase_delay_summary"],
        "note": note,
    }


def _read_csv_single_row(path: Path) -> dict[str, str]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one row in {path}, got {len(rows)}")
    return rows[0]


def _result_sort_key(row: dict[str, object]) -> tuple[int, float, str]:
    if row["status"] != "ok":
        return (1, math.inf, str(row["case_id"]))
    try:
        return (0, float(row["phase_delay_error_to_pi"]), str(row["case_id"]))
    except (TypeError, ValueError):
        return (1, math.inf, str(row["case_id"]))


def _write_case_config(
    base_config: dict[str, Any],
    output_path: Path,
    length_nm: float,
    width_nm: float,
    height_nm: float,
    rotation_deg: float,
) -> None:
    data = _copy_mapping(base_config)
    data["geometry"]["length_nm"] = _typed_number(length_nm)
    data["geometry"]["width_nm"] = _typed_number(width_nm)
    data["geometry"]["height_nm"] = _typed_number(height_nm)
    data["geometry"]["rotation_deg"] = _typed_number(rotation_deg)
    data["output"]["result_dir"] = str(output_path.parent)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def _read_yaml_mapping(path: Union[str, Path]) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")
    return data


def _required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Missing required mapping section: {key}")
    return value


def _number_list(data: dict[str, Any], key: str) -> list[float]:
    values = data.get(key)
    if not isinstance(values, list) or not values:
        raise ValueError(f"Expected non-empty list: {key}")
    return [float(value) for value in values]


def _copy_mapping(data: dict[str, Any]) -> dict[str, Any]:
    return yaml.safe_load(yaml.safe_dump(data, sort_keys=False))


def _case_id(length_nm: float, width_nm: float, height_nm: float, rotation_deg: float) -> str:
    return (
        f"L{_format_number(length_nm)}"
        f"_W{_format_number(width_nm)}"
        f"_H{_format_number(height_nm)}"
        f"_R{_format_number(rotation_deg)}"
    )


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value).replace(".", "p")


def _typed_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else value

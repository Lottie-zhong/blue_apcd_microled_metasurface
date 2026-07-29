"""Native APCD blue material library for Python/TMM/ML post-processing."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "material_reference_apcd_blue.yaml"


class MaterialRangeError(ValueError):
    """Requested wavelength lies outside the native sampled material range."""


def _read_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _native_csv_path(config: dict[str, Any]) -> Path:
    try:
        raw = config["native_library"]["native_csv"]
    except KeyError as exc:
        raise KeyError("native_library.native_csv missing from material reference config") from exc
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


@lru_cache(maxsize=2)
def load_material_library(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, dict[str, Any]]:
    """Load native sampled epsilon data without any FSP dependency."""
    config = _read_config(Path(config_path))
    aliases = {
        config["materials"]["TiO2_reference"]["source_name"]: "APCD_TIO2_NATIVE_M1",
        config["materials"]["SiO2_reference"]["source_name"]: "APCD_SIO2_NATIVE_M1",
    }
    library: dict[str, dict[str, Any]] = {}
    with _native_csv_path(config).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            material_id = aliases.get(row["material_name"])
            if material_id is None:
                continue
            entry = library.setdefault(material_id, {
                "material_reference_id": material_id,
                "canonical_name": "TiO2_native" if "TIO2" in material_id else "SiO2_native",
                "source_name": row["material_name"],
                "source_fsp_path": row["source_fsp_path"],
                "interpolation_axis": "frequency_hz",
                "extrapolation_allowed": False,
                "frequency_hz": [], "epsilon": [], "native_rows": [],
            })
            entry["frequency_hz"].append(float(row["frequency_hz"]))
            entry["epsilon"].append(complex(float(row["epsilon_real"]), float(row["epsilon_imag"])))
            entry["native_rows"].append(dict(row))
    for entry in library.values():
        order = np.argsort(entry["frequency_hz"])
        entry["frequency_hz"] = np.asarray(entry["frequency_hz"], dtype=float)[order]
        entry["epsilon"] = np.asarray(entry["epsilon"], dtype=np.complex128)[order]
        entry["native_rows"] = [entry["native_rows"][i] for i in order]
        wavelengths = 299792458.0 / entry["frequency_hz"] * 1e9
        entry["native_lambda_min_nm"] = float(wavelengths.min())
        entry["native_lambda_max_nm"] = float(wavelengths.max())
        entry["native_sample_count"] = int(len(entry["frequency_hz"]))
        entry["is_dispersive"] = True
        entry["is_lossy"] = bool(np.any(np.abs(entry["epsilon"].imag) > 0.0))
    return library


def get_material_metadata(material_reference_id: str) -> dict[str, Any]:
    entry = load_material_library()[material_reference_id]
    return {key: value for key, value in entry.items() if key not in {"frequency_hz", "epsilon", "native_rows"}}


def get_native_samples(material_reference_id: str) -> list[dict[str, str]]:
    return list(load_material_library()[material_reference_id]["native_rows"])


def validate_wavelength_range(material_reference_id: str, wavelength_nm: float) -> None:
    entry = load_material_library()[material_reference_id]
    lower, upper = entry["native_lambda_min_nm"], entry["native_lambda_max_nm"]
    if not lower <= wavelength_nm <= upper:
        raise MaterialRangeError(
            f"{material_reference_id}: {wavelength_nm} nm outside native range {lower}..{upper} nm; extrapolation is disabled"
        )


def get_epsilon(material_reference_id: str, wavelength_nm: float) -> complex:
    """Interpolate real/imag epsilon linearly on the native frequency axis."""
    validate_wavelength_range(material_reference_id, wavelength_nm)
    entry = load_material_library()[material_reference_id]
    frequency = 299792458.0 / (wavelength_nm * 1e-9)
    eps = entry["epsilon"]
    return complex(
        np.interp(frequency, entry["frequency_hz"], eps.real),
        np.interp(frequency, entry["frequency_hz"], eps.imag),
    )


def get_nk(material_reference_id: str, wavelength_nm: float) -> complex:
    """Return physical principal n+i*k reconstructed from native epsilon."""
    value = complex(np.sqrt(get_epsilon(material_reference_id, wavelength_nm)))
    return -value if value.real < 0 else value

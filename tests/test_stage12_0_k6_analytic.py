from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_k6_analytic import (
    FORWARD_BINS,
    REVERSE_BINS,
    Metadata,
    build_order_coefficients,
    compute_array_factor,
    diagnose,
    read_phase_library,
)


def test_reads_h500_stage12_six_bin_handoff_fixture(tmp_path: Path) -> None:
    path = write_fixture_library(tmp_path)
    entries = read_phase_library(path)

    assert sorted(entries) == [0, 60, 120, 180, 240, 300]
    assert entries[240].candidate_id == "H500DIMER2F_026_B240_x_pair_swap_G90_O-28"
    assert entries[240].Tx == 0.737551


def test_forward_and_reverse_phase_order_generation(tmp_path: Path) -> None:
    entries = read_phase_library(write_fixture_library(tmp_path))
    metadata = Metadata(wavelength_nm=450.0, dimer_pitch_x_nm=431.907786)

    forward = build_order_coefficients(entries, FORWARD_BINS, "forward", metadata)
    reverse = build_order_coefficients(entries, REVERSE_BINS, "reverse", metadata)

    assert [row["target_bin_deg"] for row in forward] == [0, 60, 120, 180, 240, 300]
    assert [row["target_bin_deg"] for row in reverse] == [300, 240, 180, 120, 60, 0]
    assert float(forward[4]["field_amplitude_sqrt_Tx"]) == math.sqrt(0.737551)


def test_ideal_array_factor_routes_orders(tmp_path: Path) -> None:
    entries = read_phase_library(write_ideal_library(tmp_path))
    metadata = Metadata(wavelength_nm=450.0, dimer_pitch_x_nm=431.907786)
    forward = build_order_coefficients(entries, FORWARD_BINS, "forward", metadata)
    reverse = build_order_coefficients(entries, REVERSE_BINS, "reverse", metadata)

    forward_diag = diagnose(forward, compute_array_factor(forward, metadata))
    reverse_diag = diagnose(reverse, compute_array_factor(reverse, metadata))

    assert forward_diag["dominant_order_m"] == 1
    assert reverse_diag["dominant_order_m"] == -1
    assert forward_diag["dominant_relative_strength"] > 0.999999
    assert reverse_diag["dominant_relative_strength"] > 0.999999


def write_fixture_library(tmp_path: Path) -> Path:
    path = tmp_path / "stage12_handoff_phase_library.csv"
    rows = [
        (0, "H500DIMER2C_029_B240_x_pair_noswap_G60_O-20", -3.239252, 3.239252, 1.015647),
        (60, "H500DIMER2B_006_B180_x_pair_swap_G60_O-20", 63.970518, 3.970518, 0.991815),
        (120, "H500DIMER2D_040_B300_y_pair_noswap_G20_O-40", 128.570843, 8.570843, 0.814037),
        (180, "H500DIMER2C_026_B240_x_pair_swap_G60_O-20", 175.864813, 4.135187, 0.921578),
        (240, "H500DIMER2F_026_B240_x_pair_swap_G90_O-28", -127.365287, 7.365287, 0.737551),
        (300, "H500DIMER2D_006_B240_x_pair_swap_G80_O-30", -52.525765, 7.474235, 0.987489),
    ]
    write_rows(path, rows)
    return path


def write_ideal_library(tmp_path: Path) -> Path:
    path = tmp_path / "ideal_stage12_handoff_phase_library.csv"
    rows = [(phase, f"ideal_{phase}", phase, 0.0, 1.0) for phase in FORWARD_BINS]
    write_rows(path, rows)
    return path


def write_rows(path: Path, rows: list[tuple[int, str, float, float, float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "phase_bin_deg",
                "candidate_id",
                "actual_common_phase_deg",
                "phase_err_deg",
                "selected_x_power",
                "blocked_y_leakage",
                "conversion_to_leakage_ratio",
                "matrix_error",
                "geometry_family",
                "source_stage",
                "source_file",
            ],
        )
        writer.writeheader()
        for phase_bin, candidate, actual_phase, phase_err, tx in rows:
            writer.writerow(
                {
                    "phase_bin_deg": phase_bin,
                    "candidate_id": candidate,
                    "actual_common_phase_deg": actual_phase,
                    "phase_err_deg": phase_err,
                    "selected_x_power": tx,
                    "blocked_y_leakage": 0.01,
                    "conversion_to_leakage_ratio": 10.0,
                    "matrix_error": 0.1,
                    "geometry_family": "fixture",
                    "source_stage": "fixture",
                    "source_file": "fixture.csv",
                }
            )

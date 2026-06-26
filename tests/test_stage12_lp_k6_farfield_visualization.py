import json
import math
from pathlib import Path

from metasurface.stage12_lp_k6_farfield_visualization import fwhm_from_cut, make_manifest, target_peak


def test_fwhm_from_synthetic_gaussian_like_data():
    angles = [x * 0.1 for x in range(51, 150)]
    sigma = 1.0
    intensities = [math.exp(-0.5 * ((a - 10.0) / sigma) ** 2) for a in angles]
    out = fwhm_from_cut(angles, intensities, 10.0)
    assert abs(out["peak_angle_deg"] - 10.0) < 0.11
    assert abs(out["fwhm_deg"] - 2.355) < 0.05


def test_target_peak_detection_near_angle():
    angles = [0, 5, 10, 15]
    intensities = [10, 1, 5, 2]
    assert target_peak(angles, intensities, 10, window_deg=2) == 2


def test_plot_manifest_generation(tmp_path: Path):
    manifest = make_manifest(["a.csv"], ["fig.png"], [], tmp_path)
    assert manifest["input_files_used"] == ["a.csv"]
    assert manifest["generated_figures"] == ["fig.png"]
    assert manifest["raw_farfield_arrays_found"] == []
    json.dumps(manifest)

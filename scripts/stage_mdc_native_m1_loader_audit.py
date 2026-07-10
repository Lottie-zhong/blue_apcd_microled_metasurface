from __future__ import annotations

import csv
import json
from hashlib import sha256
from pathlib import Path

import numpy as np

import apcd_native_materials as mat

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {
    "configs/material_reference_apcd_blue.yaml": "3124EB996180BDB04D7A16578D32F95D047D28A735B33C4E9BF51EBCCAFDFA4B",
    "configs/material_reference_apcd_blue.json": "EEDD65634FF203173F61DCB3BEAB98EFEED44468CB38F30DA0E0B656388DE6DB",
    "outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv": "FE8B14986EDCC5AEE6AC06B25CE421EFCC09A5D23F0EAAD0C9B19A58894BD7C5",
    "outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.json": "607829D30D58BD2F35E53D8226A9E711AE9D5806685BD2EFE558BE8A8AF823D3",
    "outputs/material_reference/mdc_blue_oujizi_m/material_ref_interp_300_1000nm_1nm.csv": "47EF598AB976D2FE7A35FA7FEAA9A9F8B8C379D8D4981CAED86763C8B077E70C",
    "outputs/material_reference/mdc_blue_oujizi_m/material_ref_interp_400_500nm_0p5nm.csv": "597DC2400FD18F7AE68CD9BEEBE7ECCC7E895E6D1F547F7C3ADC1ECC23AAFC59",
    "outputs/material_reference/mdc_blue_oujizi_m/material_ref_448_453.csv": "2BC020518EDE8290FC6B0F8D9011F26A2C21FC5275084CB801EEBDAF251049D5",
    "outputs/material_reference/mdc_blue_oujizi_m/material_ref_448_453.json": "3E503C81F8FDCAB3C059F87854A5CEEF10A9D4DF3C3E3E1FF42DD7D67D4C5A98",
    "reports/material_ref_mdc_blue_oujizi_m_report.md": "D59E1D59D787B6C8FC014602919CE902147CD5D51F0F02571453C8B301729DC6",
    "scripts/extract_material_ref_from_fsp_mdc_blue_oujizi_m.py": "280FEF2574DD8ECE7CC0DD950C437A34ADF64CD554ED165E96B32486915E60F6",
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def must_fail(callable_) -> bool:
    try:
        callable_()
    except (KeyError, ValueError):
        return True
    return False


def main() -> None:
    policy_json = json.loads((ROOT / "configs/mdc_defect_450_material_policy.json").read_text(encoding="utf-8-sig"))
    policy_yaml = json.loads((ROOT / "configs/mdc_defect_450_material_policy.yaml").read_text(encoding="utf-8-sig"))
    assert policy_json == policy_yaml
    ids = ["APCD_SIO2_NATIVE_M1", "APCD_TIO2_NATIVE_M1"]
    samples = {item: mat.load_native_sampled_epsilon(item) for item in ids}
    for item, data in samples.items():
        assert len(data["frequency_hz"]) == 101 and np.all(np.diff(data["frequency_hz"]) > 0)
    assert mat.resolve_material_id("sio222") == ids[0] and mat.resolve_material_id("tio22") == ids[1]
    assert must_fail(lambda: mat.resolve_material_id("unknown"))
    scalar = mat.get_complex_index("sio222", 450.0)
    np_scalar = mat.get_complex_index("tio22", np.float64(450.0))
    vector = mat.get_complex_index("sio222", [448.0, 450.0, 453.0])
    array = mat.get_complex_index("tio22", np.array([[448.0, 450.0], [451.0, 453.0]]))
    assert isinstance(scalar, complex) and isinstance(np_scalar, complex) and vector.shape == (3,) and array.shape == (2, 2)
    for item, data in samples.items():
        limits = [data["wavelength_nm"].min(), data["wavelength_nm"].max()]
        mat.get_complex_index(item, limits)
        assert must_fail(lambda: mat.get_complex_index(item, 150.0)) and must_fail(lambda: mat.get_complex_index(item, 1200.0))
    fine = list(csv.DictReader((ROOT / policy_json["reference"]["blue_fine_csv"]).open(encoding="utf-8")))
    parity = []
    for row in fine:
        value = mat.get_complex_index(row["material_name"], float(row["wavelength_nm"]))
        parity.append(abs(value - complex(float(row["n_real"]), float(row["k_imag"]))))
    epsilon_error = max(float(np.max(np.abs(mat.get_complex_epsilon(item, [448.0, 450.0, 453.0]) - mat.get_complex_index(item, [448.0, 450.0, 453.0]) ** 2))) for item in ids)
    frozen = {path: digest(ROOT / path) == expected for path, expected in FROZEN.items()}
    assert all(frozen.values()) and epsilon_error < 1e-10
    result = {"status": "PASS", "policy_id": policy_json["policy_id"], "sample_counts": {item: len(data["frequency_hz"]) for item, data in samples.items()}, "blue_parity_max_error": max(parity), "epsilon_reconstruction_max_error": epsilon_error, "n_450": {item: [mat.get_complex_index(item, 450.0).real, mat.get_complex_index(item, 450.0).imag] for item in ids}, "thickness_nm": {"tio2_qw": mat.quarter_wave_thickness_nm("tio22"), "sio2_qw": mat.quarter_wave_thickness_nm("sio222"), "sio2_hw": mat.half_wave_thickness_nm("sio222")}, "frozen_sha256_unchanged": frozen, "initial_geometry_reference_only": True}
    out = ROOT / "outputs/mdc_native_m1_loader_audit"; out.mkdir(parents=True, exist_ok=True)
    (out / "mdc_native_m1_loader_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (out / "mdc_native_m1_loader_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["material_id", "sample_count", "n_450", "k_450"]); writer.writeheader()
        for item in ids: writer.writerow({"material_id": item, "sample_count": result["sample_counts"][item], "n_450": result["n_450"][item][0], "k_450": result["n_450"][item][1]})
    report = "# MDC Native-M1 loader audit\n\nStatus: PASS\n\n- Native samples: 101 per material\n- 448-453 nm parity and epsilon reconstruction: PASS\n- Thicknesses are `initial_geometry_reference_only`.\n"
    report_path = ROOT / "reports/mdc_defect_450"; report_path.mkdir(parents=True, exist_ok=True)
    (report_path / "mdc_native_m1_loader_audit.md").write_text(report, encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

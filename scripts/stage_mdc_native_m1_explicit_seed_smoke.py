from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

import apcd_native_materials as materials
from mdc_tmm_core import emission_tmm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/mdc_native_m1_explicit_seed_smoke"
REPORT = ROOT / "reports/mdc_defect_450/mdc_native_m1_explicit_seed_smoke.md"
CANDIDATE = "MDC_NATIVE_M1_EXPLICIT_FAB_SEED_N3_L79_H45_C156"
GEOMETRY = {"N": 3, "L_nm": 79, "H_nm": 45, "L_defect_nm": 156}
TOPOLOGY = "Air / (L/H)^3 / L_defect / (H/L)^3 / GaN"
WAVELENGTHS = np.arange(430.0, 470.0001, 0.25)


def design_layers():
    return [("L", 79), ("H", 45)] * 3 + [("L", 156)] + [("H", 45), ("L", 79)] * 3


def average_t(wavelength, angle, model):
    te = emission_tmm(design_layers(), wavelength, angle, "TE", model)["T"]
    tm = emission_tmm(design_layers(), wavelength, angle, "TM", model)["T"]
    return te, tm, (te + tm) / 2


def fwhm(rows):
    peak = max(rows, key=lambda row: row["T_avg"])
    half = peak["T_avg"] / 2
    xs = [row["wavelength_nm"] for row in rows]; ys = [row["T_avg"] for row in rows]
    left = next((xs[i] for i in range(xs.index(peak["wavelength_nm"]), 0, -1) if ys[i - 1] < half <= ys[i]), xs[0])
    right = next((xs[i] for i in range(xs.index(peak["wavelength_nm"]), len(xs) - 1) if ys[i] >= half > ys[i + 1]), xs[-1])
    return peak["wavelength_nm"], peak["T_avg"], right - left


def metadata(model):
    item = {"candidate_id": CANDIDATE, "material_policy_id": "MDC_NATIVE_M1", "material_model": model, "high_index_material_id": "APCD_TIO2_NATIVE_M1", "low_index_material_id": "APCD_SIO2_NATIVE_M1", "defect_material_id": "APCD_SIO2_NATIVE_M1", "interpolation_source_quantity": "complex_epsilon", "interpolation_axis": "frequency_hz", "interpolation_method": "linear", "complex_index_reconstruction": "physical_principal_square_root", "extrapolation_policy": "forbidden", "geometry": json.dumps(GEOMETRY), "topology": TOPOLOGY, "propagation_direction": "GaN -> reverse(stack) -> Air"}
    if model == "legacy_constant_index": item.update({"legacy_profile": "tio2_2p25_sio2_1p47", "result_status": "historical_regression_comparison", "formal_engineering_baseline": False})
    else: item.update({"result_status": "native_m1_smoke_not_formal_baseline", "formal_engineering_baseline": False})
    return item


def main():
    OUT.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    all_spectra = []; metrics = []
    for model in ("native_m1", "legacy_constant_index"):
        by_angle = {}
        for angle in (0, 20):
            rows = []
            for wavelength in WAVELENGTHS:
                te, tm, avg = average_t(float(wavelength), angle, model)
                row = {**metadata(model), "wavelength_nm": float(wavelength), "external_air_angle_deg": angle, "T_TE": te, "T_TM": tm, "T_avg": avg, "R_TE": emission_tmm(design_layers(), float(wavelength), angle, "TE", model)["R"], "R_TM": emission_tmm(design_layers(), float(wavelength), angle, "TM", model)["R"]}
                rows.append(row); all_spectra.append(row)
            by_angle[angle] = rows
        peak, tpeak, width = fwhm(by_angle[0]); t450 = next(row["T_avg"] for row in by_angle[0] if row["wavelength_nm"] == 450); t450_20 = next(row["T_avg"] for row in by_angle[20] if row["wavelength_nm"] == 450)
        normal = np.mean([average_t(450, a, model)[2] for a in range(0, 11, 5)]); high = np.mean([average_t(450, a, model)[2] for a in range(40, 61, 5)])
        metrics.append({**metadata(model), "peak_wavelength_nm": peak, "Tpeak": tpeak, "FWHM_nm": width, "T450": t450, "T450_at_20deg": t450_20, "normal_to_40_60_ratio": normal / (high + 1e-12), "T450_TE": next(row["T_TE"] for row in by_angle[0] if row["wavelength_nm"] == 450), "T450_TM": next(row["T_TM"] for row in by_angle[0] if row["wavelength_nm"] == 450)})
    native, legacy = metrics
    for row in metrics: row.update({"native_minus_legacy_T450": native["T450"] - legacy["T450"], "native_minus_legacy_peak_nm": native["peak_wavelength_nm"] - legacy["peak_wavelength_nm"]})
    def write_csv(path, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row})); writer.writeheader(); writer.writerows(rows)
    write_csv(OUT / "metrics.csv", metrics); write_csv(OUT / "spectra.csv", all_spectra); write_csv(OUT / "blue_448_453.csv", [row for row in all_spectra if 448 <= row["wavelength_nm"] <= 453])
    manifest = {"candidate_id": CANDIDATE, "formal_default": "native_m1", "legacy_explicit_only": True, "metric_formula": "MDC1B normal_to_40_60_ratio = mean T450(0-10deg) / mean T450(40-60deg)", "outputs": ["metrics.csv", "spectra.csv", "blue_448_453.csv"]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text("# Native-M1 explicit seed smoke\n\nFixed N=3 candidate; not a formal baseline. Reuses MDC0V characteristic matrix and MDC1B ratio definition.\n\n" + "\n".join(f"- {row['material_model']}: peak={row['peak_wavelength_nm']:.2f} nm, T450={row['T450']:.6f}, ratio={row['normal_to_40_60_ratio']:.4f}" for row in metrics) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__": main()

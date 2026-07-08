from pathlib import Path
from datetime import datetime

report_dir = Path("reports") / "mdc_defect_450"
report_dir.mkdir(parents=True, exist_ok=True)

md = []
md.append("# MDC1B local integer refine decision\n")
md.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n")

md.append("## Scope\n")
md.append("MDC1B is a pure Python TMM local integer-nm refinement stage. It does not use FMM, FDTD, Lumerical, RCLED, or any FSP file.\n")
md.append("Default physical direction remains:\n\n```text\nGaN -> reverse(defect-MDC stack) -> Air\n```\n")

md.append("## Selected candidates\n")

md.append("### MDC-Baseline-Fab: MDC1B_FAB_0126\n")
md.append("```text\nTopology = T1\nN = 3\nL = SiO2 79 nm\nH = TiO2 45 nm\nC = SiO2 defect 156 nm\nLayer count = 13\npeak = 450.00 nm\nTpeak = 0.8293\nFWHM = 8.25 nm\nT450_0 = 0.8293\nT450_20 = 0.1318\nnormal_to_40_60_ratio = 38.58\nrobust_peak_span = 12.00 nm\nrobust_T4500_min = 0.2795\n```\n")
md.append("Interpretation: This is the current first fabrication-friendly defect-MDC baseline. Compared with A0-INT, it keeps 13 layers, centers the peak at 450 nm, and improves the normal-to-large-angle ratio.\n")

md.append("Design-side layer sequence:\n")
md.append("```text\nAir / (SiO2 79 nm / TiO2 45 nm)^3 / SiO2_defect 156 nm / (TiO2 45 nm / SiO2 79 nm)^3 / GaN\n```\n")
md.append("Emission-side layer sequence:\n")
md.append("```text\nGaN / (SiO2 79 nm / TiO2 45 nm)^3 / SiO2_defect 156 nm / (TiO2 45 nm / SiO2 79 nm)^3 / Air\n```\n")

md.append("### MDC-Performance: MDC1B_PERF_0890\n")
md.append("```text\nTopology = T1\nN = 4\nL = SiO2 81 nm\nH = TiO2 44 nm\nC = SiO2 defect 157 nm\nLayer count = 17\npeak = 450.00 nm\nTpeak = 0.8304\nFWHM = 2.50 nm\nT450_0 = 0.8304\nT450_20 = 0.0145\nnormal_to_40_60_ratio = 117.53\nrobust_peak_span = 12.00 nm\nrobust_T4500_min = 0.0368\n```\n")
md.append("Interpretation: This is the high-performance spectral-angular filter anchor. It is not the default fabrication baseline because 17 layers increase accumulated thickness-error risk and the light robust probe suggests high sensitivity.\n")

md.append("### MDC-Reference: MDC-A0-INT\n")
md.append("```text\nTopology = T1\nN = 3\nL = SiO2 79 nm\nH = TiO2 44 nm\nC = SiO2 defect 158 nm\nLayer count = 13\npeak = 449.0 nm\nTpeak = 0.8290\nFWHM = 8.0 nm\nT450_0 = 0.7882\nT450_20 = 0.1130\nnormal_to_40_60_ratio = 32.33\n```\n")
md.append("Interpretation: This remains the rounded quarter-wave / half-wave reference and is used to show that local integer tuning improves the 450 nm defect-MDC response.\n")

md.append("## T3 interpretation\n")
md.append("The top T3 candidates all had Nair=3 and Nled=3, which is layer-equivalent to the symmetric T1 N=3 case. Therefore T3 has not shown an independent asymmetric advantage in MDC1B and is not selected as a primary candidate.\n")

md.append("## Next stage recommendation\n")
md.append("Next stage should be MDC1C small-point stackrt/RCWA/FMM parity for the selected 2-3 candidates before any FDTD or FSP modification.\n")
md.append("Do not freeze a physical device from TMM alone.\n")

out = report_dir / "mdc1b_local_integer_refine_decision.md"
out.write_text("\n".join(md), encoding="utf-8")
print(out)

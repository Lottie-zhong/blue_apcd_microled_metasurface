from pathlib import Path
import csv
import json
from datetime import datetime

report_dir = Path("reports") / "mdc_defect_450"
report_dir.mkdir(parents=True, exist_ok=True)

summary_path = Path("outputs") / "mdc1a_integer_nm_defect_mdc_screen" / "mdc1a_integer_summary.json"
shortlist_md = Path("outputs") / "mdc1a_integer_shortlist_audit" / "mdc1a_integer_shortlist_audit.md"
metrics_csv = Path("outputs") / "mdc1a_integer_nm_defect_mdc_screen" / "mdc1a_integer_candidate_metrics.csv"

summary = json.loads(summary_path.read_text(encoding="utf-8"))

def read_candidate(cid):
    with metrics_csv.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["candidate_id"] == cid:
                return row
    return None

key_ids = [
    "MDC-A0-INT",
    "MDC1A_0202",
    "MDC1A_0319",
    "MDC1A_0227",
    "MDC1A_0577",
    "MDC1A_0694",
]

key_rows = [read_candidate(cid) for cid in key_ids]
key_rows = [r for r in key_rows if r is not None]

def fmt(r):
    return (
        f"| {r['candidate_id']} | {r['topology']} | {r['N']} | {r['N_air']} | {r['N_led']} | "
        f"{r['L_SiO2_nm']} | {r['H_TiO2_nm']} | {r['C_defect_SiO2_nm']} | "
        f"{r['layer_count']} | {float(r['peak_nm_0deg']):.1f} | "
        f"{float(r['T_peak_0deg']):.4f} | {float(r['FWHM_nm_0deg']):.1f} | "
        f"{float(r['Tavg_450_0deg']):.4f} | {float(r['Tavg_450_20deg']):.4f} | "
        f"{float(r['normal_to_40_60_ratio']):.2f} | {float(r['score']):.4g} |"
    )

md = []
md.append("# MDC defect-450 branch freeze: MDC0V + MDC1A integer TMM\n")
md.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n")
md.append("## Scope\n")
md.append("This freeze records the lightweight code and key results for the 450 nm top defect-MDC branch.\n")
md.append("No FSP, no Lumerical run, no FDTD, no RCLED continuation, no push.\n")
md.append("Default physical direction for later ranking is:\n\n```text\nGaN -> reverse(film stack) -> Air\n```\n")
md.append("## MDC0V validation result\n")
md.append("- TMM validation checks: PASS\n")
md.append("- Identity / Fresnel / oblique interface / energy conservation / reciprocity checks passed.\n")
md.append("- Integer-nm policy adopted after MDC0V/MDC1A discussion.\n")
md.append("\n## Integer baseline thickness\n")
fixed = summary["fixed_integer_baseline_nm"]
md.append(f"- SiO2 L = {fixed['SiO2_L']} nm\n")
md.append(f"- TiO2 H = {fixed['TiO2_H']} nm\n")
md.append(f"- SiO2 defect C0 = {fixed['SiO2_defect_C0']} nm\n")
md.append("\n## Key candidate comparison\n")
md.append("| candidate | topo | N | Nair | Nled | L | H | C | layers | peak | Tpeak | FWHM | T450_0 | T450_20 | ratio | score |")
md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for r in key_rows:
    md.append(fmt(r))
md.append("\n## Current interpretation\n")
md.append("- `MDC-A0-INT` is the rounded baseline: T1, N=3, L=79, H=44, C=158, 13 layers, peak around 449 nm, FWHM around 8 nm.\n")
md.append("- `MDC1A_0202` is the current fabrication-friendly anchor: T1, N=3, L=81, H=43, C=160, 13 layers, peak 450 nm, FWHM 8 nm, high T450_0.\n")
md.append("- `MDC1A_0319` is the current performance anchor: T1, N=4, L=81, H=43, C=160, 17 layers, peak 450 nm, FWHM 2 nm, much stronger angular suppression but higher layer-count risk.\n")
md.append("- N=3 is preferred for first physical MDC baseline because layer count and thickness-error accumulation are lower.\n")
md.append("- N=4 remains a high-performance comparison candidate, not the immediate default fabrication baseline.\n")
md.append("\n## Local output references\n")
md.append("- `outputs/mdc0v_tmm_validation_and_baseline_audit/`\n")
md.append("- `outputs/mdc1a_integer_nm_defect_mdc_screen/`\n")
md.append("- `outputs/mdc1a_integer_shortlist_audit/`\n")
md.append("\n## Files intentionally tracked in this commit\n")
md.append("- `scripts/stage_mdc0v_tmm_validation_and_baseline_audit.py`\n")
md.append("- `scripts/stage_mdc1a_tmm_defect_mdc_450_screen.py`\n")
md.append("- `scripts/stage_mdc1a_integer_shortlist_audit.py`\n")
md.append("- this lightweight report under `reports/mdc_defect_450/`\n")
md.append("\n## Files intentionally not tracked\n")
md.append("- `.fsp`, `.ldf`, `.mat`, `.h5`, `.npy`, `.npz`, raw monitor data, runtime folders.\n")

out = report_dir / "mdc0v_mdc1a_integer_tmm_freeze.md"
out.write_text("\n".join(md), encoding="utf-8")
print(out)

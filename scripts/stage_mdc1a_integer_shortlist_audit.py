from pathlib import Path
import csv, json

SRC = Path("outputs") / "mdc1a_integer_nm_defect_mdc_screen" / "mdc1a_integer_candidate_metrics.csv"
OUT = Path("outputs") / "mdc1a_integer_shortlist_audit"
OUT.mkdir(parents=True, exist_ok=True)

def f(row, key):
    v = row.get(key, "")
    if v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None

def i(row, key):
    v = row.get(key, "")
    if v == "":
        return None
    try:
        return int(float(v))
    except Exception:
        return None

with SRC.open("r", encoding="utf-8") as fp:
    rows = list(csv.DictReader(fp))

def sort_score(rs):
    return sorted(rs, key=lambda r: f(r, "score") or -1, reverse=True)

def keep_basic(r):
    return (
        abs((f(r, "peak_nm_0deg") or 999) - 450.0) <= 1.0
        and (f(r, "T_peak_0deg") or 0) >= 0.5
        and (f(r, "Tavg_450_0deg") or 0) >= 0.5
    )

a0 = [r for r in rows if r["candidate_id"] == "MDC-A0-INT"]

performance_anchor = sort_score([
    r for r in rows
    if keep_basic(r)
    and (i(r, "layer_count") or 999) <= 17
    and (f(r, "FWHM_nm_0deg") or 999) <= 4.0
])[:10]

fabrication_anchor = sort_score([
    r for r in rows
    if keep_basic(r)
    and (i(r, "layer_count") or 999) <= 13
    and 5.0 <= (f(r, "FWHM_nm_0deg") or 999) <= 12.0
])[:10]

asym_anchor = sort_score([
    r for r in rows
    if keep_basic(r)
    and r["topology"] == "T3"
    and (i(r, "layer_count") or 999) <= 15
])[:10]

ids = set()
for group in [a0, performance_anchor, fabrication_anchor, asym_anchor]:
    for r in group:
        ids.add(r["candidate_id"])

short = [r for r in rows if r["candidate_id"] in ids]
short = sorted(short, key=lambda r: (
    0 if r["candidate_id"] == "MDC-A0-INT" else 1,
    i(r, "layer_count") or 999,
    abs((f(r, "peak_nm_0deg") or 999) - 450.0),
    -(f(r, "score") or 0),
))

out_csv = OUT / "mdc1a_integer_shortlist_audit.csv"
with out_csv.open("w", newline="", encoding="utf-8") as fp:
    w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(short)

summary = {
    "source_csv": str(SRC),
    "baseline_A0": a0,
    "performance_anchor_top10": performance_anchor,
    "fabrication_anchor_top10": fabrication_anchor,
    "asym_anchor_top10": asym_anchor,
    "shortlist_csv": str(out_csv),
}

out_json = OUT / "mdc1a_integer_shortlist_audit.json"
out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

def one_line(r):
    return (
        f"{r['candidate_id']} topo={r['topology']} N={r['N']} Nair={r['N_air']} Nled={r['N_led']} "
        f"L={r['L_SiO2_nm']} H={r['H_TiO2_nm']} C={r['C_defect_SiO2_nm']} "
        f"layers={r['layer_count']} peak={float(r['peak_nm_0deg']):.1f} "
        f"Tpeak={float(r['T_peak_0deg']):.4f} FWHM={float(r['FWHM_nm_0deg']):.1f} "
        f"T450_0={float(r['Tavg_450_0deg']):.4f} T450_20={float(r['Tavg_450_20deg']):.4f} "
        f"ratio={float(r['normal_to_40_60_ratio']):.2f} robust_span={float(r['robust_probe_peak_span_nm']):.1f} "
        f"score={float(r['score']):.4g}"
    )

md = []
md.append("# MDC1A integer shortlist audit\n")
md.append("## A0 baseline\n")
for r in a0:
    md.append("- " + one_line(r))
md.append("\n## Performance anchor: N=4 / ultra-narrow candidates\n")
for r in performance_anchor[:5]:
    md.append("- " + one_line(r))
md.append("\n## Fabrication anchor: <=13 layers / moderate FWHM candidates\n")
for r in fabrication_anchor[:5]:
    md.append("- " + one_line(r))
md.append("\n## Asymmetric T3 anchor\n")
for r in asym_anchor[:5]:
    md.append("- " + one_line(r))
md.append("\n## Current interpretation\n")
md.append("- N=4 candidates are strong spectral-angular filters but have 17 layers and higher accumulated thickness-error risk.")
md.append("- N=3 candidates are more fabrication-friendly and likely better as the first defect-MDC baseline.")
md.append("- Do not freeze from TMM alone; next step should pick 2-3 candidates for finer TMM around integer thickness and later FDTD/stackrt parity.")
out_md = OUT / "mdc1a_integer_shortlist_audit.md"
out_md.write_text("\n".join(md), encoding="utf-8")

print("MDC1A shortlist audit complete")
print("A0 baseline:")
for r in a0:
    print("  " + one_line(r))
print("")
print("Performance anchor top5:")
for r in performance_anchor[:5]:
    print("  " + one_line(r))
print("")
print("Fabrication anchor top5:")
for r in fabrication_anchor[:5]:
    print("  " + one_line(r))
print("")
print("Asymmetric T3 anchor top5:")
for r in asym_anchor[:5]:
    print("  " + one_line(r))
print("")
print(f"shortlist_csv={out_csv}")
print(f"shortlist_json={out_json}")
print(f"shortlist_md={out_md}")

from pathlib import Path
import math, cmath, csv, json

OUT = Path("outputs") / "mdc1b_local_integer_refine"
OUT.mkdir(parents=True, exist_ok=True)

NIDX = {"Air": 1.0, "SiO2": 1.426, "TiO2": 2.535, "GaN": 2.41}
LAMBDAS = [x * 0.25 for x in range(1720, 1881)]  # 430-470 nm, 0.25 nm
THETAS_AIR = list(range(0, 61, 5))

def c_sqrt(x):
    z = cmath.sqrt(x)
    return -z if z.real < -1e-14 else z

def admittance(n, c, pol):
    return n * c if pol == "s" else n / c

def mmul(A, B):
    a,b,c,d = A; e,f,g,h = B
    return (a*e+b*g, a*f+b*h, c*e+d*g, c*f+d*h)

def tmm(n_in, n_out, layers, wl, theta_in_deg, pol):
    s0 = math.sin(math.radians(theta_in_deg))
    c0 = c_sqrt(1 - s0*s0)
    q0 = admittance(n_in, c0, pol)
    M = (1+0j, 0j, 0j, 1+0j)

    for mat, d in layers:
        nj = NIDX[mat]
        sj = n_in * s0 / nj
        cj = c_sqrt(1 - sj*sj)
        qj = admittance(nj, cj, pol)
        delta = 2 * math.pi * nj * d * cj / wl
        cd, sd = cmath.cos(delta), cmath.sin(delta)
        M = mmul(M, (cd, 1j*sd/qj, 1j*qj*sd, cd))

    ss = n_in * s0 / n_out
    cs = c_sqrt(1 - ss*ss)
    qs = admittance(n_out, cs, pol)

    A,B,C,D = M
    den = q0*A + q0*qs*B + C + qs*D
    r = (q0*A + q0*qs*B - C - qs*D) / den
    t = 2*q0 / den
    R = abs(r)**2
    T = ((qs/q0).real) * abs(t)**2
    return max(0.0, float(T)), max(0.0, float(R))

def theta_gan_from_air(theta_air):
    return math.degrees(math.asin(NIDX["Air"] / NIDX["GaN"] * math.sin(math.radians(theta_air))))

def LH(n, L, H):
    out = []
    for _ in range(n):
        out += [("SiO2", L), ("TiO2", H)]
    return out

def HL(n, L, H):
    out = []
    for _ in range(n):
        out += [("TiO2", H), ("SiO2", L)]
    return out

def reverse_layers(layers):
    return list(reversed(layers))

def design_layers(topology, N=None, Nair=None, Nled=None, L=79, H=44, C=158):
    if topology == "T1":
        return LH(N, L, H) + [("SiO2", C)] + HL(N, L, H)
    if topology == "T2":
        return HL(N, L, H) + [("SiO2", C)] + LH(N, L, H)
    if topology == "T3":
        return LH(Nair, L, H) + [("SiO2", C)] + HL(Nled, L, H)
    raise ValueError(topology)

def tavg_emission(layers_design, wl, theta_air):
    layers = reverse_layers(layers_design)
    theta_gan = theta_gan_from_air(theta_air)
    Ts, _ = tmm(NIDX["GaN"], NIDX["Air"], layers, wl, theta_gan, "s")
    Tp, _ = tmm(NIDX["GaN"], NIDX["Air"], layers, wl, theta_gan, "p")
    return 0.5*(Ts+Tp), Ts, Tp

def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def spectrum_0deg(layers):
    return [(wl, tavg_emission(layers, wl, 0)[0]) for wl in LAMBDAS]

def fwhm(spec):
    peak_wl, peak_T = max(spec, key=lambda x: x[1])
    half = peak_T / 2
    above = [wl for wl, T in spec if T >= half]
    return peak_wl, peak_T, (max(above) - min(above) if above else 999.0)

def interp_closest(layers, wl_target, theta_air):
    wl = min(LAMBDAS, key=lambda x: abs(x - wl_target))
    return tavg_emission(layers, wl, theta_air)[0]

def band_mean(layers, wl_min, wl_max, theta_values):
    vals = []
    for wl in LAMBDAS:
        if wl_min <= wl <= wl_max:
            for th in theta_values:
                vals.append(tavg_emission(layers, wl, th)[0])
    return mean(vals)

def angle_mean_450(layers, theta_min, theta_max):
    vals = []
    for th in THETAS_AIR:
        if theta_min <= th <= theta_max:
            vals.append(interp_closest(layers, 450.0, th))
    return mean(vals)

def light_robust_probe(layers):
    variants = []
    variants.append(("nominal", layers))

    variants.append(("all_plus_1", [(m, d+1) for m,d in layers]))
    variants.append(("all_minus_1", [(m, max(1, d-1)) for m,d in layers]))

    variants.append(("L_plus_1", [(m, d+1 if m=="SiO2" and d < 120 else d) for m,d in layers]))
    variants.append(("L_minus_1", [(m, max(1, d-1) if m=="SiO2" and d < 120 else d) for m,d in layers]))

    variants.append(("H_plus_1", [(m, d+1 if m=="TiO2" else d) for m,d in layers]))
    variants.append(("H_minus_1", [(m, max(1, d-1) if m=="TiO2" else d) for m,d in layers]))

    max_sio2 = max([d for m,d in layers if m=="SiO2"])
    variants.append(("C_plus_1", [(m, d+1 if m=="SiO2" and d==max_sio2 else d) for m,d in layers]))
    variants.append(("C_minus_1", [(m, max(1, d-1) if m=="SiO2" and d==max_sio2 else d) for m,d in layers]))

    peaks, t450s, tpeaks = [], [], []
    for _, v in variants:
        p, tp, _ = fwhm(spectrum_0deg(v))
        peaks.append(p)
        tpeaks.append(tp)
        t450s.append(interp_closest(v, 450.0, 0))

    return {
        "robust_peak_span_nm": max(peaks) - min(peaks),
        "robust_T4500_min": min(t450s),
        "robust_Tpeak_min": min(tpeaks),
    }

def metrics(cid, family, topology, N, Nair, Nled, L, H, C, layers):
    spec = spectrum_0deg(layers)
    peak, Tpeak, fw = fwhm(spec)

    T450_0 = interp_closest(layers, 450, 0)
    T450_10 = interp_closest(layers, 450, 10)
    T450_20 = interp_closest(layers, 450, 20)
    T450_30 = interp_closest(layers, 450, 30)

    m448_452_0 = band_mean(layers, 448, 452, [0])
    m448_452_0_10 = band_mean(layers, 448, 452, [0,5,10])
    m430_445_0 = band_mean(layers, 430, 445, [0])
    m455_470_0 = band_mean(layers, 455, 470, [0])

    m450_0_10 = angle_mean_450(layers, 0, 10)
    m450_20_40 = angle_mean_450(layers, 20, 40)
    m450_40_60 = angle_mean_450(layers, 40, 60)
    ratio = m450_0_10 / (m450_40_60 + 1e-12)

    _, Ts0, Tp0 = tavg_emission(layers, 450, 0)
    sp_imb = abs(Ts0 - Tp0) / (0.5*(Ts0+Tp0) + 1e-12)

    layer_count = len(layers)
    total_thickness = sum(d for _, d in layers)

    rb = light_robust_probe(layers) if Tpeak >= 0.05 else {
        "robust_peak_span_nm": 999.0,
        "robust_T4500_min": 0.0,
        "robust_Tpeak_min": 0.0,
    }

    peak_err = abs(peak - 450.0)
    layer_penalty = 1 + max(layer_count - 13, 0) * 0.08
    lowT_penalty = 1 if T450_0 >= 0.5 else 3

    fab_fwhm_penalty = 1 + abs(fw - 8.0) / 8.0
    fab_score = (
        m448_452_0_10
        * math.log1p(max(ratio, 0))
        / ((1 + peak_err/1.5) * fab_fwhm_penalty * layer_penalty * lowT_penalty)
    )

    perf_fwhm_penalty = 1 + max(fw - 4.0, 0) / 4.0
    perf_score = (
        m448_452_0_10
        * max(ratio, 0)
        / ((1 + peak_err/1.5) * perf_fwhm_penalty * layer_penalty * lowT_penalty)
    )

    return {
        "candidate_id": cid,
        "family": family,
        "topology": topology,
        "N": "" if N is None else N,
        "N_air": "" if Nair is None else Nair,
        "N_led": "" if Nled is None else Nled,
        "L_SiO2_nm": L,
        "H_TiO2_nm": H,
        "C_defect_SiO2_nm": C,
        "layer_count": layer_count,
        "total_thickness_nm": total_thickness,
        "peak_nm_0deg": peak,
        "peak_err_nm": peak_err,
        "T_peak_0deg": Tpeak,
        "FWHM_nm_0deg": fw,
        "Tavg_450_0deg": T450_0,
        "Tavg_450_10deg": T450_10,
        "Tavg_450_20deg": T450_20,
        "Tavg_450_30deg": T450_30,
        "mean_Tavg_448_452_0deg": m448_452_0,
        "mean_Tavg_448_452_0_10deg": m448_452_0_10,
        "mean_Tavg_430_445_0deg": m430_445_0,
        "mean_Tavg_455_470_0deg": m455_470_0,
        "mean_Tavg_450_0_10deg": m450_0_10,
        "mean_Tavg_450_20_40deg": m450_20_40,
        "mean_Tavg_450_40_60deg": m450_40_60,
        "normal_to_40_60_ratio": ratio,
        "sp_imbalance_450_0deg": sp_imb,
        "robust_peak_span_nm": rb["robust_peak_span_nm"],
        "robust_T4500_min": rb["robust_T4500_min"],
        "robust_Tpeak_min": rb["robust_Tpeak_min"],
        "fab_score": fab_score,
        "perf_score": perf_score,
        "design_layers": " / ".join([f"{m}:{d}nm" for m,d in layers]),
        "emission_layers": " / ".join([f"{m}:{d}nm" for m,d in reverse_layers(layers)]),
    }

rows = []
idx = 0

# A0 and previous anchors, explicitly retained.
anchor_defs = [
    ("MDC-A0-INT", "anchor", "T1", 3, None, None, 79, 44, 158),
    ("MDC1A_0202", "anchor", "T1", 3, None, None, 81, 43, 160),
    ("MDC1A_0319", "anchor", "T1", 4, None, None, 81, 43, 160),
    ("MDC1A_0577", "anchor", "T2", 3, None, None, 81, 45, 150),
    ("MDC1A_0694", "anchor", "T2", 4, None, None, 81, 45, 150),
]
for cid, fam, topo, N, Nair, Nled, L, H, C in anchor_defs:
    layers = design_layers(topo, N=N, Nair=Nair, Nled=Nled, L=L, H=H, C=C)
    rows.append(metrics(cid, fam, topo, N, Nair, Nled, L, H, C, layers))

# Fabrication-focused N=3 local refine around MDC1A_0202/A0.
for topo in ["T1", "T2"]:
    for L in range(78, 84):
        for H in range(42, 46):
            for C in range(150, 167):
                idx += 1
                cid = f"MDC1B_FAB_{idx:04d}"
                layers = design_layers(topo, N=3, L=L, H=H, C=C)
                rows.append(metrics(cid, "fab_N3", topo, 3, None, None, L, H, C, layers))

# Performance-focused N=4 local refine around MDC1A_0319.
for topo in ["T1", "T2"]:
    for L in range(79, 83):
        for H in range(42, 45):
            for C in range(156, 165):
                idx += 1
                cid = f"MDC1B_PERF_{idx:04d}"
                layers = design_layers(topo, N=4, L=L, H=H, C=C)
                rows.append(metrics(cid, "perf_N4", topo, 4, None, None, L, H, C, layers))

# T3 asymmetric local probe, not default baseline.
for Nair, Nled in [(3,3), (4,3), (3,4)]:
    for L in range(78, 83):
        for H in range(42, 46):
            for C in range(154, 165):
                idx += 1
                cid = f"MDC1B_T3_{idx:04d}"
                layers = design_layers("T3", Nair=Nair, Nled=Nled, L=L, H=H, C=C)
                rows.append(metrics(cid, "asym_T3", "T3", None, Nair, Nled, L, H, C, layers))

metrics_csv = OUT / "mdc1b_local_integer_refine_metrics.csv"
rows_by_fab = sorted(rows, key=lambda r: r["fab_score"], reverse=True)
with metrics_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows_by_fab)

def eligible_basic(r):
    return (
        abs(float(r["peak_nm_0deg"]) - 450.0) <= 1.0
        and float(r["Tavg_450_0deg"]) >= 0.65
        and float(r["T_peak_0deg"]) >= 0.65
    )

fab_top = [
    r for r in rows
    if eligible_basic(r) and r["family"] in ["fab_N3", "anchor"] and int(r["layer_count"]) <= 13 and 5.0 <= float(r["FWHM_nm_0deg"]) <= 12.0
]
fab_top = sorted(fab_top, key=lambda r: r["fab_score"], reverse=True)[:20]

perf_top = [
    r for r in rows
    if eligible_basic(r) and r["family"] in ["perf_N4", "anchor"] and int(r["layer_count"]) <= 17 and float(r["FWHM_nm_0deg"]) <= 4.0
]
perf_top = sorted(perf_top, key=lambda r: r["perf_score"], reverse=True)[:20]

t3_top = [
    r for r in rows
    if eligible_basic(r) and r["family"] == "asym_T3" and int(r["layer_count"]) <= 17
]
t3_top = sorted(t3_top, key=lambda r: r["fab_score"], reverse=True)[:15]

summary = {
    "stage": "MDC1B_local_integer_refine",
    "direction": "emission_side_GaN_to_reverse_layers_to_Air",
    "candidate_count": len(rows),
    "note": "TMM local integer-nm refine only. No FMM, no FDTD, no FSP. FMM/RCWA is reserved for mid-fidelity parity after this shortlist.",
    "fab_top20": fab_top,
    "perf_top20": perf_top,
    "t3_top15": t3_top,
    "outputs": {
        "metrics_csv": str(metrics_csv),
        "summary_json": str(OUT / "mdc1b_local_integer_refine_summary.json"),
        "report_md": str(OUT / "mdc1b_local_integer_refine_report.md"),
    },
}
(OUT / "mdc1b_local_integer_refine_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

def line(r):
    return (
        f"{r['candidate_id']} fam={r['family']} topo={r['topology']} "
        f"N={r['N']} Nair={r['N_air']} Nled={r['N_led']} "
        f"L={r['L_SiO2_nm']} H={r['H_TiO2_nm']} C={r['C_defect_SiO2_nm']} "
        f"layers={r['layer_count']} peak={float(r['peak_nm_0deg']):.2f} "
        f"Tpeak={float(r['T_peak_0deg']):.4f} FWHM={float(r['FWHM_nm_0deg']):.2f} "
        f"T450_0={float(r['Tavg_450_0deg']):.4f} T450_20={float(r['Tavg_450_20deg']):.4f} "
        f"ratio={float(r['normal_to_40_60_ratio']):.2f} "
        f"robust_peak_span={float(r['robust_peak_span_nm']):.2f} "
        f"robust_T4500_min={float(r['robust_T4500_min']):.4f} "
        f"fab_score={float(r['fab_score']):.4g} perf_score={float(r['perf_score']):.4g}"
    )

md = []
md.append("# MDC1B local integer-nm refine\n")
md.append("## Scope\n")
md.append("Pure TMM local integer-nm refinement around MDC1A anchors. No FMM, no Lumerical, no FDTD, no FSP.\n")
md.append("FMM/RCWA is reserved for mid-fidelity parity after choosing 2-3 local-refined candidates.\n")
md.append("## Fabrication-friendly N=3 top candidates\n")
for r in fab_top[:10]:
    md.append("- " + line(r))
md.append("\n## Performance N=4 top candidates\n")
for r in perf_top[:10]:
    md.append("- " + line(r))
md.append("\n## Asymmetric T3 probe candidates\n")
for r in t3_top[:10]:
    md.append("- " + line(r))
md.append("\n## Current intended decision\n")
md.append("- Pick one N=3 13-layer candidate as `MDC-Baseline-Fab`.")
md.append("- Pick one N=4 17-layer candidate as `MDC-Performance`.")
md.append("- Keep `MDC-A0-INT` as rounded quarter-wave reference.")
md.append("- Do not freeze from TMM alone; next should be stackrt/RCWA/FMM small-point parity before FDTD.")
(OUT / "mdc1b_local_integer_refine_report.md").write_text("\n".join(md), encoding="utf-8")

print("MDC1B local integer refine complete")
print(f"candidate_count={len(rows)}")
print(f"metrics_csv={metrics_csv}")
print(f"summary_json={OUT / 'mdc1b_local_integer_refine_summary.json'}")
print(f"report_md={OUT / 'mdc1b_local_integer_refine_report.md'}")
print("")
print("FAB top10:")
for r in fab_top[:10]:
    print("  " + line(r))
print("")
print("PERF top10:")
for r in perf_top[:10]:
    print("  " + line(r))
print("")
print("T3 top10:")
for r in t3_top[:10]:
    print("  " + line(r))

from pathlib import Path
import math, cmath, csv, json

OUT = Path("outputs") / "mdc1a_integer_nm_defect_mdc_screen"
OUT.mkdir(parents=True, exist_ok=True)

NIDX = {"Air": 1.0, "SiO2": 1.426, "TiO2": 2.535, "GaN": 2.41}

LAMBDA0 = 450.0
D_L = 79   # SiO2 quarter-wave rounded to integer nm
D_H = 44   # TiO2 quarter-wave rounded to integer nm
D_C0 = 158 # SiO2 half-wave defect rounded to integer nm

LAMBDAS = [x * 0.5 for x in range(860, 941)]  # 430-470 nm
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

def tavg_emission(design_layers, wl, theta_air):
    layers = reverse_layers(design_layers)
    theta_gan = theta_gan_from_air(theta_air)
    Ts, _ = tmm(NIDX["GaN"], NIDX["Air"], layers, wl, theta_gan, "s")
    Tp, _ = tmm(NIDX["GaN"], NIDX["Air"], layers, wl, theta_gan, "p")
    return 0.5 * (Ts + Tp), Ts, Tp

def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def closest_lambda_value(design_layers, wl_target, theta_air):
    wl = min(LAMBDAS, key=lambda x: abs(x - wl_target))
    return tavg_emission(design_layers, wl, theta_air)[0]

def spectrum_0deg(design_layers):
    return [(wl, tavg_emission(design_layers, wl, 0)[0]) for wl in LAMBDAS]

def fwhm(spec):
    peak_wl, peak_T = max(spec, key=lambda x: x[1])
    half = peak_T / 2
    above = [wl for wl, val in spec if val >= half]
    if not above:
        return peak_wl, peak_T, None
    return peak_wl, peak_T, max(above) - min(above)

def mean_band(design_layers, wl_min, wl_max, theta_list):
    vals = []
    for wl in LAMBDAS:
        if wl_min <= wl <= wl_max:
            for th in theta_list:
                vals.append(tavg_emission(design_layers, wl, th)[0])
    return mean(vals)

def mean_450_angle_band(design_layers, theta_min, theta_max):
    vals = []
    for th in THETAS_AIR:
        if theta_min <= th <= theta_max:
            vals.append(closest_lambda_value(design_layers, 450, th))
    return mean(vals)

def robust_probe(design_layers):
    # light fabrication sensitivity probe only: defect +/-2 nm and all films +/-2 nm.
    variants = []
    variants.append(design_layers)
    variants.append([(m, d+2 if m in ("SiO2","TiO2") else d) for m,d in design_layers])
    variants.append([(m, max(1, d-2) if m in ("SiO2","TiO2") else d) for m,d in design_layers])
    # defect-only +/-2, using central largest SiO2 as simple marker
    if design_layers:
        max_sio2 = max((d for m,d in design_layers if m == "SiO2"), default=None)
        for delta in [-2, 2]:
            v = []
            used = False
            for m,d in design_layers:
                if (not used) and m == "SiO2" and d == max_sio2:
                    v.append((m, max(1, d + delta)))
                    used = True
                else:
                    v.append((m,d))
            variants.append(v)
    peaks, tpeaks = [], []
    for v in variants:
        p, t, _ = fwhm(spectrum_0deg(v))
        peaks.append(p); tpeaks.append(t)
    return max(peaks) - min(peaks), min(tpeaks)

def candidate_layers(topology, Npair=None, N_air=None, N_led=None, L=D_L, H=D_H, C=D_C0):
    if topology == "T1":
        return LH(Npair, L, H) + [("SiO2", C)] + HL(Npair, L, H)
    if topology == "T2":
        return HL(Npair, L, H) + [("SiO2", C)] + LH(Npair, L, H)
    if topology == "T3":
        return LH(N_air, L, H) + [("SiO2", C)] + HL(N_led, L, H)
    raise ValueError(topology)

candidates = []

# Main integer nm search. Keep modest layer counts first.
L_CHOICES = [77, 79, 81]
H_CHOICES = [43, 44, 45]
C_CHOICES = list(range(130, 191, 5))
N_CHOICES = [2, 3, 4]
ASYM_CHOICES = [(2,2), (2,3), (3,2), (3,3), (3,4), (4,3), (4,4)]

cid_num = 0
for topology in ["T1", "T2"]:
    for Npair in N_CHOICES:
        for L in L_CHOICES:
            for H in H_CHOICES:
                for C in C_CHOICES:
                    cid_num += 1
                    layers = candidate_layers(topology, Npair=Npair, L=L, H=H, C=C)
                    candidates.append((f"MDC1A_{cid_num:04d}", topology, Npair, "", "", L, H, C, layers))

for N_air, N_led in ASYM_CHOICES:
    for C in C_CHOICES:
        cid_num += 1
        layers = candidate_layers("T3", N_air=N_air, N_led=N_led, L=D_L, H=D_H, C=C)
        candidates.append((f"MDC1A_{cid_num:04d}", "T3", "", N_air, N_led, D_L, D_H, C, layers))

# Include exact rounded baseline explicitly.
layers_a0 = candidate_layers("T1", Npair=3, L=D_L, H=D_H, C=D_C0)
candidates.append(("MDC-A0-INT", "T1", 3, "", "", D_L, D_H, D_C0, layers_a0))

rows = []
grid_rows = []

for cid, topo, Npair, Nair, Nled, L, H, C, layers in candidates:
    spec = spectrum_0deg(layers)
    peak_nm, T_peak, fw = fwhm(spec)
    fw_val = fw if fw is not None else 999.0

    T450_0 = closest_lambda_value(layers, 450, 0)
    T450_10 = closest_lambda_value(layers, 450, 10)
    T450_20 = closest_lambda_value(layers, 450, 20)

    m448_452_0 = mean_band(layers, 448, 452, [0])
    m448_452_0_10 = mean_band(layers, 448, 452, [0,5,10])
    m430_445_0 = mean_band(layers, 430, 445, [0])
    m455_470_0 = mean_band(layers, 455, 470, [0])

    m450_0_10 = mean_450_angle_band(layers, 0, 10)
    m450_20_40 = mean_450_angle_band(layers, 20, 40)
    m450_40_60 = mean_450_angle_band(layers, 40, 60)
    normal_ratio = m450_0_10 / (m450_40_60 + 1e-12)

    _, Ts0, Tp0 = tavg_emission(layers, 450, 0)
    sp_imb = abs(Ts0 - Tp0) / (0.5*(Ts0+Tp0) + 1e-12)

    layer_count = len(layers)
    total_thickness = sum(d for _, d in layers)

    # simple robust probe only for candidates that are not obviously dead
    if abs(peak_nm - 450) <= 8 and T_peak >= 0.05:
        robust_span, robust_tmin = robust_probe(layers)
    else:
        robust_span, robust_tmin = 999.0, 0.0

    peak_penalty = 1 + abs(peak_nm - 450) / 3
    fwhm_penalty = 1 + max(fw_val - 18, 0) / 18
    layer_penalty = 1 + max(layer_count - 9, 0) * 0.035
    lowT_penalty = 1 if T_peak >= 0.08 else 3
    leakage_reward = normal_ratio
    score = (m448_452_0_10 * leakage_reward) / (peak_penalty * fwhm_penalty * layer_penalty * lowT_penalty)

    rows.append({
        "candidate_id": cid,
        "topology": topo,
        "N": Npair,
        "N_air": Nair,
        "N_led": Nled,
        "L_SiO2_nm": L,
        "H_TiO2_nm": H,
        "C_defect_SiO2_nm": C,
        "layer_count": layer_count,
        "total_thickness_nm": total_thickness,
        "peak_nm_0deg": peak_nm,
        "T_peak_0deg": T_peak,
        "FWHM_nm_0deg": fw_val,
        "Tavg_450_0deg": T450_0,
        "Tavg_450_10deg": T450_10,
        "Tavg_450_20deg": T450_20,
        "mean_Tavg_448_452_0deg": m448_452_0,
        "mean_Tavg_448_452_0_10deg": m448_452_0_10,
        "mean_Tavg_430_445_0deg": m430_445_0,
        "mean_Tavg_455_470_0deg": m455_470_0,
        "mean_Tavg_450_0_10deg": m450_0_10,
        "mean_Tavg_450_20_40deg": m450_20_40,
        "mean_Tavg_450_40_60deg": m450_40_60,
        "normal_to_40_60_ratio": normal_ratio,
        "sp_imbalance_450_0deg": sp_imb,
        "robust_probe_peak_span_nm": robust_span,
        "robust_probe_min_T_peak": robust_tmin,
        "score": score,
        "design_layers": " / ".join([f"{m}:{d}nm" for m,d in layers]),
        "emission_layers": " / ".join([f"{m}:{d}nm" for m,d in reverse_layers(layers)]),
    })

    # keep grid only for baseline and top-like near candidates to avoid huge file
    if cid == "MDC-A0-INT":
        for wl in LAMBDAS:
            for th in THETAS_AIR:
                Tavg, Ts, Tp = tavg_emission(layers, wl, th)
                grid_rows.append({
                    "candidate_id": cid, "wavelength_nm": wl, "theta_air_deg": th,
                    "Tavg": Tavg, "Ts": Ts, "Tp": Tp
                })

rows_sorted = sorted(rows, key=lambda r: r["score"], reverse=True)

metrics_csv = OUT / "mdc1a_integer_candidate_metrics.csv"
with metrics_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows_sorted[0].keys()))
    w.writeheader(); w.writerows(rows_sorted)

grid_csv = OUT / "mdc1a_integer_a0_grid.csv"
with grid_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(grid_rows[0].keys()))
    w.writeheader(); w.writerows(grid_rows)

top = rows_sorted[:20]
summary = {
    "stage": "MDC1A_integer_nm_defect_MDC_screen",
    "integer_nm_policy": True,
    "default_direction": "emission_side_GaN_to_reverse_layers_to_Air",
    "fixed_integer_baseline_nm": {"SiO2_L": D_L, "TiO2_H": D_H, "SiO2_defect_C0": D_C0},
    "candidate_count": len(rows),
    "ranking_note": "score favors 448-452 nm small-angle throughput, 450 nm large-angle suppression, peak near 450, lower layer count, non-collapsed Tpeak. Robust probe is only a light diagnostic.",
    "outputs": {
        "metrics_csv": str(metrics_csv),
        "a0_grid_csv": str(grid_csv),
        "summary_json": str(OUT / "mdc1a_integer_summary.json"),
        "report_md": str(OUT / "mdc1a_integer_report.md"),
    },
    "top20": top,
}
(OUT / "mdc1a_integer_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

md = []
md.append("# MDC1A integer-nm defect-MDC screen\n")
md.append("## Scope\n")
md.append("This stage screens center-defect multilayer MDC candidates using integer-nm manufacturable thicknesses only. No FSP, no Lumerical, no FDTD, no RCLED continuation.\n")
md.append("Default physical direction is emission side: `GaN -> reverse(film stack) -> Air`.\n")
md.append("## Integer baseline\n")
md.append(f"- SiO2 L = {D_L} nm\n- TiO2 H = {D_H} nm\n- SiO2 defect C0 = {D_C0} nm\n")
md.append("Layer count is included as a penalty because thickness error accumulation worsens with more layers. Deep robustness optimization is left to later ML/FDTD stages.\n")
md.append("## Top 10 candidates\n")
md.append("| rank | id | topo | N | Nair | Nled | L | H | C | layers | peak | Tpeak | FWHM | T450_0 | T450_20 | ratio | robust_span | score |")
md.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for i, r in enumerate(top[:10], 1):
    md.append(f"| {i} | {r['candidate_id']} | {r['topology']} | {r['N']} | {r['N_air']} | {r['N_led']} | {r['L_SiO2_nm']} | {r['H_TiO2_nm']} | {r['C_defect_SiO2_nm']} | {r['layer_count']} | {r['peak_nm_0deg']:.1f} | {r['T_peak_0deg']:.4f} | {r['FWHM_nm_0deg']:.1f} | {r['Tavg_450_0deg']:.4f} | {r['Tavg_450_20deg']:.4f} | {r['normal_to_40_60_ratio']:.2f} | {r['robust_probe_peak_span_nm']:.1f} | {r['score']:.4g} |")
md.append("\n## Recommended manual check\n")
md.append("Pick candidates with integer thickness, central SiO2 defect, moderate layer count, peak near 450 nm, non-collapsed Tpeak, and lower 40-60 deg leakage. Do not freeze from TMM alone.\n")
md.append("\n## Top candidate layer sequence\n")
best = top[0]
md.append(f"Best by current score: `{best['candidate_id']}`\n")
md.append("Design-side Air -> GaN:\n")
md.append("```text\n" + best["design_layers"] + "\n```\n")
md.append("Emission-side GaN -> Air:\n")
md.append("```text\n" + best["emission_layers"] + "\n```\n")
(OUT / "mdc1a_integer_report.md").write_text("\n".join(md), encoding="utf-8")

print("MDC1A integer screen complete")
print("candidate_count=", len(rows))
print("outputs=", OUT)
print("top10:")
for i, r in enumerate(top[:10], 1):
    print(f"{i:02d} {r['candidate_id']} topo={r['topology']} N={r['N']} Nair={r['N_air']} Nled={r['N_led']} L={r['L_SiO2_nm']} H={r['H_TiO2_nm']} C={r['C_defect_SiO2_nm']} layers={r['layer_count']} peak={r['peak_nm_0deg']:.1f} Tpeak={r['T_peak_0deg']:.4f} FWHM={r['FWHM_nm_0deg']:.1f} T450_0={r['Tavg_450_0deg']:.4f} T450_20={r['Tavg_450_20deg']:.4f} ratio={r['normal_to_40_60_ratio']:.2f} robust_span={r['robust_probe_peak_span_nm']:.1f} score={r['score']:.4g}")

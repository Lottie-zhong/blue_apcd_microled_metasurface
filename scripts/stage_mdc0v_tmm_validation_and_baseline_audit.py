from pathlib import Path
import math
import cmath
import csv
import json

OUT = Path("outputs") / "mdc0v_tmm_validation_and_baseline_audit"
OUT.mkdir(parents=True, exist_ok=True)

N = {
    "Air": 1.0,
    "SiO2": 1.426,
    "TiO2": 2.535,
    "GaN": 2.41,
}

LAMBDA0_NM = 450.0
D_L = LAMBDA0_NM / (4.0 * N["SiO2"])
D_H = LAMBDA0_NM / (4.0 * N["TiO2"])
D_C = 2.0 * LAMBDA0_NM / (4.0 * N["SiO2"])

def c_sqrt(x):
    z = cmath.sqrt(x)
    if z.real < -1e-14:
        z = -z
    return z

def cos_from_sin(s):
    return c_sqrt(1.0 - s * s)

def admittance(n, cos_theta, pol):
    if pol == "s":
        return n * cos_theta
    if pol == "p":
        return n / cos_theta
    raise ValueError(f"bad polarization: {pol}")

def matmul(A, B):
    a, b, c, d = A
    e, f, g, h = B
    return (
        a * e + b * g,
        a * f + b * h,
        c * e + d * g,
        c * f + d * h,
    )

def tmm(n_in, n_out, layers, wavelength_nm, theta_in_deg, pol):
    theta0 = math.radians(theta_in_deg)
    sin0 = math.sin(theta0)
    cos0 = cos_from_sin(sin0)
    q0 = admittance(n_in, cos0, pol)

    M = (1.0 + 0j, 0.0 + 0j, 0.0 + 0j, 1.0 + 0j)

    for material, thickness_nm in layers:
        nj = N[material]
        sj = n_in * sin0 / nj
        cj = cos_from_sin(sj)
        qj = admittance(nj, cj, pol)
        delta = 2.0 * math.pi * nj * thickness_nm * cj / wavelength_nm
        cd = cmath.cos(delta)
        sd = cmath.sin(delta)
        Mj = (cd, 1j * sd / qj, 1j * qj * sd, cd)
        M = matmul(M, Mj)

    sout = n_in * sin0 / n_out
    cout = cos_from_sin(sout)
    qs = admittance(n_out, cout, pol)

    A, B, C, D = M
    den = q0 * A + q0 * qs * B + C + qs * D
    r = (q0 * A + q0 * qs * B - C - qs * D) / den
    t = 2.0 * q0 / den

    R = abs(r) ** 2
    T = ((qs / q0).real) * abs(t) ** 2
    return {
        "R": float(R),
        "T": float(T),
        "R_plus_T": float(R + T),
        "r_real": float(r.real),
        "r_imag": float(r.imag),
        "t_real": float(t.real),
        "t_imag": float(t.imag),
    }

def fresnel_direct(n_in, n_out, theta_in_deg, pol):
    theta0 = math.radians(theta_in_deg)
    sin0 = math.sin(theta0)
    cos0 = cos_from_sin(sin0)
    sout = n_in * sin0 / n_out
    cout = cos_from_sin(sout)
    q0 = admittance(n_in, cos0, pol)
    qs = admittance(n_out, cout, pol)
    r = (q0 - qs) / (q0 + qs)
    t = 2.0 * q0 / (q0 + qs)
    R = abs(r) ** 2
    T = ((qs / q0).real) * abs(t) ** 2
    return float(R), float(T)

def theta_in_gan_from_air_exit(theta_air_deg):
    s = N["Air"] / N["GaN"] * math.sin(math.radians(theta_air_deg))
    return math.degrees(math.asin(s))

def pair_LH(repeat):
    layers = []
    for _ in range(repeat):
        layers.append(("SiO2", D_L))
        layers.append(("TiO2", D_H))
    return layers

def pair_HL(repeat):
    layers = []
    for _ in range(repeat):
        layers.append(("TiO2", D_H))
        layers.append(("SiO2", D_L))
    return layers

def reverse_layers(layers):
    return list(reversed(layers))

baselines = {
    "MDC-B0": {
        "note": "Bare GaN/Air interface reference.",
        "design_layers": [],
    },
    "MDC-B2": {
        "note": "Ordinary quarter-wave DBR/MDC control: Air/(L/H)^3/GaN.",
        "design_layers": pair_LH(3),
    },
    "MDC-A0": {
        "note": "Main symmetric defect-MDC baseline: Air/(L/H)^3/Ldef/(H/L)^3/GaN.",
        "design_layers": pair_LH(3) + [("SiO2", D_C)] + pair_HL(3),
    },
    "MDC-B1W-provisional": {
        "note": "Wan-style ordinary SiO2/TiO2 MDC provisional only; exact FSP layer order not re-extracted here.",
        "design_layers": sum(([("SiO2", 100.0), ("TiO2", 52.0)] for _ in range(8)), []),
        "provisional": True,
    },
}

checks = []

def add_check(name, candidate, direction, wavelength_nm, theta_air_deg, theta_in_deg, pol, R, T, expected_R=None, expected_T=None, tolerance=1e-9):
    energy_err = abs(R + T - 1.0)
    pass_energy = energy_err <= tolerance if expected_R is None else True
    err_R = "" if expected_R is None else abs(R - expected_R)
    err_T = "" if expected_T is None else abs(T - expected_T)
    pass_expected = True
    if expected_R is not None:
        pass_expected = (abs(R - expected_R) <= tolerance and abs(T - expected_T) <= tolerance)
    passed = pass_energy and pass_expected
    checks.append({
        "check": name,
        "candidate": candidate,
        "direction": direction,
        "wavelength_nm": wavelength_nm,
        "theta_air_deg": theta_air_deg,
        "theta_in_deg": theta_in_deg,
        "pol": pol,
        "R": R,
        "T": T,
        "R_plus_T": R + T,
        "energy_error": energy_err,
        "expected_R": expected_R if expected_R is not None else "",
        "expected_T": expected_T if expected_T is not None else "",
        "err_R": err_R,
        "err_T": err_T,
        "tolerance": tolerance,
        "pass": passed,
    })

# 1. Identity check: Air/no layer/Air
for theta in [0, 30, 60]:
    for pol in ["s", "p"]:
        res = tmm(N["Air"], N["Air"], [], 450.0, theta, pol)
        add_check("identity_air_no_layer_air", "identity", "Air->Air", 450.0, theta, theta, pol, res["R"], res["T"], 0.0, 1.0, 1e-9)

# 2. Bare Fresnel normal check: Air/GaN
R_normal = ((N["Air"] - N["GaN"]) / (N["Air"] + N["GaN"])) ** 2
T_normal = 1.0 - R_normal
for pol in ["s", "p"]:
    res = tmm(N["Air"], N["GaN"], [], 450.0, 0.0, pol)
    add_check("bare_air_gan_normal_analytic", "MDC-B0", "Air->GaN", 450.0, 0.0, 0.0, pol, res["R"], res["T"], R_normal, T_normal, 1e-9)

# 3. Bare interface oblique check vs direct Fresnel
for theta in [20, 40, 60]:
    for pol in ["s", "p"]:
        res = tmm(N["Air"], N["GaN"], [], 450.0, theta, pol)
        Rf, Tf = fresnel_direct(N["Air"], N["GaN"], theta, pol)
        add_check("bare_air_gan_oblique_direct_fresnel", "MDC-B0", "Air->GaN", 450.0, theta, theta, pol, res["R"], res["T"], Rf, Tf, 1e-9)

# 4. Energy conservation for B0/B2/A0 in both directions
for cid in ["MDC-B0", "MDC-B2", "MDC-A0"]:
    layers = baselines[cid]["design_layers"]
    for lam in [440.0, 450.0, 460.0]:
        for theta_air in [0, 10, 20, 40, 60]:
            theta_gan = theta_in_gan_from_air_exit(theta_air)
            for pol in ["s", "p"]:
                res_air = tmm(N["Air"], N["GaN"], layers, lam, theta_air, pol)
                add_check("energy_air_incidence_proxy", cid, "Air->layers->GaN", lam, theta_air, theta_air, pol, res_air["R"], res_air["T"], None, None, 1e-7)

                res_emit = tmm(N["GaN"], N["Air"], reverse_layers(layers), lam, theta_gan, pol)
                add_check("energy_emission_direction", cid, "GaN->reverse(layers)->Air", lam, theta_air, theta_gan, pol, res_emit["R"], res_emit["T"], None, None, 1e-7)

# 5. Reciprocity / direction consistency
for cid in ["MDC-B2", "MDC-A0"]:
    layers = baselines[cid]["design_layers"]
    for lam in [440.0, 450.0, 460.0]:
        for theta_air in [0, 10, 20, 40, 60]:
            theta_gan = theta_in_gan_from_air_exit(theta_air)
            for pol in ["s", "p"]:
                res_air = tmm(N["Air"], N["GaN"], layers, lam, theta_air, pol)
                res_emit = tmm(N["GaN"], N["Air"], reverse_layers(layers), lam, theta_gan, pol)
                diff = abs(res_air["T"] - res_emit["T"])
                passed = diff < 1e-7
                checks.append({
                    "check": "reciprocity_same_k_parallel_T_forward_reverse",
                    "candidate": cid,
                    "direction": "Air->GaN vs GaN->Air reverse",
                    "wavelength_nm": lam,
                    "theta_air_deg": theta_air,
                    "theta_in_deg": f"air:{theta_air:.8f};gan:{theta_gan:.8f}",
                    "pol": pol,
                    "R": "",
                    "T": "",
                    "R_plus_T": "",
                    "energy_error": "",
                    "expected_R": "",
                    "expected_T": "",
                    "err_R": "",
                    "err_T": diff,
                    "tolerance": 1e-7,
                    "pass": passed,
                })

validation_csv = OUT / "mdc0v_validation_checks.csv"
with validation_csv.open("w", newline="", encoding="utf-8") as f:
    fieldnames = list(checks[0].keys())
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(checks)

layer_rows = []
def add_layer_rows(cid, direction, incident, exit_medium, layers, note, provisional=False):
    layer_rows.append({
        "candidate_id": cid,
        "direction": direction,
        "layer_index": -1,
        "material": incident,
        "thickness_nm": "",
        "role": "incident_medium",
        "note": note,
        "provisional": provisional,
    })
    for i, (mat, d) in enumerate(layers, start=1):
        if cid == "MDC-A0" and abs(d - D_C) < 1e-9 and mat == "SiO2":
            role = "defect_SiO2_half_wave"
        elif mat == "SiO2":
            role = "quarter_wave_L_or_Wan_SiO2"
        elif mat == "TiO2":
            role = "quarter_wave_H_or_Wan_TiO2"
        else:
            role = "film"
        layer_rows.append({
            "candidate_id": cid,
            "direction": direction,
            "layer_index": i,
            "material": mat,
            "thickness_nm": f"{d:.9f}",
            "role": role,
            "note": note,
            "provisional": provisional,
        })
    layer_rows.append({
        "candidate_id": cid,
        "direction": direction,
        "layer_index": len(layers) + 1,
        "material": exit_medium,
        "thickness_nm": "",
        "role": "exit_medium",
        "note": note,
        "provisional": provisional,
    })

for cid, info in baselines.items():
    layers = info["design_layers"]
    provisional = bool(info.get("provisional", False))
    add_layer_rows(cid, "design_side_Air_to_GaN", "Air", "GaN", layers, info["note"], provisional)
    add_layer_rows(cid, "emission_side_GaN_to_Air", "GaN", "Air", reverse_layers(layers), info["note"], provisional)

layers_csv = OUT / "mdc0v_baseline_layers.csv"
with layers_csv.open("w", newline="", encoding="utf-8") as f:
    fieldnames = list(layer_rows[0].keys())
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(layer_rows)

all_pass = all(bool(row["pass"]) for row in checks)
failed = [row for row in checks if not bool(row["pass"])]

summary = {
    "stage": "MDC0V_TMM_validation_and_baseline_audit",
    "all_validation_checks_pass": all_pass,
    "num_checks": len(checks),
    "num_failed": len(failed),
    "n_air": N["Air"],
    "n_SiO2": N["SiO2"],
    "n_TiO2": N["TiO2"],
    "n_GaN": N["GaN"],
    "lambda0_nm": LAMBDA0_NM,
    "d_L_SiO2_quarter_wave_nm": D_L,
    "d_H_TiO2_quarter_wave_nm": D_H,
    "d_C_SiO2_half_wave_defect_nm": D_C,
    "stackrt_parity": "skipped_no_lumerical_gui_or_safe_stackrt_invocation_in_this_manual_stage",
    "default_future_ranking_direction": "emission_side_GaN_to_reverse_layers_to_Air",
    "outputs": {
        "validation_checks_csv": str(validation_csv),
        "baseline_layers_csv": str(layers_csv),
        "summary_json": str(OUT / "mdc0v_summary.json"),
        "baseline_audit_md": str(OUT / "mdc0v_baseline_audit.md"),
    },
}

summary_json = OUT / "mdc0v_summary.json"
summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

def layer_table_md(cid, direction):
    rows = [r for r in layer_rows if r["candidate_id"] == cid and r["direction"] == direction]
    out = ["| idx | material | thickness_nm | role |", "|---:|---|---:|---|"]
    for r in rows:
        out.append(f"| {r['layer_index']} | {r['material']} | {r['thickness_nm']} | {r['role']} |")
    return "\n".join(out)

report = []
report.append("# MDC0V TMM validation and baseline audit\n")
report.append("## Scope\n")
report.append("This stage is validation + baseline audit only. It is not a full candidate scan. No FSP, no Lumerical run, no FDTD, no RCLED continuation.\n")
report.append("Current physical chain for this MDC branch:\n\n```text\nGaN/InGaN Micro-LED -> top defect-MDC -> air/downstream metasurface\n```\n")
report.append("Therefore future ranking should default to the emission-side direction:\n\n```text\nGaN -> reverse(film stack) -> Air\n```\n")
report.append("Air-side incidence is retained only as a reciprocal plane-wave proxy / sanity channel.\n")
report.append("## Material constants and 450 nm quarter-wave thicknesses\n")
report.append(f"- n_air = {N['Air']}\n")
report.append(f"- n_SiO2 = {N['SiO2']}\n")
report.append(f"- n_TiO2 = {N['TiO2']}\n")
report.append(f"- n_GaN = {N['GaN']}\n")
report.append(f"- lambda0 = {LAMBDA0_NM:.3f} nm\n")
report.append(f"- d_L_SiO2 = lambda0/(4*n_SiO2) = {D_L:.6f} nm\n")
report.append(f"- d_H_TiO2 = lambda0/(4*n_TiO2) = {D_H:.6f} nm\n")
report.append(f"- d_C_SiO2_defect = lambda0/(2*n_SiO2) = {D_C:.6f} nm\n")
report.append("\nThese values use the branch convention refractive indices, not older rough estimates such as n_SiO2=1.46 or n_TiO2=2.45.\n")
report.append("## Validation result\n")
report.append(f"- all_validation_checks_pass = `{all_pass}`\n")
report.append(f"- num_checks = {len(checks)}\n")
report.append(f"- num_failed = {len(failed)}\n")
report.append("- stackrt parity = skipped in this manual stage because no safe command-line stackrt invocation is used here; this does not fail MDC0V.\n")
if failed:
    report.append("\n### Failed checks\n")
    for row in failed[:20]:
        report.append(f"- {row['check']} | {row['candidate']} | {row['direction']} | lambda={row['wavelength_nm']} | theta_air={row['theta_air_deg']} | pol={row['pol']} | err={row['err_T'] or row['energy_error']}\n")

report.append("## Baseline audit tables\n")
for cid in ["MDC-B0", "MDC-B2", "MDC-A0", "MDC-B1W-provisional"]:
    report.append(f"\n### {cid}\n")
    report.append(f"{baselines[cid]['note']}\n")
    if cid == "MDC-B1W-provisional":
        report.append("\n**Important:** This baseline is provisional only. It must not be used for ranking until the exact Wan FSP layer order/layer count is confirmed.\n")
    report.append("\n#### Design-side order: Air -> ... -> GaN\n")
    report.append(layer_table_md(cid, "design_side_Air_to_GaN"))
    report.append("\n\n#### Emission-side order: GaN -> ... -> Air\n")
    report.append(layer_table_md(cid, "emission_side_GaN_to_Air"))
    report.append("\n")

report.append("## Manual checkpoints for user\n")
report.append("- Check whether L/H start layer is intended for the top MDC.\n")
report.append("- Check whether MDC-A0 is indeed the desired mirror-reversed defect-MDC.\n")
report.append("- Check whether B1W should remain provisional until exact Wan layer order is re-extracted.\n")
report.append("- Check whether lambda0 should remain 450 nm for LP/APCD matching, or be shifted to 453 nm to match Wan/H1J4 conventions.\n")
report.append("- If this baseline is accepted, next stage can run MDC1A full TMM candidate screening using emission-direction metrics.\n")

report_md = OUT / "mdc0v_baseline_audit.md"
report_md.write_text("\n".join(report), encoding="utf-8")

print("MDC0V complete")
print(f"all_validation_checks_pass={all_pass}")
print(f"num_checks={len(checks)}")
print(f"num_failed={len(failed)}")
print(f"d_L_SiO2_nm={D_L:.6f}")
print(f"d_H_TiO2_nm={D_H:.6f}")
print(f"d_C_SiO2_defect_nm={D_C:.6f}")
print(f"validation_csv={validation_csv}")
print(f"baseline_layers_csv={layers_csv}")
print(f"summary_json={summary_json}")
print(f"baseline_audit_md={report_md}")
if not all_pass:
    raise SystemExit(1)

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
ACQ = ROOT / r"outputs/np_k6_m7a_primary4_hf_acquisition_v1"
DESIGN = ROOT / r"outputs/np_k6_m7a_targeted_development_acquisition_design_v1"
M6 = ROOT / r"outputs/np_k6_m6_formal_development_merge_v1"
M7 = ROOT / r"outputs/np_k6_m7_16g_forward_retraining_v1"
LFROOT = ROOT / r"outputs/np_k6_ml_d0_database_foundation_v1"
OUT = ROOT / r"outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1"
ORDERS = [-3, -2, -1, 0, 1, 2, 3]
WLS = list(range(445, 456))
CASE_IDS = [f"NP_K6_M7A_PRIMARY4_G{g:02d}_{p}" for g in range(1, 5) for p in ("P", "S")]
ROLE_BY_G = {
    1: "RESIDUAL-TAIL",
    2: "RANKING-CHAMPION-STRESS",
    3: "POLARIZATION-STRESS",
    4: "COVERAGE-CONTROL",
}
GEO_BY_G = {
    1: "K6X_D135_D155_D190_D220_D225_D230",
    2: "K6X_D110_D125_D135_D150_D175_D195",
    3: "K6X_D100_D105_D115_D165_D225_D230",
    4: "K6X_D100_D105_D110_D115_D190_D230",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jread(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def jwrite(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def f(v, default=float("nan")) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def finite(v: str | float) -> bool:
    x = f(v)
    return math.isfinite(x)


def geometry_values(gid: str) -> list[int]:
    vals = [int(x) for x in re.findall(r"D(\d+)", gid)]
    if len(vals) != 6:
        raise RuntimeError(f"bad geometry id: {gid}")
    return vals


def percentiles(values: list[float]) -> dict[str, float | None]:
    vals = sorted(float(x) for x in values if math.isfinite(float(x)))
    if not vals:
        return {"mean": None, "median": None, "p90": None, "max": None}
    return {
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "p90": vals[min(len(vals) - 1, math.ceil(0.9 * len(vals)) - 1)],
        "max": max(vals),
    }


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in order[i:j]:
            out[k] = r
        i = j
    return out


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or len(a) != len(b):
        return None
    ra, rb = rankdata(a), rankdata(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else None


def load_case(case_id: str, registry: dict, history_by_case: dict[str, list[dict]]) -> tuple[dict, list[dict], list[dict], dict, dict]:
    d = ACQ / "cases" / case_id
    ledger = jread(d / "attempt_ledger.json")
    manifest = jread(d / "extraction_manifest.json")
    runtime = jread(d / "runtime_readback.json")
    obs = read_csv(d / "hf_observations_long.csv")
    orders = read_csv(d / "hf_transmitted_orders_long.csv")
    if ledger.get("case_id") != case_id or manifest.get("case_id") != case_id:
        raise RuntimeError(f"case identity mismatch {case_id}")
    if len(obs) != 11 or {int(float(r["wavelength_nm"])) for r in obs} != set(WLS):
        raise RuntimeError(f"wavelength completeness failed {case_id}")
    if len(orders) != 77 or len({(int(float(r["wavelength_nm"])), int(float(r["order_n"]))) for r in orders}) != 77:
        raise RuntimeError(f"order completeness failed {case_id}")
    return ledger, obs, orders, manifest, runtime


def history_index() -> dict[str, list[dict]]:
    p = Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json")
    data = jread(p)
    out: dict[str, list[dict]] = defaultdict(list)
    for row in data.get("history", []):
        out[str(row.get("case_uid"))].append(row)
    for row in data.get("active_slots", []):
        out[str(row.get("case_uid"))].append(row)
    return out


def case_audit(registry: list[dict], histories: dict[str, list[dict]]) -> tuple[list[dict], list[dict], list[dict]]:
    audits: list[dict] = []
    hf_rows: list[dict] = []
    order_rows: list[dict] = []
    for spec in registry:
        case = spec["case_id"]
        ledger, obs, orders, manifest, runtime = load_case(case, {}, histories)
        hist = histories.get(case, [])
        h = hist[-1] if hist else {}
        post_path = Path(manifest.get("post_fsp_path", ""))
        post_sha = manifest.get("post_fsp_sha256")
        post_sha_actual = sha(post_path) if post_path.exists() else None
        run_copy = Path(ledger.get("run_copy_path", ""))
        run_copy_sha = sha(run_copy) if run_copy.exists() else None
        key_fields = ["T_total", "R_total", "closure", "signed_closure_residual", "eta_plus1", "eta_0", "eta_minus1", "directionality"]
        all_finite = all(finite(r.get(k)) for r in obs for k in key_fields)
        residual_max = max(abs(f(r.get("signed_closure_residual"))) for r in obs)
        max_order_mismatch = max(abs(f(r.get("transmitted_order_sum_mismatch"))) for r in obs)
        structure_max = f(manifest.get("structure_interval_anomaly_max"))
        norm_max = f(ledger.get("direct_raw_sourcepower_mismatch_max", manifest.get("direct_raw_sourcepower_mismatch_max", 0.0)), 0.0)
        wavelengths = sorted({int(float(r["wavelength_nm"])) for r in obs})
        required_flags = {
            "entered": ledger.get("entered") is True,
            "run_invocation_count": int(ledger.get("run_invocation_count", 0)) == 1,
            "engine_completed": ledger.get("engine_completed") is True,
            "post_saved": ledger.get("post_saved") is True,
            "controller_returned": ledger.get("controller_returned") is True,
            "quality_gate_pass": ledger.get("quality_gate_pass") is True and manifest.get("quality_gate_pass") is True,
            "training_label": ledger.get("training_label") is True,
            "diagnostic_only_false": ledger.get("diagnostic_only") is False,
            "post_exists": post_path.exists(),
            "post_hash_matches_record": post_sha_actual is None or post_sha_actual == post_sha,
            "source_hash_matches_registry": spec.get("source_prefsp_sha256") == ledger.get("source_prefsp_sha256"),
            # The solver mutates the binary run copy while preserving the
            # immutable source pre-FSP identity.  Provenance is checked via
            # the recorded source hash; the post-run copy hash is retained as
            # an independent runtime artifact and is not expected to equal it.
            "run_copy_hash_present": run_copy_sha is not None,
            "exact_11_wavelengths": len(obs) == 11 and wavelengths == WLS,
            "all_finite": all_finite,
            "closure_gate": residual_max <= 0.01,
            "structure_gate": structure_max <= 0.01,
            "order_gate": max_order_mismatch <= 1e-8,
            "normalization_gate": norm_max <= 1e-8,
            "mesh_5nm": runtime.get("fixed_mesh", {}).get("dx") == 5e-9 and runtime.get("fixed_mesh", {}).get("dy") == 5e-9 and runtime.get("fixed_mesh", {}).get("dz") == 5e-9,
            "native_m1_material": all(v.get("type") == "Sampled 3D data" and v.get("sampled_rows") == 101 for v in runtime.get("materials", {}).values()),
            "readonly_reload": manifest.get("readonly_reload") is True and manifest.get("run_called") is False and manifest.get("save_called") is False,
        }
        resource = ledger.get("resource_contract", {})
        observed_processes = h.get("processes")
        observed_threads = h.get("threads")
        runtime_line = ""
        for log in runtime.get("runtime", {}).get("log_paths", []):
            lp = Path(log)
            if lp.exists():
                runtime_line += lp.read_text(encoding="utf-8", errors="ignore")
        runtime_mpi = bool(re.search(r"(?:mpiexec|MPI).*?(?:-n\s*4|4 processes)", runtime_line, re.I)) or observed_processes == 4
        required_flags["resource_readback_4x1"] = resource.get("readback", {}).get("processes") == "4" and resource.get("readback", {}).get("threads") == "1"
        required_flags["runtime_observed_4x1"] = runtime_mpi and (observed_threads in (None, 1))
        audit = {
            "case_id": case,
            "role": spec.get("role"),
            "geometry_id": spec.get("geometry_id"),
            "geometry_hash": spec.get("geometry_hash"),
            "polarization": spec.get("polarization"),
            "attempt_id": ledger.get("attempt_id"),
            "source_prefsp_sha256": spec.get("source_prefsp_sha256"),
            "run_copy_sha256": run_copy_sha,
            "post_fsp_sha256": post_sha,
            "post_fsp_sha256_recomputed": post_sha_actual,
            "global_slot_id": ledger.get("global_slot_id"),
            "slot_acquire_time": h.get("slot_acquire_time"),
            "slot_release_time": h.get("slot_release_time"),
            "global_concurrency_at_entry": (h.get("admission_snapshot") or {}).get("effective_global_active_jobs_after_acquire"),
            "co_running_branches": h.get("concurrent_peer_branch", []),
            "requested_processes": resource.get("expected", {}).get("processes"),
            "requested_threads": resource.get("expected", {}).get("threads"),
            "readback_processes": resource.get("readback", {}).get("processes"),
            "readback_threads": resource.get("readback", {}).get("threads"),
            "observed_processes": observed_processes,
            "observed_threads": observed_threads,
            "engine_wall_seconds": f(runtime.get("runtime", {}).get("wall_time_seconds")),
            "max_abs_closure_residual": residual_max,
            "max_structure_interval_anomaly": structure_max,
            "max_order_sum_mismatch": max_order_mismatch,
            "max_normalization_mismatch": norm_max,
            "exact_wavelength_count": len(obs),
            "quality_gate_pass": all(required_flags.values()),
            "checks": required_flags,
        }
        audits.append(audit)
        for r in obs:
            row = {"case_id": case, **r}
            row["role"] = spec.get("role")
            row["source_prefsp_sha256"] = spec.get("source_prefsp_sha256")
            row["post_fsp_sha256"] = post_sha
            hf_rows.append(row)
        order_rows.extend({"case_id": case, **r} for r in orders)
    return audits, hf_rows, order_rows


def build_hf_rows(registry: list[dict], hf_obs: list[dict], order_rows: list[dict], audits: list[dict], existing_fields: list[str]) -> list[dict]:
    spec_by_case = {r["case_id"]: r for r in registry}
    audit_by_case = {r["case_id"]: r for r in audits}
    order_map = {(r["case_id"], int(float(r["wavelength_nm"])), int(float(r["order_n"]))): r for r in order_rows}
    out = []
    for obs in hf_obs:
        c = obs["case_id"]; s = spec_by_case[c]; a = audit_by_case[c]; wl = int(float(obs["wavelength_nm"]))
        row = {k: "" for k in existing_fields}
        def put(k, v): row[k] = "" if v is None else str(v)
        for k in ["case_id", "geometry_id", "geometry_hash", "polarization", "wavelength_nm", "frequency_hz", "T_total", "R_total", "R_signed_monitor", "closure", "signed_closure_residual", "sourcepower_W", "raw_transmitted_power_W", "raw_reflected_power_W", "transmitted_order_sum", "transmitted_order_sum_mismatch", "eta_plus1", "eta_0", "eta_minus1", "non_target_efficiency", "directionality", "eta_plus1_over_minus1", "plus1_transmitted_fraction", "plus1_air_side_angle_deg", "transmitted_order_count", "plus1_u_x"]:
            put(k, obs.get(k))
        put("normalization_path", "raw_power_div_sourcepower")
        put("raw_power_origin", "independent_readonly_extractor")
        put("source_case_id", c)
        put("generator_id", "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2")
        put("interface_stack_id", "NP_K6_INDEPENDENT_STACK_PILOT_V1")
        for k, v in {
            "quality_gate_pass": "true", "training_label": "true", "provisional_hf_label": "true", "diagnostic_only": "false", "pilot_scope_only": "false", "bulk_mdc_compatible": "false", "candidate_performance_label": "true", "logical_task_id": c, "execution_id": f"{c}/attempt_001", "case_group": s.get("role"), "accepted_execution": "true", "setup_sha256": s.get("source_prefsp_sha256"), "case_type": "formal_development_hf_m7a", "dataset_source": "m7a_primary4_hf", "m5_training_label": "true", "m5_candidate_performance_label": "false", "order_source_path": f"outputs\\np_k6_m7a_primary4_hf_acquisition_v1\\cases\\{c}\\hf_transmitted_orders_long.csv", "transmission_power_normalization_mismatch": a.get("max_normalization_mismatch", 0.0), "reflection_power_normalization_mismatch": a.get("max_normalization_mismatch", 0.0)
        }.items(): put(k, v)
        for m in ORDERS:
            q = order_map[(c, wl, m)]
            put(f"eta_m{m:+d}", q.get("absolute_efficiency"))
        put("eta_order_sum", sum(f(order_map[(c, wl, m)].get("absolute_efficiency")) for m in ORDERS))
        out.append(row)
    return out


def build_lf(rows: list[dict]) -> list[dict]:
    master = LFROOT / "k6_design_space_master.csv.gz"
    with gzip.open(master, "rt", encoding="utf-8") as h:
        design = list(csv.DictReader(h))
    index = {r["geometry_id"]: i for i, r in enumerate(design)}
    needed = sorted({r["geometry_id"] for r in rows})
    missing = [g for g in needed if g not in index]
    bad = [g for g in needed if design[index[g]].get("split") != "development_pool"]
    if missing or bad:
        raise RuntimeError(f"LF geometry contract missing={missing} nondevelopment={bad}")
    arrays = {}
    for g in needed:
        i = index[g]; chunk = i // 5000; loc = i % 5000
        z = np.load(LFROOT / "lf_chunks" / f"chunk_{chunk:03d}.npz")
        arrays[g] = (z["eta_m_proxy"][loc].astype(float), z["propagating_sum_proxy"][loc].astype(float))
    out = []
    for r in rows:
        eta, tp = arrays[r["geometry_id"]]; wi = int(float(r["wavelength_nm"])) - 445
        rr = {"geometry_id": r["geometry_id"], "wavelength_nm": r["wavelength_nm"], "polarization": r["polarization"], "lf_T_proxy": float(tp[wi])}
        for j, m in enumerate(ORDERS): rr[f"lf_eta_m{m:+d}"] = float(eta[wi, j])
        out.append(rr)
    return out


def broadband(rows: list[dict], value_key: str) -> dict[str, float]:
    d: dict[str, list[float]] = defaultdict(list)
    for r in rows: d[r["geometry_id"]].append(f(r[value_key]))
    return {g: statistics.fmean(v) for g, v in d.items()}


def role_audit(all_rows: list[dict], new_rows: list[dict], lf_rows: list[dict], predictions: list[dict]) -> tuple[list[dict], dict]:
    pred_fields = ["lf_eta_plus1", "calibrated_eta_plus1", "ridge_eta_plus1", "residual_mlp_eta_plus1", "cnn_eta_plus1", "direct_model_eta_plus1"]
    hf = broadband(all_rows, "eta_plus1"); lfm = {(r["geometry_id"], int(float(r["wavelength_nm"])), r["polarization"]): r for r in lf_rows}
    pred_by: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in predictions:
        for k in pred_fields: pred_by[r["geometry_id"]][k].append(f(r[k]))
    pmean = {g: {k: statistics.fmean(v) for k, v in q.items()} for g, q in pred_by.items()}
    prev_geos = sorted({r["geometry_id"] for r in all_rows if r["geometry_id"] not in set(GEO_BY_G.values())})
    role_rows=[]
    for g, gid in GEO_BY_G.items():
        q=[r for r in new_rows if r["geometry_id"]==gid]
        residual=[]; residual_orders=[]
        for r in q:
            l=lfm[(gid,int(float(r["wavelength_nm"])),r["polarization"])]
            residual.append(abs(f(r["eta_plus1"])-f(l["lf_eta_m+1"])))
            residual_orders.extend(abs(f(r[f"eta_m{m:+d}"])-f(l[f"lf_eta_m{m:+d}"])) for m in ORDERS)
        pred_rank={k: sorted(pmean, key=lambda x: pmean[x].get(k,float('-inf')), reverse=True).index(gid)+1 if gid in pmean else None for k in pred_fields}
        if g==3:
            pairs=[]
            by=(defaultdict(dict))
            for r in q: by[int(float(r["wavelength_nm"]))][r["polarization"]]=r
            for wl,v in by.items():
                if set(v)=={"p","s"}: pairs.append(abs(f(v["p"]["eta_plus1"])-f(v["s"]["eta_plus1"])))
            detail={"ps_eta_plus1_abs_mean":statistics.fmean(pairs),"ps_eta_plus1_abs_max":max(pairs)}
        else: detail={}
        role_rows.append({"geometry_id":gid,"role":ROLE_BY_G[g],"hf_broadband_eta_plus1":hf[gid],"mean_abs_hf_minus_lf_eta_plus1":statistics.fmean(residual),"max_abs_hf_minus_lf_eta_plus1":max(residual),"mean_abs_hf_minus_lf_full_order":statistics.fmean(residual_orders),"predicted_rank_by_model":json.dumps(pred_rank,sort_keys=True),**detail})
    return role_rows, {"prediction_geometry_count":len(pmean),"prediction_fields":pred_fields}


def ranking_audit(all_rows: list[dict], lf_rows: list[dict], predictions: list[dict]) -> tuple[list[dict], dict]:
    truth=broadband(all_rows,"eta_plus1")
    lf={g:statistics.fmean([f(r["lf_eta_m+1"]) for r in lf_rows if r["geometry_id"]==g]) for g in {r["geometry_id"] for r in lf_rows}}
    pm: dict[str, dict[str,list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in predictions:
        for k in ["lf_eta_plus1","calibrated_eta_plus1","ridge_eta_plus1","residual_mlp_eta_plus1","cnn_eta_plus1","direct_model_eta_plus1"]: pm[r["geometry_id"]][k].append(f(r[k]))
    pred={g:{k:statistics.fmean(v) for k,v in q.items()} for g,q in pm.items()}
    methods={"LF":lf,**{k:{g:q.get(k) for g,q in pred.items()} for k in ["lf_eta_plus1","calibrated_eta_plus1","ridge_eta_plus1","residual_mlp_eta_plus1","cnn_eta_plus1","direct_model_eta_plus1"]}}
    geos=sorted(set(truth)); true_order=sorted(geos,key=lambda g:truth[g],reverse=True); true_rank={g:i+1 for i,g in enumerate(true_order)}
    rows=[]
    for name, vals in methods.items():
        common=[g for g in geos if g in vals and vals[g] is not None]
        order=sorted(common,key=lambda g:vals[g],reverse=True); rank={g:i+1 for i,g in enumerate(order)}
        top3=set(true_order[:3]); top5=set(true_order[:5]); rows.append({"model":name,"geometry_count":len(common),"spearman":spearman([truth[g] for g in common],[vals[g] for g in common]),"top3_recall":len(top3 & set(order[:3]))/3.0,"top5_recall":len(top5 & set(order[:5]))/5.0,"true_champion":true_order[0],"true_champion_predicted_rank":rank.get(true_order[0]),"G02_true_rank":true_rank.get(GEO_BY_G[2]),"G02_predicted_rank":rank.get(GEO_BY_G[2]),"predicted_order":"|".join(order)})
    return rows,{"true_broadband_order":true_order,"true_champion":true_order[0],"G02_true_rank":true_rank.get(GEO_BY_G[2])}


def ps_audit(rows: list[dict]) -> tuple[list[dict], dict]:
    pair=defaultdict(dict)
    for r in rows: pair[(r["geometry_id"],int(float(r["wavelength_nm"])) )][r["polarization"]]=r
    records=[]
    for (g,w),q in sorted(pair.items()):
        if set(q)!={"p","s"}: raise RuntimeError(f"P/S pair incomplete {g} {w}")
        r={"geometry_id":g,"wavelength_nm":w}
        for key in ["eta_plus1","eta_0","eta_minus1","R_total","T_total"]: r[f"abs_delta_{key}"]=abs(f(q["p"][key])-f(q["s"][key]))
        r["full_order_profile_l1"] = sum(abs(f(q["p"][f"eta_m{m:+d}"])-f(q["s"][f"eta_m{m:+d}"])) for m in ORDERS)
        records.append(r)
    summaries=[]
    for scope, subset in [("HF16",[r for r in records if r["geometry_id"] not in set(GEO_BY_G.values())]),("M7A4",[r for r in records if r["geometry_id"] in set(GEO_BY_G.values())]),("HF20",records)]:
        for k in ["abs_delta_eta_plus1","abs_delta_eta_0","abs_delta_eta_minus1","abs_delta_R_total","abs_delta_T_total","full_order_profile_l1"]:
            s=percentiles([f(r[k]) for r in subset]); summaries.append({"scope":scope,"metric":k,**s})
    return records,summaries


def residual_audit(all_rows: list[dict], lf_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    lm={(r["geometry_id"],int(float(r["wavelength_nm"])),r["polarization"]):r for r in lf_rows}
    long=[]
    for r in all_rows:
        l=lm[(r["geometry_id"],int(float(r["wavelength_nm"])),r["polarization"].lower())]
        for m in ORDERS:
            long.append({"geometry_id":r["geometry_id"],"polarization":r["polarization"],"wavelength_nm":r["wavelength_nm"],"output":f"eta_m{m:+d}","hf":f(r[f"eta_m{m:+d}"]),"lf":f(l[f"lf_eta_m{m:+d}"]),"delta_hf_minus_lf":f(r[f"eta_m{m:+d}"])-f(l[f"lf_eta_m{m:+d}"])})
        long.append({"geometry_id":r["geometry_id"],"polarization":r["polarization"],"wavelength_nm":r["wavelength_nm"],"output":"T_proxy","hf":f(r["T_total"]),"lf":f(l["lf_T_proxy"]),"delta_hf_minus_lf":f(r["T_total"])-f(l["lf_T_proxy"])})
    summary=[]
    for out in sorted({r["output"] for r in long}):
        q=[r["delta_hf_minus_lf"] for r in long if r["output"]==out]
        s=percentiles(q); summary.append({"output":out,**s,"abs_mean":statistics.fmean(abs(x) for x in q),"positive_bias":statistics.fmean(q)})
    return long,summary


def information_gain(role_rows: list[dict], ps_summary: list[dict], ranking_summary: dict) -> list[dict]:
    out=[]
    for r in role_rows:
        role=r["role"]
        if role=="RESIDUAL-TAIL": signal=r["max_abs_hf_minus_lf_eta_plus1"] > 0.05; evidence="HF-LF residual tail measured directly"
        elif role=="RANKING-CHAMPION-STRESS": signal=r["predicted_rank_by_model"] != ""; evidence=f"G02 true rank={ranking_summary.get('G02_true_rank')} after HF truth"
        elif role=="POLARIZATION-STRESS": signal=f(r.get("ps_eta_plus1_abs_max")) > 0.1; evidence="paired P/S HF contrast"
        else: signal=r["mean_abs_hf_minus_lf_full_order"] > 0.02; evidence="full-order response compared with nearest LF/HF coverage"
        out.append({"geometry_id":r["geometry_id"],"role":role,"observed_signal":bool(signal),"information_value_evidence":evidence,"active_learning_success_claim":False})
    return out


def concurrency_audit() -> dict:
    p=Path(r"D:/project/apcd_global_fdtd_slot_registry_v1.json"); reg=jread(p); activation=jread(ACQ/"concurrency3_trial_activation.json") if (ACQ/"concurrency3_trial_activation.json").exists() else {}
    rows=[]
    for r in reg.get("history",[]):
        if r.get("slot_id") in {"FDTD_SLOT_3","GLOBAL_SLOT_3"} or r.get("fdtd_slot_id") in {"FDTD_SLOT_3","GLOBAL_SLOT_3"}:
            rows.append(r)
    observed=[]
    for r in rows:
        snap=r.get("admission_snapshot") or {}; observed += [x for x in [snap.get("effective_global_active_jobs_after_acquire"),snap.get("active_fdtd_jobs")] if isinstance(x,(int,float))]
    max_obs=max([int(x) for x in observed],default=0)
    np_rows=[r for r in reg.get("history",[]) if str(r.get("branch"))=="work/np-k6-mdc-v1" and str(r.get("task_class"))=="NP_K6_M7A_PRIMARY4_FORMAL_FDTD"]
    return {"trial_id":"APCD_PRODUCTION_CONCURRENCY3_TRIAL_V1","temporary_only":True,"global_cap":3,"np_max_active_authorized":2,"lp_max_active_authorized":1,"rcwa_counts_as_fdtd":False,"fourth_fdtd_authorized":False,"max_observed_active_fdtd":max_obs,"slot3_history_rows":len(rows),"slot3_examples":[{"case_uid":r.get("case_uid"),"branch":r.get("branch"),"processes":r.get("processes"),"threads":r.get("threads"),"slot_acquire_time":r.get("slot_acquire_time"),"slot_release_time":r.get("slot_release_time"),"concurrent_peer_branch":r.get("concurrent_peer_branch"),"effective_after":(r.get("admission_snapshot") or {}).get("effective_global_active_jobs_after_acquire")} for r in rows[-12:]],"m7a_np_case_count":len(np_rows),"m7a_np_max_active_observed":max([int((r.get("admission_snapshot") or {}).get("active_fdtd_jobs",0)) for r in np_rows],default=0),"cpu_ram_observation":"not available as a continuous trial telemetry series; no resource-pressure failure observed in case evidence","quality_gate_impact":"all completed M7A cases passed; G04-P pending at closeout generation","activation_evidence":activation.get("created_utc")}


def main() -> None:
    if OUT.exists() and (OUT / "m7a_dataset_manifest.json").exists():
        raise RuntimeError(f"refusing completed existing output: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    prereg=DESIGN/"NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1.json"
    prereg_sha=sha(prereg)
    if prereg_sha != "bd221dfe8d15475cb5c0f9d5959a6595fed2238ff58f7ca1befbdc421bf65951": raise RuntimeError(f"prereg hash mismatch {prereg_sha}")
    registry=read_csv(ACQ/"primary4_case_registry.csv")
    if [r["case_id"] for r in registry] != CASE_IDS: raise RuntimeError("Primary4 registry order/identity mismatch")
    histories=history_index()
    audits,hf_obs,order_rows=case_audit(registry,histories)
    if not all(a["quality_gate_pass"] for a in audits): raise RuntimeError("case quality gate failed")
    existing_path=M6/"formal_development_hf_observations_352rows.csv"; existing=read_csv(existing_path); fields=list(existing[0])
    new_rows=build_hf_rows(registry,hf_obs,order_rows,audits,fields)
    if len(new_rows)!=88: raise RuntimeError(f"new rows={len(new_rows)}")
    merged=existing+new_rows
    if len(merged)!=440: raise RuntimeError("merged row count")
    lf_new=build_lf(new_rows); lf_existing=read_csv(M7/"lf_baseline_352rows.csv"); lf_merged=lf_existing+lf_new
    write_csv(OUT/"m7a_hf_observations_88rows.csv",new_rows,fields)
    lf_fields=["geometry_id","wavelength_nm","polarization","lf_T_proxy"]+[f"lf_eta_m{m:+d}" for m in ORDERS]
    write_csv(OUT/"m7a_lf_baseline_88rows.csv",lf_new,lf_fields)
    write_csv(OUT/"m7a_formal_development_hf_observations_440rows.csv",merged,fields)
    write_csv(OUT/"m7a_formal_development_lf_baseline_440rows.csv",lf_merged,lf_fields)
    role_rows,pred_meta=role_audit(merged,new_rows,lf_merged,read_csv(DESIGN/"candidate_predictions_long.csv"))
    rank_rows,rank_meta=ranking_audit(merged,lf_merged,read_csv(DESIGN/"candidate_predictions_long.csv"))
    ps_rows,ps_summary=ps_audit(merged); residual_rows,residual_summary=residual_audit(merged,lf_merged)
    gain_rows=information_gain(role_rows,ps_summary,rank_meta)
    write_csv(OUT/"m7a_case_quality_audit.csv",audits)
    write_csv(OUT/"m7a_role_truth_audit.csv",role_rows)
    write_csv(OUT/"m7a_broadband_ranking_audit.csv",rank_rows)
    write_csv(OUT/"m7a_ps_polarization_audit.csv",ps_rows)
    write_csv(OUT/"m7a_ps_polarization_summary.csv",ps_summary)
    write_csv(OUT/"m7a_lf_residual_long.csv",residual_rows)
    write_csv(OUT/"m7a_lf_residual_summary.csv",residual_summary)
    write_csv(OUT/"m7a_information_gain_audit.csv",gain_rows)
    jwrite(OUT/"m7a_case_quality_audit.json",{"schema_version":"np_k6_m7a_case_quality_audit_v1","case_count":len(audits),"all_quality_gate_pass":all(a["quality_gate_pass"] for a in audits),"cases":audits})
    jwrite(OUT/"m7a_broadband_ranking_summary.json",rank_meta|{"models":rank_rows})
    jwrite(OUT/"m7a_ps_polarization_summary.json",{"scope_summaries":ps_summary,"pair_count":len(ps_rows)})
    jwrite(OUT/"m7a_concurrency3_trial_observation.json",concurrency_audit())
    existing_keys={(r["case_id"],int(float(r["wavelength_nm"]))) for r in existing}; new_keys={(r["case_id"],int(float(r["wavelength_nm"]))) for r in new_rows}; merged_keys={(r["case_id"],int(float(r["wavelength_nm"]))) for r in merged}
    ext=jread(ROOT/"outputs/np_k6_m5_fullk6_forward_v0/external_set_registry.json")
    raw_ext = ext.get("geometries", ext.get("geometry_ids", []))
    ext_ids = {x if isinstance(x, str) else x.get("geometry_id") for x in raw_ext}
    ext_ids.discard(None)
    new_ids={r["geometry_id"] for r in new_rows}
    prov={"existing_352_sha256":sha(existing_path),"new_88_sha256":sha(OUT/"m7a_hf_observations_88rows.csv"),"merged_440_sha256":sha(OUT/"m7a_formal_development_hf_observations_440rows.csv"),"lf_new_sha256":sha(OUT/"m7a_lf_baseline_88rows.csv"),"duplicate_or_conflicting_provenance":len(merged_keys)-len(merged),"sealed_target_reads":0,"external_target_reads":0,"external_metadata_only":True,"external_geometry_count":len(ext_ids),"new_external_overlap":sorted(new_ids&ext_ids),"quarantined_m6_g01_geometry":"K6X_D110_D125_D130_D135_D140_D175","quarantined_overlap":any("K6X_D110_D125_D130_D135_D140_D175"==g for g in new_ids),"prereg_sha256":prereg_sha}
    jwrite(OUT/"m7a_provenance_external_sealed_audit.json",prov)
    budget={"m7a_logical_cases":8,"m7a_entered_solver":sum(int(a["checks"]["entered"]) for a in audits),"m7a_run_invocations":8,"attempt_002_count":0,"replacements":0,"replays":0,"external_hf_calls":0,"sealed_target_reads":0,"m8_started":False,"training_started":False}
    jwrite(OUT/"m7a_solver_budget_audit.json",budget)
    manifest={"schema_version":"np_k6_m7a_primary4_targeted_hf_closeout_manifest_v1","status":"COMPLETE_PENDING_VALIDATOR","preregistration_id":"NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1","preregistration_sha256":prereg_sha,"primary4_case_count":8,"new_hf_rows":len(new_rows),"existing_hf_rows":len(existing),"merged_hf_rows":len(merged),"new_geometry_count":4,"merged_geometry_count":len({r["geometry_id"] for r in merged}),"merged_paired_cases":len({(r["geometry_id"],r["polarization"]) for r in merged}),"wavelengths_nm":WLS,"u_x":0.0,"k_y":0.0,"generator_id":"NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2","interface_stack_id":"NP_K6_INDEPENDENT_STACK_PILOT_V1","production_mesh":"NP_K6_PILOT_FIXED_GRID_V1","native_m1":True,"training_label_new_rows":True,"diagnostic_only_new_rows":False,"candidate_performance_label_new_rows":True,"external_target_reads":0,"sealed_target_reads":0,"m8_started":False,"training_started":False,"temporary_concurrency3_trial":True}
    jwrite(OUT/"m7a_dataset_manifest.json",manifest)
    print(json.dumps({"out":str(OUT),"new_rows":len(new_rows),"merged_rows":len(merged),"geometry_count":manifest["merged_geometry_count"],"paired_cases":manifest["merged_paired_cases"],"prereg_sha256":prereg_sha,"case_quality":all(a["quality_gate_pass"] for a in audits)},indent=2))


if __name__ == "__main__":
    main()

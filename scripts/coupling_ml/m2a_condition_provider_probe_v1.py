import csv
import json
import os
import hashlib
from collections import defaultdict
from pathlib import Path

ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
COUPLING = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def csv_rows(p):
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(x):
    try: return float(x)
    except Exception: return None


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, prefix + "." + str(k) if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, prefix + f"[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def main():
    reg_path = ML / r"outputs\coupling_ml\M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1\M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION\M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1\M0F_FINAL_RECONCILED_LEVEL1_NUMERICAL_REGISTRY_V1.csv"
    rows = csv_rows(reg_path)
    by_case = defaultdict(list)
    for r in rows:
        if r.get("candidate") == "ALT1": by_case[r.get("logical_case_id")].append(r)
    condition_summary = []
    for case, rs in sorted(by_case.items()):
        rr = {r.get("observable"): r for r in rs}
        diffs = {}
        for k in ["R", "T"]:
            if k in rr:
                try: v = json.loads(rr[k].get("target_diff_json") or "null")
                except Exception: v = None
                vals = []
                if isinstance(v, list):
                    def collect(x):
                        if isinstance(x, list):
                            for y in x: collect(y)
                        elif isinstance(x, (int, float)): vals.append(float(x))
                    collect(v)
                elif isinstance(v, (int, float)): vals = [float(v)]
                diffs[k] = {"mean_abs": sum(abs(x) for x in vals)/len(vals) if vals else None, "max_abs": max([abs(x) for x in vals], default=None), "raw": v}
        sample = rs[0]
        condition_summary.append({
            "logical_case_id": case,
            "candidate": sample.get("candidate"), "spacer_nm": num(sample.get("spacer_nm")), "ux": num(sample.get("ux")),
            "source_polarization": sample.get("source_polarization"), "provider_channel": sample.get("provider_channel"),
            "wavelength_grid_nm": sample.get("wavelength_grid_nm"), "level1_reconciled_status": sample.get("level1_reconciled_status"),
            "residual_compatible": sample.get("residual_compatible"), "R_diff": diffs.get("R"), "T_diff": diffs.get("T"),
            "source_raw_sha256": sample.get("level2_authoritative_raw_sha256"), "source_raw_path": sample.get("level2_authoritative_raw_path"),
        })

    provider_root = COUPLING / r"outputs\coupling\rcwa_component_benchmark_v1\runtime_runs\RCWA_LEVEL1_ANGULAR_ACQUISITION_9JOB_V1"
    provider_files = []
    for dp, dns, fns in os.walk(provider_root):
        for fn in fns:
            if fn.endswith("_postprocessed.json"):
                p = Path(dp) / fn
                try:
                    obj = json.loads(p.read_text(encoding="utf-8"))
                except Exception as e:
                    provider_files.append({"path": str(p), "error": repr(e)})
                    continue
                kv = list(flatten(obj))
                matches = sorted({v for _, v in kv if any(t in v for t in ["K6X", "D1", "D2", "D3", "D4", "D5", "D6"])})
                provider_files.append({"path": str(p), "sha256": sha(p), "keys": list(obj)[:50], "string_matches": matches[:60]})
    # Files immediately around provider records, useful for provenance routing only.
    nearby = []
    if provider_root.exists():
        for p in sorted(provider_root.rglob("*")):
            if p.is_file() and p.suffix.lower() in {".json", ".csv", ".md"}:
                if "postprocessed" in p.name.lower() or "setup" in p.name.lower() or "manifest" in p.name.lower() or "readback" in p.name.lower():
                    nearby.append({"path": str(p), "size": p.stat().st_size, "sha256": sha(p)})

    print(json.dumps({"condition_summary": condition_summary, "provider_root": str(provider_root), "provider_root_exists": provider_root.exists(), "provider_files": provider_files, "nearby": nearby[:300]}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()

import csv
import json
from collections import defaultdict
from pathlib import Path

p = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv")
with p.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
by = defaultdict(list)
for r in rows:
    by[r["geometry_id"]].append(r)
fields = ["R_total", "T_total", "eta_plus1", "eta_minus1", "directionality"]
out = []
for g, rs in sorted(by.items()):
    missing = {pol: [k for k in fields if any(not r.get(k) for r in rs if r.get("polarization") == pol)] for pol in ["p", "s"]}
    out.append({"geometry_id": g, "count": len(rs), "missing": missing, "pols": sorted({r.get("polarization") for r in rs})})
print(json.dumps(out, ensure_ascii=False, indent=2))

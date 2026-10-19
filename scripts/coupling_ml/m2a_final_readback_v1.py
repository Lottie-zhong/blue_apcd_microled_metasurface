import csv
import json
import subprocess
from pathlib import Path

ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
COUPLING = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
NP = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ML / r"outputs\coupling_ml\M2A_GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING_V1"


def git(path, args):
    p = subprocess.run(["git", *args], cwd=str(path), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"rc": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def read_csv(name):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    selected = json.loads((OUT / "M2A_SELECTED_GEOMETRY_SEED_SET_V1.json").read_text(encoding="utf-8"))
    routing = json.loads((OUT / "M2A_FUTURE_CANONICAL_ROUTING_CONTRACT_PREFLIGHT_V1.json").read_text(encoding="utf-8"))
    bridge = json.loads((OUT / "M2A_ALT1_ROUTING_ANCHOR_INFORMATION_VALUE_V1.json").read_text(encoding="utf-8"))
    conditions = read_csv("M2A_CONDITION_INFORMATION_VALUE_AUDIT_V1.csv")
    pool = read_csv("M2A_NP22_GEOMETRY_CANDIDATE_POOL_V1.csv")
    selected_pool = [r for r in pool if r["selection_status"] == "SELECTED"]
    states = {}
    for name, path in [("ml", ML), ("coupling", COUPLING), ("np", NP)]:
        states[name] = {"path": str(path), "branch": git(path, ["branch", "--show-current"]), "head": git(path, ["rev-parse", "HEAD"]), "status": git(path, ["status", "--short"]), "upstream": git(path, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])}
    print(json.dumps({"selected": selected, "selected_pool": selected_pool, "conditions": conditions, "routing": routing, "bridge": bridge, "git": states}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()

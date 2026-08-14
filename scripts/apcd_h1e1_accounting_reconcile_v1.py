from pathlib import Path
import json
import os

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "reports/stage_h1e1_j1_anisotropy/h1e1_solver_accounting.json"


def main():
    data = json.loads(PATH.read_text(encoding="utf-8"))
    for row in data["cases"]:
        row["solver_entered"] = bool(row.get("solver_entered"))
        checkpoint = ROOT / "outputs/lp_extended_j1_h1e1/runtime/cases" / row["case_id"] / "checkpoint.json"
        recovered = checkpoint.exists()
        row["accepted"] = bool(row.get("accepted")) or recovered
        row["quarantined"] = (bool(row.get("quarantined")) and not recovered) or (row["solver_entered"] and not row["accepted"])
        if recovered:
            row["status"] = "ACCEPTED_POSTFSP_RECOVERED" if row.get("status") != "ACCEPTED" else row.get("status")
    data["entered_formal_subruns"] = sum(row["solver_entered"] for row in data["cases"])
    data["accepted_formal_subruns"] = sum(row["accepted"] for row in data["cases"])
    data["quarantined_formal_subruns"] = sum(row["quarantined"] for row in data["cases"])
    tmp = PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, PATH)
    print(json.dumps({k: data[k] for k in ("planned_formal_subruns", "entered_formal_subruns", "accepted_formal_subruns", "quarantined_formal_subruns")}, indent=2))


if __name__ == "__main__": main()

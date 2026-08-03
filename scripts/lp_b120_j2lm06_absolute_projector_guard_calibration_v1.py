"""Offline-only projector guard audit artifact verifier. No solver imports or calls."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=ROOT/"outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_projector_guard_execution_summary_v1.json"
    print(json.dumps(json.loads(p.read_text(encoding="utf-8")),indent=2,sort_keys=True))
if __name__=="__main__": main()

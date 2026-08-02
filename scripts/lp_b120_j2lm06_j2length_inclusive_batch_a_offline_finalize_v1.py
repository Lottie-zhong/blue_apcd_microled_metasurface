import argparse, json, pathlib

def parse_ledger_token(token):
    if token == "FINAL":
        return {"kind":"FINAL","candidate_id":None,"polarization":None}
    if "_" not in token:
        raise ValueError("expected candidate_id_polarization or FINAL")
    candidate, polarization = token.rsplit("_", 1)
    if polarization not in {"x", "y"}:
        raise ValueError("invalid polarization")
    return {"kind":"SUBRUN","candidate_id":candidate,"polarization":polarization}

def verify(root):
    an=pathlib.Path(root)/"outputs/lp_ml_dataset_v1/analysis"
    p=an/"b120_j2lm06_j2length_inclusive_batch_a_subrun_accounting_v1.json"
    with open(p,encoding="utf-8") as f: a=json.load(f)
    assert a["planned"]==8 and a["entered"]==8
    assert a["accepted"]==8 and a["failed"]==0 and a["missing"]==0
    parse_ledger_token("FINAL")
    return {"planned":8,"entered":8,"accepted":8,"failed":0,"missing":0,"solver_calls":0,"status":"OFFLINE_FINALIZED"}

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); args=ap.parse_args()
    print(json.dumps(verify(args.root),sort_keys=True))

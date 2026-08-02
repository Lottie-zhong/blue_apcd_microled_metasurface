import json,hashlib,csv
from pathlib import Path

def validate(root: Path):
    e=root/"outputs/np_k6_p1d4b_k6x_run3c_n1_material_representation_constant_eps_v2_diagnostic_v1"
    setup=root/"outputs/np_k6_p1d4b_k6x_run3c_n1_material_representation_constant_eps_v2_setup_v1"
    m=json.loads((e/"entered_ledger.json").read_text())
    assert m["entered"] and m["run_invocation_count"]==1 and m["engine_completed"] and m["post_saved"] and m["controller_returned"]
    assert m["source_prefsp_sha256"]=="8b7551773caf482a9af8d4470572fa5f4b05aee6843f4ab521d8ff88d4bef522"
    post=json.loads((e/"post_fsp_checksum.json").read_text()); assert len(post["sha256"])==64 and post["independent_readonly_reload"]
    mat=json.loads((e/"post_run_material_audit.json").read_text())
    assert mat["all_constant"] and mat["all_sampled_absent"]
    assert all(abs(x["n_squared_minus_epsilon"])<=1e-10 for x in mat["post_material_readback"].values())
    grid=json.loads((e/"actual_grid_comparison.json").read_text()); assert grid["coordinate_grid_equal"] and grid["mesh_contract_equal"]
    rows=list(csv.DictReader((e/"formal_vs_constant_eps_v2_power_balance_spectrum.csv").open()))
    assert len(rows)==11 and all(abs(float(r["order_sum_minus_T"]))<=1e-10 for r in rows)
    d=json.loads((e/"diagnostic_decision.json").read_text()); assert d["entered"]==1 and d["run_invocation_count"]==1 and d["no_N2"]
    return d["final_status"]

if __name__=="__main__": print(validate(Path(__file__).resolve().parents[1]))

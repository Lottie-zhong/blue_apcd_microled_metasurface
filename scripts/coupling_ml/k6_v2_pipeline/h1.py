"""Frozen H2 reconstruction and original conjunctive H1 evaluation."""
from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from .contracts import H1_AUTHORITY_SHA256, H2_DECODER_SHA256, MODEL_SOURCE_SHA256, ORDER_M, WAVELENGTHS_NM

def _load(path, name, expected):
    h=hashlib.sha256(path.read_bytes()).hexdigest()
    if h!=expected: raise ValueError("frozen_authority_hash_mismatch:"+str(path))
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod)
    return mod

def _root():
    return Path(__file__).resolve().parents[3]

def load_h1_authority():
    root=_root()
    gate_path=root/"reports"/"coupling"/"PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json"
    gate_hash=hashlib.sha256(gate_path.read_bytes()).hexdigest()
    if gate_hash!=H1_AUTHORITY_SHA256: raise ValueError("h1_gate_authority_hash_mismatch")
    return json.loads(gate_path.read_text(encoding="utf-8"))

def load_h2_decoder():
    return _load(_root()/"scripts"/"shared_fdtd"/"tools"/"pw_complex_floquet_state_v1.py",
                 "k6v2_frozen_h2",H2_DECODER_SHA256)

def h2_weights(decoder):
    w=np.empty((21,7,2),float)
    for i,wl in enumerate(WAVELENGTHS_NM):
        for j,m in enumerate(ORDER_M):
            for k,pol in enumerate(("TE","TM")):
                q=decoder._mode(int(m),0,float(wl),1.,1,pol,
                  period_x_m=float(decoder.PERIOD_X_M),period_y_m=float(decoder.PERIOD_Y_M))
                if not q["propagating"] or not np.isfinite(q["power_z_per_abs_e2"]):
                    raise ValueError("frozen_h2_mode_invalid")
                w[i,j,k]=q["power_z_per_abs_e2"]
    return w

def reconstruct_h2(c_hat,p_scale,decoder):
    c,p=np.asarray(c_hat,complex),np.asarray(p_scale,float)
    if c.ndim==3:c=c[None,...]
    if p.ndim==1:p=p[None,...]
    if c.ndim!=4 or c.shape[1:]!=(21,7,2) or p.shape!=(len(c),21):
        raise ValueError("h2_input_shape")
    if not (np.isfinite(c.real).all() and np.isfinite(c.imag).all() and np.isfinite(p).all()) or (p<=0).any():
        raise ValueError("h2_input_nonfinite_or_nonpositive")
    modal=np.sum(h2_weights(decoder)[None,...]*np.abs(c)**2,axis=-1)
    total=modal.sum(axis=-1)
    if not np.isfinite(total).all() or (total<=0).any():raise ValueError("h2_modal_total_invalid")
    eta=modal/total[...,None]
    return {"eta":eta,"absolute_order":eta*p[...,None],"total_power":p.copy(),"modal_order":modal}

def _pear(a,b):
    return float(np.corrcoef(np.ravel(a),np.ravel(b))[0,1])

def _metric_rows(model,ct,cp,pt,pp,et,at,decoder):
    h2=reconstruct_h2(cp,pp,decoder); rows=[]
    for i in range(len(ct)):
        rows.append(model.met(ct[i],cp[i],et[i],h2["eta"][i],at[i],
          h2["absolute_order"][i],pt[i],h2["total_power"][i]))
        rows[-1]["p_scale_relative_rmse"]=rows[-1]["total_power_relative_rmse"]
    return {"metrics":{k:model.summ([r[k] for r in rows]) for k in rows[0]},
            "routing_pearson":_pear(et,h2["eta"]),
            "total_power_pearson":_pear(pt,h2["total_power"]),"per_geometry":rows}

def evaluate_original_h1(c_true,c_pred_by_seed,p_true,p_pred_by_seed,eta_true,absolute_order_true,decoder=None):
    """C_hat is complex seed mean; P_scale is physical arithmetic mean across seeds."""
    model=_load(_root()/"scripts"/"coupling_ml"/"pw_k6_stage1_32g_frozen_model_v1.py",
                "k6v2_frozen_h1_metrics",MODEL_SOURCE_SHA256)
    gate=load_h1_authority()
    if decoder is None:decoder=load_h2_decoder()
    ct,cp=np.asarray(c_true,complex),np.asarray(c_pred_by_seed,complex)
    pt,pp=np.asarray(p_true,float),np.asarray(p_pred_by_seed,float)
    et,at=np.asarray(eta_true,float),np.asarray(absolute_order_true,float)
    if cp.ndim==4:cp=cp[None,...]
    if pp.ndim==2:pp=pp[None,...]
    n=len(ct)
    if ct.shape!=(n,21,7,2) or cp.shape[1:]!=ct.shape or pp.shape!=(len(cp),n,21):
        raise ValueError("prediction_truth_alignment_shape")
    if pt.shape!=(n,21) or et.shape!=(n,21,7) or at.shape!=(n,21,7):
        raise ValueError("h1_truth_shape")
    if not (np.isfinite(ct.real).all() and np.isfinite(ct.imag).all() and
            np.isfinite(cp.real).all() and np.isfinite(cp.imag).all() and
            np.isfinite(pt).all() and np.isfinite(pp).all() and np.isfinite(et).all() and np.isfinite(at).all()):
        raise ValueError("h1_input_nonfinite")
    if (pt<=0).any() or (pp<=0).any():raise ValueError("pscale_truth_prediction_nonpositive")
    seeds=[_metric_rows(model,ct,cp[s],pt,pp[s],et,at,decoder) for s in range(len(cp))]
    mean=_metric_rows(model,ct,cp.mean(axis=0),pt,pp.mean(axis=0),et,at,decoder)
    sm=[float(np.median([r["state_relative_rmse"] for r in x["per_geometry"]])) for x in seeds]
    sstd=float(np.std(sm)) if len(sm)>1 else None
    m=mean["metrics"]; lim=gate["chart_numeric_authority"]
    threshold=lim["thresholded_absolute_order_relative"]["significance_threshold"]
    if abs(threshold-model.THRESHOLD)>1e-15:raise ValueError("threshold_source_mismatch")
    g={
      "state":m["state_relative_rmse"]["median"]<=lim["state_relative_rmse"]["median_max"] and m["state_relative_rmse"]["q95"]<=lim["state_relative_rmse"]["q95_max"],
      "routing":m["routing_eta_rmse"]["median"]<=lim["routing_eta_rmse"]["median_max"] and m["routing_eta_rmse"]["q95"]<=lim["routing_eta_rmse"]["q95_max"] and mean["routing_pearson"]>=lim["routing_eta_rmse"]["pearson_min"],
      "absolute_order":m["absolute_order_source_normalized_rmse"]["median"]<=lim["absolute_order_source_normalized_rmse"]["median_max"] and m["absolute_order_source_normalized_rmse"]["q95"]<=lim["absolute_order_source_normalized_rmse"]["q95_max"],
      "thresholded_absolute_order":m["thresholded_absolute_order_relative_median"]["median"]<=lim["thresholded_absolute_order_relative"]["median_max"] and m["thresholded_absolute_order_relative_median"]["q95"]<=lim["thresholded_absolute_order_relative"]["q95_max"],
      "total_power":m["total_power_relative_rmse"]["median"]<=lim["total_power_relative"]["median_max"] and m["total_power_relative_rmse"]["q95"]<=lim["total_power_relative"]["q95_max"] and mean["total_power_pearson"]>=lim["total_power_relative"]["pearson_min"],
      "seed_stability":None if sstd is None else sstd<=lim["seed_state_median_std_max"]}
    applicable=[x for x in g.values() if x is not None]
    return {"h1_gate_sha256":H1_AUTHORITY_SHA256,"h2_decoder_sha256":H2_DECODER_SHA256,
      "threshold_significance":threshold,"aggregation":{"c_hat":"complex arithmetic seed mean",
      "p_scale":"arithmetic mean in positive physical domain after inverse log normalization and exp"},
      "aggregate":mean,"per_seed":[x["metrics"] for x in seeds],"seed_state_medians":sm,
      "seed_state_median_std":sstd,"gates":g,"all_applicable_numeric_gates_attained":bool(applicable) and all(applicable),
      "seed_stability_status":"NOT_APPLICABLE_DETERMINISTIC_CANDIDATE" if sstd is None else ("PASS" if g["seed_stability"] else "FAIL"),
      "production_admission":False}

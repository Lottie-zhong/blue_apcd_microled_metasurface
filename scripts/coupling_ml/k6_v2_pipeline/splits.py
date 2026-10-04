"""Frozen geometry-level outer/inner splits and train-only preprocessing."""
from __future__ import annotations
import csv,hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping,Tuple
import numpy as np
from . import contracts as C
from .ingest import DataAccessError, _need, sha256_file, ROOT, REV

@dataclass(frozen=True)
class Partition:
    train_indices:Tuple[int,...]
    validation_indices:Tuple[int,...]
    train_case_ids:Tuple[str,...]
    validation_case_ids:Tuple[str,...]
@dataclass(frozen=True)
class OuterFold:
    outer_fold:int
    train_indices:Tuple[int,...]
    validation_indices:Tuple[int,...]
    inner:Mapping[int,Partition]
    learning_curve:Mapping[int,Tuple[int,...]]
@dataclass(frozen=True)
class GeometryFoldPlan:
    case_ids:Tuple[str,...]
    outer_folds:Mapping[int,OuterFold]
    manifest_sha256:Mapping[str,str]

def _read_csv(path,expected_sha):
    _need(sha256_file(path)==expected_sha,"fold_manifest_sha_mismatch:"+path.name)
    with open(path,"r",encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def _geometry(row):
    return tuple(int(row[f"D{i}_nm"]) for i in range(1,7))
def _grouped(row):
    _need(str(row.get("all_21_wavelengths_grouped","")).lower()=="true","wavelengths_not_grouped_by_geometry")
def _role_matches(actual,manifest_role):
    if actual==C.ROLE_OLD32: return manifest_role in (C.ROLE_OLD32,"EXISTING32_TRAIN_ONLY","EXISTING32")
    return actual==manifest_role
def _rows_for(rows,fold):
    return [r for r in rows if int(r["outer_fold"])==fold]
def load_geometry_fold_plan(collection,root=None):
    _need(collection.purpose=="development","fold_plan_requires_development_collection")
    cases=collection.training_cases()
    ids=tuple(x.case_id for x in cases); _need(len(ids)==160 and len(set(ids))==160,"fold_plan_requires_exact_160_development_cases")
    byid={x.case_id:x for x in cases}; ix={cid:i for i,cid in enumerate(ids)}
    root=Path(root) if root else ROOT; d=root/REV
    outerp=d/"DEVELOPMENT_FOLD_MANIFEST_V2.csv"; innerp=d/"INNER_FOLD_MANIFEST_V2.csv"; lcp=d/"LEARNING_CURVE_SUBSET_MANIFEST_V2.csv"
    outer=_read_csv(outerp,C.V2_FOLD_MANIFEST_SHA256)
    inner=_read_csv(innerp,C.V2_INNER_FOLD_MANIFEST_SHA256)
    lc=_read_csv(lcp,C.V2_LEARNING_CURVE_MANIFEST_SHA256)
    _need(len(outer)==128 and len(inner)==512 and len(lc)==896,"fold_manifest_row_count_mismatch")
    plans={}
    for f in range(1,5):
        orows=_rows_for(outer,f); valid={r["case_id"] for r in orows}
        _need(len(orows)==32 and len(valid)==32,"outer_validation_count_mismatch")
        _need(all(byid[c].role in (C.ROLE_GLOBAL_DEV,C.ROLE_LOCAL_AXIS) for c in valid),"outer_validation_contains_non_global_dev")
        for r in orows:
            _grouped(r); cid=r["case_id"]
            _need(cid in byid and _role_matches(byid[cid].role,r["role"]) and byid[cid].ordered_D_nm==_geometry(r),"outer_manifest_case_mismatch:"+cid)
        train=set(ids)-valid
        _need(len(train)==128 and all(byid[c].role in C.DEVELOPMENT_ROLES for c in train),"outer_train_role_or_count_mismatch")
        inn={}
        for k in range(1,4):
            rr=[r for r in _rows_for(inner,f) if int(r["inner_fold"])==k]
            vids={r["case_id"] for r in rr}
            _need(len(rr) in (42,43) and vids.issubset(train),"inner_validation_set_invalid")
            for r in rr:
                _grouped(r); cid=r["case_id"]
                _need(_role_matches(byid[cid].role,r["role"]) and byid[cid].ordered_D_nm==_geometry(r),"inner_manifest_case_mismatch:"+cid)
            tr=train-vids
            _need(len(tr)+len(vids)==128,"inner_partition_count_mismatch")
            inn[k]=Partition(tuple(ix[c] for c in ids if c in tr),tuple(ix[c] for c in ids if c in vids),
                             tuple(c for c in ids if c in tr),tuple(c for c in ids if c in vids))
        inner_seen=set().union(*(set(p.validation_case_ids) for p in inn.values()))
        _need(inner_seen==train and sum(len(p.validation_indices) for p in inn.values())==128,"inner_validation_not_partition_of_outer_train")
        lcp_by_size={}
        for size in (32,64,128):
            rr=[r for r in _rows_for(lc,f) if int(r["training_geometry_count"])==size]
            ss={r["case_id"] for r in rr}
            _need(len(rr)==size and len(ss)==size and ss.issubset(train),"learning_curve_subset_invalid")
            for r in rr:
                _grouped(r); cid=r["case_id"]
                _need(_role_matches(byid[cid].role,r["role"]) and byid[cid].ordered_D_nm==_geometry(r),"learning_curve_case_mismatch:"+cid)
            if size==32: _need(all(byid[c].role==C.ROLE_OLD32 for c in ss),"32_curve_must_be_old32")
            if size==128: _need(ss==train,"128_curve_must_equal_outer_train")
            lcp_by_size[size]=tuple(ix[c] for c in ids if c in ss)
        _need(set(lcp_by_size[32]).issubset(lcp_by_size[64]) and set(lcp_by_size[64]).issubset(lcp_by_size[128]),"learning_curve_not_nested")
        plans[f]=OuterFold(f,tuple(ix[c] for c in ids if c in train),tuple(ix[c] for c in ids if c in valid),inn,lcp_by_size)
    return GeometryFoldPlan(ids,plans,{"outer":C.V2_FOLD_MANIFEST_SHA256,"inner":C.V2_INNER_FOLD_MANIFEST_SHA256,"learning_curve":C.V2_LEARNING_CURVE_MANIFEST_SHA256})

@dataclass(frozen=True)
class GeometryScaler:
    mean:np.ndarray
    scale:np.ndarray
    fit_indices:Tuple[int,...]
    fit_case_ids:Tuple[str,...]
    fit_data_sha256:str
    def transform(self,geometries):
        x=np.asarray(geometries,dtype=float)
        _need(x.ndim==2 and x.shape[1]==6 and np.isfinite(x).all(),"geometry_transform_input_invalid")
        return (x-self.mean)/self.scale

def fit_geometry_scaler(geometries,train_indices,case_ids=()):
    x=np.asarray(geometries,dtype=float); ix=tuple(int(i) for i in train_indices)
    _need(x.ndim==2 and x.shape[1]==6 and np.isfinite(x).all(),"geometry_scaler_input_invalid")
    _need(ix and len(ix)==len(set(ix)) and all(0<=i<len(x) for i in ix),"geometry_scaler_train_indices_invalid")
    train=x[np.asarray(ix,dtype=int)]
    mean=train.mean(axis=0); scale=train.std(axis=0)
    _need(np.isfinite(mean).all() and np.isfinite(scale).all() and (scale>0).all(),"geometry_scaler_zero_or_nonfinite_scale")
    cids=tuple(str(case_ids[i]) for i in ix) if case_ids else ()
    digest=hashlib.sha256(np.ascontiguousarray(train,dtype="<f8").tobytes()).hexdigest()
    return GeometryScaler(mean,scale,ix,cids,digest)

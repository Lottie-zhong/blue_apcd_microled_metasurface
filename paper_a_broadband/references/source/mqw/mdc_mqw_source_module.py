"""Validated coordinates and weights for the V1 primary-MQW source module."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'configs'/'mdc_realistic_mqw_source_module_v1.json'
def load():
    data=json.loads(CONFIG.read_text(encoding='utf-8'))
    wells=data['primary_mqw']['well_centers_nm']; weights=data['primary_mqw']['weights']
    if len(wells)!=12 or len(weights)!=12 or abs(sum(weights)-1)>1e-12: raise ValueError('invalid 12-MQW source contract')
    if any(abs(wells[i]-wells[i-1]+19)>1e-9 for i in range(1,len(wells))): raise ValueError('primary well centers violate well-first 19 nm period')
    if abs(sum(wells)/len(wells)-data['primary_mqw']['centroid_nm'])>1e-9: raise ValueError('centroid mismatch')
    if data['strain_release_mqw']['formal_primary_emission_weight']!=0: raise ValueError('strain-release wells must not enter primary output')
    return data

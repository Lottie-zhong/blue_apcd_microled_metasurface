"""Reusable Lumerical 2D monitor and closed power-box contract."""
from __future__ import annotations
import hashlib, json
from typing import Any
import numpy as np

def add_source_local_mesh(fdtd,x:float,y:float,outer_half:float=40e-9,cell:float=2e-9):
    fdtd.addmesh();fdtd.set('name','source_local_mesh');fdtd.set('x',x);fdtd.set('y',y);fdtd.set('x span',2*(outer_half+10e-9));fdtd.set('y span',2*(outer_half+10e-9));fdtd.set('override x mesh',True);fdtd.set('override y mesh',True);fdtd.set('dx',cell);fdtd.set('dy',cell)

def _monitor_spectrum(fdtd,wavelength_start:float|None=None,wavelength_stop:float|None=None,frequency_points:int=1):
    # Project-validated power monitors inherit the source limits. Power-monitor
    # objects do not expose wavelength start/stop properties in v251.
    fdtd.set('override global monitor settings',True);fdtd.set('use wavelength spacing',True);fdtd.set('frequency points',frequency_points)

def add_field_channel_monitor(fdtd,x:float,y:float,span:float=80e-9):
    fdtd.addprofile();fdtd.set('name','field_channel');fdtd.set('monitor type','2D Z-normal');fdtd.set('x',x);fdtd.set('y',y);fdtd.set('x span',span);fdtd.set('y span',span);_monitor_spectrum(fdtd)

def _line(fdtd,name,kind,x,y,span,wavelength_start=None,wavelength_stop=None,frequency_points=1):
    fdtd.addpower();fdtd.set('name',name);fdtd.set('monitor type',kind);fdtd.set('x',x);fdtd.set('y',y);fdtd.set('x span' if kind=='Linear X' else 'y span',span);_monitor_spectrum(fdtd,wavelength_start,wavelength_stop,frequency_points)

def add_2d_power_box(fdtd,prefix:str,x:float,y:float,half:float,wavelength_start=None,wavelength_stop=None,frequency_points=1):
    args=(wavelength_start,wavelength_stop,frequency_points)
    _line(fdtd,prefix+'_top','Linear X',x,y+half,2*half,*args);_line(fdtd,prefix+'_bottom','Linear X',x,y-half,2*half,*args)
    _line(fdtd,prefix+'_right','Linear Y',x+half,y,2*half,*args);_line(fdtd,prefix+'_left','Linear Y',x-half,y,2*half,*args)

def add_reference_plane_monitor(fdtd,name:str,x:float,y:float,span:float,wavelength_start=None,wavelength_stop=None,frequency_points=1):
    _line(fdtd,name,'Linear X',x,y,span,wavelength_start,wavelength_stop,frequency_points)

def read_monitor_data_inventory(fdtd,name:str)->dict[str,Any]:
    def names(value):
        if isinstance(value,str): return ';'.join(x.strip() for x in value.replace('\r','').split('\n') if x.strip())
        return ';'.join(map(str,value))
    return {'monitor':name,'data_names':names(fdtd.getdata(name)),'result_names':names(fdtd.getresult(name))}

def _available(fdtd,name,field):
    try:return np.asarray(fdtd.getdata(name,field)).squeeze()
    except Exception:return None

def read_fields(fdtd,name):
    return {k:_available(fdtd,name,k) for k in ('x','y','Ex','Ey','Ez','Hx','Hy','Hz')}

def integrate_line_poynting_flux(fields:dict[str,Any],orientation:str)->float:
    def z(name):
        value=fields.get(name);return 0 if value is None else value
    if orientation=='Linear X':
        coord=np.asarray(fields['x']).squeeze();p=.5*np.real(z('Ez')*np.conj(z('Hx'))-z('Ex')*np.conj(z('Hz')))
    elif orientation=='Linear Y':
        coord=np.asarray(fields['y']).squeeze();p=.5*np.real(z('Ey')*np.conj(z('Hz'))-z('Ez')*np.conj(z('Hy')))
    else:raise ValueError(orientation)
    value=np.asarray(p).squeeze();coord=np.asarray(coord).squeeze();axes=[n for n,size in enumerate(value.shape) if size==coord.size]
    if not axes:raise ValueError(f'coordinate_length_{coord.size}_not_in_field_shape_{value.shape}')
    integrated=np.trapezoid(value,coord,axis=axes[0]);return float(integrated) if np.ndim(integrated)==0 else np.asarray(integrated).squeeze()

def calculate_box_outward_flux(side:dict[str,Any])->dict[str,Any]:
    out={'right_out':side['right'],'left_out':-side['left'],'top_out':side['top'],'bottom_out':-side['bottom']}
    out['net_outward']=sum(out.values());return out

def read_reference_plane_flux(fdtd,name='reference_y0'):
    return integrate_line_poynting_flux(read_fields(fdtd,name),'Linear X')

def geometry_hash(value:Any)->str:return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

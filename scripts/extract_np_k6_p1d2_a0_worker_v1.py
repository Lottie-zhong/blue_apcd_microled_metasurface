import hashlib,json,os,sys
from pathlib import Path
import lumapi,numpy as np
p=Path(sys.argv[1]);q=Path(sys.argv[2]);case=sys.argv[3];dia=None if sys.argv[4]=="blank" else int(sys.argv[4])
def h(x):return hashlib.sha256(x.read_bytes()).hexdigest()
f=lumapi.FDTD(str(p),hide=True)
try:
 d=f.getresult("transmission_monitor","E");ex=f.getdata("transmission_monitor","Ex");x=np.squeeze(np.asarray(d["x"],float));y=np.squeeze(np.asarray(d["y"],float));z=np.squeeze(np.asarray(d["z"],float));la=np.squeeze(np.asarray(d["lambda"],float))*1e9;a=np.squeeze(np.asarray(ex,dtype=np.complex128));shape=a.shape;maps=[]
 for ax in range(3):
  for ay in range(3):
   if ax!=ay:
    af=next(k for k in range(3) if k not in {ax,ay})
    if shape[ax]==len(x) and shape[ay]==len(y) and shape[af]==11:maps.append((ax,ay,af))
 if len(maps)!=1:
  raw_shape=np.asarray(ex).shape
  if len(raw_shape)==4 and raw_shape[2]==1 and raw_shape[0]==len(x) and raw_shape[1]==len(y) and raw_shape[3]==11:maps=[(0,1,2)]
  else:raise RuntimeError(str({"shape":shape,"raw_shape":raw_shape,"maps":maps}))
 a=np.moveaxis(a,maps[0],(0,1,2));area=(x[-1]-x[0])*(y[-1]-y[0]);a0=np.trapz(np.trapz(a,x,axis=0),y,axis=0)/area;out={"case_id":case,"diameter_nm":dia,"post_fsp_path":str(p),"post_fsp_sha256":h(p),"monitor_name":"transmission_monitor","reference_z_nm":float(z.reshape(-1)[0]*1e9),"source_shape":list(np.asarray(ex).shape),"normalized_axis_mapping":{"x_y_frequency_axes":list(maps[0])},"dtype":str(np.asarray(ex).dtype),"complex":bool(np.iscomplexobj(ex)),"x_count":len(x),"y_count":len(y),"x_min_nm":float(x.min()*1e9),"x_max_nm":float(x.max()*1e9),"y_min_nm":float(y.min()*1e9),"y_max_nm":float(y.max()*1e9),"integrated_area_nm2":float(area*1e18),"wavelengths_nm":[float(v) for v in la],"A0_real":[float(v.real) for v in a0],"A0_imag":[float(v.imag) for v in a0],"extraction_status":"pass","readonly":True}
finally:f.close()
q.parent.mkdir(parents=True,exist_ok=True);t=q.with_suffix(".tmp");t.write_text(json.dumps(out,indent=2));os.replace(t,q)

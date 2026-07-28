import csv,json,hashlib,cmath,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d4_k6x_candidate_freeze_v1';P=R/'outputs/np_k6_p1d4_k6x_execution_package_v1';L=R/'outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv'
def w(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def main():
 cs=json.loads((O/'selected_k6x_candidates.json').read_text())['candidates'];lib=list(csv.DictReader(L.open())); by={}
 for r in lib:by.setdefault((int(r['diameter_nm']),int(r['wavelength_nm'])),r)
 bridge={'orientation_status':'resolved_by_official_grating_equation_and_discrete_fourier_bridge','monitor_plane':'XY','gratingn_axis':'x','gratingu1_axis':'u_x','grating_equation':'k_x(n)=k_x,in+n*2pi/Lambda_x; k_y(m)=k_y,in+m*2pi/Lambda_y','normal_incidence_result':'k_x,in=k_y,in=0, so n=+1 implies k_x>0 and u_x>0','target_gratingn':1,'target_u_x_sign':'positive','target_physical_direction':'+x','official_sources':[{'title':'Ansys Lumerical FDTD grating projections documentation','url':'https://optics.ansys.com/hc/en-us/articles/360034382554-grating-projections','accessed':'2026-07-28','excerpt':'gratingn and gratingu1 identify x order and x direction cosine for an XY monitor.'}]}
 w(O/'grating_sign_bridge.json',bridge);w(O/'orientation_sign_convention_contract.json',bridge)
 mappings=[];proxy=[]
 for c in cs:
  d=c['ordered_diameters_nm']; pos=[-725,-435,-145,145,435,725]; rows=[]
  for j,(D,x) in enumerate(zip(d,pos)):
   r=by[D,450];z=complex(float(r['txx_real']),float(r['txx_imag']));ph=math.degrees(cmath.phase(z)); common=math.degrees(cmath.phase(complex(float(by[d[0],450]['txx_real']),float(by[d[0],450]['txx_imag'])))); rel=(ph-common)%360; ideal=60*j;err=((rel-ideal+180)%360)-180
   rows.append({'phase_bin_index':j,'diameter_nm':D,'x_position_nm':x,'wrapped_phase_450_deg':ph,'common_phase_removed_deg':rel,'ideal_phase_deg':ideal,'phase_error_deg':err,'complex_txx_450':[z.real,z.imag],'physical_x_order':j,'target_grating_order':1})
  oh=h(rows);mir=h(list(reversed(rows)));mappings.append({'candidate_id':c['candidate_id'],'rows':rows,'ordered_geometry_hash':oh,'mirror_geometry_hash':mir,'phase_order_hash':h([r['phase_bin_index'] for r in rows]),'position_diameter_mapping_hash':h([(r['x_position_nm'],r['diameter_nm']) for r in rows])})
  spectra=[]
  for lam in range(445,456):
   t=[complex(float(by[D,lam]['txx_real']),float(by[D,lam]['txx_imag'])) for D in d]; powers={n:abs(sum(t[j]*cmath.exp(-2j*math.pi*n*j/6) for j in range(6)))**2 for n in range(-3,4)};total=sum(powers.values());dom=max(powers,key=powers.get);spectra.append({'wavelength_nm':lam,'proxy_power_by_order':powers,'normalized_proxy_fraction':{str(n):v/total for n,v in powers.items()},'dominant_proxy_order':dom})
  f=[x['normalized_proxy_fraction']['1'] for x in spectra];p450=spectra[5]['normalized_proxy_fraction'];proxy.append({'candidate_id':c['candidate_id'],'label':'LOCAL_PERIOD_DFT_PROXY','spectra':spectra,'proxy_plus1_band_min':min(f),'proxy_plus1_band_mean':sum(f)/len(f),'proxy_plus1_band_variation':max(f)-min(f),'proxy_dominant_order_450':spectra[5]['dominant_proxy_order'],'proxy_plus1_fraction_450':p450['1'],'proxy_plus1_to_minus1_ratio_450':p450['1']/p450['-1']})
 w(O/'phase_bin_mapping.json',{'x_positions_nm':[-725,-435,-145,145,435,725],'phase_bin_order':[0,1,2,3,4,5],'mappings':mappings});w(O/'local_period_dft_proxy.json',{'label':'LOCAL_PERIOD_DFT_PROXY','not_full_wave':True,'candidates':proxy})
 g=json.loads((P/'geometry_contract.json').read_text());g['phase_mappings']=mappings;w(P/'geometry_contract.json',g)
 e=json.loads((P/'execution_contract.json').read_text());e['status']=bridge['orientation_status'];e['solver_entered']=0;w(P/'execution_contract.json',e)
 q=json.loads((P/'preflight_manifest.json').read_text());q['orientation_status']=bridge['orientation_status'];q['ready_for_solver']=True;w(P/'preflight_manifest.json',q)
if __name__=='__main__':main()
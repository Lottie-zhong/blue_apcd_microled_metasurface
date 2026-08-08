import json, math
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')

def wang(psi,chi):
    p=math.radians(psi-45); q=math.radians(45-psi)
    cp,sp,cq,sq=math.cos(p),math.sin(p),math.cos(q),math.sin(q)
    e1=complex(math.cos(math.radians(-2*chi)),math.sin(math.radians(-2*chi)))
    e2=complex(math.cos(math.radians(2*chi)),math.sin(math.radians(2*chi)))
    R1=[[cp,-sp],[sp,cp]]; R2=[[cq,-sq],[sq,cq]]; B=[[.5*e1,.5],[.5,.5*e2]]
    def mm(a,b): return [[sum(a[i][k]*b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]
    return mm(mm(R1,B),R2)

def main():
    z=wang(0,0); target=[[1+0j,0j],[0j,0j]]
    err=max(abs(z[i][j]-target[i][j]) for i in range(2) for j in range(2))
    out={'formula':'0.5 R(psi-45) [[exp(-2 i chi),1],[1,exp(+2 i chi)]] R(45-psi)','psi_deg':0,'chi_deg':0,
      'matrix_Re':[[z[i][j].real for j in range(2)] for i in range(2)],'matrix_Im':[[z[i][j].imag for j in range(2)] for i in range(2)],
      'max_abs_error':err,'tolerance':1e-12,'x_pass':[[z[0][0].real,z[0][0].imag],[z[1][0].real,z[1][0].imag]],'y_block':[[z[0][1].real,z[0][1].imag],[z[1][1].real,z[1][1].imag]],'rank':1,'singular_values':[1,0],'pass':err<=1e-12}
    p=ROOT/'outputs/lp_ml_dataset_v1/analysis/lp_ml_inverse_stage1_wang_eq5_derivation_v1.json'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__': main()

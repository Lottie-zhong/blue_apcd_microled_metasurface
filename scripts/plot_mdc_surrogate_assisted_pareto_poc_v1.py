"""Nature-style Python-only figures for the surrogate Pareto POC.

Reads only the POC candidate summary/front and writes lightweight projections.
No torch, model, solver, or external/test data is imported.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial","DejaVu Sans"],"font.size":8,"axes.linewidth":0.7,"axes.spines.top":False,"axes.spines.right":False,"svg.fonttype":"none","pdf.fonttype":42})
import matplotlib.pyplot as plt

def main(run: Path):
    s=pd.read_csv(run/"candidate_summary.csv"); p=pd.read_csv(run/"pareto_front.csv")
    q=json.loads((run/"proposed_fdtd_shortlist.json").read_text(encoding="utf-8")); ids={x["geometry_id"] for x in q.get("candidates",[])}
    sh=s[s.geometry_id.astype(str).isin(ids)]
    colors={"Explicit":"#4C78A8","ZL-1":"#59A14F","ZL-2":"#B279A2"}
    c=s[s.is_traditional_champion.astype(bool)]
    def save(fig,stem):
        for ext,kw in [("png",{"dpi":600}),("pdf",{}),("svg",{})]: fig.savefig(run/(stem+"."+ext),bbox_inches="tight",**kw)
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(3.8,3.2))
    for t,g in s.groupby("topology_family"): ax.scatter(g.spectral_fwhm_nm,g.angular_fwhm_deg,s=7,alpha=.16,color=colors[t],label=t,rasterized=True)
    ax.scatter(p.spectral_fwhm_nm,p.angular_fwhm_deg,s=15,facecolors="none",edgecolors="#1F1F1F",linewidths=.5,label="Pareto")
    ax.scatter(c.spectral_fwhm_nm,c.angular_fwhm_deg,marker="*",s=85,color="#D62728",edgecolor="white",linewidth=.5,label="Traditional champion",zorder=5)
    if len(sh): ax.scatter(sh.spectral_fwhm_nm,sh.angular_fwhm_deg,marker="D",s=26,color="#F28E2B",edgecolor="white",label="Shortlist",zorder=5)
    ax.set(xlabel="Spectral FWHM (nm)",ylabel="Angular FWHM (deg)"); ax.legend(frameon=False,fontsize=6); fig.tight_layout(); save(fig,"figure_A_pareto_projection")
    fig,ax=plt.subplots(figsize=(3.8,3.2)); ax.scatter(s.spectral_peak_detuning_nm,s.angular_peak_detuning_deg,s=7,alpha=.17,c=[colors[t] for t in s.topology_family],rasterized=True); ax.scatter(p.spectral_peak_detuning_nm,p.angular_peak_detuning_deg,s=15,facecolors="none",edgecolors="#1F1F1F",linewidths=.5); ax.scatter(c.spectral_peak_detuning_nm,c.angular_peak_detuning_deg,marker="*",s=85,color="#D62728",edgecolor="white",linewidth=.5,zorder=5)
    if len(sh): ax.scatter(sh.spectral_peak_detuning_nm,sh.angular_peak_detuning_deg,marker="D",s=26,color="#F28E2B",edgecolor="white",zorder=5)
    ax.set(xlabel="|Peak wavelength − target| (nm)",ylabel="|Peak angle − target| (deg)"); fig.tight_layout(); save(fig,"figure_B_peak_detuning_projection")
    cols=["spectral_fwhm_nm","angular_fwhm_deg","spectral_peak_detuning_nm","angular_peak_detuning_deg"]; vals=s[cols].to_numpy(float); lo,hi=vals.min(0),vals.max(0); norm=(vals-lo)/np.maximum(hi-lo,1e-12); fig,ax=plt.subplots(figsize=(5,3.2)); xx=np.arange(4)
    for i in np.linspace(0,len(s)-1,min(180,len(s)),dtype=int): ax.plot(xx,norm[i],color="#BDBDBD",alpha=.12,lw=.5)
    ci=int(c.index[0]); ax.plot(xx,norm[ci],color="#D62728",lw=2,label="Traditional champion")
    for i in sh.index[:5]: ax.plot(xx,norm[int(i)],color="#F28E2B",lw=1.4)
    ax.set_xticks(xx,["Spec.\nwidth","Ang.\nwidth","λ detune","θ detune"]); ax.set_ylabel("Within-domain normalized objective"); ax.set_ylim(-.03,1.03); fig.tight_layout(); save(fig,"figure_C_parallel_objectives")
    return [str(x) for x in sorted(run.glob("figure_*.*"))]
if __name__=="__main__": print(json.dumps(main(Path(sys.argv[1])),ensure_ascii=False))

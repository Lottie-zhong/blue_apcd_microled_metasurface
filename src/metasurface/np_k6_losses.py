import numpy as np
def huber(pred,target,delta=1.0):
    e=np.asarray(pred)-np.asarray(target); a=np.abs(e); return float(np.mean(np.where(a<=delta,.5*e*e,delta*(a-.5*delta))))
def structured_loss(pred,target,weights=None):
    w={"order":1.0,"TR":1.0,"target":1.0,"physics":1.0,"complex":0.0}; w.update(weights or {})
    lo=huber(pred["eta_t_order"],target["eta_t_order"])+huber(pred["eta_r_order"],target["eta_r_order"])
    ltr=huber(pred["T"],target["T"])+huber(pred["R"],target["R"])
    idx=list(pred["order_ids"]).index(1); lt=huber(pred["eta_t_order"][:,idx],target["eta_t_order"][:,idx])
    closure=np.maximum(0,np.abs(1-pred["T"]-pred["R"])-.02).mean()
    return {"total":w["order"]*lo+w["TR"]*ltr+w["target"]*lt+w["physics"]*closure,"order":lo,"TR":ltr,"target":lt,"physics":float(closure),"complex":0.0}


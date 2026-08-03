import numpy as np
def _sigmoid(x): return 1/(1+np.exp(-np.clip(x,-40,40)))
def _softmax(x):
    z=x-np.max(x,axis=-1,keepdims=True); e=np.exp(z); return e/e.sum(axis=-1,keepdims=True)
class CircularCNNContextConditioned:
    """Small deterministic numpy reference model for dry-run and contract tests."""
    def __init__(self,in_channels=7,context_dim=4,hidden_channels=32,seed=0,order_ids=None):
        self.in_channels=in_channels; self.context_dim=context_dim; self.hidden_channels=hidden_channels; self.order_ids=np.array(order_ids if order_ids is not None else [-3,-2,-1,0,1,2,3])
        rng=np.random.default_rng(seed); self.w=[]; self.b=[]; c=in_channels
        for _ in range(3): self.w.append(rng.normal(0,.08,(hidden_channels,c,3))); self.b.append(np.zeros(hidden_channels)); c=hidden_channels
        self.ctx=rng.normal(0,.08,(context_dim,hidden_channels)); self.t=rng.normal(0,.08,(hidden_channels,len(self.order_ids))); self.r=rng.normal(0,.08,(hidden_channels,len(self.order_ids))); self.tr=rng.normal(0,.08,(hidden_channels,2))
    def _conv(self,x,w,b):
        return sum(np.roll(x,j,axis=1)@w[:,:,j].T for j in range(3))+b
    def forward(self,node_features,context):
        x=np.asarray(node_features,float); c=np.asarray(context,float); assert x.ndim==3 and x.shape[1]==6 and c.ndim==2
        h=x
        for w,b in zip(self.w,self.b): h=np.tanh(self._conv(h,w,b))
        pooled=h.mean(axis=1)+c@self.ctx; tr=_sigmoid(pooled@self.tr); T=tr[:,0]; R=tr[:,1]*(1-T)
        tf=_softmax(pooled@self.t); rf=_softmax(pooled@self.r)
        return {"T":T,"R":R,"eta_t_order":T[:,None]*tf,"eta_r_order":R[:,None]*rf,"order_ids":self.order_ids.copy(),"closure":T+R,"directionality":tf[:,self.order_ids.tolist().index(1)]}


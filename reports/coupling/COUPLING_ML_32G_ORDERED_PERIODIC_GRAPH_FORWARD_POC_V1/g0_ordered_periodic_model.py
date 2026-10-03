"""Independent APCD ordered periodic graph encoder for G0; no external graph package."""
import numpy as np
import torch
from torch import nn

SLOTS = 6
PITCH_NM = 290.0
LAMBDA_X_NM = 1740.0
X_NM = np.array([-725., -435., -145., 145., 435., 725.])
HIDDEN = 4


def parameter_budget(hidden=HIDDEN):
    graph_encoder = (2*hidden+hidden) + 3*2*(hidden+2+1)*hidden + 3*(hidden+1)*hidden + (6*hidden+1)*32
    heads = 7*(32*2+2)
    fusion = (14*32+32) + (32*14+14)
    return {"graph_encoder": graph_encoder, "heads": heads, "fusion": fusion, "total": graph_encoder+heads+fusion}


def periodic_edges():
    x = X_NM
    left, right = [], []
    for i in range(SLOTS):
        li, ri = (i-1) % SLOTS, (i+1) % SLOTS
        ls, rs = (-1 if i == 0 else 0), (1 if i == SLOTS-1 else 0)
        left.append([((x[li] + ls*LAMBDA_X_NM - x[i])/LAMBDA_X_NM), ls])
        right.append([((x[ri] + rs*LAMBDA_X_NM - x[i])/LAMBDA_X_NM), rs])
    return np.asarray(left, np.float32), np.asarray(right, np.float32)


class OrderedPeriodicG0(nn.Module):
    """Shared directional ring updates, then physical-slot ordered readout."""
    def __init__(self, hidden=HIDDEN):
        super().__init__()
        self.hidden = hidden
        self.node_embed = nn.Linear(2, hidden)
        self.left = nn.ModuleList([nn.Linear(hidden+2, hidden) for _ in range(3)])
        self.right = nn.ModuleList([nn.Linear(hidden+2, hidden) for _ in range(3)])
        self.self_update = nn.ModuleList([nn.Linear(hidden, hidden) for _ in range(3)])
        self.readout = nn.Linear(SLOTS*hidden, 32)
        self.heads = nn.ModuleList([nn.Linear(32, 2) for _ in range(7)])
        self.fuse = nn.Sequential(nn.Linear(14, 32), nn.ReLU(), nn.Linear(32, 14))
        le, re = periodic_edges()
        self.register_buffer("edge_left", torch.as_tensor(le))
        self.register_buffer("edge_right", torch.as_tensor(re))

    def forward(self, node_features, slot_ids=None, left_scale=1.0, right_scale=1.0):
        if node_features.ndim != 3 or node_features.shape[1:] != (SLOTS, 2):
            raise ValueError("node_features must have shape [batch,6,2]")
        if slot_ids is None:
            slot_ids = torch.arange(SLOTS, device=node_features.device).expand(node_features.shape[0], -1)
        if slot_ids.shape != node_features.shape[:2]:
            raise ValueError("slot_ids must have shape [batch,6]")
        if any(not torch.equal(torch.sort(row).values, torch.arange(SLOTS, device=row.device)) for row in slot_ids):
            raise ValueError("slot_ids must be a permutation of physical slots 0..5")
        h = torch.relu(self.node_embed(node_features))
        # Convert arbitrary node indexing to physical slots; no diameter sorting occurs.
        order = torch.argsort(slot_ids, dim=1)
        for lnet, rnet, snet in zip(self.left, self.right, self.self_update):
            hp = h.gather(1, order.unsqueeze(-1).expand(-1, -1, self.hidden))
            lm = torch.cat([torch.roll(hp, 1, 1), self.edge_left.expand(hp.shape[0], -1, -1)], -1)
            rm = torch.cat([torch.roll(hp, -1, 1), self.edge_right.expand(hp.shape[0], -1, -1)], -1)
            hnew = torch.relu(snet(hp) + left_scale*lnet(lm) + right_scale*rnet(rm))
            h = hnew.gather(1, torch.argsort(order, dim=1).unsqueeze(-1).expand(-1, -1, self.hidden))
        hp = h.gather(1, order.unsqueeze(-1).expand(-1, -1, self.hidden))
        q = torch.relu(self.readout(hp.reshape(hp.shape[0], -1)))
        local = torch.cat([head(q) for head in self.heads], dim=1)
        return local + self.fuse(local)


def node_features(scaled_diameters):
    d = np.asarray(scaled_diameters, dtype=np.float32)
    if d.ndim != 2 or d.shape[1] != SLOTS:
        raise ValueError("diameters must have shape [n,6]")
    pos = np.broadcast_to((X_NM/LAMBDA_X_NM).astype(np.float32), d.shape)
    return np.stack([d, pos], axis=-1).astype(np.float32)


def deterministic_test_weights(model):
    with torch.no_grad():
        for j, p in enumerate(model.parameters()):
            v = torch.arange(p.numel(), dtype=p.dtype, device=p.device).reshape(p.shape)
            p.copy_(0.03 + 0.0001*j + 0.00001*v)


def preflight():
    assert parameter_budget(4) == {"graph_encoder":1040,"heads":462,"fusion":942,"total":2444}
    assert parameter_budget(5)["total"] > 2684 and parameter_budget(4)["total"] <= 2684
    le, re = periodic_edges()
    assert le.shape == re.shape == (6,2) and np.allclose(le[:,0],-290/1740) and np.allclose(re[:,0],290/1740)
    assert np.array_equal(le[:,1],[-1,0,0,0,0,0]) and np.array_equal(re[:,1],[0,0,0,0,0,1])
    # Three ring rounds give every slot a path to all six physical slots.
    reach = np.eye(6, dtype=bool)
    adj = np.zeros((6,6),bool)
    for i in range(6): adj[i,(i-1)%6]=adj[i,(i+1)%6]=True
    for _ in range(3): reach = reach | (reach.astype(int) @ adj.astype(int) > 0)
    assert reach.all()
    m = OrderedPeriodicG0().cpu(); assert sum(p.numel() for p in m.parameters()) == 2444
    deterministic_test_weights(m)
    d = torch.tensor([[[.2,-.4,.1,.7,-.2,.5]]],dtype=torch.float32).reshape(1,6).requires_grad_(True)
    nf = torch.tensor(node_features(d.detach().numpy().copy()), requires_grad=True)
    sid = torch.arange(6).reshape(1,6)
    y = m(nf,sid); assert y.shape == (1,14) and torch.isfinite(y).all()
    grad = torch.autograd.grad((y*y).sum(),nf)[0]
    assert torch.all(torch.isfinite(grad)) and torch.all(torch.abs(grad[0,:,0]) > 1e-12)
    perm = torch.tensor([3,0,5,2,1,4]); relabel = m(nf[:,perm],sid[:,perm])
    assert torch.allclose(y,relabel,atol=1e-6,rtol=1e-6)
    shifted = nf[:,torch.roll(torch.arange(6),1)]
    assert torch.max(torch.abs(y-m(shifted,sid))).item() > 1e-7
    assert torch.max(torch.abs(y-m(nf,sid,left_scale=0.0))).item() > 1e-7
    assert torch.max(torch.abs(y-m(nf,sid,right_scale=0.0))).item() > 1e-7
    # Boundary image features are consumed by the learned edge maps.
    before = m.edge_left.clone()
    with torch.no_grad(): m.edge_left[0,1] += 0.5
    edge_changed = m(nf,sid)
    with torch.no_grad(): m.edge_left.copy_(before)
    assert torch.max(torch.abs(y-edge_changed)).item() > 1e-7
    return {"status":"PASS","parameter_count":sum(p.numel() for p in m.parameters()),"budget":parameter_budget(),"edge_left":le.tolist(),"edge_right":re.tolist(),"all_six_diameter_gradients_nonzero":True,"index_relabel_invariant_after_physical_readout":True,"cyclic_diameter_shift_remains_position_sensitive":True,"left_right_messages_and_periodic_image_shift_affect_output":True,"three_round_ring_reachability_all_pairs":bool(reach.all())}

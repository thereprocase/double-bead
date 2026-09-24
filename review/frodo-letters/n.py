from _lib import *
from beadjoint.latin import _zigzag_n

def N_edge(W):
    """Stems at the edges, diagonal whose outer edges land exactly on the outer corners (0,-4), (W,10)."""
    x1 = W - 1
    return S((1, 10), (1, -4)) | S((x1, -4), (x1, 10)) | edge_diag(0, -4, W, 10, side_a=+1, side_b=-1)

def N_ctr(W):
    x1 = W - 1
    return S((1, 10), (1, -4)) | S((x1, -4), (x1, 10)) | diagonal(1, -3.5, x1, 9.5)

cand = {
    "N zigzag (now)": _zigzag_n(),
    "N ctr 9": N_ctr(9),
    "N edge 8": N_edge(8),
    "N edge 8.5": N_edge(8.5),
    "N edge 9": N_edge(9),
}
sheet(cand, "n.png", refs="HU", cols=7, scale=14, cell=(14, 20))

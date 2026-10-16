"""Form-finding for the tensile fabric cones upstairs (numpy only, no bpy): the force density method.

A membrane in tension, with no load, settles where every free node is in balance with its neighbours: for each free
node i, sum over its edges of q_ij (x_j - x_i) = 0, with q the force per unit length on that edge. That is linear in
the positions, so the shape follows from the fixed nodes and the q's in one solve. Here the net is a polar grid from a
rigid hoop (row 0, fixed) out to the rim (row nt): the rim's nodes at the corners are fixed where the fabric is pulled
up onto the structure, the rest of the rim is a free edge with a cable in it. Three knobs:
  q_hoop   force density along the rings (meridians are 1): 0 gives straight flanks from the hoop to the rim, more
           draws the rings in towards the axis, so the flanks curve into a trumpet that flares only near the top
  q_cable  force density in the free edge's cable: high keeps the edge a shallow arc between two corners, low lets it
           sag deep towards the hoop (the scallops between the points)
  row_bias the rings' q grows by this factor per row towards the rim (> 1 keeps the throat slender and lets the top
           open out)
"""
import math

import numpy as np


def solve(hoop_c, hoop_z, hoop_r, corners, nr=160, nt=30, q_hoop=1.0, q_cable=6.0, row_bias=1.0, iters=4000):
    """hoop_c (x, y), hoop_z, hoop_r: the hoop; corners: [(x, y, z)] in order of heading round the axis (counter-
    clockwise), each fixed on the rim's node nearest its heading. Returns an (nt + 1, nr, 3) array of node positions."""
    nk = len(corners)
    cx, cy = hoop_c
    cj = []
    for c in corners:
        j = round(math.atan2(c[1] - cy, c[0] - cx) % (2 * math.pi) / (2 * math.pi) * nr) % nr
        cj.append(j if j not in cj else (j + 1) % nr)
    order = sorted(range(nk), key=lambda k: cj[k])
    corners, cj = [corners[k] for k in order], [cj[k] for k in order]
    n = (nt + 1) * nr
    idx = lambda i, j: i * nr + j % nr
    fixed = np.zeros(n, bool)
    X = np.zeros((n, 3))
    for j in range(nr):
        th = 2 * math.pi * j / nr
        X[idx(0, j)] = (cx + hoop_r * math.cos(th), cy + hoop_r * math.sin(th), hoop_z)
        fixed[idx(0, j)] = True
    for c, j in zip(corners, cj):
        X[idx(nt, j)] = c
        fixed[idx(nt, j)] = True
    a, b, q = [], [], []
    for i in range(nt + 1):
        for j in range(nr):
            if i < nt:                                            # meridian
                a.append(idx(i, j)); b.append(idx(i + 1, j)); q.append(1.0)
            if i > 0:                                             # ring (the rim's ring is the cable)
                a.append(idx(i, j)); b.append(idx(i, j + 1))
                q.append(q_cable if i == nt else q_hoop * row_bias ** i)
    a, b, q = np.array(a), np.array(b), np.array(q)
    # initial guess (only speeds up the solve): each meridian straight from the hoop to the rim, the rim interpolated
    # between corners
    for j in range(nr):
        k = max((k for k in range(nk) if cj[k] <= j), default=nk - 1)
        span = (cj[(k + 1) % nk] - cj[k]) % nr or nr
        w = ((j - cj[k]) % nr) / span
        c0, c1 = np.array(corners[k]), np.array(corners[(k + 1) % nk])
        rim = c0 * (1 - w) + c1 * w
        h = X[idx(0, j)]
        for i in range(1, nt + 1):
            if not fixed[idx(i, j)]:
                X[idx(i, j)] = h + (rim - h) * i / nt
    # conjugate gradients on the free nodes: A x = rhs, A = the weighted graph Laplacian restricted to them
    free = ~fixed
    deg = np.zeros(n)
    np.add.at(deg, a, q)
    np.add.at(deg, b, q)

    def lap(V):                                                   # (L V) for all nodes, V (n, 3)
        out = deg[:, None] * V
        np.add.at(out, a, -q[:, None] * V[b])
        np.add.at(out, b, -q[:, None] * V[a])
        return out

    Xf = np.where(free[:, None], 0.0, X)
    rhs = -lap(Xf)                                                # the fixed nodes' pull on the free ones
    rhs[~free] = 0
    x = np.where(free[:, None], X, 0.0)

    def A(V):
        r = lap(np.where(free[:, None], V, 0.0))
        r[~free] = 0
        return r

    r = rhs - A(x)
    p = r.copy()
    rs = (r * r).sum(0)
    for _ in range(iters):
        Ap = A(p)
        alpha = rs / np.maximum((p * Ap).sum(0), 1e-30)
        x += alpha * p
        r -= alpha * Ap
        rs_new = (r * r).sum(0)
        if rs_new.max() < 1e-20:
            break
        p = r + (rs_new / np.maximum(rs, 1e-30)) * p
        rs = rs_new
    X = np.where(free[:, None], x, X)
    return X.reshape(nt + 1, nr, 3)

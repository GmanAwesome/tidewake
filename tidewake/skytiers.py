"""Generator v6: stacked sky tiers.

The main terrain is one island per column. These tiers add floating islands at
fixed altitude bands all the way up to ~480, on their own jittered grids, so
several islands can sit above one another. Wherever you stand there is usually
something hanging overhead, and the fog makes the stack read as endless.

Each tier island is skipped column by column wherever it would come within a
few layers of anything already solid, so tiers never fuse with the land below.
"""
import numpy as np

from .config import CHUNK, LAYERS, HEX, SQ3
from .materials import ID as M
from .noise import rand01

TOP_CAP = LAYERS - 20          # 480
CLEAR = 5                      # air kept above and below every tier island
# (grid period in cells, accept chance, radius range as a share of the period, altitude band, seed offset)
# Stacked layers by size class. Every layer spreads its islands evenly over the whole
# column (about the cloud sea up to ~480), so at any height there is a mix of sizes
# above and below. The main terrain (continents, large, medium, small, skerries) is
# layer 0; these add more of each size class on top of it.
# (size class, grid period in world units, accept chance, radius share of the period, seed offset)
TIERS = (
    ('large', 620.0, 0.30, (0.16, 0.24), 301),
    ('medium', 300.0, 0.42, (0.14, 0.24), 311),
    ('medium', 260.0, 0.42, (0.14, 0.24), 316),
    ('small', 150.0, 0.50, (0.12, 0.22), 321),
    ('small', 130.0, 0.50, (0.12, 0.22), 326),
    ('small', 115.0, 0.50, (0.12, 0.22), 331),
    ('tiny', 60.0, 0.40, (0.07, 0.14), 341),
    ('tiny', 48.0, 0.40, (0.07, 0.14), 346),
    ('tiny', 40.0, 0.40, (0.07, 0.14), 351),
)
ALT_LO, ALT_HI = 40.0, 470.0
DEPTH_MAX = 70.0
SIZE_EDGES = (15.0, 40.0, 100.0, 250.0)   # world-unit radius: tiny < 15 <= small < 40 <= medium < 100 <= large < 250 <= huge


def size_class(rad):
    return ('tiny', 'small', 'medium', 'large', 'huge')[int(np.searchsorted(SIZE_EDGES, rad, side='right'))]


def _cand(gen, ti, ci, cj):
    """Island candidate of tier ti at grid cell (ci, cj), or None (scalar, deterministic)."""
    _, period, accept, (rmin, rmax), off = TIERS[ti]
    A, B = np.array([ci]), np.array([cj])
    if rand01(A, B, gen.h + off)[0] >= accept:
        return None
    px = (ci + 0.5 + (rand01(A, B, gen.h + off + 1)[0] - 0.5) * 0.5) * period
    pz = (cj + 0.5 + (rand01(A, B, gen.h + off + 2)[0] - 0.5) * 0.5) * period
    rad = period * (rmin + (rmax - rmin) * rand01(A, B, gen.h + off + 3)[0])
    alt = ALT_LO + (ALT_HI - ALT_LO) * rand01(A, B, gen.h + off + 4)[0]
    depth = 2.0 + min(DEPTH_MAX, rad * 0.55) * 1.15
    return (px, pz, rad, alt, depth)


_ACC = {}


def accepted(gen, ti, ci, cj):
    """The candidate if it survives: clear of the main terrain and of every accepted island
    of the earlier layers (horizontal overlap + vertical slabs with clearance). Cached."""
    key = (gen.h, ti, ci, cj)
    if key in _ACC:
        return _ACC[key]
    c = _cand(gen, ti, ci, cj)
    res = None
    if c is not None:
        px, pz, rad, alt, depth = c
        ok = _island_ok(gen, TIERS[ti][4], ci, cj, px, pz, rad, alt, depth)
        if ok:
            lo, hi = alt - depth - CLEAR, alt + 8 + CLEAR + TREE_ROOM
            for tj in range(ti):
                pj = TIERS[tj][1]
                reach = rad + TIERS[tj][3][1] * pj + 0.25 * pj + 4.0
                for a in range(int(np.floor((px - reach) / pj)), int(np.floor((px + reach) / pj)) + 1):
                    for b in range(int(np.floor((pz - reach) / pj)), int(np.floor((pz + reach) / pj)) + 1):
                        o = accepted(gen, tj, a, b)
                        if o is None:
                            continue
                        ox, oz, orad, oalt, odep = o
                        if np.hypot(ox - px, oz - pz) > rad + orad + 3.0:
                            continue
                        if oalt - odep - CLEAR <= hi and oalt + 8 + CLEAR + TREE_ROOM >= lo:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
        res = c if ok else None
    if len(_ACC) > 200000:
        _ACC.clear()
    _ACC[key] = res
    return res


TREE_ROOM = 16                 # trees and structures on the land below
_OK = {}


def _island_ok(gen, off, ci, cj, px, pz, rad, alt, depth_max):
    """Reject a whole tier island if the main terrain (plus room for its trees and the tier's
    own tapered tail) reaches into its altitude slab anywhere under its footprint. Analytic, so
    every chunk agrees and no island is ever cut in half."""
    key = (gen.h, off, ci, cj)
    v = _OK.get(key)
    if v is not None:
        return v
    pts = [(0.0, 0.0)]
    for ring in (0.45, 0.8, 1.05):
        for a in range(10):
            ang = a * np.pi / 5 + ring
            pts.append((np.cos(ang) * ring, np.sin(ang) * ring))
    X = np.array([px + rad * u for u, _ in pts])
    Z = np.array([pz + rad * w for _, w in pts])
    rr = Z / (HEX * 1.5)
    qq = X / (HEX * SQ3) - rr * 0.5
    c = gen.columns(np.round(qq).astype(np.int64), np.round(rr).astype(np.int64))
    lo = alt - depth_max - CLEAR
    hi = alt + 8 + CLEAR
    land = c['land']
    clash = land & (c['top'] + TREE_ROOM >= lo) & (c['bottom'] - CLEAR <= hi)
    v = not bool(clash.any())
    if len(_OK) > 20000:
        _OK.clear()
    _OK[key] = v
    return v


_SNOWY = (3, 14, 18)           # frostglass, cloudstep, azure
_SANDY = (6, 19)               # duneglass, golden steppe


def _realm_surface(realm):
    if realm in _SNOWY:
        return M['snow'], M['pale_stone'], M['pale_stone']
    if realm in _SANDY:
        return M['sand'], M['sandstone'], M['sandstone']
    if realm == 12:
        return M['chalk'], M['chalk'], M['chalk']
    if realm in (11, 4):
        return M['turf'], M['loam'], M['basalt']
    if realm == 13:
        return M['turf'], M['starstone'], M['starstone']
    return M['turf'], M['loam'], M['stone']


def stamp(gen, cq, cr, cells, meta=None):
    """Add tier islands to a freshly generated chunk. Returns cells placed."""
    q0, r0 = cq * CHUNK, cr * CHUNK
    qs = np.arange(q0, q0 + CHUNK, dtype=np.int64)
    rs = np.arange(r0, r0 + CHUNK, dtype=np.int64)
    Q, R = np.meshgrid(qs, rs, indexing='ij')
    X = HEX * SQ3 * (Q + R * 0.5)
    Z = HEX * 1.5 * R.astype(np.float64)
    solid_any = cells > 0
    # clearance also looks at the six neighbours, so a tier never touches land diagonally
    near = solid_any.copy()
    for dq, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)):
        near |= np.roll(np.roll(solid_any, dq, 0), dr, 2)
    # highest and lowest solid per column, to keep clearance cheaply
    occ = solid_any.any(axis=1)
    placed = 0
    for ti, (kind, period, accept, (rmin, rmax), off) in enumerate(TIERS):
        # clearance against everything placed before this tier (not this tier's own cells)
        near = solid_any.copy()
        for dq, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)):
            near |= np.roll(np.roll(solid_any, dq, 0), dr, 2)
        x0, x1 = float(X.min()), float(X.max())
        z0, z1 = float(Z.min()), float(Z.max())
        reach = rmax * period * 1.2 + 0.25 * period
        wn = None
        best_u = np.full(X.shape, 9.0)
        best_alt = np.zeros(X.shape)
        best_rad = np.ones(X.shape)
        best_id = np.zeros(X.shape, np.int64)
        for ci in range(int(np.floor((x0 - reach) / period)), int(np.floor((x1 + reach) / period)) + 1):
            for cj in range(int(np.floor((z0 - reach) / period)), int(np.floor((z1 + reach) / period)) + 1):
                c = accepted(gen, ti, ci, cj)
                if c is None:
                    continue
                px, pz, rad, alt, _ = c
                if np.hypot(np.clip(px, x0, x1) - px, np.clip(pz, z0, z1) - pz) > rad * 1.15:
                    continue
                if wn is None:
                    wn = gen.n_detail.fbm2(X / 11.0 + off, Z / 11.0 - off, 2)
                dx, dz = X - px, Z - pz
                warp = 0.12 * rad * wn
                u = (np.hypot(dx, dz) + warp) / rad
                better = u < best_u
                best_u = np.where(better, u, best_u)
                best_alt = np.where(better, alt, best_alt)
                best_rad = np.where(better, rad, best_rad)
                best_id = np.where(better, ci * 7919 + cj + off, best_id)
        land = best_u < 1.0
        if not land.any():
            continue
        e = np.clip(1.0 - best_u, 0.0, 1.0)
        dome = np.sqrt(e)
        hill = 3.0 * gen.n_hill.fbm2(X / 40.0 + off, Z / 40.0, 2) * e
        top = np.floor(best_alt + 2.0 * dome + hill)
        # tapered tail like the main islands: shallow rim, long point under the middle
        tail = 0.5 * (1.0 - np.cos(np.pi * e))
        depth = 2.0 + tail * np.minimum(DEPTH_MAX, best_rad * 0.55) * (0.85 + 0.3 * gen.n_depth.fbm2(X / 20.0, Z / 20.0, 2))
        top = np.clip(top, 8, TOP_CAP).astype(np.int64)
        bot = np.clip(top - np.floor(depth).astype(np.int64), 4, None)
        ys = np.arange(LAYERS)[None, :, None]
        T3, B3 = top[:, None, :], bot[:, None, :]
        slab = (ys >= B3 - CLEAR) & (ys <= T3 + CLEAR)
        clash = (near & slab).any(axis=1)
        put = land & ~clash
        if not put.any():
            continue
        realm = (best_id % 20).astype(np.int64)
        lut = np.array([_realm_surface(r_) for r_ in range(20)], np.uint8)     # (20, 3): surf, mid, body
        surf, mid, body = lut[realm, 0], lut[realm, 1], lut[realm, 2]
        P3 = put[:, None, :]
        fill = P3 & (ys >= B3) & (ys <= T3)
        layer_mat = np.where(ys == T3, surf[:, None, :], np.where(ys >= T3 - 2, mid[:, None, :], body[:, None, :]))
        cells[fill] = layer_mat[fill]
        solid_any |= fill
        occ |= put
        placed += int(fill.sum())
        # a few small trees and plants on top
        hsh = (rand01(Q, R, gen.h + off + 9) * 1e9).astype(np.int64)
        turf = put & (surf == M['turf'])
        for i, k in zip(*np.nonzero(turf & (e > 0.25) & (hsh % 1000 < 22))):
            if not (1 <= i < CHUNK - 1 and 1 <= k < CHUNK - 1):
                continue
            t = int(top[i, k])
            h = 3 + int(hsh[i, k]) % 4
            if t + h + 3 >= LAYERS:
                continue
            cells[i, t + 1:t + 1 + h, k] = M['heartwood']
            for a, c in ((i + 1, k), (i - 1, k), (i, k + 1), (i, k - 1), (i + 1, k - 1), (i - 1, k + 1)):
                for y in (t + h, t + h + 1):
                    if cells[a, y, c] == 0:
                        cells[a, y, c] = M['canopy']
            cells[i, t + h + 1, k] = M['canopy']
            cells[i, t + h + 2, k] = M['canopy']
        fl = turf & (hsh % 1000 > 900) & (top + 1 < LAYERS)
        fi, fk = np.nonzero(fl)
        ft = top[fi, fk] + 1
        free = cells[fi, ft, fk] == 0
        cells[fi[free], ft[free], fk[free]] = np.where(hsh[fi[free], fk[free]] % 3 > 0, M['grass'], M['wildflower'])
    return placed

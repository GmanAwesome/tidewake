"""Turns a chunk of hex cells into GPU vertex data (vectorised numpy, runs in workers).

Opaque cells are hex prisms: a 6-triangle fan on top (with a soft rim so the honeycomb
reads clearly), and quads on the six sides, emitted only where the neighbour doesn't
hide them. Small cells (crystals, blooms, lanterns...) are built from little prisms.
"""
import numpy as np

from .config import CHUNK, LAYERS, LAYER, HEX, SQ3
from .hexgrid import DIRS, CORNERS, DIR_NORMALS
from . import materials as MT
from .noise import hash2

VERT = np.dtype([('p', '<f4', 3), ('c', 'u1', 4), ('n', 'u1', 4), ('m', 'u1', 4)])   # m: material, sway, 0, 0
OPAQUE = MT.OPAQUE
_ID = MT.ID


def pack(emit, sky=1.0):
    """Colour alpha byte as a 0-1 float: high nibble emit, low nibble sky light."""
    e = np.clip(np.round(np.asarray(emit, dtype=np.float64) * 15), 0, 15)
    s = np.clip(np.round(np.asarray(sky, dtype=np.float64) * 15), 0, 15)
    return (e * 16 + s) / 255.0


def pad_chunk(get, cq, cr):
    """Assemble (CHUNK+2, LAYERS, CHUNK+2) cells from a chunk and its neighbours. get(cq, cr) -> cells or None"""
    P = np.zeros((CHUNK + 2, LAYERS, CHUNK + 2), np.uint8)
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            c = get(cq + a, cr + b)
            if c is None:
                continue
            qs = slice(1, CHUNK + 1) if a == 0 else (slice(0, 1) if a < 0 else slice(CHUNK + 1, CHUNK + 2))
            rs = slice(1, CHUNK + 1) if b == 0 else (slice(0, 1) if b < 0 else slice(CHUNK + 1, CHUNK + 2))
            cs_q = slice(0, CHUNK) if a == 0 else (slice(CHUNK - 1, CHUNK) if a < 0 else slice(0, 1))
            cs_r = slice(0, CHUNK) if b == 0 else (slice(CHUNK - 1, CHUNK) if b < 0 else slice(0, 1))
            P[qs, :, rs] = c[cs_q, :, cs_r]
    return P


def _enc_n(nx, ny, nz):
    return np.stack([nx * 127.5 + 127.5, ny * 127.5 + 127.5, nz * 127.5 + 127.5], -1)


def _faces_top(cx, cz, y, rad, col, emit, ao, up=True):
    """Hex caps. cx, cz, y, rad: (N,), col (N,3) 0-1, emit (N,), ao (N,6). -> VERT array (N*18,)"""
    n = len(cx)
    if n == 0:
        return np.zeros(0, VERT)
    out = np.zeros((n, 6, 3), VERT)
    k = np.arange(6)
    k1 = (k + 1) % 6
    # positions
    ccx = cx[:, None] + CORNERS[None, :, 0] * rad[:, None]
    ccz = cz[:, None] + CORNERS[None, :, 1] * rad[:, None]
    first, second = (k1, k) if up else (k, k1)
    P = out['p']
    P[:, :, 0, 0], P[:, :, 0, 1], P[:, :, 0, 2] = cx[:, None], y[:, None], cz[:, None]
    P[:, :, 1, 0], P[:, :, 1, 1], P[:, :, 1, 2] = ccx[:, first], y[:, None], ccz[:, first]
    P[:, :, 2, 0], P[:, :, 2, 1], P[:, :, 2, 2] = ccx[:, second], y[:, None], ccz[:, second]
    C = out['c']
    c255 = col * 255.0
    C[:, :, 0, :3] = np.clip(c255 * ao.mean(1)[:, None] * 0.5 + c255 * 0.5, 0, 255)[:, None, :]
    C[:, :, 1, :3] = np.clip(c255[:, None, :] * ao[:, first, None], 0, 255)
    C[:, :, 2, :3] = np.clip(c255[:, None, :] * ao[:, second, None], 0, 255)
    C[..., 3] = np.clip(np.round(emit * 255), 0, 255)[:, None, None]
    Nn = out['n']
    Nn[..., 0], Nn[..., 1], Nn[..., 2] = 128, (255 if up else 0), 128
    Nn[:, :, 0, 3] = 255
    Nn[:, :, 1:, 3] = 0
    return out.reshape(-1)


def _faces_side(cx, cz, y0, y1, rad, d, col_top, col_bot, emit, shade_bot=0.80):
    """Side quads facing direction d (0..5). -> VERT array (N*6,)"""
    n = len(cx)
    if n == 0:
        return np.zeros(0, VERT)
    a, b = CORNERS[(d - 1) % 6], CORNERS[d]
    out = np.zeros((n, 6), VERT)
    ax, az = cx + a[0] * rad, cz + a[1] * rad
    bx, bz = cx + b[0] * rad, cz + b[1] * rad
    # quad A(bottom a) B(bottom b) C(top b) D(top a), wound to face outwards
    xs = np.stack([ax, bx, bx, ax, ax, bx], 1)
    zs = np.stack([az, bz, bz, az, az, bz], 1)
    ys = np.stack([y0, y1, y0, y0, y1, y1], 1)
    top = np.array([0, 1, 0, 0, 1, 1], bool)
    out['p'][..., 0], out['p'][..., 1], out['p'][..., 2] = xs, ys, zs
    ct = np.clip(col_top * 255.0, 0, 255)
    cb = np.clip(col_bot * 255.0 * shade_bot, 0, 255)
    out['c'][:, :, :3] = np.where(top[None, :, None], ct[:, None, :], cb[:, None, :])
    out['c'][..., 3] = np.clip(np.round(emit * 255), 0, 255)[:, None]
    nx, nz = DIR_NORMALS[d]
    out['n'][..., 0], out['n'][..., 1], out['n'][..., 2], out['n'][..., 3] = nx * 127.5 + 127.5, 128, nz * 127.5 + 127.5, 255
    out['m'][..., 3] = np.array([0, 255, 255, 0, 0, 255], np.uint8)[None, :]     # across-the-face u
    return out.reshape(-1)


SWAY = np.zeros(256, np.uint8)
for _k, _v in (('canopy', 60), ('vine', 200), ('sprout', 200), ('bloom', 160), ('berry_bush', 90), ('petals', 120)):
    SWAY[_ID[_k]] = _v


def _tag(parts, mats):
    """Write material ids (and how much they sway in the wind) into each face array."""
    if mats is None:
        return parts
    for v, mm in parts:
        if len(v):
            per = len(v) // max(1, len(mm))
            ids = np.repeat(mm.astype(np.uint8), per)
            v['m'][:, 0] = ids
            v['m'][:, 1] = SWAY[ids]
    return [v for v, _ in parts]


def _prisms(cx, cz, y0, y1, rad, ctop, cside_t, cside_b, emit, mask_top=None, mask_bot=None, mask_side=None,
            ao=None, shade_bot=0.80, mat=None, front=None):
    """emit: (n,) packed values, or (n, 8) per face: top, bottom, then the six sides."""
    parts = []
    n = len(cx)
    if n == 0:
        return parts
    if ao is None:
        ao = np.ones((n, 6))
    E = emit if emit.ndim == 2 else np.repeat(emit[:, None], 8, 1)
    mt = np.ones(n, bool) if mask_top is None else mask_top
    M_ = None if mat is None else np.broadcast_to(np.asarray(mat), (n,))
    tg = []
    tg.append((_faces_top(cx[mt], cz[mt], y1[mt], rad[mt], ctop[mt], E[mt, 0], ao[mt], True), None if M_ is None else M_[mt]))
    mb = np.ones(n, bool) if mask_bot is None else mask_bot
    tg.append((_faces_top(cx[mb], cz[mb], y0[mb], rad[mb], cside_b[mb] * 0.8, E[mb, 1], np.ones((mb.sum(), 6)), False),
               None if M_ is None else M_[mb]))
    for d in range(6):
        ms = np.ones(n, bool) if mask_side is None else mask_side[:, d]
        sv = _faces_side(cx[ms], cz[ms], y0[ms], y1[ms], rad[ms], d, cside_t[ms], cside_b[ms], E[ms, 2 + d], shade_bot)
        if front is not None and len(sv):
            fr = np.repeat(front[ms] == d, 6)
            sv['m'][fr, 2] = 255
        tg.append((sv, None if M_ is None else M_[ms]))
    if M_ is None:
        return [v for v, _ in tg]
    return _tag(tg, M_)


def mesh_chunk(P, realm, cq, cr, Pm=None):
    """P: padded cells (CHUNK+2, LAYERS, CHUNK+2). -> (opaque bytes, water bytes, lights (M,4) float32)"""
    core = P[1:-1, :, 1:-1]
    occ = OPAQUE[P]
    wat = MT.IS_WATER[P]
    gls = MT.IS_GLASS[P]
    # sky light: is an (empty) cell roofed over, and is it enclosed from below too (a cave)?
    roof = occ & (P != _ID['canopy'])
    leaf = P == _ID['canopy']
    cs = np.cumsum(roof[:, ::-1, :], axis=1)[:, ::-1, :]
    above = (cs - roof) > 0
    below = (np.cumsum(roof, axis=1) - roof) > 0
    ls = np.cumsum(leaf[:, ::-1, :], axis=1)[:, ::-1, :]
    under_leaf = (ls - leaf) > 0
    SKY = np.where(above, np.where(below, 0.22, 0.62), np.where(under_leaf, 0.78, 1.0))
    nz = np.nonzero(core)
    if len(nz[0]) == 0:
        return b'', b'', np.zeros((0, 4), np.float32)
    lq, ly, lr = nz
    mat = core[nz]
    gq = lq.astype(np.int64) + cq * CHUNK
    gr = lr.astype(np.int64) + cr * CHUNK
    jit = 0.94 + 0.10 * ((hash2(gq * 131 + ly, gr, 0x7E1) >> np.uint64(40)).astype(np.float64) / (1 << 24))
    cx = HEX * SQ3 * (lq + lr * 0.5)
    cz = HEX * 1.5 * lr.astype(np.float64)
    rl = realm[lq, lr]

    top = MT.TOP[mat].astype(np.float64)
    side = MT.SIDE[mat].astype(np.float64)
    turf = mat == _ID['turf']
    top[turf] = MT.REALM_TURF[rl[turf]]
    canopy = mat == _ID['canopy']
    top[canopy] = MT.REALM_CANOPY[rl[canopy]]
    side[canopy] = MT.REALM_CANOPY[rl[canopy]] * 0.9
    rose = mat == _ID['rosestone']
    band = MT.ROSE_BANDS[(ly[rose] // 2) % len(MT.ROSE_BANDS)]
    top[rose], side[rose] = band, band * 0.95
    sp = (mat == _ID['dormant_spire']) | (mat == _ID['awake_spire'])
    rune = sp & (ly % 3 == 1)
    top[rune] = top[rune] * 0.75 + np.array([0.95, 0.85, 1.0]) * 0.35
    side[rune] = side[rune] * 0.7 + np.array([0.80, 0.72, 1.0]) * 0.4
    pet = mat == _ID['petals']
    top[pet] = MT.PETAL_COLORS[((gq[pet] * 7 + gr[pet] * 13) % 4)]
    side_top = side.copy()
    side_top[turf] = top[turf] * 0.92
    side_top[mat == _ID['mossrock']] = top[mat == _ID['mossrock']]
    top *= jit[:, None]
    side *= jit[:, None]
    side_top *= jit[:, None]
    emit = MT.EMIT[mat].astype(np.float64)
    emit[rune & (mat == _ID['dormant_spire'])] = 0.25
    ore = np.isin(mat, MT.ORES)
    side_top[ore] = top[ore] * 0.9

    pq, pr = lq + 1, lr + 1
    up = np.minimum(ly + 1, LAYERS - 1)
    dn = np.maximum(ly - 1, 0)
    is_full = OPAQUE[mat]
    out_o, out_w = [], []

    # ---- full prisms
    f = is_full
    if f.any():
        q_, y_, r_ = pq[f], ly[f], pr[f]
        u_, d_ = up[f], dn[f]
        show_top = ~occ[q_, u_, r_] | (y_ == LAYERS - 1)
        show_bot = ~occ[q_, d_, r_] | (y_ == 0)
        sides = np.stack([~occ[q_ + dq, y_, r_ + dr] for dq, dr in DIRS], 1)
        occ_up = np.stack([occ[q_ + dq, u_, r_ + dr] for dq, dr in DIRS], 1).astype(np.float64)
        ao = 1.0 - 0.17 * (occ_up + np.roll(occ_up, -1, axis=1))
        y0 = y_ * LAYER
        y1 = y0 + LAYER
        E = np.empty((f.sum(), 8))
        ef = emit[f]
        E[:, 0] = pack(ef, SKY[q_, u_, r_])
        E[:, 1] = pack(ef, 0.55)
        for d, (dq, dr) in enumerate(DIRS):
            E[:, 2 + d] = pack(ef, SKY[q_ + dq, y_, r_ + dr])
        mf = mat[f]
        meta_f = Pm[q_, y_, r_] if Pm is not None else np.zeros(len(mf), np.uint8)
        meta_f = meta_f.astype(np.int64)
        facing = np.where(np.isin(mf, FACING), meta_f % 8 % 6, -1)
        kl = mf == _ID['kiln']
        if kl.any():
            lit = (meta_f[kl] & 8) > 0
            for d in range(6):
                E[kl, 2 + d] = np.where(facing[kl] == d, pack(np.where(lit, 0.95, 0.12), SKY[q_[kl], y_[kl], r_[kl]]),
                                        pack(0.0, SKY[q_[kl] + DIRS[d][0], y_[kl], r_[kl] + DIRS[d][1]]))
            E[kl, 0] = pack(0.0, SKY[q_[kl], u_[kl], r_[kl]])
        out_o += _prisms(cx[f], cz[f], y0, y1, np.ones(f.sum()), top[f], side_top[f], side[f], E,
                         show_top, show_bot, sides, ao, mat=mf, front=facing)
        out_o += _extras(mf, facing, cx[f], cz[f], y1, show_top, SKY[q_, u_, r_])

    # ---- slabs (half-height prisms; not opaque, so neighbours keep their faces)
    sl = MT.IS_SLAB[mat]
    if sl.any():
        q_, y_, r_ = pq[sl], ly[sl], pr[sl]
        u_, d_ = up[sl], dn[sl]
        show_top = ~occ[q_, u_, r_]
        show_bot = ~occ[q_, d_, r_] | (y_ == 0)
        sides = np.stack([~occ[q_ + dq, y_, r_ + dr] for dq, dr in DIRS], 1)
        y0 = y_ * LAYER
        y1 = y0 + LAYER * 0.5
        out_o += _prisms(cx[sl], cz[sl], y0, y1, np.ones(sl.sum()), top[sl], side_top[sl], side[sl],
                         pack(emit[sl], SKY[q_, y_, r_]), show_top, show_bot, sides, None, mat=mat[sl])

    # ---- water
    w = MT.IS_WATER[mat]
    if w.any():
        q_, y_, r_ = pq[w], ly[w], pr[w]
        u_, d_ = up[w], dn[w]
        above_w = wat[q_, u_, r_]
        show_top = ~above_w & ~occ[q_, u_, r_]
        show_bot = ~wat[q_, d_, r_] & ~occ[q_, d_, r_]
        sides = np.stack([~wat[q_ + dq, y_, r_ + dr] & ~occ[q_ + dq, y_, r_ + dr] for dq, dr in DIRS], 1)
        y0 = y_ * LAYER
        y1 = y0 + np.where(above_w, LAYER, LAYER * 0.82)
        out_w += _prisms(cx[w], cz[w], y0, y1, np.ones(w.sum()), top[w], side[w], side[w],
                         pack(emit[w], SKY[q_, y_, r_]), show_top, show_bot, sides, None, shade_bot=0.95, mat=mat[w])

    # ---- glass (drawn with the water, see-through)
    g = MT.IS_GLASS[mat]
    if g.any():
        q_, y_, r_ = pq[g], ly[g], pr[g]
        u_, d_ = up[g], dn[g]
        show_top = ~gls[q_, u_, r_] & ~occ[q_, u_, r_]
        show_bot = ~gls[q_, d_, r_] & ~occ[q_, d_, r_]
        sides = np.stack([~gls[q_ + dq, y_, r_ + dr] & ~occ[q_ + dq, y_, r_ + dr] for dq, dr in DIRS], 1)
        y0 = y_ * LAYER
        out_w += _prisms(cx[g], cz[g], y0, y0 + LAYER, np.ones(g.sum()), top[g], side[g], side[g],
                         pack(emit[g], SKY[q_, y_, r_]), show_top, show_bot, sides, None, shade_bot=1.0, mat=mat[g])

    # ---- small cells built from parts
    lights = []
    for m_id, parts in MT.PARTS.items():
        s = mat == m_id
        if not s.any():
            continue
        n = s.sum()
        hang = np.zeros(n, bool)
        if m_id in (_ID['lumen_shard'], _ID['lantern']):
            hang = occ[pq[s], up[s], pr[s]] & ~occ[pq[s], dn[s], pr[s]]       # hanging from a ceiling
        for rad, a, b, use_top in parts:
            if m_id == _ID['lumen_shard']:
                a, b = (1 - b, 1 - a)
                aa = np.where(hang, a, 1 - b)
                bb = np.where(hang, b, 1 - a)
            else:
                aa, bb = np.full(n, a), np.full(n, b)
            y0 = (ly[s] + aa) * LAYER
            y1 = (ly[s] + bb) * LAYER
            if use_top == 'core':
                ct = np.tile(np.array([1.0, 0.90, 0.55]), (n, 1))
                em = np.maximum(emit[s], 0.25)
            elif use_top == 'berry':
                ct = np.tile(np.array([0.62, 0.36, 0.86]), (n, 1))
                em = np.full(n, 0.2)
            else:
                ct = top[s] if use_top else side[s]
                em = emit[s] if use_top else emit[s] * 0.2
            sk = SKY[pq[s], ly[s], pr[s]]
            if use_top == 'berry':
                # berries peek out of the bush on all sides
                for k in range(6):
                    ang = k * np.pi / 3 + 0.4
                    out_o += _prisms(cx[s] + np.cos(ang) * 0.42, cz[s] + np.sin(ang) * 0.42, y0 + (k % 2) * 0.08 * LAYER,
                                     y0 + (0.14 + (k % 2) * 0.08) * LAYER, np.full(n, 0.09), ct, ct, ct * 0.85, pack(em, sk), mat=m_id)
                continue
            out_o += _prisms(cx[s], cz[s], y0, y1, np.full(n, rad), ct, ct, ct * 0.85, pack(em, sk), mat=m_id)
        if m_id in MT.LIGHTS:
            lights.append(np.stack([cx[s], (ly[s] + 0.6) * LAYER, cz[s], np.full(n, m_id)], 1))
    out_o += _fittings(mat, Pm, cx, cz, ly, pq, pr, SKY)
    # point lights for solid glowing blocks (lamps, ores, starstone, and the specials above)
    already = set(MT.PARTS)  # deco lights already recorded
    for mid in MT.LIGHTS:
        if mid in already:
            continue
        s = mat == mid
        if s.any():
            lights.append(np.stack([cx[s], (ly[s] + 0.5) * LAYER, cz[s], np.full(s.sum(), mid)], 1))
    L = np.concatenate(lights).astype(np.float32) if lights else np.zeros((0, 4), np.float32)
    if len(L) > 40:
        L = L[np.linspace(0, len(L) - 1, 40).astype(int)]
    ob = np.concatenate(out_o).tobytes() if out_o else b''
    wb = np.concatenate(out_w).tobytes() if out_w else b''
    return ob, wb, L


FACING = np.array([_ID['tinker_bench'], _ID['kiln'], _ID['chest']])


def _extras(mf, facing, cx, cz, ytop, open_top, sky):
    """Little 3D touches on top of functional blocks: a vise and mallet on the bench, a chimney on the kiln."""
    out = []
    iron = np.array([0.42, 0.44, 0.50])
    wood = np.array([0.66, 0.48, 0.32])
    for mid, items in ((_ID['tinker_bench'], (('vise', 0.20, 0.55, 0.0, 0.18, 0.14, iron), ('vjaw', 0.20, 0.55, 0.18, 0.26, 0.07, iron * 1.2),
                                                ('handle', -0.30, -0.25, 0.0, 0.05, 0.05, wood), ('head', -0.30, -0.25, 0.05, 0.16, 0.12, iron * 0.9),
                                                ('plank', -0.05, 0.45, 0.0, 0.04, 0.26, wood * 1.15))),
                       (_ID['kiln'], (('chimney', 0.0, -0.42, 0.0, 0.42, 0.26, np.array([0.70, 0.42, 0.36])),
                                      ('cap', 0.0, -0.42, 0.42, 0.48, 0.30, np.array([0.50, 0.32, 0.30])))),):
        s = (mf == mid) & open_top
        if not s.any():
            continue
        ang = np.where(facing[s] >= 0, facing[s], 0) * (np.pi / 3)
        ca, sa = np.cos(ang), np.sin(ang)
        for name, ox, oz, a, b, rad, col in items:
            px = cx[s] + ox * ca - oz * sa
            pz = cz[s] + ox * sa + oz * ca
            n = s.sum()
            mat = _ID['bricks'] if mid == _ID['kiln'] else 0
            out += _prisms(px, pz, ytop[s] + a * LAYER, ytop[s] + b * LAYER, np.full(n, rad), np.tile(col, (n, 1)),
                           np.tile(col, (n, 1)), np.tile(col * 0.85, (n, 1)), pack(0.0, sky[s]), mat=mat)
    return out



def _fittings(mat, Pm, cx, cz, ly, pq, pr, SKY):
    """Doors and ladders: thin, faced fittings, not full hex prisms."""
    out = []
    if Pm is None:
        return out
    wood = np.array([0.82, 0.62, 0.42])
    dark = np.array([0.40, 0.28, 0.20])
    iron = np.array([0.45, 0.42, 0.40])
    s = mat == _ID['door']
    if s.any():
        meta = Pm[pq[s], ly[s], pr[s]].astype(np.int64)
        face = meta % 8 % 6
        opened = (meta & 8) != 0
        base = face * (np.pi / 3)
        ang = base + np.where(opened, 1.35, 0.0)
        hinge = base + np.pi / 2
        dist = np.where(opened, 0.22, 0.18)
        px = cx[s] + np.cos(ang) * dist + np.where(opened, np.cos(hinge) * 0.30, 0)
        pz = cz[s] + np.sin(ang) * dist + np.where(opened, np.sin(hinge) * 0.30, 0)
        n = int(s.sum())
        y0, y1 = ly[s] * LAYER, (ly[s] + 1) * LAYER
        E = pack(0.0, SKY[pq[s], ly[s], pr[s]])
        out += _prisms(px, pz, y0, y1, np.full(n, 0.40), np.tile(wood, (n, 1)), np.tile(wood * 0.9, (n, 1)),
                       np.tile(dark, (n, 1)), E, mat=_ID['door'], front=face)
        # a darker strap / handle
        hx = px + np.cos(ang + np.pi / 2) * 0.22
        hz = pz + np.sin(ang + np.pi / 2) * 0.22
        mid = (y0 + y1) * 0.5
        out += _prisms(hx, hz, mid - 0.06, mid + 0.06, np.full(n, 0.07), np.tile(iron, (n, 1)), np.tile(iron, (n, 1)),
                       np.tile(iron * 0.8, (n, 1)), E, mat=_ID['door'])
    s = mat == _ID['ladder']
    if s.any():
        meta = Pm[pq[s], ly[s], pr[s]].astype(np.int64)
        face = meta % 8 % 6
        ang = face * (np.pi / 3)
        n = int(s.sum())
        bx = cx[s] + np.cos(ang) * 0.72
        bz = cz[s] + np.sin(ang) * 0.72
        tx, tz = np.cos(ang + np.pi / 2), np.sin(ang + np.pi / 2)
        y0, y1 = ly[s] * LAYER, (ly[s] + 1) * LAYER
        E = pack(0.0, SKY[pq[s], ly[s], pr[s]])
        for sign in (-1.0, 1.0):
            out += _prisms(bx + tx * 0.28 * sign, bz + tz * 0.28 * sign, y0, y1, np.full(n, 0.055),
                           np.tile(wood, (n, 1)), np.tile(wood * 0.85, (n, 1)), np.tile(dark, (n, 1)), E, mat=_ID['ladder'])
        for frac in (0.18, 0.5, 0.82):
            out += _prisms(bx, bz, y0 + frac * LAYER - 0.04, y0 + frac * LAYER + 0.04, np.full(n, 0.30),
                           np.tile(wood * 1.05, (n, 1)), np.tile(wood, (n, 1)), np.tile(dark, (n, 1)), E, mat=_ID['ladder'])
    return out


def lod_mesh(cells, realm, dx=0.0, dz=0.0, step=2):
    """Cheap far-away mesh for one chunk: per column one cap + one body prism (+ a canopy slab).
    No caves, plants or lights. -> VERT array, positions offset by (dx, dz)."""
    c = cells
    can = c == _ID['canopy']
    wood = np.isin(c, list(MT.WOODS))
    terr = (OPAQUE[c] | MT.IS_WATER[c]) & ~can & ~wood
    has = terr.any(1)
    if not has.any() and not can.any():
        return np.zeros(0, VERT)
    Lm = LAYERS - 1
    # half resolution: every other column, drawn as hexes twice the size (an exact scaled tiling)
    s_ = step
    c, can, terr, has = c[::s_, :, ::s_], can[::s_, :, ::s_], terr[::s_, :, ::s_], has[::s_, ::s_]
    realm = realm[::s_, ::s_]
    N = CHUNK // s_
    top = np.where(has, Lm - np.argmax(terr[:, ::-1, :], axis=1), -1)
    bot = np.where(has, np.argmax(terr, axis=1), 0)
    Q, R = np.nonzero(has)
    t_, b_ = top[Q, R], bot[Q, R]
    tm = c[Q, t_, R]
    um = c[Q, np.maximum(b_, t_ - 2), R]
    rl = realm[Q, R]
    tc = MT.TOP[tm].astype(np.float64)
    turf = tm == _ID['turf']
    tc[turf] = MT.REALM_TURF[rl[turf]]
    sc_cap = MT.SIDE[tm].astype(np.float64)
    sc_cap[turf] = tc[turf] * 0.92
    sc_body = MT.SIDE[um].astype(np.float64)
    cx = HEX * SQ3 * s_ * (Q + R * 0.5) + dx
    cz = HEX * 1.5 * s_ * R.astype(np.float64) + dz
    n = len(Q)

    def nb(arr, fill):
        out = []
        for dq, dr in DIRS:
            a = np.full(arr.shape, fill, arr.dtype)
            qs = slice(max(0, -dq), N - max(0, dq))
            qd = slice(max(0, dq), N - max(0, -dq))
            rs = slice(max(0, -dr), N - max(0, dr))
            rd = slice(max(0, dr), N - max(0, -dr))
            a[qs, rs] = arr[qd, rd]
            out.append(a[Q, R])
        return np.stack(out, 1)
    nt = nb(top, -1)
    nbt = nb(np.where(has, bot, 999), 999)
    cap_side = nt < t_[:, None]
    body_side = ~((nbt <= b_[:, None]) & (nt >= t_[:, None] - 1))
    E = np.full(n, pack(0.0, 1.0))
    out = []
    y_cap0 = t_ * LAYER
    out += _prisms(cx, cz, y_cap0, y_cap0 + LAYER, np.full(n, float(s_)), tc, sc_cap, sc_cap, E, None, np.zeros(n, bool), cap_side, mat=tm)
    body = t_ > b_
    if body.any():
        f = body
        out += _prisms(cx[f], cz[f], b_[f] * LAYER, y_cap0[f], np.full(f.sum(), float(s_)), sc_body[f], sc_body[f], sc_body[f] * 0.8,
                       E[f], np.zeros(f.sum(), bool), np.ones(f.sum(), bool), body_side[f])
    hc = can.any(1)
    if hc.any():
        Q2, R2 = np.nonzero(hc)
        ct = Lm - np.argmax(can[:, ::-1, :], axis=1)[Q2, R2]
        cb = np.argmax(can, axis=1)[Q2, R2]
        col = MT.REALM_CANOPY[realm[Q2, R2]].astype(np.float64)
        m = len(Q2)
        out += _prisms(HEX * SQ3 * s_ * (Q2 + R2 * 0.5) + dx, HEX * 1.5 * s_ * R2.astype(np.float64) + dz, cb * LAYER, (ct + 1) * LAYER,
                       np.full(m, float(s_)), col, col * 0.9, col * 0.8, np.full(m, pack(0.0, 0.9)))
    out = [o for o in out if len(o)]
    return np.concatenate(out) if out else np.zeros(0, VERT)

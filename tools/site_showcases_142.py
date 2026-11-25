"""Find v3 sites for the 1.4.2 title showcases."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from tidewake.hexgrid import DIRS, hex_distance
from tidewake.noise import seed_from_text
from tidewake.generator import Generator
from tidewake import gensettings as GS
from tidewake.generator import (MEADOW, AMBER, ROSE, FROST, BASALT, FEN, DUNE, LUMEN,
    SALTWIND, CEDAR, LAVENDER, CINDER, CHALK, STARFALL, CLOUDSTEP, VERDIGRIS)

R = 240
STEP = 3


def load(seed):
    return Generator(seed_from_text(seed), GS.normalize({}, new=True))


def grid(gen, rad=R, step=STEP):
    qs, rs = np.meshgrid(np.arange(-rad, rad + 1, step), np.arange(-rad, rad + 1, step), indexing='ij')
    return gen.columns(qs, rs), qs, rs


def landmask(c):
    return c['land'] & ~c['skerry'] & (c['e'] > 0.05) & ~c['pool'] & ~c['fall']


def neighbors_land(gen, q, r, D, dist):
    dq, dr = DIRS[D]
    Q = np.array([q + dq * k for k in range(0, dist + 1)])
    R_ = np.array([r + dr * k for k in range(0, dist + 1)])
    c = gen.columns(Q, R_)
    return c


def plateau_ok(gen, q, r, rad, max_spread=5):
    pts = []
    for a in range(-rad, rad + 1):
        for b in range(-rad, rad + 1):
            if hex_distance(a, b, 0, 0) <= rad:
                pts.append((q + a, r + b))
    Q = np.array([p[0] for p in pts]); RR = np.array([p[1] for p in pts])
    c = gen.columns(Q, RR)
    lm = landmask(c)
    if lm.mean() < 0.72:
        return False, 0
    tops = c['top'][lm]
    mid = int(np.median(tops))
    if int(tops.max()) - int(tops.min()) > max_spread + 4:
        return False, mid
    if abs(int(c['top'][0]) - mid) > max_spread:  # origin may not be first
        # find origin
        pass
    # origin is first point (0,0 offset)
    # pts[0] is (-rad,-rad) not origin. Find it.
    i = pts.index((q, r))
    if not lm[i]:
        return False, mid
    if abs(int(c['top'][i]) - mid) > max_spread:
        return False, int(c['top'][i])
    return True, int(c['top'][i])


def edge_dir(gen, q, r, need=8, start=3):
    """A heading where land ends after a short lip and then there is open sky."""
    best = None
    for D in range(6):
        c = neighbors_land(gen, q, r, D, need + start)
        lm = landmask(c)
        # first `start` should be mostly land, then mostly air
        if lm[:start].mean() < 0.8:
            continue
        if lm[start:].mean() > 0.2:
            continue
        # require last 4 to be air
        if lm[-4:].any():
            continue
        best = D
        break
    return best


def prefer(realm, likes):
    return 40 if int(realm) in likes else 0


def scan_plateaus(gen, likes, top_lo, top_hi, rad, need_edge=False, n=8):
    c, qs, rs = grid(gen)
    lm = landmask(c)
    cand = []
    H, W = lm.shape
    for i in range(0, H):
        for j in range(0, W):
            if not lm[i, j]:
                continue
            top = int(c['top'][i, j])
            if not (top_lo <= top <= top_hi):
                continue
            q, r = int(qs[i, j]), int(rs[i, j])
            ok, t = plateau_ok(gen, q, r, rad)
            if not ok:
                continue
            D = edge_dir(gen, q, r) if need_edge else 0
            if need_edge and D is None:
                continue
            score = prefer(c['realm'][i, j], likes)
            score += 20 - min(20, abs(t - (top_lo + top_hi) // 2) / 8)
            # prefer closer to origin a bit so title loads less
            score -= 0.02 * (abs(q) + abs(r))
            cand.append((score, q, r, t, int(c['realm'][i, j]), D if need_edge else 0))
    cand.sort(reverse=True)
    # keep spread-out winners
    picked = []
    for row in cand:
        if any(hex_distance(row[1], row[2], p[1], p[2]) < 18 for p in picked):
            continue
        picked.append(row)
        if len(picked) >= n:
            break
    return picked


def scan_bridge(gen, span=16, top_lo=50, top_hi=180, n=6):
    c, qs, rs = grid(gen, rad=260, step=4)
    lm = landmask(c)
    cand = []
    H, W = lm.shape
    # map for quick lookup is coarse; refine with exact columns
    for i in range(H):
        for j in range(W):
            if not lm[i, j]:
                continue
            q, r = int(qs[i, j]), int(rs[i, j])
            t0 = int(c['top'][i, j])
            if not (top_lo <= t0 <= top_hi):
                continue
            for D in range(6):
                dq, dr = DIRS[D]
                q2, r2 = q + dq * span, r + dr * span
                c2 = gen.columns(np.array([q2]), np.array([r2]))
                if not (bool(c2['land'][0]) and not bool(c2['skerry'][0]) and c2['e'][0] > 0.05):
                    continue
                t1 = int(c2['top'][0])
                if abs(t1 - t0) > 4 or not (top_lo <= t1 <= top_hi):
                    continue
                # hut needs land a little past the far abutment
                qh, rh = q2 + dq * 4, r2 + dr * 4
                ch = gen.columns(np.array([qh]), np.array([rh]))
                if not (bool(ch['land'][0]) and not bool(ch['skerry'][0])):
                    continue
                if abs(int(ch['top'][0]) - t1) > 6:
                    continue
                # gap mid should be air
                mids = []
                Q = np.array([q + dq * k for k in range(3, span - 2)])
                RR = np.array([r + dr * k for k in range(3, span - 2)])
                cm = gen.columns(Q, RR)
                air = (~cm['land']) | cm['skerry']
                if air.mean() < 0.75:
                    continue
                # both ends fairly flat
                ok0, _ = plateau_ok(gen, q, r, 2, max_spread=6)
                ok1, _ = plateau_ok(gen, q2, r2, 2, max_spread=6)
                if not (ok0 and ok1):
                    continue
                score = 50 + air.mean() * 20 - abs(t1 - t0) * 4 - 0.02 * (abs(q) + abs(r))
                cand.append((score, q, r, t0, D, q2, r2, t1, int(c['realm'][i, j])))
    cand.sort(reverse=True)
    picked = []
    for row in cand:
        if any(hex_distance(row[1], row[2], p[1], p[2]) < 24 for p in picked):
            continue
        picked.append(row)
        if len(picked) >= n:
            break
    return picked


JOBS = [
    ('lighthouse', 'keeper-of-tides', dict(likes=(SALTWIND, CHALK, MEADOW, AMBER, VERDIGRIS),
         top_lo=50, top_hi=160, rad=6, need_edge=True)),
    ('tavern', 'tavern-cliff', dict(likes=(FEN, MEADOW, VERDIGRIS, CEDAR, AMBER),
         top_lo=50, top_hi=170, rad=7, need_edge=True)),
    ('windmill', 'salt-wind-bay', dict(likes=(MEADOW, CEDAR, LAVENDER, AMBER, SALTWIND),
         top_lo=50, top_hi=170, rad=9, need_edge=False)),
    ('dock', 'windward-isle', dict(likes=(SALTWIND, MEADOW, AMBER, CHALK, VERDIGRIS, CLOUDSTEP),
         top_lo=50, top_hi=170, rad=5, need_edge=True)),
    ('keep', 'lantern-point', dict(likes=(CLOUDSTEP, BASALT, FROST, STARFALL, CINDER, CHALK),
         top_lo=110, top_hi=200, rad=7, need_edge=False)),
    ('temple', 'salt-wind-bay', dict(likes=(ROSE, LAVENDER, MEADOW, AMBER),
         top_lo=50, top_hi=180, rad=7, need_edge=False)),
    ('treehouse', 'ember-croft', dict(likes=(CEDAR, MEADOW, AMBER, LAVENDER, FEN),
         top_lo=50, top_hi=170, rad=6, need_edge=False)),
]

REALM = ['meadow','amber','rose','frost','basalt','fen','dune','lumen',
         'saltwind','cedar','lavender','cinder','chalk','starfall','cloudstep','verdigris']

if __name__ == '__main__':
    cache = {}
    for name, seed, kw in JOBS:
        if seed not in cache:
            print('load', seed)
            cache[seed] = load(seed)
        gen = cache[seed]
        hits = scan_plateaus(gen, **kw)
        print(f'\n== {name} ({seed}) ==')
        for row in hits[:5]:
            score,q,r,t,realm,D = row
            print(f'  score {score:7.1f}  q={q:4d} r={r:4d} top={t:3d} realm={REALM[realm]:10s} D={D}')
        if not hits:
            print('  NONE')
    print('\n== bridge (twin-isles) ==')
    hits = scan_bridge(load('twin-isles'), span=16)
    for row in hits[:6]:
        score,q,r,t0,D,q2,r2,t1,realm = row
        print(f'  score {score:7.1f}  {q},{r} T{t0} -> {q2},{r2} T{t1}  D={D} realm={REALM[realm]}')
    if not hits:
        print('  NONE')

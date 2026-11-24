"""Design-time builder for title-screen showcase builds -> assets/showcase/<name>.json.

A build is a list of [dq, dr, dy, material, meta] relative to a site (q, r, top) in a fixed seed.
dy = 0 is the ground surface. Run:  python tools/make_showcase.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidewake.generator import Generator          # noqa: E402
from tidewake.hexgrid import DIRS, hex_distance, spiral   # noqa: E402
from tidewake.noise import seed_from_text          # noqa: E402
from tidewake.session import find_spawn            # noqa: E402

SEEDS = ['tidewake-lighthouse', 'harbor-light', 'cliffside-cottage', 'golden-headland', 'keeper-of-tides',
         'lantern-point', 'seabird-cove', 'windward-cape']
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'showcase', 'lighthouse_cottage.json')


def rot(v, k):
    q, r = v
    for _ in range(k % 6):
        q, r = -r, q + r
    return q, r


def add(*vs):
    return (sum(v[0] for v in vs), sum(v[1] for v in vs))


def mul(v, s):
    return (v[0] * s, v[1] * s)


def find_site(gen):
    """Score every meadow spot near spawn: a headland (sky on several sides), hills and a
    waterfall or pool in view, flat enough to build on, low enough for the lighthouse."""
    q0, r0, _, _ = find_spawn(gen)
    R = 150
    qs, rs = np.meshgrid(np.arange(q0 - R, q0 + R + 1), np.arange(r0 - R, r0 + R + 1), indexing='ij')
    c = gen.columns(qs.ravel(), rs.ravel())
    shp = qs.shape
    land = (c['land'] & ~c['pool'] & ~c['fall']).reshape(shp)
    anyland = c['land'].reshape(shp)
    top = c['top'].reshape(shp)
    realm = c['realm'].reshape(shp)
    water = (c['pool'] | c['fall']).reshape(shp)
    fall = c['fall'].reshape(shp)

    def at(arr, q, r):
        i, k = q - (q0 - R), r - (r0 - R)
        if 0 <= i < shp[0] and 0 <= k < shp[1]:
            return arr[i, k]
        return None

    best = None
    disc5 = spiral(0, 0, 5)
    ring_far = [p for p in spiral(0, 0, 26) if 12 <= hex_distance(p[0], p[1], 0, 0) <= 26][::3]
    for i in range(20, shp[0] - 20, 2):
        for k in range(20, shp[1] - 20, 2):
            if not land[i, k] or realm[i, k] != 0 or not 50 <= top[i, k] < 90:
                continue
            q, r = int(qs[i, k]), int(rs[i, k])
            T = int(top[i, k])
            ok = True
            ts = []
            for dq, dr in disc5:
                if not at(land, q + dq, r + dr) or at(realm, q + dq, r + dr) != 0:
                    ok = False
                    break
                ts.append(at(top, q + dq, r + dr))
            if not ok or np.ptp(ts) > 4:
                continue
            drops = []
            for d in range(6):
                far = [(q + DIRS[d][0] * s, r + DIRS[d][1] * s) for s in range(8, 13)]
                dr_ = [(not at(anyland, a, b)) or at(top, a, b) < T - 8 for a, b in far]
                drops.append(sum(dr_) >= 4 and dr_[-1])
            if not any(drops):
                continue
            hills = sum(1 for dq, dr in ring_far if at(anyland, q + dq, r + dr) and at(top, q + dq, r + dr) > T + 5)
            wet = sum(1 for dq, dr in ring_far if at(water, q + dq, r + dr))
            falls = sum(1 for dq, dr in ring_far if at(fall, q + dq, r + dr))
            score = 3 * sum(drops) + min(hills, 8) * .6 + min(wet, 4) * 1.2 + min(falls, 3) * 2 - np.ptp(ts) * .5
            if best is None or score > best[0]:
                D = max(range(6), key=lambda d: drops[d])
                best = (score, q, r, int(np.median(ts)), D)
    print('best score', best and round(best[0], 2))
    return best


def build(gen, site):
    _, q0, r0, top, D = site
    blocks = {}
    dirv = lambda k: rot(DIRS[0], D + k)          # direction k relative to the dock direction

    def put(p, dy, mat, meta=0):
        blocks[(p[0], p[1], dy)] = (mat, meta)

    def facing(k):
        return (D + k) % 6

    def ringc(c, rad):
        out, cur = [], add(c, mul(dirv(4), rad))
        for i in range(6):
            for _ in range(rad):
                out.append(cur)
                cur = add(cur, dirv(i))
        return out if rad else [c]

    def disc(c, rad):
        return [p for k in range(rad + 1) for p in ringc(c, k)]

    def hd(a, b):
        return hex_distance(a[0], a[1], b[0], b[1])

    A = (0, 0)
    # ---------------- cottage (hex, timber-framed, stepped tile roof)
    C = mul(dirv(3), 5)
    door = add(C, mul(dirv(0), 3))
    corners = [add(C, mul(dirv(k), 3)) for k in range(6)]
    for p in disc(C, 2):
        put(p, 0, 'polished_stone')
    for p in ringc(C, 3):
        for dy in (1, 2, 3):
            put(p, dy, 'planks')
        put(p, 4, 'heartwood')
    for k, p in enumerate(corners):
        for dy in (1, 2, 3, 4):
            put(p, dy, 'heartwood')
    for k in (1, 2, 4, 5):                       # paired windows on four sides
        for j in (1, 2):
            put(add(C, mul(dirv(k), 3), mul(dirv(k + 2), j)), 2, 'glass')
    for j in (1, 2):                             # windows beside the door
        put(add(door, mul(dirv(2), 1)) if j == 1 else add(door, mul(dirv(4), 1)), 2, 'glass')
    put(door, 1, 'air'); put(door, 2, 'air'); put(door, 3, 'planks')
    put(door, 0, 'polished_stone')
    for p in ringc(C, 4):                        # eaves
        put(p, 5, 'bricks')
    for p in ringc(C, 3):
        put(p, 5, 'bricks')
    for p in ringc(C, 2):
        put(p, 6, 'bricks')
    for p in ringc(C, 1):
        put(p, 7, 'bricks')
    put(C, 8, 'mossy_bricks')
    chim = add(C, mul(dirv(2), 2))
    for dy in range(6, 10):
        put(chim, dy, 'mossy_bricks' if dy % 2 else 'bricks')
    put(chim, 10, 'glowstick')
    # inside: bedroll, lantern, chest of keepsakes
    put(add(C, dirv(3)), 1, 'bedroll')
    put(add(C, dirv(2)), 1, 'lantern')
    put(add(C, dirv(4)), 1, 'chest', facing(0))
    put(C, 1, 'petals')
    # flower boxes under the side windows, vines on the back wall
    for k in (1, 5):
        for j in (1, 2):
            put(add(C, mul(dirv(k), 4), mul(dirv(k + 2), j)), 1, 'bloom')
    for j in (0, 1, 2, 3):
        p = add(C, mul(dirv(3), 4), mul(dirv(5), j))
        put(p, 1, 'vine'); put(p, 2, 'vine')
    # ---------------- patio with the workshop
    for p in disc(A, 2):
        if hd(p, C) > 3:
            put(p, 0, 'polished_stone' if (p[0] + 2 * p[1]) % 3 else 'mossrock')
    put(mul(dirv(1), 2), 1, 'tinker_bench', facing(4))
    put(mul(dirv(5), 2), 1, 'kiln', facing(2) | 8)          # lit
    put(add(mul(dirv(5), 2), dirv(4)), 1, 'planks')          # firewood stack
    put(add(mul(dirv(5), 2), dirv(4)), 2, 'planks')
    put(add(dirv(3), dirv(4)), 1, 'chest', facing(1))
    put(add(mul(dirv(1), 2), dirv(2)), 1, 'lantern')
    put(add(dirv(0), dirv(1), dirv(1)), 1, 'berry_bush')
    # ---------------- path to the cliff and the sky dock
    k = 3
    path = []
    while k < 20:
        p = mul(dirv(0), k)
        c = gen.columns([q0 + p[0]], [r0 + p[1]])
        if not c['land'][0] or c['top'][0] < top - 3:
            break
        path.append(p)
        k += 1
    for i, p in enumerate(path):
        put(p, 0, 'polished_stone' if i % 2 == 0 else 'mossrock')
        if i % 3 == 1:
            side = dirv(1) if (i // 3) % 2 == 0 else dirv(5)
            put(add(p, side), 1, 'glowstick')
    edge = k
    for j in range(6):                            # dock planks out over the void
        p = mul(dirv(0), edge + j)
        put(p, 0, 'planks')
        if j % 2 == 0:
            for dy in range(-1, -5, -1):
                put(p, dy, 'heartwood')
    end = mul(dirv(0), edge + 5)
    for s in (dirv(1), dirv(5), add(dirv(1), dirv(0)), add(dirv(5), dirv(0)), dirv(0)):
        put(add(end, s), 0, 'planks')
    put(add(end, dirv(1)), 1, 'lantern')
    put(add(end, dirv(5)), 1, 'lantern')
    put(add(end, dirv(0)), 1, 'chest', facing(3))
    for s in (dirv(1), dirv(5)):
        for dy in range(-1, -4, -1):
            put(add(end, s), dy, 'heartwood')
    # ---------------- lighthouse on the cliff shoulder
    L = add(mul(dirv(1), 4), mul(dirv(0), 2))
    foot = disc(L, 1)
    cl = gen.columns([q0 + p[0] for p in disc(L, 2)], [r0 + p[1] for p in disc(L, 2)])
    for i, p in enumerate(disc(L, 2)):           # rock plinth under it, down to the land
        nat = int(cl['top'][i]) if cl['land'][i] else top - 10
        for dy in range(min(0, nat - top), 1):
            put(p, dy, 'mossrock' if dy == 0 and hd(p, L) == 2 else 'stone')
    for dy in range(1, 12):
        band = 'bricks' if (dy // 2) % 2 == 0 else 'polished_stone'
        for p in foot:
            put(p, dy, band)
    put(add(L, dirv(4)), 1, 'air'); put(add(L, dirv(4)), 2, 'air')   # little door
    put(add(L, dirv(4)), 3, 'heartwood')
    put(add(L, dirv(3)), 6, 'glass'); put(add(L, dirv(0)), 8, 'glass')
    for p in disc(L, 2):
        put(p, 12, 'plinth')
    for i, p in enumerate(ringc(L, 2)):
        if i % 3 == 0:
            put(p, 13, 'lantern')
    for p in ringc(L, 1):
        put(p, 13, 'glass'); put(p, 14, 'glass')
    put(L, 13, 'lumen_lamp'); put(L, 14, 'lumen_lamp')
    for p in disc(L, 1):
        put(p, 15, 'bricks')
    put(L, 16, 'bricks')
    put(L, 17, 'glowstick')
    for s in (dirv(0), dirv(5)):
        put(add(L, mul(s, 2)), 1, 'glowcap')
    # ---------------- garden (tilled beds, berries, flowers, glowstick fence posts)
    G = add(mul(dirv(4), 4), mul(dirv(5), 1))
    for p in disc(G, 1):
        put(p, 0, 'loam')
    plants = ['sprout', 'berry_bush', 'sprout', 'bloom', 'sprout', 'berry_bush', 'petals']
    for i, p in enumerate(disc(G, 1)):
        put(p, 1, plants[i % len(plants)])
    for i, p in enumerate(ringc(G, 2)):
        if hd(p, C) > 4 and (p[0], p[1], 0) not in blocks:
            put(p, 1, 'glowstick' if i % 4 == 0 else ('petals' if i % 2 else 'bloom'))
    # a little reading bench by the cliff
    bench = add(mul(dirv(5), 4), mul(dirv(0), 3))
    put(bench, 1, 'planks'); put(add(bench, dirv(1)), 1, 'planks')
    put(add(bench, dirv(5)), 1, 'lantern')
    return [[p[0], p[1], dy, m, meta] for (p0, p1, dy), (m, meta) in sorted(blocks.items()) for p in [(p0, p1)]]


def main():
    best = None
    for st in SEEDS:
        g = Generator(seed_from_text(st))
        s = find_site(g)
        if s and (best is None or s[0] > best[0][0]):
            best = (s, st, g)
    site, seed_text, gen = best
    print('chose seed', seed_text)
    assert site, 'no site found'
    _, q, r, top, D = site
    blocks = build(gen, site)
    data = dict(name='Lighthouse Cottage', author='a cozy evening in Tidewake', seed_text=seed_text,
                site=dict(q=q, r=r, top=top, dock_dir=D),
                camera=dict(radius=42.0, height=24.0, target_dy=3.0, yaw_offset=-20.0, speed=0.035, phase=0.2,
                            center=[-1.5, 0.5]),
                flatten=dict(radius=7, blend=6, clear_up=34, clear_trees=12, flowers=16),
                blocks=blocks)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    print('site', q, r, top, 'dock dir', D, 'blocks', len(blocks), '->', OUT)


if __name__ == '__main__':
    main()

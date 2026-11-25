"""Hand-designed 1.4.1 title showcases on the v2 generator, with clear camera orbits."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidewake.hexgrid import DIRS, hex_distance, center
from tidewake.noise import seed_from_text
from tidewake.generator import Generator
from tidewake import gensettings as GS
from tidewake import showcase as SC
from tidewake.config import LAYER

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'showcase')


def dirv(k):
    return DIRS[k % 6]


def mul(v, n):
    return (v[0] * n, v[1] * n)


def add(*ps):
    q = r = 0
    for p in ps:
        q += p[0]; r += p[1]
    return (q, r)


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


class Stamp:
    def __init__(self):
        self.blocks = {}

    def put(self, p, dy, mat, meta=0):
        if mat is None:
            return
        self.blocks[(p[0], p[1], dy)] = (mat, int(meta))

    def door(self, p, dy, face, open_=False):
        m = (face % 6) | (8 if open_ else 0)
        self.put(p, dy, 'door', m)
        self.put(p, dy + 1, 'door', m | 16)

    def ladder(self, p, y0, y1, face):
        for dy in range(y0, y1 + 1):
            self.put(p, dy, 'ladder', face % 6)

    def items(self):
        return [[q, r, dy, mat, meta] for (q, r, dy), (mat, meta) in sorted(self.blocks.items())]


def dump(name, author, seed, site, camera, flatten, blocks, extra=None):
    data = dict(name=name, author=author, seed_text=seed, gen={}, site=site,
                camera=camera, flatten=flatten, blocks=blocks)
    if extra:
        data.update(extra)
    path = os.path.join(ROOT, name.lower().replace(' ', '_').replace("'", '') + '.json')
    # keep a stable short name if provided
    return data, path


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    print('wrote', path, 'blocks', len(data['blocks']), 'site', data['site'], 'cam', data['camera'])


# ---------------- builds ----------------
def build_lighthouse(D=5):
    S = Stamp()
    put, door, ladder = S.put, S.door, S.ladder
    A = (0, 0)
    inland = (D + 3) % 6
    C = mul(dirv(inland), 5)
    door_p = add(C, mul(dirv(D), 3))  # door faces the dock / cliff
    corners = [add(C, mul(dirv(k), 3)) for k in range(6)]
    for p in disc(C, 2):
        put(p, 0, 'polished_stone')
    for p in ringc(C, 3):
        for dy in (1, 2, 3):
            put(p, dy, 'planks')
        put(p, 4, 'heartwood')
    for p in corners:
        for dy in (1, 2, 3, 4):
            put(p, dy, 'heartwood')
    for k in ((D + 1) % 6, (D + 2) % 6, (D + 4) % 6, (D + 5) % 6):
        for j in (1, 2):
            put(add(C, mul(dirv(k), 3), mul(dirv(k + 2), j)), 2, 'glass')
    put(add(door_p, dirv((D + 2) % 6)), 2, 'glass')
    put(add(door_p, dirv((D + 4) % 6)), 2, 'glass')
    put(door_p, 3, 'planks')
    put(door_p, 0, 'polished_stone')
    door(door_p, 1, D, open_=True)
    for rad, dy, mat in ((4, 5, 'shingles'), (3, 5, 'shingles'), (2, 6, 'shingles'), (1, 7, 'shingles')):
        for p in ringc(C, rad):
            put(p, dy, mat)
    put(C, 8, 'mossy_bricks')
    chim = add(C, mul(dirv((D + 2) % 6), 2))
    for dy in range(6, 10):
        put(chim, dy, 'mossy_bricks' if dy % 2 else 'bricks')
    put(chim, 10, 'glowstick')
    put(add(C, dirv(inland)), 1, 'bedroll')
    put(add(C, dirv((D + 2) % 6)), 1, 'lantern')
    put(add(C, dirv((D + 4) % 6)), 1, 'chest', D)
    put(C, 1, 'petals')
    for k in ((D + 1) % 6, (D + 5) % 6):
        for j in (1, 2):
            put(add(C, mul(dirv(k), 4), mul(dirv(k + 2), j)), 1, 'bloom')
    for j in range(4):
        p = add(C, mul(dirv(inland), 4), mul(dirv((inland + 2) % 6), j))
        put(p, 1, 'vine'); put(p, 2, 'vine')
    for p in disc(A, 2):
        if hd(p, C) > 3:
            put(p, 0, 'polished_stone' if (p[0] + 2 * p[1]) % 3 else 'mossrock')
    put(mul(dirv((D + 1) % 6), 2), 1, 'tinker_bench', (D + 4) % 6)
    put(mul(dirv((D + 5) % 6), 2), 1, 'kiln', ((D + 2) % 6) | 8)
    put(add(mul(dirv((D + 5) % 6), 2), dirv((D + 4) % 6)), 1, 'planks')
    put(add(mul(dirv((D + 5) % 6), 2), dirv((D + 4) % 6)), 2, 'planks')
    put(add(dirv(inland), dirv((D + 4) % 6)), 1, 'chest', (D + 1) % 6)
    put(add(mul(dirv((D + 1) % 6), 2), dirv((D + 2) % 6)), 1, 'lantern')
    put(add(dirv(D), dirv((D + 1) % 6), dirv((D + 1) % 6)), 1, 'berry_bush')
    # path and dock along D
    edge = 8
    for k in range(1, edge):
        p = mul(dirv(D), k)
        put(p, 0, 'polished_stone' if k % 2 == 0 else 'mossrock')
        if k % 3 == 1:
            side = dirv((D + 1) % 6) if (k // 3) % 2 == 0 else dirv((D + 5) % 6)
            put(add(p, side), 1, 'glowstick')
    for j in range(6):
        p = mul(dirv(D), edge + j)
        put(p, 0, 'planks')
        if j % 2 == 0:
            for dy in range(-1, -5, -1):
                put(p, dy, 'heartwood')
        if j == 3:
            put(p, 0, 'planks_slab')
    end = mul(dirv(D), edge + 5)
    for s in (dirv((D + 1) % 6), dirv((D + 5) % 6), add(dirv((D + 1) % 6), dirv(D)),
              add(dirv((D + 5) % 6), dirv(D)), dirv(D)):
        put(add(end, s), 0, 'planks')
    put(add(end, dirv((D + 1) % 6)), 1, 'lantern')
    put(add(end, dirv((D + 5) % 6)), 1, 'lantern')
    put(add(end, dirv(D)), 1, 'chest', (D + 3) % 6)
    for s in (dirv((D + 1) % 6), dirv((D + 5) % 6)):
        for dy in range(-1, -4, -1):
            put(add(end, s), dy, 'heartwood')
    # lighthouse on the shoulder
    L = add(mul(dirv((D + 1) % 6), 4), mul(dirv(D), 2))
    foot = disc(L, 1)
    for p in disc(L, 2):
        for dy in range(-4, 1):
            put(p, dy, 'mossrock' if dy == 0 and hd(p, L) == 2 else 'stone')
    for dy in range(1, 12):
        band = 'bricks' if (dy // 2) % 2 == 0 else 'polished_stone'
        for p in foot:
            if p != L:
                put(p, dy, band)
        # hollow shaft with ladder
        put(L, dy, 'air')
    ladder(L, 1, 11, (D + 3) % 6)
    door_l = add(L, dirv((D + 4) % 6))
    door(door_l, 1, (D + 4) % 6)
    put(add(L, dirv(inland)), 6, 'glass')
    put(add(L, dirv(D)), 8, 'glass')
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
    for s in (dirv(D), dirv((D + 5) % 6)):
        put(add(L, mul(s, 2)), 1, 'glowcap')
    G = add(mul(dirv((D + 4) % 6), 4), mul(dirv((D + 5) % 6), 1))
    for p in disc(G, 1):
        put(p, 0, 'loam')
    plants = ['sprout', 'berry_bush', 'sprout', 'bloom', 'sprout', 'berry_bush', 'petals']
    for i, p in enumerate(disc(G, 1)):
        put(p, 1, plants[i % len(plants)])
    for i, p in enumerate(ringc(G, 2)):
        if hd(p, C) > 4 and (p[0], p[1], 0) not in S.blocks:
            put(p, 1, 'glowstick' if i % 4 == 0 else ('petals' if i % 2 else 'bloom'))
    bench = add(mul(dirv((D + 5) % 6), 4), mul(dirv(D), 3))
    put(bench, 1, 'planks_slab'); put(add(bench, dirv((D + 1) % 6)), 1, 'planks_slab')
    put(add(bench, dirv((D + 5) % 6)), 1, 'lantern')
    put(add(bench, dirv((D + 2) % 6)), 1, 'signpost', D)
    return S


def house(S, C, rad, D, wall='dark_planks', frame='dark_heartwood', roof='shingles',
          floor='packed_earth', storeys=2, open_door=False):
    put, door = S.put, S.door
    for p in disc(C, rad - 1):
        put(p, 0, floor)
    for p in ringc(C, rad):
        for dy in range(1, storeys * 2 + 1):
            put(p, dy, wall)
        put(p, storeys * 2 + 1, frame)
    for k in range(6):
        p = add(C, mul(dirv(k), rad))
        for dy in range(1, storeys * 2 + 2):
            put(p, dy, frame)
    door_p = add(C, mul(dirv(D), rad))
    put(door_p, storeys * 2, wall)
    door(door_p, 1, D, open_=open_door)
    # windows
    for k in ((D + 1) % 6, (D + 2) % 6, (D + 4) % 6, (D + 5) % 6):
        p = add(C, mul(dirv(k), rad))
        put(p, 2, 'glass')
        if storeys >= 2:
            put(p, 4, 'glass')
    for i, rad_r in enumerate(range(rad + 1, -1, -1)):
        for p in (ringc(C, rad_r) if rad_r else [C]):
            put(p, storeys * 2 + 2 + i, roof if rad_r else 'mossy_bricks')
    return door_p


def build_tavern(D=0):
    S = Stamp()
    put = S.put
    C = (0, 0)
    house(S, C, 3, D, wall='wattle', frame='dark_heartwood', roof='thatch',
          floor='packed_earth', storeys=2, open_door=True)
    # chimney
    chim = add(C, mul(dirv((D + 3) % 6), 2))
    for dy in range(6, 10):
        put(chim, dy, 'bricks')
    put(chim, 10, 'ember_lamp')
    put(add(C, dirv((D + 2) % 6)), 1, 'lantern')
    put(add(C, dirv((D + 4) % 6)), 1, 'chest', D)
    put(add(C, dirv((D + 3) % 6)), 1, 'bedroll')
    put(C, 1, 'petals')
    S.ladder(add(C, dirv((D + 1) % 6)), 1, 3, (D + 4) % 6)
    # porch toward the cliff
    for k in range(1, 4):
        for s in (0, -1, 1):
            p = add(mul(dirv(D), k), mul(dirv((D + 1) % 6), s) if s else (0, 0))
            put(p, 0, 'dark_planks')
            if k == 1:
                put(p, 0, 'dark_planks_slab') if s else put(p, 0, 'dark_planks')
    put(mul(dirv(D), 3), 1, 'lantern')
    put(add(mul(dirv(D), 2), dirv((D + 1) % 6)), 1, 'planks_slab')
    put(add(mul(dirv(D), 2), dirv((D + 5) % 6)), 1, 'planks_slab')
    # side cottage
    H = add(mul(dirv((D + 2) % 6), 8), mul(dirv((D + 1) % 6), 2))
    house(S, H, 2, D, wall='planks', frame='heartwood', roof='shingles',
          floor='polished_stone', storeys=1, open_door=False)
    put(add(H, dirv((D + 3) % 6)), 1, 'bedroll')
    put(add(H, dirv((D + 2) % 6)), 1, 'lantern')
    # outdoor tables, sign, flowers
    T = add(mul(dirv((D + 5) % 6), 6), mul(dirv(D), 1))
    put(T, 0, 'packed_earth')
    put(T, 1, 'planks_slab')
    put(add(T, dirv((D + 1) % 6)), 1, 'planks_slab')
    put(add(T, dirv((D + 4) % 6)), 1, 'lantern')
    put(add(C, mul(dirv(D), 4), dirv((D + 5) % 6)), 1, 'signpost', D)
    for i, p in enumerate(ringc(C, 5)):
        if hd(p, C) >= 5 and (p[0], p[1], 0) not in S.blocks and i % 3 == 0:
            put(p, 1, 'bloom' if i % 2 else 'heather')
    put(add(C, mul(dirv((D + 4) % 6), 5)), 1, 'berry_bush')
    put(add(C, mul(dirv((D + 4) % 6), 6)), 1, 'glowstick')
    return S


def build_windmill(D=4):
    # D is the direction toward water; farmhouse sits inland
    S = Stamp()
    put = S.put
    inland = (D + 3) % 6
    M = (0, 0)
    for p in disc(M, 2):
        put(p, 0, 'cobble')
        put(p, 1, 'stone_bricks')
    for dy in range(2, 10):
        for p in ringc(M, 1):
            put(p, dy, 'stone_bricks' if dy % 2 == 0 else 'cobble')
        put(M, dy, 'air')
    S.ladder(M, 2, 9, inland)
    door_p = add(M, dirv(inland))
    S.door(door_p, 2, inland, open_=True)
    put(door_p, 4, 'glass')
    for k in range(6):
        if k != inland:
            put(add(M, dirv(k)), 5, 'glass')
            put(add(M, dirv(k)), 8, 'glass')
    # cap
    for p in disc(M, 2):
        put(p, 10, 'thatch')
    for p in ringc(M, 1):
        put(p, 11, 'thatch')
    put(M, 12, 'thatch')
    put(M, 13, 'lantern')
    # four sails
    hub_h = 8
    arms = (0, 1, 3, 4)
    for a in arms:
        for dist in range(2, 6):
            p = add(M, mul(dirv(a), dist))
            put(p, hub_h + (1 if dist >= 4 else 0), 'pale_planks_slab' if dist % 2 else 'linen')
            if dist == 5:
                put(p, hub_h + 1, 'linen')
        put(add(M, mul(dirv(a), 1)), hub_h, 'pale_heartwood')
    # farmhouse inland
    H = mul(dirv(inland), 9)
    house(S, H, 2, D, wall='cedar_planks', frame='cedar_heartwood', roof='shingles',
          floor='packed_earth', storeys=1, open_door=True)
    put(add(H, dirv((D + 1) % 6)), 1, 'chest', D)
    put(add(H, dirv((D + 2) % 6)), 1, 'bedroll')
    put(add(H, dirv((D + 4) % 6)), 1, 'lantern')
    # fields
    for p in disc(add(mul(dirv((D + 1) % 6), 6), mul(dirv(D), 1)), 3):
        if hd(p, M) > 3 and hd(p, H) > 3:
            put(p, 0, 'farmland')
            put(p, 1, 'skywheat' if (p[0] + p[1]) % 3 else 'sprout')
    for p in disc(add(mul(dirv((D + 5) % 6), 6), mul(dirv(D), 1)), 2):
        if hd(p, M) > 3:
            put(p, 0, 'farmland')
            put(p, 1, 'berry_crop' if (p[0] + 2 * p[1]) % 2 else 'skywheat')
    # fence posts + path
    for k in range(1, 8):
        p = add(M, mul(dirv(inland), k))
        if (p[0], p[1], 0) not in S.blocks:
            put(p, 0, 'packed_earth')
    for i, p in enumerate(ringc(M, 6)):
        if i % 4 == 0 and hd(p, H) > 3 and (p[0], p[1], 1) not in S.blocks:
            put(p, 1, 'glowstick')
    put(add(M, mul(dirv((D + 2) % 6), 4)), 1, 'signpost', D)
    put(add(H, mul(dirv((D + 5) % 6), 3)), 1, 'berry_bush')
    return S


def build_dock(D=4):
    S = Stamp()
    put = S.put
    # dock house on land (origin), pier along D over water
    H = mul(dirv((D + 3) % 6), 3)
    house(S, H, 2, D, wall='cedar_planks', frame='cedar_heartwood', roof='thatch',
          floor='planks', storeys=1, open_door=True)
    put(add(H, dirv((D + 2) % 6)), 1, 'chest', D)
    put(add(H, dirv((D + 4) % 6)), 1, 'lantern')
    put(add(H, dirv((D + 1) % 6)), 1, 'tinker_bench', (D + 4) % 6)
    # pier
    for k in range(0, 9):
        for s in (-1, 0, 1):
            p = add(mul(dirv(D), k), mul(dirv((D + 1) % 6), s) if s else (0, 0))
            put(p, 0, 'planks')
            if s == 0 and k % 2 == 0:
                for dy in range(-1, -5, -1):
                    put(p, dy, 'heartwood')
        if k % 3 == 2:
            put(add(mul(dirv(D), k), dirv((D + 1) % 6)), 1, 'lantern')
            put(add(mul(dirv(D), k), dirv((D + 5) % 6)), 1, 'glowstick')
    # sky-boat at the end: elongated hull
    B = mul(dirv(D), 11)
    for k in range(-1, 5):
        for s in (-1, 0, 1):
            p = add(B, mul(dirv(D), k), mul(dirv((D + 1) % 6), s) if s else (0, 0))
            put(p, 0, 'dark_planks')
            if s != 0:
                put(p, 1, 'dark_planks_slab')
            if abs(s) == 1:
                for dy in range(-1, -3, -1):
                    put(p, dy, 'dark_heartwood')
    # pointed bow
    put(add(B, mul(dirv(D), 5)), 0, 'dark_heartwood')
    put(add(B, mul(dirv(D), 5)), 1, 'dark_planks_slab')
    # mast, sail, lamp
    mast = add(B, mul(dirv(D), 1))
    for dy in range(1, 7):
        put(mast, dy, 'heartwood')
    for dy in range(2, 6):
        put(add(mast, dirv((D + 3) % 6)), dy, 'linen')
        put(add(mast, mul(dirv((D + 3) % 6), 2)), dy, 'linen')
    put(mast, 7, 'lantern')
    put(add(B, dirv((D + 1) % 6)), 1, 'chest', D)
    put(add(B, dirv((D + 5) % 6)), 1, 'bedroll')
    S.ladder(add(B, mul(dirv((D + 3) % 6), 1)), 1, 3, D)
    put(add(H, mul(dirv(D), 2), dirv((D + 5) % 6)), 1, 'signpost', D)
    put(add(H, mul(dirv((D + 5) % 6), 3)), 1, 'reeds')
    put(add(H, mul(dirv((D + 1) % 6), 3)), 1, 'reeds')
    return S


def build_keep(D=0):
    S = Stamp()
    put = S.put
    C = (0, 0)
    rad = 5
    # courtyard
    for p in disc(C, rad - 1):
        put(p, 0, 'packed_earth' if hd(p, C) else 'cobble')
    put(C, 1, 'glimmer_font')
    # walls
    for p in ringc(C, rad):
        for dy in range(0, 7):
            put(p, dy, 'stone_bricks' if dy % 2 == 0 else 'cobble')
        put(p, 7, 'stone_bricks_slab')
    # merlons
    for i, p in enumerate(ringc(C, rad)):
        if i % 2 == 0:
            put(p, 8, 'stone_bricks')
    # corner towers (every other corner of the hex)
    for k in range(0, 6, 2):
        T = add(C, mul(dirv(k), rad))
        for p in disc(T, 1):
            for dy in range(0, 11):
                if p == T and dy >= 1:
                    put(p, dy, 'air')
                else:
                    put(p, dy, 'stone_bricks')
        S.ladder(T, 1, 10, (k + 3) % 6)
        for p in disc(T, 1):
            put(p, 11, 'polished_stone')
        put(T, 12, 'polished_stone')
        put(T, 13, 'lumen_lamp' if k % 4 == 0 else 'ember_lamp')
        put(add(T, dirv((k + 1) % 6)), 12, 'crimson_cloth')
        put(add(T, dirv((k + 5) % 6)), 12, 'dusk_cloth')
        for p in ringc(T, 1):
            put(p, 6, 'glass')
    # gate
    gate = add(C, mul(dirv(D), rad))
    S.door(gate, 1, D, open_=True)
    put(gate, 3, 'stone_bricks')
    put(gate, 4, 'stone_bricks')
    put(add(gate, dirv((D + 1) % 6)), 5, 'lantern')
    put(add(gate, dirv((D + 5) % 6)), 5, 'lantern')
    # inner keep
    K = add(C, mul(dirv((D + 3) % 6), 2))
    for p in disc(K, 1):
        for dy in range(0, 6):
            put(p, dy, 'carved_stone' if dy == 0 else 'stone_bricks')
        put(p, 6, 'slate_tiles')
    put(K, 7, 'slate_tiles')
    S.door(add(K, dirv(D)), 1, D)
    put(add(K, dirv((D + 2) % 6)), 2, 'glass')
    put(add(K, dirv((D + 4) % 6)), 2, 'glass')
    put(add(K, dirv((D + 1) % 6)), 1, 'chest', D)
    put(add(K, dirv((D + 5) % 6)), 1, 'lantern')
    # approach
    for k in range(1, 4):
        p = add(C, mul(dirv(D), rad + k))
        put(p, 0, 'stone_slab' if k < 3 else 'cobble')
        if k == 3:
            put(add(p, dirv((D + 1) % 6)), 1, 'signpost', D)
            put(add(p, dirv((D + 5) % 6)), 1, 'glowstick')
    return S


def build_temple(D=0):
    S = Stamp()
    put = S.put
    C = (0, 0)
    # stepped platform
    for p in disc(C, 5):
        put(p, 0, 'carved_stone' if hd(p, C) <= 3 else 'polished_rosestone')
    for p in disc(C, 3):
        put(p, 1, 'mosaic' if hd(p, C) else 'polished_starstone')
    put(C, 2, 'waystone')
    put(C, 3, 'aether_lamp')
    # columns
    for k in range(6):
        p = add(C, mul(dirv(k), 3))
        for dy in range(2, 7):
            put(p, dy, 'carved_stone')
        put(p, 7, 'polished_starstone')
        put(p, 8, 'violet_glass')
        put(add(C, mul(dirv(k), 4)), 2, 'aether_lamp' if k % 2 == 0 else 'lantern')
    # lintel ring
    for p in ringc(C, 3):
        if p not in [add(C, mul(dirv(k), 3)) for k in range(6)]:
            put(p, 6, 'polished_rosestone')
    # shallow pool off to one side
    P = add(C, mul(dirv((D + 3) % 6), 6))
    for p in disc(P, 2):
        put(p, 0, 'polished_rosestone')
        if hd(p, P) <= 1:
            put(p, 1, 'water')
        else:
            put(p, 1, 'heather' if (p[0] + p[1]) % 2 else 'bloom')
    # benches and garden
    for k in (D, (D + 2) % 6, (D + 4) % 6):
        b = add(C, mul(dirv(k), 5))
        put(b, 1, 'pale_planks_slab')
        put(add(b, dirv((k + 1) % 6)), 1, 'pale_planks_slab')
    for i, p in enumerate(ringc(C, 6)):
        if (p[0], p[1], 0) not in S.blocks:
            put(p, 0, 'loam')
            put(p, 1, ('heather', 'bloom', 'petals', 'wildflower', 'sprout')[i % 5])
    # entry steps toward D
    for k in range(1, 4):
        for s in (-1, 0, 1):
            p = add(mul(dirv(D), 5 + k), mul(dirv((D + 1) % 6), s) if s else (0, 0))
            put(p, 0, 'polished_stone_slab' if k > 1 else 'carved_stone')
    put(add(mul(dirv(D), 8), dirv((D + 1) % 6)), 1, 'signpost', D)
    put(add(mul(dirv(D), 8), dirv((D + 5) % 6)), 1, 'glowstick')
    return S


def build_treehouse(D=0):
    S = Stamp()
    put = S.put
    T = (0, 0)
    # trunk
    for p in disc(T, 1):
        for dy in range(-2, 14):
            put(p, dy, 'cedar_heartwood')
    # roots
    for k in range(6):
        put(add(T, dirv(k)), 0, 'cedar_heartwood')
        put(add(T, mul(dirv(k), 2)), 0, 'cedar_heartwood')
    # lower platform
    for p in disc(T, 3):
        if hd(p, T) >= 2:
            put(p, 7, 'cedar_planks')
    # upper cabin platform
    for p in disc(T, 3):
        put(p, 11, 'cedar_planks')
    house(S, T, 2, D, wall='cedar_planks', frame='cedar_heartwood', roof='thatch',
          floor='cedar_planks', storeys=1, open_door=True)
    # the house overwrites trunk top; restore a trunk through the floor
    for dy in range(1, 4):
        put(T, dy, 'cedar_heartwood')
    put(add(T, dirv((D + 2) % 6)), 12, 'lantern')  # house floor is dy 11? house starts at 0 relative...
    # Oops: house() places at dy 0 as floor. We need the cabin on the upper platform (dy 11).
    # Rebuild cabin manually at height 12 and clear the mistaken ground house later.
    return S  # will fix after — actually I'll rewrite this function properly


def build_treehouse_fixed(D=0):
    S = Stamp()
    put = S.put
    T = (0, 0)
    for p in disc(T, 1):
        for dy in range(-2, 16):
            put(p, dy, 'cedar_heartwood')
    for k in range(6):
        put(add(T, dirv(k)), 0, 'cedar_heartwood')
        put(add(T, mul(dirv(k), 2)), -1, 'cedar_heartwood')
        put(add(T, mul(dirv(k), 2)), 0, 'cedar_heartwood')
    # mid platform + rail
    for p in disc(T, 3):
        if hd(p, T) >= 2:
            put(p, 7, 'cedar_planks')
        if hd(p, T) == 3:
            put(p, 8, 'cedar_planks_slab')
    put(add(T, mul(dirv(D), 3)), 8, 'lantern')
    # ladder from ground to mid, mid to cabin
    S.ladder(add(T, mul(dirv(D), 2)), 1, 7, (D + 3) % 6)
    S.ladder(add(T, mul(dirv((D + 3) % 6), 2)), 8, 12, D)
    # cabin on upper platform
    C_h = 12
    for p in disc(T, 3):
        put(p, C_h, 'cedar_planks')
    for p in ringc(T, 2):
        for dy in range(C_h + 1, C_h + 4):
            put(p, dy, 'cedar_planks')
        put(p, C_h + 4, 'cedar_heartwood')
    door_p = add(T, mul(dirv(D), 2))
    S.door(door_p, C_h + 1, D, open_=True)
    put(door_p, C_h + 3, 'cedar_planks')
    for k in ((D + 1) % 6, (D + 2) % 6, (D + 4) % 6, (D + 5) % 6):
        put(add(T, mul(dirv(k), 2)), C_h + 2, 'glass')
    for rad, dy in ((3, C_h + 5), (2, C_h + 5), (1, C_h + 6), (0, C_h + 7)):
        for p in (ringc(T, rad) if rad else [T]):
            put(p, dy, 'thatch')
    put(add(T, dirv((D + 2) % 6)), C_h + 1, 'bedroll')
    put(add(T, dirv((D + 4) % 6)), C_h + 1, 'chest', D)
    put(add(T, dirv((D + 5) % 6)), C_h + 1, 'lantern')
    # hanging lamps
    put(add(T, mul(dirv((D + 1) % 6), 3)), 9, 'lantern')
    put(add(T, mul(dirv((D + 4) % 6), 3)), 9, 'glowstick')
    # second platform + plank bridge
    U = add(mul(dirv((D + 2) % 6), 7))
    for p in disc(U, 1):
        for dy in range(0, 8):
            put(p, dy, 'cedar_heartwood')
        put(p, 7, 'cedar_planks')
    for k in range(1, 6):
        p = add(T, mul(dirv((D + 2) % 6), 2 + k))
        if hd(p, T) > 3:
            put(p, 7, 'cedar_planks_slab')
            if k % 2 == 0:
                put(p, 8, 'glowstick')
    put(U, 8, 'lantern')
    put(add(U, dirv(D)), 8, 'planks_slab')
    put(add(U, dirv((D + 3) % 6)), 8, 'chest', D)
    # modest canopy halo (kept close so the orbit can stay outside)
    for p in ringc(T, 3):
        put(p, 16, 'canopy')
        if hd(p, T) == 3 and (p[0] + p[1]) % 2 == 0:
            put(p, 15, 'canopy')
    for p in ringc(T, 2):
        put(p, 17, 'canopy')
    put(T, 16, 'canopy')
    put(add(T, mul(dirv(D), 5)), 1, 'signpost', D)
    put(add(T, mul(dirv((D + 5) % 6), 4)), 1, 'mushroom')
    put(add(T, mul(dirv((D + 1) % 6), 4)), 1, 'mushroom')
    put(add(T, mul(dirv((D + 4) % 6), 5)), 1, 'shrub')
    return S


def build_bridge(D=0, span=8):
    # origin is the near shore; far shore is mul(dirv(D), span)
    S = Stamp()
    put = S.put
    A = (0, 0)
    B = mul(dirv(D), span)
    # stone abutments
    for origin in (A, B):
        for p in disc(origin, 1):
            for dy in range(-3, 2):
                put(p, dy, 'stone_bricks')
            put(p, 2, 'polished_stone')
        put(origin, 3, 'lantern')
    # span with a slight sag of slabs in the middle? keep level, posts down
    mid = span // 2
    for k in range(0, span + 1):
        p = mul(dirv(D), k)
        put(p, 1, 'planks' if abs(k - mid) > 1 else 'planks_slab')
        for s in (dirv((D + 1) % 6), dirv((D + 5) % 6)):
            put(add(p, s), 1, 'planks')
            if k % 2 == 0:
                put(add(p, s), 2, 'glowstick' if k % 4 == 0 else 'planks_slab')
        if k % 2 == 0:
            for dy in range(0, -4, -1):
                put(p, dy, 'heartwood')
    # little covered mid-span
    M = mul(dirv(D), mid)
    for s in ( (0, 0), dirv((D + 1) % 6), dirv((D + 5) % 6) ):
        put(add(M, s), 3, 'shingles')
        put(add(M, s), 4, 'shingles' if s == (0, 0) else 'shingles_slab')
    put(M, 2, 'lantern')
    # hut on the far isle
    H = add(B, mul(dirv(D), 4))
    house(S, H, 2, (D + 3) % 6, wall='planks', frame='heartwood', roof='shingles',
          floor='polished_stone', storeys=1, open_door=True)
    put(add(H, dirv((D + 1) % 6)), 1, 'bedroll')
    put(add(H, dirv((D + 2) % 6)), 1, 'chest', (D + 3) % 6)
    put(add(H, dirv((D + 4) % 6)), 1, 'lantern')
    put(add(A, mul(dirv((D + 3) % 6), 3)), 1, 'signpost', D)
    put(add(A, mul(dirv((D + 2) % 6), 2)), 1, 'bloom')
    put(add(B, mul(dirv((D + 1) % 6), 3)), 1, 'bloom')
    return S


# ---------------- camera tuner ----------------
def longest_clear_arc(sc, world, n=96, min_frac=0.28):
    # probe a full circle regardless of any existing arc
    saved_arc = sc.camera.pop('arc', None)
    angs = [2 * math.pi * i / n for i in range(n)]
    good = []
    build = SC._build_cells(sc)
    for ang in angs:
        pos, tgt = SC.orbit_pose(sc, ang)
        clip = SC._cam_in_solid(world, *pos)
        hide = SC._ray_hits_terrain(world, pos, tgt, build)
        good.append(not clip and not hide)
    if saved_arc is not None:
        sc.camera['arc'] = saved_arc
    # circular longest run
    ext = good + good
    best = (0, 0, 0)  # length, start, end exclusive
    i = 0
    while i < len(ext):
        if not ext[i]:
            i += 1
            continue
        j = i
        while j < len(ext) and ext[j]:
            j += 1
        if j - i > best[0]:
            best = (j - i, i, j)
        i = j
    length, a, b = best
    if length >= n:  # whole circle
        return None
    if length / n < min_frac:
        return None
    # map back to [0, 2pi), shrink by one sample on each end
    a = a % n
    b = (b - 1) % n
    if length > 4:
        a = (a + 1) % n
        b = (b - 1) % n
    return [angs[a], angs[b] if b >= a else angs[b] + 2 * math.pi]


def tune(sc, world=None):
    world = world or SC.stamped_world(sc)
    cam = sc.camera
    cam.setdefault('radius', 44.0)
    cam.setdefault('height', 22.0)
    cam.setdefault('target_dy', 3.0)
    # keep the orbit outside the build's footprint
    fx, fz = sc.focus()
    extent = 8.0
    for q, r in sc.cols:
        x, z = center(q, r)
        extent = max(extent, math.hypot(x - fx, z - fz))
    cam['radius'] = max(float(cam['radius']), extent + 10.0)
    cam.pop('arc', None)
    sc.camera = cam
    offsets = [(0, 0), (-8, 0), (8, 0), (0, -8), (0, 8), (-6, 6), (6, -6)]
    for step in range(16):
        for cx, cz in offsets:
            if cx or cz:
                cam['center'] = [cx, cz]
            elif 'center' in cam and step == 0:
                pass  # keep a pre-set center on the first pass
            else:
                cam.pop('center', None)
            sc.camera = cam
            rep = SC.path_report(sc, world, n=96)
            print(f"  tune {sc.name}: clips={len(rep['clips'])} hides={len(rep['hides'])}/{rep['n']} "
                  f"r={cam['radius']:.1f} h={cam['height']:.1f} c={cam.get('center')} arc={cam.get('arc')}")
            if rep['ok']:
                return world, rep
        cam.pop('center', None)
        cam['height'] = float(cam['height']) + 2.0
        cam['radius'] = float(cam['radius']) + 2.5
        if cam['height'] >= 26 or step >= 2:
            arc = longest_clear_arc(sc, world)
            if arc:
                cam['arc'] = [round(arc[0], 3), round(arc[1], 3)]
                rep2 = SC.path_report(sc, world, n=72)
                print(f"  arc {cam['arc']} clips={len(rep2['clips'])} hides={len(rep2['hides'])} ok={rep2['ok']}")
                if rep2['ok']:
                    return world, rep2
                cam.pop('arc', None)
        if cam['height'] > 44 or cam['radius'] > 76:
            break
    # last try: high and wide + best arc
    arc = longest_clear_arc(sc, world, min_frac=0.22)
    if arc:
        cam['arc'] = [round(arc[0], 3), round(arc[1], 3)]
    rep = SC.path_report(sc, world, n=96)
    print(f"  final {sc.name}: clips={len(rep['clips'])} hides={len(rep['hides'])} cam={cam} ok={rep['ok']}")
    return world, rep


def spec(name, author, seed, q, r, top, stamp, camera, flatten, site_extra=None):
    site = dict(q=q, r=r, top=top)
    if site_extra:
        site.update(site_extra)
    data = dict(name=name, author=author, seed_text=seed, gen={}, site=site,
                camera=dict(camera), flatten=flatten, blocks=stamp.items())
    fname = {
        'Lighthouse Cottage': 'lighthouse_cottage.json',
        'Cliffside Tavern': 'cliffside_tavern.json',
        'Windmill Farm': 'windmill_farm.json',
        'Sky-boat Dock': 'skyboat_dock.json',
        'High Keep': 'high_keep.json',
        'Rose Temple': 'rose_temple.json',
        'Cedar Treehouse': 'cedar_treehouse.json',
        'Twin Isles Bridge': 'twin_isles_bridge.json',
    }[name]
    return data, os.path.join(ROOT, fname)


BUILDS = [
    dict(name='Lighthouse Cottage', author='a cozy evening in Tidewake', seed='keeper-of-tides',
         q=79, r=3, top=51, D=5, stamp=lambda D: build_lighthouse(D),
         camera=dict(radius=46.0, height=24.0, target_dy=3.0, yaw_offset=-20.0, speed=0.035, phase=0.18),
         flatten=dict(radius=7, blend=6, clear_up=28, clear_trees=14, flowers=16)),
    dict(name='Cliffside Tavern', author='a fen-side stop for wanderers', seed='tavern-cliff',
         q=115, r=-2, top=71, D=0, stamp=lambda D: build_tavern(D),
         camera=dict(radius=44.0, height=20.0, target_dy=3.0, yaw_offset=16.0, speed=0.032, phase=0.26),
         flatten=dict(radius=8, blend=5, clear_up=24, clear_trees=14, flowers=12)),
    dict(name='Windmill Farm', author='a cedar lea at harvest', seed='salt-wind-bay',
         q=103, r=-1, top=72, D=4, stamp=lambda D: build_windmill(D),
         camera=dict(radius=48.0, height=22.0, target_dy=4.0, yaw_offset=-18.0, speed=0.03, phase=0.14),
         flatten=dict(radius=10, blend=6, clear_up=22, clear_trees=16, flowers=10)),
    dict(name='Sky-boat Dock', author='a quay at the cloud shore', seed='windward-isle',
         q=168, r=-35, top=76, D=4, stamp=lambda D: build_dock(D),
         camera=dict(radius=48.0, height=20.0, target_dy=3.0, yaw_offset=22.0, speed=0.033, phase=0.22),
         flatten=dict(radius=6, blend=5, clear_up=20, clear_trees=14, flowers=8)),
    dict(name='High Keep', author='a cloudstep hold', seed='lantern-point',
         q=-62, r=-24, top=105, D=1, stamp=lambda D: build_keep(D),
         camera=dict(radius=52.0, height=26.0, target_dy=5.0, yaw_offset=-14.0, speed=0.028, phase=0.08),
         flatten=dict(radius=8, blend=5, clear_up=26, clear_trees=16, flowers=6)),
    dict(name='Rose Temple', author='a quiet garden above the bay', seed='salt-wind-bay',
         q=67, r=25, top=80, D=3, stamp=lambda D: build_temple(D),
         camera=dict(radius=46.0, height=20.0, target_dy=3.0, yaw_offset=12.0, speed=0.031, phase=0.20),
         flatten=dict(radius=8, blend=5, clear_up=22, clear_trees=14, flowers=0)),
    dict(name='Cedar Treehouse', author='a loft in the high cedars', seed='ember-croft',
         q=74, r=123, top=48, D=0, stamp=lambda D: build_treehouse_fixed(D),
         camera=dict(radius=44.0, height=28.0, target_dy=8.0, yaw_offset=-24.0, speed=0.03, phase=0.30),
         flatten=dict(radius=7, blend=5, clear_up=30, clear_trees=16, flowers=8)),
    dict(name='Twin Isles Bridge', author='a crossing on the salt wind', seed='twin-isles',
         q=-95, r=21, top=45, D=0, stamp=lambda D: build_bridge(D, span=8),
         camera=dict(radius=48.0, height=22.0, target_dy=2.0, yaw_offset=18.0, speed=0.03, phase=0.16),
         flatten=dict(radius=0, blend=0, clear_up=0, clear_trees=14, flowers=0)),
]


def build_all(tune_cameras=True):
    results = []
    for b in BUILDS:
        st = b['stamp'](b['D'])
        data, path = spec(b['name'], b['author'], b['seed'], b['q'], b['r'], b['top'], st, b['camera'], b['flatten'],
                          site_extra={'dock_dir': b['D']})
        write(path, data)
        if tune_cameras:
            sc = SC.Showcase(data)
            # reset applied between worlds
            world, rep = tune(sc)
            # write back tuned camera
            data['camera'] = sc.camera
            # round camera numbers
            cam = data['camera']
            for k, v in list(cam.items()):
                if k == 'arc' or not isinstance(v, float):
                    continue
                cam[k] = round(v, 3 if k in ('speed', 'phase') else 2)
            write(path, data)
            results.append((b['name'], path, sc.camera, rep))
        else:
            results.append((b['name'], path, data['camera'], None))
    return results


def retune_seeds():
    """Move stale seed-only skies onto current v2 spawns and clear their orbits."""
    from tidewake.session import find_spawn
    updated = []
    for spec in SC.SEED_SHOWS:
        gen = Generator(seed_from_text(spec['seed_text']), GS.normalize({}))
        q, r, top, sp = find_spawn(gen)
        if sp:
            q, r, top = sp['q'], sp['r'], sp['top']
        spec['site'] = dict(q=int(q), r=int(r), top=int(top))
        cam = spec.setdefault('camera', {})
        cam.setdefault('radius', 50.0)
        cam.setdefault('height', 24.0)
        cam.setdefault('target_dy', 4.0)
        cam.pop('arc', None)
        data = dict(spec)
        data.setdefault('kind', 'seed')
        data.setdefault('blocks', [])
        data['gen'] = GS.normalize({})
        sc = SC.Showcase(data)
        world, rep = tune(sc)
        for k, v in list(sc.camera.items()):
            if k == 'arc' or not isinstance(v, float):
                continue
            sc.camera[k] = round(v, 3 if k in ('speed', 'phase') else 2)
        spec['camera'] = sc.camera
        updated.append((spec, rep))
    return updated


if __name__ == '__main__':
    args = set(sys.argv[1:])
    if not args or 'builds' in args or 'all' in args:
        build_all(tune_cameras='notune' not in args)
    if 'seeds' in args or 'all' in args:
        recs = retune_seeds()
        print('SEED_SHOWS = [')
        for spec, rep in recs:
            print('   ', spec, ',')
            print('   # clips', len(rep['clips']), 'hides', len(rep['hides']), 'ok', rep['ok'])
        print(']')

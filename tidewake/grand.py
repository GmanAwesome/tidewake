"""1.4.4 (generator v6): grand procedural structures.

Big, rare landmarks that span many chunks. Each GRAND region (14 x 14 chunks)
rolls once from the sky seed: maybe a structure, which kind, where, and a
private seed. The builder runs once per process into a cell dict that is
cached and bucketed by chunk, so every chunk it overlaps stamps its own part
and the pieces always line up. Builders are modular and seeded: sizes,
shapes, palettes, layouts and set dressing all vary, so no two match.

Kinds (weights in KINDS):
  hot_air_balloon  sky   striped / banded / harlequin / spiral / chevron / patchwork envelopes,
                         round, teardrop, tall, pumpkin or onion shapes, basket / deck / boat /
                         cabin gondolas, ropes, burner glow, cargo, pennants; sometimes a pair
  sky_city         sky   several cloud-and-stone platforms at different heights, towers, domes,
                         gardens and houses, joined by bridges, with a central spire
  floating_fortress sky  an inverted rock mountain with a walled castle, towers and keep
  world_tree       land  a giant tree with spiral stairs, branch platforms, huts and rope bridges
  colossus         land  a robed guardian statue holding a lantern or staff; some are ruined
  megaspire        land  a tower up to ~250 layers: buttressed, pagoda or crystal styles
  leviathan_wreck  land  a crashed sky-leviathan skeleton or a wrecked airship with its cargo
  titan_ruins      land  giant broken columns, a great arch, a fallen head, rubble and moss
  village          land  5-13 seeded houses of 1-3 storeys round a plaza with a well or lamp,
                         gardens, market stalls and paths
  airship          sky   an intact flying airship: hull, cabin, propellers, striped envelope, rigging
  watchtower       land  the small end: a stone tower with a lookout and roof
Older skies (v5 and below) never call this module.
"""
import math
import random

import numpy as np

from .config import CHUNK, LAYERS, LAYER, CLOUD_SEA, SQ3, HEX
from .hexgrid import center, hex_distance, DIRS, ring as hex_ring
from . import materials as MT

M = MT.ID
REGION = 14                      # chunks per side of a grand region
CHANCE = 0.546                   # share of regions that hold a grand structure (1.4.6: 0.42 x 1.3)
HUES = ('rose', 'ember', 'honey', 'leaf', 'moss', 'tide', 'sky', 'indigo',
        'violet', 'orchid', 'blush', 'cocoa', 'snow', 'pearl', 'ash', 'ink')
BRIGHT = ('rose', 'ember', 'honey', 'leaf', 'tide', 'sky', 'indigo', 'violet', 'orchid', 'blush', 'snow')
KINDS = [('hot_air_balloon', 18), ('sky_city', 8), ('floating_fortress', 8), ('world_tree', 12),
         ('colossus', 10), ('megaspire', 9), ('leviathan_wreck', 10), ('titan_ruins', 11),
         ('village', 12), ('airship', 9), ('watchtower', 8)]
SKY_KINDS = {'hot_air_balloon', 'sky_city', 'floating_fortress', 'airship'}
LOOT_SKY = 7


def _m(name, fb='stone'):
    return M[name] if name in M else M[fb]


# ---------------------------------------------------------------------------
# canvas
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, gen=None):
        self.cells = {}
        self.gen = gen
        self.lamps = 0
        self._ground = {}

    def put(self, q, r, y, mat, meta=0):
        if mat is None or not (1 <= y < LAYERS - 2):
            return
        self.cells[(int(q), int(r), int(y))] = (int(mat), int(meta))

    def get(self, q, r, y):
        v = self.cells.get((q, r, y))
        return v[0] if v else None

    def lamp(self, q, r, y, mat):
        """Cap point lights per structure; extra lamps become their glass shade."""
        if self.lamps < 18:
            self.lamps += 1
            self.put(q, r, y, mat)
        else:
            self.put(q, r, y, M['glass'])

    def chest(self, q, r, y):
        self.put(q, r, y, M['chest'], (LOOT_SKY & 15) << 3)

    def col(self, q, r, y0, y1, mat):
        for y in range(int(y0), int(y1) + 1):
            self.put(q, r, y, mat)

    def disk(self, q, r, y, rad, mat):
        rad = int(rad)
        for dq in range(-rad, rad + 1):
            for dr in range(-rad, rad + 1):
                if hex_distance(0, 0, dq, dr) <= rad:
                    self.put(q + dq, r + dr, y, mat)

    def ring(self, q, r, y, rad, mat):
        for a, b in hex_ring(q, r, int(rad)):
            self.put(a, b, y, mat)

    def round_cells(self, q, r, rad):
        """Cells within a round world-space radius (in cell spacings): (q, r, d, angle)."""
        x0, z0 = center(q, r)
        n = int(rad) + 2
        out = []
        for dq in range(-n, n + 1):
            for dr in range(-n, n + 1):
                x, z = center(q + dq, r + dr)
                d = math.hypot(x - x0, z - z0) / (HEX * SQ3)
                if d <= rad + 0.01:
                    out.append((q + dq, r + dr, d, math.atan2(z - z0, x - x0)))
        return out

    def line3(self, q0, r0, y0, q1, r1, y1, mat, thick=0):
        x0, z0 = center(q0, r0)
        x1, z1 = center(q1, r1)
        n = int(max(abs(hex_distance(q0, r0, q1, r1)), abs(y1 - y0) * LAYER / SQ3) * 1.5) + 1
        from .hexgrid import cell_at
        for i in range(n + 1):
            t = i / n
            x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
            y = int(round(y0 + (y1 - y0) * t))
            a, b = cell_at(x, z)
            if thick:
                self.disk(a, b, y, thick, mat)
            else:
                self.put(a, b, y, mat)

    # terrain
    def ground_many(self, qs, rs):
        qs = np.asarray(qs, np.int64)
        rs = np.asarray(rs, np.int64)
        c = self.gen.columns(qs, rs)
        top = np.where(c['land'], c['top'], -1)
        return top, c

    def prefetch(self, q, r, rad):
        qs, rs = [], []
        for dq in range(-rad, rad + 1):
            for dr in range(-rad, rad + 1):
                qs.append(q + dq)
                rs.append(r + dr)
        t, _ = self.ground_many(qs, rs)
        for a, b, v in zip(qs, rs, t):
            self._ground[(a, b)] = int(v)

    def ground(self, q, r):
        key = (q, r)
        if key not in self._ground:
            t, _ = self.ground_many([q], [r])
            self._ground[key] = int(t[0])
        return self._ground[key]

    def foundation(self, cells, y, mat, cap=None):
        """Fill each (q, r) from its ground (or a short pier) up to layer y."""
        qs = [c[0] for c in cells]
        rs = [c[1] for c in cells]
        if not qs:
            return
        tops, _ = self.ground_many(qs, rs)
        for (q, r), t in zip(zip(qs, rs), tops):
            lo = int(t) + 1 if t >= 0 else y - 6
            lo = max(lo, y - 40)
            for yy in range(lo, y):
                self.put(q, r, yy, mat)
            self.put(q, r, y, cap if cap is not None else mat)


def _palette(rng, n=None, bright=False):
    pool = list(BRIGHT if bright else HUES)
    rng.shuffle(pool)
    n = n or rng.randint(3, 6)
    return pool[:n]


def _stone_set(rng):
    return rng.choice([
        ('chalk', 'chalk_bricks', 'polished_chalk', 'chalk_tiles'),
        ('sandstone', 'sandstone_bricks', 'polished_sandstone', 'sandstone_tiles'),
        ('basalt', 'basalt_bricks', 'polished_basalt', 'basalt_tiles'),
        ('pale_stone', 'stone_bricks', 'polished_pale_stone', 'stone_tiles'),
        ('rosestone', 'rosestone_bricks', 'polished_rosestone', 'rosestone_tiles'),
        ('slate', 'slate_bricks', 'polished_slate', 'slate_tiles'),
        ('starstone', 'lavender_bricks', 'polished_starstone', 'starstone_tiles'),
    ])


def _wood_set(rng):
    return rng.choice([('heartwood', 'planks', 'planks_slab'), ('cedar_heartwood', 'cedar_planks', 'cedar_planks_slab'),
                       ('pale_heartwood', 'pale_planks', 'pale_planks_slab'),
                       ('dark_heartwood', 'dark_planks', 'dark_planks_slab')])


# ---------------------------------------------------------------------------
# hot air balloons
# ---------------------------------------------------------------------------
def _envelope_radius(shape, t, R, ang, lobes):
    """t in [-1, 1] bottom..top -> radius (cells)."""
    if shape == 'round':
        rad = R * math.sqrt(max(0.0, 1 - t * t))
        if t < 0:
            rad *= 1 - 0.45 * (-t) ** 1.6
    elif shape == 'teardrop':
        rad = R * math.sqrt(max(0.0, 1 - t * t)) * (1 - 0.6 * max(0.0, -t))
    elif shape == 'tall':
        rad = R * 0.85 * math.sqrt(max(0.0, 1 - t ** 4)) * (1 - 0.55 * max(0.0, -t) ** 1.3)
    elif shape == 'onion':
        rad = R * math.sqrt(max(0.0, 1 - t * t)) * (1 + 0.25 * math.sin(max(0.0, t) * math.pi)) \
            * (1 - 0.8 * max(0.0, t) ** 3) * (1 - 0.5 * max(0.0, -t))
    else:  # pumpkin
        rad = R * math.sqrt(max(0.0, 1 - t * t)) * (1 - 0.40 * max(0.0, -t) ** 1.4)
    if lobes:
        rad *= 1 + 0.07 * math.cos(lobes * ang)
    return rad


def build_hot_air_balloon(cv, rng, q, r, y, R=None):
    R = R or rng.uniform(10.0, 19.0)
    shape = rng.choice(['round', 'teardrop', 'tall', 'pumpkin', 'onion'])
    pattern = rng.choice(['gores', 'bands', 'harlequin', 'spiral', 'chevron', 'patch', 'rainbow'])
    hues = _palette(rng, rng.randint(3, 7), bright=True)
    if pattern == 'rainbow':
        hues = ['rose', 'ember', 'honey', 'leaf', 'tide', 'sky', 'indigo', 'violet']
    gores = rng.choice([8, 12, 16, 24])
    lobes = gores if shape == 'pumpkin' else 0
    accent = rng.choice(['patterned_tile', 'woven_panel', 'stained_glass', 'terrazzo'])
    trim = rng.choice(['brass', 'copper', 'snow_terrazzo', 'ink_terrazzo'])
    Hy = R * {'round': 1.1, 'teardrop': 1.25, 'tall': 1.55, 'pumpkin': 1.0, 'onion': 1.35}[shape]
    span = int(Hy / LAYER)
    x0, z0 = center(q, r)
    n = int(R * 1.35) + 2
    cellsxy = []
    for dq in range(-n, n + 1):
        for dr in range(-n, n + 1):
            x, z = center(q + dq, r + dr)
            cellsxy.append((q + dq, r + dr, math.hypot(x - x0, z - z0) / SQ3, math.atan2(z - z0, x - x0)))
    mouth_y = y - span
    mouth_r = 1.0
    for dy in range(-span, span + 1):
        t = dy / span
        tn = (dy + 1) / span
        for a, b, d, ang in cellsxy:
            rad = _envelope_radius(shape, t, R, ang, lobes)
            if rad < 0.5:
                continue
            inner = max(_envelope_radius(shape, min(1.0, tn), R, ang, lobes) if dy >= 0 else
                        _envelope_radius(shape, max(-1.0, (dy - 1) / span), R, ang, lobes), rad - 1.15)
            inner = min(inner, rad - 0.9)
            if not (inner < d <= rad):
                continue
            g = int(((ang + math.pi) / (2 * math.pi)) * gores) % gores
            band = (dy + span) // 3
            if pattern == 'gores':
                idx = g
            elif pattern == 'bands' or pattern == 'rainbow':
                idx = (dy + span) * len(hues) // (2 * span + 1)
            elif pattern == 'harlequin':
                idx = g * 12 // gores + (dy + span) // 6
            elif pattern == 'spiral':
                idx = int(g + (dy + span) / 2.5)
            elif pattern == 'chevron':
                idx = (dy + span + abs((g % 6) - 3)) // 3
            else:
                # patchwork: big panels, not per-cell noise
                idx = (g * 12 // gores) * 3 + ((dy + span) // max(3, span // 3)) * 5
            hue = hues[idx % len(hues)]
            fam = 'terrazzo'
            if accent != 'terrazzo' and (dy + span) % 7 == 3:
                fam = accent
            if abs(dy - int(span * 0.15)) == 0 and pattern != 'rainbow':
                mat = _m(trim)
            else:
                mat = M[f'{hue}_{fam}']
            cv.put(a, b, y + dy, mat)
        if dy == -span + 1:
            mouth_r = max(1.0, _envelope_radius(shape, t, R, 0.0, 0))
    # crown
    cv.put(q, r, y + span + 1, _m(trim))
    # mouth ring and burner
    mr = max(1, int(round(mouth_r)))
    for a, b in hex_ring(q, r, mr):
        cv.put(a, b, mouth_y - 1, M['brass'])
    burner_y = mouth_y - 2
    cv.put(q, r, burner_y, M['wrought_iron'])
    cv.lamp(q, r, burner_y + 1, M['ember_crystal_lamp'])
    for a, b in hex_ring(q, r, 1):
        cv.put(a, b, burner_y, M['copper'])
    # gondola
    style = rng.choice(['basket', 'deck', 'boat', 'cabin'])
    gr = {'basket': max(2, int(R * 0.22)), 'deck': max(3, int(R * 0.38)),
          'boat': max(3, int(R * 0.34)), 'cabin': max(3, int(R * 0.34))}[style]
    drop = int(R * rng.uniform(0.7, 1.1) / LAYER) + 3
    gy = mouth_y - drop
    wood = _wood_set(rng)
    rope = rng.choice([M['linen'], M['heather'], M['wattle']])
    # ropes from the envelope's lower rim to the gondola rim
    for k, (dq, dr) in enumerate(DIRS):
        top_q, top_r = q + dq * (mr + 1), r + dr * (mr + 1)
        cv.line3(top_q, top_r, mouth_y + 1, q + dq * gr, r + dr * gr, gy + 2, rope)
    if style == 'basket':
        cv.disk(q, r, gy, gr, M['wattle'])
        for yy in (gy + 1, gy + 2):
            cv.ring(q, r, yy, gr, M['wattle'])
        cv.chest(q, r, gy + 1)
    elif style in ('deck', 'cabin'):
        cv.disk(q, r, gy, gr, M[wood[1]])
        cv.disk(q, r, gy - 1, gr - 1, M[wood[0]])
        cv.ring(q, r, gy + 1, gr, M['wood_lattice'] if rng.random() < 0.5 else M['pale_lattice'])
        for k, (a, b) in enumerate(hex_ring(q, r, gr)[::max(1, gr)]):
            cv.lamp(a, b, gy + 2, M['lantern'])
        cv.chest(q + 1, r, gy + 1)
        cv.chest(q - 1, r + 1, gy + 1)
        if style == 'cabin':
            for yy in range(gy + 1, gy + 4):
                cv.ring(q, r, yy, 1, M[wood[1]])
            cv.put(q + 1, r, gy + 1, 0)
            cv.put(q + 1, r, gy + 2, 0)
            cv.disk(q, r, gy + 4, 2, M['shingles'])
            cv.put(q, r, gy + 5, M['shingles_slab'])
        else:
            cv.put(q, r, gy + 1, M['bedroll'])
    else:  # boat
        L = gr + 2
        for i in range(-L, L + 1):
            w = max(0, int(round(gr * 0.6 * math.sqrt(max(0.0, 1 - (i / (L + 0.5)) ** 2)))))
            for j in range(-w, w + 1):
                cv.put(q + i, r + j, gy, M[wood[1]])
            cv.put(q + i, r - w - 1, gy + 1, M[wood[1]])
            cv.put(q + i, r + w + 1, gy + 1, M[wood[1]])
            cv.put(q + i, r, gy - 1, M[wood[0]])
        cv.put(q + L + 1, r, gy + 1, M[wood[0]])
        cv.put(q + L + 2, r, gy + 2, M[wood[0]])
        cv.chest(q - 1, r, gy + 1)
        cv.lamp(q + L, r, gy + 2, M['lantern'])
        cv.put(q - L, r, gy + 1, M[f'{hues[0]}_banner'])
    # sandbags and pennants around the rim
    for a, b in hex_ring(q, r, gr)[1::3]:
        cv.put(a, b, gy - 1, M['linen'])
    for k, (a, b) in enumerate(hex_ring(q, r, max(2, int(R * 0.75)))[::4]):
        cv.put(a, b, mouth_y + 1, M[f'{hues[k % len(hues)]}_banner'])
    return {'R': round(R, 1), 'shape': shape, 'pattern': pattern, 'hues': hues, 'gondola': style,
            'top': y + span + 1, 'bottom': gy - 1}


# ---------------------------------------------------------------------------
# sky city
# ---------------------------------------------------------------------------
def _sky_pad(cv, q, r, y, rad, base, stone, depth=None):
    depth = depth or int(rad * 0.9) + 2
    for k in range(depth):
        rr = rad * (1 - k / depth) ** 0.7
        if rr < 0.5:
            break
        for a, b, d, ang in cv.round_cells(q, r, rr):
            cv.put(a, b, y - k, base if k < 2 else stone)


def build_sky_city(cv, rng, q, r, y):
    st = _stone_set(rng)
    hue = rng.choice(BRIGHT)
    hue2 = rng.choice(BRIGHT)
    roof = rng.choice(['shingles', 'thatch', f'{hue}_patterned_tile', f'{hue2}_terrazzo'])
    base = M[rng.choice(['shimmer_cloud', 'cloudstuff', 'fluff_block'])]
    pads = [(q, r, y, rng.uniform(9, 13))]
    n = rng.randint(3, 6)
    for i in range(n):
        ang = i / n * 2 * math.pi + rng.uniform(-0.3, 0.3)
        dist = rng.uniform(20, 32)
        pq = q + int(round(math.cos(ang) * dist))
        pr = r + int(round(math.sin(ang) * dist * 0.9))
        pads.append((pq, pr, y + rng.randint(-14, 16), rng.uniform(5, 9)))
    for pq, pr, py, rad in pads:
        _sky_pad(cv, pq, pr, py, rad, base, M[st[0]])
        for a, b, d, ang in cv.round_cells(pq, pr, rad - 0.5):
            cv.put(a, b, py + 1, M[st[3]] if d < rad - 1.5 else M[st[1]])
    # central spire
    h = rng.randint(40, 70)
    for yy in range(y + 2, y + 2 + h):
        t = (yy - y) / h
        rad = max(1, int(round(4.5 * max(0.0, 1 - t) ** 0.8)))
        cv.ring(q, r, yy, rad, M[st[1]] if (yy // 4) % 3 else M[st[2]])
        if rad >= 2 and yy % 6 == 0:
            for dq, dr in DIRS:
                cv.put(q + dq * rad, r + dr * rad, yy, M[f'{hue}_stained_glass'])
    cv.put(q, r, y + 2 + h, M['cosmic_star'])
    for yy in (y + 14, y + 30):
        cv.ring(q, r, yy, 6, M['wrought_iron'])
    # modules on outer pads
    mods = ['tower', 'dome', 'garden', 'houses', 'plaza']
    for i, (pq, pr, py, rad) in enumerate(pads[1:]):
        mod = mods[(i + rng.randint(0, 4)) % len(mods)]
        fy = py + 2
        if mod == 'tower':
            th = rng.randint(14, 28)
            for yy in range(fy, fy + th):
                cv.ring(pq, pr, yy, 2, M[st[1]])
            cv.disk(pq, pr, fy + th, 3, M[roof] if roof in M else M['shingles'])
            cv.disk(pq, pr, fy + th + 1, 2, M[roof] if roof in M else M['shingles'])
            cv.put(pq, pr, fy + th + 2, M[f'{hue2}_banner'])
            cv.lamp(pq + 2, pr, fy + th - 2, M[f'{hue}_crystal_lamp'])
        elif mod == 'dome':
            R = rad - 1.5
            for a, b, d, ang in cv.round_cells(pq, pr, R):
                hh = int(math.sqrt(max(0.0, R * R - d * d)) * 1.2)
                nh = int(math.sqrt(max(0.0, R * R - (d + 1) ** 2)) * 1.2) if d + 1 < R else 0
                for yy in range(fy + nh, fy + hh + 1):
                    cv.put(a, b, yy, M[f'{HUES[(int(ang * 3) + yy) % 16]}_stained_glass'] if yy % 3 else M[st[2]])
            cv.lamp(pq, pr, fy, M['lumen_lamp'])
        elif mod == 'garden':
            for a, b, d, ang in cv.round_cells(pq, pr, rad - 1):
                cv.put(a, b, fy - 1, M['turf'])
                if (a * 5 + b * 3) % 4 == 0:
                    cv.put(a, b, fy, M[rng.choice(['bloom', 'wildflower', 'petals', 'shrub', 'berry_bush'])])
            for k in range(rng.randint(1, 3)):
                tq, tr = pq + rng.randint(-2, 2), pr + rng.randint(-2, 2)
                th = rng.randint(5, 8)
                cv.col(tq, tr, fy, fy + th, M['pale_heartwood'])
                for dq, dr in [(0, 0)] + DIRS:
                    cv.put(tq + dq, tr + dr, fy + th + 1, M['canopy'])
                    cv.put(tq + dq, tr + dr, fy + th, M['canopy'])
        elif mod == 'houses':
            for k in range(rng.randint(2, 3)):
                hq, hr = pq + rng.randint(-2, 2), pr + rng.randint(-2, 2)
                hh = rng.randint(3, 6)
                for yy in range(fy, fy + hh):
                    cv.ring(hq, hr, yy, 1, M[rng.choice(['ivory_plaster', 'blush_plaster', 'sage_plaster', 'dusk_plaster'])])
                cv.disk(hq, hr, fy + hh, 2, M[roof] if roof in M else M['shingles'])
                cv.put(hq, hr, fy + hh + 1, M['shingles_slab'])
        else:
            for a, b, d, ang in cv.round_cells(pq, pr, rad - 1):
                g = int(((ang + math.pi) / (2 * math.pi)) * 8)
                cv.put(a, b, fy - 1, M[f'{HUES[(g * 2) % 16]}_terrazzo'])
            cv.col(pq, pr, fy, fy + 3, M[st[2]])
            cv.lamp(pq, pr, fy + 4, M[f'{hue}_crystal_lamp'])
        # bridge back to the hub
        bridge = M[rng.choice(['pale_planks', 'cedar_planks', st[1]])]
        cv.line3(pq, pr, py + 1, q, r, y + 1, bridge)
        cv.line3(pq, pr, py + 2, q, r, y + 2, 0)
    return {'pads': len(pads), 'spire': h}


# ---------------------------------------------------------------------------
# floating fortress
# ---------------------------------------------------------------------------
def build_floating_fortress(cv, rng, q, r, y):
    st = _stone_set(rng)
    R = rng.uniform(13, 22)
    depth = int(R * rng.uniform(1.6, 2.4))
    rock = M[rng.choice(['stone', 'basalt', 'slate', 'cobble'])]
    ores = [M['emberite_ore'], M['silverine_ore'], M['aetherite_ore'], M['verdigris_ore']]
    for k in range(depth):
        t = k / depth
        rr = R * (1 - t) ** 0.9 * (1 + 0.08 * math.sin(k * 0.7))
        if rr < 0.6:
            break
        for a, b, d, ang in cv.round_cells(q, r, rr):
            if d > rr - 1.6 or k < 2 or k % 4 == 0:
                mat = rock
                if (a * 31 + b * 17 + k * 7) % 53 == 0:
                    mat = ores[(a + b) % 4]
                cv.put(a, b, y - k, mat)
    cv.col(q, r, y - depth - 6, y - depth, rock)
    for a, b, d, ang in cv.round_cells(q, r, R - 0.5):
        cv.put(a, b, y, M['turf'] if d < R - 3 else M[st[0]])
    wall_r = R - 2.5
    wh = rng.randint(6, 10)
    cells = [c for c in cv.round_cells(q, r, wall_r) if c[2] > wall_r - 1.2]
    for a, b, d, ang in cells:
        for yy in range(y + 1, y + wh):
            cv.put(a, b, yy, M[st[1]])
        if (a + b) % 2 == 0:
            cv.put(a, b, y + wh, M[st[1]])
    ntw = rng.choice([4, 5, 6, 8])
    roofhue = rng.choice(BRIGHT)
    for i in range(ntw):
        ang = i / ntw * 2 * math.pi
        x0, z0 = center(q, r)
        from .hexgrid import cell_at
        tq, tr = cell_at(x0 + math.cos(ang) * wall_r * SQ3, z0 + math.sin(ang) * wall_r * SQ3)
        th = wh + rng.randint(6, 12)
        for yy in range(y + 1, y + th):
            cv.disk(tq, tr, yy, 2, M[st[1]] if yy % 5 else M[st[2]])
        for k in range(4):
            cv.disk(tq, tr, y + th + k, 3 - k, M[f'{roofhue}_patterned_tile'])
        cv.put(tq, tr, y + th + 4, M[f'{roofhue}_banner'])
        cv.lamp(tq, tr, y + th - 2, M['lantern'])
    # gate
    gq, gr_ = q + int(wall_r), r
    for dq in (-1, 0, 1):
        for yy in range(y + 1, y + 5):
            cv.put(gq + dq, gr_, yy, 0)
            cv.put(gq + dq, gr_ - 1, yy, 0)
    # keep
    kr = max(3, int(R * 0.3))
    kh = rng.randint(20, 34)
    for yy in range(y + 1, y + kh):
        cv.ring(q, r, yy, kr, M[st[2]] if yy % 6 else M[st[1]])
        if yy % 6 == 3:
            for dq, dr in DIRS:
                cv.put(q + dq * kr, r + dr * kr, yy, M[f'{roofhue}_stained_glass'])
        if yy % 7 == 0:
            cv.disk(q, r, yy, kr - 1, M[_wood_set(rng)[1]])
    for k in range(kr + 2):
        cv.disk(q, r, y + kh + k, kr + 1 - k, M[f'{roofhue}_terrazzo'])
    cv.lamp(q, r, y + kh + kr + 2, M['cosmic_star'])
    cv.chest(q, r, y + 1)
    for a, b in hex_ring(q, r, kr + 2)[::3]:
        cv.put(a, b, y + 1, M['shrub'])
    return {'R': round(R, 1), 'towers': ntw, 'keep': kh}


# ---------------------------------------------------------------------------
# world tree
# ---------------------------------------------------------------------------
def build_world_tree(cv, rng, q, r, y):
    log, plank, slab = _wood_set(rng)
    TR = rng.randint(3, 6)
    H = rng.randint(60, 120)
    foot = cv.round_cells(q, r, TR + 6)
    cv.foundation([(a, b) for a, b, d, _ in foot], y, M['packed_earth'], M['turf'])
    # roots
    for k in range(rng.randint(5, 8)):
        ang = k * 2 * math.pi / 7 + rng.uniform(-0.3, 0.3)
        from .hexgrid import cell_at
        x0, z0 = center(q, r)
        for s in range(TR, TR + 9):
            a, b = cell_at(x0 + math.cos(ang) * s * SQ3, z0 + math.sin(ang) * s * SQ3)
            cv.put(a, b, y + 1 + max(0, (TR + 4 - s) // 2), M[log])
    # trunk with a gentle sway
    sway_a = rng.uniform(0, 2 * math.pi)
    for yy in range(y + 1, y + H):
        t = (yy - y) / H
        rad = TR * (1 - 0.55 * t)
        off = 2.0 * math.sin(t * math.pi * 1.2)
        from .hexgrid import cell_at
        x0, z0 = center(q, r)
        cq_, cr_ = cell_at(x0 + math.cos(sway_a) * off * SQ3, z0 + math.sin(sway_a) * off * SQ3)
        for a, b, d, ang in cv.round_cells(cq_, cr_, rad):
            cv.put(a, b, yy, M[log])
        # spiral stair around the trunk
        ang = yy * 0.35
        sa, sb = cell_at(x0 + math.cos(ang) * (rad + 1.5) * SQ3 + math.cos(sway_a) * off * SQ3,
                         z0 + math.sin(ang) * (rad + 1.5) * SQ3 + math.sin(sway_a) * off * SQ3)
        if yy < y + H * 0.8:
            cv.put(sa, sb, yy, M[slab])
    # branches with platforms, canopies and huts
    nb = rng.randint(4, 7)
    plats = []
    from .hexgrid import cell_at
    x0, z0 = center(q, r)
    for i in range(nb):
        by = y + int(H * rng.uniform(0.45, 0.92))
        ang = i / nb * 2 * math.pi + rng.uniform(-0.4, 0.4)
        L = rng.uniform(12, 24)
        eq, er = cell_at(x0 + math.cos(ang) * L * SQ3, z0 + math.sin(ang) * L * SQ3)
        ey = by + rng.randint(4, 12)
        cv.line3(q, r, by, eq, er, ey, M[log], thick=1)
        cr = rng.uniform(5, 9)
        for a, b, d, an in cv.round_cells(eq, er, cr):
            hh = int(math.sqrt(max(0.0, cr * cr - d * d)) * 0.7)
            for yy in range(ey + 2, ey + 3 + hh):
                cv.put(a, b, yy, M['canopy'])
        # platform under the canopy
        pr_ = rng.randint(3, 4)
        cv.disk(eq, er, ey - 2, pr_, M[plank])
        cv.ring(eq, er, ey - 1, pr_, M['wood_lattice'])
        if rng.random() < 0.7:
            hq, hr = eq, er
            for yy in range(ey - 1, ey + 2):
                cv.ring(hq, hr, yy, 1, M[plank])
            cv.put(hq + 1, hr, ey - 1, 0)
            cv.put(hq + 1, hr, ey, 0)
            cv.put(hq, hr, ey - 1, M['bedroll'])
        cv.lamp(eq + pr_, er, ey, M['lantern'])
        plats.append((eq, er, ey - 2))
    # rope bridges between neighbouring platforms
    for i in range(len(plats)):
        a, b = plats[i], plats[(i + 1) % len(plats)]
        if abs(a[2] - b[2]) < 14:
            cv.line3(a[0], a[1], a[2], b[0], b[1], b[2], M[plank])
    # crown
    top_y = y + H
    for a, b, d, an in cv.round_cells(q, r, 11):
        hh = int(math.sqrt(max(0.0, 121 - d * d)) * 0.8)
        for yy in range(top_y - 2, top_y + hh):
            cv.put(a, b, yy, M['canopy'])
    cv.chest(q + TR + 1, r, y + 1)
    return {'height': H, 'trunk': TR, 'branches': nb}


# ---------------------------------------------------------------------------
# colossus
# ---------------------------------------------------------------------------
def build_colossus(cv, rng, q, r, y):
    """A robed, hooded guardian (no anatomy: a robe from shoulder to plinth)."""
    st = _stone_set(rng)
    stone, brick, polish, tile = (M[s] for s in st)
    trim = M[rng.choice(['brass', 'copper', 'pewter', f'{rng.choice(BRIGHT)}_terrazzo'])]
    H = rng.randint(55, 110)          # layers from plinth top to crown
    H = max(30, min(H, LAYERS - 40 - y))
    s = H / 80.0
    ruined = rng.random() < 0.3
    cut = y + int(H * rng.uniform(0.45, 0.75)) if ruined else 10 ** 6
    face = rng.uniform(0, 2 * math.pi)
    fx, fz = math.cos(face), math.sin(face)
    x0, z0 = center(q, r)
    from .hexgrid import cell_at
    # plinth (stepped)
    pr = int(10 * s) + 4
    base = cv.round_cells(q, r, pr)
    cv.foundation([(a, b) for a, b, d, _ in base], y, brick)
    py = y
    for k in range(3):
        for a, b, d, _ in cv.round_cells(q, r, pr - k * 2):
            cv.put(a, b, py + 1 + k, tile if k == 2 else brick)
    py += 3

    def blob(cx, cz, yy, rad, mat):
        a0, b0 = cell_at(cx, cz)
        for a, b, d, _ in cv.round_cells(a0, b0, rad):
            if yy < cut:
                cv.put(a, b, yy, mat)

    # robe: a flared cone with folds
    robe_h = int(H * 0.62)
    for k in range(robe_h):
        t = k / robe_h
        rad = (7.5 - 4.0 * t) * s + 0.4 * math.sin(k * 0.6)
        blob(x0, z0, py + 1 + k, rad, stone if (k // 5) % 4 else polish)
    # sash
    blob(x0, z0, py + int(robe_h * 0.55), 4.2 * s, trim)
    # shoulders and chest
    sy = py + robe_h
    for k in range(int(8 * s)):
        blob(x0, z0, sy + k, (4.6 - 0.15 * k) * s, stone)
    # hood and head
    hy = sy + int(8 * s)
    for k in range(int(10 * s)):
        t = k / (10 * s)
        blob(x0, z0, hy + k, (3.4 * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2)) + 0.6) * s, polish)
    # face shadow under the hood
    for k in range(int(3 * s), int(6 * s)):
        a, b = cell_at(x0 + fx * 2.6 * s * SQ3, z0 + fz * 2.6 * s * SQ3)
        if hy + k < cut:
            cv.put(a, b, hy + k, M['ink_terrazzo'])
    # arms: one raised with a lantern or staff, one folded down
    side = (-fz, fx)
    hold = rng.choice(['lantern', 'staff', 'orb'])
    arm_top = hy + int(9 * s)
    for k in range(int(14 * s)):
        t = k / (14 * s)
        cx = x0 + side[0] * (5.0 * s) * SQ3 + fx * 1.5 * s * SQ3 * t
        cz = z0 + side[1] * (5.0 * s) * SQ3 + fz * 1.5 * s * SQ3 * t
        blob(cx, cz, sy + 2 + int(t * (arm_top - sy - 2)), 1.3 * s, stone)
    hx = x0 + side[0] * 5.0 * s * SQ3 + fx * 1.5 * s * SQ3
    hz = z0 + side[1] * 5.0 * s * SQ3 + fz * 1.5 * s * SQ3
    ha, hb = cell_at(hx, hz)
    if arm_top < cut:
        if hold == 'lantern':
            for k in range(3):
                cv.disk(ha, hb, arm_top + 2 + k, 1, M['wrought_iron'] if k != 1 else M['glass'])
            cv.lamp(ha, hb, arm_top + 3, M['honey_crystal_lamp'])
        elif hold == 'staff':
            cv.col(ha, hb, py + 1, arm_top + int(12 * s), trim)
            cv.disk(ha, hb, arm_top + int(12 * s) + 1, 1, M['crystal'])
            cv.lamp(ha, hb, arm_top + int(12 * s) + 2, M['lumen_shard'])
        else:
            for a, b, d, _ in cv.round_cells(ha, hb, 2.2 * s):
                for k in range(int(4 * s)):
                    cv.put(a, b, arm_top + 2 + k, M['aether_lamp'] if (a + b + k) % 5 == 0 else M['violet_stained_glass'])
    for k in range(int(10 * s)):
        cx = x0 - side[0] * 4.4 * s * SQ3 + fx * 1.2 * s * SQ3
        cz = z0 - side[1] * 4.4 * s * SQ3 + fz * 1.2 * s * SQ3
        blob(cx, cz, sy + 4 - k, 1.2 * s, stone)
    if ruined:
        # the fallen top half lies beside the plinth; rubble and moss
        for k in range(int(8 * s)):
            for a, b, d, _ in cv.round_cells(q + int(pr + 4), r + k - int(4 * s), 3.0 * s):
                cv.put(a, b, cv.ground(a, b) + 1 if cv.ground(a, b) > 0 else y + 1, polish)
        for i in range(30):
            a = q + rng.randint(-pr - 6, pr + 6)
            b = r + rng.randint(-pr - 6, pr + 6)
            g = cv.ground(a, b)
            if g > 0:
                cv.put(a, b, g + 1, M[rng.choice(['cobble', 'mossrock', st[1]])])
    cv.chest(q + pr - 1, r, py + 1)
    return {'height': H, 'ruined': ruined, 'holds': hold}


# ---------------------------------------------------------------------------
# megaspire
# ---------------------------------------------------------------------------
def build_megaspire(cv, rng, q, r, y):
    style = rng.choice(['buttress', 'pagoda', 'crystal', 'helix'])
    st = _stone_set(rng)
    hue = rng.choice(BRIGHT)
    H = min(LAYERS - 12 - y, rng.randint(120, 250))
    R0 = rng.uniform(6, 10)
    cv.foundation([(a, b) for a, b, d, _ in cv.round_cells(q, r, R0 + 4)], y, M[st[1]], M[st[3]])
    from .hexgrid import cell_at
    x0, z0 = center(q, r)
    for yy in range(y + 1, y + H):
        t = (yy - y) / H
        if style == 'pagoda':
            tier = int(t * 9)
            tt = t * 9 - tier
            rad = R0 * (1 - tier / 10.5)
            if tt > 0.85:
                rad += 2.5
        else:
            rad = R0 * (1 - t) ** 0.85 + 0.6
        if rad < 0.6:
            continue
        for a, b, d, ang in cv.round_cells(q, r, rad):
            if d < rad - 1.3 and yy % 9 != 0:
                continue
            if style == 'crystal':
                mat = M['crystal'] if (int(ang * 3) + yy // 6) % 3 == 0 else M[f'{hue}_stained_glass'] if yy % 4 else M['glass']
            elif style == 'helix':
                band = int(((ang + math.pi) / (2 * math.pi)) * 6 + yy / 7) % 6
                mat = M[st[2]] if band in (0, 3) else M[f'{hue}_terrazzo'] if band == 1 else M[st[1]]
            elif style == 'pagoda':
                tier = int(t * 9)
                mat = M[f'{hue}_patterned_tile'] if (t * 9 - tier) > 0.85 else M[st[1]]
            else:
                mat = M[st[1]] if yy % 8 else M[st[2]]
                if yy % 12 == 6 and int(ang * 4) % 2 == 0:
                    mat = M[f'{hue}_stained_glass']
            cv.put(a, b, yy, mat)
        if style == 'buttress' and yy < y + H * 0.45:
            for k in range(4):
                ang = k * math.pi / 2 + 0.4
                reach = rad + (1 - t / 0.45) * 7
                for s in np.arange(rad, reach, 0.7):
                    a, b = cell_at(x0 + math.cos(ang) * s * SQ3, z0 + math.sin(ang) * s * SQ3)
                    if (s - rad) < (1 - t / 0.45) * 7 * 0.9:
                        cv.put(a, b, yy, M[st[0]])
        if yy % 30 == 0 and rad > 2:
            cv.ring(q, r, yy, int(rad) + 2, M['wrought_iron'])
            cv.ring(q, r, yy - 1, int(rad) + 2, M[st[3]])
            cv.ring(q, r, yy - 1, int(rad) + 1, M[st[3]])
    # crown
    top = y + H
    cv.col(q, r, top - 4, top + 6, M['brass'])
    cv.disk(q, r, top + 7, 1, M['crystal'])
    cv.lamp(q, r, top + 8, M['cosmic_star'])
    for k in range(1, 5):
        cv.lamp(q + int(R0 * 0.7), r, y + k * H // 5, M[f'{hue}_crystal_lamp'])
    # base hall door
    for yy in range(y + 1, y + 5):
        for k in range(int(R0) - 2, int(R0) + 2):
            cv.put(q + k, r, yy, 0)
    cv.chest(q, r, y + 1)
    return {'style': style, 'height': H}


# ---------------------------------------------------------------------------
# leviathan wreck
# ---------------------------------------------------------------------------
def build_leviathan_wreck(cv, rng, q, r, y):
    from .hexgrid import cell_at
    x0, z0 = center(q, r)
    ang = rng.uniform(0, 2 * math.pi)
    ux, uz = math.cos(ang), math.sin(ang)
    px, pz = -uz, ux
    L = rng.uniform(40, 80)
    kind = rng.choice(['bones', 'airship'])

    def at(s, w):
        return cell_at(x0 + (ux * s + px * w) * SQ3, z0 + (uz * s + pz * w) * SQ3)

    if kind == 'bones':
        bone = M['ivory_plaster']
        rib = M['pearl_terrazzo']
        sag = rng.uniform(0.0, 0.15)
        for i in range(int(L)):
            s = i - L / 2
            a, b = at(s, 0)
            g = cv.ground(a, b)
            gy = g if g > 0 else y
            sy = gy + int(6 + 6 * math.sin(i / L * math.pi) - sag * i)
            cv.put(a, b, sy, bone)
            cv.put(a, b, sy + 1, bone)
            if i % 4 == 0 and 0.15 < i / L < 0.7:
                rw = 6 + 8 * math.sin(i / L * math.pi)
                for k in range(20):
                    th = k / 19 * math.pi
                    for sgn in (-1, 1):
                        aa, bb = at(s, sgn * math.sin(th) * rw)
                        cv.put(aa, bb, sy - int((1 - math.cos(th)) * rw * 0.9 / LAYER * 0.5) + 1, rib)
        # skull
        hs = L / 2
        for k in range(10):
            for w in range(-5, 6):
                a, b = at(hs + k, w * (1 - k / 12))
                g = cv.ground(a, b)
                gy = (g if g > 0 else y) + 1
                for yy in range(gy, gy + int(6 * (1 - k / 11)) + 1):
                    if abs(w) > 3 or yy == gy or yy > gy + 4:
                        cv.put(a, b, yy, bone)
        a, b = at(hs + 3, 2)
        cv.lamp(a, b, cv.ground(a, b) + 4 if cv.ground(a, b) > 0 else y + 4, M['aether_lamp'])
    else:
        log, plank, slab = _wood_set(rng)
        tilt = rng.uniform(0.08, 0.25)
        W = rng.uniform(5, 8)
        for i in range(int(L)):
            s = i - L / 2
            prof = math.sqrt(max(0.0, 1 - (s / (L / 2 + 1)) ** 2))
            w = W * prof
            if i % 9 == 4 and 0.2 < i / L < 0.8:
                continue          # broken gaps in the hull
            for k in range(-int(w) - 1, int(w) + 2):
                a, b = at(s, k)
                g = cv.ground(a, b)
                gy = (g if g > 0 else y) - 1
                depth = int((1 - (abs(k) / (w + 1)) ** 2) * 5)
                roll = int(k * tilt * 3)
                for yy in range(gy + roll, gy + roll + 2 + (6 if abs(k) >= int(w) else 0)):
                    if yy <= gy + roll + 1 or abs(k) >= int(w):
                        cv.put(a, b, yy, M[plank] if yy % 3 else M[log])
                if abs(k) <= 1:
                    cv.put(a, b, gy + roll - 1 - depth // 3, M[log])
        # broken mast and torn envelope cloth draped across
        a, b = at(0, 0)
        g = cv.ground(a, b)
        gy = g if g > 0 else y
        cv.col(a, b, gy + 1, gy + 24, M[log])
        hues = _palette(rng, 4, bright=True)
        for i in range(int(L * 0.6)):
            for k in range(-9, 10):
                if (i * 7 + k * 3) % 11 == 0:
                    continue
                aa, bb = at(i - L * 0.3, k)
                g = cv.ground(aa, bb)
                if g > 0:
                    cv.put(aa, bb, g + 1 + int(2 * math.sin(i * 0.3 + k * 0.2) + 2),
                           M[f'{hues[(i // 4 + k // 3) % len(hues)]}_woven_panel'])
        for k in range(8):
            aa, bb = at(rng.uniform(-L / 2, L / 2), rng.uniform(-14, 14))
            g = cv.ground(aa, bb)
            if g > 0:
                cv.put(aa, bb, g + 1, M[plank])
                cv.put(aa, bb, g + 2, M[slab])
        aa, bb = at(-3, 0)
        g = cv.ground(aa, bb)
        cv.lamp(aa, bb, (g if g > 0 else y) + 2, M['lantern'])
    a, b = at(0, 2)
    g = cv.ground(a, b)
    cv.chest(a, b, (g if g > 0 else y) + 1)
    return {'kind': kind, 'length': int(L)}


# ---------------------------------------------------------------------------
# titan ruins
# ---------------------------------------------------------------------------
def build_titan_ruins(cv, rng, q, r, y):
    st = _stone_set(rng)
    from .hexgrid import cell_at
    x0, z0 = center(q, r)
    R = rng.uniform(22, 36)
    # dais
    cv.foundation([(a, b) for a, b, d, _ in cv.round_cells(q, r, 9)], y, M[st[1]], M[st[3]])
    for a, b, d, _ in cv.round_cells(q, r, 6):
        cv.put(a, b, y + 1, M[st[2]])
    # colonnade ring of giant columns, many broken, some toppled
    n = rng.randint(8, 14)
    for i in range(n):
        ang = i / n * 2 * math.pi
        a0, b0 = cell_at(x0 + math.cos(ang) * R * SQ3, z0 + math.sin(ang) * R * SQ3)
        g = cv.ground(a0, b0)
        if g <= 0:
            continue
        cr = rng.uniform(2.0, 3.6)
        roll = rng.random()
        if roll < 0.3:
            # toppled: lies along the ground, drums apart
            dang = rng.uniform(0, 2 * math.pi)
            for s in range(0, rng.randint(16, 30)):
                if s % 7 == 6:
                    continue
                aa, bb = cell_at(x0 + (math.cos(ang) * R + math.cos(dang) * s) * SQ3,
                                 z0 + (math.sin(ang) * R + math.sin(dang) * s) * SQ3)
                gg = cv.ground(aa, bb)
                if gg > 0:
                    for k in range(int(cr * 1.4)):
                        cv.put(aa, bb, gg + 1 + k, M[st[0]] if s % 7 else M[st[2]])
        else:
            hh = rng.randint(20, 60) if roll < 0.75 else rng.randint(60, 90)
            for yy in range(g + 1, g + hh):
                for a, b, d, an in cv.round_cells(a0, b0, cr):
                    flute = int(((an + math.pi) / (2 * math.pi)) * 12) % 2
                    cv.put(a, b, yy, M[st[0]] if flute else M[st[2]])
            if roll >= 0.75:
                cv.disk(a0, b0, g + hh, int(cr) + 2, M[st[1]])
                cv.disk(a0, b0, g + hh + 1, int(cr) + 1, M[st[3]])
            if rng.random() < 0.6:
                for yy in range(g + 1, g + hh, 3):
                    cv.put(a0 + int(cr) + 1, b0, yy, M['vine'] if 'vine' in M else M['canopy'])
    # the great arch
    ang = rng.uniform(0, 2 * math.pi)
    half = rng.uniform(10, 16)
    ah = rng.randint(30, 55)
    for sgn in (-1, 1):
        a0, b0 = cell_at(x0 + (math.cos(ang) * (R * 0.5) - math.sin(ang) * half * sgn) * SQ3,
                         z0 + (math.sin(ang) * (R * 0.5) + math.cos(ang) * half * sgn) * SQ3)
        g = cv.ground(a0, b0)
        g = g if g > 0 else y
        for yy in range(g + 1, y + ah):
            cv.disk(a0, b0, yy, 2, M[st[1]])
    for k in range(41):
        t = k / 40
        w = (t * 2 - 1) * half
        yy = y + ah + int(math.sin(t * math.pi) * 10)
        a, b = cell_at(x0 + (math.cos(ang) * (R * 0.5) - math.sin(ang) * w) * SQ3,
                       z0 + (math.sin(ang) * (R * 0.5) + math.cos(ang) * w) * SQ3)
        for d in range(3):
            cv.disk(a, b, yy + d, 1, M[st[2]] if d == 1 else M[st[1]])
    # a giant fallen head half buried by the dais
    hq, hr = q + int(R * 0.35), r - int(R * 0.2)
    g = cv.ground(hq, hr)
    g = g if g > 0 else y
    for a, b, d, _ in cv.round_cells(hq, hr, 7):
        h = int(math.sqrt(max(0.0, 49 - d * d)) * 1.3)
        for yy in range(g - 2, g + h):
            cv.put(a, b, yy, M[st[0]])
    for dw in (-2, 2):
        cv.put(hq + 6, hr + dw, g + 5, M['ink_terrazzo'])
        cv.put(hq + 6, hr + dw, g + 6, M['ink_terrazzo'])
    cv.lamp(q, r, y + 2, M['lumen_lamp'])
    for i in range(50):
        a = q + rng.randint(-int(R), int(R))
        b = r + rng.randint(-int(R), int(R))
        gg = cv.ground(a, b)
        if gg > 0 and cv.get(a, b, gg + 1) is None:
            cv.put(a, b, gg + 1, M[rng.choice(['cobble', 'mossrock', st[1], 'mossy_bricks', 'shrub'])])
    cv.chest(q, r, y + 2)
    return {'columns': n, 'arch': ah}



# ---------------------------------------------------------------------------
# village (seeded town of multi-storey houses)
# ---------------------------------------------------------------------------
def _house(cv, rng, q, r, g, rad, floors, wall, roof, trim, wood):
    fh = 4
    for f in range(floors):
        base = g + 1 + f * fh
        for yy in range(base, base + fh):
            cv.ring(q, r, yy, rad, wall if yy != base + fh - 1 else trim)
        cv.disk(q, r, base - 1, rad - 1, wood)
        for d, (dq, dr) in enumerate(DIRS):
            if (d + f) % 2 == 0:
                cv.put(q + dq * rad, r + dr * rad, base + 1, M['glass'])
    top = g + 1 + floors * fh
    for k in range(rad + 2):
        cv.disk(q, r, top + k, rad + 1 - k, roof)
    # door gap facing +q
    cv.put(q + rad, r, g + 1, 0)
    cv.put(q + rad, r, g + 2, 0)
    cv.lamp(q + rad + 1, r - 1, g + 3, M['lantern'])
    return top + rad + 1


def build_village(cv, rng, q, r, y):
    n = rng.randint(5, 13)
    walls = [M[w] for w in rng.sample(['ivory_plaster', 'blush_plaster', 'sage_plaster', 'dusk_plaster',
                                        'chalk_bricks', 'sandstone_bricks', 'stone_bricks'], 3)]
    roofs = [M[w] for w in rng.sample(['shingles', 'thatch', 'rose_patterned_tile', 'tide_patterned_tile',
                                        'honey_patterned_tile', 'clay_tiles', 'slate_tiles'], 3)]
    wood = M[_wood_set(rng)[1]]
    trim = M[rng.choice(['dark_planks', 'cedar_planks', 'brass', 'wrought_iron'])]
    # plaza with a well or fountain
    pr = rng.randint(4, 6)
    g0 = cv.ground(q, r)
    g0 = g0 if g0 > 0 else y
    pave = M[rng.choice(['stone_tiles', 'pearl_terrazzo', 'honey_patterned_tile', 'cobble'])]
    cv.foundation([(a, b) for a, b, d, _ in cv.round_cells(q, r, pr)], g0, M['packed_earth'], pave)
    if rng.random() < 0.5:
        cv.ring(q, r, g0 + 1, 1, M['stone_bricks'])
        cv.put(q, r, g0, M['water'], 7)
        cv.col(q + 1, r, g0 + 2, g0 + 3, M['dark_planks'])
        cv.put(q, r, g0 + 4, M['shingles'])
    else:
        cv.col(q, r, g0 + 1, g0 + 3, M['polished_chalk'])
        cv.lamp(q, r, g0 + 4, M[f'{rng.choice(BRIGHT)}_crystal_lamp'])
    houses = []
    for i in range(n):
        ang = i / n * 2 * math.pi + rng.uniform(-0.25, 0.25)
        dist = pr + 6 + rng.uniform(0, 14) + (i % 3) * 4
        from .hexgrid import cell_at
        x0, z0 = center(q, r)
        hq, hr = cell_at(x0 + math.cos(ang) * dist * SQ3, z0 + math.sin(ang) * dist * SQ3)
        if any(hex_distance(hq, hr, a, b) < 7 for a, b in houses):
            continue
        g = cv.ground(hq, hr)
        if g <= 0:
            continue
        rad = rng.randint(2, 3)
        floors = rng.choice([1, 1, 2, 2, 3])
        cv.foundation([(a, b) for a, b, d, _ in cv.round_cells(hq, hr, rad + 1)], g, M['cobble'], wood)
        _house(cv, rng, hq, hr, g, rad, floors, rng.choice(walls), rng.choice(roofs), trim, wood)
        houses.append((hq, hr))
        # a garden plot or market stall beside some houses
        if rng.random() < 0.5:
            for a, b in hex_ring(hq - rad - 2, hr, 1):
                gg = cv.ground(a, b)
                if gg > 0:
                    cv.put(a, b, gg, M['farmland'])
                    cv.put(a, b, gg + 1, M[rng.choice(['skywheat', 'sweetroot_crop', 'berry_crop'])], 3)
        elif rng.random() < 0.5:
            a, b = hq, hr + rad + 2
            gg = cv.ground(a, b)
            if gg > 0:
                hue = rng.choice(BRIGHT)
                cv.col(a, b, gg + 1, gg + 2, M['dark_planks'])
                cv.disk(a, b, gg + 3, 1, M[f'{hue}_woven_panel'])
                cv.put(a + 1, b, gg + 1, M[f'{hue}_banner'])
    # paths from the plaza to each door
    for hq, hr in houses:
        from .tutorial import hex_line
        for a, b in hex_line(q, r, hq + 4, hr)[pr:]:
            gg = cv.ground(a, b)
            if gg > 0 and cv.get(a, b, gg + 1) is None:
                cv.put(a, b, gg, M['packed_earth'])
    cv.chest(q - 1, r, g0 + 1)
    return {'houses': len(houses)}


# ---------------------------------------------------------------------------
# airship (intact, flying)
# ---------------------------------------------------------------------------
def build_airship(cv, rng, q, r, y):
    log, plank, slab = _wood_set(rng)
    L = rng.randint(14, 30)
    W = rng.uniform(3.5, 6.0)
    hues = _palette(rng, rng.randint(2, 4), bright=True)
    ax = rng.choice([0, 1, 2])
    dq_, dr_ = DIRS[ax]
    pq_, pr_ = DIRS[(ax + 2) % 6]

    def at(i, j):
        return q + dq_ * i + pq_ * j, r + dr_ * i + pr_ * j
    # hull
    for i in range(-L, L + 1):
        prof = math.sqrt(max(0.0, 1 - (i / (L + 0.5)) ** 2))
        w = max(1, int(round(W * prof)))
        for j in range(-w, w + 1):
            a, b = at(i, j)
            cv.put(a, b, y, M[plank])
            depth = int((1 - (j / (w + 0.5)) ** 2) * 4 * prof) + 1
            for k in range(1, depth + 1):
                cv.put(a, b, y - k, M[plank] if k < depth else M[log])
        for sgn in (-1, 1):
            a, b = at(i, sgn * (w + 1))
            cv.put(a, b, y + 1, M['wood_lattice'] if i % 3 else M[log])
    # prow and stern
    a, b = at(L + 1, 0)
    cv.col(a, b, y, y + 2, M[log])
    a, b = at(L + 2, 0)
    cv.put(a, b, y + 3, M['brass'])
    # cabin
    for i in range(-L // 2 - 3, -L // 2 + 4):
        for j in (-2, -1, 0, 1, 2):
            a, b = at(i, j)
            edge = abs(j) == 2 or i in (-L // 2 - 3, -L // 2 + 3)
            for yy in range(y + 1, y + 5):
                if edge:
                    cv.put(a, b, yy, M[plank] if yy != y + 2 else M['glass'])
            cv.put(a, b, y + 5, M['shingles'])
    a, b = at(-L // 2 + 3, 0)
    cv.put(a, b, y + 1, 0)
    cv.put(a, b, y + 2, 0)
    # propellers
    for sgn in (-1, 1):
        a, b = at(-L + 2, sgn * (int(W) + 2))
        cv.put(a, b, y + 1, M['brass'])
        for k in (-2, -1, 1, 2):
            cv.put(a, b, y + 1 + k, M['pewter'])
    # envelope: a long striped ellipsoid above the deck
    EH = int(W * 1.4 / LAYER) + 3
    ey = y + 8 + EH
    ER = W * 1.25
    EL = L * 0.95
    for i in range(-int(EL) - 1, int(EL) + 2):
        for j in range(-int(ER) - 2, int(ER) + 3):
            for dy in range(-EH, EH + 1):
                v = (i / EL) ** 2 + (j / ER) ** 2 + (dy / EH) ** 2
                if 0.78 < v <= 1.0:
                    a, b = at(i, j)
                    band = (i + int(EL)) // max(2, int(EL / 4))
                    hue = hues[(band + (1 if abs(j) > ER * 0.6 else 0)) % len(hues)]
                    cv.put(a, b, ey + dy, M[f'{hue}_terrazzo'] if dy % 5 else M[f'{hue}_woven_panel'])
    # rigging
    for i in range(-L + 4, L - 3, 5):
        for sgn in (-1, 1):
            a0, b0 = at(i, sgn * int(W))
            a1, b1 = at(i, sgn * int(ER * 0.8))
            cv.line3(a0, b0, y + 1, a1, b1, ey - EH + 1, M['linen'])
    cv.lamp(*at(L, 0), y + 2, M['lantern'])
    cv.lamp(*at(-L, 0), y + 2, M['lantern'])
    cv.chest(*at(-L // 2, 0), y + 1)
    cv.chest(*at(2, 1), y + 1)
    return {'length': 2 * L + 1, 'hues': hues}


# ---------------------------------------------------------------------------
# watchtower (the smaller end of the range)
# ---------------------------------------------------------------------------
def build_watchtower(cv, rng, q, r, y):
    st = _stone_set(rng)
    H = rng.randint(18, 40)
    rad = rng.randint(2, 3)
    cv.foundation([(a, b) for a, b, d, _ in cv.round_cells(q, r, rad + 2)], y, M[st[1]], M[st[3]])
    for yy in range(y + 1, y + H):
        cv.ring(q, r, yy, rad, M[st[1]] if yy % 6 else M[st[2]])
        cv.put(q, r, yy, M['ladder'])
    cv.put(q + rad, r, y + 1, 0)
    cv.put(q + rad, r, y + 2, 0)
    cv.disk(q, r, y + H, rad + 2, M[_wood_set(rng)[1]])
    cv.ring(q, r, y + H + 1, rad + 2, M['wrought_iron'])
    hue = rng.choice(BRIGHT)
    for k in range(3):
        cv.disk(q, r, y + H + 4 + k, rad + 1 - k, M[f'{hue}_patterned_tile'])
    for dq, dr in DIRS[::2]:
        cv.col(q + dq * (rad + 1), r + dr * (rad + 1), y + H + 1, y + H + 3, M[st[2]])
    cv.lamp(q, r, y + H + 1, M['lantern'])
    cv.put(q, r, y + H + 7, M[f'{hue}_banner'])
    return {'height': H}


BUILDERS = {
    'hot_air_balloon': build_hot_air_balloon,
    'sky_city': build_sky_city,
    'floating_fortress': build_floating_fortress,
    'world_tree': build_world_tree,
    'colossus': build_colossus,
    'megaspire': build_megaspire,
    'leviathan_wreck': build_leviathan_wreck,
    'titan_ruins': build_titan_ruins,
    'village': build_village,
    'airship': build_airship,
    'watchtower': build_watchtower,
}
FOOTPRINT = {'hot_air_balloon': 26, 'sky_city': 44, 'floating_fortress': 26, 'world_tree': 34,
             'colossus': 22, 'megaspire': 18, 'leviathan_wreck': 46, 'titan_ruins': 44,
             'village': 30, 'airship': 36, 'watchtower': 8}


# ---------------------------------------------------------------------------
# siting
# ---------------------------------------------------------------------------
def _hash(*parts):
    return random.Random('grand|' + '|'.join(str(p) for p in parts))


def site(gen, rq, rr):
    """-> None or dict(kind, q, r, y, seed). Deterministic in the sky seed."""
    rng = _hash(gen.h, rq, rr)
    if rng.random() >= CHANCE:
        return None
    tot = sum(w for _, w in KINDS)
    pick = rng.uniform(0, tot)
    kind = KINDS[-1][0]
    for k, w in KINDS:
        if pick < w:
            kind = k
            break
        pick -= w
    span = REGION * CHUNK
    q0, r0 = rq * span, rr * span
    seed = rng.getrandbits(48)
    fp = FOOTPRINT[kind]
    lo, hi = fp + 4, span - fp - 4
    # coarse sample of the region interior
    qs, rs = [], []
    for i in range(14):
        for j in range(14):
            qs.append(q0 + lo + (hi - lo) * i // 13 + rng.randint(-3, 3))
            rs.append(r0 + lo + (hi - lo) * j // 13 + rng.randint(-3, 3))
    qs, rs = np.array(qs), np.array(rs)
    c = gen.columns(qs, rs)
    land = c['land'] & ~c['skerry']
    if kind in SKY_KINDS:
        # an open-air site: no land under the footprint, near islands for scale
        open_ = ~c['land']
        idx = np.flatnonzero(open_)
        rng.shuffle(idx)
        tops_all = c['top'][land]
        for i in idx[:24]:
            q, r = int(qs[i]), int(rs[i])
            ring_q, ring_r = [], []
            for k in range(16):
                a = k / 16 * 2 * math.pi
                for d in (fp * 0.35, fp * 0.7, fp):
                    ring_q.append(q + int(math.cos(a) * d))
                    ring_r.append(r + int(math.sin(a) * d))
            cc = gen.columns(np.array(ring_q), np.array(ring_r))
            if cc['land'].any():
                continue
            ref = int(np.median(tops_all)) if len(tops_all) else 120
            y = ref + rng.randint(18, 70)
            y = int(min(max(y, CLOUD_SEA + 60), LAYERS - 90))
            return {'kind': kind, 'q': q, 'r': r, 'y': y, 'seed': seed}
        return None
    # land kinds want broad, fairly flat interior land
    ok = land & (c['e'] > 0.18) & ~c['pool']
    idx = np.flatnonzero(ok)
    rng.shuffle(idx)
    for i in idx[:16]:
        q, r = int(qs[i]), int(rs[i])
        ring_q, ring_r = [q], [r]
        for k in range(12):
            a = k / 12 * 2 * math.pi
            for d in (fp * 0.3, fp * 0.6):
                ring_q.append(q + int(math.cos(a) * d))
                ring_r.append(r + int(math.sin(a) * d))
        cc = gen.columns(np.array(ring_q), np.array(ring_r))
        inner = cc['land'][:13]
        if not inner.all() or cc['land'].mean() < 0.8 or cc['pool'][:13].any():
            continue
        t = cc['top'][cc['land']]
        if int(t.max()) - int(t.min()) > 22:
            continue
        y = int(np.median(t))
        if kind == 'megaspire' and y > LAYERS - 150:
            continue
        if kind == 'world_tree' and y > LAYERS - 140:
            continue
        return {'kind': kind, 'q': q, 'r': r, 'y': y, 'seed': seed}
    return None


_CACHE = {}


def build(gen, rq, rr):
    key = (gen.h, gen.version, rq, rr)
    if key in _CACHE:
        return _CACHE[key]
    s = site(gen, rq, rr)
    out = None
    if s:
        cv = Canvas(gen)
        if s['kind'] not in SKY_KINDS:
            cv.prefetch(s['q'], s['r'], FOOTPRINT[s['kind']] + 12)
        info = BUILDERS[s['kind']](cv, random.Random(s['seed']), s['q'], s['r'], s['y']) or {}
        buckets = {}
        for (q, r, y), (mat, meta) in cv.cells.items():
            cq, cr = q // CHUNK, r // CHUNK
            buckets.setdefault((cq, cr), []).append((q - cq * CHUNK, y, r - cr * CHUNK, mat, meta))
        packed = {}
        for k, v in buckets.items():
            a = np.array(v, np.int64)
            packed[k] = a
        out = dict(s, info=info, buckets=packed, cells=len(cv.cells))
    if len(_CACHE) > 48:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = out
    return out


def apply(gen, cq, cr, cells, meta):
    """Stamp every grand structure part that falls in chunk (cq, cr)."""
    rq, rr = cq // REGION, cr // REGION
    hit = []
    for a in (rq - 1, rq, rq + 1):
        for b in (rr - 1, rr, rr + 1):
            g = build(gen, a, b)
            if not g:
                continue
            arr = g['buckets'].get((cq, cr))
            if arr is None:
                continue
            cells[arr[:, 0], arr[:, 1], arr[:, 2]] = arr[:, 3].astype(np.uint8)
            meta[arr[:, 0], arr[:, 1], arr[:, 2]] = arr[:, 4].astype(np.uint8)
            hit.append(g['kind'])
    return hit


def occupied(gen, cq, cr, pad=1):
    """True if a grand structure stamps into chunk (cq, cr) or a chunk within pad of it."""
    regs = {((cq + dq) // REGION, (cr + dr) // REGION) for dq in (-pad, 0, pad) for dr in (-pad, 0, pad)}
    seen = set()
    for rq, rr in regs:
        for a in (rq - 1, rq, rq + 1):
            for b in (rr - 1, rr, rr + 1):
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                if not site(gen, a, b):
                    continue
                g = build(gen, a, b)
                if not g:
                    continue
                for dq in range(-pad, pad + 1):
                    for dr in range(-pad, pad + 1):
                        if (cq + dq, cr + dr) in g['buckets']:
                            return True
    return False


def nearby(gen, q, r, regions=2):
    """Grand structures near a cell (for tours, tests and the debug overlay)."""
    rq, rr = (q // CHUNK) // REGION, (r // CHUNK) // REGION
    out = []
    for a in range(rq - regions, rq + regions + 1):
        for b in range(rr - regions, rr + regions + 1):
            s = site(gen, a, b)
            if s:
                out.append(dict(s, rq=a, rr=b))
    return out


# ---------------------------------------------------------------------------
# huge trees (v6): drawn across chunk edges, a few per island
# ---------------------------------------------------------------------------
TREE_GRID = 34
TREE_CHANCE = 0.30
_TREE_SPECIES = {
    # realm: (wood, leaf, form)
    0: ('heartwood', 'canopy', 'oak'), 1: ('dark_heartwood', 'canopy', 'oak'), 2: ('heartwood', 'canopy', 'oak'),
    3: ('pale_heartwood', 'frost_canopy', 'cone'), 4: ('heartwood', 'canopy', 'oak'), 5: ('dark_heartwood', 'canopy', 'willow'),
    7: ('pale_heartwood', 'canopy', 'toadstool'), 8: ('pale_heartwood', 'canopy', 'oak'),
    9: ('cedar_heartwood', 'canopy', 'cone'), 10: ('dark_heartwood', 'violet_canopy', 'oak'),
    13: ('dark_heartwood', 'violet_canopy', 'oak'), 14: ('pale_heartwood', 'canopy', 'cone'),
    15: ('dark_heartwood', 'canopy', 'willow'),
    16: ('pale_heartwood', 'blossom_canopy', 'oak'), 17: ('dark_heartwood', 'autumn_canopy', 'oak'),
    18: ('pale_heartwood', 'frost_canopy', 'cone'), 19: ('heartwood', 'golden_canopy', 'acacia'),
}
_TREES = {}


def _tree_site(gen, gi, gj):
    key = (gen.h, gi, gj)
    if key in _TREES:
        return _TREES[key]
    rng = _hash('tree', gen.h, gi, gj)
    res = None
    if rng.random() < TREE_CHANCE:
        q = gi * TREE_GRID + rng.randint(6, TREE_GRID - 6)
        r = gj * TREE_GRID + rng.randint(6, TREE_GRID - 6)
        c = gen.columns(np.array([q]), np.array([r]))
        realm = int(c['realm'][0])
        if (bool(c['land'][0]) and not bool(c['skerry'][0]) and not bool(c['pool'][0]) and not bool(c['fall'][0])
                and float(c['e'][0]) > 0.12 and realm in _TREE_SPECIES):
            res = _build_tree(rng, q, r, int(c['top'][0]), realm)
    if len(_TREES) > 4096:
        _TREES.clear()
    _TREES[key] = res
    return res


def _build_tree(rng, q, r, top, realm):
    wood, leaf, form = _TREE_SPECIES[realm]
    wood, leaf = M[wood], M[leaf]
    cv = Canvas()
    H = rng.randint(18, 34)
    tr = 1 if H < 26 else 2
    for y in range(top + 1, top + H):
        cv.disk(q, r, y, tr if y < top + H - 6 else max(0, tr - 1), wood)
    for d, (dq, dr) in enumerate(DIRS):        # buttress roots
        cv.col(q + dq * (tr + 1), r + dr * (tr + 1), top + 1, top + 2 + d % 2, wood)
    ty = top + H
    if form == 'cone':
        for i, y in enumerate(range(top + 6, ty + 4)):
            rad = max(0, int(6 - i * 6 / (H - 2)))
            cv.disk(q, r, y, rad, leaf)
    elif form == 'toadstool':
        for k in range(4):
            cv.disk(q, r, ty + k, 7 - k * 2 if k else 7, leaf)
        for a, b in hex_ring(q, r, 6)[::3]:
            cv.put(a, b, ty - 1, M['glowcap'])
    elif form == 'acacia':
        for k, (dq, dr) in enumerate(DIRS[::2]):
            cv.line3(q, r, ty - 4, q + dq * 4, r + dr * 4, ty, wood)
            cv.disk(q + dq * 4, r + dr * 4, ty + 1, 3, leaf)
        cv.disk(q, r, ty + 2, 4, leaf)
    else:
        R = rng.uniform(5.0, 8.0)
        for a, b, d, ang in cv.round_cells(q, r, R):
            hh = int(math.sqrt(max(0.0, R * R - d * d)) * 0.9)
            for y in range(ty - hh // 2 - 1, ty + hh + 1):
                cv.put(a, b, y, leaf)
        for k, (dq, dr) in enumerate(DIRS):
            cv.line3(q, r, ty - 6, q + dq * 4, r + dr * 4, ty - 2, wood)
        if form == 'willow':
            for a, b, d, ang in cv.round_cells(q, r, R):
                if d > R - 1.2 and (a + b) % 2 == 0:
                    cv.col(a, b, ty - 7, ty - 1, M['vine'])
    packed = {}
    for (a, b, y), (mat, meta) in cv.cells.items():
        cq, cr = a // CHUNK, b // CHUNK
        packed.setdefault((cq, cr), []).append((a - cq * CHUNK, y, b - cr * CHUNK, mat))
    out = {k: np.array(v, np.int64) for k, v in packed.items()}
    out['info'] = {'q': q, 'r': r, 'top': top, 'H': H, 'realm': realm, 'form': form}
    return out


def giant_trees(gen, cq, cr, cells):
    """Stamp huge trees whose cells fall in this chunk, into air only."""
    q0, r0 = cq * CHUNK, cr * CHUNK
    n = 0
    for gi in range((q0 - 12) // TREE_GRID, (q0 + CHUNK + 12) // TREE_GRID + 1):
        for gj in range((r0 - 12) // TREE_GRID, (r0 + CHUNK + 12) // TREE_GRID + 1):
            t = _tree_site(gen, gi, gj)
            if not t:
                continue
            arr = t.get((cq, cr))
            if arr is None:
                continue
            free = cells[arr[:, 0], arr[:, 1], arr[:, 2]] == 0
            a = arr[free]
            cells[a[:, 0], a[:, 1], a[:, 2]] = a[:, 3].astype(np.uint8)
            n += 1
    return n

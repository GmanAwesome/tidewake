"""Procedural structures: a registry of families, placement rules, modular pieces,
condition/decoration, and support for surface, buried and aerial sites.

New structure types register with @register(...). The generator calls place() once
per chunk; older (v1) skies skip this so existing worlds stay unchanged.
"""
import random

import numpy as np

from .config import CHUNK, LAYERS, CLOUD_SEA
from .hexgrid import DIRS, hex_distance
from .noise import hash2
from . import materials as MT

M = MT.ID

INTACT, ABANDONED, RUINED, OVERGROWN = range(4)
COND_NAMES = ('intact', 'abandoned', 'ruined', 'overgrown')

# loot tables (stored in chest meta bits 3-6; 0 = player-placed, empty)
LOOT_CAMP = 1
LOOT_STORE = 2
LOOT_TEMPLE = 3
LOOT_CHAMBER = 4
LOOT_STONES = 5
LOOT_BOAT = 6

REGION = 6          # one structure attempt per REGION x REGION chunks
REGION_CHANCE = 52  # percent of regions that get a structure

# family, name, flags, builder
TYPES = []


def register(family, name, *, surface=True, buried=False, aerial=False,
             min_thickness=6, max_slope=2, biomes=None, rarity=1.0, pad=3,
             min_version=2, sky=False):
    """Hook for adding a structure type without touching the placer."""
    def deco(fn):
        TYPES.append({
            'family': family, 'name': name, 'fn': fn,
            'surface': surface, 'buried': buried, 'aerial': aerial,
            'min_thickness': min_thickness, 'max_slope': max_slope,
            'biomes': set(biomes) if biomes is not None else None,
            'rarity': rarity, 'pad': pad,
            'min_version': min_version, 'sky': sky,
        })
        return fn
    return deco


def _h64(a, b, seed):
    return int(hash2(np.int64(a), np.int64(b), int(seed) & ((1 << 64) - 1)))


def _rng(*parts):
    """Portable deterministic RNG (Random() will not take a tuple)."""
    return random.Random('|'.join(str(p) for p in parts))


# ---------------------------------------------------------------------------
# palette + condition
# ---------------------------------------------------------------------------
def palette(realm, cond):
    """Biome-tinted building materials; condition swaps in wear and growth."""
    planks = M['planks']
    log = M['heartwood']
    if realm == 9:
        planks, log = M['cedar_planks'], M['cedar_heartwood']
    elif realm in (8, 12, 14):
        planks, log = M['pale_planks'], M['pale_heartwood']
    elif realm in (1, 15):
        planks, log = M['dark_planks'], M['dark_heartwood']
    stone = {
        1: M['rosestone'], 4: M['basalt'], 8: M['sandstone'], 10: M['cinder'],
        11: M['pale_stone'], 12: M['chalk'], 13: M['starstone'],
        14: M['pale_stone'], 2: M['rosestone'],
    }.get(realm, M['stone'])
    if realm == 11:
        stone = M['pale_stone']
    brick = {
        2: M['rosestone_bricks'], 4: M['basalt_bricks'], 8: M['sandstone_bricks'],
        9: M['stone_bricks'], 10: M['cinder_bricks'], 11: M['lavender_bricks'],
        12: M['chalk_bricks'], 13: M['starstone'] and M['dusk_bricks'],
        14: M['snow_bricks'], 15: M['verdigris_bricks'], 3: M['snow_bricks'],
    }.get(realm, M['stone_bricks'])
    if realm == 13:
        brick = M['dusk_bricks']
    tile = {
        2: M['rosestone_tiles'], 4: M['basalt_tiles'], 8: M['sandstone_tiles'],
        11: M['lavender_tiles'], 12: M['chalk_tiles'], 13: M['starstone_tiles'],
        15: M['verdigris_tiles'],
    }.get(realm, M['stone_tiles'])
    roof = M['shingles'] if realm in (4, 10, 13) else M['thatch']
    floor = M['packed_earth'] if realm not in (3, 13, 14) else tile
    lamp = M['ember_lamp']
    if realm in (13, 7):
        lamp = M['aether_lamp']
    elif realm == 15:
        lamp = M['verdigris_lamp']
    pal = dict(planks=planks, log=log, stone=stone, brick=brick, tile=tile,
               roof=roof, floor=floor, lamp=lamp,
               cobble=M['cobble'], moss=M['mossy_bricks'],
               glass=M['glass'] if cond == INTACT else M['glass'],
               cloth=M['linen'] if realm not in (11, 13) else M['dusk_cloth'])
    if realm == 11:
        pal['cloth'] = M['dusk_cloth']
    if cond == OVERGROWN:
        pal['brick'] = M['mossy_bricks']
        pal['floor'] = M['heather'] if realm in (0, 11, 9, 5) else M['mossrock']
        pal['roof'] = M['thatch']
    if cond == RUINED:
        pal['floor'] = pal['cobble']
    return pal


def wear(st, mat):
    """Condition may skip, crack, or overgrow a construction block."""
    c = st.cond
    if mat == 0:
        return 0
    if c == INTACT:
        return mat
    if c == RUINED:
        if st.chance(0.22):
            return 0
        if st.chance(0.28) and mat not in (M['chest'], M['door'], M['ladder'], M['bedroll']):
            return st.pal['cobble']
    if c == ABANDONED:
        if st.chance(0.08):
            return 0
    if c == OVERGROWN:
        if mat in (st.pal['brick'], st.pal['stone'], M['stone_bricks'], M['bricks']):
            if st.chance(0.45):
                return M['mossy_bricks']
        if st.chance(0.06):
            return 0
    return mat


# ---------------------------------------------------------------------------
# stamp
# ---------------------------------------------------------------------------
class Stamp:
    def __init__(self, cells, meta, top, bot, land, realm, cq, cr, rng, cond, pal, world=None):
        self.cells, self.meta = cells, meta
        self.top, self.bot, self.land, self.realm = top, bot, land, realm
        self.cq, self.cr = cq, cr
        self.q0, self.r0 = cq * CHUNK, cr * CHUNK
        self.rng = rng
        self.cond = cond
        self.pal = pal
        self.world = world

    def chance(self, p):
        return self.rng.random() < p

    def local(self, q, r):
        return q - self.q0, r - self.r0

    def in_bounds(self, q, r, y=None):
        lq, lr = self.local(q, r)
        if self.world is not None:
            if y is not None and not (1 <= y < LAYERS - 1):
                return False
            return True
        ok = 0 <= lq < CHUNK and 0 <= lr < CHUNK
        if y is not None:
            ok = ok and 1 <= y < LAYERS - 1
        return ok

    def get(self, q, r, y):
        if self.world is not None:
            return self.world.get(q, r, y)
        lq, lr = self.local(q, r)
        if not (0 <= lq < CHUNK and 0 <= lr < CHUNK and 0 <= y < LAYERS):
            return 0
        return int(self.cells[lq, y, lr])

    def ground(self, q, r):
        if self.world is not None:
            t = self.world.column_top(q, r)
            return int(t) if t is not None else None
        lq, lr = self.local(q, r)
        if not (0 <= lq < CHUNK and 0 <= lr < CHUNK):
            return None
        if not self.land[lq, lr]:
            return None
        return int(self.top[lq, lr])

    def thickness(self, q, r):
        lq, lr = self.local(q, r)
        if self.world is not None:
            t = self.world.column_top(q, r)
            # walk down for bottom
            if t is None:
                return 0
            y = t
            while y > 0 and self.world.get(q, r, y) > 0:
                y -= 1
            return t - y
        if not (0 <= lq < CHUNK and 0 <= lr < CHUNK) or not self.land[lq, lr]:
            return 0
        return int(self.top[lq, lr] - self.bot[lq, lr] + 1)

    def put(self, q, r, y, mat, meta=0, force=False):
        if mat and not force:
            mat = wear(self, mat)
        if not self.in_bounds(q, r, y):
            return False
        cur = self.get(q, r, y)
        if cur in (M['dormant_spire'], M['awake_spire']) and not force:
            return False
        if self.world is not None:
            self.world.set(q, r, y, int(mat), int(meta), now=False)
            return True
        lq, lr = self.local(q, r)
        self.cells[lq, y, lr] = int(mat)
        if self.meta is not None:
            self.meta[lq, y, lr] = int(meta)
        return True

    def clear_above(self, q, r, y):
        for yy in range(y, min(LAYERS - 1, y + 8)):
            cur = self.get(q, r, yy)
            if cur in (M['dormant_spire'], M['awake_spire']):
                break
            self.put(q, r, yy, 0, force=True)

    def fill_to(self, q, r, y, mat):
        """Fill air under y so the pad sits in the terrain."""
        gy = self.ground(q, r)
        start = (gy + 1) if gy is not None else y - 4
        if start > y:
            # cut down
            for yy in range(y + 1, start + 1):
                self.put(q, r, yy, 0, force=True)
            self.put(q, r, y, mat, force=True)
            return
        for yy in range(start, y):
            if self.get(q, r, yy) == 0:
                self.put(q, r, yy, mat, force=True)

    def flatten(self, cq, cr, rad, y=None, floor=None):
        """Level a hex pad to y (default: median ground) and lay a floor."""
        cells = [(cq + dq, cr + dr) for dq in range(-rad, rad + 1)
                 for dr in range(max(-rad, -dq - rad), min(rad, -dq + rad) + 1)]
        tops = [self.ground(q, r) for q, r in cells]
        tops = [t for t in tops if t is not None]
        if not tops:
            return None
        y = int(sorted(tops)[len(tops) // 2]) if y is None else y
        floor = floor or self.pal['floor']
        for q, r in cells:
            self.fill_to(q, r, y, self.pal['stone'])
            self.put(q, r, y, floor, force=True)
            self.clear_above(q, r, y + 1)
        return y

    def column(self, q, r, y0, h, mat):
        for i in range(h):
            self.put(q, r, y0 + i, mat)

    def disk(self, q, r, y, rad, mat, force=False):
        for dq in range(-rad, rad + 1):
            for dr in range(max(-rad, -dq - rad), min(rad, -dq + rad) + 1):
                self.put(q + dq, r + dr, y, mat, force=force)

    def ring(self, q, r, y, rad, mat, h=1):
        for dq in range(-rad, rad + 1):
            for dr in range(max(-rad, -dq - rad), min(rad, -dq + rad) + 1):
                if hex_distance(0, 0, dq, dr) == rad:
                    self.column(q + dq, r + dr, y, h, mat)

    def hex_line(self, q0, r0, q1, r1):
        n = max(1, (abs(q1 - q0) + abs(r1 - r0) + abs((q0 + r0) - (q1 + r1))) // 2)
        out = []
        for i in range(n + 1):
            t = i / n
            q = int(round(q0 + (q1 - q0) * t))
            r = int(round(r0 + (r1 - r0) * t))
            if not out or out[-1] != (q, r):
                out.append((q, r))
        return out

    def path(self, q0, r0, q1, r1, mat=None):
        mat = mat or M['packed_earth']
        for q, r in self.hex_line(q0, r0, q1, r1):
            y = self.ground(q, r)
            if y is None:
                continue
            self.put(q, r, y, mat, force=True)
            # trim plants on the path
            up = self.get(q, r, y + 1)
            if up in (M['sprout'], M['petals'], M['bloom'], M['vine'], M['berry_bush']):
                self.put(q, r, y + 1, 0, force=True)

    def door(self, q, r, y, facing=0):
        if self.cond == RUINED and self.chance(0.5):
            self.put(q, r, y, 0, force=True)
            self.put(q, r, y + 1, 0, force=True)
            return
        self.put(q, r, y, M['door'], facing & 7, force=True)
        self.put(q, r, y + 1, M['door'], (facing & 7) | 16, force=True)

    def chest(self, q, r, y, table, facing=0):
        if self.cond == RUINED and self.chance(0.35):
            return
        if self.cond == ABANDONED and self.chance(0.2):
            return
        meta = (facing & 7) | ((table & 15) << 3)
        self.put(q, r, y, M['chest'], meta, force=True)

    def lamp(self, q, r, y):
        if self.cond == RUINED and not self.chance(0.25):
            return
        if self.cond == ABANDONED and not self.chance(0.4):
            return
        if self.cond == OVERGROWN and self.chance(0.5):
            self.put(q, r, y, M['glowcap'], force=True)
            return
        self.put(q, r, y, self.pal['lamp'], force=True)

    def debris(self, q, r, rad, n=6):
        mats = [self.pal['cobble'], self.pal['planks'], M['bricks'] if self.chance(0.5) else self.pal['stone']]
        if self.cond == OVERGROWN:
            mats += [M['vine'], M['mossrock'], M['heather'], M['sprout']]
        for _ in range(n):
            dq = self.rng.randint(-rad, rad)
            dr = self.rng.randint(-rad, rad)
            if hex_distance(0, 0, dq, dr) > rad:
                continue
            y = self.ground(q + dq, r + dr)
            if y is None:
                continue
            mat = self.rng.choice(mats)
            if mat in (M['vine'], M['sprout']):
                self.put(q + dq, r + dr, y + 1, mat, force=True)
            else:
                # small scatter on the floor, don't bury the pad
                if self.get(q + dq, r + dr, y + 1) == 0 and self.chance(0.7):
                    self.put(q + dq, r + dr, y + 1, mat if self.chance(0.4) else 0, force=True)

    def vines_on(self, q, r, y, h):
        if self.cond not in (OVERGROWN, RUINED):
            return
        for i in range(h):
            if self.chance(0.5):
                # hang off a random side
                dq, dr = DIRS[self.rng.randrange(6)]
                self.put(q + dq, r + dr, y + i, M['vine'])


def _house_walls(st, q, r, y, rad, h, door_dir):
    """Hollow hex house: walls of planks/wattle, door on door_dir, glass windows."""
    pal, cond = st.pal, st.cond
    wall = pal['planks'] if st.chance(0.65) else M['wattle']
    if cond == RUINED:
        wall = pal['cobble']
    dq, dr = DIRS[door_dir % 6]
    for a in range(-rad, rad + 1):
        for b in range(max(-rad, -a - rad), min(rad, -a + rad) + 1):
            d = hex_distance(0, 0, a, b)
            if d != rad:
                continue
            is_door = (a, b) == (dq * rad, dr * rad) or (a, b) == (dq * (rad - 0), dr * rad)
            # prefer the cell in door_dir at this radius
            is_door = (a == dq * rad and b == dr * rad)
            for i in range(h):
                if is_door and i < 2:
                    continue
                mat = wall
                # windows on the mid layer, not on the door face
                if i == 1 and not is_door and st.chance(0.35) and cond == INTACT:
                    mat = pal['glass'] if st.chance(0.7) else M['green_glass']
                st.put(q + a, r + b, y + 1 + i, mat)
            if is_door:
                st.door(q + a, r + b, y + 1, door_dir)
            st.vines_on(q + a, r + b, y + 1, h)
    # roof
    roof = pal['roof']
    for layer, rr in enumerate(range(rad, -1, -1)):
        yy = y + 1 + h + layer
        if cond == RUINED and layer == 0 and st.chance(0.4):
            # hole in the roof
            st.disk(q, r, yy, rr, roof)
            st.put(q, r, yy, 0, force=True)
        else:
            st.disk(q, r, yy, rr, roof)
    # interior floor already flattened; furniture
    st.put(q, r, y, pal['floor'], force=True)


# ---------------------------------------------------------------------------
# families
# ---------------------------------------------------------------------------
@register('settlement', 'hut', surface=True, min_thickness=5, max_slope=2, pad=4)
def build_hut(st, q, r, y, door_dir=0, with_well=False):
    y = st.flatten(q, r, 3, y, st.pal['floor'])
    if y is None:
        return
    _house_walls(st, q, r, y, 2, 3, door_dir)
    # reason to visit: a bed, a chest of supplies, sometimes a bench
    st.put(q, r + 1, y + 1, M['bedroll'], force=True)
    st.chest(q, r - 1, y + 1, LOOT_CAMP, door_dir)
    if st.cond == INTACT or st.chance(0.4):
        st.put(q + 1, r, y + 1, M['tinker_bench'], door_dir, force=True)
    st.lamp(q - 1, r + 1, y + 2)
    if st.cond in (ABANDONED, RUINED, OVERGROWN):
        st.debris(q, r, 3, 7)
    if with_well:
        build_well(st, q + 3, r - 1, y)


@register('settlement', 'village', surface=True, min_thickness=6, max_slope=2, pad=5)
def build_village(st, q, r, y, door_dir=0):
    """Two or three huts, a well, paths and a storage shed."""
    y = st.flatten(q, r, 6, y, M['packed_earth'])
    if y is None:
        return
    n = 3 if st.chance(0.45) else 2
    spots = [(q - 3, r - 1), (q + 3, r - 2), (q + 1, r + 3)][:n]
    for i, (sq, sr) in enumerate(spots):
        st.flatten(sq, sr, 2, y, st.pal['floor'])
        _house_walls(st, sq, sr, y, 2, 3, (door_dir + i) % 6)
        if i == 0:
            st.put(sq, sr + 1, y + 1, M['bedroll'], force=True)
            st.chest(sq, sr - 1, y + 1, LOOT_CAMP, door_dir)
            st.put(sq + 1, sr, y + 1, M['tinker_bench'], door_dir, force=True)
        elif i == 1:
            # storage
            st.chest(sq, sr, y + 1, LOOT_STORE, door_dir)
            st.chest(sq + 1, sr, y + 1, LOOT_STORE, (door_dir + 1) % 6)
            if st.cond == INTACT:
                st.put(sq - 1, sr, y + 1, M['kiln'], door_dir, force=True)
        else:
            st.put(sq, sr, y + 1, M['bedroll'], force=True)
            st.lamp(sq, sr + 1, y + 2)
        st.path(q, r, sq, sr, M['packed_earth'] if st.cond != RUINED else M['cobble'])
    build_well(st, q, r, y)
    if st.cond != INTACT:
        st.debris(q, r, 6, 12)


def build_well(st, q, r, y):
    st.flatten(q, r, 1, y, st.pal['cobble'])
    st.ring(q, r, y + 1, 1, st.pal['cobble'], 1)
    st.put(q, r, y, M['water'] if st.cond != RUINED else 0, force=True)
    st.put(q, r, y - 1, M['water'] if y > 2 else st.pal['cobble'], force=True)


@register('ruin', 'standing_stones', surface=True, min_thickness=5, max_slope=3, pad=5)
def build_stones(st, q, r, y):
    y = st.flatten(q, r, 4, y, st.pal['stone'])
    if y is None:
        return
    n = st.rng.randint(5, 8)
    rad = 3
    mat = st.pal['stone'] if st.chance(0.5) else M['carved_stone']
    for i in range(n):
        ang = i / n
        # hex-ish ring: pick n points around radius 3
        dq, dr = DIRS[i % 6]
        k = 2 + (i % 3) % 2
        # walk around the ring with slight jitter
        spots = [(q + a, r + b) for a in range(-rad, rad + 1)
                 for b in range(max(-rad, -a - rad), min(rad, -a + rad) + 1)
                 if hex_distance(0, 0, a, b) == rad]
        if not spots:
            continue
        sq, sr = spots[int(ang * len(spots)) % len(spots)]
        h = 3 + (st.rng.randint(0, 3) if st.cond != RUINED else st.rng.randint(0, 2))
        if st.cond == RUINED and st.chance(0.25):
            h = max(1, h - 2)
            st.put(sq, sr, y + 1, st.pal['cobble'])
        st.column(sq, sr, y + 1, h, mat)
        st.vines_on(sq, sr, y + 1, h)
    # center altar: a reason to visit
    st.put(q, r, y, M['carved_stone'] if st.cond != OVERGROWN else M['mossrock'], force=True)
    st.put(q, r, y + 1, M['waystone'] if st.cond != RUINED or st.chance(0.7) else M['plinth'], force=True)
    if st.chance(0.45) or st.cond == INTACT:
        st.put(q, r + 1, y + 1, M['lumen_shard'] if st.chance(0.5) else st.pal['lamp'], force=True)
    if st.chance(0.55):
        st.chest(q + 1, r, y + 1, LOOT_STONES, 0)
    if st.cond in (OVERGROWN, RUINED, ABANDONED):
        st.debris(q, r, 4, 8)


@register('ruin', 'temple', surface=True, min_thickness=8, max_slope=2, pad=6)
def build_temple(st, q, r, y):
    y = st.flatten(q, r, 5, y, st.pal['tile'])
    if y is None:
        return
    # stepped stylobate
    st.disk(q, r, y, 5, st.pal['stone'], force=True)
    st.disk(q, r, y + 1, 4, st.pal['tile'], force=True)
    y1 = y + 1
    # columns
    mat = M['carved_stone']
    spots = [(q + a, r + b) for a in range(-3, 4)
             for b in range(max(-3, -a - 3), min(3, -a + 3) + 1)
             if hex_distance(0, 0, a, b) == 3]
    for i, (sq, sr) in enumerate(spots):
        if i % 2 and st.cond == RUINED and st.chance(0.4):
            st.column(sq, sr, y1 + 1, 1, st.pal['cobble'])
            continue
        h = 4 if st.cond != RUINED else st.rng.randint(2, 4)
        st.column(sq, sr, y1 + 1, h, mat)
        st.vines_on(sq, sr, y1 + 1, h)
    # back wall / shrine
    for a, b in ((-2, 2), (-1, 2), (0, 2), (1, 1), (2, 0)):
        st.column(q + a, r + b, y1 + 1, 3 if st.cond != RUINED else 2, st.pal['brick'])
    # altar and loot — the reason to visit
    st.put(q, r, y1, M['plinth'], force=True)
    st.put(q, r, y1 + 1, M['waystone'], force=True)
    st.put(q, r, y1 + 2, st.pal['lamp'] if st.cond != RUINED else M['lumen_shard'], force=True)
    st.chest(q, r - 1, y1 + 1, LOOT_TEMPLE, 0)
    if st.cond == INTACT:
        st.put(q + 1, r - 1, y1 + 1, M['bedroll'], force=True)
    if st.cond != INTACT:
        st.debris(q, r, 5, 10)


@register('ruin', 'chamber', buried=True, surface=False, min_thickness=14, max_slope=4, pad=4)
def build_chamber(st, q, r, y):
    """A buried room with a ladder shaft and rarer loot."""
    gy = st.ground(q, r)
    if gy is None:
        return
    floor = max(int(st.bot[st.local(q, r)[0], st.local(q, r)[1]]) + 2 if st.world is None else gy - 9, 3)
    # if we have bot
    lq, lr = st.local(q, r)
    if st.world is None and 0 <= lq < CHUNK and 0 <= lr < CHUNK:
        floor = max(int(st.bot[lq, lr]) + 2, gy - 10)
    floor = max(floor, 3)
    ceil = floor + 4
    if ceil >= gy:
        ceil = gy - 1
        floor = max(3, ceil - 4)
    rad = 2
    # carve room
    for a in range(-rad, rad + 1):
        for b in range(max(-rad, -a - rad), min(rad, -a + rad) + 1):
            for yy in range(floor, ceil + 1):
                d = hex_distance(0, 0, a, b)
                if d < rad:
                    st.put(q + a, r + b, yy, 0, force=True)
                else:
                    st.put(q + a, r + b, yy, st.pal['brick'], force=True)
            st.put(q + a, r + b, floor, st.pal['tile'] if hex_distance(0, 0, a, b) < rad else st.pal['brick'], force=True)
            if ceil + 1 < gy:
                st.put(q + a, r + b, ceil, st.pal['stone'], force=True)
    # shaft + ladder up to the surface
    for yy in range(ceil, gy + 1):
        st.put(q, r, yy, 0, force=True)
        st.put(q, r, yy, M['ladder'], 0, force=True)
    # rim at the surface so you notice the shaft
    st.ring(q, r, gy, 1, M['carved_stone'], 1)
    st.put(q, r, gy, 0, force=True)
    st.put(q, r, gy, M['ladder'], 0, force=True)
    # chamber furnishings — rarer loot is the reason to climb down
    st.chest(q + 1, r, floor + 1, LOOT_CHAMBER, 0)
    # always two lamps (st.lamp often skipped these in ruined/abandoned rooms,
    # which left the chamber reading as a dark pit)
    st.put(q - 1, r, ceil - 1, M['lumen_lamp'], force=True)
    st.put(q + 1, r, floor + 1, M['ember_lamp'], force=True)
    st.put(q, r + 1, floor + 1, M['waystone'], force=True)
    if st.cond == OVERGROWN:
        st.put(q - 1, r + 1, floor + 1, M['glowcap'], force=True)
        st.put(q + 1, r - 1, floor + 1, M['vine'], force=True)


@register('aerial', 'sky_boat', aerial=True, surface=False, min_thickness=4, max_slope=5, pad=5)
def build_boat(st, q, r, y, edge_dir=0):
    """A small sky boat moored at an island edge, with a walkway back to land."""
    dq, dr = DIRS[edge_dir % 6]
    # port / starboard
    pq, pr = DIRS[(edge_dir + 2) % 6]
    sq, sr = DIRS[(edge_dir + 4) % 6]
    gy = st.ground(q, r)
    if gy is None:
        gy = y
    deck = gy + 1
    pl = st.pal['planks']
    # solid hull: 6 long, 3 wide, keel + deck + gunwales
    cells = []
    for i in range(-1, 5):
        for s, (wq, wr) in ((0, (0, 0)), (-1, (pq, pr)), (1, (sq, sr))):
            tq, tr = q + dq * i + wq, r + dr * i + wr
            cells.append((tq, tr, s, i))
            st.put(tq, tr, deck - 1, pl, force=True)
            st.put(tq, tr, deck, pl, force=True)
            # gunwale on the sides and at the bow/stern, leave a walk along the middle
            if s != 0 or i in (-1, 4):
                if not (st.cond == RUINED and st.chance(0.4)):
                    st.put(tq, tr, deck + 1, pl, force=True)
    # mast + sail, midships
    mq, mr = q + dq * 2, r + dr * 2
    st.column(mq, mr, deck + 1, 4 if st.cond != RUINED else 2, st.pal['log'])
    if st.cond != RUINED:
        st.put(mq + pq, mr + pr, deck + 3, st.pal['cloth'], force=True)
        st.put(mq + pq, mr + pr, deck + 4, st.pal['cloth'], force=True)
        st.put(mq, mr, deck + 5, st.pal['cloth'], force=True)
        st.put(mq + sq, mr + sr, deck + 3, st.pal['cloth'], force=True)
        st.put(mq + sq, mr + sr, deck + 4, st.pal['cloth'], force=True)
    # walkway back onto the island (inward)
    for i in range(0, 4):
        tq, tr = q - dq * i, r - dr * i
        gy2 = st.ground(tq, tr)
        st.put(tq, tr, deck, pl, force=True)
        if gy2 is not None and abs(gy2 - deck) <= 2:
            break
        st.put(tq, tr, deck - 1, pl, force=True)
    st.put(q, r, deck, M['ladder'], edge_dir, force=True)
    # reason to visit
    st.put(q + dq, r + dr, deck + 1, M['bedroll'], force=True)
    st.chest(q + dq * 3, r + dr * 3, deck + 1, LOOT_BOAT, edge_dir)
    st.lamp(mq, mr, deck + 3)
    if st.cond != INTACT:
        st.debris(q + dq, r + dr, 3, 5)


# ---------------------------------------------------------------------------
# placement
# ---------------------------------------------------------------------------
def _slope(col, P, a, b):
    top = col['top']
    pa, pb = a + P, b + P
    t = int(top[pa, pb])
    s = 0
    for dq, dr in DIRS:
        s = max(s, abs(t - int(top[pa + dq, pb + dr])))
    return s


def _is_edge(col, P, a, b):
    land = col['land']
    pa, pb = a + P, b + P
    for i, (dq, dr) in enumerate(DIRS):
        if not land[pa + dq, pb + dr]:
            return True, i
    return False, 0


def _pick_condition(family, h):
    roll = (h >> 24) % 10
    if family == 'settlement':
        return [INTACT, INTACT, INTACT, INTACT, ABANDONED, ABANDONED, RUINED, RUINED, OVERGROWN, OVERGROWN][roll]
    if family == 'ruin':
        return [INTACT, ABANDONED, ABANDONED, RUINED, RUINED, RUINED, RUINED, OVERGROWN, OVERGROWN, OVERGROWN][roll]
    return [INTACT, INTACT, INTACT, INTACT, INTACT, ABANDONED, ABANDONED, RUINED, RUINED, OVERGROWN][roll]


def place(gen, cq, cr, cells, meta, col, sl):
    """Try to stamp at most one structure into this chunk. Deterministic in the seed."""
    ver = getattr(gen, 'version', 1)
    if ver >= 5:
        return place_v5(gen, cq, cr, cells, meta, col, sl)
    if ver != 2:
        return None
    P = sl[0].start
    rq, rr = cq // REGION, cr // REGION
    h = _h64(rq, rr, gen.h + 0xA11E)
    if ((h >> 20) % 100) >= REGION_CHANCE:
        return None
    aq = rq * REGION + (h % REGION)
    ar = rr * REGION + ((h >> 8) % REGION)
    if (aq, ar) != (cq, cr):
        return None
    if getattr(gen, 'version', 5) >= 6:
        from . import grand as GR
        if GR.occupied(gen, cq, cr):
            return None          # leave room for the grand structure instead of overlapping it
    top = col['top'][sl]
    bot = col['bottom'][sl]
    land = col['land'][sl]
    realm = col['realm'][sl]
    # collect candidate columns
    cands = []
    for a in range(4, CHUNK - 4):
        for b in range(4, CHUNK - 4):
            if not land[a, b]:
                continue
            th = int(top[a, b] - bot[a, b] + 1)
            slp = _slope(col, P, a, b)
            edge, edir = _is_edge(col, P, a, b)
            cands.append((slp, th, edge, edir, a, b, int(top[a, b]), int(realm[a, b])))
    if not cands:
        return None
    # pick a family, then a type that fits
    fam_roll = (h >> 16) % 10
    edges = [c for c in cands if c[2]]
    thick = [c for c in cands if c[1] >= 14]
    if fam_roll >= 8 and edges:
        family = 'aerial'
    elif fam_roll >= 5:
        family = 'ruin'
    else:
        family = 'settlement'
        # settlements want flatter ground
        if not any(c[0] <= 2 and not c[2] for c in cands) and edges:
            family = 'aerial' if fam_roll & 1 else 'ruin'
    types = [t for t in TYPES if t['family'] == family and t.get('min_version', 2) <= 2]
    if family == 'ruin':
        # prefer a chamber when the island is thick enough
        if thick and ((h >> 12) % 3 == 0):
            types = [t for t in types if t['buried']] or types
        else:
            types = [t for t in types if not t['buried']] or types
    if not types:
        return None
    typ = types[(h >> 4) % len(types)]
    # filter candidates by rules
    fit = []
    for slp, th, edge, edir, a, b, y, rm in cands:
        if typ['biomes'] is not None and rm not in typ['biomes']:
            continue
        if th < typ['min_thickness']:
            continue
        if typ['aerial'] and not edge:
            continue
        if typ['surface'] and not typ['aerial'] and slp > typ['max_slope']:
            continue
        if typ['buried'] and th < typ['min_thickness']:
            continue
        # villages need more interior land
        if typ['name'] == 'village' and (edge or slp > typ['max_slope']):
            continue
        fit.append((slp, th, edge, edir, a, b, y, rm))
    if not fit:
        return None
    # prefer flatter, thicker (or edgier for boats)
    if typ['aerial']:
        fit.sort(key=lambda c: (0 if c[2] else 1, c[0], -c[1]))
    elif typ['buried']:
        fit.sort(key=lambda c: (-c[1], c[0]))
    else:
        fit.sort(key=lambda c: (c[0], -c[1]))
    pick = fit[h % min(len(fit), 5)]
    slp, th, edge, edir, a, b, y, rm = pick
    cond = _pick_condition(family, h)
    pal = palette(rm, cond)
    rng = _rng(h, cq, cr, typ['name'], cond, y)
    st = Stamp(cells, meta, top, bot, land, realm, cq, cr, rng, cond, pal)
    q = cq * CHUNK + a
    r = cr * CHUNK + b
    kwargs = {}
    if typ['name'] in ('hut', 'village'):
        kwargs['door_dir'] = (h >> 6) % 6
    if typ['name'] == 'sky_boat':
        kwargs['edge_dir'] = edir
    typ['fn'](st, q, r, y, **kwargs)
    return typ['name'], cond, q, r, y


def stamp_world(world, q, r, typ_name, cond=INTACT, seed=1, realm=0):
    """Stamp a named type into a live world (tours and showcases)."""
    typ = next((t for t in TYPES if t['name'] == typ_name), None)
    if typ is None:
        raise KeyError(typ_name)
    pal = palette(realm, cond)
    rng = _rng(seed, typ_name, cond, q, r)
    # dummy arrays; Stamp uses world.set
    st = Stamp(None, None, None, None, None, None, 0, 0, rng, cond, pal, world=world)
    y = st.ground(q, r) or 40
    kwargs = {}
    if typ_name in ('hut', 'village', 'hamlet'):
        kwargs['door_dir'] = seed % 6
    if typ_name in ('sky_boat', 'lighthouse', 'waterfall_temple'):
        # face the first empty neighbour if we can
        edir = 0
        for i, (dq, dr) in enumerate(DIRS):
            if st.ground(q + dq, r + dr) is None:
                edir = i
                break
        kwargs['edge_dir'] = edir
    typ['fn'](st, q, r, y, **kwargs)
    if hasattr(world, 'mark_dirty'):
        try:
            world.mark_dirty(q, r)
        except Exception:
            pass
    return typ_name, cond, q, r, y


def fill_chest(inv, table, seed, q, r, y):
    """Deterministic loot for a generated chest, based on its table id."""
    from . import items as I
    rng = _rng(int(seed), int(q), int(r), int(y), int(table))

    def put(iid, lo, hi=None):
        n = lo if hi is None else rng.randint(lo, hi)
        if n > 0:
            inv.add(iid, n)

    common_food = [I.BERRIES.id, I.PIE.id, I.STEW.id]
    if table == LOOT_CAMP:
        put(I.STICK.id, 2, 6)
        put(M['planks'], 2, 8)
        put(rng.choice(common_food), 1, 4)
        put(M['glowstick'], 1, 3)
        if rng.random() < 0.5:
            put(I.FLUFF.id, 1, 4)
        if rng.random() < 0.35:
            put(I.EMBERITE.id, 1, 3)
    elif table == LOOT_STORE:
        put(M['planks'], 4, 12)
        put(M['bricks'], 2, 8)
        put(M['glass'], 0, 4)
        put(I.BRICK.id, 2, 8)
        put(rng.choice(common_food), 1, 3)
        if rng.random() < 0.4:
            put(I.VERDIGRIS.id, 1, 3)
        if rng.random() < 0.25:
            put(I.SILVERINE.id, 1, 2)
    elif table == LOOT_TEMPLE:
        put(I.GLIMMER.id, 2, 6)
        put(M['crystal'], 1, 4)
        put(M['polished_stone'], 2, 6)
        put(M['carved_stone'], 1, 3)
        if rng.random() < 0.5:
            put(I.SILVERINE.id, 1, 3)
        if rng.random() < 0.3:
            put(M['aether_lamp'], 1, 1)
        put(M['lumen_shard'], 0, 3)
    elif table == LOOT_CHAMBER:
        put(I.GLIMMER.id, 3, 8)
        put(M['lumen_shard'], 1, 4)
        if rng.random() < 0.55:
            put(I.AETHERITE.id, 1, 2)
        if rng.random() < 0.45:
            put(I.SILVERINE.id, 1, 3)
        put(M['starstone'], 0, 4)
        put(M['aether_lamp'] if rng.random() < 0.5 else M['lumen_lamp'], 1, 1)
        if rng.random() < 0.3:
            put(I.AETHERITE.id, 1, 1)
    elif table == LOOT_STONES:
        put(I.GLIMMER.id, 1, 4)
        put(M['lumen_shard'], 0, 2)
        put(M['petals'], 1, 4)
        if rng.random() < 0.35:
            put(I.SILVERINE.id, 1, 2)
    elif table == LOOT_BOAT:
        put(I.FLUFF.id, 2, 6)
        put(M['cloudstuff'], 1, 4)
        put(rng.choice(common_food), 1, 3)
        put(M['glowstick'], 2, 5)
        put(M['pale_planks'] if rng.random() < 0.5 else M['planks'], 2, 6)
        if rng.random() < 0.4:
            put(I.GLIMMER.id, 1, 3)
        if rng.random() < 0.25:
            put(M['ember_lamp'], 1, 1)
    elif table == 7:
        put(I.GLIMMER.id, 1, 4)
        put(M['shimmer_cloud'], 1, 3)
        put(M['cosmic_star'] if rng.random() < 0.35 else M['crystal'], 0, 2)
        put(rng.choice(common_food), 1, 3)
        if rng.random() < 0.4:
            put(M['sky_crystal_lamp'] if 'sky_crystal_lamp' in M else M['lumen_lamp'], 1, 1)
    else:
        put(I.STICK.id, 1, 4)


def _air_clear(col, P, a, b, y0, y1):
    """True if this local column has no land intersecting [y0, y1]."""
    land = col['land']
    top = col['top']
    bot = col['bottom']
    pa, pb = a + P, b + P
    if not (0 <= pa < land.shape[0] and 0 <= pb < land.shape[1]):
        return False
    if not land[pa, pb]:
        return True
    t, btm = int(top[pa, pb]), int(bot[pa, pb])
    return t < y0 or btm > y1


def place_v5(gen, cq, cr, cells, meta, col, sl):
    """v5 placer: island builds, short bridges, and true sky structures."""
    P = sl[0].start
    REGION = 5
    CHANCE = 65 if getattr(gen, 'version', 5) >= 6 else 50   # 1.4.6: +30% in v6
    rq, rr = cq // REGION, cr // REGION
    h = _h64(rq, rr, gen.h + 0xB144)
    # every region also has a reserved bridge opportunity
    want_bridge = ((h >> 18) % 10) >= 8
    if ((h >> 20) % 100) >= CHANCE and not want_bridge:
        return None
    aq = rq * REGION + (h % REGION)
    ar = rr * REGION + ((h >> 8) % REGION)
    if (aq, ar) != (cq, cr):
        return None
    top = col['top'][sl]
    bot = col['bottom'][sl]
    land = col['land'][sl]
    realm = col['realm'][sl]
    cands = []
    edges = []
    for a in range(3, CHUNK - 3):
        for b in range(3, CHUNK - 3):
            if not land[a, b]:
                continue
            th = int(top[a, b] - bot[a, b] + 1)
            slp = _slope(col, P, a, b)
            edge, edir = _is_edge(col, P, a, b)
            rec = (slp, th, edge, edir, a, b, int(top[a, b]), int(realm[a, b]))
            cands.append(rec)
            if edge:
                edges.append(rec)
    # --- short bridges between close islands ---
    if want_bridge and edges:
        rng = _rng(h, cq, cr, 'bridge')
        for slp, th, edge, edir, a, b, y, rm in edges:
            dq, dr = DIRS[edir]
            # look 4-8 cells outward for another shore
            found = None
            for dist in range(4, 9):
                aa, bb = a + dq * dist, b + dr * dist
                if not (0 <= aa < CHUNK and 0 <= bb < CHUNK):
                    break
                pa, pb = aa + P, bb + P
                if not col['land'][pa, pb]:
                    continue
                y2 = int(col['top'][pa, pb])
                if abs(y2 - y) <= 4:
                    found = (aa, bb, y2, dist)
                    break
                break  # hit land too soon or tall mismatch; stop this ray
            if found and found[3] >= 4:
                pal_rm = rm
                cond = _pick_condition('settlement', h)
                pal = palette(pal_rm, cond)
                st = Stamp(cells, meta, top, bot, land, realm, cq, cr, rng, cond, pal)
                q0 = cq * CHUNK + a + dq
                r0 = cr * CHUNK + b + dr
                q1 = cq * CHUNK + found[0] - dq
                r1 = cr * CHUNK + found[1] - dr
                from . import builds144 as B
                if B.build_bridge(st, q0, r0, q1, r1, y, found[2]):
                    return 'bridge', cond, q0, r0, y
        if ((h >> 20) % 100) >= CHANCE:
            return None

    fam_roll = (h >> 16) % 10
    if fam_roll >= 7:
        family = 'sky'
    elif fam_roll >= 5:
        family = 'ruin'
    else:
        family = 'settlement'
        if cands and not any(c[0] <= 2 and not c[2] for c in cands) and edges:
            family = 'sky' if fam_roll & 1 else 'aerial'

    types = [t for t in TYPES if t['family'] == family and t.get('min_version', 2) <= 5]
    if family == 'ruin':
        thick = [c for c in cands if c[1] >= 14]
        if thick and ((h >> 12) % 3 == 0):
            types = [t for t in types if t['buried']] or types
        else:
            types = [t for t in types if not t['buried']] or types
    if family == 'sky' and not types:
        types = [t for t in TYPES if t.get('sky') and t.get('min_version', 2) <= 5]
    # rare wonders (~1 in 10 structure regions), fall back if none are registered
    if ((h >> 22) % 10) == 0:
        wtypes = [t for t in TYPES if t['family'] == 'wonder' and t.get('min_version', 2) <= 5]
        if wtypes:
            types = wtypes
    if not types:
        # fall back to a classic settlement if the family was empty
        types = [t for t in TYPES if t['family'] == 'settlement' and t.get('min_version', 2) <= 5]
    if not types:
        return None
    # weighted pick by rarity
    typ = types[(h >> 4) % len(types)]

    if typ.get('sky'):
        # pick an open column, preferably near land, with room above the cloud sea
        sky = []
        near_top = [c[6] for c in cands] or [90]
        import statistics
        mid = int(sorted(near_top)[len(near_top) // 2])
        y_sky = max(CLOUD_SEA + 24, min(280, mid + 16 + (h >> 9) % 24))
        pad = typ.get('pad', 4)
        for a in range(pad, CHUNK - pad):
            for b in range(pad, CHUNK - pad):
                if land[a, b]:
                    continue
                clear = True
                for da in range(-pad, pad + 1):
                    for db in range(-pad, pad + 1):
                        if not _air_clear(col, P, a + da, b + db, y_sky - 3, y_sky + 10):
                            clear = False
                            break
                    if not clear:
                        break
                if clear:
                    # prefer sites close to an island edge
                    dist = min((abs(a - c[4]) + abs(b - c[5]) for c in cands), default=20)
                    sky.append((dist, a, b, y_sky, 0))
        if not sky:
            # try a settlement instead
            typ = next((t for t in TYPES if t['name'] == 'hamlet'), typ)
            if typ.get('sky'):
                return None
        else:
            sky.sort()
            dist, a, b, y, rm = sky[h % min(len(sky), 7)]
            rm = int(cands[0][7]) if cands else 0
            cond = _pick_condition('ruin' if typ['family'] == 'ruin' else 'settlement', h)
            pal = palette(rm, cond)
            rng = _rng(h, cq, cr, typ['name'], cond, y)
            st = Stamp(cells, meta, top, bot, land, realm, cq, cr, rng, cond, pal)
            q = cq * CHUNK + a
            r = cr * CHUNK + b
            typ['fn'](st, q, r, y)
            return typ['name'], cond, q, r, y

    # surface / aerial / buried on land
    fit = []
    for slp, th, edge, edir, a, b, y, rm in cands:
        if typ['biomes'] is not None and rm not in typ['biomes']:
            continue
        if th < typ['min_thickness']:
            continue
        if typ['aerial'] and not typ.get('sky') and not edge:
            continue
        if typ['surface'] and not typ['aerial'] and slp > typ['max_slope']:
            continue
        if typ['name'] in ('village', 'hamlet', 'market', 'garden', 'observatory') and (edge or slp > typ['max_slope']):
            continue
        fit.append((slp, th, edge, edir, a, b, y, rm))
    if not fit:
        return None
    if typ['aerial']:
        fit.sort(key=lambda c: (0 if c[2] else 1, c[0], -c[1]))
    elif typ['buried']:
        fit.sort(key=lambda c: (-c[1], c[0]))
    else:
        fit.sort(key=lambda c: (c[0], -c[1]))
    pick = fit[h % min(len(fit), 5)]
    slp, th, edge, edir, a, b, y, rm = pick
    cond = _pick_condition(typ['family'] if typ['family'] != 'sky' else 'settlement', h)
    pal = palette(rm, cond)
    rng = _rng(h, cq, cr, typ['name'], cond, y)
    st = Stamp(cells, meta, top, bot, land, realm, cq, cr, rng, cond, pal)
    q = cq * CHUNK + a
    r = cr * CHUNK + b
    kwargs = {}
    if typ['name'] in ('hut', 'village', 'hamlet'):
        kwargs['door_dir'] = (h >> 6) % 6
    if typ['name'] in ('sky_boat', 'lighthouse', 'waterfall_temple'):
        kwargs['edge_dir'] = edir
    typ['fn'](st, q, r, y, **kwargs)
    return typ['name'], cond, q, r, y


# 1.4.4 builders (registers on import; min_version=5)
from . import builds144 as _builds144  # noqa: F401
from . import builds145 as _builds145  # noqa: F401

"""Title-screen showcase builds: hand-made structures shown behind the main menu.

Each build lives in assets/showcase/<name>.json:
    {name, author, seed_text, site{q, r, top}, camera{...}, flatten{radius, blend, clear_up},
     blocks: [[dq, dr, dy, material, meta], ...]}      (dy = 0 is the ground surface)
The edits are applied to chunks in memory as they load into a storage-less World, so the
showcase never touches any saved sky. Hand-made JSON builds and strong-seed skies (using
the current generator) take turns on the title screen.
"""
import glob
import json
import os
import random
import sys

import numpy as np

from . import materials as MT
from .config import CHUNK, LAYERS
from .hexgrid import hex_distance


def _dir():
    base = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'assets', 'showcase')


def list_builds():
    return sorted(glob.glob(os.path.join(_dir(), '*.json')))


# Strong v2 skies, scored for a nearby spire, land, and a mix of realms.
# site is the spawn we found for that seed so the camera has a place to stand.
SEED_SHOWS = [
    dict(name='Bright Arch', seed_text='bright-arch', site={'q': -72, 'r': 15, 'top': 81},
         camera={'radius': 48.0, 'height': 22.0, 'target_dy': 4.0, 'yaw_offset': -16.0, 'speed': 0.032, 'phase': 0.12}),
    dict(name='Saltwind Bay', seed_text='salt-wind-bay', site={'q': 27, 'r': 33, 'top': 71},
         camera={'radius': 46.0, 'height': 20.0, 'target_dy': 3.0, 'yaw_offset': 18.0, 'speed': 0.03, 'phase': 0.28}),
    dict(name='Windward Isle', seed_text='windward-isle', site={'q': 157, 'r': -36, 'top': 76},
         camera={'radius': 50.0, 'height': 24.0, 'target_dy': 5.0, 'yaw_offset': -28.0, 'speed': 0.034, 'phase': 0.08,
                 'center': [-8, 0]}),
    dict(name='Ember Croft', seed_text='ember-croft', site={'q': 28, 'r': 123, 'top': 41},
         camera={'radius': 53.0, 'height': 26.0, 'target_dy': 4.0, 'yaw_offset': 12.0, 'speed': 0.036, 'phase': 0.36,
                 'arc': [0.524, 5.629]}),
    dict(name='Sky 4096', seed_text='4096', site={'q': -62, 'r': -124, 'top': 56},
         camera={'radius': 52.0, 'height': 29.0, 'target_dy': 4.0, 'yaw_offset': -8.0, 'speed': 0.03, 'phase': 0.18,
                 'arc': [4.189, 8.574]}),
    dict(name='Hardy 1729', seed_text='1729', site={'q': 153, 'r': -160, 'top': 55},
         camera={'radius': 57.0, 'height': 30.0, 'target_dy': 6.0, 'yaw_offset': 24.0, 'speed': 0.028, 'phase': 0.22,
                 'arc': [3.927, 6.48]}),
]


_index = 0


def catalog():
    """JSON builds first, then the strong-seed skies, in a stable order for rotation."""
    items = [('json', path) for path in list_builds()]
    items.extend(('seed', spec) for spec in SEED_SHOWS)
    return items


def item_key(kind, payload):
    if kind == 'json':
        return 'json:' + os.path.splitext(os.path.basename(payload))[0]
    return 'seed:' + str(payload.get('seed_text') or payload.get('name') or '')


def catalog_keys():
    return [item_key(k, p) for k, p in catalog()]


def choose_launch(last_key=''):
    """Pick a random opening showcase, skipping the one used last launch if we can."""
    global _index
    items = catalog()
    if not items:
        return ''
    keys = [item_key(k, p) for k, p in items]
    choices = [i for i, key in enumerate(keys) if key != last_key]
    if not choices:
        choices = list(range(len(items)))
    _index = random.choice(choices)
    return keys[_index]


def pick(advance=True):
    global _index
    items = catalog()
    if not items:
        return None
    kind, payload = items[_index % len(items)]
    if advance:
        _index += 1
    if kind == 'json':
        return Showcase.load(payload)
    data = dict(payload)
    data.setdefault('kind', 'seed')
    data.setdefault('blocks', [])
    if data.get('gen') is None:
        from . import gensettings as GS
        data['gen'] = GS.normalize({})
    return Showcase(data)


_GROUND = np.array([MT.OPAQUE[i] and MT.NAMES[i] not in ('Canopy', 'Heartwood') for i in range(MT.N)])
_FLOWERS = [MT.ID['bloom'], MT.ID['petals'], MT.ID['bloom'], MT.ID['sprout'], MT.ID['berry_bush']]
_TREE = np.array([MT.ID['canopy'], MT.ID['heartwood']])
_TURF, _LOAM, _STONE = MT.ID['turf'], MT.ID['loam'], MT.ID['stone']


class Showcase:
    def __init__(self, data):
        self.data = data
        self.kind = data.get('kind', 'json')
        self.gen = data.get('gen')
        if self.gen is not None:
            from . import gensettings as GS
            self.gen = GS.normalize(self.gen)
        self.name = data.get('name', 'A little build')
        self.seed_text = data['seed_text']
        s = data['site']
        self.q, self.r, self.top = int(s['q']), int(s['r']), int(s['top'])
        self.camera = data.get('camera', {})
        fl = data.get('flatten', {})
        self.flat_r, self.blend, self.clear_up = int(fl.get('radius', 0)), int(fl.get('blend', 0)), int(fl.get('clear_up', 24))
        # group block edits by column so each chunk only looks at its own cells
        self.cols = {}
        for dq, dr, dy, mat, meta in data.get('blocks') or ():
            key = (self.q + dq, self.r + dr)
            self.cols.setdefault(key, []).append((self.top + dy, MT.ID[mat], int(meta)))
        self.reach = self.flat_r + self.blend
        self.tree_r = int(fl.get('clear_trees', self.reach))
        self.flower_r = int(fl.get('flowers', 0))
        self.applied = set()

    def focus(self):
        """World (x, z) the camera orbits: the middle of the build, or the seed's spawn."""
        from .hexgrid import center
        if self.cols:
            pts = [center(q, r) for q, r in self.cols]
            x, z = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        else:
            x, z = center(self.q, self.r)
        off = self.camera.get('center')
        if off and len(off) >= 2:
            x += float(off[0])
            z += float(off[1])
        return x, z

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls(json.load(f))

    def apply_chunk(self, c):
        """World.on_chunk_loaded hook: shape terrain and place the build inside chunk c (in place)."""
        q0, r0 = c.cq * CHUNK, c.cr * CHUNK
        if hex_distance(q0 + CHUNK // 2, r0 + CHUNK // 2, self.q, self.r) > max(self.reach, self.tree_r) + CHUNK + 40:
            return
        cells, meta = c.cells, c.meta
        T = self.top
        for lq in range(CHUNK):
            for lr in range(CHUNK):
                q, r = q0 + lq, r0 + lr
                d = hex_distance(q, r, self.q, self.r)
                if d <= self.tree_r:                              # open the view: no trees around the build
                    col = cells[lq, :, lr]
                    tree = np.isin(col, _TREE)
                    tree[:max(0, T - 6)] = False
                    col[tree] = 0
                if d <= self.reach:
                    col = cells[lq, :, lr]
                    g = np.nonzero(_GROUND[col])[0]
                    if len(g):                                    # only shape real land (cliffs stay cliffs)
                        nat = int(g[-1])
                        if d <= self.flat_r:
                            tgt = T
                        else:
                            tgt = int(round(T + (nat - T) * (d - self.flat_r) / (self.blend + 1)))
                        if abs(nat - T) <= 12 or d <= self.flat_r:
                            hi = min(LAYERS, max(nat, tgt) + self.clear_up)
                            col[tgt + 1:hi] = 0                    # clear trees / bumps above
                            meta[lq, tgt + 1:hi, lr] = 0
                            if nat < tgt:
                                col[nat + 1:tgt] = _LOAM
                            col[max(0, tgt - 3):tgt] = np.where(_GROUND[col[max(0, tgt - 3):tgt]], col[max(0, tgt - 3):tgt], _LOAM)
                            col[tgt] = _TURF
                if d <= self.flower_r and (q, r) not in self.cols:     # meadow flowers around the build
                    h = (q * 73856093 ^ r * 19349663) & 0xFFFF
                    if h % 100 < 11:
                        col = cells[lq, :, lr]
                        g = np.nonzero(_GROUND[col])[0]
                        if len(g) and col[g[-1]] == _TURF and g[-1] + 1 < LAYERS and col[g[-1] + 1] == 0:
                            col[g[-1] + 1] = _FLOWERS[(h >> 8) % len(_FLOWERS)]
                for y, m, mt in self.cols.get((q, r), ()):
                    if 0 <= y < LAYERS:
                        cells[lq, y, lr] = m
                        meta[lq, y, lr] = mt
        c.modified = False                                        # never saved (no storage anyway)
        self.applied.add((c.cq, c.cr))


# ------------------------------------------------------------------ camera path
def orbit_span(sc):
    """Inclusive start/end orbit angles in radians. A missing arc is a full circle."""
    import math
    arc = (sc.camera or {}).get('arc')
    if arc and len(arc) >= 2:
        return float(arc[0]), float(arc[1])
    return 0.0, 2.0 * math.pi


def orbit_pose(sc, ang):
    """Camera world position and look-at point for an orbit angle (radians)."""
    import math
    from .config import LAYER
    fx, fz = sc.focus()
    cam = sc.camera or {}
    rad = float(cam.get('radius', 30.0))
    y = (sc.top + float(cam.get('height', 13))) * LAYER
    ty = (sc.top + float(cam.get('target_dy', 5))) * LAYER
    return (fx + math.cos(ang) * rad, y, fz + math.sin(ang) * rad), (fx, ty, fz)


def iter_orbit(sc, n=96):
    """Sample poses along the showcase orbit (full circle, or the clear arc)."""
    import math
    a0, a1 = orbit_span(sc)
    span = a1 - a0
    full = abs(span - 2.0 * math.pi) < 1e-4 or abs(span) < 1e-6
    if full:
        angs = [a0 + 2.0 * math.pi * i / n for i in range(n)]
    else:
        n = max(n, 2)
        angs = [a0 + span * i / (n - 1) for i in range(n)]
    return [(ang, *orbit_pose(sc, ang)) for ang in angs]


def stamped_world(sc, chunk_radius=6):
    """Headless world with the showcase's chunks generated and the build stamped in."""
    import math
    from .config import CHUNK
    from .generator import Generator
    from .hexgrid import cell_at, chunk_of
    from .noise import seed_from_text
    from .world import Chunk, World

    gen = Generator(seed_from_text(sc.seed_text), sc.gen)
    world = World(seed_from_text(sc.seed_text), None, None, None, 2, far_distance=2, gen_settings=sc.gen)
    keys = set()
    cq0, cr0 = chunk_of(sc.q, sc.r)
    for i in range(-chunk_radius, chunk_radius + 1):
        for k in range(-chunk_radius, chunk_radius + 1):
            keys.add((cq0 + i, cr0 + k))
    fx, fz = sc.focus()
    rad = float((sc.camera or {}).get('radius', 40.0)) + 16.0
    for i in range(12):
        ang = (2.0 * math.pi) * i / 12.0
        q, r = cell_at(fx + math.cos(ang) * rad, fz + math.sin(ang) * rad)
        cq, cr = chunk_of(q, r)
        for di in range(-1, 2):
            for dk in range(-1, 2):
                keys.add((cq + di, cr + dk))
    for cq, cr in keys:
        cells, meta, realm = gen.generate(cq, cr)
        c = Chunk(cq, cr, cells, meta, realm)
        sc.apply_chunk(c)
        world.chunks[(cq, cr)] = c
    return world


def _cam_in_solid(world, x, y, z, rad=0.4):
    """True if the camera (or a small ball around it) sits inside a solid cell, including leaves."""
    import math
    from .entities import solid_at
    if solid_at(world, x, y, z):
        return True
    for i in range(6):
        a = 2.0 * math.pi * i / 6.0
        if solid_at(world, x + math.cos(a) * rad, y, z + math.sin(a) * rad):
            return True
    return solid_at(world, x, y - 0.25, z) or solid_at(world, x, y + 0.25, z)


def _build_cells(sc):
    cells = set()
    for (q, r), edits in sc.cols.items():
        for y, _m, _mt in edits:
            cells.add((q, r, int(y)))
    return cells


def _ray_hits_terrain(world, p0, p1, build, steps=20, ignore_tail=0.28):
    """True if a solid that isn't part of the build sits on the look ray, before the last stretch."""
    from .entities import solid_at
    from .hexgrid import cell_at
    from .config import LAYER
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    limit = int(steps * (1.0 - ignore_tail))
    for i in range(1, limit + 1):
        t = i / steps
        x, y, z = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
        if not solid_at(world, x, y, z):
            continue
        q, r = cell_at(x, z)
        ly = int(y / LAYER)
        if (q, r, ly) in build or (q, r, ly - 1) in build or (q, r, ly + 1) in build:
            continue
        if (q, r) in sc_cols_only(build):
            continue
        return True
    return False


def sc_cols_only(build):
    return {(q, r) for q, r, _y in build}


def _near_clip(world, p0, p1, dist=8.0, steps=16):
    """True if a solid sits on the look ray close in front of the camera (a face in a cliff)."""
    import math
    from .entities import solid_at
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2) or 1.0
    # walk the first `dist` world units of the ray, skipping the first 0.4 so we
    # don't flag the camera's own clearance ball twice
    span = min(dist / length, 0.55)
    for i in range(1, steps + 1):
        t = span * i / steps
        if t * length < 0.5:
            continue
        x, y, z = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
        if solid_at(world, x, y, z):
            return True
    return False


def path_report(sc, world=None, n=96):
    """Sample the orbit for solid clips (including canopy) and long terrain occlusion."""
    if world is None:
        world = stamped_world(sc)
    build = _build_cells(sc)
    clips, hides = [], []
    samples = iter_orbit(sc, n)
    for ang, cam, target in samples:
        if _cam_in_solid(world, *cam) or _near_clip(world, cam, target):
            clips.append(ang)
        if _ray_hits_terrain(world, cam, target, build):
            hides.append(ang)
    return {
        'n': len(samples),
        'clips': clips,
        'hides': hides,
        'ok': (len(clips) == 0) and (len(hides) <= max(2, 0.22 * len(samples))),
    }

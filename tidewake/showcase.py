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
    dict(name='Bright Arch', seed_text='bright-arch', site={'q': -63, 'r': 22, 'top': 48},
         camera={'radius': 48.0, 'height': 22.0, 'target_dy': 4.0, 'yaw_offset': -16.0, 'speed': 0.032, 'phase': 0.12}),
    dict(name='Saltwind Bay', seed_text='salt-wind-bay', site={'q': 33, 'r': 43, 'top': 56},
         camera={'radius': 46.0, 'height': 20.0, 'target_dy': 3.0, 'yaw_offset': 18.0, 'speed': 0.03, 'phase': 0.28}),
    dict(name='Windward Isle', seed_text='windward-isle', site={'q': 141, 'r': -28, 'top': 48},
         camera={'radius': 50.0, 'height': 24.0, 'target_dy': 5.0, 'yaw_offset': -28.0, 'speed': 0.034, 'phase': 0.08}),
    dict(name='Ember Croft', seed_text='ember-croft', site={'q': 26, 'r': -24, 'top': 58},
         camera={'radius': 44.0, 'height': 18.0, 'target_dy': 3.0, 'yaw_offset': 12.0, 'speed': 0.036, 'phase': 0.36}),
    dict(name='Sky 4096', seed_text='4096', site={'q': -46, 'r': -135, 'top': 60},
         camera={'radius': 42.0, 'height': 21.0, 'target_dy': 4.0, 'yaw_offset': -8.0, 'speed': 0.03, 'phase': 0.18}),
    dict(name='Hardy 1729', seed_text='1729', site={'q': 21, 'r': 76, 'top': 73},
         camera={'radius': 52.0, 'height': 26.0, 'target_dy': 6.0, 'yaw_offset': 24.0, 'speed': 0.028, 'phase': 0.22}),
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
            return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        return center(self.q, self.r)

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

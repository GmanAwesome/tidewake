"""Title-screen showcase builds: hand-made structures shown behind the main menu.

Each build lives in assets/showcase/<name>.json:
    {name, author, seed_text, site{q, r, top}, camera{...}, flatten{radius, blend, clear_up},
     blocks: [[dq, dr, dy, material, meta], ...]}      (dy = 0 is the ground surface)
The edits are applied to chunks in memory as they load into a storage-less World, so the
showcase never touches any saved sky. Add more JSON files and one is picked at random.
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


def pick(rng=random):
    files = list_builds()
    return Showcase.load(rng.choice(files)) if files else None


_GROUND = np.array([MT.OPAQUE[i] and MT.NAMES[i] not in ('Canopy', 'Heartwood') for i in range(MT.N)])
_FLOWERS = [MT.ID['bloom'], MT.ID['petals'], MT.ID['bloom'], MT.ID['sprout'], MT.ID['berry_bush']]
_TREE = np.array([MT.ID['canopy'], MT.ID['heartwood']])
_TURF, _LOAM, _STONE = MT.ID['turf'], MT.ID['loam'], MT.ID['stone']


class Showcase:
    def __init__(self, data):
        self.data = data
        self.name = data.get('name', 'A little build')
        self.seed_text = data['seed_text']
        s = data['site']
        self.q, self.r, self.top = int(s['q']), int(s['r']), int(s['top'])
        self.camera = data.get('camera', {})
        fl = data.get('flatten', {})
        self.flat_r, self.blend, self.clear_up = int(fl.get('radius', 0)), int(fl.get('blend', 0)), int(fl.get('clear_up', 24))
        # group block edits by column so each chunk only looks at its own cells
        self.cols = {}
        for dq, dr, dy, mat, meta in data['blocks']:
            key = (self.q + dq, self.r + dr)
            self.cols.setdefault(key, []).append((self.top + dy, MT.ID[mat], int(meta)))
        self.reach = self.flat_r + self.blend
        self.tree_r = int(fl.get('clear_trees', self.reach))
        self.flower_r = int(fl.get('flowers', 0))
        self.applied = set()

    def focus(self):
        """World (x, z) the camera orbits: the middle of the build."""
        from .hexgrid import center
        pts = [center(q, r) for q, r in self.cols]
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

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

"""The living simulation: tuned cells keep changing on their own.

Water flows and falls, vines creep down cliffs, crystals grow in the dusk tide, blooms
spread across turf in the light tide, mossrock greens nearby stone, sprouts become trees.
Only cells that might change are tracked ("active"), a few dozen per step.
"""
import random

from .config import CLOUD_SEA, LAYERS
from .hexgrid import DIRS
from . import materials as MT

M = MT.ID
SOLID = MT.SOLID
LIVING = {M['water'], M['vine'], M['crystal'], M['bloom'], M['mossrock'], M['sprout']}
STONY = {M['stone'], M['basalt'], M['rosestone']}
GROUND = {M['turf'], M['loam'], M['mossrock'], M['sand'], M['snow'], M['clay']}


class Simulation:
    def __init__(self, world, rng_seed=0):
        self.world = world
        self.active = {}
        self.rng = random.Random(rng_seed)
        self.acc = 0.0
        self.on_tree = None

    def wake(self, q, r, y, delay=0.0):
        self.active[(q, r, y)] = delay

    def wake_around(self, q, r, y):
        w = self.world
        for dq, dr in [(0, 0)] + DIRS:
            for dy in (-1, 0, 1):
                m = w.get(q + dq, r + dr, y + dy)
                if m in LIVING:
                    self.wake(q + dq, r + dr, y + dy, 0.2)

    def step(self, dt, dusk, budget=48):
        if not self.active:
            return
        items = list(self.active.items())
        self.rng.shuffle(items)
        n = 0
        light = 1.0 - dusk
        for key, t in items:
            t -= dt
            if t > 0:
                self.active[key] = t
                continue
            if n >= budget:
                break
            n += 1
            del self.active[key]
            again = self._tick(*key, light, dusk)
            if again is not None:
                self.active[key] = again

    def _set(self, q, r, y, mat, meta, delay):
        if self.world.set(q, r, y, mat, meta):
            if mat in LIVING:
                self.active[(q, r, y)] = delay
            return True
        return False

    def _tick(self, q, r, y, light, dusk):
        w, rng = self.world, self.rng
        m = w.get(q, r, y)
        if m not in LIVING:
            return None
        meta = w.get_meta(q, r, y)
        if m == M['water']:
            if y <= CLOUD_SEA:
                return None
            below = w.get(q, r, y - 1)
            if below == 0 or below == M['petals']:
                self._set(q, r, y - 1, M['water'], min(meta, 5), 0.12)
                return None
            if below < 0:
                return 1.0
            if meta <= 1 or below == M['water'] and w.get_meta(q, r, y - 1) >= meta:
                return None
            spread = False
            for dq, dr in DIRS:
                n = w.get(q + dq, r + dr, y)
                if n == 0 or n == M['petals']:
                    self._set(q + dq, r + dr, y, M['water'], meta - 1, 0.35)
                    spread = True
                elif n < 0:
                    return 1.0
            return None
        if m == M['vine']:
            if meta <= 0:
                return None
            if rng.random() > 0.25 + 0.6 * light:
                return 1.5
            if w.get(q, r, y - 1) == 0 and y - 1 > CLOUD_SEA:
                self._set(q, r, y - 1, M['vine'], meta - 1, 2.0)
                w.set_meta(q, r, y, 0)
                return None
            opts = []
            for dq, dr in DIRS:
                if w.get(q + dq, r + dr, y) == 0:
                    # must cling to something solid
                    if any(SOLID[max(0, w.get(q + dq + a, r + dr + b, y))] for a, b in DIRS) or \
                            SOLID[max(0, w.get(q + dq, r + dr, y + 1))] or SOLID[max(0, w.get(q + dq, r + dr, y - 1))]:
                        opts.append((q + dq, r + dr))
            if opts:
                a, b = rng.choice(opts)
                self._set(a, b, y, M['vine'], meta - 2, 2.5)
                w.set_meta(q, r, y, max(0, meta - 2))
                return 3.0 if meta - 2 > 0 else None
            return None
        if m == M['crystal']:
            if meta >= 3:
                return None
            if dusk < 0.45:
                return 4.0                      # waits for the dusk tide
            if rng.random() < 0.5:
                return 2.0
            if w.get(q, r, y + 1) == 0:
                self._set(q, r, y + 1, M['crystal'], meta + 1, 3.0)
                w.set_meta(q, r, y, 3)
            return None
        if m == M['bloom']:
            if meta <= 0:
                return None
            if light < 0.4:
                return 4.0
            if rng.random() < 0.5:
                return 2.0
            dq, dr = rng.choice(DIRS)
            for dy in (0, 1, -1):
                t = w.get(q + dq, r + dr, y + dy)
                g = w.get(q + dq, r + dr, y + dy - 1)
                if t == 0 and g in (M['turf'], M['mossrock']):
                    self._set(q + dq, r + dr, y + dy, M['bloom'], meta - 1, 3.0)
                    break
            w.set_meta(q, r, y, meta - 1)
            return 2.5 if meta - 1 > 0 else None
        if m == M['mossrock']:
            if meta <= 0:
                return None
            if rng.random() < 0.4:
                return 3.0
            dq, dr = rng.choice(DIRS + [(0, 0)])
            dy = rng.choice((-1, 0, 1))
            t = w.get(q + dq, r + dr, y + dy)
            if t in STONY:
                self._set(q + dq, r + dr, y + dy, M['mossrock'], meta - 1, 4.0)
            w.set_meta(q, r, y, meta - 1)
            return 3.0 if meta - 1 > 0 else None
        if m == M['sprout']:
            g = w.get(q, r, y - 1)
            if g not in GROUND:
                return None
            if light < 0.35:
                return 3.0
            meta += 1
            w.set_meta(q, r, y, meta)
            if meta >= 6 and self.on_tree:
                self.on_tree(q, r, y - 1)
                return None
            return 2.0
        return None


def grow_tree(world, q, r, top, realm, rng):
    """A young tree grown from a sprout (written straight into the world)."""
    wood, leaf = M['heartwood'], M['canopy']
    hgt = rng.randint(4, 6)

    def put(a, b, y, mat):
        if world.get(a, b, y) in (0, M['petals'], M['sprout']):
            world.set(a, b, y, mat)

    def disk(y, rad, mat):
        for dq in range(-rad, rad + 1):
            for dr in range(max(-rad, -dq - rad), min(rad, -dq + rad) + 1):
                put(q + dq, r + dr, y, mat)

    world.set(q, r, top + 1, wood)
    for y in range(top + 2, top + hgt + 1):
        put(q, r, y, wood)
    if realm == 3:
        for i, y in enumerate(range(top + 3, top + hgt + 2)):
            disk(y, max(0, 2 - i // 2), leaf)
    else:
        disk(top + hgt - 1, 2, leaf)
        disk(top + hgt, 2, leaf)
        disk(top + hgt + 1, 1, leaf)

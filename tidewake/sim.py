"""The living simulation: tuned cells keep changing on their own.

Water flows and falls, vines creep down cliffs, crystals grow in the dusk tide, blooms
spread across turf in the light tide, mossrock greens nearby stone, sprouts become trees.
Only cells that might change are tracked ("active"), a few dozen per step.
"""
import random

from .config import CLOUD_SEA, LAYERS
from .hexgrid import DIRS, hex_distance
from . import materials as MT

M = MT.ID
SOLID = MT.SOLID
LIVING = {M['water'], M['vine'], M['crystal'], M['bloom'], M['mossrock'], M['sprout'],
          M['skywheat'], M['sweetroot_crop'], M['berry_crop'], M['farmland']}
STONY = {M['stone'], M['basalt'], M['rosestone']}
GROUND = {M['turf'], M['loam'], M['mossrock'], M['sand'], M['snow'], M['clay'], M['heather'], M['packed_earth']}


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
                if m in LIVING or m == M['canopy']:
                    self.wake(q + dq, r + dr, y + dy, 0.2)

    def wake_leaves(self, q, r, y, delay=0.4):
        """Start decay checks on nearby canopy after a log (or leaf) is removed."""
        for dq in range(-5, 6):
            for dr in range(-5, 6):
                if hex_distance(0, 0, dq, dr) > 5:
                    continue
                for dy in range(-5, 6):
                    if self.world.get(q + dq, r + dr, y + dy) == M['canopy']:
                        self.wake(q + dq, r + dr, y + dy, delay)

    def _leaf_supported(self, q, r, y, reach=4):
        """True if this canopy cell is connected to heartwood through other leaves."""
        w = self.world
        seen = {(q, r, y)}
        stack = [(q, r, y, 0)]
        while stack:
            cq, cr, cy, d = stack.pop()
            if w.get(cq, cr, cy) in MT.WOODS:
                return True
            if d >= reach:
                continue
            for dq, dr in DIRS + [(0, 0)]:
                for dy in (-1, 0, 1):
                    if dq == 0 and dr == 0 and dy == 0:
                        continue
                    n = (cq + dq, cr + dr, cy + dy)
                    if n in seen:
                        continue
                    m = w.get(*n)
                    if m == M['canopy'] or m in MT.WOODS:
                        seen.add(n)
                        stack.append((*n, d + 1))
        return False

    def _tick_leaf(self, q, r, y):
        if self.world.get(q, r, y) != M['canopy']:
            return None
        if self._leaf_supported(q, r, y):
            return None
        # unsupported: vanish and nudge neighbours so the canopy withers outward
        self.world.set(q, r, y, 0, 0)
        self.wake_leaves(q, r, y, 0.25)
        return None

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
            if self.world.get(*key) == M['canopy']:
                again = self._tick_leaf(*key)
            else:
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
        from . import farming as FARM
        if m == M['farmland']:
            # unused dry beds slowly rest back to loam
            if w.get(q, r, y + 1) in FARM.crops():
                return 8.0
            if FARM.hydrated(w, q, r, y):
                return 12.0
            meta += 1
            if meta >= 8:
                self._set(q, r, y, M['loam'], 0, None)
                return None
            w.set_meta(q, r, y, meta)
            return 10.0
        if m in FARM.crops():
            if w.get(q, r, y - 1) != M['farmland']:
                return None
            if meta >= FARM.STAGES - 1:
                return None
            wet = FARM.hydrated(w, q, r, y - 1)
            if light < 0.3:
                return 6.0
            if rng.random() < (0.25 if wet else 0.45):
                return 4.0 if wet else 8.0
            self._set(q, r, y, m, meta + 1, 6.0 if wet else 12.0)
            return 6.0 if wet else 12.0
        return None


def grow_tree(world, q, r, top, realm, rng):
    """A young tree grown from a sprout (written straight into the world)."""
    wood, leaf = M['heartwood'], M['canopy']
    if realm == 9:          # Cedar Highlands
        wood = M['cedar_heartwood']
        hgt = rng.randint(7, 9)
    elif realm in (8, 12, 14):  # Saltwind, Chalk, Cloudstep
        wood = M['pale_heartwood']
        hgt = rng.randint(3, 5)
    elif realm in (1, 15):      # Amberwood, Verdigris
        wood = M['dark_heartwood']
        hgt = rng.randint(5, 7)
    else:
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
    if realm in (3, 9, 14):  # frost, cedar, cloudstep firs
        for i, y in enumerate(range(top + 3, top + hgt + 2)):
            disk(y, max(0, 2 - i // 2), leaf)
    else:
        disk(top + hgt - 1, 2, leaf)
        disk(top + hgt, 2, leaf)
        disk(top + hgt + 1, 1, leaf)

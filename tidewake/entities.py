"""Creatures and dropped items.

Woolhops, pebblebeaks and mossbacks wander the islands and drop useful things.
Skywhales drift between the islands, and fairies glow near flowers as dusk comes on.
Sky jellies and cloud rays share the open air; moss turtles, crystal beetles and
skittish islekits keep to the turf. Gloomlings come out in the dusk tide (they can
be switched off in Settings), and fade away when the light returns.
"""
import math
import random

import numpy as np

from .config import LAYER, CLOUD_SEA
from .materials import is_blocking, overlaps_solid, support_top
from .hexgrid import cell_at, center
from . import materials as MT
from . import items as I
from . import models as MD

SOLID = MT.SOLID
KINDS = {
    #             hp   speed radius height  hostile  drops
    'woolhop':   (8,   1.6,  0.45, 1.05,  False, [(I.FLUFF.id, 1, 2), (I.HOPMEAT.id, 1, 2)]),
    'pebblebeak': (4,  1.9,  0.25, 0.80,  False, [(I.PLUME.id, 0, 2), (I.EGG.id, 0, 1)]),
    'mossback':  (14,  0.8,  0.55, 0.56,  False, [(MT.ID['mossrock'], 1, 2), (MT.ID['vine'], 0, 2)]),
    'gloomling': (10,  2.9,  0.40, 0.84,  True,  [(I.GLOOM.id, 1, 2)]),
    'brute':     (26,  2.2,  0.65, 1.40,  True,  [(I.GLOOM.id, 2, 4), (I.EMBERITE.id, 0, 2)]),
    'skywhale':  (40,  0.55, 2.20, 1.60,  False, []),
    'fairy':     (2,   1.35, 0.16, 0.28,  False, []),
    'skyjelly':  (6,   0.65, 0.48, 0.72,  False, [(I.FLUFF.id, 0, 2)]),
    'cloudray':  (10,  0.95, 0.85, 0.36,  False, [(I.PLUME.id, 0, 2)]),
    'mossturtle':(16,  0.55, 0.62, 0.64,  False, [(MT.ID['mossrock'], 1, 2), (MT.ID['sprout'], 0, 2)]),
    'crystalbeetle': (5, 2.4, 0.22, 0.28, False, [(MT.ID['crystal'], 0, 1)]),
    'islekit':   (4,   2.2,  0.22, 0.42,  False, [(I.FLUFF.id, 0, 1)]),
}
SCALE = {'brute': 1.7, 'skywhale': 3.4, 'mossturtle': 1.25, 'skyjelly': 1.35, 'cloudray': 2.1}
FLYING = frozenset({'skywhale', 'fairy', 'skyjelly', 'cloudray'})
SHY = {'islekit': 8.0, 'crystalbeetle': 4.5, 'mossturtle': 5.5}
FLOWER_BLOCKS = {MT.ID['bloom'], MT.ID['petals'], MT.ID['berry_bush'], MT.ID['sprout'],
                 MT.ID['skywheat'], MT.ID['berry_crop']}


def solid_at(world, x, y, z):
    q, r = cell_at(x, z)
    return overlaps_solid(world, q, r, y, y + 0.02, LAYER)


class Mob:
    def __init__(self, kind, x, y, z):
        self.kind = kind
        hp, self.speed, self.radius, self.height, self.hostile, self.drops = KINDS[kind]
        self.hp = self.max_hp = hp
        self.x, self.y, self.z = x, y, z
        self.vx = self.vy = self.vz = 0.0
        self.yaw = random.uniform(0, 360)
        self.t = random.uniform(0, 10)
        self.think = 0.0
        self.walking = False
        self.on_ground = False
        self.hurt = 0.0
        self.attack_cd = 0.0
        self.fade = 1.0           # gloomlings fade out at lighttide
        self.dead = False
        self.panic = 0.0
        self.seed = random.random()
        self.lay = random.uniform(60, 200)
        self.scale = SCALE.get(kind, 1.0)
        self.home = (x, y, z)
        self._cruise_y = y
        self.tether = None        # 1.4.4: lesson-island creatures stay near their spot
        self.tut_id = None

    def update(self, dt, world, player, dusk, peaceful):
        self.t += dt
        self.hurt = max(0.0, self.hurt - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.think -= dt
        self.panic = max(0.0, self.panic - dt)
        if self.kind in FLYING:
            self._update_fly(dt, world, player, dusk)
            return
        dx, dz = player.x - self.x, player.z - self.z
        dist = math.hypot(dx, dz)
        want = 0.0
        if self.hostile:
            if dusk < 0.25 or peaceful:
                self.fade -= dt * 0.6
                if self.fade <= 0:
                    self.dead = True
            if dist < 18 and not peaceful and not player.dev_ghost:
                self.yaw = math.degrees(math.atan2(dx, -dz))
                want = self.speed if dist > 0.9 else 0.0
            elif self.think <= 0:
                self.think = random.uniform(2, 5)
                self.yaw = random.uniform(0, 360)
                self.walking = random.random() < 0.5
            if dist >= 18 and self.walking:
                want = self.speed * 0.4
        else:
            shy = SHY.get(self.kind)
            if shy and dist < shy and not player.dev_ghost:
                self.yaw = math.degrees(math.atan2(-dx, dz)) + math.sin(self.t * 4) * 18
                want = self.speed * (1.8 if self.kind == 'islekit' else 1.35)
            elif self.panic > 0:
                self.yaw = math.degrees(math.atan2(-dx, dz)) + math.sin(self.t * 3) * 25
                want = self.speed * 2.0
            else:
                if self.think <= 0:
                    self.think = random.uniform(1.5, 5)
                    self.walking = random.random() < 0.55
                    self.yaw = (self.yaw + random.uniform(-120, 120)) % 360
                    if self.tether and math.hypot(self.x - self.home[0], self.z - self.home[2]) > self.tether:
                        self.yaw = math.degrees(math.atan2(self.home[0] - self.x, -(self.home[2] - self.z)))
                        self.walking = True
                want = self.speed if self.walking else 0.0
        a = math.radians(self.yaw)
        fx, fz = math.sin(a), -math.cos(a)
        k = min(1.0, 8 * dt)
        self.vx += (fx * want - self.vx) * k
        self.vz += (fz * want - self.vz) * k
        self.walking = want > 0.05
        # don't wander off island edges (unless hostile and chasing)
        if self.walking and self.on_ground:
            ax, az = self.x + fx * (self.radius + 0.6), self.z + fz * (self.radius + 0.6)
            if not any(solid_at(world, ax, self.y - LAYER * k2 - 0.01, az) for k2 in (1, 2, 3)):
                self.vx = self.vz = 0
                self.yaw = (self.yaw + 150) % 360
                self.think = 1.0
        if not self.on_ground:
            self.vy -= 24.0 * dt
            self.vy = max(self.vy, -30)
        else:
            self.vy = min(self.vy, 0.0)
        self._move(world, dt)
        if self.y < CLOUD_SEA * LAYER - 4:
            self.dead = True


    def _update_fly(self, dt, world, player, dusk):
        """Skywhales drift slowly through the open air; fairies hover near flowers."""
        a = math.radians(self.yaw)
        fx, fz = math.sin(a), -math.cos(a)
        if self.kind == 'skywhale':
            if self.think <= 0:
                self.think = random.uniform(8, 20)
                self.yaw = (self.yaw + random.uniform(-50, 50)) % 360
                self._cruise_y = max(CLOUD_SEA * LAYER + 8, self._cruise_y + random.uniform(-2.5, 2.5))
            want = self.speed * (1.35 if self.hurt > 0 else 1.0)
            k = min(1.0, 1.1 * dt)
            self.vx += (fx * want - self.vx) * k
            self.vz += (fz * want - self.vz) * k
            tgt = self._cruise_y + math.sin(self.t * 0.18 + self.seed * 6) * 1.4
            self.vy += ((tgt - self.y) * 0.25 - self.vy) * min(1.0, 1.8 * dt)
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.walking = True
            self.on_ground = False
            if self.y < CLOUD_SEA * LAYER + 4:
                self.vy = abs(self.vy) + 0.6
                self.y = CLOUD_SEA * LAYER + 4
            if solid_at(world, self.x, self.y, self.z) or solid_at(world, self.x + fx * 3, self.y, self.z + fz * 3):
                self.vy = max(self.vy, 2.4)
                self.yaw = (self.yaw + 25) % 360
        elif self.kind == 'cloudray':
            if self.think <= 0:
                self.think = random.uniform(4, 10)
                self.yaw = (self.yaw + random.uniform(-80, 80)) % 360
                self._cruise_y = max(CLOUD_SEA * LAYER + 6, self._cruise_y + random.uniform(-3.0, 3.0))
                if self.tether:
                    hx, hy, hz = self.home
                    self._cruise_y = min(max(self._cruise_y, hy - 4), hy + 4)
                    if math.hypot(self.x - hx, self.z - hz) > self.tether:
                        self.yaw = math.degrees(math.atan2(hx - self.x, -(hz - self.z)))
            want = self.speed * (1.5 if self.hurt > 0 else 1.0)
            k = min(1.0, 2.2 * dt)
            self.vx += (fx * want - self.vx) * k
            self.vz += (fz * want - self.vz) * k
            tgt = self._cruise_y + math.sin(self.t * 0.55 + self.seed * 5) * 1.1
            self.vy += ((tgt - self.y) * 0.45 - self.vy) * min(1.0, 2.4 * dt)
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.walking = True
            self.on_ground = False
            if self.y < CLOUD_SEA * LAYER + 3:
                self.vy = abs(self.vy) + 0.5
                self.y = CLOUD_SEA * LAYER + 3
            if solid_at(world, self.x, self.y, self.z) or solid_at(world, self.x + fx * 2, self.y, self.z + fz * 2):
                self.vy = max(self.vy, 1.8)
                self.yaw = (self.yaw + 40) % 360
        elif self.kind == 'skyjelly':
            hx, hy, hz = self.home
            if self.think <= 0:
                self.think = random.uniform(2.0, 5.0)
                self.yaw = (self.yaw + random.uniform(-100, 100)) % 360
                if math.hypot(self.x - hx, self.z - hz) > 14:
                    self.yaw = math.degrees(math.atan2(hx - self.x, -(hz - self.z)))
            want = self.speed * (1.6 if self.hurt > 0 else 1.0)
            k = min(1.0, 2.0 * dt)
            self.vx += (fx * want - self.vx) * k
            self.vz += (fz * want - self.vz) * k
            bob = hy + math.sin(self.t * 0.7 + self.seed * 6) * 1.6
            self.vy += ((bob - self.y) * 0.8 - self.vy) * min(1.0, 2.0 * dt)
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.walking = True
            self.on_ground = False
            if self.y < CLOUD_SEA * LAYER + 2:
                self.vy = abs(self.vy) + 0.4
                self.y = CLOUD_SEA * LAYER + 2
        else:
            hx, hy, hz = self.home
            dart = 1.35 + (0.7 if dusk > 0.35 else 0.0)
            if self.think <= 0:
                self.think = random.uniform(0.7, 2.4)
                self.yaw = (self.yaw + random.uniform(-140, 140)) % 360
                if math.hypot(self.x - hx, self.z - hz) > 4.5:
                    self.yaw = math.degrees(math.atan2(hx - self.x, -(hz - self.z)))
            want = self.speed * dart * (0.55 + 0.45 * (self.think < 0.35))
            if self.hurt > 0:
                want = self.speed * 2.2
            k = min(1.0, 6 * dt)
            self.vx += (fx * want - self.vx) * k
            self.vz += (fz * want - self.vz) * k
            bob = hy + 0.55 + math.sin(self.t * 2.6 + self.seed * 8) * 0.28
            if dusk > 0.35:
                bob += 0.15
            self.vy += ((bob - self.y) * 2.4 - self.vy) * min(1.0, 6 * dt)
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.walking = True
            self.on_ground = False
        if self.y < CLOUD_SEA * LAYER - 2:
            self.dead = True

    def _blocked(self, world, x, y, z):
        h = self.height * self.scale
        for oy in (0.05, h * 0.5, h - 0.05):
            for ox, oz in ((0, 0), (self.radius, 0), (-self.radius, 0), (0, self.radius), (0, -self.radius)):
                if solid_at(world, x + ox * 0.8, y + oy, z + oz * 0.8):
                    return True
        return False

    def _move(self, world, dt):
        nx, nz = self.x + self.vx * dt, self.z + self.vz * dt
        if not self._blocked(world, nx, self.y, nz):
            self.x, self.z = nx, nz
        elif self.on_ground:
            q, r = cell_at(nx, nz)
            # step up to the actual floor top of the neighbouring cell, not the next layer line
            ahead_top = support_top(world, q, r, self.y + LAYER * 1.6, LAYER)
            if ahead_top is not None and ahead_top > self.y + 0.02:
                up = ahead_top + 0.001
                if up - self.y <= LAYER * 1.05 and not self._blocked(world, nx, up, nz) and not self._blocked(world, self.x, up, self.z):
                    self.y = up
                    self.x, self.z = nx, nz
                elif not self._blocked(world, nx, up + 0.05, nz) and up - self.y <= LAYER * 2.1:
                    self.vy = 7.5
                else:
                    self.think = 0
            else:
                self.think = 0
        ny = self.y + self.vy * dt
        q, r = cell_at(self.x, self.z)
        # probe just under the feet so a body already sitting on a floor stays there
        under = support_top(world, q, r, self.y + 0.08, LAYER)
        if self.vy <= 0 and self._blocked(world, self.x, ny, self.z):
            # snap to the real top of the floor, not a layer-grid line (that oscillated)
            top = support_top(world, q, r, max(self.y, ny) + 0.2, LAYER)
            if top is None:
                top = math.floor(ny / LAYER + 1) * LAYER
            self.y = top + 0.001
            if self._blocked(world, self.x, self.y, self.z):
                top2 = support_top(world, q, r, self.y + LAYER * 1.5, LAYER)
                if top2 is not None:
                    self.y = top2 + 0.001
            self.vy = 0
            self.on_ground = True
        elif self.vy <= 0 and under is not None and (self.y - under) <= 0.10 and (ny - under) <= 0.10:
            # already standing on the floor: keep the snap, don't clear on_ground and fall
            self.y = under + 0.001
            self.vy = 0
            self.on_ground = True
        elif self.vy > 0 and self._blocked(world, self.x, ny + 0.05, self.z):
            self.vy = 0
            self.on_ground = False
        else:
            self.y = ny
            self.on_ground = False

    def hit_test(self, ox, oy, oz, dx, dy, dz, reach):
        """Distance along the ray to this creature's body, or None."""
        cx, cy, cz = self.x, self.y + self.height * self.scale * 0.5, self.z
        rad = max(self.radius, self.height * 0.5) * self.scale + 0.1
        lx, ly, lz = cx - ox, cy - oy, cz - oz
        t = lx * dx + ly * dy + lz * dz
        if t < 0 or t > reach + rad:
            return None
        d2 = lx * lx + ly * ly + lz * lz - t * t
        if d2 > rad * rad:
            return None
        return max(0.0, t - math.sqrt(max(0.0, rad * rad - d2)))

    def model(self, cam):
        v = MD.creature(self.kind, self.t, self.walking, self.seed, self.hurt)
        return MD.transform(v, yaw_deg=self.yaw, scale=self.scale * (0.6 + 0.4 * max(0.0, self.fade)),
                            offset=(self.x - cam[0], self.y - cam[1], self.z - cam[2]))


class Drop:
    def __init__(self, iid, count, x, y, z, uses=None, vy=3.0):
        self.iid, self.count, self.uses = iid, count, uses
        self.x, self.y, self.z = x, y, z
        a = random.uniform(0, math.tau)
        self.vx, self.vz = math.cos(a) * 1.2, math.sin(a) * 1.2
        self.vy = vy
        self.age = 0.0
        self.t = random.uniform(0, 6)

    def update(self, dt, world):
        self.age += dt
        self.t += dt
        self.vy -= 20 * dt
        nx, nz = self.x + self.vx * dt, self.z + self.vz * dt
        if not solid_at(world, nx, self.y + 0.1, nz):
            self.x, self.z = nx, nz
        ny = self.y + self.vy * dt
        if self.vy < 0 and solid_at(world, self.x, ny, self.z):
            q, r = cell_at(self.x, self.z)
            top = support_top(world, q, r, ny + LAYER * 0.55, LAYER)
            self.y = (top + 0.001) if top is not None else math.floor(ny / LAYER + 1) * LAYER
            self.vy = 0
            self.vx *= 0.5
            self.vz *= 0.5
        else:
            self.y = ny
        if solid_at(world, self.x, self.y + 0.05, self.z):
            q, r = cell_at(self.x, self.z)
            top = support_top(world, q, r, self.y + LAYER * 0.55, LAYER)
            self.y = (top + 0.001) if top is not None else self.y + LAYER

    def model(self, cam):
        v = MD.cached_item(self.iid)
        it = I.get(self.iid)
        scale = 0.32 if it and it.model in ('block', 'deco') else 0.42
        return MD.transform(v, yaw_deg=self.t * 70, scale=scale,
                            offset=(self.x - cam[0], self.y + 0.3 + math.sin(self.t * 2.5) * 0.06 - cam[1], self.z - cam[2]))


def spawn_spot(world, x, z, rng=random, need_open=True):
    """Find a standing spot on top of a column near (x, z) -> (x, y, z) or None."""
    q, r = cell_at(x, z)
    top = world.column_top(q, r)
    if top is None or top < CLOUD_SEA + 2:
        return None
    m = world.get(q, r, top)
    if m <= 0 or not SOLID[m] or MT.KIND[m] != 'full':
        return None
    if world.get(q, r, top + 1) not in (0, MT.ID['petals']) or world.get(q, r, top + 2) != 0:
        return None
    cx, cz = center(q, r)
    return cx, (top + 1) * LAYER + 0.001, cz, m

"""The wanderer: walking over hex terraces (auto-stepping one layer), jumping, gliding,
climbing vines, bouncing on cloudstuff, swimming, and free drifting in Dreamer skies."""
import math

from . import config as C
from .config import LAYER, RADIUS, HEIGHT
from .materials import is_blocking
from .hexgrid import cell_at, center, DIRS, hex_sdf
from . import materials as MT

SOLID = MT.SOLID
_CLOUD = MT.ID['cloudstuff']
_VINE = MT.ID['vine']
_WATER = MT.ID['water']


class Player:
    def __init__(self, x, y, z, yaw=0.0, pitch=0.0):
        self.x, self.y, self.z = x, y, z
        self.vx = self.vy = self.vz = 0.0
        self.yaw, self.pitch = yaw, pitch
        self.on_ground = False
        self.drifting = False
        self.gliding = False
        self.in_water = False
        self.climbing = False
        self.can_glide = False
        self.can_updraft = False
        self.air_jumps = 0
        self.eye_offset = 0.0           # smooths the camera when auto-stepping
        self.last_safe = (x, y, z)
        self.bounced = False
        self.landed = 0.0
        self.noclip = False
        self.fly_speed = C.DRIFT_SPEED
        self.dev_ghost = False          # creatures ignore you (dev mode)
        self.knock = (0.0, 0.0)
        self.crouching = False
        self._eye = C.EYE

    # ------------------------------------------------------------------ collision
    def _columns(self, x, z):
        q, r = cell_at(x, z)
        out = []
        for dq, dr in [(0, 0)] + DIRS:
            cx, cz = center(q + dq, r + dr)
            if hex_sdf(x - cx, z - cz) < RADIUS:
                out.append((q + dq, r + dr))
        return out

    def _solid(self, world, q, r, y):
        return is_blocking(world, q, r, y)

    def body_height(self):
        return C.CROUCH_HEIGHT if self.crouching else HEIGHT

    def collides(self, world, x, y, z):
        ly0 = math.floor((y + 0.002) / LAYER)
        ly1 = math.floor((y + self.body_height() - 0.002) / LAYER)
        for q, r in self._columns(x, z):
            for ly in range(ly0, ly1 + 1):
                if self._solid(world, q, r, ly):
                    return True
        return False

    def touching(self, world, mat):
        ly0 = math.floor((self.y + 0.05) / LAYER)
        ly1 = math.floor((self.y + self.body_height() * 0.8) / LAYER)
        for q, r in self._columns(self.x, self.z):
            for ly in range(ly0, ly1 + 1):
                if world.get(q, r, ly) == mat:
                    return True
        return False

    def ground_material(self, world):
        ly = math.floor((self.y - 0.05) / LAYER)
        q, r = cell_at(self.x, self.z)
        m = world.get(q, r, ly)
        if m > 0 and SOLID[m]:
            return m
        for q2, r2 in self._columns(self.x, self.z):
            m = world.get(q2, r2, ly)
            if m > 0 and SOLID[m]:
                return m
        return 0

    # ------------------------------------------------------------------ movement
    def update(self, dt, world, fwd, strafe, jump_held, jump_pressed, down_held, hurry, crouch=False):
        dt = min(dt, 0.05)
        yaw = math.radians(self.yaw)
        fx, fz = math.sin(yaw), -math.cos(yaw)
        rx, rz = math.cos(yaw), math.sin(yaw)
        mx, mz = fx * fwd + rx * strafe, fz * fwd + rz * strafe
        ml = math.hypot(mx, mz)
        if ml > 1:
            mx, mz = mx / ml, mz / ml
        self.in_water = self.touching(world, _WATER)
        self.climbing = self.touching(world, _VINE) or self.touching(world, MT.ID['ladder'])
        self.bounced = False
        want_crouch = bool(crouch) and not self.drifting
        # only stand up if there's room
        if self.crouching and not want_crouch:
            self.crouching = False
            if self.collides(world, self.x, self.y, self.z):
                self.crouching = True
        else:
            self.crouching = want_crouch
        tgt = C.CROUCH_EYE if self.crouching else C.EYE
        self._eye += (tgt - self._eye) * min(1.0, 12.0 * dt)
        if self.drifting:
            sp = self.fly_speed * (1.8 if hurry else 1.0)
            self.vx, self.vz = mx * sp, mz * sp
            self.vy = (sp * 0.7) * ((1 if jump_held else 0) - (1 if down_held else 0))
            self.gliding = False
        else:
            if self.crouching:
                sp = C.CROUCH_SPEED
            elif hurry:
                sp = C.HURRY
            else:
                sp = C.WALK
            if self.in_water:
                sp *= 0.6
            self.gliding = (self.can_glide and jump_held and not self.on_ground and self.vy < 0
                            and not self.in_water and not self.climbing)
            if self.gliding:
                sp *= 1.45
            accel = 14.0 if self.on_ground else 5.0
            k = min(1.0, accel * dt)
            self.vx += (mx * sp - self.vx) * k
            self.vz += (mz * sp - self.vz) * k
            if self.knock != (0.0, 0.0):
                self.vx += self.knock[0]
                self.vz += self.knock[1]
                self.knock = (0.0, 0.0)
            if self.on_ground:
                self.air_jumps = 0
            if jump_pressed:
                if self.on_ground:
                    self.vy = C.JUMP
                elif self.can_updraft and self.air_jumps < 1 and not self.in_water:
                    self.vy = C.JUMP * 1.05
                    self.air_jumps += 1
            if self.in_water:
                self.vy -= C.GRAVITY * 0.25 * dt
                self.vy *= max(0.0, 1 - 2.5 * dt)
                if jump_held:
                    self.vy = max(self.vy, 3.2)
            elif self.climbing:
                self.vy = 3.0 if (jump_held or fwd > 0) else (-2.0 if down_held else max(self.vy - C.GRAVITY * dt, -1.0))
            else:
                self.vy -= C.GRAVITY * dt
                if self.gliding:
                    self.vy = max(self.vy, -C.GLIDE_FALL)
            self.vy = max(self.vy, -40.0)
        self._move(world, dt)
        if self.eye_offset < 0:
            self.eye_offset = min(0.0, self.eye_offset + dt * 5.0)

    def _move(self, world, dt):
        if self.noclip and self.drifting:
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.on_ground = False
            return
        total = max(abs(self.vx), abs(self.vy), abs(self.vz)) * dt
        steps = max(1, int(total / 0.2) + 1)
        h = dt / steps
        was_ground = self.on_ground
        self.on_ground = False
        for _ in range(steps):
            for axis in (0, 2):
                v = self.vx if axis == 0 else self.vz
                if v == 0:
                    continue
                nx = self.x + (v * h if axis == 0 else 0)
                nz = self.z + (v * h if axis == 2 else 0)
                if not self.collides(world, nx, self.y, nz):
                    if self.crouching and (was_ground or self.on_ground) and not self.drifting:
                        # no walking off edges while crouched
                        if not self.collides(world, nx, self.y - 0.12, nz):
                            if axis == 0:
                                self.vx = 0
                            else:
                                self.vz = 0
                            continue
                    self.x, self.z = nx, nz
                    continue
                # gently step up one layer if there's room
                if (was_ground or self.in_water or self.climbing) and not self.drifting:
                    up = (math.floor(self.y / LAYER + 0.01) + 1) * LAYER
                    if up - self.y <= LAYER + 0.01 and not self.collides(world, nx, up + 0.001, nz) \
                            and not self.collides(world, self.x, up + 0.001, self.z):
                        self.eye_offset -= (up - self.y)
                        self.eye_offset = max(self.eye_offset, -LAYER)
                        self.y = up + 0.001
                        self.x, self.z = nx, nz
                        continue
                if axis == 0:
                    self.vx = 0
                else:
                    self.vz = 0
            ny = self.y + self.vy * h
            if not self.collides(world, self.x, ny, self.z):
                self.y = ny
            else:
                if self.vy < 0:
                    self.y = math.floor((ny + 0.002) / LAYER + 1) * LAYER
                    if self.collides(world, self.x, self.y, self.z):
                        self.y = math.floor(self.y / LAYER + 1) * LAYER
                    landing = self.vy
                    self.on_ground = True
                    self.vy = 0
                    if self.ground_material(world) == _CLOUD and landing < -2.5:
                        self.vy = min(18.0, max(10.0, -landing * 0.9))
                        self.on_ground = False
                        self.bounced = True
                    elif landing < -6:
                        self.landed = -landing
                else:
                    self.vy = 0
        if not self.on_ground and not self.drifting and self.vy <= 0:
            # standing exactly on a top surface?
            if self.collides(world, self.x, self.y - 0.01, self.z):
                self.on_ground = True
        if self.on_ground and self.ground_material(world) not in (0, _CLOUD):
            self.last_safe = (self.x, self.y, self.z)

    @property
    def eye(self):
        return self.x, self.y + self._eye + self.eye_offset, self.z


def raycast(world, ox, oy, oz, dx, dy, dz, reach, skip_water=False):
    """March along the ray; returns ((q, r, y) hit, (q, r, y) previous empty) or (None, None)."""
    step = 0.05
    n = int(reach / step)
    prev = None
    last = None
    x, y, z = ox, oy, oz
    for i in range(n):
        x += dx * step
        y += dy * step
        z += dz * step
        q, r = cell_at(x, z)
        ly = math.floor(y / LAYER)
        cell = (q, r, ly)
        if cell == last:
            continue
        m = world.get(q, r, ly)
        if m < 0:
            return None, None
        if m != 0 and not (skip_water and m == _WATER):
            return cell, prev
        prev = cell
        last = cell
    return None, None

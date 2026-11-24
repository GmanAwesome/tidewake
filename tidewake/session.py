"""One open sky: the wanderer, essences and tuning, spires, tides, motes and saving."""
import math
import random
import time

import numpy as np

from . import config as C
from .config import LAYER, CHUNK, CLOUD_SEA
from .generator import Generator, SPIRE_REGION
from .hexgrid import cell_at, center, hex_distance, DIRS, ring, spiral
from . import materials as MT
from .materials import ID as M, ELEMENTS, ELEMENT_COLORS, FORMS, FORM_LIST, chord_cost
from .mathutil import forward_vector
from .player import Player, raycast
from .sim import Simulation, grow_tree, LIVING
from . import tide as TIDE
from .world import World

START_ESSENCE = [14, 6, 4, 8]
MAX_ESSENCE = 99
ABILITIES = [('Glide', 'Hold Space while falling to glide on the wind.'),
             ('Updraft', 'Press Space in mid-air for a second jump.'),
             ('Tidecall', 'Press T to call the next tide early.')]
INITIAL_META = {M['water']: 4, M['vine']: 8, M['crystal']: 0, M['bloom']: 4, M['mossrock']: 5, M['sprout']: 0}
NEEDS_GROUND = {M['sprout'], M['bloom'], M['crystal']}


def find_spawn(gen):
    """Land a short walk from the nearest spire, so there's something to wonder about right away."""
    sp = None
    for radius in (1, 2, 4):
        cands = [s for s in gen.spires_near(0, 0, radius)]
        if cands:
            sp = min(cands, key=lambda s: s['q'] ** 2 + s['r'] ** 2 + s['q'] * s['r'])
            break
    if sp:
        cq, cr = sp['q'], sp['r']
        for rad in range(16, 40):
            pts = ring(cq, cr, rad)
            Q = np.array([p[0] for p in pts])
            R = np.array([p[1] for p in pts])
            c = gen.columns(Q, R)
            ok = np.nonzero(c['land'] & ~c['skerry'] & ~c['pool'] & ~c['fall'] & (c['e'] > 0.05) &
                            (np.abs(c['top'] - sp['top']) < 6))[0]
            if len(ok):
                open_ = [i for i in ok if c['realm'][i] in (0, 2, 3, 4, 6)]
                i = open_[len(open_) // 2] if open_ else ok[len(ok) // 2]
                return int(Q[i]), int(R[i]), int(c['top'][i]), sp
    for rad in range(0, 400, 3):
        pts = ring(0, 0, rad)
        Q = np.array([p[0] for p in pts])
        R = np.array([p[1] for p in pts])
        c = gen.columns(Q, R)
        ok = np.nonzero(c['land'] & ~c['skerry'] & ~c['pool'] & (c['e'] > 0.08))[0]
        if len(ok):
            i = ok[0]
            return int(Q[i]), int(R[i]), int(c['top'][i]), None
    return 0, 0, 60, None


class Session:
    def __init__(self, app, storage, create=None, view_distance=6):
        self.app = app
        self.storage = storage
        if create:
            self.name = create['name']
            self.seed = create['seed']
            self.seed_text = create.get('seed_text', '')
            self.mode = create.get('mode', 'wanderer')
            self.gen = Generator(self.seed)
            q, r, top, sp = find_spawn(self.gen)
            x, z = center(q, r)
            yaw = 0.0
            if sp:
                sx, sz = center(sp['q'], sp['r'])
                yaw = math.degrees(math.atan2(sx - x, -(sz - z)))
            self.player = Player(x, (top + 1) * LAYER + 0.001, z, yaw=yaw, pitch=4.0)
            self.spawn_spire = sp
            self.essence = list(START_ESSENCE)
            self.chord = [0]
            self.awakened = []
            self.phase = 0.08
            self.play_time = 0.0
            self.created = time.time()
            self.stats = {'gathered': 0, 'shaped': 0, 'motes': 0}
            self.new_sky = True
        else:
            d = storage.load()
            self.name = d.get('name', storage.folder)
            self.seed = d['seed']
            self.seed_text = d.get('seed_text', '')
            self.mode = d.get('mode', 'wanderer')
            self.gen = Generator(self.seed)
            p = d['player']
            self.player = Player(p['x'], p['y'], p['z'], p.get('yaw', 0), p.get('pitch', 0))
            self.player.drifting = bool(p.get('drifting')) and self.mode == 'dreamer'
            self.player.last_safe = tuple(p.get('safe', (p['x'], p['y'], p['z'])))
            self.essence = [int(v) for v in d.get('essence', START_ESSENCE)][:4]
            self.chord = [int(e) for e in d.get('chord', [0])][:2] or [0]
            self.awakened = list(d.get('awakened', []))
            self.phase = float(d.get('phase', 0.1))
            self.play_time = float(d.get('play_time', 0))
            self.created = d.get('created', time.time())
            self.stats = dict({'gathered': 0, 'shaped': 0, 'motes': 0}, **d.get('stats', {}))
            self.new_sky = False
        self.world = World(self.seed, storage, app.renderer, app.pool, view_distance)
        self.sim = Simulation(self.world, self.seed & 0xFFFF)
        self.sim.on_tree = self._grow_tree
        self.world.on_chunk_loaded = self._chunk_loaded
        self.apply_abilities()
        self.ready = False
        self.target = self.target_prev = None
        self.target_name = ''
        self.cooldown = 0.0
        self.particles = np.zeros((0, 12))      # x y z vx vy vz r g b life size homing
        self.motes = []                          # [x, y, z, phase, life]
        self.jellies = []                        # drifting sky jellies: [x, y, z, phase, hue, size, vx, vz]
        self.toasts = []                         # [text, sub, time_left]
        self.autosave = C.AUTOSAVE
        self.walk = 0.0
        self.step_acc = 0.0
        self.carry = 0.0                         # > 0 while the clouds carry you back
        self.tide_rush = 0.0
        self.last_tide_name = TIDE.name(self.phase)
        self.spire_cache_t = 0.0
        self.nearest_spire = None
        self.beams = []                          # awakened spires near you get a light beam
        self.time = 0.0
        self.hold = False
        if self.new_sky:
            self.toast('Welcome to ' + self.name, 'Follow the wayfinder to the dormant spire. Press J for the journal.')
        self.save()

    # ------------------------------------------------------------------ helpers
    def apply_abilities(self):
        n = len(self.awakened) if self.mode == 'wanderer' else 3
        self.player.can_glide = n >= 1
        self.player.can_updraft = n >= 2
        self.can_tidecall = n >= 3

    def toast(self, text, sub='', secs=5.0):
        self.toasts = [t for t in self.toasts if t[0] != text][-1:]
        self.toasts.append([text, sub, secs])

    @property
    def form(self):
        return FORMS[tuple(sorted(self.chord))]

    def form_name(self):
        return MT.NAMES[self.form]

    def toggle_element(self, e):
        ch = list(self.chord)
        if e in ch:
            if len(ch) > 1:
                ch.remove(e)
        else:
            ch = ([ch[-1]] if ch else []) + [e]
            ch = ch[-2:]
        self.chord = sorted(ch)
        self.app.audio.play('chord')

    def cycle_form(self, d):
        i = FORM_LIST.index(tuple(sorted(self.chord)))
        self.chord = list(FORM_LIST[(i + d) % len(FORM_LIST)])
        self.app.audio.play('chord', 0.6)

    def can_afford(self):
        if self.mode == 'dreamer':
            return True
        cost = chord_cost(self.chord)
        return all(self.essence[i] >= cost[i] for i in range(4))

    # ------------------------------------------------------------------ loading
    def load_progress(self):
        p = self.player
        self.world.update(p.x, p.z, 6)
        return self.world.progress(p.x, p.z, 50.0)

    def finish_loading(self):
        """Make sure we're standing on something (a saved sky may have changed)."""
        p = self.player
        if self.new_sky:
            q0, r0 = cell_at(p.x, p.z)
            ground = (M['turf'], M['sand'], M['snow'], M['stone'], M['basalt'], M['rosestone'], M['loam'])

            def good(a, b, open_r, picky):
                top = self.world.column_top(a, b)
                if top is None or top < 0 or self.world.get(a, b, top) not in ground:
                    return None
                if picky and self.world.realm_at(a, b) in (1, 5, 7):
                    return None
                if self.world.get(a, b, top + 1) not in (0, M['petals']) or self.world.get(a, b, top + 2) != 0:
                    return None
                for c, d in spiral(a, b, open_r):
                    t = self.world.column_top(c, d)
                    if t is None or t > top + 1:
                        return None
                return top

            spot = None
            for open_r, picky, reach in ((4, True, 22), (2, False, 20)):
                for a, b in spiral(q0, r0, reach):
                    top = good(a, b, open_r, picky)
                    if top is not None:
                        spot = (a, b, top)
                        break
                if spot:
                    break
            if spot:
                a, b, top = spot
                p.x, p.z = center(a, b)
                p.y = (top + 1) * LAYER + 0.001
                p.last_safe = (p.x, p.y, p.z)
                sp = getattr(self, 'spawn_spire', None)
                if sp:
                    sx, sz = center(sp['q'], sp['r'])
                    p.yaw = math.degrees(math.atan2(sx - p.x, -(sz - p.z)))
        if p.collides(self.world, p.x, p.y, p.z):
            q, r = cell_at(p.x, p.z)
            top = self.world.column_top(q, r)
            if top is not None and top >= 0:
                p.y = (top + 1) * LAYER + 0.001
        self.ready = True

    def _chunk_loaded(self, c):
        """Wake living cells in loaded player-changed chunks (so growth carries on)."""
        if not c.from_save:
            return
        living = np.isin(c.cells, list(LIVING)) & (c.meta > 0)
        idx = np.argwhere(living)
        for lq, y, lr in idx[:400]:
            self.sim.wake(c.cq * CHUNK + int(lq), c.cr * CHUNK + int(lr), int(y), random.uniform(0.5, 4))

    def _grow_tree(self, q, r, top):
        realm = self.world.realm_at(q, r) or 0
        self.world.set(q, r, top + 1, 0)
        grow_tree(self.world, q, r, top, realm, random.Random(q * 31 + r))
        self.app.audio.play('chord', 0.5)
        self.burst(q, r, top + 3, (0.6, 0.95, 0.5), 18)

    # ------------------------------------------------------------------ frame
    def update(self, dt, inp):
        self.time += dt
        self.play_time += dt
        p = self.player
        speed = 1.0 / C.TIDE_LENGTH * (25.0 if self.tide_rush > 0 else 1.0)
        old = self.phase
        self.phase = (self.phase + dt * speed) % 1.0
        if self.tide_rush > 0:
            self.tide_rush -= dt
            if (old < 0.5 <= self.phase) or (old > self.phase):     # reached a tide peak
                self.tide_rush = 0
        nm = TIDE.name(self.phase)
        if nm != self.last_tide_name and nm in ('Lighttide', 'Dusktide'):
            self.toast(nm + ' rises', 'Things grow in the light; crystals and blooms shine in the dusk.'
                       if nm == 'Dusktide' else 'Sprouts, vines and blooms spread while the light is high.', 4)
            self.app.audio.play('tide', 0.6)
        self.last_tide_name = nm

        if self.carry > 0:
            self.carry -= dt
            if self.carry <= 0.6 and self.carry + dt > 0.6:
                p.x, p.y, p.z = p.last_safe
                p.y += 0.01
                p.vx = p.vy = p.vz = 0
            inp = dict(inp, fwd=0, strafe=0, jump=False, jump_pressed=False)
        if self.hold:
            if self.world.ready_at(p.x, p.z) and not self.world.dirty:
                self.hold = False
            inp = dict(inp, fwd=0, strafe=0, jump=False, jump_pressed=False)
            p.vy = 0
        else:
            p.update(dt, self.world, inp['fwd'], inp['strafe'], inp['jump'], inp['jump_pressed'], inp['down'], inp['hurry'])
        if p.bounced:
            self.app.audio.play('bounce', 0.8)
        if p.landed:
            self.app.audio.play('step_soft', 0.7)
            p.landed = 0
        if p.y < CLOUD_SEA * LAYER - 2 and self.carry <= 0:
            self.carry = 1.6
            self.app.audio.play('whoosh', 0.8)
            self.toast('The clouds carry you back', 'Nothing is ever lost in Tidewake.', 3.5)
        # footsteps
        moving = math.hypot(p.vx, p.vz)
        if p.on_ground and moving > 0.5:
            self.walk += moving * dt
            self.step_acc += moving * dt
            if self.step_acc > 2.1:
                self.step_acc = 0
                g = p.ground_material(self.world)
                snd = MT.SOUND[g] if g > 0 else None
                if snd:
                    self.app.audio.play('step_' + snd, 0.5)
        # aim
        ex, ey, ez = p.eye
        fx, fy, fz = forward_vector(p.yaw, p.pitch)
        self.target, self.target_prev = raycast(self.world, ex, ey, ez, fx, fy, fz, C.REACH)
        self.target_name = ''
        if self.target:
            m = self.world.get(*self.target)
            if m > 0:
                self.target_name = MT.NAMES[m]
        self.cooldown -= dt
        if self.cooldown <= 0 and self.carry <= 0:
            if inp.get('gather'):
                self.gather()
                self.cooldown = 0.22
            elif inp.get('shape'):
                self.shape()
                self.cooldown = 0.22
        self.sim.step(dt, TIDE.dusk_amount(self.phase))
        self.world.update(p.x, p.z)
        self._update_motes(dt)
        self._update_jellies(dt)
        self._update_particles(dt)
        for t in self.toasts:
            t[2] -= dt
        self.toasts = [t for t in self.toasts if t[2] > 0]
        self.spire_cache_t -= dt
        if self.spire_cache_t <= 0:
            self.spire_cache_t = 0.5
            self._scan_spires()
        self.autosave -= dt
        if self.autosave <= 0:
            self.autosave = C.AUTOSAVE
            self.save()

    # ------------------------------------------------------------------ gather / shape
    def gather(self):
        if not self.target:
            return
        q, r, y = self.target
        m = self.world.get(q, r, y)
        if m <= 0 or not MT.GATHERABLE[m]:
            if m in (M['dormant_spire'], M['awake_spire']):
                self.toast('The spire will not move', 'It is older than the islands.', 2.5)
            return
        self.world.set(q, r, y, 0, 0, now=True)
        above = self.world.get(q, r, y + 1)
        if above > 0 and MT.IS_DECO[above] and above not in (M['vine'], M['lantern']):
            self.world.set(q, r, y + 1, 0, 0, now=True)
        y_ = MT.YIELDS[m]
        if self.mode == 'wanderer':
            for i in range(4):
                self.essence[i] = min(MAX_ESSENCE, self.essence[i] + y_[i])
        self.stats['gathered'] += 1
        self.sim.wake_around(q, r, y)
        snd = MT.SOUND[m] or 'stone'
        self.app.audio.play('gather_' + snd, 0.8)
        cx, cz = center(q, r)
        for i in range(4):
            if y_[i]:
                self._spawn(cx, (y + 0.5) * LAYER, cz, ELEMENT_COLORS[i], 7 * y_[i], homing=True)
        self._spawn(cx, (y + 0.5) * LAYER, cz, MT.TOP[m], 8, homing=False)

    def shape(self):
        if not self.target or not self.target_prev:
            return
        q, r, y = self.target_prev
        cur = self.world.get(q, r, y)
        if cur not in (0, M['water']) or y >= C.LAYERS - 1 or y < 1:
            return
        form = self.form
        if not self.can_afford():
            cost = chord_cost(self.chord)
            lack = [ELEMENTS[i] for i in range(4) if self.essence[i] < cost[i]]
            hint = 'Gather glowing things, or catch dusk motes.' if 'Light' in lack else 'Gather cells to collect more.'
            self.toast('Not enough ' + ' and '.join(lack), hint, 2.5)
            return
        below = self.world.get(q, r, y - 1)
        if form in NEEDS_GROUND and not (below > 0 and MT.SOLID[below]):
            self.toast(MT.NAMES[form] + ' needs solid ground beneath it', '', 2.0)
            return
        if MT.SOLID[form]:
            p = self.player
            # don't shape a cell inside yourself
            lo, hi = math.floor((p.y + 0.01) / LAYER), math.floor((p.y + C.HEIGHT) / LAYER)
            if lo <= y <= hi and (q, r) in p._columns(p.x, p.z):
                return
        self.world.set(q, r, y, form, INITIAL_META.get(form, 0), now=True)
        if self.mode == 'wanderer':
            cost = chord_cost(self.chord)
            for i in range(4):
                self.essence[i] -= cost[i]
        self.stats['shaped'] += 1
        if form in LIVING:
            self.sim.wake(q, r, y, 0.5)
        self.sim.wake_around(q, r, y)
        self.app.audio.play('shape', 0.7)
        cx, cz = center(q, r)
        self._spawn(cx, (y + 0.5) * LAYER, cz, MT.TOP[form], 10, homing=False)
        self._check_spires(q, r, y)

    # ------------------------------------------------------------------ spires
    def spire_state(self, s):
        """(present materials set, missing list) for a spire's offering ring."""
        T = s['top']
        have = set()
        for a, b in ring(s['q'], s['r'], 1):
            m = self.world.get(a, b, T + 1)
            if m > 0:
                have.add(m)
        missing = [w for w in s['wants'] if w not in have]
        return have, missing

    def _check_spires(self, q, r, y):
        for s in self.gen.spires_near(q, r, 1):
            if s['id'] in self.awakened:
                continue
            if hex_distance(q, r, s['q'], s['r']) == 1 and y == s['top'] + 1:
                have, missing = self.spire_state(s)
                if not missing:
                    self.awaken(s)
                else:
                    self.toast('The spire stirs...', 'It still longs for ' + ', '.join(MT.NAMES[m] for m in missing), 3.5)

    def awaken(self, s):
        self.awakened.append(s['id'])
        T = s['top']
        for y in range(T + 1, T + 1 + s['height']):
            if self.world.get(s['q'], s['r'], y) == M['dormant_spire']:
                self.world.set(s['q'], s['r'], y, M['awake_spire'], now=False)
        rng = random.Random(len(self.awakened))
        for a, b in spiral(s['q'], s['r'], 7):
            if hex_distance(a, b, s['q'], s['r']) <= 1:
                continue
            top = self.world.column_top(a, b)
            if top is None or top < 0:
                continue
            g = self.world.get(a, b, top)
            if g in (M['turf'], M['mossrock'], M['plinth'], M['stone'], M['snow'], M['sand']) and \
                    self.world.get(a, b, top + 1) == 0 and rng.random() < 0.35:
                self.world.set(a, b, top + 1, M['bloom'] if g in (M['turf'], M['mossrock']) else M['crystal'], 1)
        n = len(self.awakened)
        if self.mode == 'wanderer':
            self.essence[2] = min(MAX_ESSENCE, self.essence[2] + 12)
            self.essence[3] = min(MAX_ESSENCE, self.essence[3] + 6)
        self.apply_abilities()
        self.app.audio.play('awaken', 1.0)
        cx, cz = center(s['q'], s['r'])
        for k in range(5):
            self._spawn(cx, (T + 2 + k * 2) * LAYER, cz, (0.85, 0.78, 1.0), 25, homing=False, speed=4.0)
        if self.mode == 'wanderer' and n <= len(ABILITIES):
            ab = ABILITIES[n - 1]
            self.toast(f'A spire awakens! You learned {ab[0]}', ab[1], 7.0)
        else:
            self.toast('A spire awakens!', f'{n} spires sing in this sky now.', 6.0)
        self.save()

    def _scan_spires(self):
        p = self.player
        q, r = cell_at(p.x, p.z)
        best, bd = None, 1e18
        for s in self.gen.spires_near(q, r, 3):
            if s['id'] in self.awakened:
                continue
            sx, sz = center(s['q'], s['r'])
            d = math.hypot(sx - p.x, sz - p.z)
            if d < bd:
                best, bd = s, d
        self.nearest_spire = (best, bd) if best else None
        self.beams = []
        for s in self.gen.spires_near(q, r, 2):
            if s['id'] in self.awakened:
                self.beams.append(s)

    def spire_at(self, q, r):
        for s in self.gen.spires_near(q, r, 1):
            if s['q'] == q and s['r'] == r:
                return s
        return None

    # ------------------------------------------------------------------ motes & particles
    def _spawn(self, x, y, z, col, n, homing=False, speed=2.0):
        rng = np.random.default_rng()
        P = np.zeros((n, 12))
        P[:, 0], P[:, 1], P[:, 2] = x, y, z
        P[:, 3:6] = rng.normal(0, speed * 0.5, (n, 3))
        P[:, 4] += speed * 0.6
        P[:, 6:9] = np.array(col[:3]) * rng.uniform(0.85, 1.15, (n, 1))
        P[:, 9] = rng.uniform(0.8, 1.6, n)
        P[:, 10] = rng.uniform(0.10, 0.22, n)
        P[:, 11] = 1.0 if homing else 0.0
        self.particles = np.concatenate([self.particles, P])[-1500:]

    def burst(self, q, r, y, col, n):
        cx, cz = center(q, r)
        self._spawn(cx, (y + 0.5) * LAYER, cz, col, n)

    def _update_particles(self, dt):
        P = self.particles
        if not len(P):
            return
        p = self.player
        ex, ey, ez = p.x, p.y + 1.1, p.z
        h = P[:, 11] > 0.5
        if h.any():
            to = np.stack([ex - P[h, 0], ey - P[h, 1], ez - P[h, 2]], 1)
            d = np.linalg.norm(to, axis=1, keepdims=True) + 1e-6
            P[h, 3:6] += (to / d * 14.0 - P[h, 3:6]) * min(1.0, 3.0 * dt)
            P[h, 9] = np.where(d[:, 0] < 0.6, 0, P[h, 9])
        P[~h, 4] -= 1.0 * dt
        P[~h, 3:6] *= (1 - 1.2 * dt)
        P[:, 0:3] += P[:, 3:6] * dt
        P[:, 9] -= dt
        self.particles = P[P[:, 9] > 0]

    def _update_motes(self, dt):
        if not self.app.settings['motes']:
            self.motes = []
            return
        p = self.player
        dusk = TIDE.dusk_amount(self.phase)
        want = int(4 + 14 * dusk)
        while len(self.motes) < want and random.random() < dt * 3:
            ang = random.uniform(0, 2 * math.pi)
            dist = random.uniform(4, 16)
            x, z = p.x + math.cos(ang) * dist, p.z + math.sin(ang) * dist
            y = p.y + random.uniform(0.6, 4.0)
            q, r = cell_at(x, z)
            if self.world.get(q, r, math.floor(y / LAYER)) == 0:
                self.motes.append([x, y, z, random.uniform(0, 6.3), random.uniform(18, 40), dusk > 0.45])
        keep = []
        ex, ey, ez = p.x, p.y + 0.9, p.z
        for m in self.motes:
            m[3] += dt
            m[4] -= dt
            m[0] += math.sin(m[3] * 0.7) * 0.4 * dt
            m[2] += math.cos(m[3] * 0.5) * 0.4 * dt
            m[1] += math.sin(m[3] * 1.3) * 0.25 * dt
            d = math.sqrt((m[0] - ex) ** 2 + (m[1] - ey) ** 2 + (m[2] - ez) ** 2)
            if d < 1.5 and m[5]:
                if self.mode == 'wanderer':
                    self.essence[2] = min(MAX_ESSENCE, self.essence[2] + 1)
                self.stats['motes'] += 1
                self.app.audio.play('mote', 0.7)
                self._spawn(m[0], m[1], m[2], ELEMENT_COLORS[2], 6, homing=True)
                continue
            if m[4] > 0 and math.hypot(m[0] - p.x, m[2] - p.z) < 26:
                keep.append(m)
        self.motes = keep

    def _update_jellies(self, dt):
        p = self.player
        if len(self.jellies) < 5 and random.random() < dt * 0.5:
            ang = random.uniform(0, 2 * math.pi)
            d = random.uniform(25, 55)
            hue = random.choice([(0.80, 0.70, 1.0), (0.60, 0.95, 0.90), (1.0, 0.75, 0.70), (0.95, 0.90, 0.60)])
            sp = random.uniform(0.4, 1.0)
            a2 = random.uniform(0, 2 * math.pi)
            self.jellies.append([p.x + math.cos(ang) * d, p.y + random.uniform(4, 22), p.z + math.sin(ang) * d,
                                 random.uniform(0, 6.3), hue, random.uniform(1.4, 2.6), math.cos(a2) * sp, math.sin(a2) * sp])
        keep = []
        for j in self.jellies:
            j[3] += dt
            j[0] += j[6] * dt
            j[2] += j[7] * dt
            j[1] += math.sin(j[3] * 0.9) * 0.5 * dt + 0.1 * dt
            if math.hypot(j[0] - p.x, j[2] - p.z) < 75:
                keep.append(j)
        self.jellies = keep

    def _jelly_points(self, cx, cy, cz):
        if not self.jellies:
            return None
        dusk = TIDE.dusk_amount(self.phase)
        out = []
        for x, y, z, ph, hue, size, _, _ in self.jellies:
            pulse = 0.85 + 0.15 * math.sin(ph * 2.2)
            a = np.linspace(0, 2 * math.pi, 14, endpoint=False)
            rr = 0.9 * size * pulse
            ring_ = np.column_stack([x + np.cos(a) * rr, y + np.zeros(14), z + np.sin(a) * rr])
            dome = np.array([[x, y + 0.5 * size, z], [x, y + 0.25 * size, z]])
            pts = [ring_, dome]
            for k in range(5):
                ang = k / 5 * 2 * math.pi + 0.3
                t = np.arange(1, 8)
                sway = np.sin(ph * 1.5 + t * 0.6 + k) * 0.25 * size
                pts.append(np.column_stack([x + math.cos(ang) * rr * 0.5 + sway, y - t * 0.35 * size,
                                            z + math.sin(ang) * rr * 0.5 + sway * 0.5]))
            P = np.concatenate(pts)
            n = len(P)
            alpha = np.concatenate([np.full(14, 0.55), [0.8, 0.9], np.tile(np.linspace(0.45, 0.1, 7), 5)]) * (0.5 + 0.6 * dusk)
            sz = np.concatenate([np.full(14, 0.9), [2.2, 1.6], np.full(35, 0.45)]) * size
            col = np.tile(hue, (n, 1))
            out.append(np.column_stack([P[:, 0] - cx, P[:, 1] - cy, P[:, 2] - cz, col, alpha, sz]))
        return np.concatenate(out)

    def point_data(self, cam):
        """(N, 8) float32 relative to the camera: particles, motes and spire beams."""
        cx, cy, cz = cam
        out = []
        P = self.particles
        if len(P):
            a = np.clip(P[:, 9], 0, 1)
            out.append(np.column_stack([P[:, 0] - cx, P[:, 1] - cy, P[:, 2] - cz, P[:, 6:9], a, P[:, 10] * 1.4]))
        if self.motes:
            Mo = np.array(self.motes)
            tw = 0.6 + 0.4 * np.sin(Mo[:, 3] * 3.0)
            gold = Mo[:, 5] > 0.5
            col = np.where(gold[:, None], np.array([1.0, 0.85, 0.45]), np.array([0.85, 1.0, 0.75]))
            out.append(np.column_stack([Mo[:, 0] - cx, Mo[:, 1] - cy, Mo[:, 2] - cz, col, tw * np.where(gold, 1.0, 0.5),
                                        np.where(gold, 0.55, 0.3)]))
        J = self._jelly_points(cx, cy, cz)
        if J is not None:
            out.append(J)
        for s in self.beams:
            sx, sz = center(s['q'], s['r'])
            base = (s['top'] + 1 + s['height']) * LAYER
            ys = base + np.arange(0, 60, 1.5) + (self.time * 3.0) % 1.5
            n = len(ys)
            fade = np.clip(1 - (ys - base) / 60, 0, 1)
            out.append(np.column_stack([np.full(n, sx - cx), ys - cy, np.full(n, sz - cz), np.full(n, 0.85),
                                        np.full(n, 0.78), np.full(n, 1.0), fade * 0.8, np.full(n, 2.2)]))
        if not out:
            return np.zeros((0, 8), 'f4')
        return np.concatenate(out).astype('f4')

    def extra_lights(self, cam):
        """Point lights for motes near the camera."""
        cx, cy, cz = cam
        L = [(m[0] - cx, m[1] - cy, m[2] - cz, M['lantern']) for m in self.motes[:6] if m[5]]
        return [np.array(L)] if L else []

    # ------------------------------------------------------------------ commands
    def command(self, text):
        parts = text.strip().lstrip('/').split()
        if not parts:
            return
        cmd, args = parts[0].lower(), parts[1:]
        p = self.player
        try:
            if cmd == 'tp' and len(args) >= 2:
                x, z = float(args[0].replace(',', '')), float(args[1].replace(',', ''))
                q0, r0 = cell_at(x, z)
                spot = None
                for rad in range(0, 300, 2):
                    pts = ring(q0, r0, rad)[::max(1, rad // 6)]
                    c = self.gen.columns(np.array([a for a, b in pts]), np.array([b for a, b in pts]))
                    ok = np.nonzero(c['land'] & ~c['pool'] & ~c['fall'] & (c['e'] > 0.03))[0]
                    if len(ok):
                        i = ok[0]
                        spot = (pts[i][0], pts[i][1], int(c['top'][i]))
                        break
                if spot is None:
                    self.toast('Only clouds out there', 'No island found near that spot.', 3)
                    return
                p.x, p.z = center(spot[0], spot[1])
                p.y = (spot[2] + 4) * LAYER
                p.vx = p.vy = p.vz = 0
                p.last_safe = (p.x, (spot[2] + 1) * LAYER + 0.001, p.z)
                self.hold = True
                self.toast(f'Drifted to {p.x:,.0f}, {p.z:,.0f}', '', 3)
            elif cmd == 'tide':
                self.phase = 0.5 if args and args[0].startswith('d') else 0.0
                self.toast('The tide turns', '', 2)
            elif cmd == 'seed':
                self.toast(f'Seed: {self.seed}', self.seed_text, 6)
            elif cmd == 'spire':
                if self.nearest_spire:
                    s = self.nearest_spire[0]
                    x, z = center(s['q'] + 5, s['r'] + 2)
                    p.x, p.z, p.y = x, z, (s['top'] + 4) * LAYER
                    self.toast('Drifted near a spire', '', 3)
            else:
                self.toast('Unknown words: ' + cmd, 'Try /tp x z, /tide dusk, /tide light, /seed, /spire', 4)
        except ValueError:
            self.toast('Those words did not make sense', '', 3)

    # ------------------------------------------------------------------ saving
    def to_dict(self):
        p = self.player
        return {'name': self.name, 'seed': self.seed, 'seed_text': self.seed_text, 'mode': self.mode,
                'player': {'x': p.x, 'y': p.y, 'z': p.z, 'yaw': p.yaw, 'pitch': p.pitch, 'drifting': p.drifting,
                           'safe': list(p.last_safe)},
                'essence': self.essence, 'chord': self.chord, 'awakened': self.awakened, 'phase': self.phase,
                'play_time': self.play_time, 'created': self.created, 'stats': self.stats}

    def save(self):
        if self.storage:
            self.world.save_modified()
            self.storage.save(self.to_dict())

    def close(self):
        self.save()
        self.world.close()

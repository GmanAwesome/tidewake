"""One open sky: the wanderer, mining and building, creatures, spires, tides and saving."""
import math
import random
import time

import numpy as np

from . import config as C
from .config import LAYER, CHUNK, CLOUD_SEA
from . import gensettings as GS
from .generator import Generator, SPIRE_REGION
from .hexgrid import cell_at, center, hex_distance, DIRS, ring, spiral
from . import materials as MT
from .materials import ID as M
from .mathutil import forward_vector
from .player import Player, raycast
from .sim import Simulation, grow_tree, LIVING
from . import tide as TIDE
from .world import World
from . import items as I
from .inventory import Inventory
from .entities import Mob, Drop, spawn_spot, KINDS, FLYING, FLOWER_BLOCKS, solid_at
from . import models as MD

ABILITIES = [('Glide', 'Hold Space while falling to glide on the wind.'),
             ('Updraft', 'Press Space in mid-air for a second jump.'),
             ('Tidecall', 'Press T to call the next tide early.')]
INITIAL_META = {M['water']: 4, M['vine']: 8, M['crystal']: 0, M['bloom']: 4, M['mossrock']: 5, M['sprout']: 0}
NEEDS_GROUND = {M['sprout'], M['bloom'], M['crystal'], M['berry_bush'], M['glowstick'], M['bedroll'], M['petals'],
                M['glowcap'], M['door'], M['skywheat'], M['sweetroot_crop'], M['berry_crop']}
MAX_HP = 20
MAX_FOOD = 20
STARTER = [(I.BERRIES.id, 4), (M['glowstick'], 3)]
USE_BLOCKS = {M['tinker_bench'], M['kiln'], M['chest'], M['bedroll'], M['door'], M['waystone'], M['tidewell']}
SPRITE_HELD = {'pick', 'axe', 'spade', 'blade', 'stick', 'rod', 'hoe'}
PASSIVE_REALMS = {
    'woolhop': (0, 1, 5, 3, 7, 8, 9, 10, 14),
    'pebblebeak': (0, 2, 6, 1, 4, 11, 12),
    'mossback': (5, 4, 3, 7, 9, 12, 15),
    'mossturtle': (5, 4, 3, 7, 9, 12, 15),
    'crystalbeetle': (1, 4, 8, 11, 13, 14),
    'islekit': (0, 1, 3, 5, 8, 9, 10, 14),
}


def find_spawn(gen):
    """Land a short walk from the nearest spire, so there's something to wonder about right away."""
    if getattr(gen, 'tutorial', False):
        from . import tutorial as TUT
        q, r, top = TUT.SPAWN
        return q, r, top, None
    def _near(cands):
        return min(cands, key=lambda s: s['q'] ** 2 + s['r'] ** 2 + s['q'] * s['r'])

    mid_lo, mid_hi = (80, 170) if getattr(gen, 'version', 2) >= 3 else (36, 88)
    mid = (mid_lo + mid_hi) // 2

    def _around_spire(sp, mid_only=True):
        cq, cr = sp['q'], sp['r']
        for rad in range(16, 48):
            pts = ring(cq, cr, rad)
            Q = np.array([p[0] for p in pts])
            R = np.array([p[1] for p in pts])
            c = gen.columns(Q, R)
            ok = c['land'] & ~c['skerry'] & ~c['pool'] & ~c['fall'] & (c['e'] > 0.05) & (
                np.abs(c['top'] - sp['top']) < 8)
            if mid_only:
                ok = ok & (c['top'] >= mid_lo) & (c['top'] <= mid_hi)
            idx = np.nonzero(ok)[0]
            if len(idx):
                open_ = [i for i in idx if c['realm'][i] in (0, 2, 3, 4, 6)]
                i = open_[len(open_) // 2] if open_ else idx[len(idx) // 2]
                return int(Q[i]), int(R[i]), int(c['top'][i]), sp
        return None

    mid_spires, any_spires = [], []
    for radius in (1, 2, 4, 6):
        cands = list(gen.spires_near(0, 0, radius))
        any_spires.extend(cands)
        mid_spires.extend(s for s in cands if mid_lo <= s['top'] <= mid_hi)
        if mid_spires:
            break
    if mid_spires:
        found = _around_spire(_near(mid_spires), mid_only=True)
        if found:
            return found
    for rad in range(0, 400, 3):
        pts = ring(0, 0, rad)
        Q = np.array([p[0] for p in pts])
        R = np.array([p[1] for p in pts])
        c = gen.columns(Q, R)
        mid_ok = np.nonzero(c['land'] & ~c['skerry'] & ~c['pool'] & (c['e'] > 0.08) &
                            (np.abs(c['top'] - mid) <= 24))[0]
        if len(mid_ok):
            i = mid_ok[0]
            return int(Q[i]), int(R[i]), int(c['top'][i]), None
    # last resort: the nearest spire, even if it sits very high or low
    if any_spires:
        found = _around_spire(_near(any_spires), mid_only=False)
        if found:
            return found
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
    def __init__(self, app, storage, create=None, view_distance=8, far_distance=16):
        self.app = app
        self.storage = storage
        self.inv = Inventory(36)
        self.chests = {}
        self.kilns = {}
        if create:
            self.name = create['name']
            self.seed = create['seed']
            self.seed_text = create.get('seed_text', '')
            self.mode = create.get('mode', 'wanderer')
            self.tutorial = bool(create.get('tutorial'))
            self.gen_settings = GS.normalize(create.get('gen'))
            if self.tutorial:
                self.gen_settings = dict(self.gen_settings or GS.defaults(), tutorial=True)
            self.gen = Generator(self.seed, self.gen_settings)
            q, r, top, sp = find_spawn(self.gen)
            x, z = center(q, r)
            yaw = 0.0
            if sp:
                sx, sz = center(sp['q'], sp['r'])
                yaw = math.degrees(math.atan2(sx - x, -(sz - z)))
            self.player = Player(x, (top + 1) * LAYER + 0.001, z, yaw=yaw, pitch=4.0)
            self.spawn_spire = sp
            self.awakened = []
            self.phase = 0.08
            self.play_time = 0.0
            self.created = time.time()
            self.stats = {'mined': 0, 'placed': 0, 'motes': 0, 'crafted': 0, 'fished': 0, 'farmed': 0}
            self.new_sky = True
            self.hp, self.food = MAX_HP, MAX_FOOD
            self.spawn = None
            self.dev = self.mode == 'dreamer'
            self.hot = 0
            self.weather = 'clear'
            self.waystones = {}
            self.attune = []
            self.achieved = []
            for iid, n in STARTER:
                self.inv.add(iid, n)
        else:
            d = storage.load()
            self.name = d.get('name', storage.folder)
            self.seed = d['seed']
            self.seed_text = d.get('seed_text', '')
            self.mode = d.get('mode', 'wanderer')
            self.gen_settings = GS.normalize(d['gen']) if d.get('gen') is not None else None
            self.tutorial = bool(d.get('tutorial'))
            if self.tutorial:
                self.gen_settings = dict(self.gen_settings or GS.defaults(), tutorial=True)
            self.gen = Generator(self.seed, self.gen_settings)
            p = d['player']
            self.player = Player(p['x'], p['y'], p['z'], p.get('yaw', 0), p.get('pitch', 0))
            self.player.drifting = bool(p.get('drifting'))
            self.player.noclip = bool(p.get('noclip'))
            self.player.fly_speed = float(p.get('fly_speed', C.DRIFT_SPEED))
            self.player.last_safe = tuple(p.get('safe', (p['x'], p['y'], p['z'])))
            self.awakened = list(d.get('awakened', []))
            self.phase = float(d.get('phase', 0.1))
            self.play_time = float(d.get('play_time', 0))
            self.created = d.get('created', time.time())
            self.stats = dict({'mined': 0, 'placed': 0, 'motes': 0, 'crafted': 0, 'fished': 0, 'farmed': 0}, **d.get('stats', {}))
            self.new_sky = False
            self.hp = float(d.get('hp', MAX_HP))
            self.food = float(d.get('food', MAX_FOOD))
            self.spawn = tuple(d['spawn']) if d.get('spawn') else None
            self.dev = bool(d.get('dev', self.mode == 'dreamer'))
            self.hot = int(d.get('hot', 0)) % 9
            self.weather = d.get('weather', 'clear')
            if 'inventory' in d:
                self.inv.load(d['inventory'])
            else:                                   # a 1.0 sky: hand over a starter kit
                for iid, n in STARTER:
                    self.inv.add(iid, n)
            self.chests = {k: Inventory(27).load(v) for k, v in d.get('chests', {}).items()}
            self.kilns = {k: {'slots': Inventory(3).load(v.get('slots', [])), 'burn': float(v.get('burn', 0)),
                              'burn_max': float(v.get('burn_max', 1)), 'prog': float(v.get('prog', 0))}
                          for k, v in d.get('kilns', {}).items()}
            self.waystones = dict(d.get('waystones', {}))
            self.attune = list(d.get('attune', []))
            self.achieved = list(d.get('achieved', []))
        self.world = World(self.seed, storage, app.renderer, app.pool, view_distance, far_distance,
                          gen_settings=self.gen_settings)
        self.sim = Simulation(self.world, self.seed & 0xFFFF)
        self.sim.on_tree = self._grow_tree
        self.world.on_chunk_loaded = self._chunk_loaded
        if not hasattr(self, 'waystones'):
            self.waystones = {}
        if not hasattr(self, 'attune'):
            self.attune = []
        if not hasattr(self, 'achieved'):
            self.achieved = []
        if not hasattr(self, 'tutorial'):
            self.tutorial = bool(getattr(self.gen, 'tutorial', False))
        self.apply_abilities()
        self.apply_attune()
        self.apply_dev()
        # path unlocks after hooks exist; polled once world is ready
        self.ready = False
        self.target = self.target_prev = None
        self.target_name = ''
        self.target_mob = None
        self.cooldown = 0.0
        self.mining = None                       # (cell, progress 0-1, total secs)
        self.mine_sound = 0.0
        self.swing = 0.0
        self.eat_t = 0.0
        self.particles = np.zeros((0, 12))      # x y z vx vy vz r g b life size homing
        self.motes = []
        self.npcs = []
        self.talk = None
        self.fishing = None
        self._fish_arm = True
        self.jellies = []
        self.mobs = []
        self.drops = []
        self.toasts = []
        self.autosave = C.AUTOSAVE
        self.walk = 0.0
        self.step_acc = 0.0
        self.carry = 0.0
        self.tide_rush = 0.0
        self.last_tide_name = TIDE.name(self.phase)
        self.spire_cache_t = 0.0
        self.nearest_spire = None
        self.beams = []
        self.time = 0.0
        self.hold = False
        self.hurt_flash = 0.0
        self.food_t = 0.0
        self.regen_t = 0.0
        self.path_t = 1.0
        self.mob_t = 0.0
        self.dead = False
        self.sleeping = None
        self.pos1 = self.pos2 = None
        self.undo = []
        self.cursor = None                       # item held on the mouse in menus
        if self.new_sky:
            if self.dev:
                self.toast('Welcome to ' + self.name, 'Dreamer sky: you can fly (F) and build freely. Middle-click removes an item. F5 cycles the camera. F7 opens the admin panel.')
            else:
                self.toast('Welcome to ' + self.name, 'Hold left click on a tree to gather wood. Press E for your backpack.')
        self.save()

    # ------------------------------------------------------------------ helpers
    def apply_abilities(self):
        n = len(self.awakened) if not self.dev else 3
        self.player.can_glide = n >= 1
        self.player.can_updraft = n >= 2
        self.can_tidecall = n >= 3

    def apply_dev(self):
        p = self.player
        p.dev_ghost = self.dev
        if not self.dev:
            p.drifting = False
            p.noclip = False
        self.apply_abilities()

    def set_dev(self, on):
        self.dev = on
        if on:
            self.player.drifting = True
            self.player.vy = 0
            self.hp, self.food = MAX_HP, MAX_FOOD
        self.apply_dev()
        self.toast('Dev mode on' if on else 'Dev mode off',
                   'F fly · N noclip · [ ] speed · F5 camera · F7 admin panel · instant break, endless items' if on else
                   'Back to wandering: mining takes time and things cost items.', 4)

    def apply_attune(self):
        self.player.speed_mul = 1.12 if 'lightfoot' in self.attune else 1.0

    def reach_range(self):
        return C.REACH + (6 if self.dev else 0) + (1.5 if 'reach' in self.attune else 0)

    def _use_waystone(self, q, r, y):
        from . import glimmer as G
        from .ui.systems import WaystoneScreen
        key = G.key(q, r, y)
        rec = self.waystones.get(key)
        if rec is None:
            rec = {'name': self._waystone_name(q, r), 'attuned': False}
            self.waystones[key] = rec
        if not rec['attuned']:
            if self.dev:
                rec['attuned'] = True
            elif self.inv.count(I.GLIMMER.id) < 1:
                self.toast('The waystone is quiet',
                           'It wants 1 Glimmer to remember you. Catch a floating mote: just walk into it.', 4)
                return
            else:
                self.inv.remove(I.GLIMMER.id, 1)
                rec['attuned'] = True
                self.app.audio.play('awaken', 0.55)
                others = sum(1 for k2, v in self.waystones.items() if v.get('attuned') and k2 != key)
                if others:
                    self.toast('The waystone remembers you',
                               'Right-click it again to travel to any attuned waystone. Travel is free.', 4.5)
                else:
                    self.toast('The waystone remembers you',
                               'Attune a second waystone, then right-click either to travel between them. Travel is free.', 5)
                self.check_path()
                return
        self.app.set_screen(WaystoneScreen(key))
        self.app.audio.play('chord', 0.45)

    def _waystone_name(self, q, r):
        names = ('Amber', 'Cinder', 'Hollow', 'Lumen', 'Mire', 'Nimbus',
                 'Pebble', 'Reed', 'Salt', 'Thorn', 'Verdant', 'Wisp')
        base = names[(int(q) * 17 + int(r) * 31) % len(names)] + ' shrine'
        used = {v.get('name') for v in self.waystones.values()}
        if base not in used:
            return base
        n = 2
        while f'{base} {n}' in used:
            n += 1
        return f'{base} {n}'

    def travel_to_waystone(self, key):
        from . import glimmer as G
        rec = self.waystones.get(key)
        if not rec or not rec.get('attuned'):
            return False
        q, r, y = G.parse_key(key)
        cx, cz = center(q, r)
        dest = (cx, (y + 1) * LAYER + 0.05, cz)
        p = self.player
        p.x, p.y, p.z = dest
        p.vx = p.vy = p.vz = 0
        p.last_safe = dest
        self.hold = True
        self.app.audio.play('whoosh', 0.7)
        self.toast('The shrine carries you', rec.get('name', ''), 3)
        return True

    def buy_attunement(self, aid):
        from . import glimmer as G
        rec = next((a for a in G.ATTUNEMENTS if a[0] == aid), None)
        if rec is None or aid in self.attune:
            return False
        _, title, cost, _ = rec
        if not self.dev and self.inv.count(I.GLIMMER.id) < cost:
            need = cost - self.inv.count(I.GLIMMER.id)
            self.toast('Not enough Glimmer', f'{title} costs {cost}. Catch {need} more: walk into floating motes.', 3.5)
            return False
        if not self.dev:
            self.inv.remove(I.GLIMMER.id, cost)
        self.attune.append(aid)
        self.apply_attune()
        self.app.audio.play('awaken', 0.6)
        self.toast(title, 'The Tidewell keeps this gift with the sky.', 3.5)
        self.check_path()
        return True

    def check_path(self, quiet=False):
        from . import achievements as A
        new = A.poll(self)
        if new and not quiet:
            rec = A.BY_ID[new[0]]
            more = f'  (+{len(new) - 1} more)' if len(new) > 1 else ''
            self.toast('Path: ' + rec[1] + more, rec[5].split('.')[0] + '.', 3.8)
            self.app.audio.play('chord', 0.35)
        return new

    def toast(self, text, sub='', secs=5.0):
        self.toasts = [t for t in self.toasts if t[0] != text][-1:]
        self.toasts.append([text, sub, secs])

    @property
    def held(self):
        return self.inv.slots[self.hot]

    @property
    def held_item(self):
        s = self.inv.slots[self.hot]
        return I.get(s[0]) if s else None

    def select(self, i):
        self.hot = i % 9
        self.mining = None
        self.app.audio.play('chord', 0.35)

    def can_dreamer_remove(self):
        return self.mode == 'dreamer' or self.dev

    def remove_inv_slot(self, slots=None, i=None):
        """Dreamer (and dev): take an item out of a slot. Returns True if something was removed."""
        if not self.can_dreamer_remove():
            return False
        if slots is None:
            slots, i = self.inv.slots, self.hot if i is None else i
        if i is None or i < 0 or i >= len(slots) or not slots[i]:
            return False
        slots[i] = None
        return True

    def cycle_hot(self, d):
        self.select(self.hot + d)

    def give(self, iid, n=1, uses=None, quiet=False):
        left = self.inv.add(iid, n, uses)
        if left:
            p = self.player
            self.drops.append(Drop(iid, left, p.x, p.y + 1.0, p.z, uses, vy=2))
        if not quiet:
            self.app.audio.play('mote', 0.35)

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
        if getattr(self, 'tutorial', False):
            from . import tutorial as TUT
            from .inventory import Inventory
            TUT.fill_tutorial_chests(self)
            if not self.npcs:
                self.npcs = TUT.npc_records()
            if self.new_sky:
                self.spawn = (self.player.x, self.player.y, self.player.z)
                self.toast('A quiet lesson island',
                           'Walk with W A S D. Talk to the people you meet — right-click them, or just walk close.', 7)
            for q, r in ((2, 6), (3, 6), (4, 6), (2, 7), (3, 7), (4, 7)):
                self.sim.wake(q, r, TUT.SURF, 4.0)
                self.sim.wake(q, r, TUT.SURF + 1, 3.0)
        self.check_path(quiet=True)
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
        if self.sleeping:
            self._tick_sleep(dt)
            inp = dict(inp, fwd=0, strafe=0, jump=False, jump_pressed=False)
        speed = 1.0 / C.TIDE_LENGTH * (25.0 if self.tide_rush > 0 else 1.0)
        old = self.phase
        if not self.sleeping:
            self.phase = (self.phase + dt * speed) % 1.0
        if self.tide_rush > 0:
            self.tide_rush -= dt
            if (old < 0.5 <= self.phase) or (old > self.phase):
                self.tide_rush = 0
        nm = TIDE.name(self.phase)
        if nm != self.last_tide_name and nm in ('Lighttide', 'Dusktide'):
            critters = self.app.settings['dusk_critters'] and not self.dev
            self.toast(nm + ' rises', ('Gloomlings creep out in the dusk. Stay near light, or rest on a bedroll.'
                                       if critters else 'Crystals and blooms shine in the dusk.')
                       if nm == 'Dusktide' else 'The gloomlings fade. Sprouts and blooms grow in the light.', 4)
            self.app.audio.play('tide', 0.6)
            if random.random() < 0.3:
                self.weather = 'rain' if self.weather == 'clear' else 'clear'
        self.last_tide_name = nm
        if self.dead:
            return
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.swing = max(0.0, self.swing - dt * 3.5)

        if self.carry > 0:
            self.carry -= dt
            if self.carry <= 0.6 and self.carry + dt > 0.6:
                p.x, p.y, p.z = self._sky_drop(*p.last_safe)
                p.vx = p.vy = p.vz = 0
            inp = dict(inp, fwd=0, strafe=0, jump=False, jump_pressed=False)
        if self.hold:
            if self.world.ready_at(p.x, p.z) and not self.world.dirty:
                self.hold = False
            inp = dict(inp, fwd=0, strafe=0, jump=False, jump_pressed=False)
            p.vy = 0
        else:
            p.update(dt, self.world, inp['fwd'], inp['strafe'], inp['jump'], inp['jump_pressed'], inp['down'], inp['hurry'],
                     crouch=inp.get('crouch', False))
        if p.bounced:
            self.app.audio.play('bounce', 0.8)
        if p.landed:
            self.app.audio.play('step_soft', 0.7)
            if p.landed > 13.5 and not p.in_water:
                self.damage((p.landed - 13.5) * 0.9 + 1, 'fall')
            p.landed = 0
        if p.y < CLOUD_SEA * LAYER - 2 and self.carry <= 0 and not p.noclip:
            self.carry = 1.6
            self.app.audio.play('whoosh', 0.8)
            n = int(self.stats.get('cloud_rescues', 0))
            self.stats['cloud_rescues'] = n + 1
            if n == 0:
                self.toast('The clouds carry you back',
                           'Watch the edge next time — a longer fall will sting.', 4.0)
            else:
                self.toast('The clouds carry you back', 'They are gentle, but it still stings a little.', 3.5)
                if not self.dev:
                    self.hp = max(1.0, self.hp - 3)
        # footsteps
        moving = math.hypot(p.vx, p.vz)
        self.edge_warn = max(0.0, getattr(self, 'edge_warn', 0.0) - dt)
        if p.on_ground and moving > 0.8 and not p.drifting and not p.noclip:
            a = math.radians(p.yaw)
            ax, az = p.x + math.sin(a) * 1.7, p.z - math.cos(a) * 1.7
            if not any(solid_at(self.world, ax, p.y - LAYER * k - 0.01, az) for k in (1, 2, 3, 4)):
                self.edge_warn = 1.15
        if p.on_ground and moving > 0.5:
            self.walk += moving * dt
            self.step_acc += moving * dt
            if self.step_acc > 2.1:
                self.step_acc = 0
                g = p.ground_material(self.world)
                snd = MT.SOUND[g] if g > 0 else None
                if snd:
                    self.app.audio.play('step_' + snd, 0.5)
        self._survival(dt, inp, moving)
        # aim: blocks and creatures
        ex, ey, ez = p.eye
        fx, fy, fz = forward_vector(p.yaw, p.pitch)
        reach = self.reach_range()
        self.target, self.target_prev = raycast(self.world, ex, ey, ez, fx, fy, fz, reach, skip_water=True)
        bd = 1e9
        if self.target:
            q, r, y = self.target
            cx_, cz_ = center(q, r)
            bd = math.sqrt((cx_ - ex) ** 2 + ((y + 0.5) * LAYER - ey) ** 2 + (cz_ - ez) ** 2) - 0.5
        self.target_mob = None
        for mob in self.mobs:
            t = mob.hit_test(ex, ey, ez, fx, fy, fz, 4.5)
            if t is not None and t < bd:
                bd = t
                self.target_mob = mob
        if self.target_mob:
            self.target = self.target_prev = None
        self.target_npc = None
        for npc in getattr(self, 'npcs', []):
            tnp = self._npc_hit(npc, ex, ey, ez, fx, fy, fz, 5.0)
            if tnp is not None and tnp < bd:
                bd = tnp
                self.target_npc = npc
        if self.target_npc:
            self.target = self.target_prev = None
            self.target_mob = None
        self.target_name = ''
        if self.target_npc:
            self.target_name = self.target_npc['name']
        elif self.target_mob:
            self.target_name = self.target_mob.kind.capitalize()
        elif self.target:
            m = self.world.get(*self.target)
            if m > 0:
                self.target_name = MT.NAMES[m]
        self.cooldown -= dt
        self.eat_t = max(0.0, self.eat_t - dt)
        if not inp.get('shape'):
            self._fish_arm = True
        it_now = self.held_item
        if self.fishing and (not it_now or it_now.kind != 'rod'):
            self.fishing = None
        self._update_fishing(dt)
        if self.carry <= 0:
            if inp.get('gather'):
                if getattr(self, 'target_npc', None):
                    self.mining = None
                elif self.target_mob:
                    if self.cooldown <= 0:
                        self.attack(self.target_mob)
                        self.cooldown = 0.45
                    self.mining = None
                else:
                    self.mine(dt)
            else:
                self.mining = None
            if inp.get('shape') and self.cooldown <= 0:
                if self.use():
                    self.cooldown = 0.25
                else:
                    self.cooldown = 0.1
        self.sim.step(dt, TIDE.dusk_amount(self.phase))
        self.world.update(p.x, p.z)
        self._update_mobs(dt)
        self._update_drops(dt)
        self._update_kilns(dt)
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
        self.path_t = getattr(self, 'path_t', 0) - dt
        if self.path_t <= 0:
            self.path_t = 1.6
            self.check_path()

    # ------------------------------------------------------------------ health and food
    def _survival(self, dt, inp, moving):
        if self.dev:
            self.hp, self.food = MAX_HP, MAX_FOOD
            return
        drain = 1 / 50.0 + (1 / 30.0 if inp.get('hurry') and moving > 0.5 else 0)
        if 'breath' in getattr(self, 'attune', []):
            drain *= 0.7
        self.food = max(0.0, self.food - drain * dt * 0.5)
        self.regen_t += dt
        if self.regen_t > 3.0:
            self.regen_t = 0
            if self.food >= 14 and self.hp < MAX_HP:
                extra = 1 if 'brightwake' in getattr(self, 'attune', []) else 0
                self.hp = min(MAX_HP, self.hp + 1 + extra)
                self.food = max(0, self.food - 0.4)
            elif self.food <= 0 and self.hp > 2:
                self.hp -= 1
                self.hurt_flash = 0.3
                self.toast('You are hungry', 'Eat something: berries, roast hopmeat, pie...', 3)

    def damage(self, amount, why=''):
        if self.dev or self.dead or amount <= 0:
            return
        self.hp -= amount
        self.hurt_flash = 0.45
        self.app.audio.play('gather_soft', 0.9)
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.mining = None
            self.app.on_faded(why)

    def _sky_drop(self, x, y, z):
        """Return a position high above land at (x, z), so falling off the world is a drop-in, not a hard snap."""
        q, r = cell_at(x, z)
        top = self.world.column_top(q, r)
        if top is None or top < 0:
            top = max(0, int(y / LAYER))
        return x, (top + C.FALL_RESPAWN_LAYERS) * LAYER + 0.01, z

    def respawn(self):
        p = self.player
        if self.spawn:
            p.x, p.y, p.z = self._sky_drop(*self.spawn)
        else:
            p.x, p.y, p.z = self._sky_drop(*p.last_safe)
        p.vx = p.vy = p.vz = 0
        self.hp = MAX_HP
        self.food = max(self.food, 12)
        self.dead = False
        self.hold = True
        self.mobs = [m for m in self.mobs if not m.hostile]
        self.toast('You wake again', 'Your things are still with you.', 3)

    def eat(self, it):
        if self.food >= MAX_FOOD - 0.5 and not self.dev:
            self.toast('You are full', '', 1.5)
            return False
        self.food = min(MAX_FOOD, self.food + it.food)
        self.hp = min(MAX_HP, self.hp + it.food * 0.25)
        if not self.dev:
            self.inv.take_from(self.hot)
        self.app.audio.play('chord', 0.6)
        p = self.player
        ex, ey, ez = p.eye
        fx, fy, fz = forward_vector(p.yaw, p.pitch)
        self._spawn(ex + fx * 0.6, ey - 0.2, ez + fz * 0.6, it.color, 8)
        return True

    # ------------------------------------------------------------------ mining
    def mine(self, dt):
        if not self.target:
            self.mining = None
            return
        q, r, y = self.target
        m = self.world.get(q, r, y)
        if m <= 0 or m in I.UNBREAKABLE:
            if m in (M['dormant_spire'], M['awake_spire']) and self.cooldown <= 0:
                self.toast('The spire will not move', 'It is older than the islands.', 2.5)
                self.cooldown = 1.0
            self.mining = None
            return
        it = self.held_item
        secs, drops = I.mine_time(m, it)
        if self.dev:
            if self.cooldown > 0:
                return
            self.break_cell(q, r, y, m, drop=False)
            self.cooldown = 0.18
            return
        if self.mining is None or self.mining[0] != self.target:
            self.mining = [self.target, 0.0, secs, drops]
        self.mining[1] += dt / secs
        self.swing = 1.0
        self.mine_sound -= dt
        cx, cz = center(q, r)
        if self.mine_sound <= 0:
            self.mine_sound = 0.28
            snd = MT.SOUND[m] or 'stone'
            self.app.audio.play('step_' + snd, 0.6)
            self._spawn(cx, (y + 0.7) * LAYER, cz, MT.TOP[m], 3, speed=1.5)
        if self.mining[1] >= 1.0:
            self.break_cell(q, r, y, m, drop=drops)
            if not drops and MT.NAMES[m].endswith('Ore') or (not drops and I.HARD.get(MT.NAMES[m].lower().replace(' ', '_'), (0, 0, 0))[2] > 0):
                self.toast('It crumbles to nothing', 'You need a better pick to collect this.', 2.5)
            self.mining = None
            self._wear_tool()

    def _wear_tool(self):
        s = self.held
        it = self.held_item
        if not s or not it or it.kind not in ('tool', 'rod', 'hoe') or self.dev or not it.uses:
            return
        s[2] -= 1
        if s[2] <= 0:
            self.inv.slots[self.hot] = None
            self.toast(f'Your {it.name} wore out', '', 2.5)
            self.app.audio.play('gather_stone', 0.8)

    def break_cell(self, q, r, y, m, drop=True):
        harvest_meta = self.world.get_meta(q, r, y) if m in getattr(MT, 'CROP_GROW', ()) else None
        other = None
        if m == M['door']:
            mt = self.world.get_meta(q, r, y)
            other = (q, r, y - 1 if (mt & 16) else y + 1)
        self.world.set(q, r, y, 0, 0, now=True)
        if other and self.world.get(*other) == M['door']:
            self.world.set(*other, 0, 0, now=True)
        if m in MT.WOODS or m == M['canopy']:
            self.sim.wake_leaves(q, r, y, 0.35)
        above = self.world.get(q, r, y + 1)
        cx, cz = center(q, r)
        if above > 0 and MT.IS_DECO[above] and above in NEEDS_GROUND:
            self.world.set(q, r, y + 1, 0, 0, now=True)
            if drop:
                for iid, n in I.drops_for(above):
                    self.drops.append(Drop(iid, n, cx, (y + 1.3) * LAYER, cz))
        key = f'{q},{r},{y}'
        if key in self.chests:
            for s in self.chests.pop(key).slots:
                if s:
                    self.drops.append(Drop(s[0], s[1], cx, (y + 0.5) * LAYER, cz, s[2]))
        if key in self.kilns:
            for s in self.kilns.pop(key)['slots'].slots:
                if s:
                    self.drops.append(Drop(s[0], s[1], cx, (y + 0.5) * LAYER, cz, s[2]))
        if self.spawn and m == M['bedroll']:
            sq, sr = cell_at(self.spawn[0], self.spawn[2])
            if (sq, sr) == (q, r):
                self.spawn = None
        if drop:
            if harvest_meta is not None:
                from . import farming as F
                drops = F.harvest(m, harvest_meta)
                if harvest_meta >= F.STAGES - 1:
                    self.stats['farmed'] = self.stats.get('farmed', 0) + 1
                    self.check_path()
            else:
                drops = I.drops_for(m)
            for iid, n in drops:
                self.drops.append(Drop(iid, n, cx, (y + 0.3) * LAYER, cz))
        self.stats['mined'] += 1
        self.sim.wake_around(q, r, y)
        snd = MT.SOUND[m] or 'stone'
        self.app.audio.play('gather_' + snd, 0.8)
        self._spawn(cx, (y + 0.5) * LAYER, cz, MT.TOP[m], 14, homing=False, speed=2.5)

    def attack(self, mob):
        it = self.held_item
        dmg = it.damage if it and it.kind == 'tool' else 1.0
        if self.dev:
            dmg = 999
        mob.hp -= dmg
        mob.hurt = 0.35
        mob.panic = 5.0
        p = self.player
        dx, dz = mob.x - p.x, mob.z - p.z
        d = math.hypot(dx, dz) or 1
        mob.vx += dx / d * 5
        mob.vz += dz / d * 5
        mob.vy = 4.5
        self.swing = 1.0
        self.app.audio.play('gather_soft', 0.8)
        self._spawn(mob.x, mob.y + 0.6, mob.z, (1, 0.8, 0.8), 6)
        if it and it.kind == 'tool' and it.tool[0] == 'blade':
            self._wear_tool()
        if mob.hp <= 0:
            self.kill(mob)

    def kill(self, mob, drops=True):
        mob.dead = True
        self._spawn(mob.x, mob.y + 0.5, mob.z, (0.9, 0.85, 1.0), 20, speed=3)
        self.app.audio.play('whoosh', 0.5)
        if drops:
            for iid, lo, hi in mob.drops:
                n = random.randint(lo, hi)
                if n:
                    self.drops.append(Drop(iid, n, mob.x, mob.y + 0.5, mob.z))

    # ------------------------------------------------------------------ placing and using
    def use(self):
        p = self.player
        it = self.held_item
        if getattr(self, 'target_npc', None):
            return self.talk_npc(self.target_npc)
        if self.fishing:
            return self.use_rod()
        if it and it.kind == 'rod':
            return self.use_rod()
        if it and it.kind == 'hoe':
            return self.use_hoe()
        if it and it.kind == 'seed':
            return self.use_seed()
        # use a block you're looking at
        if self.target:
            q, r, y = self.target
            m = self.world.get(q, r, y)
            if m in USE_BLOCKS and not self.app.keys_down_shift():
                return self.use_block(q, r, y, m)
        if it and it.kind == 'food':
            if self.eat_t <= 0 and self.eat(it):
                self.eat_t = 0.6
                return True
            return False
        if it and it.kind == 'pail':
            return self.use_pail(it)
        if not it or it.kind != 'block' or not self.target_prev:
            return False
        q, r, y = self.target_prev
        cur = self.world.get(q, r, y)
        if cur not in (0, M['water'], M['petals']) or y >= C.LAYERS - 1 or y < 1:
            return False
        mat = it.block
        below = self.world.get(q, r, y - 1)
        if mat in NEEDS_GROUND and not (below > 0 and MT.SOLID[below]):
            self.toast(MT.NAMES[mat] + ' needs solid ground beneath it', '', 2.0)
            return False
        if (MT.SOLID[mat] or mat == M['door']) and not p.noclip:
            lo, hi = math.floor((p.y + 0.01) / LAYER), math.floor((p.y + p.body_height()) / LAYER)
            if lo <= y <= hi and (q, r) in p._columns(p.x, p.z):
                return False
            for mob in self.mobs:
                if cell_at(mob.x, mob.z) == (q, r) and math.floor(mob.y / LAYER) <= y <= math.floor((mob.y + mob.height) / LAYER):
                    return False
        meta0 = INITIAL_META.get(mat, 0)
        if mat in (M['tinker_bench'], M['kiln'], M['chest'], M['door'], M['ladder'], M['waystone'], M['tidewell']):
            # face the front (drawer, firebox, latch, door, rungs) towards you
            from .hexgrid import DIR_NORMALS
            cx_, cz_ = center(q, r)
            vx, vz = p.x - cx_, p.z - cz_
            meta0 = max(range(6), key=lambda d: DIR_NORMALS[d][0] * vx + DIR_NORMALS[d][1] * vz)
            if mat == M['ladder']:
                meta0 = (meta0 + 3) % 6          # hang against the wall, rungs face you
        if mat == M['door']:
            if y + 1 >= C.LAYERS or self.world.get(q, r, y + 1) not in (0, M['water'], M['petals']):
                self.toast('The doorway is blocked', 'Doors need two empty cells, one above the other.', 2.0)
                return False
        if mat == M['ladder']:
            from .hexgrid import DIRS as _DIRS
            dq, dr = _DIRS[meta0 % 6]
            # the face the ladder hangs on is the one toward the block you clicked, i.e. opposite the look
            back = self.world.get(q - dq, r - dr, y)
            if not (back > 0 and MT.SOLID[back]):
                # try the clicked face: meta already faces the player, so the wall is behind the ladder
                pass
        self.world.set(q, r, y, mat, meta0, now=True)
        if mat == M['door']:
            self.world.set(q, r, y + 1, mat, meta0 | 16, now=True)
        if not self.dev:
            self.inv.take_from(self.hot)
        self.stats['placed'] += 1
        if mat in (M['door'], M['ladder']):
            self.stats['doors'] = self.stats.get('doors', 0) + 1
        self.check_path()
        if mat in LIVING:
            self.sim.wake(q, r, y, 0.5)
        self.sim.wake_around(q, r, y)
        self.app.audio.play('shape', 0.7)
        self.swing = 0.6
        cx, cz = center(q, r)
        self._spawn(cx, (y + 0.5) * LAYER, cz, MT.TOP[mat], 8, homing=False)
        if mat == M['chest']:
            self.chests[f'{q},{r},{y}'] = Inventory(27)
        elif mat == M['kiln']:
            self.kilns[f'{q},{r},{y}'] = {'slots': Inventory(3), 'burn': 0.0, 'burn_max': 1.0, 'prog': 0.0}
        self._check_spires(q, r, y)
        return True

    def _toggle_door(self, q, r, y):
        mt = self.world.get_meta(q, r, y)
        opened = (mt & 8) == 0
        other = (q, r, y - 1 if (mt & 16) else y + 1)
        # don't open into a solid block
        if opened:
            from .materials import is_blocking
            # the door stays in its cell; opening only changes collision of this cell
            pass
        new = (mt ^ 8)
        self.world.set_meta(q, r, y, new)
        self.world.dirty.add((q // C.CHUNK, r // C.CHUNK))
        if self.world.get(*other) == M['door']:
            omt = self.world.get_meta(*other)
            self.world.set_meta(*other, (omt & ~8) | (new & 8) | (omt & 16))
            self.world.dirty.add((other[0] // C.CHUNK, other[1] // C.CHUNK))
        self.app.audio.play('step_wood', 0.7)
        self.stats['doors'] = self.stats.get('doors', 0) + 1
        self.check_path()

    def use_block(self, q, r, y, m):
        from .ui import inventory_ui as IU
        key = f'{q},{r},{y}'
        if m == M['tinker_bench']:
            self.stats['tinker'] = self.stats.get('tinker', 0) + 1
            self.check_path()
            self.app.set_screen(IU.CraftScreen(3))
        elif m == M['chest']:
            if key not in self.chests:
                inv = Inventory(27)
                table = (self.world.get_meta(q, r, y) >> 3) & 15
                if table:
                    from .structures import fill_chest
                    fill_chest(inv, table, getattr(self, 'seed', 0), q, r, y)
                self.chests[key] = inv
            self.app.set_screen(IU.ChestScreen(self.chests[key]))
            self.app.audio.play('step_wood', 0.8)
        elif m == M['kiln']:
            if key not in self.kilns:
                self.kilns[key] = {'slots': Inventory(3), 'burn': 0.0, 'burn_max': 1.0, 'prog': 0.0}
            self.app.set_screen(IU.KilnScreen(self.kilns[key]))
        elif m == M['door']:
            self._toggle_door(q, r, y)
        elif m == M['waystone']:
            self._use_waystone(q, r, y)
        elif m == M['tidewell']:
            from .ui.systems import TidewellScreen
            self.app.set_screen(TidewellScreen())
            self.app.audio.play('chord', 0.5)
        elif m == M['bedroll']:
            cx, cz = center(q, r)
            self.spawn = (cx, (y + 1) * LAYER + 0.01, cz)
            dusk = TIDE.dusk_amount(self.phase)
            if dusk > 0.4:
                hostile = [mob for mob in self.mobs if mob.hostile and math.hypot(mob.x - cx, mob.z - cz) < 10]
                if hostile:
                    self.toast('You can\'t rest now', 'Gloomlings are close by.', 2.5)
                else:
                    self.sleeping = {'stage': 'out', 't': 0.0}
                    self.mobs = [mob for mob in self.mobs if not mob.hostile]
                    self.toast('You rest until the light returns', 'You will wake here from now on.', 4)
                    self.app.audio.play('tide', 0.8)
            else:
                self.toast('Waking spot set', 'Rest here during the dusk to skip to the light.', 3)
        return True




    def _tick_sleep(self, dt):
        """Fade to black, then ease the tide through a dawn into the light."""
        s = self.sleeping
        s['t'] += dt
        if s['stage'] == 'out':
            if s['t'] >= 1.0:
                s['stage'] = 'dawn'
                s['t'] = 0.0
                self.phase = 0.82
        elif s['stage'] == 'dawn':
            # 0.82 -> 1.0 over ~2 seconds (turning to light, then the peak of lighttide)
            self.phase = min(1.0, 0.82 + 0.18 * min(1.0, s['t'] / 2.0))
            if self.phase >= 1.0:
                self.phase = 0.0
                self.sleeping = None
                self.last_tide_name = TIDE.name(self.phase)

    def sleep_fade(self):
        """0..1 black overlay while resting."""
        s = self.sleeping
        if not s:
            return 0.0
        if s['stage'] == 'out':
            return min(1.0, s['t'] / 1.0)
        # hold black briefly, then lift as dawn comes in
        if s['t'] < 0.25:
            return 1.0
        return max(0.0, 1.0 - (s['t'] - 0.25) / 1.75)

    def _npc_hit(self, npc, ox, oy, oz, dx, dy, dz, reach):
        cx, cy, cz = npc['x'], npc['y'] + 0.7, npc['z']
        rad = 0.55
        lx, ly, lz = cx - ox, cy - oy, cz - oz
        t = lx * dx + ly * dy + lz * dz
        if t < 0 or t > reach + rad:
            return None
        d2 = lx * lx + ly * ly + lz * lz - t * t
        if d2 > rad * rad:
            return None
        return max(0.0, t - math.sqrt(max(0.0, rad * rad - d2)))

    def talk_npc(self, npc):
        lines = npc.get('lines') or ()
        if not lines:
            return False
        npc['line'] = (npc.get('line', 0) + 1) % len(lines) if self.talk == npc['name'] else 0
        self.talk = npc['name']
        self._frame_npc(npc)
        self.app.audio.play('chord', 0.25)
        return True

    def _frame_npc(self, npc):
        """Stand a few cells back on open ground, looking at the NPC, not inside them or a trunk."""
        from .materials import support_top
        p = self.player
        tx, ty, tz = npc['x'], npc['y'] + 0.95, npc['z']
        dx, dz = p.x - tx, p.z - tz
        dist = math.hypot(dx, dz)
        if dist < 0.25:
            a0 = math.radians(p.yaw)
            dx, dz = -math.sin(a0), math.cos(a0)
            dist = 1.0
        ux, uz = dx / dist, dz / dist
        placed = False
        for ang in (0, 50, -50, 90, -90, 130, -130, 180):
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            rx, rz = ux * ca - uz * sa, ux * sa + uz * ca
            for d in (3.1, 2.5, 3.8, 2.1):
                nx, nz = tx + rx * d, tz + rz * d
                q, r = cell_at(nx, nz)
                top = support_top(self.world, q, r, npc['y'] + LAYER * 2.4, LAYER)
                if top is None or abs(top - npc['y']) > LAYER * 2.6:
                    continue
                if solid_at(self.world, nx, top + 0.9, nz) or solid_at(self.world, nx, top + 1.6, nz):
                    continue
                if math.hypot(nx - tx, nz - tz) < 1.55:
                    continue
                p.x, p.z = nx, nz
                p.y = top + 0.001
                p.vx = p.vy = p.vz = 0.0
                p.drifting = False
                p.noclip = False
                placed = True
                break
            if placed:
                break
        ex, ey, ez = p.eye
        p.yaw = math.degrees(math.atan2(tx - ex, -(tz - ez))) % 360
        p.pitch = math.degrees(math.atan2(ty - ey, math.hypot(tx - ex, tz - ez)))

    def _npc_dist(self, npc):
        p = self.player
        return math.sqrt((npc['x'] - p.x) ** 2 + (npc['z'] - p.z) ** 2 + (npc['y'] - p.y) ** 2)

    def closest_npc(self, reach=5.5):
        """The closest lesson NPC within reach, or None."""
        if not getattr(self, 'npcs', None):
            return None
        best, bd = None, reach
        for npc in self.npcs:
            d = self._npc_dist(npc)
            if d < bd:
                best, bd = npc, d
        return best

    def nearby_talk(self):
        """Active tutorial dialog, only after a right-click, and only while still close."""
        if not getattr(self, 'talk', None) or not getattr(self, 'npcs', None):
            return None
        for npc in self.npcs:
            if npc.get('name') == self.talk:
                if self._npc_dist(npc) < 6.5:
                    return npc
                self.talk = None
                return None
        self.talk = None
        return None

    def use_hoe(self):
        from . import farming as F
        if not self.target:
            self.toast('Till some soil', 'Right-click turf or loam with the hoe.', 2.2)
            return False
        q, r, y = self.target
        m = self.world.get(q, r, y)
        if m not in F.TILLABLE:
            self.toast('The hoe needs soil', 'Turf, loam, packed earth or heather will do.', 2.2)
            return False
        self.world.set(q, r, y, M['farmland'], 0, now=True)
        self.stats['tilled'] = self.stats.get('tilled', 0) + 1
        self.sim.wake(q, r, y, 8.0)
        self._wear_tool()
        self.swing = 0.45
        self.app.audio.play('gather_soft', 0.7)
        # first turning of turf sometimes turns up grain seeds
        if m == M['turf'] and random.random() < 0.28:
            self.give(I.GRAIN_SEEDS.id, 1)
            self.toast('Grain seeds in the soil', 'Plant them on the tilled bed.', 3.0)
        elif m == M['loam'] and random.random() < 0.12:
            self.give(I.ROOT_SEEDS.id, 1)
            self.toast('Root seeds in the soil', 'Plant them on the tilled bed.', 3.0)
        else:
            self.toast('Tilled soil', 'Plant seeds here. A nearby pool helps them grow.', 2.5)
        cx, cz = center(q, r)
        self._spawn(cx, (y + 1) * LAYER, cz, (0.52, 0.38, 0.26), 6, homing=False)
        return True

    def use_seed(self):
        from . import farming as F
        it = self.held_item
        crop = F.plant_of(it.id) if it else None
        if crop is None:
            return False
        cell = None
        if self.target and self.world.get(*self.target) == M['farmland']:
            q, r, y = self.target
            cell = (q, r, y + 1)
        elif self.target_prev:
            q, r, y = self.target_prev
            if self.world.get(q, r, y) in (0, M['petals']) and self.world.get(q, r, y - 1) == M['farmland']:
                cell = (q, r, y)
        if cell is None:
            self.toast('Plant on tilled soil', 'Till turf or loam with a hoe first.', 2.5)
            return False
        q, r, y = cell
        if y >= C.LAYERS - 1 or self.world.get(q, r, y) not in (0, M['petals']):
            self.toast('The bed is not empty', '', 2.0)
            return False
        self.world.set(q, r, y, crop, 0, now=True)
        self.sim.wake(q, r, y, 4.0)
        if not self.dev:
            self.inv.take_from(self.hot)
        self.swing = 0.4
        self.app.audio.play('shape', 0.5)
        return True

    def use_rod(self):
        from . import fishing as F
        if self.fishing:
            if not self._fish_arm:
                return True
            self._fish_arm = False
            st = self.fishing
            if st['state'] == 'bite':
                self._land_catch()
            else:
                self.fishing = None
                self.toast('The fish got away', 'Wait for the bobber to dip, then reel.', 2.5)
                self.app.audio.play('gather_soft', 0.5)
            return True
        # fresh cast
        if not self._fish_arm:
            return True
        hit = self._water_ahead()
        if not hit:
            self.toast('Cast into a pool', 'Right-click still water with the rod.', 2.5)
            return False
        q, r, y = hit
        cx, cz = center(q, r)
        wait, window = F.start_wait()
        realm = self.world.realm_at(q, r) or 0
        self.fishing = {'state': 'wait', 't': 0.0, 'wait': wait, 'window': window,
                        'pos': (cx, (y + 0.92) * LAYER, cz), 'realm': realm, 'cell': (q, r, y)}
        self._fish_arm = False
        self.swing = 0.45
        self.app.audio.play('gather_water', 0.55)
        return True

    def _water_ahead(self):
        p = self.player
        ex, ey, ez = p.eye
        fx, fy, fz = forward_vector(p.yaw, p.pitch)
        hit, _prev = raycast(self.world, ex, ey, ez, fx, fy, fz, self.reach_range(), skip_water=False)
        if hit and self.world.get(*hit) == M['water']:
            return hit
        # standing at the rim: the cell you would place into, or just below the look
        if self.target_prev:
            q, r, y = self.target_prev
            if self.world.get(q, r, y) == M['water']:
                return (q, r, y)
            if self.world.get(q, r, y - 1) == M['water']:
                return (q, r, y - 1)
        return None

    def _update_fishing(self, dt):
        st = self.fishing
        if not st:
            return
        st['t'] += dt
        x, y, z = st['pos']
        # line snaps if you wander off
        if math.hypot(self.player.x - x, self.player.z - z) > 12:
            self.fishing = None
            self.toast('The line snapped', 'Stay close to the bobber.', 2.5)
            return
        if st['state'] == 'wait' and st['t'] >= st['wait']:
            st['state'] = 'bite'
            st['t'] = 0.0
            self.app.audio.play('mote', 0.45)
        elif st['state'] == 'bite' and st['t'] >= st['window']:
            self.fishing = None
            self.toast('It got away', 'Reel as soon as the bobber dips.', 2.5)

    def _land_catch(self):
        from . import fishing as F
        st = self.fishing
        self.fishing = None
        iid, n, kind = F.roll_catch(st['realm'], self.phase)
        it = I.get(iid)
        self.give(iid, n)
        self.stats['fished'] = self.stats.get('fished', 0) + 1
        self.check_path()
        self._wear_tool()
        name = it.name if it else 'something'
        if kind == 'treasure':
            self.toast(f'Treasure on the line', f'You pulled up {name}.', 3.5)
            self.app.audio.play('awaken', 0.4)
        else:
            self.toast(f'You caught a {name}', 'Cook it in a kiln for a proper meal.', 3.2)
            self.app.audio.play('gather_soft', 0.8)
        x, y, z = st['pos']
        col = it.color if it else (0.7, 0.8, 0.9)
        self._spawn(x, y + 0.3, z, col, 8, homing=True)

    def use_pail(self, it):
        ex, ey, ez = self.player.eye
        fx, fy, fz = forward_vector(self.player.yaw, self.player.pitch)
        if it.id == I.PAIL.id:
            hit, prev = raycast(self.world, ex, ey, ez, fx, fy, fz, self.reach_range())
            if hit and self.world.get(*hit) == M['water']:
                self.world.set(*hit, 0, 0, now=True)
                self.sim.wake_around(*hit)
                if not self.dev:
                    self.inv.take_from(self.hot)
                self.give(I.PAIL_FULL.id, 1, quiet=True)
                self.app.audio.play('gather_water', 0.8)
                return True
            return False
        if self.target_prev:
            q, r, y = self.target_prev
            if self.world.get(q, r, y) in (0, M['petals']):
                self.world.set(q, r, y, M['water'], 7, now=True)
                self.sim.wake(q, r, y, 0.3)
                if not self.dev:
                    self.inv.slots[self.hot] = [I.PAIL.id, 1, 0]
                self.app.audio.play('gather_water', 0.8)
                self._check_spires(q, r, y)
                return True
        return False

    def craft_take(self, grid_slots, result):
        """Consume one of each ingredient in a crafting grid."""
        for i, s in enumerate(grid_slots):
            if s:
                s[1] -= 1
                if s[1] <= 0:
                    grid_slots[i] = None
        self.stats['crafted'] += 1
        self.check_path()

    # ------------------------------------------------------------------ creatures and drops
    def _update_mobs(self, dt):
        p = self.player
        dusk = TIDE.dusk_amount(self.phase)
        peaceful = not self.app.settings['dusk_critters']
        self.mob_t -= dt
        if self.mob_t <= 0 and self.app.settings['creatures']:
            self.mob_t = 1.0
            passive = [m for m in self.mobs if not m.hostile]
            hostile = [m for m in self.mobs if m.hostile]
            if not getattr(self, 'tutorial', False):
                ground = [m for m in passive if m.kind not in FLYING]
                if len(ground) < 12:
                    self._try_spawn(False)
                self._try_spawn_flyers(dusk)
            if dusk > 0.55 and not peaceful and not getattr(self, 'tutorial', False) and len(hostile) < 6:
                self._try_spawn(True)
        self._mob_tick = getattr(self, '_mob_tick', 0) + 1
        for i, mob in enumerate(self.mobs):
            # far creatures think less often (spread over frames)
            if abs(mob.x - p.x) + abs(mob.z - p.z) > 36:
                mob._acc = getattr(mob, '_acc', 0.0) + dt
                if (i + self._mob_tick) % 4:
                    continue
                mdt, mob._acc = min(mob._acc, 0.25), 0.0
            else:
                mdt = dt
            mob.update(mdt, self.world, p, dusk, peaceful)
            if mob.hostile and not mob.dead and mob.fade > 0.5 and not self.dev:
                d = math.hypot(mob.x - p.x, mob.z - p.z)
                if d < 0.75 + mob.radius * mob.scale and abs(mob.y - p.y) < 1.4 and mob.attack_cd <= 0:
                    mob.attack_cd = 1.5
                    self.damage(3 if mob.kind == 'brute' else 1, mob.kind)
                    k = 6.0 / max(d, 0.1)
                    p.knock = ((p.x - mob.x) * k, (p.z - mob.z) * k)
                    p.vy = 5.0
            if mob.kind == 'pebblebeak':
                mob.lay -= dt
                if mob.lay <= 0:
                    mob.lay = random.uniform(80, 220)
                    self.drops.append(Drop(I.EGG.id, 1, mob.x, mob.y + 0.3, mob.z))
        self.mobs = [m for m in self.mobs if not m.dead and
                     math.hypot(m.x - p.x, m.z - p.z) < (140 if m.kind == 'skywhale' else 70)]

    def _try_spawn(self, hostile, kind=None, near=None):
        p = self.player
        for _ in range(6):
            a = random.uniform(0, math.tau)
            d = random.uniform(14, 28) if hostile else random.uniform(18, 40)
            if near:
                d = random.uniform(2, 6)
            x, z = p.x + math.cos(a) * d, p.z + math.sin(a) * d
            spot = spawn_spot(self.world, x, z)
            if not spot:
                continue
            sx, sy, sz, ground = spot
            q, r = cell_at(sx, sz)
            realm = self.world.realm_at(q, r) or 0
            if kind is None:
                if hostile:
                    kind = 'brute' if random.random() < 0.15 else 'gloomling'
                else:
                    if ground not in (M['turf'], M['snow'], M['sand'], M['loam'], M['mossrock']):
                        continue
                    opts = [k for k, rs in PASSIVE_REALMS.items() if realm in rs]
                    if not opts:
                        continue
                    kind = random.choice(opts)
            if hostile and not near:
                # not right next to bright lights
                if any(self.world.get(q + dq, r + dr, math.floor(sy / LAYER) + dy) in (M['glowstick'], M['lantern'], M['lumen_lamp'])
                       for dq, dr in [(0, 0)] + DIRS for dy in (0, 1)):
                    continue
            n = 1 if hostile or near else random.randint(1, 3)
            for k in range(n):
                self.mobs.append(Mob(kind, sx + random.uniform(-0.4, 0.4), sy, sz + random.uniform(-0.4, 0.4)))
            return True
        return False


    def _try_spawn_flyers(self, dusk):
        """A couple of skywhales in the open air, and fairies near flowers.
        1.4.4 also keeps a few sky jellies and cloud rays in the open sky."""
        whales = [m for m in self.mobs if m.kind == 'skywhale']
        fairies = [m for m in self.mobs if m.kind == 'fairy']
        jellies = [m for m in self.mobs if m.kind == 'skyjelly']
        rays = [m for m in self.mobs if m.kind == 'cloudray']
        p = self.player
        if len(whales) < 2:
            for _ in range(4):
                a = random.uniform(0, math.tau)
                d = random.uniform(32, 70)
                x, z = p.x + math.cos(a) * d, p.z + math.sin(a) * d
                q, r = cell_at(x, z)
                top = self.world.column_top(q, r)
                base = ((top + 1) * LAYER) if top is not None else max(p.y, CLOUD_SEA * LAYER + 8)
                y = base + random.uniform(10, 20)
                self.mobs.append(Mob('skywhale', x, y, z))
                break
        if len(jellies) < 3:
            for _ in range(4):
                a = random.uniform(0, math.tau)
                d = random.uniform(16, 42)
                x, z = p.x + math.cos(a) * d, p.z + math.sin(a) * d
                q, r = cell_at(x, z)
                top = self.world.column_top(q, r)
                base = ((top + 1) * LAYER) if top is not None else max(p.y, CLOUD_SEA * LAYER + 8)
                y = base + random.uniform(3, 9)
                self.mobs.append(Mob('skyjelly', x, y, z))
                break
        if len(rays) < 3:
            for _ in range(4):
                a = random.uniform(0, math.tau)
                d = random.uniform(22, 55)
                x, z = p.x + math.cos(a) * d, p.z + math.sin(a) * d
                q, r = cell_at(x, z)
                top = self.world.column_top(q, r)
                base = ((top + 1) * LAYER) if top is not None else max(p.y, CLOUD_SEA * LAYER + 8)
                y = base + random.uniform(6, 14)
                self.mobs.append(Mob('cloudray', x, y, z))
                break
        want_fairies = 6 if dusk > 0.3 else 3
        if len(fairies) < want_fairies:
            # look for a nearby flower, otherwise a grassy column
            for _ in range(8):
                a = random.uniform(0, math.tau)
                d = random.uniform(8, 26)
                x, z = p.x + math.cos(a) * d, p.z + math.sin(a) * d
                q, r = cell_at(x, z)
                top = self.world.column_top(q, r)
                if top is None:
                    continue
                above = self.world.get(q, r, top + 1)
                ground = self.world.get(q, r, top)
                if above not in FLOWER_BLOCKS and ground not in (M['turf'], M['loam'], M['mossrock']):
                    continue
                cx, cz = center(q, r)
                y = (top + 1) * LAYER + 0.4
                self.mobs.append(Mob('fairy', cx + random.uniform(-0.3, 0.3), y, cz + random.uniform(-0.3, 0.3)))
                break

    def _update_drops(self, dt):
        p = self.player
        keep = []
        for dr in self.drops:
            dr.update(dt, self.world)
            dx, dy, dz = p.x - dr.x, (p.y + 0.8) - dr.y, p.z - dr.z
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dr.age > 0.5 and d < 3.2:
                dr.x += dx * min(1, dt * 10)
                dr.y += dy * min(1, dt * 10)
                dr.z += dz * min(1, dt * 10)
                if d < 0.7:
                    left = self.inv.add(dr.iid, dr.count, dr.uses)
                    if left < dr.count:
                        self.app.audio.play('mote', 0.45)
                    if left:
                        dr.count = left
                        keep.append(dr)
                    continue
            if dr.age < 600 and dr.y > CLOUD_SEA * LAYER - 6:
                keep.append(dr)
        self.drops = keep[-300:]

    def _update_kilns(self, dt):
        for key, k in self.kilns.items():
            lit = k['burn'] > 0
            if lit != k.get('_lit', False):
                k['_lit'] = lit
                try:
                    q, r, y = (int(v) for v in key.split(','))
                    if self.world.get(q, r, y) == M['kiln']:
                        mt = self.world.get_meta(q, r, y)
                        self.world.set_meta(q, r, y, (mt | 8) if lit else (mt & ~8))
                        self.world.dirty.add((q // C.CHUNK, r // C.CHUNK))
                except Exception:
                    pass
        for k in self.kilns.values():
            sl = k['slots'].slots            # 0 input, 1 fuel, 2 output
            inp, fuel, out = sl
            res = I.SMELT.get(inp[0]) if inp else None
            can = res is not None and (out is None or (out[0] == res and out[1] < I.get(res).stack))
            if k['burn'] <= 0 and can and fuel and fuel[0] in I.FUEL:
                k['burn'] = k['burn_max'] = I.FUEL[fuel[0]] * I.SMELT_TIME
                fuel[1] -= 1
                if fuel[1] <= 0:
                    sl[1] = None
            if k['burn'] > 0:
                k['burn'] -= dt
                if can:
                    k['prog'] += dt / I.SMELT_TIME
                    if k['prog'] >= 1:
                        k['prog'] = 0
                        inp[1] -= 1
                        if inp[1] <= 0:
                            sl[0] = None
                        out_now = sl[2]
                        if out_now is None:
                            uses = I.get(res).uses
                            sl[2] = [res, 1, 0 if uses is None else uses]
                        else:
                            sl[2][1] += 1
                        self.stats['smelted'] = self.stats.get('smelted', 0) + 1
                        self.check_path()
                else:
                    k['prog'] = 0
            else:
                k['prog'] = max(0.0, k['prog'] - dt)

    def dynamic_models(self, cam):
        """Creatures and dropped items as one VERT array (camera-relative)."""
        parts = []
        p = self.player
        for npc in getattr(self, 'npcs', []):
            v = MD.guide(npc['color'], self.time)
            # face the wanderer
            yaw = math.degrees(math.atan2(p.x - npc['x'], -(p.z - npc['z'])))
            parts.append(MD.transform(v, yaw_deg=yaw,
                                      offset=(npc['x'] - cam[0], npc['y'] - cam[1], npc['z'] - cam[2])))
        fx, fz = math.sin(math.radians(p.yaw)), -math.cos(math.radians(p.yaw))
        for mob in self.mobs:
            dx, dz = mob.x - cam[0], mob.z - cam[2]
            d = math.hypot(dx, dz)
            if d < 60 and (d < 4 or (dx * fx + dz * fz) > -0.3 * d):     # roughly in view
                mob._skyt = getattr(mob, '_skyt', 0) - 1
                if mob._skyt <= 0:
                    mob._skyt, mob._sky = 15, self.sky_at(mob.x, mob.y + 0.5, mob.z)
                parts.append(MD.set_sky(mob.model(cam), mob._sky))
        for dr in self.drops:
            if math.hypot(dr.x - cam[0], dr.z - cam[2]) < 40:
                parts.append(dr.model(cam))
        if getattr(self.app, 'cam_view', 0):
            parts.append(self.player_model(cam))
        return MD.cat(*parts) if parts else None

    def player_model(self, cam):
        """Third-person body. Only a held (crafted or found) item is attached; no default loot."""
        p = self.player
        walking = abs(getattr(p, 'vx', 0.0)) + abs(getattr(p, 'vz', 0.0)) > 0.15 or getattr(self, 'walk', 0) > 0.4
        v = MD.wanderer(self.time, walking)
        it = self.held_item
        if it is not None:
            hand = MD.transform(MD.cached_item(it.id), yaw_deg=10, pitch_deg=-25, scale=0.28,
                                offset=(0.30, 0.88, -0.12))
            v = MD.cat(v, hand)
        return MD.set_sky(MD.transform(v, yaw_deg=p.yaw,
                                       offset=(p.x - cam[0], p.y - cam[1], p.z - cam[2])),
                          self.sky_at(p.x, p.y + 0.9, p.z))

    def sky_at(self, x, y, z):
        q, r = cell_at(x, z)
        y0 = math.floor(y / LAYER) + 1
        col = [max(0, self.world.get(q, r, k)) for k in range(y0, min(C.LAYERS, y0 + 24))]
        roof = any(MT.OPAQUE[m] and m != M['canopy'] for m in col)
        if not roof:
            return 0.78 if M['canopy'] in col else 1.0
        floor_ = any(MT.OPAQUE[max(0, self.world.get(q, r, k))] for k in range(max(0, y0 - 24), y0 - 1))
        return 0.22 if floor_ else 0.62

    def held_model(self, cam, bob=0.0):
        """The item in your hand, placed in front of the camera."""
        return MD.set_sky(self._held_model(cam, bob), self.sky_at(*self.player.eye))

    def _held_model(self, cam, bob=0.0):
        p = self.player
        it = self.held_item
        fwd = forward_vector(p.yaw, p.pitch)
        right = np.array([math.cos(math.radians(p.yaw)), 0, math.sin(math.radians(p.yaw))])
        up = np.cross(right, fwd)
        sw = math.sin(self.swing * math.pi) if self.swing > 0 else 0.0
        pos = fwd * (0.62 - sw * 0.06) + right * (0.36 - sw * 0.08) - up * (0.30 + bob + sw * 0.05)
        if it is None:
            # a soft mitten
            v = MD.prisms(0, 0, -0.18, 0.18, 0.12, (0.98, 0.80, 0.70), (0.92, 0.72, 0.62))
            return MD.transform(v, yaw_deg=p.yaw + 10, pitch_deg=p.pitch - 60 + sw * 40, scale=1.0,
                                offset=tuple(fwd * 0.55 + right * 0.38 - up * (0.42 + bob)))
        v = MD.cached_item(it.id)
        if it.model in SPRITE_HELD:
            # sprite tools are drawn handle-down in XY; rotate so the head points along the look vector
            v = MD.transform(v, yaw_deg=p.yaw + 18, pitch_deg=p.pitch - 50 - sw * 70, roll_deg=-8 + sw * 12, scale=0.42, offset=tuple(pos))
        else:
            v = MD.transform(v, yaw_deg=p.yaw + 12, pitch_deg=p.pitch - 18 - sw * 40, scale=0.24, offset=tuple(pos))
        return v

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
                    self.app.audio.play('chord', 0.6)

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
        self.give(I.GLIMMER.id, 6, quiet=True)
        self.give(I.AETHERITE.id, 1, quiet=True)
        self.apply_abilities()
        self.app.audio.play('awaken', 1.0)
        cx, cz = center(s['q'], s['r'])
        for k in range(5):
            self._spawn(cx, (T + 2 + k * 2) * LAYER, cz, (0.85, 0.78, 1.0), 25, homing=False, speed=4.0)
        if n <= len(ABILITIES):
            ab = ABILITIES[n - 1]
            self.toast(f'A spire awakens! You learned {ab[0]}', ab[1] + ' It also left you Aetherite and Glimmer.', 7.0)
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
        gmul = getattr(self.gen, 'glimmer_mul', 1.0)
        sense = 'sense' in getattr(self, 'attune', [])
        # ceil so mid-rarity still yields a daytime trickle (int() used to floor to 0)
        want = int(math.ceil((1 + 5 * dusk) * gmul * (1.35 if sense else 1.0) - 1e-9))
        if getattr(self, 'tutorial', False):
            want = max(want, 4)
        while len(self.motes) < want and random.random() < dt * (1.2 if sense else 0.8) * max(0.12, gmul):
            ang = random.uniform(0, 2 * math.pi)
            dist = random.uniform(4, 16)
            x, z = p.x + math.cos(ang) * dist, p.z + math.sin(ang) * dist
            y = p.y + random.uniform(0.6, 4.0)
            q, r = cell_at(x, z)
            if self.world.get(q, r, math.floor(y / LAYER)) == 0:
                gold = dusk > 0.45
                if getattr(self, 'tutorial', False):
                    # practice motes drift around whichever Glimmer court is nearer
                    from . import tutorial as TUT
                    sx, sy, sz = min(TUT.mote_courts(), key=lambda c: (c[0] - p.x) ** 2 + (c[2] - p.z) ** 2)
                    x, y, z = sx + random.uniform(-4, 4), sy + random.uniform(0.3, 1.8), sz + random.uniform(-4, 4)
                    gold = True
                self.motes.append([x, y, z, random.uniform(0, 6.3), random.uniform(18, 40), gold])
        keep = []
        ex, ey, ez = p.x, p.y + 0.9, p.z
        for m in self.motes:
            m[3] += dt
            m[4] -= dt * (0.6 if sense else 1.0)
            m[0] += math.sin(m[3] * 0.7) * 0.4 * dt
            m[2] += math.cos(m[3] * 0.5) * 0.4 * dt
            m[1] += math.sin(m[3] * 1.3) * 0.25 * dt
            d = math.sqrt((m[0] - ex) ** 2 + (m[1] - ey) ** 2 + (m[2] - ez) ** 2)
            if d < (2.2 if sense else 1.5):
                # every mote is Glimmer: pale by day, golden at dusk
                self.inv.add(I.GLIMMER.id, 1)
                self.stats['motes'] += 1
                if self.stats['motes'] == 1:
                    self.toast('You caught Glimmer!',
                               '1 Glimmer attunes a waystone. 2-4 buys a lasting gift at a Tidewell.', 5.5)
                self.app.audio.play('mote', 0.7)
                self._spawn(m[0], m[1], m[2], (1.0, 0.84, 0.45), 6, homing=True)
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
        if self.fishing:
            bx, by, bz = self.fishing['pos']
            bite = self.fishing['state'] == 'bite'
            dip = 0.18 if bite else 0.04 * math.sin(self.time * 3.2)
            col = (1.0, 0.35, 0.28) if bite else (1.0, 0.92, 0.85)
            out.append(np.array([[bx - cx, by - dip - cy, bz - cz, col[0], col[1], col[2],
                                  1.0 if bite else 0.9, 1.15 if bite else 0.7]], dtype=np.float64))
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
        if self.weather == 'rain' and self.app.settings['motes'] is not None:
            n = 520
            i = np.arange(n)
            # unique seeds per drop, not a regular lattice
            sx = np.sin(i * 12.9898) * 43758.5453
            sz = np.sin(i * 78.233) * 23421.631
            fx, fz = (sx % 1.0) * 40 - 20, (sz % 1.0) * 40 - 20
            # fall + horizontal wind drift (each drop has its own wind and wobble)
            wind = 1.6
            speed = 11.0 + (np.sin(i * 3.7) % 1.0) * 4.0
            life = 22.0
            tt = self.time * speed + i * 5.17
            ph = (tt / life) % 1.0
            wobble = np.sin(self.time * 6.0 + i * 0.37) * 0.18 + np.sin(self.time * 11.0 + i * 1.1) * 0.08
            rx = cx + fx + ph * wind * 2.2 + wobble
            rz = cz + fz + ph * wind * 0.9 + np.sin(self.time * 5.0 + i * 0.51) * 0.14
            ry = cy + 16 - ph * life
            # short wind-tilted streaks so the rain reads against the sky
            tilt_x = wind * 2.2 / life * 1.2
            tilt_z = wind * 0.9 / life * 1.2
            parts = []
            for step, alpha, size in ((0.0, 0.55, 0.70), (0.45, 0.38, 0.55), (0.90, 0.22, 0.42)):
                parts.append(np.column_stack([
                    rx - cx - tilt_x * step, ry - cy + step, rz - cz - tilt_z * step,
                    np.full(n, 0.82), np.full(n, 0.90), np.full(n, 1.0),
                    np.full(n, alpha), np.full(n, size)]))
            out.append(np.concatenate(parts))
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
        """Point lights for motes near the camera, plus Brightwake's soft glow."""
        cx, cy, cz = cam
        L = [(m[0] - cx, m[1] - cy, m[2] - cz, M['lantern']) for m in self.motes[:6] if m[5]]
        if 'brightwake' in getattr(self, 'attune', []):
            p = self.player
            L.append((p.x - cx, p.y + 0.9 - cy, p.z - cz, M['tidewell']))
        lamp = M.get('lumen_lamp', M['lantern'])
        for mob in self.mobs:
            if mob.kind != 'fairy' or mob.dead:
                continue
            if abs(mob.x - cx) + abs(mob.z - cz) > 28:
                continue
            L.append((mob.x - cx, mob.y + 0.12 - cy, mob.z - cz, lamp))
        if getattr(self, 'tutorial', False):
            from . import landmark as LM
            L.append(LM.lights((cx, cy, cz)))
        return [np.array(L)] if L else []

    # ------------------------------------------------------------------ commands (whisper box)
    ADMIN_HELP = [
        ('/tp x z  ·  /tp x y z', 'go to a spot (finds land)'),
        ('/tp spire  ·  /tp spawn', 'go to the nearest sleeping spire, or your waking spot'),
        ('/give item [count]', 'e.g. /give aetherite pick, /give glass 64'),
        ('/spawn creature [count]', 'woolhop, pebblebeak, mossback, gloomling, brute, skywhale, fairy'),
        ('/killmobs', 'clear all creatures (also /kill)'),
        ('/tide light|dusk|0-1', 'set the tide (also /time day|night)'),
        ('/weather clear|rain', 'change the weather'),
        ('/pos1  /pos2', 'mark two corners at the cell you look at'),
        ('/fill block  ·  /clear', 'fill (or empty) the marked box'),
        ('/replace from to', 'swap one block for another in the box'),
        ('/undo', 'undo the last fill / replace / clear'),
        ('/speed n', 'flying speed (default 13)'),
        ('/heal  ·  /feed', 'full health / full food'),
        ('/fly  ·  /noclip', 'toggle flying / passing through walls'),
        ('/mobs on|off', 'dusk gloomlings on or off'),
        ('/locate spire', 'distance and direction to the nearest spire'),
        ('/seed  ·  /spawnpoint', 'show the seed / set your waking spot here'),
        ('/clearinv', 'empty your backpack'),
    ]
    OPEN_CMDS = {'help', 'seed', 'locate', 'dev'}

    def command(self, text):
        parts = text.strip().lstrip('/').split()
        if not parts:
            return
        cmd, args = parts[0].lower(), parts[1:]
        p = self.player
        if cmd not in self.OPEN_CMDS and not self.dev:
            self.toast('That is an admin command', 'Press F4 to turn on dev mode first.', 3.5)
            return
        try:
            if cmd == 'help':
                from .ui import inventory_ui as IU
                self.app.set_screen(IU.AdminScreen())
            elif cmd == 'dev':
                self.set_dev(not self.dev if not args else args[0] in ('on', '1', 'true'))
            elif cmd in ('tp', 'teleport'):
                self._cmd_tp(args)
            elif cmd in ('tide', 'time'):
                a = args[0].lower() if args else 'light'
                if a in ('dusk', 'night', 'd', 'n'):
                    self.phase = 0.5
                elif a in ('light', 'day', 'l', 'morning'):
                    self.phase = 0.0
                else:
                    self.phase = float(a) % 1.0
                self.toast('The tide turns', TIDE.name(self.phase), 2)
            elif cmd == 'give':
                count = 1
                if args and args[-1].isdigit():
                    count = int(args[-1])
                    args = args[:-1]
                it = I.find(' '.join(args)) if args else None
                if not it:
                    self.toast('No such item', 'Try /give stone pick, /give planks 64, /give glimmer 10', 3)
                    return
                self.give(it.id, max(1, min(count, 999)))
                self.toast(f'Gave {count} {it.name}', '', 2)
            elif cmd in ('spawn', 'summon'):
                kind = (args[0].lower() if args else 'woolhop')
                kind = next((k for k in KINDS if k.startswith(kind)), None)
                if not kind:
                    self.toast('Unknown creature', 'woolhop, pebblebeak, mossback, gloomling, brute, skywhale, fairy', 3)
                    return
                n = int(args[1]) if len(args) > 1 else 1
                ex, ey, ez = p.eye
                fx, fy, fz = forward_vector(p.yaw, 0)
                made = 0
                for k in range(min(n, 30)):
                    x, z = p.x + fx * (3 + k % 4) + random.uniform(-1, 1), p.z + fz * (3 + k % 4) + random.uniform(-1, 1)
                    if kind in FLYING:
                        y = p.y + (12 if kind == 'skywhale' else 1.2) + random.uniform(-0.4, 0.8)
                        self.mobs.append(Mob(kind, x, y, z))
                    else:
                        spot = spawn_spot(self.world, x, z)
                        if spot:
                            self.mobs.append(Mob(kind, spot[0], spot[1], spot[2]))
                        else:
                            self.mobs.append(Mob(kind, x, p.y + 1, z))
                    made += 1
                self.toast(f'Spawned {made} {kind}', '', 2)
            elif cmd in ('killmobs', 'kill', 'butcher'):
                n = len(self.mobs)
                for m in self.mobs:
                    self.kill(m, drops=False)
                self.mobs = []
                self.toast(f'Cleared {n} creatures', '', 2)
            elif cmd == 'weather':
                self.weather = 'rain' if args and args[0].startswith('r') else 'clear'
                self.toast('Weather: ' + self.weather, '', 2)
            elif cmd in ('pos1', 'pos2'):
                cell = self.target or (cell_at(p.x, p.z) + (math.floor(p.y / LAYER) - 1,))
                setattr(self, cmd, tuple(cell))
                self.toast(f'{cmd} set', f'q {cell[0]}  r {cell[1]}  layer {cell[2]}', 2.5)
            elif cmd in ('fill', 'clear', 'set'):
                mat = 0 if cmd == 'clear' else self._block_arg(' '.join(args))
                if mat is None:
                    return
                self._fill(lambda m: mat)
            elif cmd == 'replace':
                if len(args) < 2:
                    self.toast('Use: /replace from to', 'e.g. /replace stone glass', 3)
                    return
                a, b = self._block_arg(args[0]), self._block_arg(' '.join(args[1:]))
                if a is None or b is None:
                    return
                self._fill(lambda m: b if m == a else None)
            elif cmd == 'undo':
                if not self.undo:
                    self.toast('Nothing to undo', '', 2)
                    return
                last = self.undo.pop()
                for q, r, y, m in last:
                    self.world.set(q, r, y, m)
                self.toast(f'Undid {len(last)} cells', '', 2)
            elif cmd == 'speed':
                p.fly_speed = max(2.0, min(120.0, float(args[0]) if args else C.DRIFT_SPEED))
                self.toast(f'Flying speed {p.fly_speed:.0f}', '', 2)
            elif cmd == 'heal':
                self.hp = MAX_HP
                self.toast('Healed', '', 1.5)
            elif cmd == 'feed':
                self.food = MAX_FOOD
                self.toast('Fed', '', 1.5)
            elif cmd == 'fly':
                p.drifting = not p.drifting
                p.vy = 0
                self.toast('Flying' if p.drifting else 'Walking', '', 1.5)
            elif cmd == 'noclip':
                p.noclip = not p.noclip
                if p.noclip:
                    p.drifting = True
                self.toast('Noclip on' if p.noclip else 'Noclip off', 'Fly through anything.' if p.noclip else '', 2)
            elif cmd == 'mobs':
                on = not args or args[0] in ('on', '1', 'true')
                self.app.settings['dusk_critters'] = on
                if not on:
                    self.mobs = [m for m in self.mobs if not m.hostile]
                self.toast('Dusk gloomlings ' + ('on' if on else 'off'), '', 2)
            elif cmd == 'locate':
                if self.nearest_spire:
                    s, d = self.nearest_spire
                    sx, sz = center(s['q'], s['r'])
                    ang = math.degrees(math.atan2(sx - p.x, -(sz - p.z))) % 360
                    dirs = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']
                    self.toast(f'Nearest sleeping spire: {d:,.0f} m {dirs[int((ang + 22.5) // 45) % 8]}',
                               f'at x {sx:,.0f}  z {sz:,.0f}. Use /tp spire to go there.', 5)
                else:
                    self.toast('No sleeping spire nearby', '', 3)
            elif cmd == 'seed':
                self.toast(f'Seed: {self.seed}', self.seed_text, 6)
            elif cmd == 'spawnpoint':
                self.spawn = (p.x, p.y + 0.01, p.z)
                self.toast('Waking spot set here', '', 2)
            elif cmd == 'clearinv':
                self.inv.clear()
                self.toast('Backpack emptied', '', 2)
            else:
                self.toast('Unknown command: ' + cmd, 'Type /help or press F7 for the admin panel.', 4)
        except (ValueError, IndexError):
            self.toast('Those words did not make sense', 'Type /help for the list of commands.', 3)

    def _block_arg(self, name):
        if name.strip().lower() in ('air', 'nothing', 'empty'):
            return 0
        it = I.find(name) if name.strip() else None
        if not it or it.kind != 'block':
            self.toast('Not a block: ' + name, 'e.g. stone, glass, planks, water, lumen lamp', 3)
            return None
        return it.block

    def _fill(self, fn):
        if not self.pos1 or not self.pos2:
            self.toast('Mark a box first', 'Look at a cell and type /pos1, then another and /pos2.', 4)
            return
        (q1, r1, y1), (q2, r2, y2) = self.pos1, self.pos2
        qa, qb = sorted((q1, q2))
        ra, rb = sorted((r1, r2))
        ya, yb = sorted((y1, y2))
        vol = (qb - qa + 1) * (rb - ra + 1) * (yb - ya + 1)
        if vol > 200000:
            self.toast('That box is too big', f'{vol:,} cells; the limit is 200,000.', 3)
            return
        backup = []
        n = 0
        w = self.world
        for q in range(qa, qb + 1):
            for r in range(ra, rb + 1):
                for y in range(max(0, ya), min(C.LAYERS - 1, yb) + 1):
                    m = w.get(q, r, y)
                    if m < 0:
                        continue
                    new = fn(m)
                    if new is None or new == m:
                        continue
                    if m in (M['dormant_spire'], M['awake_spire']):
                        continue
                    backup.append((q, r, y, m))
                    w.set(q, r, y, new, INITIAL_META.get(new, 0))
                    n += 1
        self.undo = (self.undo + [backup])[-5:]
        self.toast(f'Changed {n:,} cells', 'Type /undo to take it back.', 3)

    def _cmd_tp(self, args):
        p = self.player
        if args and args[0] in ('spire', 'spawn'):
            if args[0] == 'spawn':
                if self.spawn:
                    p.x, p.y, p.z = self.spawn
                else:
                    p.x, p.y, p.z = p.last_safe
                self.hold = True
                self.toast('Back to your waking spot', '', 2)
                return
            if self.nearest_spire:
                s = self.nearest_spire[0]
                x, z = center(s['q'] + 5, s['r'] + 2)
                p.x, p.z, p.y = x, z, (s['top'] + 4) * LAYER
                self.hold = True
                self.toast('Drifted near a spire', '', 3)
            return
        nums = [float(a.replace(',', '')) for a in args]
        if len(nums) >= 3:
            p.x, p.y, p.z = nums[0], nums[1], nums[2]
            p.vx = p.vy = p.vz = 0
            self.hold = True
            self.toast(f'Moved to {p.x:,.0f}, {p.y:,.0f}, {p.z:,.0f}', '', 3)
            return
        x, z = nums[0], nums[1]
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

    # ------------------------------------------------------------------ saving
    def to_dict(self):
        p = self.player
        return {'version': 2, 'name': self.name, 'seed': self.seed, 'seed_text': self.seed_text, 'mode': self.mode,
                'gen': self.gen_settings,
                'player': {'x': p.x, 'y': p.y, 'z': p.z, 'yaw': p.yaw, 'pitch': p.pitch, 'drifting': p.drifting,
                           'noclip': p.noclip, 'fly_speed': p.fly_speed, 'safe': list(p.last_safe)},
                'awakened': self.awakened, 'phase': self.phase, 'play_time': self.play_time, 'created': self.created,
                'stats': self.stats, 'hp': self.hp, 'food': self.food, 'spawn': list(self.spawn) if self.spawn else None,
                'dev': self.dev, 'hot': self.hot, 'weather': self.weather, 'inventory': self.inv.to_list(),
                'chests': {k: v.to_list() for k, v in self.chests.items()},
                'kilns': {k: {'slots': v['slots'].to_list(), 'burn': v['burn'], 'burn_max': v['burn_max'], 'prog': v['prog']}
                          for k, v in self.kilns.items()},
                'waystones': self.waystones, 'attune': list(self.attune), 'achieved': list(self.achieved),
                'tutorial': bool(getattr(self, 'tutorial', False))}

    def save(self):
        if self.storage:
            if self.cursor:
                self.give(self.cursor[0], self.cursor[1], self.cursor[2], quiet=True)
                self.cursor = None
            self.world.save_modified()
            self.storage.save(self.to_dict())

    def close(self):
        self.save()
        self.world.close()

"""World generation: an endless archipelago of floating hex islands over a cloud sea.

Everything is a pure function of (seed, q, r), evaluated with vectorised numpy on
float64 world coordinates and int64 lattice hashes, so it never repeats and never
wraps, and any chunk can be generated on its own in a worker process.

Each seed also rolls its own "temperament" (island size, how crowded the sky is,
warp strength, height range, how often skerries and spires appear...), so two
seeds don't just differ in layout, they feel different.
"""
import math
import random

import numpy as np

from .config import CHUNK, LAYERS, CLOUD_SEA, HEX, SQ3
from .materials import ID, N_REALMS
from .noise import Noise, splitmix64, hash2, rand01, hash_ints
from . import gensettings as GS

M = ID
MEADOW, AMBER, ROSE, FROST, BASALT, FEN, DUNE, LUMEN = range(8)
SALTWIND, CEDAR, LAVENDER, CINDER, CHALK, STARFALL, CLOUDSTEP, VERDIGRIS = range(8, 16)
TOP_MAX = LAYERS - 18
TOP_MIN = CLOUD_SEA + 12
SPIRE_REGION = 88                      # cells; at most one spire per region
OFFERINGS = [M['crystal'], M['bloom'], M['vine'], M['clay'], M['mossrock'], M['cloudstuff'], M['lantern'], M['water']]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class Generator:
    def __init__(self, seed, settings=None):
        self.seed = seed
        # v1: skies saved before 1.4-phase2a (no sliders). v2: new worlds, sliders saved with the sky.
        self.settings = GS.normalize(settings) if settings is not None else None
        self.version = 2 if self.settings is not None else 1
        rng = random.Random(splitmix64(seed & ((1 << 64) - 1)))
        k = lambda i: splitmix64((seed + 0x51ED * (i + 1)) & ((1 << 64) - 1))
        self.n_island, self.n_warp1, self.n_warp2, self.n_alt, self.n_hill = (Noise(k(i)) for i in range(5))
        self.n_heat, self.n_wet, self.n_lumen, self.n_detail, self.n_pool = (Noise(k(i)) for i in range(5, 10))
        self.n_depth, self.n_islet, self.n_tunnel, self.n_islet_alt = (Noise(k(i)) for i in range(10, 14))
        self.n_mount, self.n_cave, self.n_ore = Noise(k(14)), Noise(k(15)), Noise(k(16))
        self.n_cliff, self.n_terrace, self.n_arch = Noise(k(17)), Noise(k(18)), Noise(k(19))
        self.h = k(20)
        self.n_form, self.n_mass, self.n_spice, self.n_room = (Noise(k(i)) for i in range(21, 25))
        self.n_hw, self.n_fiss, self.n_style = Noise(k(25)), Noise(k(26)), Noise(k(27))
        # the seed's temperament (v1 uses these raw; v2 uses them as a slight personality around the sliders)
        self.island_scale = rng.uniform(120, 300)
        self.coverage = rng.uniform(-0.04, 0.16)
        self.warp = rng.uniform(20, 110)
        self.alt_base = rng.uniform(52, 66)
        self.alt_amp = rng.uniform(10, 30)
        self.hill_amp = rng.uniform(4, 16)
        self.depth_amp = rng.uniform(34, 70)
        self.mount_amp = rng.uniform(24, 46)
        self.caves = rng.uniform(0.07, 0.12)
        self.realm_scale = rng.uniform(260, 720)
        self.islet_rate = rng.uniform(0.05, 0.35)
        self.tunnels = rng.uniform(0.0, 0.09)
        self.heat_bias = rng.uniform(-0.15, 0.15)
        self.wet_bias = rng.uniform(-0.15, 0.15)
        self.spire_rate = rng.uniform(0.55, 0.9)
        self._spires = {}
        self.cliff_amp = rng.uniform(5, 11)       # 1.3: cliffs, terraces, arches
        self.arches = rng.uniform(0.40, 0.52)
        if self.version == 2:
            s = self.settings
            # personality jitter stays, sliders do the heavy lifting
            self.island_scale = self.island_scale * GS.scale(s, 'island_size', 0.55, 1.0, 1.65)
            self.coverage = self.coverage - (s['sky_density'] - 50) / 50.0 * 0.14
            self.realm_scale = self.realm_scale * GS.scale(s, 'biome_size', 0.5, 1.0, 1.8)
            self.hill_amp = self.hill_amp * GS.scale(s, 'terrain_roughness', 0.45, 1.05, 1.8)
            self.mount_amp = self.mount_amp * GS.scale(s, 'mountain_height', 0.35, 1.15, 1.9)
            self.depth_amp = (self.depth_amp + 10) * GS.scale(s, 'island_thickness', 0.42, 1.0, 2.15)
            self.caves = self.caves * GS.scale(s, 'cave_amount', 0.35, 1.25, 2.1)
            self.tree_mul = GS.scale(s, 'tree_density', 0.15, 1.0, 2.2)
            self.water_mul = GS.scale(s, 'water', 0.15, 1.0, 2.0)
            self.flatness = s['flatness'] / 100.0
            self.cave_size = GS.scale(s, 'cave_size', 0.55, 1.0, 1.85)
            self.glimmer_mul = GS.scale(s, 'glimmer_rarity', 2.1, 1.0, 0.28)
        else:
            self.tree_mul = 1.0
            self.water_mul = 1.0
            self.flatness = 0.35
            self.cave_size = 1.0
            self.glimmer_mul = 1.0

    # ------------------------------------------------------------------ columns
    def columns(self, Q, R):
        """Island shape for arrays of axial columns (any shape). Returns a dict of arrays."""
        if self.version == 1:
            return self._columns_v1(Q, R)
        return self._columns_v2(Q, R)

    def _columns_v1(self, Q, R):
        """Pre-1.4-phase2a terrain, kept so old skies keep generating matching new chunks."""
        Q = np.asarray(Q, dtype=np.int64)
        R = np.asarray(R, dtype=np.int64)
        X = HEX * SQ3 * (Q.astype(np.float64) + R.astype(np.float64) * 0.5)
        Z = HEX * 1.5 * R.astype(np.float64)
        s1 = self.island_scale
        wx = X + self.warp * self.n_warp1.fbm2(X / (s1 * 0.9), Z / (s1 * 0.9), 3)
        wz = Z + self.warp * self.n_warp2.fbm2(X / (s1 * 0.9) + 17.3, Z / (s1 * 0.9) - 4.1, 3)
        e = self.n_island.fbm2(wx / s1, wz / s1, 5) - self.coverage
        # skerries: small high islets in the gaps
        ei = self.n_islet.fbm2(wx / 38.0, wz / 38.0, 3) - (0.62 - self.islet_rate)
        alt = self.alt_base + self.alt_amp * self.n_alt.fbm2(X / 900.0, Z / 900.0, 3)

        heat = self.n_heat.fbm2(X / self.realm_scale, Z / self.realm_scale, 3) * 1.5 + self.heat_bias
        wet = self.n_wet.fbm2(X / self.realm_scale, Z / self.realm_scale, 3) * 1.5 + self.wet_bias
        lum = self.n_lumen.fbm2(X / (self.realm_scale * 0.7), Z / (self.realm_scale * 0.7), 2)
        realm = np.full(Q.shape, MEADOW, dtype=np.int64)
        realm[heat > 0.05] = AMBER
        realm[(heat > 0.30) & (wet >= -0.05)] = ROSE
        realm[(heat > 0.30) & (wet < -0.05)] = DUNE
        realm[(wet > 0.28) & (heat <= 0.30)] = FEN
        realm[(wet < -0.30) & (heat <= 0.30)] = BASALT
        realm[heat < -0.28] = FROST
        realm[lum > 0.40] = LUMEN

        hills = self.n_hill.fbm2(wx / 70.0, wz / 70.0, 4)
        ridge = 1.0 - np.abs(self.n_detail.fbm2(wx / 45.0, wz / 45.0, 3)) * 2
        inner = smoothstep(0.0, 0.18, e)
        h = alt + self.hill_amp * (hills * 0.8 + 0.6) * inner - 5.0 * (1 - smoothstep(0.0, 0.06, e))
        h = h + np.where(realm == FROST, ridge * 9 * inner, 0)
        h = h + self.hill_amp * 0.25 * hills * inner                 # a little more roll
        cl = smoothstep(-0.035, 0.035, self.n_cliff.fbm2(wx / 110.0, wz / 110.0, 2))
        h = h + self.cliff_amp * cl * smoothstep(0.08, 0.25, e) * np.where((realm == FEN) | (realm == DUNE), 0.2, 1.0)
        terr_on = (self.n_terrace.fbm2(X / 220.0, Z / 220.0, 2) > 0.18) & np.isin(realm, (MEADOW, AMBER, FROST))
        h = np.where(terr_on, np.floor(h / 3.0) * 3.0 + 0.5, h)
        mount = smoothstep(0.04, 0.5, self.n_mount.fbm2(X / 240.0, Z / 240.0, 3)) * smoothstep(0.05, 0.3, e)
        h = h + self.mount_amp * mount * (0.55 + 0.45 * ridge) * np.where(realm == FEN, 0.3, 1.0)
        h = h + np.where(realm == DUNE, np.sin(wx / 9.0 + hills * 4) * 2.2 * inner, 0)
        h = np.where(realm == FEN, alt + (h - alt) * 0.35, h)
        top = np.floor(h)
        terr = np.floor(h / 4.0) * 4.0 + np.where(hills > 0.25, 1, 0)
        top = np.where(realm == ROSE, terr, top)
        col_rand = rand01(Q, R, self.h)
        top = np.where(realm == BASALT, top + np.floor(col_rand * 3.0 * inner), top)

        depth = 3 + np.sqrt(np.clip(e, 0, None)) * self.depth_amp * (0.65 + 0.5 * self.n_depth.fbm2(X / 30.0, Z / 30.0, 2))
        depth = depth + (rand01(Q, R, self.h + 1) ** 6) * 14 * inner      # dripping stalks underneath
        bottom = top - np.floor(depth)

        # skerries (only where the main island isn't)
        sk = (ei > 0) & (e <= 0)
        sk_alt = np.floor(self.alt_base + 22 + 18 * self.n_islet_alt.fbm2(X / 300.0, Z / 300.0, 2) + ei * 25)
        top = np.where(sk, sk_alt, top)
        bottom = np.where(sk, sk_alt - np.floor(2 + np.sqrt(np.clip(ei, 0, None)) * 30), bottom)
        land = (e > 0) | sk
        top = np.clip(top, TOP_MIN, TOP_MAX).astype(np.int64)
        bottom = np.clip(bottom, CLOUD_SEA + 2, None).astype(np.int64)
        bottom = np.minimum(bottom, top)

        pooln = self.n_pool.fbm2(X / 26.0, Z / 26.0, 2)
        pool_t = np.where(realm == FEN, 0.05, np.where((realm == BASALT) | (realm == MEADOW), 0.42, 9.0))
        pool = land & ~sk & (e > 0.05) & (pooln > pool_t)
        fall = land & ~sk & (e > 0.0) & (e < 0.03) & (rand01(Q, R, self.h + 2) < 0.012) & \
            np.isin(realm, (MEADOW, AMBER, FEN, BASALT, LUMEN))
        return {'e': e, 'land': land, 'top': top, 'bottom': bottom, 'realm': realm, 'pool': pool, 'fall': fall,
                'skerry': sk, 'inner': inner, 'rand': col_rand, 'peak': top > self.alt_base + 30}
    def _columns_v2(self, Q, R):
        """Richer landforms: plains, hills, valleys and mixed mountain ranges, thicker islands, wider altitude bands."""
        Q = np.asarray(Q, dtype=np.int64)
        R = np.asarray(R, dtype=np.int64)
        X = HEX * SQ3 * (Q.astype(np.float64) + R.astype(np.float64) * 0.5)
        Z = HEX * 1.5 * R.astype(np.float64)
        s1 = self.island_scale
        wx = X + self.warp * self.n_warp1.fbm2(X / (s1 * 0.9), Z / (s1 * 0.9), 3)
        wz = Z + self.warp * self.n_warp2.fbm2(X / (s1 * 0.9) + 17.3, Z / (s1 * 0.9) - 4.1, 3)
        e = self.n_island.fbm2(wx / s1, wz / s1, 5) - self.coverage
        ei = self.n_islet.fbm2(wx / 38.0, wz / 38.0, 3) - (0.62 - self.islet_rate)

        # each island gets its own vertical center of mass (some low over the clouds, some high)
        shelf = 48.0 + 28.0 * self.n_alt.fbm2(X / 1800.0, Z / 1800.0, 3)
        mass = self.n_mass.fbm2(wx / s1, wz / s1, 2)
        com = shelf + 22.0 * mass + (self.alt_base - 59.0)  # seed personality still nudges the band
        # thicker worlds sit a little higher so the undersides have room
        com = com + 0.22 * (self.depth_amp - 40.0)
        com = np.clip(com, CLOUD_SEA + 16, TOP_MAX - 28)

        heat = self.n_heat.fbm2(X / self.realm_scale, Z / self.realm_scale, 3) * 1.5 + self.heat_bias
        wet = self.n_wet.fbm2(X / self.realm_scale, Z / self.realm_scale, 3) * 1.5 + self.wet_bias
        lum = self.n_lumen.fbm2(X / (self.realm_scale * 0.7), Z / (self.realm_scale * 0.7), 2)
        sp = self.n_spice.fbm2(X / (self.realm_scale * 0.85), Z / (self.realm_scale * 0.85), 3)
        realm = np.full(Q.shape, MEADOW, dtype=np.int64)
        realm[heat > 0.05] = AMBER
        realm[(heat > 0.30) & (wet >= -0.05)] = ROSE
        realm[(heat > 0.30) & (wet < -0.05)] = DUNE
        realm[(wet > 0.28) & (heat <= 0.30)] = FEN
        realm[(wet < -0.30) & (heat <= 0.30)] = BASALT
        realm[heat < -0.28] = FROST
        realm[lum > 0.40] = LUMEN
        # eight new landscapes, occupying niches so the original eight still appear
        realm[(wet > 0.02) & (e > 0) & (e < 0.13) & (heat > -0.16) & (heat < 0.36) & (lum <= 0.40)] = SALTWIND
        realm[(heat < 0.02) & (heat > -0.30) & (wet > 0.00) & (sp < 0.22) & (lum <= 0.40)
              & np.isin(realm, (MEADOW, FEN, AMBER, CEDAR))] = CEDAR
        realm[(np.abs(heat) < 0.26) & (wet > -0.16) & (wet < 0.28) & (sp > 0.10) & (lum <= 0.40)
              & np.isin(realm, (MEADOW, AMBER, ROSE, LAVENDER))] = LAVENDER
        realm[(heat > 0.14) & (wet < 0.10) & (sp > 0.04) & (lum <= 0.40)
              & np.isin(realm, (AMBER, ROSE, DUNE, CINDER))] = CINDER
        realm[(wet < -0.02) & (heat > -0.14) & (heat < 0.32) & (sp < 0.18) & (lum <= 0.40)
              & np.isin(realm, (MEADOW, BASALT, DUNE, AMBER, CHALK))] = CHALK
        realm[(sp > 0.20) & (heat < 0.28) & (lum > -0.02) & (lum <= 0.40)] = STARFALL
        realm[(mass > 0.08) & (shelf > 50) & (lum <= 0.40)] = CLOUDSTEP
        realm[(wet > 0.04) & (heat > -0.16) & (heat < 0.36) & (sp > 0.00) & (sp < 0.36) & (lum <= 0.40)
              & np.isin(realm, (MEADOW, FEN, BASALT, AMBER, VERDIGRIS, SALTWIND))] = VERDIGRIS
        # lumen still wins at the heart of a grove
        realm[lum > 0.40] = LUMEN

        # landform mix: plains, rolling hills, valleys, mixed mountain styles (fairly even shares)
        form = 0.5 + 0.5 * self.n_form.fbm2(X / 640.0, Z / 640.0, 3)
        plains = smoothstep(0.38, 0.18, form)
        hills_w = np.clip(1.0 - np.abs(form - 0.44) / 0.26, 0, 1)
        valleys = smoothstep(0.46, 0.56, form) * smoothstep(0.82, 0.68, form)
        mounts = smoothstep(0.55, 0.70, form)
        style = self.n_style.fbm2(X / 900.0, Z / 900.0, 2)
        hills = self.n_hill.fbm2(wx / 70.0, wz / 70.0, 4)
        ridge = 1.0 - np.abs(self.n_detail.fbm2(wx / 45.0, wz / 45.0, 3)) * 2
        inner = smoothstep(0.0, 0.18, e)
        flat = self.flatness
        rough = max(0.35, self.hill_amp / 10.0)

        h = com.copy()
        # plains: very gentle roll, almost gone when Flatness is high
        h = h + (3.0 + 6.0 * rough) * hills * plains * inner * (1.0 - 0.85 * flat)
        # rolling hills
        h = h + (8.0 + self.hill_amp) * (hills * 0.9 + 0.25) * hills_w * inner * (1.0 - 0.80 * flat)
        # valleys cut between ridges
        h = h - (14.0 + 22.0 * rough) * valleys * inner * np.clip(1.15 - ridge, 0, 1) * (1.0 - 0.7 * flat)
        # mountain styles: sharp ridges, broader alpine, or stepped plateaus
        mount = mounts * smoothstep(0.03, 0.22, e)
        peak = (18.0 + self.mount_amp) * mount * (0.65 + 0.80 * np.clip(ridge, 0, 1))
        alpine = (16.0 + self.mount_amp) * mount * (0.75 + 0.45 * hills)
        plateau = com + (14.0 + self.mount_amp) * 0.85 * mount
        plateau = np.floor(plateau / 5.0) * 5.0 + 0.4
        h = h + np.where(style > 0.10, np.where(style > 0.38, peak, alpine), 0) * (1.0 - 0.85 * flat)
        h = np.where((style <= 0.10) & (mount > 0.12),
                     com + (plateau - com) * (1.0 - 0.75 * flat), h)
        # realm flavour
        h = h + np.where(realm == FROST, ridge * 8 * inner * (1.0 - 0.5 * flat), 0)
        h = h + np.where(realm == DUNE, np.sin(wx / 9.0 + hills * 4) * 2.2 * inner, 0)
        h = h + np.where(realm == CINDER, self.cliff_amp * 0.8 * inner, 0)
        h = np.where(realm == FEN, com + (h - com) * (0.55 - 0.25 * flat), h)
        h = np.where(realm == SALTWIND, com + (h - com) * (0.30 - 0.15 * flat), h)
        h = np.where(realm == CHALK, com + (h - com) * 0.55, h)
        h = np.where(realm == LAVENDER, com + (h - com) * (0.65 - 0.2 * flat), h)
        cl = smoothstep(-0.035, 0.035, self.n_cliff.fbm2(wx / 110.0, wz / 110.0, 2))
        h = h + self.cliff_amp * cl * smoothstep(0.08, 0.25, e) * np.where(
            np.isin(realm, (FEN, DUNE, SALTWIND, LAVENDER)), 0.25, 1.0)
        terr_on = (self.n_terrace.fbm2(X / 220.0, Z / 220.0, 2) > 0.18) & np.isin(
            realm, (MEADOW, AMBER, FROST, CEDAR, CHALK, CLOUDSTEP))
        h = np.where(terr_on, np.floor(h / 3.0) * 3.0 + 0.5, h)
        top = np.floor(h)
        terr = np.floor(h / 4.0) * 4.0 + np.where(hills > 0.25, 1, 0)
        top = np.where(realm == ROSE, terr, top)
        col_rand = rand01(Q, R, self.h)
        top = np.where(np.isin(realm, (BASALT, VERDIGRIS, CINDER)), top + np.floor(col_rand * 3.0 * inner), top)

        # substantially thicker in most places, still clearly varied
        thick = self.depth_amp * (0.85 + 0.50 * self.n_depth.fbm2(X / 36.0, Z / 36.0, 3))
        thick = thick * (1.0 + 0.28 * mounts + 0.06 * plains)
        depth = 10 + (0.20 + np.sqrt(np.clip(e, 0, None))) * thick
        depth = depth + (rand01(Q, R, self.h + 1) ** 6) * 14 * inner
        # saltwind and chalk run a little shallower; mountains and cloudstep run deeper
        depth = depth * np.where(np.isin(realm, (SALTWIND, CHALK, LAVENDER)), 0.78, 1.0)
        depth = depth * np.where(np.isin(realm, (CLOUDSTEP, CINDER, FROST)), 1.18, 1.0)
        bottom = top - np.floor(depth)
        # clip into the cloud sea if needed, but do not lift per-column (that flattened the terrain)

        sk = (ei > 0) & (e <= 0)
        sk_alt = np.floor(com + 8 + 16 * self.n_islet_alt.fbm2(X / 300.0, Z / 300.0, 2) + ei * 25)
        top = np.where(sk, sk_alt, top)
        bottom = np.where(sk, sk_alt - np.floor(3 + np.sqrt(np.clip(ei, 0, None)) * 36), bottom)
        land = (e > 0) | sk
        # thick low islands may hang down into the cloud sea; don't clip thickness away
        top = np.clip(top, TOP_MIN, TOP_MAX).astype(np.int64)
        bottom = np.clip(bottom, 2, None).astype(np.int64)
        bottom = np.minimum(bottom, top - 2)

        pooln = self.n_pool.fbm2(X / 26.0, Z / 26.0, 2)
        wmul = self.water_mul
        pool_t = np.where(np.isin(realm, (FEN, SALTWIND, VERDIGRIS)), 0.14 - 0.10 * wmul,
                          np.where(np.isin(realm, (BASALT, MEADOW, LAVENDER, CEDAR)), 0.50 - 0.16 * wmul, 9.0))
        pool_t = np.where(np.isin(realm, (CINDER, DUNE, CHALK)), 0.75 - 0.10 * wmul, pool_t)
        pool = land & ~sk & (e > 0.04) & (pooln > pool_t) & (wmul > 0.2)
        fall = land & ~sk & (e > 0.0) & (e < 0.03) & (rand01(Q, R, self.h + 2) < (0.012 * wmul)) & \
            np.isin(realm, (MEADOW, AMBER, FEN, BASALT, LUMEN, CEDAR, VERDIGRIS, CLOUDSTEP, LAVENDER))
        return {'e': e, 'land': land, 'top': top, 'bottom': bottom, 'realm': realm, 'pool': pool, 'fall': fall,
                'skerry': sk, 'inner': inner, 'rand': col_rand, 'peak': top > (com + 24), 'com': com}


    # ------------------------------------------------------------------ spires
    def spire(self, rq, rr):
        """The ancient spire of region (rq, rr), or None. Cached."""
        key = (rq, rr)
        if key in self._spires:
            return self._spires[key]
        hsh = hash_ints(self.h, rq, rr, 77)
        res = None
        if (hsh & 0xFFFF) / 65536.0 < self.spire_rate:
            m = SPIRE_REGION - 20
            q = rq * SPIRE_REGION + 10 + (hsh >> 16) % m
            r = rr * SPIRE_REGION + 10 + (hsh >> 32) % m
            c = self.columns(np.array([q]), np.array([r]))
            ok = bool(c['land'][0]) and not bool(c['skerry'][0]) and c['e'][0] > 0.07 and not c['pool'][0]
            if ok:
                rng = random.Random(hsh)
                n = 2 if rng.random() < 0.7 else 3
                wants = rng.sample(OFFERINGS, n)
                res = {'id': f'{rq}_{rr}', 'q': int(q), 'r': int(r), 'top': int(c['top'][0]),
                       'height': 7 + (hsh >> 48) % 6, 'wants': wants, 'realm': int(c['realm'][0])}
        if len(self._spires) > 4096:
            self._spires.clear()
        self._spires[key] = res
        return res

    def spires_near(self, q, r, regions=2):
        rq0, rr0 = q // SPIRE_REGION, r // SPIRE_REGION
        out = []
        for a in range(rq0 - regions, rq0 + regions + 1):
            for b in range(rr0 - regions, rr0 + regions + 1):
                s = self.spire(a, b)
                if s:
                    out.append(s)
        return out

    # ------------------------------------------------------------------ chunks
    def generate(self, cq, cr):
        """-> cells (CHUNK, LAYERS, CHUNK) uint8, meta (same) uint8, realm (CHUNK, CHUNK) uint8"""
        P = 4                                   # margin for features that spill across chunk edges
        q0, r0 = cq * CHUNK, cr * CHUNK
        qs = np.arange(q0 - P, q0 + CHUNK + P, dtype=np.int64)
        rs = np.arange(r0 - P, r0 + CHUNK + P, dtype=np.int64)
        Q, R = np.meshgrid(qs, rs, indexing='ij')
        col = self.columns(Q, R)
        sl = (slice(P, P + CHUNK), slice(P, P + CHUNK))
        top, bot, realm = col['top'][sl], col['bottom'][sl], col['realm'][sl]
        land = col['land'][sl]
        ys = np.arange(LAYERS, dtype=np.int64)[None, :, None]
        T = top[:, None, :]
        B = bot[:, None, :]
        Rm = realm[:, None, :]
        solid = land[:, None, :] & (ys >= B) & (ys <= T)
        d = T - ys
        cells = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
        body = np.full(Rm.shape, M['stone'], np.uint8)
        body = np.where(Rm == ROSE, M['rosestone'], body)
        body = np.where(Rm == BASALT, M['basalt'], body)
        body = np.where(Rm == CINDER, M['cinder'], body)
        body = np.where(Rm == VERDIGRIS, M['mossrock'], body)
        body = np.where(Rm == CHALK, M['chalk'], body)
        body = np.where(Rm == SALTWIND, M['sandstone'], body)
        body = np.where(Rm == STARFALL, M['starstone'], body)
        body = np.where(Rm == CLOUDSTEP, M['pale_stone'], body)
        mid = np.where(np.isin(Rm, (MEADOW, AMBER, FEN, LUMEN, CEDAR, LAVENDER, VERDIGRIS)), M['loam'], body)
        mid = np.where(np.isin(Rm, (DUNE,)), M['sand'], mid)
        mid = np.where(Rm == SALTWIND, M['sandstone'], mid)
        mid = np.where(Rm == CHALK, M['chalk'], mid)
        mid = np.where(np.isin(Rm, (FROST,)), M['snow'], mid)
        mid = np.where(Rm == CLOUDSTEP, M['pale_stone'], mid)
        mid = np.where(Rm == STARFALL, M['starstone'], mid)
        mid = np.where(Rm == CINDER, M['cinder'], mid)
        surf = np.where(np.isin(Rm, (MEADOW, AMBER, FEN, LUMEN, CEDAR, LAVENDER, VERDIGRIS, STARFALL, CLOUDSTEP)), M['turf'], body)
        surf = np.where(np.isin(Rm, (DUNE,)), M['sand'], surf)
        surf = np.where(Rm == CHALK, M['chalk'], surf)
        surf = np.where(Rm == SALTWIND, M['sandstone'], surf)
        surf = np.where(Rm == FROST, M['snow'], surf)
        surf = np.where(Rm == CINDER, M['cinder'], surf)
        det = self.n_detail.fbm2(Q[sl] / 7.0, R[sl] / 7.0, 2)[:, None, :]
        surf = np.where((Rm == BASALT) & (det > 0.1), M['turf'], surf)
        surf = np.where((Rm == ROSE) & (det > 0.15), M['turf'], surf)
        surf = np.where((Rm == FROST) & (det > 0.35), M['ice'], surf)
        surf = np.where((Rm == FEN) & (det < -0.32), M['clay'], surf)
        surf = np.where((Rm == SALTWIND) & (det < 0.05), M['clay'], surf)
        surf = np.where((Rm == CEDAR) & (det < -0.2), M['mossrock'], surf)
        surf = np.where((Rm == CHALK) & (det > 0.25), M['cobble'], surf)
        surf = np.where((Rm == CLOUDSTEP) & (det > 0.2), M['snow'], surf)
        surf = np.where((Rm == VERDIGRIS) & (det > 0.15), M['mossrock'], surf)
        surf = np.where((Rm == CINDER) & (det > 0.35), M['basalt'], surf)
        surf = np.where((Rm == SALTWIND) & (det < 0.0), M['salt_block'], surf)
        surf = np.where((Rm == LAVENDER) & (det > 0.22), M['heather'], surf)
        surf = np.where((Rm == STARFALL) & (det < -0.2), M['starstone'], surf)
        surf = np.where((Rm == CEDAR) & (det > 0.28), M['slate'], surf)
        peak = col['peak'][sl][:, None, :] & ~np.isin(Rm, (DUNE, LUMEN, SALTWIND, CINDER, CHALK))
        surf = np.where(peak, M['snow'], surf)
        # cloudstep undersides fade into cloudstuff
        cells = np.where(solid, body, 0).astype(np.uint8)
        cells = np.where(solid & (d <= 3) & (d >= 1), mid, cells)
        cells = np.where(solid & (d == 0), surf, cells)
        # Cloudstep Isles: the lowest third of the island is cloudstuff
        from_bot = ys - B
        thick = np.maximum(1, T - B)
        cells = np.where(solid & (Rm == CLOUDSTEP) & (from_bot <= thick * 0.34) & (d >= 2), M['cloudstuff'], cells)
        # ores in the stone body, in veins, rarer the deeper you go
        body_mask = solid & (d >= 3)
        if body_mask.any():
            idx = np.nonzero(body_mask)
            qq = Q[sl][idx[0], idx[2]].astype(np.float64)
            rr = R[sl][idx[0], idx[2]].astype(np.float64)
            xx, zz = qq + rr * 0.5, rr * 0.866
            yy = idx[1].astype(np.float64) * 0.7 / 1.73
            dd = d[idx[0], idx[1], idx[2]]
            for k, (ore, mind, thr, sc) in enumerate(((M['emberite_ore'], 3, 0.50, 3.2), (M['verdigris_ore'], 7, 0.55, 2.8),
                                                      (M['silverine_ore'], 14, 0.60, 2.6), (M['aetherite_ore'], 24, 0.70, 2.2))):
                n = self.n_ore.noise3(xx / sc + 37.1 * k, yy / sc - 11.3 * k, zz / sc + 5.7 * k)
                hit = (dd >= mind) & (n > thr)
                cells[idx[0][hit], idx[1][hit], idx[2][hit]] = ore
            # caves: winding worms, linking highways, rooms of mixed scale, fissures, arches
            # v2 keeps a thicker roof so caves don't pock the walking surface
            roof_d = 5 if self.version == 2 else 3
            deep = (dd >= roof_d) & ((idx[1] - B[idx[0], 0, idx[2]]) >= 3)
            if self.version == 2:
                cs = self.cave_size
                amt = self.caves
                n1 = self.n_cave.noise3(xx / (16.0 * cs), yy / (7.0 * cs), zz / (16.0 * cs))
                n2 = self.n_cave.noise3(xx / (16.0 * cs) + 31.7, yy / (7.0 * cs) - 3.3, zz / (16.0 * cs) + 11.9)
                worm = (np.abs(n1) < amt * 1.15) & (np.abs(n2) < amt * 2.0)
                # larger "highway" worms that stitch chambers together
                h1 = self.n_hw.noise3(xx / (42.0 * cs), yy / (16.0 * cs), zz / (42.0 * cs))
                h2 = self.n_hw.noise3(xx / (42.0 * cs) + 8.1, yy / (16.0 * cs) - 5.4, zz / (42.0 * cs) + 19.2)
                highway = (np.abs(h1) < amt * 0.85) & (np.abs(h2) < amt * 1.3)
                # rooms: a few sizes of open cavern
                small = self.n_room.noise3(xx / (18.0 * cs), yy / (10.0 * cs), zz / (18.0 * cs)) > (0.52 - amt * 0.6)
                midc = self.n_tunnel.noise3(xx / (34.0 * cs), yy / (16.0 * cs), zz / (34.0 * cs)) > (0.46 - amt * 0.5)
                huge = self.n_room.noise3(xx / (70.0 * cs) + 4.4, yy / (28.0 * cs), zz / (70.0 * cs)) > (0.62 - amt * 0.25)
                # tall fissures and wide squash chambers
                fiss = (np.abs(self.n_fiss.noise3(xx / 9.0, yy / 22.0, zz / 9.0)) < 0.07 * (0.7 + amt)) & (
                    np.abs(self.n_fiss.noise3(xx / 22.0 + 3, yy / 9.0, zz / 22.0)) < 0.22)
                hole = deep & (worm | highway | small | midc | huge | fiss)
            else:
                n1 = self.n_cave.noise3(xx / 16.0, yy / 7.0, zz / 16.0)
                n2 = self.n_cave.noise3(xx / 16.0 + 31.7, yy / 7.0 - 3.3, zz / 16.0 + 11.9)
                worm = (np.abs(n1) < self.caves) & (np.abs(n2) < self.caves * 1.7)
                big = self.n_tunnel.noise3(xx / 34.0, yy / 14.0, zz / 34.0) > 0.42
                hole = deep & (worm | big)
            # arches and overhangs: keep a solid roof so the walking surface is not holey
            # v2: start deeper (at least 5 layers under the top) and carve them more rarely
            roof = 5 if self.version == 2 else 2
            band = (dd >= roof) & (dd <= 9) & ((idx[1] - B[idx[0], 0, idx[2]]) >= 4)
            if band.any():
                na = self.n_arch.noise3(xx / 11.0, yy / 4.5, zz / 11.0)
                thr = self.arches + (0.14 if self.version == 2 else 0.0)
                hole |= band & (na > thr)
            cells[idx[0][hole], idx[1][hole], idx[2][hole]] = 0
            # glowcaps and crystals on cave floors
            fl = hole & (rand01(qq.astype(np.int64), rr.astype(np.int64) * 7 + idx[1], self.h + 31) < 0.04)
            for a, y, b in zip(idx[0][fl], idx[1][fl], idx[2][fl]):
                if y > 0 and cells[a, y - 1, b] not in (0, M['water']) and cells[a, y, b] == 0:
                    cells[a, y, b] = M['glowcap'] if (a + b + y) % 3 else M['crystal']
        meta = np.zeros_like(cells)

        # pools and waterfalls
        pool, fall = col['pool'][sl], col['fall'][sl]
        ii, kk = np.nonzero(pool)
        for i, k in zip(ii, kk):
            t = top[i, k]
            cells[i, t, k] = M['water']
            meta[i, t, k] = 7
        ii, kk = np.nonzero(fall)
        for i, k in zip(ii, kk):
            t = top[i, k]
            cells[i, CLOUD_SEA:t + 1, k] = M['water']
            meta[i, CLOUD_SEA:t + 1, k] = 7

        # small things: petals, glowcaps, crystals, lumen shards under the islands
        rnd = rand01(Q[sl], R[sl], self.h + 5)
        rnd2 = rand01(Q[sl], R[sl], self.h + 6)
        free = land & ~pool & ~fall & (top + 1 < LAYERS)
        surf_top = cells[np.arange(CHUNK)[:, None], top, np.arange(CHUNK)[None, :]]
        on_turf = free & ((surf_top == M['turf']) | (surf_top == M['snow']) | (surf_top == M['sand']))
        deco_rate = np.take([0.07, 0.03, 0.02, 0.012, 0.03, 0.04, 0.012, 0.10,
                            0.03, 0.04, 0.11, 0.02, 0.015, 0.08, 0.03, 0.05], np.clip(realm, 0, 15))
        deco = np.take([M['petals'], M['petals'], M['petals'], M['crystal'], M['petals'], M['petals'],
                         M['crystal'], M['glowcap'],
                         M['petals'], M['petals'], M['petals'], M['crystal'], M['petals'], M['crystal'],
                         M['glowcap'], M['vine']], np.clip(realm, 0, 15))
        place = on_turf & (rnd < deco_rate)
        ii, kk = np.nonzero(place)
        for i, k in zip(ii, kk):
            if cells[i, top[i, k], k] != 0:
                cells[i, top[i, k] + 1, k] = deco[i, k]
        bush = on_turf & ~place & (rnd2 > 1 - np.take([0.012, 0.02, 0.004, 0.0, 0.006, 0.02, 0.0, 0.004,
                                                     0.008, 0.025, 0.016, 0.0, 0.004, 0.006, 0.005, 0.014], np.clip(realm, 0, 15)))
        ii, kk = np.nonzero(bush)
        for i, k in zip(ii, kk):
            if cells[i, top[i, k], k] != 0:
                cells[i, top[i, k] + 1, k] = M['berry_bush']
        under = land & (rnd2 < 0.02) & (bot > CLOUD_SEA + 3) & ~fall
        ii, kk = np.nonzero(under)
        for i, k in zip(ii, kk):
            if cells[i, bot[i, k], k]:
                cells[i, bot[i, k] - 1, k] = M['lumen_shard']

        # spires (and keep trees away from them)
        spires = []
        for s in self.spires_near(q0 + CHUNK // 2, r0 + CHUNK // 2, 1):
            if q0 - 8 <= s['q'] < q0 + CHUNK + 8 and r0 - 8 <= s['r'] < r0 + CHUNK + 8:
                spires.append(s)

        # trees
        trnd = rand01(Q, R, self.h + 7)
        tree_rate = np.take([0.016, 0.05, 0.006, 0.02, 0.004, 0.022, 0.002, 0.03,
                             0.004, 0.045, 0.012, 0.003, 0.005, 0.018, 0.008, 0.024], np.clip(col['realm'], 0, 15))
        tree_rate = tree_rate * getattr(self, 'tree_mul', 1.0)
        tmask = col['land'] & ~col['pool'] & ~col['fall'] & (trnd < tree_rate) & (col['e'] > 0.035) & ~col['skerry']
        ii, kk = np.nonzero(tmask)
        for i, k in zip(ii, kk):
            q, r = int(Q[i, k]), int(R[i, k])
            if any(abs(q - s['q']) + abs(r - s['r']) + abs(q + r - s['q'] - s['r']) < 14 for s in spires):
                continue
            self._tree(cells, q - q0, r - r0, int(col['top'][i, k]), int(col['realm'][i, k]),
                       hash_ints(self.h, q, r, 9))
        for s in spires:
            self._stamp_spire(cells, meta, s, q0, r0)
        return cells, meta, realm.astype(np.uint8)

    # ------------------------------------------------------------------ features
    @staticmethod
    def _put(cells, lq, y, lr, mat, only_air=True):
        if 0 <= lq < CHUNK and 0 <= lr < CHUNK and 0 <= y < LAYERS:
            if not only_air or cells[lq, y, lr] == 0 or cells[lq, y, lr] in (M['petals'],):
                cells[lq, y, lr] = mat

    def _disk(self, cells, lq, lr, y, radius, mat, only_air=True):
        for dq in range(-radius, radius + 1):
            for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
                self._put(cells, lq + dq, y, lr + dr, mat, only_air)

    def _tree(self, cells, lq, lr, top, realm, hsh):
        rng = random.Random(hsh)
        if not (-3 <= lq < CHUNK + 3 and -3 <= lr < CHUNK + 3):
            return
        wood, leaf = M['heartwood'], M['canopy']
        if realm == CEDAR:
            wood = M['cedar_heartwood']
        elif realm in (SALTWIND, CHALK, CLOUDSTEP):
            wood = M['pale_heartwood']
        elif realm in (AMBER, VERDIGRIS):
            wood = M['dark_heartwood']
        if realm == LUMEN:                      # giant glowing toadstool
            hgt = rng.randint(4, 7)
            for y in range(top + 1, top + 1 + hgt):
                self._put(cells, lq, y, lr, M['plinth'] if False else wood)
            self._disk(cells, lq, lr, top + hgt, 2, leaf)
            self._disk(cells, lq, lr, top + hgt + 1, 1, leaf)
            for (dq, dr) in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, -2), (-2, 2)):
                self._put(cells, lq + dq, top + hgt - 1, lr + dr, M['glowcap'])
            return
        if realm == FROST:                      # stacked rings, narrowing: a hex fir
            hgt = rng.randint(6, 9)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, wood)
            for i, y in enumerate(range(top + 3, top + hgt + 1)):
                rad = max(0, 2 - i // 2)
                self._disk(cells, lq, lr, y, rad, leaf)
            return
        if realm == DUNE or realm == CINDER:
            for y in range(top + 1, top + rng.randint(3, 5)):
                self._put(cells, lq, y, lr, M['crystal'] if realm == DUNE else M['basalt'])
            if realm == CINDER:
                self._put(cells, lq, top + rng.randint(2, 4), lr, M['crystal'])
            return
        if realm == STARFALL:
            hgt = rng.randint(4, 7)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, M['crystal'] if y > top + hgt - 3 else wood)
            self._disk(cells, lq, lr, top + hgt, 2, leaf)
            self._put(cells, lq, top + hgt + 1, lr, M['lumen_shard'])
            return
        if realm == CEDAR or realm == CLOUDSTEP:
            hgt = rng.randint(7, 10) if realm == CEDAR else rng.randint(4, 6)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, wood)
            for i, y in enumerate(range(top + (3 if realm == CEDAR else 2), top + hgt + 1)):
                rad = max(0, (2 if realm == CEDAR else 1) - i // 2)
                self._disk(cells, lq, lr, y, rad, leaf)
            return
        if realm == CHALK or realm == SALTWIND:
            hgt = rng.randint(3, 5)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, wood)
            self._disk(cells, lq, lr, top + hgt, 1, leaf)
            return
        hgt = rng.randint(4, 6) + (2 if realm in (AMBER, VERDIGRIS) else 0)
        for y in range(top + 1, top + hgt + 1):
            self._put(cells, lq, y, lr, wood)
        rad = 2 if realm != ROSE else 1
        self._disk(cells, lq, lr, top + hgt - 1, rad, leaf)
        self._disk(cells, lq, lr, top + hgt, rad, leaf)
        self._disk(cells, lq, lr, top + hgt + 1, max(1, rad - 1), leaf)
        if realm in (FEN, VERDIGRIS):          # weeping vines from the canopy edge
            for (dq, dr) in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, -2), (-2, 2)):
                for y in range(top + hgt - 2 - rng.randint(0, 2), top + hgt - 1):
                    self._put(cells, lq + dq, y, lr + dr, M['vine'])

    def _stamp_spire(self, cells, meta, s, q0, r0):
        lq, lr, T = s['q'] - q0, s['r'] - r0, s['top']
        for dq in range(-4, 5):
            for dr in range(max(-4, -dq - 4), min(4, -dq + 4) + 1):
                a, b = lq + dq, lr + dr
                if not (0 <= a < CHUNK and 0 <= b < CHUNK):
                    continue
                dist = (abs(dq) + abs(dr) + abs(dq + dr)) // 2
                cells[a, T + 1:T + 16, b] = 0
                meta[a, T + 1:T + 16, b] = 0
                if dist <= 3:
                    lo = T - 3
                    col = cells[a, lo:T + 1, b]
                    col[col == 0] = M['plinth'] if dist <= 2 else M['stone']
                    col[col == M['water']] = M['plinth']
                    cells[a, T, b] = M['plinth'] if dist <= 2 else cells[a, T, b] or M['stone']
                if dist == 0:
                    cells[a, T + 1:T + 1 + s['height'], b] = M['dormant_spire']
                if dist == 3 and (dq + 2 * dr) % 2 == 0:
                    hp = 1 + (abs(dq * 7 + dr * 3) % 3)
                    cells[a, T + 1:T + 1 + hp, b] = M['plinth']

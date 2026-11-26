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

from .config import CHUNK, LAYERS, CLOUD_SEA, HEX, SQ3, V2_LAYERS
from .materials import ID, N_REALMS
from .noise import Noise, splitmix64, hash2, rand01, hash_ints
from . import gensettings as GS

M = ID
MEADOW, AMBER, ROSE, FROST, BASALT, FEN, DUNE, LUMEN = range(8)
SALTWIND, CEDAR, LAVENDER, CINDER, CHALK, STARFALL, CLOUDSTEP, VERDIGRIS = range(8, 16)
TOP_MAX = LAYERS - 18          # v3 ceiling (room for a surface near 300)
TOP_MIN = CLOUD_SEA + 12
V2_TOP_MAX = V2_LAYERS - 18    # 1.4 / 1.4.1 ceiling; must stay fixed
V2_TOP_MIN = CLOUD_SEA + 12
SPIRE_REGION = 88                      # cells; at most one spire per region
OFFERINGS = [M['crystal'], M['bloom'], M['vine'], M['clay'], M['mossrock'], M['cloudstuff'], M['lantern'], M['water']]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _dilate_hex(mask):
    """One step of 6-neighbour hex dilation plus up and down."""
    out = mask.copy()
    out[1:] |= mask[:-1]
    out[:-1] |= mask[1:]
    out[:, :, 1:] |= mask[:, :, :-1]
    out[:, :, :-1] |= mask[:, :, 1:]
    out[1:, :, :-1] |= mask[:-1, :, 1:]
    out[:-1, :, 1:] |= mask[1:, :, :-1]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


class Generator:
    def __init__(self, seed, settings=None):
        self.seed = seed
        self.tutorial = bool(isinstance(settings, dict) and settings.get('tutorial'))
        # v1: skies saved before 1.4-phase2a (no sliders). v2: 1.4 / 1.4.1.
        # v3: 1.4.2 (separated altitude shelves, higher peaks). v4: 1.4.3 discrete
        # spaced islands. v5: 1.4.4 larger islands and rare huge continents.
        # Missing version on a saved slider sky means 2, so 1.4.1 worlds keep their terrain.
        self.settings = GS.normalize(settings) if settings is not None else None
        if self.settings is None:
            self.version = 1
        else:
            self.version = int(self.settings.get('generator_version') or 2)
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
        if self.version >= 2:
            s = self.settings
            # personality jitter stays, sliders do the heavy lifting
            self.island_scale = self.island_scale * GS.scale(s, 'island_size', 0.55, 1.0, 1.65)
            self.coverage = self.coverage - (s['sky_density'] - 50) / 50.0 * 0.14
            self.realm_scale = self.realm_scale * GS.scale(s, 'biome_size', 0.5, 1.0, 1.8)
            self.hill_amp = self.hill_amp * GS.scale(s, 'terrain_roughness', 0.45, 1.05, 1.8)
            self.mount_amp = self.mount_amp * GS.scale(s, 'mountain_height', 0.35, 1.15, 1.9)
            self.depth_amp = (self.depth_amp + 10) * GS.scale(s, 'island_thickness', 0.42, 1.0, 2.15)
            # max used to Swiss-cheese islands; keep a mid that's still roomy
            self.caves = self.caves * GS.scale(s, 'cave_amount', 0.35, 1.15, 1.55)
            self.tree_mul = GS.scale(s, 'tree_density', 0.15, 1.0, 2.2)
            self.water_mul = GS.scale(s, 'water', 0.15, 1.0, 2.0)
            self.flatness = s['flatness'] / 100.0
            self.cave_size = GS.scale(s, 'cave_size', 0.55, 1.0, 1.45)
            # 1.4-phase3: Glimmer is substantially rarer at every slider setting
            self.glimmer_mul = GS.scale(s, 'glimmer_rarity', 0.70, 0.32, 0.10)
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
        if self.version >= 5:
            return self._columns_v5(Q, R)
        if self.version >= 4:
            return self._columns_v4(Q, R)
        if self.version >= 3:
            return self._columns_v3(Q, R)
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
        top = np.clip(top, V2_TOP_MIN, V2_TOP_MAX).astype(np.int64)
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

        # each island sits in a Worley altitude band so neighbours can hang far above or far below,
        # while a single island stays on one shelf (the cell is a little larger than a typical island)
        mass = self.n_mass.fbm2(wx / s1, wz / s1, 2)
        period = max(float(s1) * 1.05, 220.0)
        fx, fz = X / period, Z / period
        best_d = np.full(Q.shape, 1e9, np.float64)
        best_band = np.zeros(Q.shape, np.float64)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                cx = np.floor(fx) + di
                cz = np.floor(fz) + dj
                jx = rand01(cx.astype(np.int64), cz.astype(np.int64), self.h + 3)
                jz = rand01(cx.astype(np.int64), cz.astype(np.int64), self.h + 4)
                px = cx + 0.5 + (jx - 0.5) * 0.8
                pz = cz + 0.5 + (jz - 0.5) * 0.8
                d2 = (fx - px) ** 2 + (fz - pz) ** 2
                band = (hash2(cx.astype(np.int64), cz.astype(np.int64), self.h + 5) % np.uint64(7)).astype(np.float64)
                closer = d2 < best_d
                best_band = np.where(closer, band, best_band)
                best_d = np.minimum(best_d, d2)
        lo_alt, hi_alt = float(CLOUD_SEA + 18), float(V2_TOP_MAX - 14)
        com = lo_alt + (best_band + 0.30 * mass) / 6.0 * (hi_alt - lo_alt) + (self.alt_base - 59.0)
        com = com + 0.10 * (self.depth_amp - 40.0)
        com = np.clip(com, CLOUD_SEA + 16, V2_TOP_MAX - 14)
        shelf = com

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

        # inverted-dome / teardrop underside: thin rounded lip at the rim, a belly under the core
        thick = self.depth_amp * (0.85 + 0.50 * self.n_depth.fbm2(X / 36.0, Z / 36.0, 3))
        thick = thick * (1.0 + 0.28 * mounts + 0.06 * plains)
        hull = smoothstep(0.0, 0.32, np.clip(e, 0, None))
        rho = 1.0 - hull
        dome = np.sqrt(np.clip(1.0 - rho * rho, 0, 1))
        depth = 4.0 + thick * (0.88 * dome + 0.22 * (hull ** 2))
        # a few stalactite drips hanging from the belly
        depth = depth + (rand01(Q, R, self.h + 1) ** 7) * 18 * hull
        # saltwind and chalk run a little shallower; mountains and cloudstep run deeper
        depth = depth * np.where(np.isin(realm, (SALTWIND, CHALK, LAVENDER)), 0.78, 1.0)
        depth = depth * np.where(np.isin(realm, (CLOUDSTEP, CINDER, FROST)), 1.18, 1.0)
        # rounded lip: shave the top a little at the rim so the edge isn't a flat slab
        top = top - np.floor((1.0 - hull) ** 2 * 2.4)
        bottom = top - np.floor(depth)

        sk = (ei > 0) & (e <= 0)
        sk_alt = np.floor(com + 8 + 16 * self.n_islet_alt.fbm2(X / 300.0, Z / 300.0, 2) + ei * 25)
        top = np.where(sk, sk_alt, top)
        sk_hull = smoothstep(0.0, 0.28, np.clip(ei, 0, None))
        sk_dome = np.sqrt(np.clip(1.0 - (1.0 - sk_hull) ** 2, 0, 1))
        bottom = np.where(sk, sk_alt - np.floor(2 + sk_dome * 28 + (1.0 - sk_hull) * 0), bottom)
        land = (e > 0) | sk
        # thick low islands may hang down into the cloud sea; don't clip thickness away
        top = np.clip(top, V2_TOP_MIN, V2_TOP_MAX).astype(np.int64)
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



    def _worley_bands(self, X, Z, period, n_bands):
        """Nearest and second-nearest jittered-grid cells, with a discrete altitude band each."""
        fx, fz = X / period, Z / period
        best_d = np.full(X.shape, 1e9, np.float64)
        second_d = np.full(X.shape, 1e9, np.float64)
        best_band = np.zeros(X.shape, np.float64)
        second_band = np.zeros(X.shape, np.float64)
        n = np.uint64(n_bands)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                cx = np.floor(fx) + di
                cz = np.floor(fz) + dj
                ci, cj = cx.astype(np.int64), cz.astype(np.int64)
                jx = rand01(ci, cj, self.h + 3)
                jz = rand01(ci, cj, self.h + 4)
                px = cx + 0.5 + (jx - 0.5) * 0.8
                pz = cz + 0.5 + (jz - 0.5) * 0.8
                d2 = (fx - px) ** 2 + (fz - pz) ** 2
                band = (hash2(ci, cj, self.h + 5) % n).astype(np.float64)
                closer = d2 < best_d
                mid = (~closer) & (d2 < second_d)
                second_band = np.where(closer, best_band, np.where(mid, band, second_band))
                second_d = np.where(closer, best_d, np.where(mid, d2, second_d))
                best_band = np.where(closer, band, best_band)
                best_d = np.minimum(best_d, d2)
        return best_band, second_band, np.sqrt(best_d), np.sqrt(second_d)

    def _columns_v3(self, Q, R):
        """Separated altitude shelves, surfaces up to ~300, and walkable multi-scale relief."""
        Q = np.asarray(Q, dtype=np.int64)
        R = np.asarray(R, dtype=np.int64)
        X = HEX * SQ3 * (Q.astype(np.float64) + R.astype(np.float64) * 0.5)
        Z = HEX * 1.5 * R.astype(np.float64)
        s1 = self.island_scale
        wx = X + self.warp * self.n_warp1.fbm2(X / (s1 * 0.9), Z / (s1 * 0.9), 3)
        wz = Z + self.warp * self.n_warp2.fbm2(X / (s1 * 0.9) + 17.3, Z / (s1 * 0.9) - 4.1, 3)
        # a second, slower warp so ranges meander instead of sitting on a grid
        wx = wx + 28.0 * self.n_warp1.fbm2(X / 420.0, Z / 420.0, 2)
        wz = wz + 28.0 * self.n_warp2.fbm2(X / 420.0 + 9.1, Z / 420.0 - 3.4, 2)
        e = self.n_island.fbm2(wx / s1, wz / s1, 5) - self.coverage
        ei = self.n_islet.fbm2(wx / 38.0, wz / 38.0, 3) - (0.62 - self.islet_rate)

        mass = self.n_mass.fbm2(wx / s1, wz / s1, 2)
        period = max(float(s1) * 1.15, 260.0)
        n_bands = 8
        best_band, second_band, f1, f2 = self._worley_bands(X, Z, period, n_bands)
        # shelves from the low thirties up to ~250, leaving room for peaks near 300
        lo_alt, hi_alt = 34.0, 292.0
        bias = 6.0 * mass + 0.08 * (self.depth_amp - 40.0) + (self.alt_base - 59.0) * 0.35
        com1b = lo_alt + best_band / float(n_bands - 1) * (hi_alt - lo_alt)
        com2b = lo_alt + second_band / float(n_bands - 1) * (hi_alt - lo_alt)
        com1 = np.clip(com1b + bias, CLOUD_SEA + 16, 300.0)
        com2 = np.clip(com2b + bias, CLOUD_SEA + 16, 300.0)
        # soft merge vs gap, decided from band altitudes only (so the weight does
        # not flip between neighbours from local mass). overlapping or close
        # shelves blend into one landmass; far-apart shelves open a sky gap.
        up, down = 28.0, max(24.0, float(self.depth_amp) * 0.95)
        sep = np.abs(com1b - com2b) - (up + down)
        different = np.abs(best_band - second_band) >= 1.0
        # Height-blending close shelves produced steep neighbour steps (maxdt ~30)
        # and failed the 1.4.2 walkable-surface check. Shelves that would collide
        # are separated by a wide, noisy sky gap instead of a straight cut plane.
        merge_w = np.zeros(com1.shape, np.float64)
        com = com1
        shelf = com

        edge = f2 - f1
        wander = (0.050 * self.n_form.fbm2(X / 58.0, Z / 58.0, 3)
                  + 0.022 * self.n_spice.fbm2(X / 22.0, Z / 22.0, 2))
        edge_n = edge + wander
        gap_w = 0.11
        gap_amt = (1.0 - merge_w) * different.astype(np.float64)
        pull = (edge_n < gap_w) & (gap_amt > 0.25)
        e = np.where(pull, np.minimum(e, (edge_n - gap_w) * 2.6), e)
        ei = np.where(pull & (edge_n < gap_w * 0.82), np.minimum(ei, (edge_n - gap_w * 0.82) * 2.6), ei)

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
        realm[(mass > 0.08) & (shelf > 170) & (lum <= 0.40)] = CLOUDSTEP
        realm[(wet > 0.04) & (heat > -0.16) & (heat < 0.36) & (sp > 0.00) & (sp < 0.36) & (lum <= 0.40)
              & np.isin(realm, (MEADOW, FEN, BASALT, AMBER, VERDIGRIS, SALTWIND))] = VERDIGRIS
        realm[lum > 0.40] = LUMEN

        form = 0.5 + 0.5 * self.n_form.fbm2(X / 860.0, Z / 860.0, 2)
        plains = smoothstep(0.38, 0.18, form)
        hills_w = np.clip(1.0 - np.abs(form - 0.44) / 0.28, 0, 1)
        valleys = smoothstep(0.40, 0.62, form) * smoothstep(0.88, 0.68, form)
        mounts = smoothstep(0.42, 0.84, form)
        style = self.n_style.fbm2(X / 980.0, Z / 980.0, 2)
        # multi-scale relief with long wavelengths so neighbouring cells stay walkable (1–2 steps)
        hills = self.n_hill.fbm2(wx / 140.0, wz / 140.0, 3)
        fine = self.n_detail.fbm2(wx / 52.0, wz / 52.0, 2)
        ridge_m = 1.0 - np.abs(self.n_mount.fbm2(wx / 400.0, wz / 400.0, 2)) * 2
        inner = smoothstep(0.0, 0.18, e)
        flat = self.flatness
        rough = max(0.45, self.hill_amp / 10.0)
        peak_scale = (1.0 - 0.80 * flat)

        h = com.copy()
        h = h + (5.0 + 6.0 * rough) * hills * plains * inner * (1.0 - 0.80 * flat)
        h = h + (16.0 + self.hill_amp * 1.2) * (hills * 0.9 + 0.15 * fine) * hills_w * inner * peak_scale
        h = h - (14.0 + 10.0 * rough) * valleys * inner * np.clip(0.7 + 0.4 * hills, 0, 1.2) * (1.0 - 0.65 * flat)
        # long, walkable ranges; peaks climb tens of layers over many hexes, never as a wall
        mount = mounts * smoothstep(0.04, 0.24, e)
        alpine = (28.0 + self.mount_amp * 0.7) * mount * (0.55 + 0.45 * np.clip(ridge_m, 0, 1))
        # eroded mesas: a wide skirt so the cap never drops as a wall
        mesa_field = 0.5 + 0.5 * self.n_style.fbm2(wx / 380.0, wz / 380.0, 2)
        mesa = smoothstep(0.08, 0.82, mesa_field)
        mesa_h = (24.0 + self.mount_amp * 0.55) * mount * mesa
        h = h + np.where(style > 0.18, alpine, mesa_h) * peak_scale
        h = h + 2.4 * fine * inner * (1.0 - 0.85 * flat)
        h = h + np.where(realm == FROST, ridge_m * 6 * inner * peak_scale, 0)
        h = h + np.where(realm == DUNE, np.sin(wx / 16.0 + hills * 3) * 2.2 * inner, 0)
        h = np.where(realm == FEN, com + (h - com) * (0.72 - 0.20 * flat), h)
        h = np.where(realm == SALTWIND, com + (h - com) * (0.62 - 0.15 * flat), h)
        h = np.where(realm == CHALK, com + (h - com) * 0.85, h)
        h = np.where(realm == LAVENDER, com + (h - com) * (0.82 - 0.15 * flat), h)
        h = np.where(realm == CINDER, com + (h - com) * 0.90 + 2.0 * fine * inner, h)

        top = np.floor(h)
        terr = np.floor(h / 2.0) * 2.0
        top = np.where(realm == ROSE, terr, top)
        col_rand = rand01(Q, R, self.h)

        thick = self.depth_amp * (0.85 + 0.50 * self.n_depth.fbm2(X / 36.0, Z / 36.0, 3))
        thick = thick * (1.0 + 0.32 * mounts + 0.06 * plains)
        hull = smoothstep(0.0, 0.32, np.clip(e, 0, None))
        rho = 1.0 - hull
        dome = np.sqrt(np.clip(1.0 - rho * rho, 0, 1))
        depth = 4.0 + thick * (0.88 * dome + 0.22 * (hull ** 2))
        depth = depth + (rand01(Q, R, self.h + 1) ** 7) * 18 * hull
        depth = depth * np.where(np.isin(realm, (SALTWIND, CHALK, LAVENDER)), 0.78, 1.0)
        depth = depth * np.where(np.isin(realm, (CLOUDSTEP, CINDER, FROST)), 1.18, 1.0)
        top = top - np.floor((1.0 - hull) ** 2 * 2.4)
        bottom = top - np.floor(depth)

        # nibble only the land mask (never add cells) so a zero-contour cannot
        # run as a long straight hex-axis wall, without creating height steps
        coast = np.clip(1.0 - np.abs(e) / 0.12, 0.0, 1.0)
        wriggle = (0.08 * self.n_detail.fbm2(wx / 14.0, wz / 14.0, 2)
                   + 0.06 * self.n_spice.fbm2(wx / 7.0, wz / 7.0, 2))
        # only nibble (half the coast), never grow a new cell that could seam
        e_mask = e - coast * np.maximum(wriggle, 0.0)
        sk = (ei > 0) & (e_mask <= 0)
        sk_alt = np.floor(com + 8 + 16 * self.n_islet_alt.fbm2(X / 300.0, Z / 300.0, 2) + ei * 25)
        top = np.where(sk, sk_alt, top)
        sk_hull = smoothstep(0.0, 0.28, np.clip(ei, 0, None))
        sk_dome = np.sqrt(np.clip(1.0 - (1.0 - sk_hull) ** 2, 0, 1))
        bottom = np.where(sk, sk_alt - np.floor(2 + sk_dome * 28), bottom)
        land = (e_mask > 0) | sk
        top = np.clip(top, TOP_MIN, TOP_MAX).astype(np.int64)
        # compress the underside into the space above layer 2 so a low, thick
        # island keeps a domed bottom instead of a wide flat slice at the floor
        room = np.maximum(2, top - 4)
        thick = np.minimum(top - bottom, room)
        bottom = (top - thick).astype(np.int64)
        bottom = np.clip(bottom, 2, None)
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
                'skerry': sk, 'inner': inner, 'rand': col_rand, 'peak': top > (com + 28), 'com': com,
                'band': best_band}

    # ------------------------------------------------------------------ spires

    def _v4_stamp(self, X, Z, Q, R, period, accept_p, jitter, h_off, rad_kind,
                    reserved, allow, near_u, best_u, best_com, best_id, best_r, scale_id):
        """One jittered-grid island scale. Footprints stay inside `reserved`*period."""
        fx, fz = X / period, Z / period
        for di in (-2, -1, 0, 1, 2):
            for dj in (-2, -1, 0, 1, 2):
                ci = np.floor(fx).astype(np.int64) + di
                cj = np.floor(fz).astype(np.int64) + dj
                keep = (rand01(ci, cj, self.h + h_off + 1) < accept_p)
                jx = rand01(ci, cj, self.h + h_off + 2)
                jz = rand01(ci, cj, self.h + h_off + 3)
                px = (ci.astype(np.float64) + 0.5 + (jx - 0.5) * jitter) * period
                pz = (cj.astype(np.float64) + 0.5 + (jz - 0.5) * jitter) * period
                kind = rand01(ci, cj, self.h + h_off + 4)
                rad = period * rad_kind(kind)
                altn = rand01(ci, cj, self.h + h_off + 5)
                com = 46.0 + altn * 252.0 + (self.alt_base - 59.0) * 0.35
                com = np.clip(com, CLOUD_SEA + 16, 300.0)
                dx, dz = X - px, Z - pz
                # lobes + warp, then clamp to the reserved radius so neighbours never meet
                ang0 = rand01(ci, cj, self.h + h_off + 6) * 2.0 * np.pi
                ang1 = rand01(ci, cj, self.h + h_off + 7) * 2.0 * np.pi
                ang2 = rand01(ci, cj, self.h + h_off + 8) * 2.0 * np.pi
                stretch = 0.88 + 0.22 * rand01(ci, cj, self.h + h_off + 9)
                warp = (0.10 if scale_id == 0 else 0.07) * rad
                dx = dx + warp * self.n_detail.fbm2(X / (9.0 + 6.0 * scale_id), Z / (9.0 + 6.0 * scale_id), 2)
                dz = dz + warp * self.n_spice.fbm2(X / (8.0 + 5.0 * scale_id), Z / (8.0 + 5.0 * scale_id), 2)
                ca, sa = np.cos(ang0), np.sin(ang0)
                rx = dx * ca + dz * sa
                rz = (-dx * sa + dz * ca) / stretch
                d = np.sqrt(rx * rx + rz * rz)
                theta = np.arctan2(rz, rx)
                lobe = (0.18 * np.cos(2.0 * (theta - ang0)) +
                        0.10 * np.cos(3.0 * (theta - ang1)) +
                        0.06 * np.cos(5.0 * (theta - ang2)))
                # nibble-only coast noise (coves, not bulges past the budget)
                coast = self.n_detail.fbm2((X + px) / 11.0, (Z + pz) / 11.0, 2)
                coast2 = self.n_spice.fbm2((X + px) / 5.5, (Z + pz) / 5.5, 2)
                nibble = 0.10 * np.maximum(-coast, 0.0) + 0.06 * np.maximum(-coast2, 0.0)
                r_eff = rad * (1.0 + lobe) * (1.0 - nibble)
                # stretch extends the long axis; keep the world-space reach in budget
                r_eff = np.minimum(r_eff, reserved * period / np.maximum(stretch, 1.0))
                u = d / (r_eff + 1e-6)
                near = keep & allow & (u < near_u)
                near_u = np.where(near, u, near_u)
                hit = keep & allow & (u < 1.0) & (u < best_u)
                best_u = np.where(hit, u, best_u)
                best_com = np.where(hit, com, best_com)
                best_r = np.where(hit, r_eff, best_r)
                ident = (ci.astype(np.float64) * 131071.0 + cj.astype(np.float64) +
                         float(scale_id) * 1000000000.0)
                best_id = np.where(hit, ident, best_id)
        return near_u, best_u, best_com, best_id, best_r

    def _columns_v4(self, Q, R):
        """Discrete islands on three jittered grids: continents, medium, small.

        Neighbouring centres are far enough, and each footprint is clamped to a
        reserved radius, so volumes never intersect and there is no Worley cut
        plane. Large islands are irregular, flat-topped landmasses; medium and
        small ones fill the gaps. Undersides are rounded domes above layer 2.
        """
        Q = np.asarray(Q, dtype=np.int64)
        R = np.asarray(R, dtype=np.int64)
        X = HEX * SQ3 * (Q.astype(np.float64) + R.astype(np.float64) * 0.5)
        Z = HEX * 1.5 * R.astype(np.float64)
        scale = float(self.island_scale)
        # three scales. reserved fractions stay under the jittered min centre gap
        # (1 - jitter) so even a noisy, lobed coast cannot meet its neighbour.
        period_L = float(np.clip(max(360.0, scale * 1.85), 360.0, 640.0))
        period_M = float(np.clip(max(170.0, scale * 0.90), 170.0, 300.0))
        period_S = float(np.clip(max(80.0, scale * 0.48), 80.0, 150.0))
        dens = (0.06 - float(self.coverage)) / 0.20
        accept_L = float(np.clip(0.26 - dens * 0.10, 0.16, 0.36))
        accept_M = float(np.clip(0.42 - dens * 0.12, 0.28, 0.58))
        accept_S = float(np.clip(0.50 - dens * 0.14, 0.32, 0.70))
        jitter = 0.15
        best_u = np.full(X.shape, 10.0, np.float64)
        near_u = np.full(X.shape, 10.0, np.float64)
        best_com = np.zeros(X.shape, np.float64)
        best_id = np.full(X.shape, -1.0, np.float64)
        best_r = np.ones(X.shape, np.float64)
        # large: a few continents, hundreds of cells across, mixed with big-medium
        def rad_L(kind):
            return np.where(kind > 0.82, 0.30, np.where(kind > 0.45, 0.24, 0.18))
        near_L = np.full(X.shape, 10.0, np.float64)
        near_L, best_u, best_com, best_id, best_r = self._v4_stamp(
            X, Z, Q, R, period_L, accept_L, jitter, 20, rad_L, 0.40,
            True, near_L, best_u, best_com, best_id, best_r, 0)
        near_u = np.minimum(near_u, near_L)
        # medium: only in the open water around continents
        allow_M = near_L > 1.30
        def rad_M(kind):
            return np.where(kind > 0.65, 0.22, np.where(kind > 0.30, 0.16, 0.11))
        near_M = np.full(X.shape, 10.0, np.float64)
        near_M, best_u, best_com, best_id, best_r = self._v4_stamp(
            X, Z, Q, R, period_M, accept_M, jitter, 40, rad_M, 0.38,
            allow_M, near_M, best_u, best_com, best_id, best_r, 1)
        near_u = np.minimum(near_u, near_M)
        # small islets, held off both larger scales
        allow_S = (near_L > 1.35) & (near_M > 1.35)
        def rad_S(kind):
            return np.where(kind > 0.55, 0.20, 0.12)
        near_S = np.full(X.shape, 10.0, np.float64)
        near_S, best_u, best_com, best_id, best_r = self._v4_stamp(
            X, Z, Q, R, period_S, accept_S, jitter, 60, rad_S, 0.36,
            allow_S, near_S, best_u, best_com, best_id, best_r, 2)
        near_u = np.minimum(near_u, near_S)

        inside = best_u < 1.0
        # nibble-only outer rim so a hex-axis coast cannot run for 12+ cells
        rim = inside & (best_u > 0.80)
        nibble = rim & (rand01(Q, R, self.h + 41) > 0.55)
        inside = inside & ~nibble
        best_u = np.where(nibble, 1.05, best_u)
        e = np.where(inside, 1.0 - best_u, 1.0 - near_u)
        com = best_com
        shelf = com

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
        realm[(inside) & (shelf > 170) & (lum <= 0.40)] = CLOUDSTEP
        realm[(wet > 0.04) & (heat > -0.16) & (heat < 0.36) & (sp > 0.00) & (sp < 0.36) & (lum <= 0.40)
              & np.isin(realm, (MEADOW, FEN, BASALT, AMBER, VERDIGRIS, SALTWIND))] = VERDIGRIS
        realm[lum > 0.40] = LUMEN

        # wide walkable plateau on large islands; shorter radial fade on small ones
        fade = np.where(best_r > 80.0, 0.12, np.where(best_r > 36.0, 0.20, 0.28))
        inner = (best_u - 1.0) / (fade - 1.0)
        inner = np.clip(inner, 0.0, 1.0)
        inner = inner * inner * (3.0 - 2.0 * inner)
        hills = self.n_hill.fbm2(X / 160.0, Z / 160.0, 3)
        fine = self.n_detail.fbm2(X / 64.0, Z / 64.0, 2)
        ridge_m = 1.0 - np.abs(self.n_mount.fbm2(X / 400.0, Z / 400.0, 2)) * 2
        form = 0.5 + 0.5 * self.n_form.fbm2(X / 860.0, Z / 860.0, 2)
        mounts = smoothstep(0.42, 0.84, form)
        flat = self.flatness
        rough = max(0.45, self.hill_amp / 10.0)
        peak_scale = (1.0 - 0.80 * flat)
        h = com.copy()
        h = h + (4.0 + 4.0 * rough) * hills * inner * (1.0 - 0.80 * flat)
        h = h + (7.0 + self.hill_amp * 0.6) * (hills * 0.9 + 0.15 * fine) * inner * peak_scale
        alpine = (12.0 + self.mount_amp * 0.35) * mounts * (0.55 + 0.45 * np.clip(ridge_m, 0, 1)) * inner * peak_scale
        h = h + alpine
        h = h + 1.6 * fine * inner * (1.0 - 0.85 * flat)
        h = np.where(realm == FROST, h + ridge_m * 3 * inner * peak_scale, h)
        h = np.where(realm == DUNE, h + np.sin(X / 16.0 + hills * 3) * 1.5 * inner, h)
        h = np.where(realm == FEN, com + (h - com) * (0.72 - 0.20 * flat), h)
        h = np.where(realm == SALTWIND, com + (h - com) * (0.62 - 0.15 * flat), h)
        rim = np.clip((best_u - 0.84) / 0.16, 0.0, 1.0)
        h = h - rim * 2.0
        top = np.floor(h)
        terr = np.floor(h / 2.0) * 2.0
        top = np.where(realm == ROSE, terr, top)

        thick = self.depth_amp * (0.85 + 0.50 * self.n_depth.fbm2(X / 36.0, Z / 36.0, 3))
        thick = thick * (1.0 + 0.28 * mounts)
        dome = 0.5 * (1.0 + np.cos(np.pi * np.clip(best_u, 0, 1)))
        depth = 4.0 + thick * (0.90 * dome + 0.10)
        depth = depth * np.where(np.isin(realm, (SALTWIND, CHALK, LAVENDER)), 0.78, 1.0)
        depth = depth * np.where(np.isin(realm, (CLOUDSTEP, CINDER, FROST)), 1.18, 1.0)
        avail = np.maximum(4.0, top - 2.0)
        r_cells = np.maximum(6.0, best_r / 1.5)
        depth = np.minimum(depth, 2.0 + (avail - 2.0) * (0.88 * dome + 0.12))
        depth = np.minimum(depth, 3.2 * r_cells * (0.90 * dome + 0.10) + 2.0)
        bottom = top - np.floor(depth)

        ei = self.n_islet.fbm2(X / 38.0, Z / 38.0, 3) - (0.70 - self.islet_rate)
        sk = (~inside) & (ei > 0) & (near_u > 1.40)
        sk_alt = np.floor(46 + 40 * self.n_islet_alt.fbm2(X / 300.0, Z / 300.0, 2) + ei * 25)
        top = np.where(sk, sk_alt, top)
        sk_dome = np.sqrt(np.clip(ei / 0.35, 0, 1))
        sk_depth = 2.0 + sk_dome * 18.0
        sk_avail = np.maximum(4.0, sk_alt - 2.0)
        sk_depth = np.minimum(sk_depth, 2.0 + (sk_avail - 2.0) * (0.88 * sk_dome + 0.12))
        bottom = np.where(sk, sk_alt - np.floor(sk_depth), bottom)
        land = inside | sk
        e = np.where(sk, np.maximum(e, ei), e)

        top = np.clip(top, TOP_MIN, TOP_MAX).astype(np.int64)
        bottom = np.clip(bottom, 2, None).astype(np.int64)
        bottom = np.minimum(bottom, top - 2)
        col_rand = rand01(Q, R, self.h)
        inner = np.where(land, np.maximum(inner, np.where(sk, smoothstep(0.0, 0.28, ei), 0)), 0)
        wmul = self.water_mul
        pool_t = np.where(np.isin(realm, (FEN, SALTWIND, VERDIGRIS)), 0.14 - 0.10 * wmul,
                          np.where(np.isin(realm, (BASALT, MEADOW, LAVENDER, CEDAR)), 0.50 - 0.16 * wmul, 9.0))
        pool_t = np.where(np.isin(realm, (CINDER, DUNE, CHALK)), 0.75 - 0.10 * wmul, pool_t)
        pooln = self.n_pool.fbm2(X / 26.0, Z / 26.0, 2)
        pool = land & ~sk & (e > 0.12) & (pooln > pool_t) & (wmul > 0.2)
        fall = land & ~sk & (e > 0.0) & (e < 0.10) & (rand01(Q, R, self.h + 2) < (0.012 * wmul)) & \
            np.isin(realm, (MEADOW, AMBER, FEN, BASALT, LUMEN, CEDAR, VERDIGRIS, CLOUDSTEP, LAVENDER))
        return {'e': e, 'land': land, 'top': top, 'bottom': bottom, 'realm': realm, 'pool': pool, 'fall': fall,
                'skerry': sk, 'inner': inner, 'rand': col_rand, 'peak': land & (top > (com + 24)), 'com': com,
                'band': best_id}


    def _columns_v5(self, Q, R):
        """v4 layout, scaled up, plus a rare huge-continent tier.

        Standard, medium and large footprints (and depth) grow about 30%. A
        fourth jittered grid plants a few huge continents, 350–500 cells across,
        with mixed biomes, taller relief, valleys and inland lakes. Neighbours
        still cannot meet: each scale keeps a reserved radius inside the
        jittered centre gap, and smaller islands only spawn in open water.
        """
        Q = np.asarray(Q, dtype=np.int64)
        R = np.asarray(R, dtype=np.int64)
        X = HEX * SQ3 * (Q.astype(np.float64) + R.astype(np.float64) * 0.5)
        Z = HEX * 1.5 * R.astype(np.float64)
        scale = float(self.island_scale)
        # ~30% larger periods so radii can grow without eating the reserved gap.
        period_H = float(np.clip(max(1100.0, scale * 3.80), 1100.0, 1250.0))
        period_L = float(np.clip(max(468.0, scale * 2.40), 468.0, 832.0))
        period_M = float(np.clip(max(221.0, scale * 1.17), 221.0, 390.0))
        period_S = float(np.clip(max(104.0, scale * 0.62), 104.0, 195.0))
        dens = (0.06 - float(self.coverage)) / 0.20
        accept_H = float(np.clip(0.12 - dens * 0.04, 0.07, 0.16))
        accept_L = float(np.clip(0.28 - dens * 0.10, 0.18, 0.40))
        accept_M = float(np.clip(0.46 - dens * 0.12, 0.30, 0.62))
        accept_S = float(np.clip(0.54 - dens * 0.14, 0.34, 0.74))
        jitter = 0.15
        best_u = np.full(X.shape, 10.0, np.float64)
        near_u = np.full(X.shape, 10.0, np.float64)
        best_com = np.zeros(X.shape, np.float64)
        best_id = np.full(X.shape, -1.0, np.float64)
        best_r = np.ones(X.shape, np.float64)
        # huge continents first, so smaller scales leave them a wide berth
        def rad_H(kind):
            return np.where(kind > 0.70, 0.30, np.where(kind > 0.35, 0.28, 0.26))
        near_H = np.full(X.shape, 10.0, np.float64)
        near_H, best_u, best_com, best_id, best_r = self._v4_stamp(
            X, Z, Q, R, period_H, accept_H, jitter, 10, rad_H, 0.38,
            True, near_H, best_u, best_com, best_id, best_r, 3)
        near_u = np.minimum(near_u, near_H)
        def rad_L(kind):
            return np.where(kind > 0.82, 0.30, np.where(kind > 0.45, 0.24, 0.18))
        allow_L = near_H > 1.30
        near_L = np.full(X.shape, 10.0, np.float64)
        near_L, best_u, best_com, best_id, best_r = self._v4_stamp(
            X, Z, Q, R, period_L, accept_L, jitter, 20, rad_L, 0.40,
            allow_L, near_L, best_u, best_com, best_id, best_r, 0)
        near_u = np.minimum(near_u, near_L)
        allow_M = (near_H > 1.32) & (near_L > 1.30)
        def rad_M(kind):
            return np.where(kind > 0.65, 0.22, np.where(kind > 0.30, 0.16, 0.11))
        near_M = np.full(X.shape, 10.0, np.float64)
        near_M, best_u, best_com, best_id, best_r = self._v4_stamp(
            X, Z, Q, R, period_M, accept_M, jitter, 40, rad_M, 0.38,
            allow_M, near_M, best_u, best_com, best_id, best_r, 1)
        near_u = np.minimum(near_u, near_M)
        allow_S = (near_H > 1.35) & (near_L > 1.35) & (near_M > 1.35)
        def rad_S(kind):
            return np.where(kind > 0.55, 0.20, 0.12)
        near_S = np.full(X.shape, 10.0, np.float64)
        near_S, best_u, best_com, best_id, best_r = self._v4_stamp(
            X, Z, Q, R, period_S, accept_S, jitter, 60, rad_S, 0.36,
            allow_S, near_S, best_u, best_com, best_id, best_r, 2)
        near_u = np.minimum(near_u, near_S)

        inside = best_u < 1.0
        rim = inside & (best_u > 0.80)
        nibble = rim & (rand01(Q, R, self.h + 41) > 0.55)
        inside = inside & ~nibble
        best_u = np.where(nibble, 1.05, best_u)
        e = np.where(inside, 1.0 - best_u, 1.0 - near_u)
        com = best_com
        shelf = com
        huge = best_r > 200.0

        # shorter biome wavelength on huge land so one continent holds several landscapes
        rscale = np.where(huge, self.realm_scale * 0.42, self.realm_scale)
        heat = self.n_heat.fbm2(X / rscale, Z / rscale, 3) * 1.5 + self.heat_bias
        wet = self.n_wet.fbm2(X / rscale, Z / rscale, 3) * 1.5 + self.wet_bias
        lum = self.n_lumen.fbm2(X / (rscale * 0.7), Z / (rscale * 0.7), 2)
        sp = self.n_spice.fbm2(X / (rscale * 0.85), Z / (rscale * 0.85), 3)
        realm = np.full(Q.shape, MEADOW, dtype=np.int64)
        realm[heat > 0.05] = AMBER
        realm[(heat > 0.30) & (wet >= -0.05)] = ROSE
        realm[(heat > 0.30) & (wet < -0.05)] = DUNE
        realm[(wet > 0.28) & (heat <= 0.30)] = FEN
        realm[(wet < -0.30) & (heat <= 0.30)] = BASALT
        realm[heat < -0.28] = FROST
        realm[lum > 0.40] = LUMEN
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
        realm[(inside) & (shelf > 170) & (lum <= 0.40)] = CLOUDSTEP
        realm[(wet > 0.04) & (heat > -0.16) & (heat < 0.36) & (sp > 0.00) & (sp < 0.36) & (lum <= 0.40)
              & np.isin(realm, (MEADOW, FEN, BASALT, AMBER, VERDIGRIS, SALTWIND))] = VERDIGRIS
        realm[lum > 0.40] = LUMEN

        fade = np.where(best_r > 200.0, 0.08, np.where(best_r > 80.0, 0.12, np.where(best_r > 36.0, 0.20, 0.28)))
        inner = (best_u - 1.0) / (fade - 1.0)
        inner = np.clip(inner, 0.0, 1.0)
        inner = inner * inner * (3.0 - 2.0 * inner)
        hills = self.n_hill.fbm2(X / 160.0, Z / 160.0, 3)
        fine = self.n_detail.fbm2(X / 64.0, Z / 64.0, 2)
        ridge_m = 1.0 - np.abs(self.n_mount.fbm2(X / 400.0, Z / 400.0, 2)) * 2
        form = 0.5 + 0.5 * self.n_form.fbm2(X / 860.0, Z / 860.0, 2)
        mounts = smoothstep(0.42, 0.84, form)
        flat = self.flatness
        rough = max(0.45, self.hill_amp / 10.0)
        peak_scale = (1.0 - 0.80 * flat)
        h = com.copy()
        h = h + (4.0 + 4.0 * rough) * hills * inner * (1.0 - 0.80 * flat)
        h = h + (7.0 + self.hill_amp * 0.6) * (hills * 0.9 + 0.15 * fine) * inner * peak_scale
        alpine = (12.0 + self.mount_amp * 0.35) * mounts * (0.55 + 0.45 * np.clip(ridge_m, 0, 1)) * inner * peak_scale
        h = h + alpine
        h = h + 1.6 * fine * inner * (1.0 - 0.85 * flat)
        # broad valleys on huge continents
        valley = self.n_form.fbm2(X / 240.0, Z / 240.0, 2)
        h = h - np.where(huge, (9.0 + 4.0 * rough) * np.maximum(0.0, 0.22 - valley) * inner * peak_scale, 0.0)
        h = np.where(realm == FROST, h + ridge_m * 3 * inner * peak_scale, h)
        h = np.where(realm == DUNE, h + np.sin(X / 16.0 + hills * 3) * 1.5 * inner, h)
        h = np.where(realm == FEN, com + (h - com) * (0.72 - 0.20 * flat), h)
        h = np.where(realm == SALTWIND, com + (h - com) * (0.62 - 0.15 * flat), h)
        rim = np.clip((best_u - 0.84) / 0.16, 0.0, 1.0)
        h = h - rim * 2.0
        top = np.floor(h)
        terr = np.floor(h / 2.0) * 2.0
        top = np.where(realm == ROSE, terr, top)

        # depth grows with the 30% footprint scale, still a cosine dome above layer 2
        thick = self.depth_amp * 1.30 * (0.85 + 0.50 * self.n_depth.fbm2(X / 36.0, Z / 36.0, 3))
        thick = thick * (1.0 + 0.28 * mounts)
        thick = np.where(huge, thick * 1.15, thick)
        dome = 0.5 * (1.0 + np.cos(np.pi * np.clip(best_u, 0, 1)))
        depth = 4.0 + thick * (0.90 * dome + 0.10)
        depth = depth * np.where(np.isin(realm, (SALTWIND, CHALK, LAVENDER)), 0.78, 1.0)
        depth = depth * np.where(np.isin(realm, (CLOUDSTEP, CINDER, FROST)), 1.18, 1.0)
        avail = np.maximum(4.0, top - 2.0)
        r_cells = np.maximum(6.0, best_r / 1.5)
        depth = np.minimum(depth, 2.0 + (avail - 2.0) * (0.88 * dome + 0.12))
        depth = np.minimum(depth, 3.2 * r_cells * (0.90 * dome + 0.10) + 2.0)
        bottom = top - np.floor(depth)

        ei = self.n_islet.fbm2(X / 38.0, Z / 38.0, 3) - (0.70 - self.islet_rate)
        sk = (~inside) & (ei > 0) & (near_u > 1.40)
        sk_alt = np.floor(46 + 40 * self.n_islet_alt.fbm2(X / 300.0, Z / 300.0, 2) + ei * 25)
        top = np.where(sk, sk_alt, top)
        sk_dome = np.sqrt(np.clip(ei / 0.35, 0, 1))
        sk_depth = 2.0 + sk_dome * 18.0
        sk_avail = np.maximum(4.0, sk_alt - 2.0)
        sk_depth = np.minimum(sk_depth, 2.0 + (sk_avail - 2.0) * (0.88 * sk_dome + 0.12))
        bottom = np.where(sk, sk_alt - np.floor(sk_depth), bottom)
        land = inside | sk
        e = np.where(sk, np.maximum(e, ei), e)

        top = np.clip(top, TOP_MIN, TOP_MAX).astype(np.int64)
        bottom = np.clip(bottom, 2, None).astype(np.int64)
        bottom = np.minimum(bottom, top - 2)
        col_rand = rand01(Q, R, self.h)
        inner = np.where(land, np.maximum(inner, np.where(sk, smoothstep(0.0, 0.28, ei), 0)), 0)
        wmul = self.water_mul
        pool_t = np.where(np.isin(realm, (FEN, SALTWIND, VERDIGRIS)), 0.14 - 0.10 * wmul,
                          np.where(np.isin(realm, (BASALT, MEADOW, LAVENDER, CEDAR)), 0.50 - 0.16 * wmul, 9.0))
        pool_t = np.where(np.isin(realm, (CINDER, DUNE, CHALK)), 0.75 - 0.10 * wmul, pool_t)
        # huge inland basins hold more lakes
        pool_t = np.where(huge & (best_u < 0.72), pool_t - 0.16, pool_t)
        pooln = self.n_pool.fbm2(X / 26.0, Z / 26.0, 2)
        pool = land & ~sk & (e > 0.12) & (pooln > pool_t) & (wmul > 0.2)
        fall = land & ~sk & (e > 0.0) & (e < 0.10) & (rand01(Q, R, self.h + 2) < (0.012 * wmul)) & \
            np.isin(realm, (MEADOW, AMBER, FEN, BASALT, LUMEN, CEDAR, VERDIGRIS, CLOUDSTEP, LAVENDER))
        return {'e': e, 'land': land, 'top': top, 'bottom': bottom, 'realm': realm, 'pool': pool, 'fall': fall,
                'skerry': sk, 'inner': inner, 'rand': col_rand, 'peak': land & (top > (com + 24)), 'com': com,
                'band': best_id}

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
        if self.tutorial:
            from . import tutorial as TUT
            return TUT.generate_chunk(cq, cr)
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
            original = cells.copy()
            roof_d = 5 if self.version >= 2 else 3
            deep = (dd >= roof_d) & ((idx[1] - B[idx[0], 0, idx[2]]) >= 3)
            if self.version >= 2:
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
                small = self.n_room.noise3(xx / (18.0 * cs), yy / (10.0 * cs), zz / (18.0 * cs)) > max(0.30, 0.52 - amt * 0.6)
                midc = self.n_tunnel.noise3(xx / (34.0 * cs), yy / (16.0 * cs), zz / (34.0 * cs)) > max(0.28, 0.46 - amt * 0.5)
                huge = self.n_room.noise3(xx / (70.0 * cs) + 4.4, yy / (28.0 * cs), zz / (70.0 * cs)) > max(0.42, 0.62 - amt * 0.25)
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
            roof = 5 if self.version >= 2 else 2
            band = (dd >= roof) & (dd <= 9) & ((idx[1] - B[idx[0], 0, idx[2]]) >= 4)
            if band.any():
                na = self.n_arch.noise3(xx / 11.0, yy / 4.5, zz / 11.0)
                thr = self.arches + (0.14 if self.version >= 2 else 0.0)
                hole |= band & (na > thr)
            cells[idx[0][hole], idx[1][hole], idx[2][hole]] = 0
            # v2: fill any cave that opens onto the outside, then cut a few framed mouths
            if self.version >= 2:
                cave = solid & (cells == 0)
                near = ~solid
                for _ in range(2):
                    near = _dilate_hex(near)
                heal = cave & near
                # always keep a solid roof (the walking surface and the lip under it)
                yy = np.arange(LAYERS, dtype=np.int64)[None, :, None]
                heal = heal | (cave & ((T - yy) < 5))
                cells[heal] = original[heal]
                # a mouth is a healed flank cell with open sky beside it, well under the roof
                ext = ~solid
                has_ext = np.zeros(cells.shape, bool)
                for da, db in ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)):
                    a0, a1 = max(0, da), CHUNK + min(0, da)
                    b0, b1 = max(0, db), CHUNK + min(0, db)
                    has_ext[a0:a1, :, b0:b1] |= ext[a0 - da:a1 - da, :, b0 - db:b1 - db]
                HEX_N = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
                interior = solid & (cells == 0)
                reach = interior.copy()
                for _ in range(4):
                    reach = _dilate_hex(reach)
                # start the tunnel on the shell, where a remaining cave is a short walk inside
                cand = reach & has_ext & solid & ((T - yy) >= 6) & ((yy - B) >= 3) & ((T - yy) <= 18)
                col_hit = cand.any(1)
                roll = rand01(Q[sl], R[sl], self.h + 91)
                pick = col_hit & (roll < 0.07)
                if not pick.any() and col_hit.any():
                    # at least one mouth in the chunk if a cave is waiting just inside
                    ia0, ib0 = np.nonzero(col_hit)
                    k = int(np.argmin(roll[col_hit]))
                    pick = np.zeros_like(col_hit)
                    pick[ia0[k], ib0[k]] = True
                ia, ib = np.nonzero(pick)
                if len(ia) > 2:
                    # keep the two with the lowest roll so a chunk does not look like Swiss cheese
                    order = np.argsort(roll[pick])
                    keep = set(zip(ia[order[:2]], ib[order[:2]]))
                    ia, ib = zip(*keep) if keep else ((), ())
                    ia, ib = list(ia), list(ib)
                frame = M['cobble']
                for a, b in zip(ia, ib):
                    ys = np.flatnonzero(cand[a, :, b])
                    if len(ys) == 0:
                        continue
                    y = int(ys[len(ys) // 2])
                    y2 = y + 1 if y + 1 < LAYERS else y
                    # tunnel a couple of cells inward until we reach the remaining cave
                    path = [(a, b)]
                    ca, cb = a, b
                    for _ in range(5):
                        nxt = None
                        for da, db in HEX_N:
                            na, nb = ca + da, cb + db
                            if not (0 <= na < CHUNK and 0 <= nb < CHUNK):
                                continue
                            if not solid[na, y, nb] or has_ext[na, y, nb]:
                                continue
                            if (na, nb) in path:
                                continue
                            nxt = (na, nb)
                            if interior[na, y, nb] or interior[na, min(y2, LAYERS - 1), nb]:
                                break
                        if nxt is None:
                            break
                        path.append(nxt)
                        if interior[nxt[0], y, nxt[1]] or interior[nxt[0], min(y2, LAYERS - 1), nxt[1]]:
                            break
                        ca, cb = nxt
                    for pa, pb in path:
                        cells[pa, y, pb] = 0
                        cells[pa, y2, pb] = 0
                    for dy in (-1, 0, 1, 2):
                        ny = y + dy
                        if ny < 0 or ny >= LAYERS:
                            continue
                        if (T[a, 0, b] - ny) < 2:
                            continue
                        for da, db in HEX_N:
                            na, nb = a + da, b + db
                            if not (0 <= na < CHUNK and 0 <= nb < CHUNK):
                                continue
                            if cells[na, ny, nb] != 0 and (na, ny, nb) not in (
                                (p[0], y, p[1]) for p in path) and (na, ny, nb) not in (
                                (p[0], y2, p[1]) for p in path):
                                cells[na, ny, nb] = frame
                        if dy in (-1, 2) and cells[a, ny, b] != 0:
                            cells[a, ny, b] = frame
            # glowcaps and crystals on cave floors
            cave_now = (cells == 0) & solid
            if cave_now.any():
                ca, cy, cb = np.nonzero(cave_now)
                flg = rand01(Q[sl][ca, cb].astype(np.int64), R[sl][ca, cb].astype(np.int64) * 7 + cy, self.h + 31) < 0.04
                for a, y, b in zip(ca[flg], cy[flg], cb[flg]):
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
        if self.version >= 2:
            self._decorate_v2(cells, Q[sl], R[sl], top, bot, land, pool, fall, realm, surf_top, on_turf, free)
        else:
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
        if self.version >= 2:
            from . import structures as ST
            ST.place(self, cq, cr, cells, meta, col, sl)
        return cells, meta, realm.astype(np.uint8)

    def _decorate_v2(self, cells, Q, R, top, bot, land, pool, fall, realm, surf_top, on_turf, free):
        """Richer, biome-specific ground cover: mixed plants, clusters, and sub-variations."""
        # each biome: list of (mat, rate). rates are per-column chances on a plantable surface.
        tables = {
            MEADOW:    [(M['grass'], 0.28), (M['wildflower'], 0.08), (M['petals'], 0.07), (M['sprout'], 0.05),
                        (M['shrub'], 0.03), (M['bloom'], 0.015), (M['pebble'], 0.02)],
            AMBER:     [(M['grass'], 0.16), (M['petals'], 0.08), (M['shrub'], 0.05), (M['sprout'], 0.04),
                        (M['wildflower'], 0.03), (M['pebble'], 0.02)],
            ROSE:      [(M['bloom'], 0.06), (M['petals'], 0.10), (M['wildflower'], 0.07), (M['grass'], 0.08),
                        (M['pebble'], 0.04), (M['shrub'], 0.02)],
            FROST:     [(M['crystal'], 0.06), (M['pebble'], 0.08), (M['sprout'], 0.02)],
            BASALT:    [(M['pebble'], 0.10), (M['grass'], 0.08), (M['sprout'], 0.04), (M['mushroom'], 0.02),
                        (M['shrub'], 0.02)],
            FEN:       [(M['reeds'], 0.14), (M['grass'], 0.12), (M['mushroom'], 0.05), (M['vine'], 0.04),
                        (M['sprout'], 0.05), (M['shrub'], 0.03)],
            DUNE:      [(M['pebble'], 0.08), (M['sprout'], 0.03), (M['grass'], 0.02)],
            LUMEN:     [(M['glowcap'], 0.10), (M['bloom'], 0.05), (M['crystal'], 0.04), (M['wildflower'], 0.04),
                        (M['grass'], 0.06)],
            SALTWIND:  [(M['reeds'], 0.10), (M['pebble'], 0.08), (M['grass'], 0.05), (M['sprout'], 0.03)],
            CEDAR:     [(M['mushroom'], 0.06), (M['shrub'], 0.07), (M['grass'], 0.12), (M['vine'], 0.03),
                        (M['sprout'], 0.04), (M['petals'], 0.03)],
            LAVENDER:  [(M['wildflower'], 0.12), (M['petals'], 0.10), (M['grass'], 0.16), (M['shrub'], 0.05),
                        (M['bloom'], 0.03)],
            CINDER:    [(M['pebble'], 0.10), (M['crystal'], 0.03), (M['sprout'], 0.02)],
            CHALK:     [(M['pebble'], 0.12), (M['sprout'], 0.03), (M['grass'], 0.04), (M['wildflower'], 0.02)],
            STARFALL:  [(M['crystal'], 0.08), (M['bloom'], 0.05), (M['glowcap'], 0.04), (M['wildflower'], 0.04),
                        (M['grass'], 0.06)],
            CLOUDSTEP: [(M['grass'], 0.10), (M['petals'], 0.06), (M['crystal'], 0.03), (M['wildflower'], 0.03)],
            VERDIGRIS: [(M['vine'], 0.06), (M['mushroom'], 0.05), (M['reeds'], 0.05), (M['grass'], 0.10),
                        (M['shrub'], 0.04), (M['sprout'], 0.04)],
        }
        planted = np.zeros(top.shape, bool)
        # ground-cover mixes: patchy surface swaps (heather, moss, cobble, clay) for sub-variation
        det = self.n_detail.fbm2(Q.astype(np.float64) / 7.0, R.astype(np.float64) / 7.0, 2)
        patch = self.n_spice.fbm2(Q.astype(np.float64) / 18.0, R.astype(np.float64) / 18.0, 2)
        cover = [
            (LAVENDER, 0.18, M['heather'], 0.05),
            (VERDIGRIS, 0.12, M['mossrock'], -0.05),
            (FEN, 0.10, M['mossrock'], -0.1),
            (CHALK, 0.12, M['cobble'], 0.1),
            (CEDAR, 0.08, M['mossrock'], -0.15),
            (SALTWIND, 0.08, M['salt_block'], 0.0),
            (MEADOW, 0.05, M['heather'], 0.2),
        ]
        for bio, rate, mat, lo in cover:
            hit = free & (realm == bio) & (surf_top == M['turf']) & (patch > lo) & (
                rand01(Q, R, self.h + 41 + bio) < rate)
            ii, kk = np.nonzero(hit)
            for i, k in zip(ii, kk):
                cells[i, top[i, k], k] = mat
        # refresh plantable mask after cover swaps
        surf_top = cells[np.arange(CHUNK)[:, None], top, np.arange(CHUNK)[None, :]]
        plantable = free & np.isin(surf_top, (M['turf'], M['snow'], M['sand'], M['heather'], M['mossrock'],
                                             M['chalk'], M['cinder'], M['pale_stone']))
        # scatter each species, then bloom it into a small cluster around a few seeds
        for bio, rows in tables.items():
            in_b = plantable & (realm == bio)
            if not in_b.any():
                continue
            for j, (mat, rate) in enumerate(rows):
                rnd = rand01(Q, R, self.h + 50 + bio * 8 + j)
                seed = in_b & ~planted & (rnd < rate)
                # cluster seeds: a slower noise makes patches of the same plant
                clump = in_b & ~planted & (self.n_detail.fbm2(
                    (Q.astype(np.float64) + 13 * j) / 5.0,
                    (R.astype(np.float64) - 7 * j) / 5.0, 2) > 0.32) & (rnd < rate * 2.2)
                hit = seed | clump
                ii, kk = np.nonzero(hit)
                for i, k in zip(ii, kk):
                    y = int(top[i, k]) + 1
                    if 0 <= y < LAYERS and cells[i, y, k] == 0:
                        cells[i, y, k] = mat
                        planted[i, k] = True
        # a few extra berry bushes in wooded biomes (keep some of the old flavour)
        bush_rate = np.take([0.010, 0.018, 0.003, 0.0, 0.005, 0.016, 0.0, 0.003,
                             0.006, 0.020, 0.012, 0.0, 0.003, 0.004, 0.004, 0.010], np.clip(realm, 0, 15))
        bush = plantable & ~planted & (rand01(Q, R, self.h + 6) < bush_rate)
        ii, kk = np.nonzero(bush)
        for i, k in zip(ii, kk):
            y = int(top[i, k]) + 1
            if 0 <= y < LAYERS and cells[i, y, k] == 0:
                cells[i, y, k] = M['berry_bush']
        under = land & (rand01(Q, R, self.h + 6) < 0.02) & (bot > CLOUD_SEA + 3) & ~fall
        ii, kk = np.nonzero(under)
        for i, k in zip(ii, kk):
            y = int(bot[i, k]) - 1
            if y > 0 and cells[i, int(bot[i, k]), k] and cells[i, y, k] == 0:
                cells[i, y, k] = M['lumen_shard']
        # mushrooms prefer the shade just under a would-be tree density, and the underside lip
        shade = plantable & np.isin(realm, (CEDAR, FEN, VERDIGRIS, MEADOW, BASALT))
        mush = shade & ~planted & (rand01(Q, R, self.h + 77) < 0.018)
        ii, kk = np.nonzero(mush)
        for i, k in zip(ii, kk):
            y = int(top[i, k]) + 1
            if 0 <= y < LAYERS and cells[i, y, k] == 0:
                cells[i, y, k] = M['mushroom']
        # reeds along the water's edge
        wet = free & np.isin(realm, (FEN, SALTWIND, VERDIGRIS, MEADOW, LAVENDER))
        # a neighbour in the padded sense isn't available; use pool flag of this column's rim
        reed = wet & ~planted & (rand01(Q, R, self.h + 78) < np.where(pool, 0.0, 0.04))
        # prefer columns near a pool: e is not here, but pool neighbours via shift
        near_pool = pool.copy()
        near_pool[1:] |= pool[:-1]
        near_pool[:-1] |= pool[1:]
        near_pool[:, 1:] |= pool[:, :-1]
        near_pool[:, :-1] |= pool[:, 1:]
        reed = wet & near_pool & ~pool & (rand01(Q, R, self.h + 79) < 0.35)
        ii, kk = np.nonzero(reed)
        for i, k in zip(ii, kk):
            y = int(top[i, k]) + 1
            if 0 <= y < LAYERS and cells[i, y, k] == 0:
                cells[i, y, k] = M['reeds']

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
            hgt = rng.randint(6, 9)
            for y in range(top + 1, top + 1 + hgt):
                self._put(cells, lq, y, lr, M['plinth'] if False else wood)
            self._disk(cells, lq, lr, top + hgt, 2, leaf)
            self._disk(cells, lq, lr, top + hgt + 1, 1, leaf)
            for (dq, dr) in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, -2), (-2, 2)):
                self._put(cells, lq + dq, top + hgt - 1, lr + dr, M['glowcap'])
            return
        if realm == FROST:                      # stacked rings, narrowing: a hex fir
            hgt = rng.randint(8, 12)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, wood)
            for i, y in enumerate(range(top + 5, top + hgt + 1)):
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
            hgt = rng.randint(6, 9)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, M['crystal'] if y > top + hgt - 3 else wood)
            self._disk(cells, lq, lr, top + hgt, 2, leaf)
            self._put(cells, lq, top + hgt + 1, lr, M['lumen_shard'])
            return
        if realm == CEDAR or realm == CLOUDSTEP:
            hgt = rng.randint(9, 13) if realm == CEDAR else rng.randint(7, 10)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, wood)
            for i, y in enumerate(range(top + 5, top + hgt + 1)):
                rad = max(0, (2 if realm == CEDAR else 1) - i // 2)
                self._disk(cells, lq, lr, y, rad, leaf)
            return
        if realm == CHALK or realm == SALTWIND:
            hgt = rng.randint(6, 8)
            for y in range(top + 1, top + hgt):
                self._put(cells, lq, y, lr, wood)
            self._disk(cells, lq, lr, top + hgt, 1, leaf)
            return
        hgt = rng.randint(7, 10) + (2 if realm in (AMBER, VERDIGRIS) else 0)
        for y in range(top + 1, top + hgt + 1):
            self._put(cells, lq, y, lr, wood)
        rad = 2 if realm != ROSE else 1
        self._disk(cells, lq, lr, top + hgt, rad, leaf)
        self._disk(cells, lq, lr, top + hgt + 1, rad, leaf)
        self._disk(cells, lq, lr, top + hgt + 2, max(1, rad - 1), leaf)
        if realm in (FEN, VERDIGRIS):          # weeping vines from the canopy edge
            for (dq, dr) in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, -2), (-2, 2)):
                for y in range(top + hgt - 1 - rng.randint(0, 1), top + hgt + 1):
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

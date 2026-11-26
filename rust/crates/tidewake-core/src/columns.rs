//! Generator v6 column shape. A direct port of `Generator._columns_v5` with `k=1.5`.
//!
//! Each column is a pure function of the seed and `(q, r)`. v1–v5 are not implemented.

use crate::biomes::*;
use crate::config::{CLOUD_SEA, TOP_MAX_V6, TOP_MIN};
use crate::hex;
use crate::noise::{rand01, Noise};
use crate::pyrandom::PyRng;
use crate::settings::{scale, Settings};

const K: f64 = 1.5;
const DEPTH_K: f64 = 1.80;
const ALT_SPAN: f64 = 404.0;
const ALT_MAX: f64 = 446.0;

#[derive(Clone, Copy, Debug)]
pub struct Column {
    pub e: f64,
    pub land: bool,
    pub top: i32,
    pub bottom: i32,
    pub realm: u8,
    pub pool: bool,
    pub fall: bool,
    pub skerry: bool,
    pub inner: f64,
    pub rand: f64,
    pub peak: bool,
    pub com: f64,
    pub island_r: f64,
}

#[derive(Clone)]
#[allow(dead_code)]
pub struct Generator {
    pub seed: i64,
    pub settings: Settings,
    pub h: u64,
    pub island_scale: f64,
    pub coverage: f64,
    pub alt_base: f64,
    pub hill_amp: f64,
    pub depth_amp: f64,
    pub mount_amp: f64,
    pub caves: f64,
    pub realm_scale: f64,
    pub islet_rate: f64,
    pub heat_bias: f64,
    pub wet_bias: f64,
    pub spire_rate: f64,
    pub arches: f64,
    pub tree_mul: f64,
    pub water_mul: f64,
    pub flatness: f64,
    pub cave_size: f64,
    pub glimmer_mul: f64,
    pub period_h: f64,
    pub period_l: f64,
    pub period_m: f64,
    pub period_s: f64,
    pub accept_h: f64,
    pub accept_l: f64,
    pub accept_m: f64,
    pub accept_s: f64,
    n_heat: Noise,
    n_wet: Noise,
    n_lumen: Noise,
    n_detail: Noise,
    n_pool: Noise,
    n_depth: Noise,
    n_islet: Noise,
    n_tunnel: Noise,
    n_islet_alt: Noise,
    n_mount: Noise,
    n_cave: Noise,
    n_ore: Noise,
    n_arch: Noise,
    n_form: Noise,
    n_spice: Noise,
    n_room: Noise,
    n_hw: Noise,
    n_fiss: Noise,
    n_hill: Noise,
}

impl Generator {
    pub fn new(seed: i64, settings: Settings) -> Self {
        let u = seed as u64;
        let mut rng = PyRng::seed_u64(crate::noise::splitmix64(u));
        let k = |i: u64| crate::noise::splitmix64(u.wrapping_add(0x51ED * (i + 1)));
        let mut island_scale = rng.uniform(120.0, 300.0);
        let mut coverage = rng.uniform(-0.04, 0.16);
        let _warp = rng.uniform(20.0, 110.0);
        let alt_base = rng.uniform(52.0, 66.0);
        let alt_amp = rng.uniform(10.0, 30.0);
        let mut hill_amp = rng.uniform(4.0, 16.0);
        let mut depth_amp = rng.uniform(34.0, 70.0);
        let mut mount_amp = rng.uniform(24.0, 46.0);
        let mut caves = rng.uniform(0.07, 0.12);
        let mut realm_scale = rng.uniform(260.0, 720.0);
        let islet_rate = rng.uniform(0.05, 0.35);
        let _tunnels = rng.uniform(0.0, 0.09);
        let heat_bias = rng.uniform(-0.15, 0.15);
        let wet_bias = rng.uniform(-0.15, 0.15);
        let spire_rate = rng.uniform(0.55, 0.9);
        let _cliff = rng.uniform(5.0, 11.0);
        let arches = rng.uniform(0.40, 0.52);

        island_scale *= scale(&settings, "island_size", 0.55, 1.0, 1.65);
        coverage -= (settings.sky_density - 50) as f64 / 50.0 * 0.14;
        realm_scale *= scale(&settings, "biome_size", 0.5, 1.0, 1.8);
        hill_amp *= scale(&settings, "terrain_roughness", 0.45, 1.05, 1.8);
        mount_amp *= scale(&settings, "mountain_height", 0.35, 1.15, 1.9);
        depth_amp = (depth_amp + 10.0) * scale(&settings, "island_thickness", 0.42, 1.0, 2.15);
        caves *= scale(&settings, "cave_amount", 0.35, 1.15, 1.55);
        let tree_mul = scale(&settings, "tree_density", 0.15, 1.0, 2.2);
        let water_mul = scale(&settings, "water", 0.15, 1.0, 2.0);
        let flatness = settings.flatness as f64 / 100.0;
        let cave_size = scale(&settings, "cave_size", 0.55, 1.0, 1.45);
        let glimmer_mul = scale(&settings, "glimmer_rarity", 0.70, 0.32, 0.10);

        let dens = (0.06 - coverage) / 0.20;
        let clip = |v: f64, lo: f64, hi: f64| v.clamp(lo, hi);
        let period = |floor: f64, mul: f64, lo: f64, hi: f64| clip(floor.max(island_scale * mul), lo, hi) * K;

        // Silence unused personality fields that v6's shape does not read.
        let _ = (alt_amp, _warp, _tunnels, _cliff);

        Self {
            seed,
            settings,
            h: k(20),
            island_scale,
            coverage,
            alt_base,
            hill_amp,
            depth_amp,
            mount_amp,
            caves,
            realm_scale,
            islet_rate,
            heat_bias,
            wet_bias,
            spire_rate,
            arches,
            tree_mul,
            water_mul,
            flatness,
            cave_size,
            glimmer_mul,
            period_h: period(1100.0, 3.80, 1100.0, 1250.0),
            period_l: period(468.0, 2.40, 468.0, 832.0),
            period_m: period(221.0, 1.17, 221.0, 390.0),
            period_s: period(104.0, 0.62, 104.0, 195.0),
            accept_h: clip(0.12 - dens * 0.04, 0.07, 0.16),
            accept_l: clip(0.28 - dens * 0.10, 0.18, 0.40),
            accept_m: clip(0.46 - dens * 0.12, 0.30, 0.62),
            accept_s: clip(0.54 - dens * 0.14, 0.34, 0.74),
            n_heat: Noise::new(k(5)),
            n_wet: Noise::new(k(6)),
            n_lumen: Noise::new(k(7)),
            n_detail: Noise::new(k(8)),
            n_pool: Noise::new(k(9)),
            n_depth: Noise::new(k(10)),
            n_islet: Noise::new(k(11)),
            n_tunnel: Noise::new(k(12)),
            n_islet_alt: Noise::new(k(13)),
            n_mount: Noise::new(k(14)),
            n_cave: Noise::new(k(15)),
            n_ore: Noise::new(k(16)),
            n_arch: Noise::new(k(19)),
            n_form: Noise::new(k(21)),
            n_spice: Noise::new(k(23)),
            n_room: Noise::new(k(24)),
            n_hw: Noise::new(k(25)),
            n_fiss: Noise::new(k(26)),
            n_hill: Noise::new(k(4)),
        }
    }

    pub fn sample(&self, q: i64, r: i64) -> Column {
        let (x, z) = hex::center(q, r);
        let jitter = 0.15;
        let mut near_u: f64 = 10.0;
        let mut best_u = 10.0;
        let mut best_com = 0.0;
        let mut best_id = -1.0;
        let mut best_r = 1.0;

        let near_h = self.stamp(
            x, z, self.period_h, self.accept_h, jitter, 10, rad_h, 0.38, true, 10.0,
            &mut best_u, &mut best_com, &mut best_id, &mut best_r, 3, ALT_SPAN, ALT_MAX,
        );
        near_u = near_u.min(near_h);
        let allow_l = near_h > 1.30;
        let near_l = self.stamp(
            x, z, self.period_l, self.accept_l, jitter, 20, rad_l, 0.40, allow_l, 10.0,
            &mut best_u, &mut best_com, &mut best_id, &mut best_r, 0, ALT_SPAN, ALT_MAX,
        );
        near_u = near_u.min(near_l);
        let allow_m = near_h > 1.32 && near_l > 1.30;
        let near_m = self.stamp(
            x, z, self.period_m, self.accept_m, jitter, 40, rad_m, 0.38, allow_m, 10.0,
            &mut best_u, &mut best_com, &mut best_id, &mut best_r, 1, ALT_SPAN, ALT_MAX,
        );
        near_u = near_u.min(near_m);
        let allow_s = near_h > 1.35 && near_l > 1.35 && near_m > 1.35;
        let near_s = self.stamp(
            x, z, self.period_s, self.accept_s, jitter, 60, rad_s, 0.36, allow_s, 10.0,
            &mut best_u, &mut best_com, &mut best_id, &mut best_r, 2, ALT_SPAN, ALT_MAX,
        );
        near_u = near_u.min(near_s);

        let mut inside = best_u < 1.0;
        let nibbled = inside && best_u > 0.80 && rand01(q, r, self.h.wrapping_add(41)) > 0.55;
        if nibbled {
            inside = false;
            best_u = 1.05;
        }
        let mut e = if inside { 1.0 - best_u } else { 1.0 - near_u };
        let com = best_com;
        let huge = best_r > 200.0 * K;

        let rscale = if huge { self.realm_scale * 0.42 } else { self.realm_scale };
        let heat = self.n_heat.fbm2(x / rscale, z / rscale, 3) * 1.5 + self.heat_bias;
        let wet = self.n_wet.fbm2(x / rscale, z / rscale, 3) * 1.5 + self.wet_bias;
        let lum = self.n_lumen.fbm2(x / (rscale * 0.7), z / (rscale * 0.7), 2);
        let sp = self.n_spice.fbm2(x / (rscale * 0.85), z / (rscale * 0.85), 3);
        let mut realm = MEADOW;
        if heat > 0.05 { realm = AMBER; }
        if heat > 0.30 && wet >= -0.05 { realm = ROSE; }
        if heat > 0.30 && wet < -0.05 { realm = DUNE; }
        if wet > 0.28 && heat <= 0.30 { realm = FEN; }
        if wet < -0.30 && heat <= 0.30 { realm = BASALT; }
        if heat < -0.28 { realm = FROST; }
        if lum > 0.40 { realm = LUMEN; }
        if wet > 0.02 && e > 0.0 && e < 0.13 && heat > -0.16 && heat < 0.36 && lum <= 0.40 {
            realm = SALTWIND;
        }
        if heat < 0.02 && heat > -0.30 && wet > 0.0 && sp < 0.22 && lum <= 0.40
            && one_of(realm, &[MEADOW, FEN, AMBER, CEDAR])
        {
            realm = CEDAR;
        }
        if heat.abs() < 0.26 && wet > -0.16 && wet < 0.28 && sp > 0.10 && lum <= 0.40
            && one_of(realm, &[MEADOW, AMBER, ROSE, LAVENDER])
        {
            realm = LAVENDER;
        }
        if heat > 0.14 && wet < 0.10 && sp > 0.04 && lum <= 0.40
            && one_of(realm, &[AMBER, ROSE, DUNE, CINDER])
        {
            realm = CINDER;
        }
        if wet < -0.02 && heat > -0.14 && heat < 0.32 && sp < 0.18 && lum <= 0.40
            && one_of(realm, &[MEADOW, BASALT, DUNE, AMBER, CHALK])
        {
            realm = CHALK;
        }
        if sp > 0.20 && heat < 0.28 && lum > -0.02 && lum <= 0.40 {
            realm = STARFALL;
        }
        if inside && com > 230.0 && lum <= 0.40 {
            realm = CLOUDSTEP;
        }
        if wet > 0.04 && heat > -0.16 && heat < 0.36 && sp > 0.0 && sp < 0.36 && lum <= 0.40
            && one_of(realm, &[MEADOW, FEN, BASALT, AMBER, VERDIGRIS, SALTWIND])
        {
            realm = VERDIGRIS;
        }
        if lum > 0.40 {
            realm = LUMEN;
        }
        let nb = self.n_spice.fbm2(x / (rscale * 0.55) + 113.0, z / (rscale * 0.55) - 71.0, 2);
        if nb > 0.20 && one_of(realm, &[MEADOW, LAVENDER, ROSE]) { realm = BLOSSOM; }
        if nb < -0.20 && one_of(realm, &[AMBER, CEDAR, VERDIGRIS]) { realm = AUTUMN; }
        if nb > 0.16 && one_of(realm, &[FROST, CLOUDSTEP, SALTWIND, CHALK]) { realm = AZURE; }
        if nb < -0.18 && one_of(realm, &[DUNE, MEADOW, CINDER]) { realm = GOLDEN; }

        let fade = if best_r > 200.0 * K {
            0.08
        } else if best_r > 80.0 * K {
            0.12
        } else if best_r > 36.0 * K {
            0.20
        } else {
            0.28
        };
        let mut inner = ((best_u - 1.0) / (fade - 1.0)).clamp(0.0, 1.0);
        inner = inner * inner * (3.0 - 2.0 * inner);
        let hills = self.n_hill.fbm2(x / 160.0, z / 160.0, 3);
        let fine = self.n_detail.fbm2(x / 64.0, z / 64.0, 2);
        let ridge_m = 1.0 - self.n_mount.fbm2(x / 400.0, z / 400.0, 2).abs() * 2.0;
        let form = 0.5 + 0.5 * self.n_form.fbm2(x / 860.0, z / 860.0, 2);
        let mounts = smoothstep(0.42, 0.84, form);
        let flat = self.flatness;
        let rough = (self.hill_amp / 10.0).max(0.45);
        let peak_scale = 1.0 - 0.80 * flat;
        let mut h = com;
        h += (4.0 + 4.0 * rough) * hills * inner * (1.0 - 0.80 * flat);
        h += (7.0 + self.hill_amp * 0.6) * (hills * 0.9 + 0.15 * fine) * inner * peak_scale;
        let alpine = (12.0 + self.mount_amp * 0.35)
            * mounts
            * (0.55 + 0.45 * ridge_m.clamp(0.0, 1.0))
            * inner
            * peak_scale;
        h += alpine;
        h += 1.6 * fine * inner * (1.0 - 0.85 * flat);
        let valley = self.n_form.fbm2(x / 240.0, z / 240.0, 2);
        if huge {
            h -= (9.0 + 4.0 * rough) * (0.22 - valley).max(0.0) * inner * peak_scale;
        }
        if realm == FROST {
            h += ridge_m * 3.0 * inner * peak_scale;
        }
        if realm == DUNE {
            h += (x / 16.0 + hills * 3.0).sin() * 1.5 * inner;
        }
        if realm == FEN {
            h = com + (h - com) * (0.72 - 0.20 * flat);
        }
        if realm == SALTWIND {
            h = com + (h - com) * (0.62 - 0.15 * flat);
        }
        let rim = ((best_u - 0.84) / 0.16).clamp(0.0, 1.0);
        h -= rim * 2.0;
        let mut top = h.floor();
        if realm == ROSE {
            top = (h / 2.0).floor() * 2.0;
        }

        let mut thick = self.depth_amp * DEPTH_K * (0.85 + 0.50 * self.n_depth.fbm2(x / 36.0, z / 36.0, 3));
        thick *= 1.0 + 0.28 * mounts;
        if huge {
            thick *= 1.15;
        }
        let dome = 0.5 * (1.0 + (std::f64::consts::PI * best_u.clamp(0.0, 1.0)).cos());
        let mut depth = 4.0 + thick * (0.90 * dome + 0.10);
        if one_of(realm, &[SALTWIND, CHALK, LAVENDER]) {
            depth *= 0.78;
        }
        if one_of(realm, &[CLOUDSTEP, CINDER, FROST]) {
            depth *= 1.18;
        }
        let avail = (top - 2.0).max(4.0);
        let r_cells = (best_r / 1.5).max(6.0);
        depth = depth.min(2.0 + (avail - 2.0) * (0.88 * dome + 0.12));
        depth = depth.min(3.2 * r_cells * (0.90 * dome + 0.10) + 2.0);
        let mut bottom = top - depth.floor();

        let mut ei = self.n_islet.fbm2(x / 38.0, z / 38.0, 3) - (0.70 - self.islet_rate);
        ei = ei.max(self.n_islet.fbm2(x / 23.0 + 71.0, z / 23.0 - 37.0, 2) - 0.62);
        let sk = !inside && ei > 0.0 && near_u > 1.40;
        let mut sk_alt = (46.0 + 40.0 * self.n_islet_alt.fbm2(x / 300.0, z / 300.0, 2) + ei * 25.0).floor();
        let spread = (0.5 + 0.5 * self.n_islet_alt.fbm2(x / 140.0 + 19.0, z / 140.0 - 53.0, 2)).clamp(0.0, 1.0);
        sk_alt = (sk_alt + spread * 400.0).floor();
        if sk {
            top = sk_alt;
            let sk_dome = (ei / 0.35).clamp(0.0, 1.0).sqrt();
            let mut sk_depth = 2.0 + sk_dome * 18.0;
            let sk_avail = (sk_alt - 2.0).max(4.0);
            sk_depth = sk_depth.min(2.0 + (sk_avail - 2.0) * (0.88 * sk_dome + 0.12));
            bottom = sk_alt - sk_depth.floor();
            e = e.max(ei);
        }
        let land = inside || sk;
        let mut top_i = top.clamp(TOP_MIN as f64, TOP_MAX_V6 as f64) as i32;
        let mut bot_i = bottom.max(2.0) as i32;
        // `as i32` truncates; values are integral after floor, but a negative
        // floor such as -2.0 casts correctly. Clamp the underside afterwards.
        if bottom < 2.0 {
            bot_i = 2;
        }
        if bot_i > top_i - 2 {
            bot_i = top_i - 2;
        }
        if top_i < TOP_MIN {
            top_i = TOP_MIN;
        }

        let col_rand = rand01(q, r, self.h);
        let inner = if land {
            inner.max(if sk { smoothstep(0.0, 0.28, ei) } else { 0.0 })
        } else {
            0.0
        };
        let wmul = self.water_mul;
        let mut pool_t = if one_of(realm, &[FEN, SALTWIND, VERDIGRIS]) {
            0.14 - 0.10 * wmul
        } else if one_of(realm, &[BASALT, MEADOW, LAVENDER, CEDAR]) {
            0.50 - 0.16 * wmul
        } else {
            9.0
        };
        if one_of(realm, &[CINDER, DUNE, CHALK]) {
            pool_t = 0.75 - 0.10 * wmul;
        }
        if huge && best_u < 0.72 {
            pool_t -= 0.16;
        }
        let pooln = self.n_pool.fbm2(x / 26.0, z / 26.0, 2);
        let pool = land && !sk && e > 0.12 && pooln > pool_t && wmul > 0.2;
        let fall = land
            && !sk
            && e > 0.0
            && e < 0.10
            && rand01(q, r, self.h.wrapping_add(2)) < (0.012 * wmul * 0.5)
            && one_of(realm, &[MEADOW, AMBER, FEN, BASALT, LUMEN, CEDAR, VERDIGRIS, CLOUDSTEP, LAVENDER]);
        Column {
            e,
            land,
            top: top_i,
            bottom: bot_i,
            realm: realm as u8,
            pool,
            fall,
            skerry: sk,
            inner,
            rand: col_rand,
            peak: land && (top_i as f64) > (com + 24.0),
            com,
            island_r: if inside { best_r } else { 0.0 },
        }
    }

    /// Nominal radius of an accepted main-terrain island centre, or 0 if that grid cell is empty.
    /// Used by tests to find every size class without sampling every column.
    pub fn main_island_radius(&self, scale: MainScale, ci: i64, cj: i64) -> f64 {
        let (period, accept, off, rad): (f64, f64, u64, fn(f64) -> f64) = match scale {
            MainScale::Huge => (self.period_h, self.accept_h, 10, rad_h),
            MainScale::Large => (self.period_l, self.accept_l, 20, rad_l),
            MainScale::Medium => (self.period_m, self.accept_m, 40, rad_m),
            MainScale::Small => (self.period_s, self.accept_s, 60, rad_s),
        };
        if rand01(ci, cj, self.h.wrapping_add(off + 1)) >= accept {
            return 0.0;
        }
        let kind = rand01(ci, cj, self.h.wrapping_add(off + 4));
        period * rad(kind)
    }
}

#[derive(Clone, Copy)]
pub enum MainScale {
    Huge,
    Large,
    Medium,
    Small,
}

fn rad_h(kind: f64) -> f64 {
    if kind > 0.70 { 0.30 } else if kind > 0.35 { 0.28 } else { 0.26 }
}
fn rad_l(kind: f64) -> f64 {
    if kind > 0.82 { 0.30 } else if kind > 0.45 { 0.24 } else { 0.18 }
}
fn rad_m(kind: f64) -> f64 {
    if kind > 0.65 { 0.22 } else if kind > 0.30 { 0.16 } else { 0.11 }
}
fn rad_s(kind: f64) -> f64 {
    if kind > 0.55 { 0.20 } else { 0.12 }
}

fn smoothstep(a: f64, b: f64, x: f64) -> f64 {
    let t = ((x - a) / (b - a)).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

impl Generator {
    #[allow(clippy::too_many_arguments)]
    fn stamp<F: Fn(f64) -> f64>(
        &self,
        x: f64,
        z: f64,
        period: f64,
        accept_p: f64,
        jitter: f64,
        h_off: u64,
        rad_kind: F,
        reserved: f64,
        allow: bool,
        mut near_u: f64,
        best_u: &mut f64,
        best_com: &mut f64,
        best_id: &mut f64,
        best_r: &mut f64,
        scale_id: i32,
        alt_span: f64,
        alt_max: f64,
    ) -> f64 {
        if !allow {
            return near_u;
        }
        let fx = x / period;
        let fz = z / period;
        let sid = scale_id as f64;
        let det = self.n_detail.fbm2(x / (9.0 + 6.0 * sid), z / (9.0 + 6.0 * sid), 2);
        let spi = self.n_spice.fbm2(x / (8.0 + 5.0 * sid), z / (8.0 + 5.0 * sid), 2);
        let warp_k = if scale_id == 0 { 0.10 } else { 0.07 };
        let base_i = fx.floor() as i64;
        let base_j = fz.floor() as i64;
        for di in -2..=2 {
            for dj in -2..=2 {
                let ci = base_i + di;
                let cj = base_j + dj;
                let h = self.h;
                if rand01(ci, cj, h.wrapping_add(h_off + 1)) >= accept_p {
                    continue;
                }
                let jx = rand01(ci, cj, h.wrapping_add(h_off + 2));
                let jz = rand01(ci, cj, h.wrapping_add(h_off + 3));
                let px = (ci as f64 + 0.5 + (jx - 0.5) * jitter) * period;
                let pz = (cj as f64 + 0.5 + (jz - 0.5) * jitter) * period;
                let kind = rand01(ci, cj, h.wrapping_add(h_off + 4));
                let rad = period * rad_kind(kind);
                let altn = rand01(ci, cj, h.wrapping_add(h_off + 5));
                let com = (46.0 + altn * alt_span + (self.alt_base - 59.0) * 0.35)
                    .clamp(CLOUD_SEA as f64 + 16.0, alt_max);
                let mut dx = x - px;
                let mut dz = z - pz;
                let ang0 = rand01(ci, cj, h.wrapping_add(h_off + 6)) * std::f64::consts::TAU;
                let ang1 = rand01(ci, cj, h.wrapping_add(h_off + 7)) * std::f64::consts::TAU;
                let ang2 = rand01(ci, cj, h.wrapping_add(h_off + 8)) * std::f64::consts::TAU;
                let stretch = 0.88 + 0.22 * rand01(ci, cj, h.wrapping_add(h_off + 9));
                let warp = warp_k * rad;
                dx += warp * det;
                dz += warp * spi;
                let (ca, sa) = (ang0.cos(), ang0.sin());
                let rx = dx * ca + dz * sa;
                let rz = (-dx * sa + dz * ca) / stretch;
                let d = (rx * rx + rz * rz).sqrt();
                let theta = rz.atan2(rx);
                let lobe = 0.18 * (2.0 * (theta - ang0)).cos()
                    + 0.10 * (3.0 * (theta - ang1)).cos()
                    + 0.06 * (5.0 * (theta - ang2)).cos();
                let coast = self.n_detail.fbm2((x + px) / 11.0, (z + pz) / 11.0, 2);
                let coast2 = self.n_spice.fbm2((x + px) / 5.5, (z + pz) / 5.5, 2);
                let nibble = 0.10 * (-coast).max(0.0) + 0.06 * (-coast2).max(0.0);
                let mut r_eff = rad * (1.0 + lobe) * (1.0 - nibble);
                r_eff = r_eff.min(reserved * period / stretch.max(1.0));
                let u = d / (r_eff + 1e-6);
                if u < near_u {
                    near_u = u;
                }
                if u < 1.0 && u < *best_u {
                    *best_u = u;
                    *best_com = com;
                    *best_r = r_eff;
                    *best_id = ci as f64 * 131071.0 + cj as f64 + sid * 1_000_000_000.0;
                }
            }
        }
        near_u
    }
}

/// World-unit radius class. Edges match `skytiers.SIZE_EDGES`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum SizeClass {
    Tiny,
    Small,
    Medium,
    Large,
    Huge,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::settings::Settings;

    #[test]
    fn columns_match_python_v6() {
        let g = Generator::new(7, Settings::default());
        // Recorded from tidewake.generator.Generator(7, v6).columns.
        let rows = [
            (0i64, 0i64, false, 24, 2, 12u8, -1.32474953, 0.0, false, false),
            (10, 62, true, 100, 94, 10, 0.01435853, 22.909116, false, false),
            (12, 63, true, 102, 89, 10, 0.24433623, 23.171611, false, false),
            (25, 57, true, 102, 93, 10, 0.22650044, 16.878823, false, true),
            (25, 59, true, 102, 77, 10, 0.49423570, 20.705372, false, false),
        ];
        for (q, r, land, top, bot, realm, e, rad, sk, pool) in rows {
            let c = g.sample(q, r);
            assert_eq!(c.land, land, "{q},{r}");
            assert_eq!((c.top, c.bottom, c.realm, c.skerry, c.pool), (top, bot, realm, sk, pool));
            assert!((c.e - e).abs() < 1e-6, "{} {}", c.e, e);
            assert!((c.island_r - rad).abs() < 1e-4, "{} {}", c.island_r, rad);
        }
        let mut land_n = 0;
        for q in 0..64 {
            for r in 0..64 {
                if g.sample(q, r).land {
                    land_n += 1;
                }
            }
        }
        assert_eq!(land_n, 176);
    }
}

pub fn size_class(rad: f64) -> SizeClass {
    const EDGES: [f64; 4] = [15.0, 40.0, 100.0, 250.0];
    let mut i = 0;
    while i < EDGES.len() && rad >= EDGES[i] {
        i += 1;
    }
    [SizeClass::Tiny, SizeClass::Small, SizeClass::Medium, SizeClass::Large, SizeClass::Huge][i]
}

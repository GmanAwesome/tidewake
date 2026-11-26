//! Filled v6 chunks: solid islands, surface materials, pools, waterfalls, trees.
//!
//! Spike cleanup follows `generator.generate` for version 6: lone rim columns stay
//! shallow, and a column may hang at most four layers below its deepest neighbour.
//! Waterfalls are water, so they are not treated as rock pillars.

use crate::columns::{Column, Generator};
use crate::config::{CHUNK, CLOUD_SEA, LAYERS};
use crate::hex::DIRS;
use crate::materials::id;
use crate::noise::{hash_ints, rand01};
use crate::pyrandom::PyRng;
use crate::tiers;

pub const PAD: i32 = 4;

#[derive(Clone)]
pub struct Chunk {
    pub cq: i32,
    pub cr: i32,
    pub cells: Vec<u8>,
    /// Per-cell extra bits (door facing, crop stage). Same index as `cells`.
    pub meta: Vec<u8>,
    pub realm: Vec<u8>,
}

impl Chunk {
    pub fn index(lq: i32, y: i32, lr: i32) -> usize {
        ((lq as usize) * LAYERS as usize + y as usize) * CHUNK as usize + lr as usize
    }

    pub fn get(&self, lq: i32, y: i32, lr: i32) -> u8 {
        if lq < 0 || lr < 0 || y < 0 || lq >= CHUNK || lr >= CHUNK || y >= LAYERS {
            return 0;
        }
        self.cells[Self::index(lq, y, lr)]
    }

    pub fn set(&mut self, lq: i32, y: i32, lr: i32, mat: u8) {
        if lq < 0 || lr < 0 || y < 0 || lq >= CHUNK || lr >= CHUNK || y >= LAYERS {
            return;
        }
        self.cells[Self::index(lq, y, lr)] = mat;
    }

    pub fn get_meta(&self, lq: i32, y: i32, lr: i32) -> u8 {
        if lq < 0 || lr < 0 || y < 0 || lq >= CHUNK || lr >= CHUNK || y >= LAYERS {
            return 0;
        }
        self.meta[Self::index(lq, y, lr)]
    }

    pub fn set_meta(&mut self, lq: i32, y: i32, lr: i32, meta: u8) {
        if lq < 0 || lr < 0 || y < 0 || lq >= CHUNK || lr >= CHUNK || y >= LAYERS {
            return;
        }
        self.meta[Self::index(lq, y, lr)] = meta;
    }

    pub fn blank(cq: i32, cr: i32) -> Self {
        let n = (CHUNK * LAYERS * CHUNK) as usize;
        Self {
            cq,
            cr,
            cells: vec![0; n],
            meta: vec![0; n],
            realm: vec![0; (CHUNK * CHUNK) as usize],
        }
    }
}

/// First solid column near the origin, a few layers above the surface.
pub fn find_spawn(gen: &Generator) -> (f64, f64, f64) {
    use crate::hex::{center, hex_distance};
    for rad in 0..120 {
        for q in -rad..=rad {
            for r in -rad..=rad {
                if hex_distance(q, r, 0, 0) != rad {
                    continue;
                }
                let c = gen.sample(q, r);
                if c.land && !c.skerry && c.e > 0.04 {
                    let (x, z) = center(q, r);
                    return (x, c.top as f64 * crate::config::LAYER + 8.0, z);
                }
            }
        }
    }
    (0.0, 80.0, 0.0)
}

pub fn generate(gen: &Generator, cq: i32, cr: i32) -> Chunk {
    let side = CHUNK + PAD * 2;
    let q0 = cq as i64 * CHUNK as i64;
    let r0 = cr as i64 * CHUNK as i64;
    let mut cols = Vec::with_capacity((side * side) as usize);
    for i in 0..side {
        for k in 0..side {
            let q = q0 - PAD as i64 + i as i64;
            let r = r0 - PAD as i64 + k as i64;
            cols.push(gen.sample(q, r));
        }
    }
    let at = |cols: &[Column], i: i32, k: i32| -> Column {
        let i = i.rem_euclid(side);
        let k = k.rem_euclid(side);
        cols[(i * side + k) as usize]
    };

    let mut bottom = vec![0i32; (side * side) as usize];
    let mut top = vec![0i32; (side * side) as usize];
    let mut land = vec![false; (side * side) as usize];
    for i in 0..side {
        for k in 0..side {
            let c = at(&cols, i, k);
            let ix = (i * side + k) as usize;
            bottom[ix] = c.bottom;
            top[ix] = c.top;
            land[ix] = c.land;
        }
    }
    // Lone rim columns (0 or 1 land neighbours) stay a shallow nub.
    for i in 0..side {
        for k in 0..side {
            let ix = (i * side + k) as usize;
            if !land[ix] {
                continue;
            }
            let mut n = 0;
            for (dq, dr) in DIRS {
                if at_flag(&land, side, i + dq, k + dr) {
                    n += 1;
                }
            }
            if n <= 1 {
                bottom[ix] = bottom[ix].max(top[ix] - 2);
            }
        }
    }
    for _ in 0..3 {
        let mut nbmin = vec![1_000_000i32; (side * side) as usize];
        for i in 0..side {
            for k in 0..side {
                let ix = (i * side + k) as usize;
                let mut m = 1_000_000;
                for (dq, dr) in DIRS {
                    let ni = (i + dq).rem_euclid(side);
                    let nk = (k + dr).rem_euclid(side);
                    let nx = (ni * side + nk) as usize;
                    let b = if land[nx] { bottom[nx] } else { 1_000_000 };
                    m = m.min(b);
                }
                nbmin[ix] = m;
            }
        }
        for i in 0..(side * side) as usize {
            if land[i] {
                bottom[i] = top[i].saturating_sub(1).min(bottom[i].max(nbmin[i] - 4));
            }
        }
    }

    let mut chunk = Chunk::blank(cq, cr);
    for i in 0..CHUNK {
        for k in 0..CHUNK {
            let c = at(&cols, i + PAD, k + PAD);
            let ix = ((i + PAD) * side + (k + PAD)) as usize;
            chunk.realm[(i * CHUNK + k) as usize] = c.realm;
            if !c.land {
                continue;
            }
            let top_y = c.top;
            let bot_y = bottom[ix];
            let realm = c.realm as i64;
            let (qx, rx) = (q0 + i as i64, r0 + k as i64);
            let det = gen.fbm_detail(qx as f64 / 7.0, rx as f64 / 7.0, 2);
            let body = body_of(realm);
            let mid = mid_of(realm, body);
            let surf = surf_of(realm, body, det, c.peak);
            let thick = (top_y - bot_y).max(1);
            for y in bot_y..=top_y {
                if y < 0 || y >= LAYERS {
                    continue;
                }
                let d = top_y - y;
                let mut mat = body;
                if d <= 3 && d >= 1 {
                    mat = mid;
                }
                if d == 0 {
                    mat = surf;
                }
                let from_bot = y - bot_y;
                if realm == crate::biomes::CLOUDSTEP && from_bot as f64 <= thick as f64 * 0.34 && d >= 2 {
                    mat = id::CLOUDSTUFF;
                }
                chunk.set(i, y, k, mat);
            }
            if c.pool && (0..LAYERS).contains(&top_y) {
                chunk.set(i, top_y, k, id::WATER);
            }
            if c.fall {
                let lo = CLOUD_SEA.max(bot_y - 40);
                for y in lo..=top_y {
                    if (0..LAYERS).contains(&y) {
                        chunk.set(i, y, k, id::WATER);
                    }
                }
            }
        }
    }

    // Trees may be rooted in the padded margin and spill into this chunk.
    for i in 0..side {
        for k in 0..side {
            let c = at(&cols, i, k);
            if !c.land || c.pool || c.fall || c.skerry || c.e <= 0.035 {
                continue;
            }
            let q = q0 - PAD as i64 + i as i64;
            let r = r0 - PAD as i64 + k as i64;
            let rate = TREE_RATE[c.realm as usize] * gen.tree_mul;
            if rand01(q, r, gen.h.wrapping_add(7)) >= rate {
                continue;
            }
            let lq = (q - q0) as i32;
            let lr = (r - r0) as i32;
            if !(-3..CHUNK + 3).contains(&lq) || !(-3..CHUNK + 3).contains(&lr) {
                continue;
            }
            let hsh = hash_ints(gen.h, &[q, r, 9]);
            let mut rng = PyRng::seed_u64(hsh);
            plant_tree(&mut chunk, lq, lr, c.top, c.realm as i64, &mut rng);
        }
    }

    place_ores(gen, &mut chunk, q0, r0);
    carve_caves(gen, &mut chunk, q0, r0);
    stamp_spires(gen, &mut chunk);
    tiers::stamp(gen, cq, cr, &mut chunk);
    crate::trees::stamp(gen, &mut chunk);
    crate::structures::stamp(gen, &mut chunk);
    chunk
}

fn at_flag(land: &[bool], side: i32, i: i32, k: i32) -> bool {
    land[(i.rem_euclid(side) * side + k.rem_euclid(side)) as usize]
}

const TREE_RATE: [f64; 20] = [
    0.016, 0.05, 0.006, 0.02, 0.004, 0.022, 0.002, 0.03, 0.004, 0.045, 0.012, 0.003, 0.005, 0.018,
    0.008, 0.024, 0.034, 0.042, 0.012, 0.006,
];

fn body_of(realm: i64) -> u8 {
    use crate::biomes::*;
    match realm {
        ROSE => id::ROSESTONE,
        BASALT => id::BASALT,
        CINDER => id::CINDER,
        VERDIGRIS => id::MOSSROCK,
        CHALK => id::CHALK,
        SALTWIND => id::SANDSTONE,
        STARFALL => id::STARSTONE,
        CLOUDSTEP => id::PALE_STONE,
        AZURE => id::SLATE,
        GOLDEN => id::SANDSTONE,
        BLOSSOM => id::ROSESTONE,
        _ => id::STONE,
    }
}

fn mid_of(realm: i64, body: u8) -> u8 {
    use crate::biomes::*;
    if matches!(realm, MEADOW | AMBER | FEN | LUMEN | CEDAR | LAVENDER | VERDIGRIS | BLOSSOM | AUTUMN | AZURE | GOLDEN) {
        return id::LOAM;
    }
    match realm {
        DUNE => id::SAND,
        SALTWIND => id::SANDSTONE,
        CHALK => id::CHALK,
        FROST => id::SNOW,
        CLOUDSTEP => id::PALE_STONE,
        STARFALL => id::STARSTONE,
        CINDER => id::CINDER,
        _ => body,
    }
}

fn surf_of(realm: i64, body: u8, det: f64, peak: bool) -> u8 {
    use crate::biomes::*;
    let mut surf = if matches!(
        realm,
        MEADOW | AMBER | FEN | LUMEN | CEDAR | LAVENDER | VERDIGRIS | STARFALL | CLOUDSTEP | BLOSSOM | AUTUMN | AZURE | GOLDEN
    ) {
        id::TURF
    } else {
        body
    };
    if realm == DUNE { surf = id::SAND; }
    if realm == CHALK { surf = id::CHALK; }
    if realm == SALTWIND { surf = id::SANDSTONE; }
    if realm == FROST { surf = id::SNOW; }
    if realm == CINDER { surf = id::CINDER; }
    if realm == BASALT && det > 0.1 { surf = id::TURF; }
    if realm == ROSE && det > 0.15 { surf = id::TURF; }
    if realm == FROST && det > 0.35 { surf = id::ICE; }
    if realm == FEN && det < -0.32 { surf = id::CLAY; }
    if realm == SALTWIND && det < 0.05 { surf = id::CLAY; }
    if realm == CEDAR && det < -0.2 { surf = id::MOSSROCK; }
    if realm == CHALK && det > 0.25 { surf = id::COBBLE; }
    if realm == CLOUDSTEP && det > 0.2 { surf = id::SNOW; }
    if realm == VERDIGRIS && det > 0.15 { surf = id::MOSSROCK; }
    if realm == CINDER && det > 0.35 { surf = id::BASALT; }
    if realm == SALTWIND && det < 0.0 { surf = id::SALT_BLOCK; }
    if realm == LAVENDER && det > 0.22 { surf = id::HEATHER; }
    if realm == STARFALL && det < -0.2 { surf = id::STARSTONE; }
    if realm == AZURE && det > 0.30 { surf = id::ICE; }
    if realm == GOLDEN && det < -0.30 { surf = id::SAND; }
    if realm == AUTUMN && det > 0.32 { surf = id::CLAY; }
    if realm == CEDAR && det > 0.28 { surf = id::SLATE; }
    if peak && !matches!(realm, DUNE | LUMEN | SALTWIND | CINDER | CHALK) {
        surf = id::SNOW;
    }
    surf
}

fn put(chunk: &mut Chunk, lq: i32, y: i32, lr: i32, mat: u8, only_air: bool) {
    if !(0..CHUNK).contains(&lq) || !(0..CHUNK).contains(&lr) || !(0..LAYERS).contains(&y) {
        return;
    }
    let cur = chunk.get(lq, y, lr);
    if !only_air || cur == 0 || cur == id::PETALS {
        chunk.set(lq, y, lr, mat);
    }
}

fn disk(chunk: &mut Chunk, lq: i32, lr: i32, y: i32, radius: i32, mat: u8) {
    for dq in -radius..=radius {
        let lo = (-radius).max(-dq - radius);
        let hi = radius.min(-dq + radius);
        for dr in lo..=hi {
            put(chunk, lq + dq, y, lr + dr, mat, true);
        }
    }
}

fn plant_tree(chunk: &mut Chunk, lq: i32, lr: i32, top: i32, realm: i64, rng: &mut PyRng) {
    use crate::biomes::*;
    if tree_v6(chunk, lq, lr, top, realm, rng) {
        return;
    }
    let mut wood = id::HEARTWOOD;
    let leaf = id::CANOPY;
    if realm == CEDAR {
        wood = id::CEDAR_HEARTWOOD;
    } else if matches!(realm, SALTWIND | CHALK | CLOUDSTEP) {
        wood = id::PALE_HEARTWOOD;
    } else if matches!(realm, AMBER | VERDIGRIS) {
        wood = id::DARK_HEARTWOOD;
    }
    if realm == LUMEN {
        let hgt = rng.randint(6, 9);
        for y in top + 1..top + 1 + hgt {
            put(chunk, lq, y, lr, wood, true);
        }
        disk(chunk, lq, lr, top + hgt, 2, leaf);
        disk(chunk, lq, lr, top + hgt + 1, 1, leaf);
        for (dq, dr) in [(2, 0), (-2, 0), (0, 2), (0, -2), (2, -2), (-2, 2)] {
            put(chunk, lq + dq, top + hgt - 1, lr + dr, id::GLOWCAP, true);
        }
        return;
    }
    if realm == FROST {
        let hgt = rng.randint(8, 12);
        for y in top + 1..top + hgt {
            put(chunk, lq, y, lr, wood, true);
        }
        for (i, y) in (top + 5..=top + hgt).enumerate() {
            disk(chunk, lq, lr, y, (2 - (i as i32) / 2).max(0), leaf);
        }
        return;
    }
    if realm == DUNE || realm == CINDER {
        let h = rng.randint(3, 5);
        for y in top + 1..top + h {
            put(chunk, lq, y, lr, if realm == DUNE { id::CRYSTAL } else { id::BASALT }, true);
        }
        if realm == CINDER {
            put(chunk, lq, top + rng.randint(2, 4), lr, id::CRYSTAL, true);
        }
        return;
    }
    if realm == STARFALL {
        let hgt = rng.randint(6, 9);
        for y in top + 1..top + hgt {
            let m = if y > top + hgt - 3 { id::CRYSTAL } else { wood };
            put(chunk, lq, y, lr, m, true);
        }
        disk(chunk, lq, lr, top + hgt, 2, leaf);
        put(chunk, lq, top + hgt + 1, lr, id::LUMEN_SHARD, true);
        return;
    }
    if realm == CEDAR || realm == CLOUDSTEP {
        let hgt = if realm == CEDAR { rng.randint(9, 13) } else { rng.randint(7, 10) };
        for y in top + 1..top + hgt {
            put(chunk, lq, y, lr, wood, true);
        }
        for (i, y) in (top + 5..=top + hgt).enumerate() {
            let base = if realm == CEDAR { 2 } else { 1 };
            disk(chunk, lq, lr, y, (base - (i as i32) / 2).max(0), leaf);
        }
        return;
    }
    if realm == CHALK || realm == SALTWIND {
        let hgt = rng.randint(6, 8);
        for y in top + 1..top + hgt {
            put(chunk, lq, y, lr, wood, true);
        }
        disk(chunk, lq, lr, top + hgt, 1, leaf);
        return;
    }
    let hgt = rng.randint(7, 10) + if matches!(realm, AMBER | VERDIGRIS) { 2 } else { 0 };
    for y in top + 1..=top + hgt {
        put(chunk, lq, y, lr, wood, true);
    }
    let rad = if realm == ROSE { 1 } else { 2 };
    disk(chunk, lq, lr, top + hgt, rad, leaf);
    disk(chunk, lq, lr, top + hgt + 1, rad, leaf);
    disk(chunk, lq, lr, top + hgt + 2, (rad - 1).max(1), leaf);
    if matches!(realm, FEN | VERDIGRIS) {
        for (dq, dr) in [(2, 0), (-2, 0), (0, 2), (0, -2), (2, -2), (-2, 2)] {
            let drop = rng.randint(0, 1);
            for y in (top + hgt - 1 - drop)..(top + hgt + 1) {
                put(chunk, lq + dq, y, lr + dr, id::VINE, true);
            }
        }
    }
}

fn tree_v6(chunk: &mut Chunk, lq: i32, lr: i32, top: i32, realm: i64, rng: &mut PyRng) -> bool {
    use crate::biomes::*;
    let size = rng.random();
    if !matches!(realm, BLOSSOM | AUTUMN | AZURE | GOLDEN | LAVENDER) {
        if size < 0.30 && !matches!(realm, LUMEN | DUNE | CINDER | STARFALL) {
            let wood = if realm == CEDAR { id::CEDAR_HEARTWOOD } else { id::HEARTWOOD };
            let h = rng.randint(2, 4);
            for y in top + 1..top + 1 + h {
                put(chunk, lq, y, lr, wood, true);
            }
            disk(chunk, lq, lr, top + h + 1, 1, id::CANOPY);
            put(chunk, lq, top + h + 2, lr, id::CANOPY, true);
            return true;
        }
        return false;
    }
    let (wood, leaf, form) = if realm == BLOSSOM {
        (id::PALE_HEARTWOOD, id::BLOSSOM_CANOPY, "round")
    } else if realm == AUTUMN {
        (id::DARK_HEARTWOOD, id::AUTUMN_CANOPY, "tall")
    } else if realm == AZURE {
        (id::PALE_HEARTWOOD, id::FROST_CANOPY, "cone")
    } else if realm == GOLDEN {
        (id::HEARTWOOD, id::GOLDEN_CANOPY, "flat")
    } else if size < 0.35 {
        (id::DARK_HEARTWOOD, id::VIOLET_CANOPY, "round")
    } else {
        return false;
    };
    let big = size > 0.65;
    if form == "round" {
        let h = rng.randint(5, 7) + if big { 2 } else { 0 };
        for y in top + 1..=top + h {
            put(chunk, lq, y, lr, wood, true);
        }
        let rad = if big { 3 } else { 2 };
        disk(chunk, lq, lr, top + h, rad, leaf);
        disk(chunk, lq, lr, top + h + 1, rad, leaf);
        disk(chunk, lq, lr, top + h + 2, rad - 1, leaf);
    } else if form == "tall" {
        let h = rng.randint(9, 12) + if big { 3 } else { 0 };
        for y in top + 1..=top + h {
            put(chunk, lq, y, lr, wood, true);
        }
        for y in (top + h - 4)..(top + h + 2) {
            disk(chunk, lq, lr, y, if y < top + h { 2 } else { 1 }, leaf);
        }
    } else if form == "cone" {
        let h = rng.randint(8, 12) + if big { 3 } else { 0 };
        for y in top + 1..top + h {
            put(chunk, lq, y, lr, wood, true);
        }
        for (i, y) in (top + 3..=top + h).enumerate() {
            let rad = ((if big { 3 } else { 2 }) - (i as i32) / 3).max(0);
            disk(chunk, lq, lr, y, rad, leaf);
        }
    } else {
        let h = rng.randint(6, 8) + if big { 2 } else { 0 };
        for y in top + 1..=top + h {
            put(chunk, lq, y, lr, wood, true);
        }
        disk(chunk, lq, lr, top + h + 1, if big { 3 } else { 2 }, leaf);
    }
    true
}

fn place_ores(gen: &Generator, chunk: &mut Chunk, q0: i64, r0: i64) {
    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let mut top = -1;
            for y in (0..LAYERS).rev() {
                let idn = chunk.get(lq, y, lr);
                if crate::materials::is_solid(idn) && idn != id::WATER {
                    top = y;
                    break;
                }
            }
            if top < 6 {
                continue;
            }
            let q = (q0 + lq as i64) as f64;
            let r = (r0 + lr as i64) as f64;
            for y in 0..top {
                let idn = chunk.get(lq, y, lr);
                if !crate::materials::is_solid(idn) || idn == id::WATER {
                    continue;
                }
                if let Some(ore) = gen.ore_at(q, r, y as f64, top - y) {
                    chunk.set(lq, y, lr, ore);
                }
            }
        }
    }
}

const SPIRE_REGION: i64 = 88;

fn stamp_spires(gen: &Generator, chunk: &mut Chunk) {
    let q0 = chunk.cq as i64 * CHUNK as i64;
    let r0 = chunk.cr as i64 * CHUNK as i64;
    let rq0 = (q0 - 8).div_euclid(SPIRE_REGION);
    let rq1 = (q0 + CHUNK as i64 + 8).div_euclid(SPIRE_REGION);
    let rr0 = (r0 - 8).div_euclid(SPIRE_REGION);
    let rr1 = (r0 + CHUNK as i64 + 8).div_euclid(SPIRE_REGION);
    for rq in rq0..=rq1 {
        for rr in rr0..=rr1 {
            let hsh = hash_ints(gen.h, &[rq, rr, 77]);
            if (hsh & 0xFFFF) as f64 / 65536.0 >= gen.spire_rate {
                continue;
            }
            let m = SPIRE_REGION - 20;
            let q = rq * SPIRE_REGION + 10 + ((hsh >> 16) % m as u64) as i64;
            let r = rr * SPIRE_REGION + 10 + ((hsh >> 32) % m as u64) as i64;
            let col = gen.sample(q, r);
            if !(col.land && !col.skerry && col.e > 0.07 && !col.pool) {
                continue;
            }
            let height = 7 + ((hsh >> 48) % 6) as i32;
            let top = col.top;
            for dq in -4..=4 {
                for dr in -4..=4 {
                    let dist = crate::hex::hex_distance(0, 0, dq, dr);
                    if dist > 4 {
                        continue;
                    }
                    let lq = (q + dq - q0) as i32;
                    let lr = (r + dr - r0) as i32;
                    if !(0..CHUNK).contains(&lq) || !(0..CHUNK).contains(&lr) {
                        continue;
                    }
                    for y in top + 1..top + 16 {
                        chunk.set(lq, y, lr, 0);
                    }
                    if dist <= 3 {
                        for y in top - 3..=top {
                            if chunk.get(lq, y, lr) == 0 || chunk.get(lq, y, lr) == id::WATER {
                                chunk.set(lq, y, lr, if dist <= 2 { id::PLINTH } else { id::STONE });
                            }
                        }
                        if dist <= 2 {
                            chunk.set(lq, top, lr, id::PLINTH);
                        }
                    }
                    if dist == 0 {
                        for y in top + 1..top + 1 + height {
                            chunk.set(lq, y, lr, id::DORMANT_SPIRE);
                        }
                    }
                    if dist == 3 && (dq + 2 * dr) % 2 == 0 {
                        let hp = 1 + (dq * 7 + dr * 3).unsigned_abs() as i32 % 3;
                        for y in top + 1..top + 1 + hp {
                            chunk.set(lq, y, lr, id::PLINTH);
                        }
                    }
                }
            }
        }
    }
}

/// Open caves under a solid roof, then seal any that break the walking surface.
fn carve_caves(gen: &Generator, chunk: &mut Chunk, q0: i64, r0: i64) {
    let original = chunk.cells.clone();
    let mut carved = vec![false; original.len()];
    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let mut top = -1;
            for y in (0..LAYERS).rev() {
                let id = chunk.get(lq, y, lr);
                if crate::materials::is_solid(id) && id != id::WATER {
                    top = y;
                    break;
                }
            }
            if top < 8 {
                continue;
            }
            let q = q0 + lq as i64;
            let r = r0 + lr as i64;
            for y in 0..top {
                let id = chunk.get(lq, y, lr);
                if !crate::materials::is_solid(id) || id == id::WATER {
                    continue;
                }
                let d = top - y;
                if gen.cave_hole(q as f64, r as f64, y as f64, d) {
                    let ix = Chunk::index(lq, y, lr);
                    carved[ix] = true;
                    chunk.cells[ix] = 0;
                }
            }
        }
    }
    // Air, plus two hex steps of it, is "outside". Caves that touch it are filled
    // back in so the shore is not full of holes. The top five layers stay solid.
    let mut outside = vec![false; original.len()];
    for i in 0..original.len() {
        outside[i] = !crate::materials::is_solid(original[i]);
    }
    for _ in 0..2 {
        let prev = outside.clone();
        for lq in 0..CHUNK {
            for lr in 0..CHUNK {
                for y in 0..LAYERS {
                    let ix = Chunk::index(lq, y, lr);
                    if prev[ix] {
                        outside[ix] = true;
                        continue;
                    }
                    let mut touch = false;
                    for (dq, dr) in DIRS {
                        let a = lq + dq;
                        let b = lr + dr;
                        if (0..CHUNK).contains(&a) && (0..CHUNK).contains(&b) && prev[Chunk::index(a, y, b)] {
                            touch = true;
                            break;
                        }
                    }
                    if y > 0 && prev[Chunk::index(lq, y - 1, lr)] {
                        touch = true;
                    }
                    if y + 1 < LAYERS && prev[Chunk::index(lq, y + 1, lr)] {
                        touch = true;
                    }
                    outside[ix] = touch;
                }
            }
        }
    }
    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let mut top = -1;
            for y in (0..LAYERS).rev() {
                if crate::materials::is_solid(original[Chunk::index(lq, y, lr)]) {
                    top = y;
                    break;
                }
            }
            for y in 0..LAYERS {
                let ix = Chunk::index(lq, y, lr);
                if carved[ix] && (outside[ix] || top - y < 5) {
                    chunk.cells[ix] = original[ix];
                }
            }
        }
    }
    frame_mouths(gen, chunk, &original, q0, r0);
    // Glowcaps and crystals on cave floors.
    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let q = q0 + lq as i64;
            let r = r0 + lr as i64;
            for y in 1..LAYERS {
                let ix = Chunk::index(lq, y, lr);
                if !carved[ix] || chunk.cells[ix] != 0 {
                    continue;
                }
                let below = chunk.get(lq, y - 1, lr);
                if below == 0 || below == id::WATER {
                    continue;
                }
                if rand01(q, r * 7 + y as i64, gen.h.wrapping_add(31)) < 0.04 {
                    let mat = if (lq + lr + y) % 3 == 0 { id::CRYSTAL } else { id::GLOWCAP };
                    chunk.set(lq, y, lr, mat);
                }
            }
        }
    }
}

/// Cobble-framed tunnels from the cliff face into a sealed cave.
fn frame_mouths(gen: &Generator, chunk: &mut Chunk, original: &[u8], q0: i64, r0: i64) {
    let mut interior = vec![false; original.len()];
    for i in 0..original.len() {
        interior[i] = crate::materials::is_solid(original[i]) && chunk.cells[i] == 0;
    }
    let mut reach = interior.clone();
    for _ in 0..4 {
        let prev = reach.clone();
        for lq in 0..CHUNK {
            for lr in 0..CHUNK {
                for y in 0..LAYERS {
                    let ix = Chunk::index(lq, y, lr);
                    if prev[ix] {
                        reach[ix] = true;
                        continue;
                    }
                    for (dq, dr) in DIRS {
                        let a = lq + dq;
                        let b = lr + dr;
                        if (0..CHUNK).contains(&a)
                            && (0..CHUNK).contains(&b)
                            && prev[Chunk::index(a, y, b)]
                        {
                            reach[ix] = true;
                            break;
                        }
                    }
                    if y > 0 && prev[Chunk::index(lq, y - 1, lr)] {
                        reach[ix] = true;
                    }
                    if y + 1 < LAYERS && prev[Chunk::index(lq, y + 1, lr)] {
                        reach[ix] = true;
                    }
                }
            }
        }
    }
    let mut picks: Vec<(f64, i32, i32, i32)> = Vec::new();
    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let q = q0 + lq as i64;
            let r = r0 + lr as i64;
            let mut top = -1i32;
            let mut bot = LAYERS;
            for y in 0..LAYERS {
                if crate::materials::is_solid(original[Chunk::index(lq, y, lr)]) {
                    if top < 0 {
                        bot = y;
                    }
                    top = y;
                }
            }
            if top < 0 {
                continue;
            }
            let mut ys = Vec::new();
            for y in 0..LAYERS {
                let ix = Chunk::index(lq, y, lr);
                if !reach[ix] || !crate::materials::is_solid(original[ix]) {
                    continue;
                }
                let d = top - y;
                if d < 6 || d > 18 || y - bot < 3 {
                    continue;
                }
                let mut open = false;
                for (dq, dr) in DIRS {
                    let a = lq + dq;
                    let b = lr + dr;
                    if !(0..CHUNK).contains(&a) || !(0..CHUNK).contains(&b) {
                        open = true;
                        break;
                    }
                    if !crate::materials::is_solid(original[Chunk::index(a, y, b)]) {
                        open = true;
                        break;
                    }
                }
                if open {
                    ys.push(y);
                }
            }
            if ys.is_empty() {
                continue;
            }
            let roll = rand01(q, r, gen.h.wrapping_add(91));
            picks.push((roll, lq, lr, ys[ys.len() / 2]));
        }
    }
    if picks.is_empty() {
        return;
    }
    picks.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    let mut chosen: Vec<_> = picks.iter().copied().filter(|p| p.0 < 0.07).collect();
    if chosen.is_empty() {
        chosen.push(picks[0]);
    }
    chosen.truncate(2);
    for (_, lq, lr, y) in chosen {
        let y2 = (y + 1).min(LAYERS - 1);
        let mut path = vec![(lq, lr)];
        let (mut ca, mut cb) = (lq, lr);
        for _ in 0..5 {
            let mut nxt = None;
            for (dq, dr) in DIRS {
                let na = ca + dq;
                let nb = cb + dr;
                if !(0..CHUNK).contains(&na) || !(0..CHUNK).contains(&nb) {
                    continue;
                }
                if !crate::materials::is_solid(original[Chunk::index(na, y, nb)]) {
                    continue;
                }
                if path.contains(&(na, nb)) {
                    continue;
                }
                nxt = Some((na, nb));
                let ix = Chunk::index(na, y, nb);
                if interior[ix] || interior[Chunk::index(na, y2, nb)] {
                    break;
                }
            }
            let Some(n) = nxt else { break };
            path.push(n);
            let ix = Chunk::index(n.0, y, n.1);
            if interior[ix] || interior[Chunk::index(n.0, y2, n.1)] {
                break;
            }
            (ca, cb) = n;
        }
        for (pa, pb) in &path {
            chunk.set(*pa, y, *pb, 0);
            chunk.set(*pa, y2, *pb, 0);
        }
        let top = (0..LAYERS)
            .rev()
            .find(|yy| crate::materials::is_solid(original[Chunk::index(lq, *yy, lr)]))
            .unwrap_or(y);
        for dy in [-1, 0, 1, 2] {
            let ny = y + dy;
            if !(0..LAYERS).contains(&ny) || top - ny < 2 {
                continue;
            }
            for (dq, dr) in DIRS {
                let na = lq + dq;
                let nb = lr + dr;
                if !(0..CHUNK).contains(&na) || !(0..CHUNK).contains(&nb) {
                    continue;
                }
                if path.iter().any(|(pa, pb)| *pa == na && *pb == nb) {
                    continue;
                }
                if chunk.get(na, ny, nb) != 0 {
                    chunk.set(na, ny, nb, id::COBBLE);
                }
            }
            if matches!(dy, -1 | 2) && chunk.get(lq, ny, lr) != 0 {
                chunk.set(lq, ny, lr, id::COBBLE);
            }
        }
    }
}

/// A column of non-water cells with no solid neighbour, ten or more layers tall.
pub fn pillar_runs(chunk: &Chunk) -> usize {
    let mut runs = 0;
    for i in 1..CHUNK - 1 {
        for k in 1..CHUNK - 1 {
            let mut y = 0;
            while y < LAYERS {
                if lone_solid(chunk, i, y, k) {
                    let y0 = y;
                    while y < LAYERS && lone_solid(chunk, i, y, k) {
                        y += 1;
                    }
                    if y - y0 >= 10 {
                        let only_spire = (y0..y).all(|yy| chunk.get(i, yy, k) == id::DORMANT_SPIRE);
                        if !only_spire {
                            runs += 1;
                        }
                    }
                } else {
                    y += 1;
                }
            }
        }
    }
    runs
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::columns::{size_class, MainScale, SizeClass};
    use crate::settings::Settings;
    use std::collections::HashSet;

    #[test]
    fn caves_sit_under_a_solid_roof() {
        let g = Generator::new(7, Settings::default());
        let c = generate(&g, 1, 3);
        let mut holes = 0;
        for lq in 1..CHUNK - 1 {
            for lr in 1..CHUNK - 1 {
                let mut top = -1;
                for y in (0..LAYERS).rev() {
                    if crate::materials::is_solid(c.get(lq, y, lr)) {
                        top = y;
                        break;
                    }
                }
                if top < 12 {
                    continue;
                }
                for y in 2..top - 5 {
                    if c.get(lq, y, lr) == 0
                        && crate::materials::is_solid(c.get(lq, y - 1, lr))
                        && crate::materials::is_solid(c.get(lq, y + 1, lr))
                    {
                        holes += 1;
                    }
                }
            }
        }
        assert!(holes > 0, "enclosed cave cells {holes}");
        let mut ore = 0;
        for idn in &c.cells {
            if matches!(*idn, id::EMBERITE_ORE | id::VERDIGRIS_ORE | id::SILVERINE_ORE | id::AETHERITE_ORE) {
                ore += 1;
            }
        }
        assert!(ore > 0, "no ore in a thick chunk");
    }

    #[test]
    fn chunk_is_deterministic_and_has_no_pillars() {
        let g = Generator::new(7, Settings::default());
        let t = std::time::Instant::now();
        let a = generate(&g, 0, 0);
        let ms = t.elapsed().as_secs_f64() * 1000.0;
        let b = generate(&g, 0, 0);
        assert_eq!(a.cells, b.cells);
        assert!(a.cells.iter().any(|&c| c != 0), "chunk 0,0 should contain land or a tier");
        assert_eq!(pillar_runs(&a), 0, "chunk gen took {ms:.1} ms");
        let mut solids = 0;
        for c in &a.cells {
            if *c != 0 { solids += 1; }
        }
        eprintln!("chunk 0,0 solids {solids} in {ms:.1} ms");
    }

    #[test]
    fn five_size_classes_exist() {
        let g = Generator::new(7, Settings::default());
        let mut kinds = HashSet::new();
        for scale in [MainScale::Huge, MainScale::Large, MainScale::Medium, MainScale::Small] {
            let mut found = 0.0;
            for ci in -6..6 {
                for cj in -6..6 {
                    let r = g.main_island_radius(scale, ci, cj);
                    if r > found { found = r; }
                }
            }
            assert!(found > 0.0, "scale present");
            kinds.insert(size_class(found));
        }
        let tiers = crate::tiers::tier_classes(&g, 400);
        for k in tiers { kinds.insert(k); }
        for need in [SizeClass::Tiny, SizeClass::Small, SizeClass::Medium, SizeClass::Large, SizeClass::Huge] {
            assert!(kinds.contains(&need), "missing {need:?} in {kinds:?}");
        }
    }
}

fn lone_solid(chunk: &Chunk, i: i32, y: i32, k: i32) -> bool {
    let idn = chunk.get(i, y, k);
    if idn == 0 || idn == id::WATER || !crate::materials::is_solid(idn) {
        return false;
    }
    for (dq, dr) in DIRS {
        let n = chunk.get(i + dq, y, k + dr);
        if n != 0 && n != id::WATER && crate::materials::is_solid(n) {
            return false;
        }
    }
    true
}

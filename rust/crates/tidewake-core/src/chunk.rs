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

    let mut chunk = Chunk {
        cq,
        cr,
        cells: vec![0u8; (CHUNK * LAYERS * CHUNK) as usize],
        realm: vec![0u8; (CHUNK * CHUNK) as usize],
    };
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

    tiers::stamp(gen, cq, cr, &mut chunk);
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
                        runs += 1;
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

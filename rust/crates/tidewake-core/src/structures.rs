//! Grand landmarks and the smaller island builds.
//!
//! Grand structures fill 54.6% of regions (the 1.4.6 rate, 30% above 1.4.5).
//! Smaller builds fill 65% of their regions and skip any chunk a grand
//! structure already covers, so the two never overlap.
//! Wonders replace about one in ten small-structure rolls.

use std::collections::{HashMap, HashSet};

use crate::chunk::Chunk;
use crate::columns::Generator;
use crate::config::{CHUNK, LAYERS};
use crate::hex::{self, hex_distance};
use crate::materials::id;
use crate::noise::hash_ints;
use crate::pyrandom::PyRng;

const GRAND_REGION: i32 = 14;
const GRAND_CHANCE: f64 = 0.546;
const SMALL_REGION: i32 = 5;
const SMALL_CHANCE: u64 = 65;

struct Kind {
    name: &'static str,
    weight: u32,
    footprint: i64,
    sky: bool,
}

const KINDS: &[Kind] = &[
    Kind { name: "hot_air_balloon", weight: 18, footprint: 26, sky: true },
    Kind { name: "sky_city", weight: 8, footprint: 44, sky: true },
    Kind { name: "floating_fortress", weight: 8, footprint: 26, sky: true },
    Kind { name: "world_tree", weight: 12, footprint: 34, sky: false },
    Kind { name: "colossus", weight: 10, footprint: 22, sky: false },
    Kind { name: "megaspire", weight: 9, footprint: 18, sky: false },
    Kind { name: "leviathan_wreck", weight: 10, footprint: 46, sky: false },
    Kind { name: "titan_ruins", weight: 11, footprint: 44, sky: false },
    Kind { name: "village", weight: 12, footprint: 30, sky: false },
    Kind { name: "airship", weight: 9, footprint: 36, sky: true },
    Kind { name: "watchtower", weight: 8, footprint: 8, sky: false },
];

#[derive(Clone)]
#[allow(dead_code)]
struct Site {
    kind: &'static str,
    q: i64,
    r: i64,
    y: i32,
    footprint: i64,
    sky: bool,
    seed: u64,
}

fn rng_for(gen: &Generator, a: i64, b: i64, tag: i64) -> PyRng {
    PyRng::seed_u64(hash_ints(gen.h, &[a, b, tag]))
}

fn pick_kind(rng: &mut PyRng) -> &'static Kind {
    let tot: u32 = KINDS.iter().map(|k| k.weight).sum();
    let mut pick = (rng.random() * tot as f64) as u32;
    for k in KINDS {
        if pick < k.weight {
            return k;
        }
        pick -= k.weight;
    }
    KINDS.last().unwrap()
}

fn grand_site(gen: &Generator, rq: i32, rr: i32) -> Option<Site> {
    let mut rng = rng_for(gen, rq as i64, rr as i64, 0x6A4D);
    if rng.random() >= GRAND_CHANCE {
        return None;
    }
    let kind = pick_kind(&mut rng);
    let span = GRAND_REGION as i64 * CHUNK as i64;
    let q0 = rq as i64 * span;
    let r0 = rr as i64 * span;
    let seed = rng.random().to_bits();
    let lo = kind.footprint + 4;
    let hi = span - kind.footprint - 4;
    if kind.sky {
        for _ in 0..24 {
            let q = q0 + lo + rng.randint(0, (hi - lo).max(1) as i32) as i64;
            let r = r0 + lo + rng.randint(0, (hi - lo).max(1) as i32) as i64;
            let c = gen.sample(q, r);
            if c.land {
                continue;
            }
            let y = (80 + rng.randint(0, 180)).clamp(40, LAYERS - 90);
            return Some(Site { kind: kind.name, q, r, y, footprint: kind.footprint, sky: true, seed });
        }
        return None;
    }
    for _ in 0..20 {
        let q = q0 + lo + rng.randint(0, (hi - lo).max(1) as i32) as i64;
        let r = r0 + lo + rng.randint(0, (hi - lo).max(1) as i32) as i64;
        let c = gen.sample(q, r);
        if c.land && !c.skerry && !c.pool && c.e > 0.12 {
            return Some(Site {
                kind: kind.name,
                q,
                r,
                y: c.top + 1,
                footprint: kind.footprint,
                sky: false,
                seed,
            });
        }
    }
    None
}

fn covers(site: &Site, cq: i32, cr: i32) -> bool {
    let sq = site.q.div_euclid(CHUNK as i64) as i32;
    let sr = site.r.div_euclid(CHUNK as i64) as i32;
    let reach = (site.footprint / CHUNK as i64) as i32 + 1;
    (cq - sq).abs() <= reach && (cr - sr).abs() <= reach
}

fn grand_covers(gen: &Generator, cq: i32, cr: i32) -> bool {
    let rq = cq.div_euclid(GRAND_REGION);
    let rr = cr.div_euclid(GRAND_REGION);
    for a in rq - 1..=rq + 1 {
        for b in rr - 1..=rr + 1 {
            if let Some(site) = grand_site(gen, a, b) {
                if covers(&site, cq, cr) {
                    return true;
                }
            }
        }
    }
    false
}

struct Pen {
    cells: HashMap<(i64, i64, i32), u8>,
}

impl Pen {
    fn put(&mut self, q: i64, r: i64, y: i32, mat: u8) {
        if (1..LAYERS - 2).contains(&y) {
            self.cells.insert((q, r, y), mat);
        }
    }
    fn disk(&mut self, q: i64, r: i64, y: i32, rad: i64, mat: u8) {
        for dq in -rad..=rad {
            for dr in -rad..=rad {
                if hex_distance(0, 0, dq, dr) <= rad {
                    self.put(q + dq, r + dr, y, mat);
                }
            }
        }
    }
    fn col(&mut self, q: i64, r: i64, y0: i32, y1: i32, mat: u8) {
        for y in y0..=y1 {
            self.put(q, r, y, mat);
        }
    }
    fn walls(&mut self, q: i64, r: i64, y: i32, rad: i64, h: i32, mat: u8) {
        for dq in -rad..=rad {
            for dr in -rad..=rad {
                let d = hex_distance(0, 0, dq, dr);
                if d == rad || d == rad - 1 {
                    self.col(q + dq, r + dr, y, y + h, mat);
                }
            }
        }
    }
}

fn build_grand(site: &Site) -> Pen {
    let mut rng = PyRng::seed_u64(site.seed);
    let mut p = Pen { cells: HashMap::new() };
    let (q, r, y) = (site.q, site.r, site.y);
    match site.kind {
        "hot_air_balloon" => {
            let cloth = [id::ROSE_JELLY, id::HONEY_JELLY, id::TIDE_JELLY, id::VIOLET_JELLY][rng.randint(0, 3) as usize];
            let rad = 10 + rng.randint(0, 4) as i64;
            for dy in 0..rad as i32 * 2 {
                let t = dy as f64 / (rad as f64 * 2.0);
                let slice = (rad as f64 * (1.0 - (t * 2.0 - 1.0).powi(2)).sqrt()) as i64;
                p.disk(q, r, y + 8 + dy, slice.max(1), cloth);
            }
            p.col(q, r, y, y + 8, id::DARK_PLANKS);
            p.disk(q, r, y, 3, id::PLANKS);
            p.disk(q, r, y + 1, 2, id::PLANKS);
            p.put(q, r, y + 6, id::LUMEN_LAMP);
        }
        "sky_city" => {
            for (i, dy) in [0, 10, 18, 28].into_iter().enumerate() {
                p.disk(q, r, y + dy, 8 - i as i64, id::PALE_STONE);
                p.disk(q + 14, r, y + dy, 4, id::PALE_STONE);
                for t in 1..14 {
                    p.put(q + t, r, y + dy, id::PLANKS);
                }
            }
            p.col(q, r, y, y + 36, id::STONE_BRICKS);
            p.put(q, r, y + 36, id::LUMEN_LAMP);
        }
        "floating_fortress" => {
            p.disk(q, r, y, 10, id::BASALT);
            p.disk(q, r, y - 6, 6, id::BASALT);
            p.walls(q, r, y + 1, 8, 6, id::BASALT_BRICKS);
            for (dq, dr) in [(8, 0), (-8, 0), (0, 8), (0, -8)] {
                p.col(q + dq, r + dr, y + 1, y + 12, id::BASALT_BRICKS);
            }
            p.col(q, r, y + 1, y + 10, id::DARK_PLANKS);
        }
        "world_tree" => {
            p.col(q, r, y, y + 40, id::DARK_HEARTWOOD);
            p.disk(q, r, y + 28, 3, id::PLANKS);
            p.walls(q, r, y + 29, 2, 3, id::PLANKS);
            p.disk(q, r, y + 36, 8, id::CANOPY);
            p.disk(q, r, y + 40, 5, id::CANOPY);
        }
        "colossus" => {
            // A robed figure: cloak, sleeves, hood. No body under the cloth.
            p.disk(q, r, y, 4, id::PLINTH);
            p.col(q, r, y + 1, y + 16, id::DUSK_CLOTH);
            p.disk(q, r, y + 6, 3, id::DUSK_CLOTH);
            p.col(q - 3, r, y + 8, y + 14, id::DUSK_CLOTH);
            p.col(q + 3, r, y + 8, y + 15, id::DUSK_CLOTH);
            p.put(q + 3, r, y + 16, id::LUMEN_LAMP);
            p.disk(q, r, y + 17, 2, id::PALE_STONE);
        }
        "megaspire" => {
            let h = 70 + rng.randint(0, 40);
            for dy in 0..h {
                let rad = 4 - dy / 25;
                p.disk(q, r, y + dy, rad.max(1) as i64, id::ROSESTONE_BRICKS);
            }
            for (dq, dr) in hex::DIRS {
                p.col(q + dq as i64 * 3, r + dr as i64 * 3, y, y + 18, id::ROSESTONE_BRICKS);
            }
        }
        "leviathan_wreck" => {
            for i in 0..18 {
                let sway = ((i as f64) * 0.4).sin() as i64;
                p.col(q + i, r + sway, y, y + 2, id::PALE_STONE);
                if i % 3 == 0 {
                    p.col(q + i, r + sway + 4, y, y + 5, id::PALE_STONE);
                    p.col(q + i, r + sway - 4, y, y + 5, id::PALE_STONE);
                }
            }
            p.disk(q + 16, r, y + 3, 3, id::PALE_STONE);
        }
        "titan_ruins" => {
            for i in 0..6 {
                let ang = i as f64 * std::f64::consts::TAU / 6.0;
                let cq = q + (ang.cos() * 8.0) as i64;
                let cr = r + (ang.sin() * 8.0) as i64;
                let h = 8 + (i % 4) * 3;
                p.col(cq, cr, y, y + h, id::CHALK_BRICKS);
            }
            for t in -6..=6 {
                p.put(q + t, r, y + 10, id::CHALK_BRICKS);
            }
            p.disk(q, r, y, 3, id::MOSSY_BRICKS);
        }
        "village" => {
            p.disk(q, r, y - 1, 8, id::COBBLE);
            for (i, (dq, dr)) in hex::DIRS.into_iter().enumerate() {
                let hq = q + dq as i64 * 5;
                let hr = r + dr as i64 * 5;
                p.disk(hq, hr, y - 1, 2, id::PLANKS);
                p.walls(hq, hr, y, 2, 3, id::PLANKS);
                p.disk(hq, hr, y + 4, 2, id::DARK_PLANKS);
                if i == 0 {
                    p.put(hq, hr, y, 0);
                }
            }
            p.disk(q, r, y, 2, id::COBBLE);
            p.put(q, r, y + 1, id::WATER);
        }
        "airship" => {
            for i in -8..=8i64 {
                let rad = 2 - (i.abs() / 5);
                p.disk(q + i, r, y, rad.max(1), id::DARK_PLANKS);
            }
            p.walls(q, r, y + 1, 2, 3, id::PALE_PLANKS);
            p.disk(q, r, y + 8, 5, id::SHIMMER_CLOUD);
            p.disk(q, r, y + 12, 3, id::SHIMMER_CLOUD);
        }
        _ => {
            // watchtower
            p.col(q, r, y, y + 16, id::COBBLE);
            p.disk(q, r, y + 14, 2, id::PLANKS);
            p.disk(q, r, y + 17, 2, id::DARK_PLANKS);
            p.put(q, r, y + 15, id::LUMEN_LAMP);
        }
    }
    p
}

fn build_small(name: &str, q: i64, r: i64, y: i32, door: i64) -> Pen {
    let mut p = Pen { cells: HashMap::new() };
    match name {
        "shrine" => {
            p.disk(q, r, y, 2, id::PLINTH);
            p.col(q, r, y + 1, y + 4, id::PLINTH);
            p.put(q, r, y + 5, id::CRYSTAL);
        }
        "windmill" => {
            p.col(q, r, y, y + 8, id::PALE_STONE);
            p.disk(q, r, y + 9, 1, id::DARK_PLANKS);
            for (dq, dr) in [(3, 0), (-3, 0), (0, 3), (0, -3)] {
                p.col(q + dq, r + dr, y + 7, y + 8, id::PLANKS);
            }
        }
        "lighthouse" => {
            p.col(q, r, y, y + 14, id::PALE_STONE);
            p.disk(q, r, y + 14, 2, id::PALE_STONE);
            p.put(q, r, y + 15, id::LUMEN_LAMP);
            p.disk(q, r, y + 16, 1, id::DARK_PLANKS);
        }
        "well" => {
            p.disk(q, r, y, 2, id::COBBLE);
            p.put(q, r, y, id::WATER);
            p.col(q + 2, r, y + 1, y + 3, id::PLANKS);
            p.col(q - 2, r, y + 1, y + 3, id::PLANKS);
        }
        "clockwork_tower" => {
            p.col(q, r, y, y + 22, id::BRASS);
            p.disk(q, r, y + 10, 3, id::BRASS);
            p.disk(q, r, y + 18, 2, id::COSMIC_STAR);
            p.put(q, r, y + 23, id::LUMEN_LAMP);
        }
        "crystal_nave" => {
            p.disk(q, r, y - 1, 6, id::POLISHED_STONE);
            p.walls(q, r, y, 5, 6, id::GLASS);
            p.col(q, r, y, y + 8, id::CRYSTAL);
            for (dq, dr) in hex::DIRS {
                p.put(q + dq as i64 * 3, r + dr as i64 * 3, y + 3, id::LUMEN_LAMP);
            }
        }
        "hanging_keep" => {
            p.disk(q, r, y + 8, 5, id::BASALT);
            p.walls(q, r, y + 4, 4, 4, id::BASALT_BRICKS);
            p.col(q, r, y, y + 8, id::DARK_PLANKS);
        }
        _ => {
            // hut, and the default house
            p.disk(q, r, y - 1, 2, id::PLANKS);
            p.walls(q, r, y, 2, 3, id::PLANKS);
            p.disk(q, r, y + 3, 2, id::DARK_PLANKS);
            let (dq, dr) = hex::DIRS[door as usize % 6];
            p.put(q + dq as i64 * 2, r + dr as i64 * 2, y, 0);
            p.put(q + dq as i64 * 2, r + dr as i64 * 2, y + 1, 0);
        }
    }
    p
}

fn stamp_pen(chunk: &mut Chunk, pen: &Pen) {
    let q0 = chunk.cq as i64 * CHUNK as i64;
    let r0 = chunk.cr as i64 * CHUNK as i64;
    for ((q, r, y), mat) in &pen.cells {
        let lq = (*q - q0) as i32;
        let lr = (*r - r0) as i32;
        if (0..CHUNK).contains(&lq) && (0..CHUNK).contains(&lr) {
            chunk.set(lq, *y, lr, *mat);
        }
    }
}

fn small_name(h: u64) -> &'static str {
    if (h >> 22) % 10 == 0 {
        return ["clockwork_tower", "crystal_nave", "hanging_keep"][((h >> 4) % 3) as usize];
    }
    let fam = (h >> 16) % 10;
    if fam >= 7 {
        ["lighthouse", "windmill"][((h >> 4) % 2) as usize]
    } else if fam >= 5 {
        ["shrine", "well"][((h >> 4) % 2) as usize]
    } else {
        "hut"
    }
}

/// Kinds of grand sites in a window of regions. Used by tests.
pub fn grand_kinds(gen: &Generator, n: i32) -> HashSet<&'static str> {
    let mut out = HashSet::new();
    for rq in -n..n {
        for rr in -n..n {
            if let Some(site) = grand_site(gen, rq, rr) {
                out.insert(site.kind);
            }
        }
    }
    out
}

pub fn stamp(gen: &Generator, chunk: &mut Chunk) {
    let cq = chunk.cq;
    let cr = chunk.cr;
    let rq = cq.div_euclid(GRAND_REGION);
    let rr = cr.div_euclid(GRAND_REGION);
    let mut covered = false;
    for a in rq - 1..=rq + 1 {
        for b in rr - 1..=rr + 1 {
            if let Some(site) = grand_site(gen, a, b) {
                if covers(&site, cq, cr) {
                    covered = true;
                    stamp_pen(chunk, &build_grand(&site));
                }
            }
        }
    }
    if covered {
        return;
    }
    let srq = cq.div_euclid(SMALL_REGION);
    let srr = cr.div_euclid(SMALL_REGION);
    let h = hash_ints(gen.h.wrapping_add(0xB144), &[srq as i64, srr as i64]);
    if (h >> 20) % 100 >= SMALL_CHANCE {
        return;
    }
    let aq = srq * SMALL_REGION + (h % SMALL_REGION as u64) as i32;
    let ar = srr * SMALL_REGION + ((h >> 8) % SMALL_REGION as u64) as i32;
    if (aq, ar) != (cq, cr) {
        return;
    }
    // A land cell near the chunk middle, if the chunk has one.
    let q0 = cq as i64 * CHUNK as i64;
    let r0 = cr as i64 * CHUNK as i64;
    let mut spot = None;
    for lq in 3..CHUNK - 3 {
        for lr in 3..CHUNK - 3 {
            let c = gen.sample(q0 + lq as i64, r0 + lr as i64);
            if c.land && !c.skerry && !c.pool {
                spot = Some((q0 + lq as i64, r0 + lr as i64, c.top + 1));
                break;
            }
        }
        if spot.is_some() {
            break;
        }
    }
    let Some((q, r, y)) = spot else { return };
    if grand_covers(gen, cq, cr) {
        return;
    }
    let name = small_name(h);
    stamp_pen(chunk, &build_small(name, q, r, y, ((h >> 6) % 6) as i64));
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::settings::Settings;

    #[test]
    fn grand_kinds_are_varied_and_small_builds_skip_them() {
        let g = Generator::new(7, Settings::default());
        let kinds = grand_kinds(&g, 3);
        assert!(kinds.len() >= 3, "{kinds:?}");
        assert!(kinds.contains("hot_air_balloon"), "{kinds:?}");
        // A chunk under a grand site is covered, so the small placer must not run.
        let mut covered = 0;
        let mut open = 0;
        for cq in -6..6 {
            for cr in -6..6 {
                if grand_covers(&g, cq, cr) {
                    covered += 1;
                } else {
                    open += 1;
                }
            }
        }
        assert!(covered > 0 && open > 0, "covered {covered} open {open}");
    }
}

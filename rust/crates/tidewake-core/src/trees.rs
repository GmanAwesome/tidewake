//! Huge trees from `grand.py`: 18–34 layers, drawn across chunk edges.
//!
//! A jittered grid drops a tree on about 30% of cells when the column is
//! broad land of a wooded biome. Oaks, cones, willows, acacias and toadstools.

use std::collections::HashMap;

use crate::chunk::Chunk;
use crate::columns::Generator;
use crate::config::{CHUNK, HEX, LAYERS, SQ3};
use crate::hex::{self, cell_at, center, hex_distance};
use crate::materials::id;
use crate::noise::hash_ints;
use crate::pyrandom::PyRng;

const TREE_GRID: i64 = 34;
const TREE_CHANCE: f64 = 0.30;

struct Species {
    wood: u8,
    leaf: u8,
    form: &'static str,
}

fn species(realm: i64) -> Option<Species> {
    let (w, l, f) = match realm {
        0 => (id::HEARTWOOD, id::CANOPY, "oak"),
        1 => (id::DARK_HEARTWOOD, id::CANOPY, "oak"),
        2 => (id::HEARTWOOD, id::CANOPY, "oak"),
        3 => (id::PALE_HEARTWOOD, id::FROST_CANOPY, "cone"),
        4 => (id::HEARTWOOD, id::CANOPY, "oak"),
        5 => (id::DARK_HEARTWOOD, id::CANOPY, "willow"),
        7 => (id::PALE_HEARTWOOD, id::CANOPY, "toadstool"),
        8 => (id::PALE_HEARTWOOD, id::CANOPY, "oak"),
        9 => (id::CEDAR_HEARTWOOD, id::CANOPY, "cone"),
        10 => (id::DARK_HEARTWOOD, id::VIOLET_CANOPY, "oak"),
        13 => (id::DARK_HEARTWOOD, id::VIOLET_CANOPY, "oak"),
        14 => (id::PALE_HEARTWOOD, id::CANOPY, "cone"),
        15 => (id::DARK_HEARTWOOD, id::CANOPY, "willow"),
        16 => (id::PALE_HEARTWOOD, id::BLOSSOM_CANOPY, "oak"),
        17 => (id::DARK_HEARTWOOD, id::AUTUMN_CANOPY, "oak"),
        18 => (id::PALE_HEARTWOOD, id::FROST_CANOPY, "cone"),
        19 => (id::HEARTWOOD, id::GOLDEN_CANOPY, "acacia"),
        _ => return None,
    };
    Some(Species { wood: w, leaf: l, form: f })
}

struct Canvas {
    cells: HashMap<(i64, i64, i32), u8>,
}

impl Canvas {
    fn put(&mut self, q: i64, r: i64, y: i32, mat: u8) {
        if (1..LAYERS - 2).contains(&y) {
            self.cells.insert((q, r, y), mat);
        }
    }

    fn col(&mut self, q: i64, r: i64, y0: i32, y1: i32, mat: u8) {
        for y in y0..=y1 {
            self.put(q, r, y, mat);
        }
    }

    fn disk(&mut self, q: i64, r: i64, y: i32, rad: i32, mat: u8) {
        let rad = rad.max(0);
        for dq in -rad..=rad {
            for dr in -rad..=rad {
                if hex_distance(0, 0, dq as i64, dr as i64) <= rad as i64 {
                    self.put(q + dq as i64, r + dr as i64, y, mat);
                }
            }
        }
    }

    fn round_cells(&self, q: i64, r: i64, rad: f64) -> Vec<(i64, i64, f64)> {
        let (x0, z0) = center(q, r);
        let n = rad as i32 + 2;
        let mut out = Vec::new();
        for dq in -n..=n {
            for dr in -n..=n {
                let (x, z) = center(q + dq as i64, r + dr as i64);
                let d = ((x - x0).hypot(z - z0)) / (HEX * SQ3);
                if d <= rad + 0.01 {
                    out.push((q + dq as i64, r + dr as i64, d));
                }
            }
        }
        out
    }

    fn line3(&mut self, q0: i64, r0: i64, y0: i32, q1: i64, r1: i64, y1: i32, mat: u8) {
        let (x0, z0) = center(q0, r0);
        let (x1, z1) = center(q1, r1);
        let n = ((hex_distance(q0, r0, q1, r1) as f64).abs().max((y1 - y0).abs() as f64 * crate::config::LAYER / SQ3) * 1.5) as i32 + 1;
        let n = n.max(1);
        for i in 0..=n {
            let t = i as f64 / n as f64;
            let x = x0 + (x1 - x0) * t;
            let z = z0 + (z1 - z0) * t;
            let y = (y0 as f64 + (y1 - y0) as f64 * t).round() as i32;
            let (a, b) = cell_at(x, z);
            self.put(a, b, y, mat);
        }
    }
}

#[derive(Clone)]
pub struct HugeTree {
    pub q: i64,
    pub r: i64,
    pub top: i32,
    pub height: i32,
    pub form: &'static str,
    cells: HashMap<(i64, i64, i32), u8>,
}

pub fn tree_at(gen: &Generator, gi: i64, gj: i64) -> Option<HugeTree> {
    let mut rng = PyRng::seed_u64(hash_ints(gen.h, &[gi, gj, 0x71EE]));
    if rng.random() >= TREE_CHANCE {
        return None;
    }
    let q = gi * TREE_GRID + rng.randint(6, (TREE_GRID as i32) - 6) as i64;
    let r = gj * TREE_GRID + rng.randint(6, (TREE_GRID as i32) - 6) as i64;
    let c = gen.sample(q, r);
    let realm = c.realm as i64;
    if !(c.land && !c.skerry && !c.pool && !c.fall && c.e > 0.12) {
        return None;
    }
    let spec = species(realm)?;
    Some(build(&mut rng, q, r, c.top, spec))
}

fn build(rng: &mut PyRng, q: i64, r: i64, top: i32, spec: Species) -> HugeTree {
    let mut cv = Canvas { cells: HashMap::new() };
    let h = rng.randint(18, 34);
    let tr = if h < 26 { 1 } else { 2 };
    for y in top + 1..top + h {
        let rad = if y < top + h - 6 { tr } else { (tr - 1).max(0) };
        cv.disk(q, r, y, rad, spec.wood);
    }
    for (d, (dq, dr)) in hex::DIRS.iter().enumerate() {
        cv.col(
            q + *dq as i64 * (tr as i64 + 1),
            r + *dr as i64 * (tr as i64 + 1),
            top + 1,
            top + 2 + (d % 2) as i32,
            spec.wood,
        );
    }
    let ty = top + h;
    match spec.form {
        "cone" => {
            let span = (h - 2).max(1);
            for (i, y) in (top + 6..ty + 4).enumerate() {
                let rad = (6 - i as i32 * 6 / span).max(0);
                cv.disk(q, r, y, rad, spec.leaf);
            }
        }
        "toadstool" => {
            for k in 0..4 {
                let rad = if k == 0 { 7 } else { 7 - k * 2 };
                cv.disk(q, r, ty + k, rad, spec.leaf);
            }
            for (i, (dq, dr)) in hex::DIRS.iter().enumerate() {
                if i % 3 == 0 {
                    cv.put(q + *dq as i64 * 6, r + *dr as i64 * 6, ty - 1, id::GLOWCAP);
                }
            }
        }
        "acacia" => {
            for (i, (dq, dr)) in hex::DIRS.iter().enumerate() {
                if i % 2 != 0 {
                    continue;
                }
                cv.line3(q, r, ty - 4, q + *dq as i64 * 4, r + *dr as i64 * 4, ty, spec.wood);
                cv.disk(q + *dq as i64 * 4, r + *dr as i64 * 4, ty + 1, 3, spec.leaf);
            }
            cv.disk(q, r, ty + 2, 4, spec.leaf);
        }
        form => {
            let radius = 5.0 + rng.random() * 3.0;
            for (a, b, d) in cv.round_cells(q, r, radius) {
                let hh = ((radius * radius - d * d).max(0.0).sqrt() * 0.9) as i32;
                for y in (ty - hh / 2 - 1)..(ty + hh + 1) {
                    cv.put(a, b, y, spec.leaf);
                }
            }
            for (dq, dr) in hex::DIRS {
                cv.line3(q, r, ty - 6, q + dq as i64 * 4, r + dr as i64 * 4, ty - 2, spec.wood);
            }
            if form == "willow" {
                for (a, b, d) in cv.round_cells(q, r, radius) {
                    if d > radius - 1.2 && (a + b) % 2 == 0 {
                        cv.col(a, b, ty - 7, ty - 1, id::VINE);
                    }
                }
            }
        }
    }
    HugeTree { q, r, top, height: h, form: spec.form, cells: cv.cells }
}

pub fn stamp(gen: &Generator, chunk: &mut Chunk) {
    let q0 = chunk.cq as i64 * CHUNK as i64;
    let r0 = chunk.cr as i64 * CHUNK as i64;
    let gi0 = (q0 - 12).div_euclid(TREE_GRID);
    let gi1 = (q0 + CHUNK as i64 + 12).div_euclid(TREE_GRID);
    let gj0 = (r0 - 12).div_euclid(TREE_GRID);
    let gj1 = (r0 + CHUNK as i64 + 12).div_euclid(TREE_GRID);
    for gi in gi0..=gi1 {
        for gj in gj0..=gj1 {
            let Some(tree) = tree_at(gen, gi, gj) else { continue };
            for ((q, r, y), mat) in &tree.cells {
                let lq = (*q - q0) as i32;
                let lr = (*r - r0) as i32;
                if (0..CHUNK).contains(&lq) && (0..CHUNK).contains(&lr) && chunk.get(lq, *y, lr) == 0 {
                    chunk.set(lq, *y, lr, *mat);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::settings::Settings;
    use std::collections::HashSet;

    #[test]
    fn huge_trees_are_tall_and_varied() {
        let g = Generator::new(7, Settings::default());
        let mut heights = Vec::new();
        let mut forms = HashSet::new();
        for gi in -10..10 {
            for gj in -10..10 {
                if let Some(t) = tree_at(&g, gi, gj) {
                    heights.push(t.height);
                    forms.insert(t.form);
                }
            }
        }
        assert!(heights.len() >= 4, "found {}", heights.len());
        assert!(heights.iter().all(|h| (18..=34).contains(h)));
        assert!(forms.len() >= 2, "{forms:?}");
    }
}

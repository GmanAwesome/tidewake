//! Lesson-island showpieces from `tutorial_builds.py`.
//!
//! Placements, radii and materials follow that file. Cells on the lesson path
//! and at the stations are reserved from the surface through four layers up,
//! the same window `Plan.put` keeps clear.

use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

use crate::config::{CHUNK, HEX, SQ3};
use crate::hex::{hex_distance, hex_line, ring, DIRS};
use crate::lesson::in_land;
use crate::materials::id_named;

pub const SURF: i32 = 48;

const HUES: [&str; 16] = [
    "rose", "ember", "honey", "leaf", "moss", "tide", "sky", "indigo", "violet", "orchid", "blush",
    "cocoa", "snow", "pearl", "ash", "ink",
];

fn m(name: &str) -> u8 {
    id_named(name).unwrap_or(1)
}

fn hue(i: usize, family: &str) -> u8 {
    m(&format!("{}_{family}", HUES[i % 16]))
}

fn py_round(x: f64) -> i32 {
    let f = x.floor();
    let frac = x - f;
    if (frac - 0.5).abs() < 1e-9 {
        let i = f as i64;
        if i % 2 == 0 { i as i32 } else { i as i32 + 1 }
    } else {
        x.round() as i32
    }
}

struct Plan {
    cells: HashMap<(i64, i64, i32), u8>,
    reserved: HashSet<(i64, i64)>,
}

impl Plan {
    fn put(&mut self, q: i64, r: i64, y: i32, mat: u8) {
        if !(0..500).contains(&y) {
            return;
        }
        if self.reserved.contains(&(q, r)) && (SURF..=SURF + 4).contains(&y) {
            return;
        }
        self.cells.insert((q, r, y), mat);
    }

    fn col(&mut self, q: i64, r: i64, y0: i32, y1: i32, mat: u8) {
        for y in y0..=y1 {
            self.put(q, r, y, mat);
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

    fn ring(&mut self, q: i64, r: i64, y: i32, rad: i64, mat: u8) {
        for (a, b) in ring(q, r, rad) {
            self.put(a, b, y, mat);
        }
    }

    fn round_cells(&self, q: i64, r: i64, rad: f64) -> Vec<(i64, i64, f64, f64)> {
        let (x0, z0) = crate::hex::center(q, r);
        let n = rad as i64 + 2;
        let mut out = Vec::new();
        for dq in -n..=n {
            for dr in -n..=n {
                let (x, z) = crate::hex::center(q + dq, r + dr);
                let d = ((x - x0).hypot(z - z0)) / (HEX * SQ3);
                if d <= rad + 0.01 {
                    out.push((q + dq, r + dr, d, (z - z0).atan2(x - x0)));
                }
            }
        }
        out
    }
}

fn rainbow_plaza(p: &mut Plan, q: i64, r: i64) {
    for (a, b, d, ang) in p.round_cells(q, r, 11.5) {
        let sector = ((((ang + std::f64::consts::PI) / std::f64::consts::TAU) * 16.0) as i64).rem_euclid(16) as usize;
        let mat = if d > 10.5 {
            m("ink_terrazzo")
        } else if d > 9.5 {
            m("pearl_patterned_tile")
        } else if d < 3.6 {
            m("snow_terrazzo")
        } else {
            hue(sector, "terrazzo")
        };
        p.put(a, b, SURF, mat);
        for y in SURF + 1..SURF + 6 {
            p.put(a, b, y, 0);
        }
    }
    let rim = ring(q, r, 10);
    let step = (rim.len() / 16).max(1);
    for (i, (a, b)) in rim.iter().step_by(step).take(16).enumerate() {
        p.col(*a, *b, SURF + 1, SURF + 3, m("pewter"));
        p.put(*a, *b, SURF + 4, hue(i, "crystal_lamp"));
        p.put(*a, *b, SURF + 5, hue(i, "banner"));
    }
    cosmic_clocktower(p, q, r);
}

fn cosmic_clocktower(p: &mut Plan, q: i64, r: i64) {
    let bands = [
        "ochre_bricks", "brass", "ink_bricks", "copper", "rose_checker", "wrought_iron", "sky_stripe",
        "pewter", "ink_checker", "rose_stripe", "brass", "ochre_bricks",
    ];
    let h = 34;
    for i in 0..h {
        let mat = m(bands[(i / 3) % bands.len()]);
        let y = SURF + 1 + i as i32;
        p.ring(q, r, y, 3, mat);
        p.ring(q, r, y, 2, mat);
        for (a, b) in ring(q, r, 1) {
            p.put(a, b, y, 0);
        }
        p.put(q, r, y, 0);
        if i == 8 || i == 17 || i == 26 {
            p.ring(q, r, y, 4, m("wrought_iron"));
            if i == 26 {
                p.ring(q, r, y + 1, 4, m("pale_lattice"));
            }
        }
    }
    for i in 0..h {
        p.put(q, r, SURF + 1 + i as i32, m("ladder"));
    }
    for (a, b) in [(q + 3, r), (q + 2, r)] {
        p.put(a, b, SURF + 1, 0);
        p.put(a, b, SURF + 2, 0);
    }
    for (d, (dq, dr)) in DIRS.iter().enumerate() {
        let (fq, fr) = (q + *dq as i64 * 3, r + *dr as i64 * 3);
        p.put(fq, fr, SURF + 22, m("snow_patterned_tile"));
        p.put(fq, fr, SURF + 23, if d % 2 == 0 { m("honey_crystal_lamp") } else { m("snow_patterned_tile") });
        p.put(fq, fr, SURF + 24, m("snow_patterned_tile"));
    }
    for (i, name) in ["violet_glass", "amber_glass", "green_glass", "glass"].iter().enumerate() {
        p.ring(q, r, SURF + 35 + i as i32, 3, m(name));
    }
    p.disk(q, r, SURF + 39, 3, m("brass"));
    p.disk(q, r, SURF + 40, 2, m("shimmer_cloud"));
    p.disk(q, r, SURF + 41, 1, m("shimmer_cloud"));
    p.put(q, r, SURF + 42, m("copper"));
    p.put(q, r, SURF + 43, m("cosmic_star"));
    p.put(q, r, SURF + 36, m("lumen_lamp"));
}

fn bazaar(p: &mut Plan, q: i64, r: i64) {
    let spots = ring(q, r, 14);
    let step = spots.len() as f64 / 16.0;
    for i in 0..16 {
        let (a, b) = spots[(i as f64 * step) as usize];
        let post = if i % 2 == 0 { m("cedar_planks") } else { m("dark_planks") };
        for (dq, dr) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
            p.col(a + dq, b + dr, SURF + 1, SURF + 3, post);
        }
        p.disk(a, b, SURF, 1, hue(i, "patterned_tile"));
        p.disk(a, b, SURF + 4, 1, hue(i, "woven_panel"));
        p.put(a, b, SURF + 5, hue(i, "woven_panel"));
        p.put(a, b, SURF + 1, hue(i, "stained_glass"));
        p.put(a + 1, b - 1, SURF + 1, hue(i, "banner"));
    }
    let cloths = ["linen", "crimson_cloth", "dusk_cloth", "heather"];
    for (i, (a, b)) in ring(q, r, 16).iter().step_by(6).enumerate() {
        p.put(*a, *b, SURF + 1, m("wattle"));
        p.put(*a, *b, SURF + 2, m(cloths[i % 4]));
    }
}

fn hall_of_stones(p: &mut Plan, q: i64, r: i64) {
    let stones = [
        "stone", "cobble", "slate", "chalk", "sandstone", "cinder", "salt_block", "pale_stone", "basalt",
        "rosestone", "clay", "packed_earth", "mossy_bricks", "carved_stone", "mosaic", "polished_stone",
        "polished_basalt", "polished_rosestone", "polished_slate", "polished_chalk", "polished_sandstone",
        "polished_pale_stone", "stone_bricks", "basalt_bricks", "rosestone_bricks", "slate_bricks",
        "sandstone_bricks", "chalk_bricks", "cinder_bricks", "snow_bricks", "dusk_bricks", "lavender_bricks",
        "verdigris_bricks", "bricks", "stone_tiles", "basalt_tiles", "rosestone_tiles", "slate_tiles",
        "sandstone_tiles", "chalk_tiles", "clay_tiles", "verdigris_tiles", "lavender_tiles", "starstone",
        "polished_starstone", "starstone_tiles",
    ];
    let mut y = SURF + 1;
    let mut k = 0;
    for t in 0..8 {
        let rad = 9 - t;
        for _ in 0..3 {
            p.disk(q, r, y, rad, m(stones[k % stones.len()]));
            k += 1;
            y += 1;
        }
    }
    let ores = ["emberite_ore", "verdigris_ore", "silverine_ore", "aetherite_ore"];
    for t in 0..8 {
        let rad = 9 - t;
        for (d, (dq, dr)) in DIRS.iter().enumerate() {
            p.put(q + *dq as i64 * rad, r + *dr as i64 * rad, SURF + 2 + t as i32 * 3, m(ores[(d + t as usize) % 4]));
        }
    }
    let slabs = [
        "stone_slab", "cobble_slab", "planks_slab", "cedar_planks_slab", "pale_planks_slab", "dark_planks_slab",
        "bricks_slab", "stone_bricks_slab", "sandstone_slab", "slate_slab", "thatch_slab", "shingles_slab",
        "polished_stone_slab",
    ];
    for t in 0..9 {
        let sq = q + 10 - t;
        p.put(sq, r, SURF + t as i32 * 3, m("polished_stone"));
        p.put(sq, r, SURF + t as i32 * 3 + 1, m(slabs[t as usize % slabs.len()]));
        p.put(sq, r - 1, SURF + t as i32 * 3 + 1, m(slabs[(t as usize + 6) % slabs.len()]));
        for yy in SURF + t as i32 * 3 + 2..SURF + t as i32 * 3 + 5 {
            p.put(sq, r, yy, 0);
            p.put(sq, r - 1, yy, 0);
        }
    }
    let top = SURF + 1 + 8 * 3;
    p.disk(q, r, top, 1, m("starstone_tiles"));
    let lamps = ["ember_lamp", "aether_lamp", "verdigris_lamp", "lumen_lamp", "kiln", "starstone"];
    for ((dq, dr), lamp) in DIRS.iter().zip(lamps) {
        p.put(q + *dq as i64, r + *dr as i64, top + 1, m(lamp));
    }
    p.put(q, r, top + 1, m("plinth"));
    p.put(q, r, top + 2, m("lumen_shard"));
}

fn conservatory(p: &mut Plan, q: i64, r: i64) {
    let radius = 9.0;
    let plain = [m("glass"), m("green_glass"), m("amber_glass"), m("violet_glass")];
    let cells = p.round_cells(q, r, radius);
    for (a, b, d, _) in &cells {
        let floor = if *d > radius - 1.2 { m("leaf_terrazzo") } else { m("turf") };
        p.put(*a, *b, SURF, floor);
        for y in SURF + 1..SURF + 12 {
            p.put(*a, *b, y, 0);
        }
    }
    for (a, b, d, ang) in &cells {
        let hgt = (radius * radius - d * d).max(0.0).sqrt() * 1.15;
        let nxt = if d + 1.0 < radius { (radius * radius - (d + 1.0).powi(2)).max(0.0).sqrt() * 1.15 } else { 0.0 };
        let y_top = SURF + py_round(hgt);
        let y_bot = SURF + 1 + py_round(nxt);
        let sector = ((((ang + std::f64::consts::PI) / std::f64::consts::TAU) * 16.0) as i64).rem_euclid(16) as usize;
        for y in y_bot..=y_top {
            let lat = y - SURF;
            let mat = if sector % 4 == 0 {
                if lat % 2 == 0 { m("wood_lattice") } else { m("pale_lattice") }
            } else if lat > 8 {
                plain[(sector + lat as usize) % 4]
            } else {
                hue((sector + (lat / 3) as usize) % 16, "stained_glass")
            };
            p.put(*a, *b, y, mat);
        }
    }
    for d in [0, 2, 3, 5] {
        let (dq, dr) = DIRS[d];
        for k in 8..11 {
            for y in SURF + 1..SURF + 4 {
                p.put(q + dq as i64 * k, r + dr as i64 * k, y, 0);
            }
        }
    }
    let beds = [
        ("bloom", "turf"), ("vine", "mossrock"), ("sprout", "loam"), ("glowcap", "mossrock"), ("petals", "turf"),
        ("berry_bush", "turf"), ("grass", "turf"), ("wildflower", "turf"), ("mushroom", "loam"), ("pebble", "sand"),
        ("shrub", "turf"), ("reeds", "sand"), ("crystal", "snow"), ("lumen_shard", "ice"), ("skywheat", "farmland"),
        ("sweetroot_crop", "farmland"), ("berry_crop", "farmland"),
    ];
    for (a, b, d, ang) in cells.iter().filter(|c| c.2 > 2.5 && c.2 < radius - 2.0) {
        let idx = ((ang + std::f64::consts::PI) * 4.0) as i64 + *d as i64;
        let (plant, ground) = beds[idx.rem_euclid(beds.len() as i64) as usize];
        p.put(*a, *b, SURF, m(ground));
        p.put(*a, *b, SURF + 1, m(plant));
    }
    for (a, b, d, _) in &cells {
        if *d < 2.2 {
            p.put(*a, *b, SURF - 1, m("stone"));
            p.put(*a, *b, SURF, m("water"));
        }
    }
    p.col(q, r, SURF, SURF + 3, m("polished_chalk"));
    p.put(q, r, SURF + 4, m("lumen_lamp"));
    p.put(q, r, SURF + 5, m("glass"));
}

fn mossback_monument(p: &mut Plan, q: i64, r: i64) {
    for (a, b, d, _) in p.round_cells(q, r, 6.2) {
        let h = py_round((6.2_f64.powi(2) - d * d).max(0.0).sqrt() * 0.9);
        for y in SURF + 2..SURF + 2 + h {
            let mat = if (d as i32 + y) % 3 == 0 { m("leaf_patterned_tile") } else { m("moss_terrazzo") };
            p.put(a, b, y, mat);
        }
        p.put(a, b, SURF + 2 + h, if d > 2.0 { m("moss_patterned_tile") } else { m("turf") });
        if d < 4.5 && (a * 7 + b * 3) % 3 == 0 {
            p.put(a, b, SURF + 3 + h, if (a + b) % 2 == 0 { m("bloom") } else { m("shrub") });
        }
    }
    for (dq, dr) in [(4, -2), (-4, 2), (2, 3), (-2, -3)] {
        p.col(q + dq, r + dr, SURF + 1, SURF + 2, m("sage_plaster"));
    }
    let (hq, hr) = (q + 8, r - 1);
    for y in SURF + 2..SURF + 6 {
        p.disk(hq - 1, hr, y, if y < SURF + 5 { 1 } else { 0 }, m("sage_plaster"));
    }
    p.disk(hq, hr, SURF + 5, 1, m("sage_plaster"));
    p.put(hq + 1, hr, SURF + 5, m("sage_plaster"));
    p.put(hq + 1, hr - 1, SURF + 6, m("ink_terrazzo"));
    p.put(hq, hr + 1, SURF + 6, m("ink_terrazzo"));
    p.put(q - 7, r + 1, SURF + 2, m("sage_plaster"));
    p.put(q - 8, r + 1, SURF + 2, m("sage_plaster"));
    p.disk(q, r, SURF, 7, m("packed_earth"));
    p.put(q, r, SURF + 9, m("leaf_crystal_lamp"));
}

fn sky_funfair(p: &mut Plan, q: i64, r: i64, y: i32) {
    let pads = [
        (q, r, 4_i64, "shimmer_cloud", 0),
        (q - 10, r + 6, 4, "cloudstuff", 2),
        (q + 8, r + 8, 3, "fluff_block", -1),
        (q - 4, r + 14, 3, "shimmer_cloud", 4),
    ];
    let jellies = ["rose_jelly", "honey_jelly", "tide_jelly", "violet_jelly"];
    for (i, (a, b, rad, mat, dy)) in pads.iter().enumerate() {
        let yy = y + dy;
        let mat = m(mat);
        p.disk(*a, *b, yy, *rad, mat);
        p.disk(*a, *b, yy - 1, rad - 1, mat);
        p.disk(*a, *b, yy - 2, (rad - 2).max(0), mat);
        p.put(*a, *b, yy, m(jellies[i]));
        for (dq, dr) in DIRS.iter().step_by(2) {
            p.put(a + *dq as i64 * rad, b + *dr as i64 * rad, yy + 1, m("pale_lattice"));
        }
    }
    let links = [(0, 1), (0, 2), (1, 3)];
    for (i0, i1) in links {
        let (a0, b0, _, _, y0) = pads[i0];
        let (a1, b1, _, _, y1) = pads[i1];
        let pts = hex_line(a0, b0, a1, b1);
        let n = pts.len().max(1) - 1;
        for (k, (a, b)) in pts.iter().enumerate() {
            let yy = y + y0 + py_round((y1 - y0) as f64 * k as f64 / n.max(1) as f64);
            if p.cells.get(&(*a, *b, yy)).copied().unwrap_or(0) == 0 {
                p.put(*a, *b, yy, m("pale_planks"));
            }
            p.put(*a, *b, yy + 1, 0);
        }
    }
    let (gq, gr, gy) = (q - 4, r + 14, y + 5);
    for (dq, dr) in DIRS.iter().step_by(2) {
        p.col(gq + *dq as i64 * 2, gr + *dr as i64 * 2, gy, gy + 3, m("ivory_plaster"));
    }
    p.disk(gq, gr, gy + 4, 2, m("indigo_terrazzo"));
    p.disk(gq, gr, gy + 5, 1, m("indigo_patterned_tile"));
    p.put(gq, gr, gy + 6, m("cosmic_star"));
    p.put(gq, gr, gy, m("bedroll"));
}

fn bounce_park(p: &mut Plan, q: i64, r: i64) {
    let jellies = ["rose_jelly", "tide_jelly", "honey_jelly", "violet_jelly"];
    for (i, (dq, dr)) in [(0, 0), (3, -1), (-3, 1), (1, 3), (-1, -3), (4, 2), (-4, -2)].iter().enumerate() {
        p.disk(q + dq, r + dr, SURF, 1, m(jellies[i % 4]));
    }
    for (a, b) in ring(q, r, 6) {
        p.put(a, b, SURF, if (a + b) % 2 == 0 { m("ink_checker") } else { m("rose_checker") });
    }
    for (a, b) in ring(q, r, 7) {
        p.put(a, b, SURF + 1, if (a - b) % 3 == 0 { m("rose_stripe") } else { m("sky_stripe") });
    }
    let (tq, tr) = (q + 6, r - 6);
    for y in SURF + 1..SURF + 18 {
        p.ring(tq, tr, y, 1, if y % 4 == 0 { m("rose_stripe") } else { m("pale_planks") });
        p.put(tq, tr, y, m("ladder"));
    }
    p.put(tq - 1, tr + 1, SURF + 1, 0);
    p.put(tq - 1, tr + 1, SURF + 2, 0);
    sky_funfair(p, tq, tr, SURF + 17);
}

fn observatory(p: &mut Plan, q: i64, r: i64) {
    for y in SURF + 1..SURF + 18 {
        let mat = if y % 5 == 0 { m("dusk_bricks") } else { m("lavender_bricks") };
        p.ring(q, r, y, 3, mat);
        p.ring(q, r, y, 2, mat);
        for (a, b) in ring(q, r, 1) {
            p.put(a, b, y, 0);
        }
        p.put(q, r, y, m("ladder"));
    }
    for (a, b) in [(q + 3, r), (q + 2, r)] {
        p.put(a, b, SURF + 1, 0);
        p.put(a, b, SURF + 2, 0);
    }
    p.disk(q, r, SURF + 18, 4, m("polished_starstone"));
    p.ring(q, r, SURF + 19, 4, m("verdigris_bricks"));
    for i in 0..4 {
        let mat = if i % 2 == 0 { m("verdigris_tiles") } else { m("starstone_tiles") };
        p.disk(q, r, SURF + 20 + i, 3 - i as i64, mat);
    }
    for k in 0..6 {
        p.put(q + 1 + k / 2, r - 1, SURF + 19 + k as i32, if k < 5 { m("brass") } else { m("copper") });
    }
    p.put(q - 3, r + 1, SURF + 19, m("aether_lamp"));
    p.disk(q, r, SURF, 5, m("slate_tiles"));
}

fn treehouse_grove(p: &mut Plan, q: i64, r: i64) {
    let woods = [
        ("heartwood", "planks", "thatch"),
        ("cedar_heartwood", "cedar_planks", "shingles"),
        ("pale_heartwood", "pale_planks", "thatch"),
        ("dark_heartwood", "dark_planks", "shingles"),
    ];
    let spots = [(q - 5, r - 2), (q + 5, r - 3), (q + 4, r + 5), (q - 5, r + 6)];
    let deck_y = SURF + 9;
    for ((a, b), (log, plank, roof)) in spots.iter().zip(woods) {
        for y in SURF + 1..SURF + 18 {
            p.disk(*a, *b, y, if y < SURF + 14 { 1 } else { 0 }, m(log));
        }
        for y in SURF + 14..SURF + 21 {
            p.disk(*a, *b, y, if y < SURF + 19 { 4 } else { 2 }, m("canopy"));
        }
        for (a2, b2) in ring(*a, *b, 1) {
            p.put(a2, b2, SURF + 14, m(log));
        }
        p.put(*a, *b, SURF + 14, m(log));
        p.disk(*a, *b, deck_y, 3, m(plank));
        p.ring(*a, *b, deck_y + 1, 3, m("wood_lattice"));
        p.ring(*a, *b, deck_y + 1, 2, 0);
        let (hq, hr) = (*a + 2, *b - 1);
        p.ring(hq, hr, deck_y + 1, 1, m(plank));
        p.ring(hq, hr, deck_y + 2, 1, m(plank));
        p.disk(hq, hr, deck_y + 3, 1, m(roof));
        let slab = format!("{roof}_slab");
        p.put(hq, hr, deck_y + 4, if id_named(&slab).is_some() { m(&slab) } else { m(roof) });
        p.put(hq, hr, deck_y + 1, m("bedroll"));
        p.put(hq + 1, hr, deck_y + 1, 0);
        p.put(hq + 1, hr, deck_y + 2, 0);
        p.put(*a - 1, *b + 1, deck_y + 2, m("lantern"));
        for y in SURF + 1..=deck_y {
            p.put(*a - 2, *b, y, m("ladder"));
        }
        p.put(*a - 2, *b, deck_y + 1, 0);
    }
    for i in 0..4 {
        let (a0, b0) = spots[i];
        let (a1, b1) = spots[(i + 1) % 4];
        let pts = hex_line(a0, b0, a1, b1);
        if pts.len() > 4 {
            for (a, b) in &pts[2..pts.len() - 2] {
                p.put(*a, *b, deck_y, m("planks"));
                p.put(*a, *b, deck_y + 1, 0);
            }
        }
    }
    p.put(q, r, SURF + 1, m("tinker_bench"));
    p.put(q + 1, r, SURF + 1, m("cedar_planks"));
}

fn frost_folly(p: &mut Plan, q: i64, r: i64) {
    for (a, b, _, _) in p.round_cells(q, r, 5.5) {
        p.put(a, b, SURF, m("snow"));
    }
    for (d, (dq, dr)) in DIRS.iter().enumerate() {
        let (a, b) = (q + *dq as i64 * 4, r + *dr as i64 * 4);
        let h = 5 + (d % 3) as i32 * 2;
        for y in SURF + 1..SURF + 1 + h {
            p.put(a, b, y, if y % 3 == 0 { m("snow_bricks") } else { m("ice") });
        }
        p.put(a, b, SURF + 1 + h, m("salt_block"));
    }
    p.disk(q, r, SURF + 1, 1, m("polished_chalk"));
    p.put(q, r, SURF + 2, m("chalk_bricks"));
    p.put(q, r, SURF + 3, m("snow_crystal_lamp"));
    p.put(q + 1, r + 1, SURF + 1, m("snow_banner"));
}

fn ember_forge(p: &mut Plan, q: i64, r: i64) {
    for (a, b, d, _) in p.round_cells(q, r, 5.0) {
        p.put(a, b, SURF, if d > 3.0 { m("cinder_bricks") } else { m("basalt_tiles") });
    }
    for (a, b) in ring(q, r, 4) {
        p.col(a, b, SURF + 1, SURF + 2, m("cinder"));
    }
    for (a, b) in ring(q, r, 4).iter().step_by(3) {
        p.col(*a, *b, SURF + 3, SURF + 5, m("polished_basalt"));
        p.put(*a, *b, SURF + 6, m("ember_crystal_lamp"));
    }
    p.disk(q, r, SURF + 6, 4, m("basalt_bricks"));
    p.disk(q, r, SURF + 7, 2, m("ember_patterned_tile"));
    p.put(q, r, SURF + 1, m("kiln"));
    p.put(q + 1, r, SURF + 1, m("emberite_ore"));
    for (a, b) in [(q + 4, r), (q + 3, r), (q + 4, r - 1)] {
        p.put(a, b, SURF + 1, 0);
        p.put(a, b, SURF + 2, 0);
    }
}

fn tidewell_sanctuary(p: &mut Plan, q: i64, r: i64) {
    for (d, (dq, dr)) in DIRS.iter().enumerate() {
        let (a, b) = (q + *dq as i64 * 5, r + *dr as i64 * 5);
        p.col(a, b, SURF + 1, SURF + 6, m("dusk_plaster"));
        p.put(a, b, SURF + 7, if d % 2 == 0 { m("dusk_plaster") } else { m("violet_crystal_lamp") });
    }
    for (a, b, d, ang) in p.round_cells(q, r, 5.6) {
        let sector = ((((ang + std::f64::consts::PI) / std::f64::consts::TAU) * 16.0) as i64).rem_euclid(16) as usize;
        let lift = py_round((5.6_f64.powi(2) - d * d).max(0.0).sqrt() * 0.5);
        p.put(a, b, SURF + 7 + lift, hue(sector, "stained_glass"));
    }
    p.put(q, r, SURF + 11, m("shimmer_cloud"));
    for (a, b) in ring(q, r, 6).iter().step_by(4) {
        p.put(*a, *b, SURF + 1, m("violet_banner"));
    }
}

fn knoll_crown(p: &mut Plan, q: i64, r: i64, top: i32) {
    for (a, b) in ring(q, r, 8).iter().step_by(6) {
        p.col(*a, *b, top + 1, top + 5, m("carved_stone"));
        p.put(*a, *b, top + 6, m("polished_pale_stone"));
        p.put(*a, *b, top + 7, m("crystal"));
    }
    for (a, b) in ring(q, r, 8) {
        p.put(a, b, top + 6, m("polished_pale_stone"));
    }
}

fn arch(p: &mut Plan, q0: i64, r0: i64, q1: i64, r1: i64, mat: u8, cap: u8, banner: u8) {
    for (a, b) in [(q0, r0), (q1, r1)] {
        p.col(a, b, SURF + 1, SURF + 7, mat);
    }
    for (a, b) in hex_line(q0, r0, q1, r1) {
        p.put(a, b, SURF + 8, cap);
        p.put(a, b, SURF + 9, mat);
    }
    let (mq, mr) = ((q0 + q1) / 2, (r0 + r1) / 2);
    p.put(mq, mr, SURF + 7, banner);
    p.put(mq, mr, SURF + 10, m("honey_crystal_lamp"));
}

fn windmill(p: &mut Plan, q: i64, r: i64) {
    p.disk(q, r, SURF, 6, m("packed_earth"));
    for y in SURF + 1..SURF + 20 {
        let rad = if y < SURF + 8 { 4 } else if y < SURF + 15 { 3 } else { 2 };
        p.ring(q, r, y, rad, if y % 6 == 0 { m("cedar_planks") } else { m("ivory_plaster") });
        for k in 0..rad {
            for (a, b) in ring(q, r, k) {
                p.put(a, b, y, 0);
            }
        }
    }
    p.put(q + 4, r, SURF + 1, 0);
    p.put(q + 4, r, SURF + 2, 0);
    for y in SURF + 20..SURF + 24 {
        p.disk(q, r, y, (23 + SURF - y) as i64, m("shingles"));
    }
    let (hub_q, hub_r, hub_y) = (q, r - 3, SURF + 17);
    p.put(hub_q, hub_r, hub_y, m("brass"));
    for k in 1..12 {
        for (dq, dy) in [(k, 0), (-k, 0), (0, k), (0, -k)] {
            let yy = if dy == 0 { hub_y } else { hub_y + dy * 2 };
            p.put(hub_q + dq as i64, hub_r - 1, yy, m("dark_planks"));
            if k > 3 {
                let cloth = if (k / 2) % 2 == 0 { m("linen") } else { m("crimson_cloth") };
                if dy == 0 {
                    p.put(hub_q + dq as i64, hub_r - 1, hub_y + if dq > 0 { 1 } else { -1 }, cloth);
                } else {
                    p.put(hub_q + if dy > 0 { -1 } else { 1 }, hub_r - 1, hub_y + dy * 2, cloth);
                }
            }
        }
    }
    for (a, b) in ring(q, r, 6).iter().step_by(2) {
        p.put(*a, *b, SURF + 1, m("wattle"));
    }
    for (a, b) in ring(q, r, 5).iter().step_by(5) {
        p.put(*a, *b, SURF + 1, m("skywheat"));
    }
}

fn hedge_maze(p: &mut Plan, q: i64, r: i64) {
    let radius = 9.0;
    for (a, b, d, _) in p.round_cells(q, r, radius + 0.5) {
        p.put(a, b, SURF, if d > 1.5 { m("packed_earth") } else { m("polished_chalk") });
    }
    for ring_r in [3.0, 5.0, 7.0, 9.0] {
        let gap = ((ring_r as i32 * 37) % 360) as f64;
        for (a, b, d, ang) in p.round_cells(q, r, ring_r + 0.5) {
            if d < ring_r - 0.5 {
                continue;
            }
            let deg = (ang.to_degrees() + 360.0) % 360.0;
            let delta = ((deg - gap + 180.0) % 360.0) - 180.0;
            if delta.abs() < 14.0 {
                continue;
            }
            p.put(a, b, SURF + 1, m("canopy"));
            p.put(a, b, SURF + 2, m("canopy"));
            if (a + b) % 7 == 0 {
                p.put(a, b, SURF + 3, m("bloom"));
            }
        }
    }
    p.put(q, r, SURF + 1, m("carved_stone"));
    p.put(q, r, SURF + 2, m("plinth"));
    p.put(q, r, SURF + 3, m("cosmic_star"));
}

fn woolhop_statue(p: &mut Plan, q: i64, r: i64) {
    for (a, b, d, _) in p.round_cells(q, r, 6.5) {
        let h = py_round((6.5_f64.powi(2) - d * d).max(0.0).sqrt() * 1.6);
        for y in SURF + 3..SURF + 3 + h {
            p.put(a, b, y, if (a + b + y as i64) % 5 == 0 { m("cloudstuff") } else { m("fluff_block") });
        }
    }
    for (dq, dr) in [(3, -2), (-3, 2), (2, 2), (-2, -2)] {
        p.col(q + dq, r + dr, SURF + 1, SURF + 3, m("ash_terrazzo"));
    }
    let (hq, hr) = (q, r - 7);
    for y in SURF + 8..SURF + 13 {
        p.disk(hq, hr, y, 2, m("ink_terrazzo"));
    }
    p.put(hq - 1, hr - 2, SURF + 11, m("snow_terrazzo"));
    p.put(hq + 1, hr - 2, SURF + 11, m("snow_terrazzo"));
    p.col(hq - 2, hr, SURF + 13, SURF + 15, m("ink_terrazzo"));
    p.col(hq + 2, hr, SURF + 13, SURF + 15, m("ink_terrazzo"));
    p.disk(q, r, SURF, 7, m("moss_terrazzo"));
}

fn sky_castle(p: &mut Plan, q: i64, r: i64, y: i32) {
    for (k, rad) in [11_i64, 10, 8, 6, 3].iter().enumerate() {
        let mat = if k == 0 { m("shimmer_cloud") } else { m("cloudstuff") };
        p.disk(q, r, y - k as i32, *rad, mat);
    }
    p.disk(q, r, y + 1, 9, m("stone_tiles"));
    for yy in y + 2..y + 8 {
        p.ring(q, r, yy, 8, m("stone_bricks"));
    }
    for (a, b) in ring(q, r, 8).iter().step_by(2) {
        p.put(*a, *b, y + 8, m("stone_bricks"));
    }
    for (dq, dr) in DIRS {
        let (tq, tr) = (q + dq as i64 * 8, r + dr as i64 * 8);
        for yy in y + 2..y + 14 {
            let mat = if yy % 4 == 0 { m("stone_bricks") } else { m("chalk_bricks") };
            p.disk(tq, tr, yy, 1, mat);
        }
        p.disk(tq, tr, y + 14, 2, m("indigo_patterned_tile"));
        p.disk(tq, tr, y + 15, 1, m("indigo_patterned_tile"));
        p.put(tq, tr, y + 16, m("sky_banner"));
    }
    for yy in y + 2..y + 22 {
        let mat = if yy % 5 == 0 { m("snow_bricks") } else { m("polished_chalk") };
        p.ring(q, r, yy, 3, mat);
        p.ring(q, r, yy, 2, mat);
    }
    for yy in (y + 10..y + 20).step_by(3) {
        for (dq, dr) in DIRS {
            p.put(q + dq as i64 * 3, r + dr as i64 * 3, yy, m("sky_stained_glass"));
        }
    }
    for k in 0..4 {
        p.disk(q, r, y + 22 + k, 3 - k as i64, m("sky_patterned_tile"));
    }
    p.put(q, r, y + 26, m("sky_crystal_lamp"));
}

fn meadow(p: &mut Plan) {
    let plants = [
        "grass", "grass", "wildflower", "petals", "bloom", "shrub", "mushroom", "pebble", "sprout", "berry_bush",
        "grass", "wildflower",
    ];
    let woods = ["heartwood", "pale_heartwood", "cedar_heartwood", "dark_heartwood"];
    for q in -50..81 {
        for r in -76..81 {
            if !in_land(q, r) || p.reserved.contains(&(q, r)) {
                continue;
            }
            if (SURF..SURF + 4).any(|y| p.cells.contains_key(&(q, r, y))) {
                continue;
            }
            let h = (q.wrapping_mul(73856093) ^ r.wrapping_mul(19349663)) & 0xFFFF;
            let avoid = r < 0 && crate::hex::center(q, r).0.abs() < 12.0;
            if h % 997 < 6 && !avoid {
                let clear = std::iter::once((0, 0)).chain(DIRS.iter().copied()).all(|(dq, dr)| {
                    let (qq, rr) = (q + dq as i64, r + dr as i64);
                    !p.reserved.contains(&(qq, rr))
                        && !(SURF..SURF + 10).any(|y| p.cells.contains_key(&(qq, rr, y)))
                });
                if clear {
                    let hh = 6 + (h % 4) as i32;
                    p.col(q, r, SURF + 1, SURF + hh, m(woods[(h % 4) as usize]));
                    for (dq, dr) in std::iter::once((0, 0)).chain(DIRS.iter().copied()) {
                        for y in SURF + hh - 1..SURF + hh + 2 {
                            if !(dq == 0 && dr == 0 && y <= SURF + hh) {
                                p.put(q + dq as i64, r + dr as i64, y, m("canopy"));
                            }
                        }
                    }
                    continue;
                }
            }
            if h % 100 < 9 {
                p.put(q, r, SURF + 1, m(plants[((h >> 4) as usize) % plants.len()]));
            }
        }
    }
}

fn block_gallery(p: &mut Plan, q: i64, r: i64) {
    let used: HashSet<u8> = p.cells.values().copied().collect();
    let want: Vec<u8> = (1..crate::materials::N as u8)
        .filter(|id| {
            let name = crate::materials::MATS[*id as usize].name.to_ascii_lowercase().replace(' ', "_");
            name != "dormant_spire" && name != "awake_spire" && *id != m("water") && !used.contains(id)
        })
        .collect();
    let mut spots = Vec::new();
    for rad in [4, 6, 8] {
        spots.extend(ring(q, r, rad).into_iter().filter(|(a, _)| *a <= q + 1));
    }
    for ((a, b), mid) in spots.into_iter().zip(want) {
        p.put(a, b, SURF, m("polished_stone"));
        p.put(a, b, SURF + 1, m("plinth"));
        p.put(a, b, SURF + 2, mid);
    }
}

fn reserve(p: &mut Plan) {
    let stations = [
        (0, 0, 7), (34, -9, 6), (58, 4, 5), (60, 28, 5), (38, 48, 5), (10, 60, 6), (-26, 41, 5), (6, -32, 4),
        (8, -43, 6),
    ];
    for (q, r, rad) in stations {
        for dq in -rad..=rad {
            for dr in -rad..=rad {
                if hex_distance(0, 0, dq, dr) <= rad {
                    p.reserved.insert((q + dq, r + dr));
                }
            }
        }
    }
    for (q, r) in crate::lesson::path_cells() {
        for (dq, dr) in std::iter::once((0, 0)).chain(DIRS.iter().copied()) {
            p.reserved.insert((q + dq as i64, r + dr as i64));
        }
    }
    for (q, r) in [(6, 2), (34, -8), (58, 8), (60, 32), (38, 52), (6, 54), (-26, 38), (6, -32)] {
        for (dq, dr) in std::iter::once((0, 0)).chain(DIRS.iter().copied()) {
            p.reserved.insert((q + dq as i64, r + dr as i64));
        }
    }
    for (q, r, _) in [(33, -10, 0), (59, 31, 0), (37, 51, 0), (7, 55, 0), (-25, 39, 0), (5, -31, 0)] {
        p.reserved.insert((q, r));
    }
}

fn build_plan() -> HashMap<(i32, i32), Vec<(i32, i32, i32, u8)>> {
    let mut p = Plan { cells: HashMap::new(), reserved: HashSet::new() };
    reserve(&mut p);
    rainbow_plaza(&mut p, 28, 20);
    bazaar(&mut p, 28, 20);
    hall_of_stones(&mut p, 47, 22);
    conservatory(&mut p, 10, 36);
    mossback_monument(&mut p, 12, 12);
    bounce_park(&mut p, 24, 4);
    observatory(&mut p, 22, -24);
    treehouse_grove(&mut p, 24, 66);
    frost_folly(&mut p, -36, 36);
    ember_forge(&mut p, -34, 24);
    tidewell_sanctuary(&mut p, 6, -32);
    knoll_crown(&mut p, 10, -58, SURF + 3);
    arch(&mut p, 24, -3, 23, -9, m("blush_plaster"), m("rose_patterned_tile"), m("rose_banner"));
    arch(&mut p, 56, 14, 63, 13, m("sage_plaster"), m("leaf_patterned_tile"), m("leaf_banner"));
    arch(&mut p, 30, 50, 29, 56, m("ivory_plaster"), m("honey_patterned_tile"), m("honey_banner"));
    arch(&mut p, -16, 39, -13, 45, m("dusk_plaster"), m("violet_patterned_tile"), m("violet_banner"));
    windmill(&mut p, 61, -11);
    hedge_maze(&mut p, -3, 29);
    woolhop_statue(&mut p, 34, 39);
    sky_castle(&mut p, -16, 18, SURF + 34);
    meadow(&mut p);
    block_gallery(&mut p, -14, 2);
    let mut buckets: HashMap<(i32, i32), Vec<(i32, i32, i32, u8)>> = HashMap::new();
    for ((q, r, y), mat) in p.cells {
        let cq = q.div_euclid(CHUNK as i64) as i32;
        let cr = r.div_euclid(CHUNK as i64) as i32;
        let lq = (q - cq as i64 * CHUNK as i64) as i32;
        let lr = (r - cr as i64 * CHUNK as i64) as i32;
        buckets.entry((cq, cr)).or_default().push((lq, y, lr, mat));
    }
    buckets
}

fn buckets() -> &'static HashMap<(i32, i32), Vec<(i32, i32, i32, u8)>> {
    static PLAN: OnceLock<HashMap<(i32, i32), Vec<(i32, i32, i32, u8)>>> = OnceLock::new();
    PLAN.get_or_init(build_plan)
}

pub fn apply(chunk: &mut crate::chunk::Chunk) {
    let Some(cells) = buckets().get(&(chunk.cq, chunk.cr)) else { return };
    for (lq, y, lr, mat) in cells {
        chunk.set(*lq, *y, *lr, *mat);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clocktower_and_castle_use_the_python_materials() {
        let plan = buckets();
        let tower = plan.get(&(1, 1)).expect("plaza chunk");
        assert!(tower.iter().any(|(_, y, _, mat)| *y == SURF + 43 && *mat == m("cosmic_star")));
        let castle = plan.values().flatten().any(|(_, y, _, mat)| *y == SURF + 34 + 26 && *mat == m("sky_crystal_lamp"));
        assert!(castle, "sky castle lamp");
        assert!(plan.values().flatten().any(|(_, _, _, mat)| *mat == m("canopy")), "maze or grove");
    }
}

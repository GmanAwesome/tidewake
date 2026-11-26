//! The lesson island from `tutorial.py`, plus the 1.4.6 showpieces.
//!
//! Land shape, path, stations and the bridge match the Python lesson. The
//! showpiece overlay is `showpieces`.

use crate::chunk::Chunk;
use crate::config::{CHUNK, LAYERS};
use crate::hex::{hex_distance, hex_line, DIRS};
use crate::materials::{id_named, id};
use crate::showpieces::{self, SURF};

const BOT: i32 = 42;

pub fn in_land(q: i64, r: i64) -> bool {
    if hex_distance(q, r, 10, -58) <= 10 {
        return true;
    }
    if (-48..=-39).contains(&r) {
        return false;
    }
    hex_distance(q, r, 0, 0) <= 18
        || hex_distance(q, r, 38, 12) <= 32
        || hex_distance(q, r, 56, 28) <= 14
        || hex_distance(q, r, 20, 48) <= 26
        || hex_distance(q, r, -22, 36) <= 18
        || hex_distance(q, r, 6, -28) <= 14
        || hex_distance(q, r, 16, 30) <= 20
        || hex_distance(q, r, 0, 24) <= 14
        || hex_distance(q, r, 20, -10) <= 16
        || hex_distance(q, r, -4, 42) <= 16
        || hex_distance(q, r, 28, 22) <= 12
}

fn rim(q: i64, r: i64) -> bool {
    in_land(q, r) && DIRS.iter().any(|(dq, dr)| !in_land(q + *dq as i64, r + *dr as i64))
}

const WAYPOINTS: [(i64, i64); 20] = [
    (0, 0), (6, 2), (16, -4), (34, -8), (48, 0), (58, 8), (60, 20), (60, 32), (50, 42), (38, 52), (20, 54),
    (6, 54), (-10, 48), (-26, 38), (-8, 20), (0, 8), (0, 0), (4, -16), (6, -32), (8, -38),
];

pub fn path_cells() -> Vec<(i64, i64)> {
    let mut pts = Vec::new();
    let knoll = [(8, -38), (8, -48), (10, -58)];
    let mut all = WAYPOINTS.to_vec();
    all.extend_from_slice(&knoll);
    for w in all.windows(2) {
        pts.extend(hex_line(w[0].0, w[0].1, w[1].0, w[1].1));
    }
    pts
}

fn mat(name: &str) -> u8 {
    id_named(name).unwrap_or(id::STONE)
}

pub fn generate(cq: i32, cr: i32) -> Chunk {
    let mut chunk = Chunk {
        cq,
        cr,
        cells: vec![0u8; (CHUNK * LAYERS * CHUNK) as usize],
        realm: vec![0u8; (CHUNK * CHUNK) as usize],
    };
    let q0 = cq as i64 * CHUNK as i64;
    let r0 = cr as i64 * CHUNK as i64;
    if q0 > 90 || (q0 + CHUNK as i64) < -60 || r0 > 90 || (r0 + CHUNK as i64) < -80 {
        return chunk;
    }
    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let q = q0 + lq as i64;
            let r = r0 + lr as i64;
            if !in_land(q, r) {
                continue;
            }
            let knoll = hex_distance(q, r, 10, -58) <= 10;
            let top = SURF + if rim(q, r) { 1 } else { 0 } + if knoll { 2 } else { 0 };
            let fill = if knoll { mat("carved_stone") } else { id::STONE };
            for y in BOT..top {
                chunk.set(lq, y, lr, if y >= top - 1 { id::LOAM } else { fill });
            }
            let cap = if knoll {
                if hex_distance(q, r, 10, -58) >= 8 { mat("carved_stone") } else { id::TURF }
            } else if hex_distance(q, r, 0, 0) <= 8 {
                mat("pearl_terrazzo")
            } else {
                id::TURF
            };
            chunk.set(lq, top, lr, cap);
        }
    }

    let tile = mat("honey_patterned_tile");
    let mut seen = std::collections::HashSet::new();
    for (q, r) in path_cells() {
        for (dq, dr) in std::iter::once((0_i32, 0)).chain(DIRS.iter().copied()) {
            let (qq, rr) = (q + dq as i64, r + dr as i64);
            if !seen.insert((qq, rr)) {
                continue;
            }
            if !in_land(qq, rr) && !(-50..=-37).contains(&rr) {
                continue;
            }
            paint(&mut chunk, qq, rr, SURF, tile);
            for y in SURF + 1..SURF + 4 {
                paint(&mut chunk, qq, rr, y, 0);
            }
        }
    }
    for (q, r) in [(14, -4), (46, 2), (60, 20), (50, 42), (20, 54), (-10, 48), (-8, 20), (4, -16), (8, -38)] {
        paint(&mut chunk, q, r, SURF, tile);
        paint(&mut chunk, q, r, SURF + 1, mat("signpost"));
    }
    plaza(&mut chunk);
    stations(&mut chunk);
    showpieces::apply(&mut chunk);
    for (q, r) in [(33_i64, -10_i64), (59, 31), (37, 51), (7, 55), (-25, 39), (5, -31)] {
        paint(&mut chunk, q, r, SURF + 1, mat("chest"));
    }
    chunk
}

fn paint(chunk: &mut Chunk, q: i64, r: i64, y: i32, mat_id: u8) {
    let q0 = chunk.cq as i64 * CHUNK as i64;
    let r0 = chunk.cr as i64 * CHUNK as i64;
    let lq = q - q0;
    let lr = r - r0;
    if (0..CHUNK as i64).contains(&lq) && (0..CHUNK as i64).contains(&lr) {
        if y == SURF && chunk.get(lq as i32, SURF, lr as i32) == 0 && mat_id != 0 {
            for yy in BOT..SURF {
                chunk.set(lq as i32, yy, lr as i32, if yy >= SURF - 1 { id::LOAM } else { id::STONE });
            }
        }
        chunk.set(lq as i32, y, lr as i32, mat_id);
    }
}

fn plaza(chunk: &mut Chunk) {
    let terra = mat("pearl_terrazzo");
    let tile = mat("honey_patterned_tile");
    let ink = mat("ink_patterned_tile");
    for dq in -7..=7 {
        for dr in -7..=7 {
            if hex_distance(0, 0, dq, dr) > 7 || !in_land(dq, dr) {
                continue;
            }
            let ring = hex_distance(0, 0, dq, dr);
            let floor = if ring == 5 || ring == 6 { ink } else if ring >= 3 { tile } else { terra };
            paint(chunk, dq, dr, SURF, floor);
            paint(chunk, dq, dr, SURF + 1, 0);
            paint(chunk, dq, dr, SURF + 2, 0);
        }
    }
    let ivory = mat("ivory_plaster");
    for (dq, dr) in std::iter::once((0, 0)).chain(DIRS.iter().copied()) {
        paint(chunk, dq as i64, 6 + dr as i64, SURF, ivory);
    }
    paint(chunk, 0, 6, SURF, mat("pewter"));
    paint(chunk, 0, 6, SURF + 1, id::WATER);
    for (dq, dr) in DIRS {
        paint(chunk, dq as i64, 6 + dr as i64, SURF + 1, mat("tide_stained_glass"));
        paint(chunk, dq as i64, 6 + dr as i64, SURF + 2, 0);
    }
    for (q, r, name) in [(7, 3, "rose_banner"), (7, 5, "honey_banner"), (-6, 5, "sky_banner"), (8, 1, "leaf_banner"), (-7, 3, "rose_banner")] {
        paint(chunk, q, r, SURF + 1, mat(name));
    }
    paint(chunk, 7, 4, SURF + 1, ivory);
    paint(chunk, -6, 4, SURF + 1, ivory);
    paint(chunk, 7, 4, SURF + 2, mat("honey_crystal_lamp"));
    paint(chunk, 3, 2, SURF + 1, mat("bedroll"));
    paint(chunk, 2, 3, SURF + 1, mat("glowstick"));
    for (q, r) in [(-3, 5), (4, 5), (5, 4)] {
        paint(chunk, q, r, SURF + 1, ivory);
    }
}

fn stations(chunk: &mut Chunk) {
    for (q, r, h) in [(32, -12, 8), (36, -12, 7), (37, -9, 8), (31, -6, 7), (38, -6, 6), (30, -11, 7)] {
        tree(chunk, q, r, h);
    }
    for (q, r) in [(35, -5), (36, -5), (36, -4), (37, -5)] {
        paint(chunk, q, r, SURF, id::STONE);
        paint(chunk, q, r, SURF + 1, mat("cobble"));
        paint(chunk, q, r, SURF + 2, id::STONE);
    }
    workshop(chunk, 58, 4);
    kiln_hall(chunk, 60, 28);
    practice_house(chunk, 38, 48);
    pond(chunk, 10, 60, 5);
    for (q, r) in [(6, 54), (6, 55), (7, 54), (7, 56), (8, 56), (8, 57)] {
        paint(chunk, q, r, SURF, id::PLANKS);
        paint(chunk, q, r, SURF + 1, 0);
    }
    paint(chunk, 6, 56, SURF + 1, mat("wood_lattice"));
    paint(chunk, 9, 57, SURF + 1, mat("sky_banner"));
    paint(chunk, 5, 54, SURF + 1, mat("sky_banner"));
    for (q, r) in [(-28, 40), (-27, 40), (-26, 40), (-25, 40), (-28, 41), (-27, 41), (-26, 41), (-25, 41), (-27, 42), (-26, 42), (-25, 42), (-24, 40), (-24, 41)] {
        paint(chunk, q, r, SURF, mat("farmland"));
        paint(chunk, q, r, SURF + 1, 0);
    }
    paint(chunk, -28, 40, SURF + 1, mat("skywheat"));
    paint(chunk, -25, 41, SURF + 1, mat("berry_crop"));
    paint(chunk, -26, 42, SURF + 1, mat("skywheat"));
    for (q, r) in [(-29, 39), (-29, 41), (-23, 39), (-23, 42), (-28, 43)] {
        paint(chunk, q, r, SURF + 1, mat("leaf_woven_panel"));
    }
    paint(chunk, -24, 43, SURF + 1, mat("leaf_banner"));
    for (q, r) in [(-22, 43), (-21, 43), (-22, 44)] {
        paint(chunk, q, r, SURF - 1, id::STONE);
        paint(chunk, q, r, SURF, id::WATER);
        paint(chunk, q, r, SURF + 1, 0);
    }
    let dusk = mat("dusk_plaster");
    for dq in -3..=3 {
        for dr in -3..3 {
            if hex_distance(0, 0, dq, dr) <= 3 {
                paint(chunk, 6 + dq, -32 + dr, SURF, dusk);
            }
        }
    }
    paint(chunk, 6, -32, SURF + 1, 0);
    paint(chunk, 8, -32, SURF + 1, mat("waystone"));
    paint(chunk, 4, -33, SURF + 1, mat("tidewell"));
    paint(chunk, 8, -34, SURF + 1, mat("violet_crystal_lamp"));
    paint(chunk, 4, -30, SURF + 1, mat("honey_banner"));
    bridge(chunk);
    paint(chunk, 10, -58, SURF + 3, mat("carved_stone"));
    paint(chunk, 10, -58, SURF + 4, mat("waystone"));
    for (dq, dr) in DIRS {
        paint(chunk, 10 + dq as i64, -58 + dr as i64, SURF + 3, mat("carved_stone"));
        paint(chunk, 10 + dq as i64, -58 + dr as i64, SURF + 4, 0);
    }
    paint(chunk, 10, -60, SURF + 4, dusk);
    paint(chunk, 10, -60, SURF + 5, dusk);
    paint(chunk, 10, -60, SURF + 6, mat("cosmic_star"));
    paint(chunk, 12, -57, SURF + 4, mat("violet_crystal_lamp"));
    paint(chunk, 8, -57, SURF + 4, mat("honey_banner"));
}

fn tree(chunk: &mut Chunk, q: i64, r: i64, h: i32) {
    for i in 0..h {
        paint(chunk, q, r, SURF + 1 + i, id::HEARTWOOD);
    }
    for (dq, dr) in std::iter::once((0, 0)).chain(DIRS.iter().copied()) {
        for dy in h - 2..h + 2 {
            if dq == 0 && dr == 0 && dy < h {
                continue;
            }
            paint(chunk, q + dq as i64, r + dr as i64, SURF + 1 + dy, id::CANOPY);
        }
    }
}

fn workshop(chunk: &mut Chunk, q: i64, r: i64) {
    let plaster = mat("blush_plaster");
    let stain = mat("rose_stained_glass");
    for dq in -3..=3 {
        for dr in -3..3 {
            let floor = if dq == 0 && dr == 0 { mat("honey_patterned_tile") } else { plaster };
            paint(chunk, q + dq, r + dr, SURF, floor);
            paint(chunk, q + dq, r + dr, SURF + 1, 0);
            paint(chunk, q + dq, r + dr, SURF + 2, 0);
        }
    }
    for dq in -3..=3 {
        for dr in -3..3 {
            let edge = dq == -3 || dq == 3 || dr == -3;
            if edge {
                let win = (dr == -3 && (dq == -1 || dq == 1)) || ((dq == -3 || dq == 3) && dr == -1);
                paint(chunk, q + dq, r + dr, SURF + 1, plaster);
                paint(chunk, q + dq, r + dr, SURF + 2, if win { stain } else { plaster });
            }
            paint(chunk, q + dq, r + dr, SURF + 3, plaster);
        }
    }
    paint(chunk, q, r, SURF + 1, mat("tinker_bench"));
    paint(chunk, q - 3, r + 2, SURF + 1, mat("rose_banner"));
    paint(chunk, q + 3, r + 2, SURF + 1, mat("rose_banner"));
    paint(chunk, q + 2, r + 2, SURF + 1, mat("pale_lattice"));
}

fn kiln_hall(chunk: &mut Chunk, q: i64, r: i64) {
    let brick = mat("ochre_bricks");
    let iron = mat("wrought_iron");
    for dq in -3..=3 {
        for dr in -3..3 {
            paint(chunk, q + dq, r + dr, SURF, brick);
            paint(chunk, q + dq, r + dr, SURF + 1, 0);
            paint(chunk, q + dq, r + dr, SURF + 2, 0);
            let edge = dq == -3 || dq == 3 || dr == -3;
            if edge {
                paint(chunk, q + dq, r + dr, SURF + 1, brick);
                paint(chunk, q + dq, r + dr, SURF + 2, if dq == 0 && dr == -3 { iron } else { brick });
            }
            paint(chunk, q + dq, r + dr, SURF + 3, brick);
            if dq.abs() == 3 || dr == -3 {
                paint(chunk, q + dq, r + dr, SURF + 4, brick);
            }
        }
    }
    paint(chunk, q, r, SURF + 1, mat("kiln"));
    paint(chunk, q + 2, r - 1, SURF + 1, mat("brass"));
}

fn practice_house(chunk: &mut Chunk, q: i64, r: i64) {
    let plaster = mat("sage_plaster");
    let stain = mat("sky_stained_glass");
    for dq in -3..=3 {
        for dr in -2..=2 {
            paint(chunk, q + dq, r + dr, SURF, plaster);
            let edge = dq == -3 || dq == 3 || dr == -2 || dr == 2;
            let door = dr == 2 && dq == 0;
            if edge && !door {
                let win = ((dr == -2 || dr == 2) && (-2..=2).contains(&dq)) || ((dq == -3 || dq == 3) && dr == 0);
                paint(chunk, q + dq, r + dr, SURF + 1, plaster);
                paint(chunk, q + dq, r + dr, SURF + 2, if win { stain } else { plaster });
                paint(chunk, q + dq, r + dr, SURF + 3, plaster);
                paint(chunk, q + dq, r + dr, SURF + 4, if win { stain } else { plaster });
            }
            if door {
                paint(chunk, q + dq, r + dr, SURF + 1, mat("door"));
                paint(chunk, q + dq, r + dr, SURF + 2, mat("door"));
                paint(chunk, q + dq, r + dr, SURF + 3, plaster);
            }
            paint(chunk, q + dq, r + dr, SURF + 5, plaster);
        }
    }
    for dq in -2..=2 {
        for dr in -1..=1 {
            if !(dq == -2 && dr == 0) {
                paint(chunk, q + dq, r + dr, SURF + 3, mat("pale_planks"));
            }
        }
    }
    for y in SURF + 1..SURF + 6 {
        paint(chunk, q - 4, r, y, mat("ladder"));
    }
    paint(chunk, q - 3, r, SURF + 1, mat("wood_lattice"));
    paint(chunk, q + 4, r + 2, SURF + 1, mat("pale_lattice"));
}

fn pond(chunk: &mut Chunk, q0: i64, r0: i64, rad: i64) {
    for dq in -rad..=rad {
        for dr in -rad..=rad {
            if hex_distance(0, 0, dq, dr) <= rad {
                let (q, r) = (q0 + dq, r0 + dr);
                paint(chunk, q, r, SURF - 2, id::STONE);
                paint(chunk, q, r, SURF - 1, id::WATER);
                paint(chunk, q, r, SURF, 0);
            }
        }
    }
}

fn bridge(chunk: &mut Chunk) {
    let plank = mat("pale_planks");
    let rail = mat("wood_lattice");
    let post = mat("brass");
    for (q, r) in hex_line(8, -38, 8, -48) {
        paint(chunk, q, r, SURF, plank);
        paint(chunk, q, r, SURF + 1, 0);
        paint(chunk, q, r, SURF + 2, 0);
        for y in SURF - 4..SURF {
            paint(chunk, q, r, y, if y == SURF - 4 { post } else { plank });
        }
        for (dq, dr) in DIRS.iter().take(2) {
            paint(chunk, q + *dq as i64, r + *dr as i64, SURF, plank);
            paint(chunk, q + *dq as i64, r + *dr as i64, SURF + 1, rail);
        }
    }
    paint(chunk, 8, -38, SURF + 1, post);
    paint(chunk, 8, -48, SURF + 1, post);
    paint(chunk, 8, -48, SURF + 2, mat("sky_crystal_lamp"));
    paint(chunk, 8, -38, SURF, plank);
    paint(chunk, 8, -48, SURF, plank);
}

pub fn spawn() -> (f64, f64, f64) {
    let (x, z) = crate::hex::center(0, 0);
    let feet = (SURF as f64 + 1.0) * crate::config::LAYER + 0.02;
    (x, feet, z)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn land_shape_and_plaza_match_the_lesson() {
        assert!(in_land(0, 0));
        assert!(!in_land(0, -44));
        assert!(in_land(10, -58));
        let home = generate(0, 0);
        assert_eq!(home.get(0, SURF, 0), mat("pearl_terrazzo"));
        assert_eq!(home.get(0, SURF + 1, 6), id::WATER);
        let grove = generate(1, 1);
        assert!(grove.cells.iter().any(|c| *c == mat("cosmic_star")), "clocktower star");
    }
}

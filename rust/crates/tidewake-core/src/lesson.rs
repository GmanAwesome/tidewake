//! The lesson island. A hand-built disc the tutorial opens on, so Learn to play
//! has ground, a path, water and a tree without waiting on the full showpiece set.
//!
//! The 1.4.6 showpiece builds (plaza, bazaar, castle, maze and the rest) are
//! still pending. See ROADMAP-2.1.md.

use crate::chunk::Chunk;
use crate::config::{CHUNK, LAYERS};
use crate::hex::hex_distance;
use crate::materials::id;

const SURFACE: i32 = 48;
const RADIUS: i64 = 22;

pub fn is_lesson_chunk(cq: i32, cr: i32) -> bool {
    let q0 = cq as i64 * CHUNK as i64;
    let r0 = cr as i64 * CHUNK as i64;
    // The disc can touch this chunk if any corner is near the origin.
    for (dq, dr) in [(0, 0), (CHUNK as i64 - 1, 0), (0, CHUNK as i64 - 1), (CHUNK as i64 - 1, CHUNK as i64 - 1)] {
        if hex_distance(q0 + dq, r0 + dr, 0, 0) <= RADIUS + 2 {
            return true;
        }
    }
    hex_distance(q0 + 8, r0 + 8, 0, 0) <= RADIUS + 8
}

pub fn generate(cq: i32, cr: i32) -> Chunk {
    let mut chunk = Chunk {
        cq,
        cr,
        cells: vec![0u8; (CHUNK * LAYERS * CHUNK) as usize],
        realm: vec![0u8; (CHUNK * CHUNK) as usize],
    };
    if !is_lesson_chunk(cq, cr) {
        return chunk;
    }
    let q0 = cq as i64 * CHUNK as i64;
    let r0 = cr as i64 * CHUNK as i64;
    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let q = q0 + lq as i64;
            let r = r0 + lr as i64;
            let dist = hex_distance(q, r, 0, 0);
            chunk.realm[(lq * CHUNK + lr) as usize] = 0;
            if dist > RADIUS {
                continue;
            }
            let top = SURFACE - if dist > RADIUS - 2 { 1 } else { 0 };
            for y in (top - 6)..=top {
                let mat = if y == top {
                    if dist > 6 && dist < 9 && q.abs() <= 1 { id::PLANKS } else { id::TURF }
                } else if y >= top - 2 {
                    id::LOAM
                } else {
                    id::STONE
                };
                chunk.set(lq, y, lr, mat);
            }
            // A small pool off the path.
            if hex_distance(q, r, 8, -4) <= 3 && dist < RADIUS - 1 {
                chunk.set(lq, top, lr, id::WATER);
                chunk.set(lq, top - 1, lr, id::SAND);
            }
            // A tree at the north of the plaza.
            if q == 0 && r == -8 {
                for y in top + 1..top + 6 {
                    chunk.set(lq, y, lr, id::HEARTWOOD);
                }
            }
            if hex_distance(q, r, 0, -8) <= 2 && hex_distance(q, r, 0, -8) > 0 {
                chunk.set(lq, top + 5, lr, id::CANOPY);
                chunk.set(lq, top + 6, lr, id::CANOPY);
            }
            // A cottage of planks.
            if (4..8).contains(&q) && (-2..3).contains(&r) {
                if q == 4 || q == 7 || r == -2 || r == 2 {
                    if !(q == 4 && r == 0) {
                        for y in top + 1..top + 4 {
                            chunk.set(lq, y, lr, id::PLANKS);
                        }
                    }
                }
                if q > 4 && q < 7 && r > -2 && r < 2 {
                    chunk.set(lq, top + 4, lr, id::PLANKS);
                }
            }
        }
    }
    chunk
}

pub fn spawn() -> (f64, f64, f64) {
    let (x, z) = crate::hex::center(0, 0);
    let feet = (SURFACE as f64 + 1.0) * crate::config::LAYER + 0.02;
    (x, feet, z)
}

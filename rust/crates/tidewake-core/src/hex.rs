//! Pointy-top axial hex lattice. Matches `tidewake/hexgrid.py`.

use crate::config::{CHUNK, HEX, LAYER, SQ3};

pub const DIRS: [(i32, i32); 6] = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)];

#[inline]
pub fn center(q: i64, r: i64) -> (f64, f64) {
    let q = q as f64;
    let r = r as f64;
    (HEX * SQ3 * (q + r * 0.5), HEX * 1.5 * r)
}

#[inline]
pub fn layer_of(y: f64) -> i32 {
    (y / LAYER).floor() as i32
}

#[inline]
pub fn layer_y(layer: i32) -> f64 {
    layer as f64 * LAYER
}

pub fn cube_round(qf: f64, rf: f64) -> (i64, i64) {
    let sf = -qf - rf;
    let mut q = qf.round();
    let mut r = rf.round();
    let s = sf.round();
    let dq = (q - qf).abs();
    let dr = (r - rf).abs();
    let ds = (s - sf).abs();
    if dq > dr && dq > ds {
        q = -r - s;
    } else if dr > ds {
        r = -q - s;
    }
    (q as i64, r as i64)
}

pub fn cell_at(x: f64, z: f64) -> (i64, i64) {
    let qf = (SQ3 / 3.0 * x - z / 3.0) / HEX;
    let rf = (2.0 / 3.0 * z) / HEX;
    cube_round(qf, rf)
}

pub fn hex_distance(q1: i64, r1: i64, q2: i64, r2: i64) -> i64 {
    let dq = q1 - q2;
    let dr = r1 - r2;
    (dq.abs() + dr.abs() + (dq + dr).abs()) / 2
}

/// Signed distance to a cell's outline. Negative is inside. Matches `hex_sdf`.
pub fn hex_sdf(px: f64, pz: f64) -> f64 {
    let inradius = HEX * SQ3 / 2.0;
    let kx = -0.866025404;
    let ky = 0.5;
    let kz = 0.577350269;
    let mut x = pz.abs();
    let mut y = px.abs();
    let d = 2.0 * (kx * x + ky * y).min(0.0);
    x -= d * kx;
    y -= d * ky;
    let lim = kz * inradius;
    x -= x.clamp(-lim, lim);
    y -= inradius;
    (x * x + y * y).sqrt() * if y > 0.0 { 1.0 } else { -1.0 }
}

pub fn chunk_of(q: i64, r: i64) -> (i32, i32) {
    ((q.div_euclid(CHUNK as i64)) as i32, (r.div_euclid(CHUNK as i64)) as i32)
}

/// Six corners in x,z, relative to the cell centre. Pointy top.
pub fn corners() -> [(f64, f64); 6] {
    let mut out = [(0.0, 0.0); 6];
    let mut angles = [0.0; 6];
    for (i, d) in DIRS.iter().enumerate() {
        let (x, z) = center(d.0 as i64, d.1 as i64);
        angles[i] = z.atan2(x);
    }
    for i in 0..6 {
        let a = angles[i] + 30.0_f64.to_radians();
        out[i] = (HEX * a.cos(), HEX * a.sin());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_near_origin() {
        for q in -8..8 {
            for r in -8..8 {
                let (x, z) = center(q, r);
                assert_eq!(cell_at(x, z), (q, r), "q={q} r={r}");
            }
        }
    }

    #[test]
    fn negative_chunks_floor() {
        assert_eq!(chunk_of(-1, -1), (-1, -1));
        assert_eq!(chunk_of(-16, 16), (-1, 1));
        assert_eq!(chunk_of(0, 0), (0, 0));
    }

    #[test]
    fn sdf_is_inside_at_the_centre() {
        assert!(hex_sdf(0.0, 0.0) < 0.0);
        assert!(hex_sdf(2.0, 0.0) > 0.0);
    }

    #[test]
    fn distance_matches_axial() {
        assert_eq!(hex_distance(0, 0, 2, -1), 2);
        assert_eq!(hex_distance(1, -1, -1, 2), 3);
    }
}

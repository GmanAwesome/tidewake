//! Stacked sky tiers from `tidewake/skytiers.py`.
//!
//! Extra islands of every size sit at independent heights from just above the
//! cloud sea up to about 480. A tier is kept only when it clears the main
//! terrain and every earlier tier, so islands are never cut in half.

use std::collections::HashMap;

use crate::chunk::Chunk;
use crate::columns::{size_class, Generator, SizeClass};
use crate::config::{CHUNK, HEX, LAYERS, SQ3};
use crate::hex::DIRS;
use crate::materials::id;
use crate::noise::rand01;

pub const CLEAR: f64 = 5.0;
pub const TREE_ROOM: f64 = 16.0;
const TOP_CAP: i32 = LAYERS - 20;
const ALT_LO: f64 = 40.0;
const ALT_HI: f64 = 470.0;
const DEPTH_MAX: f64 = 70.0;

/// (name, period, accept, rmin, rmax, seed offset)
const TIERS: [(&str, f64, f64, f64, f64, u64); 9] = [
    ("large", 620.0, 0.30, 0.16, 0.24, 301),
    ("medium", 300.0, 0.42, 0.14, 0.24, 311),
    ("medium", 260.0, 0.42, 0.14, 0.24, 316),
    ("small", 150.0, 0.50, 0.12, 0.22, 321),
    ("small", 130.0, 0.50, 0.12, 0.22, 326),
    ("small", 115.0, 0.50, 0.12, 0.22, 331),
    ("tiny", 60.0, 0.40, 0.07, 0.14, 341),
    ("tiny", 48.0, 0.40, 0.07, 0.14, 346),
    ("tiny", 40.0, 0.40, 0.07, 0.14, 351),
];

#[derive(Clone, Copy)]
pub(crate) struct Island {
    px: f64,
    pz: f64,
    rad: f64,
    alt: f64,
    depth: f64,
}

pub struct TierCache {
    cols: HashMap<(i64, i64), crate::columns::Column>,
    acc: HashMap<(usize, i64, i64), Option<Island>>,
    ok: HashMap<(u64, i64, i64), bool>,
}

impl TierCache {
    pub fn new() -> Self {
        Self { cols: HashMap::new(), acc: HashMap::new(), ok: HashMap::new() }
    }
}

impl Default for TierCache {
    fn default() -> Self { Self::new() }
}

fn cand(gen: &Generator, ti: usize, ci: i64, cj: i64) -> Option<Island> {
    let (_, period, accept, rmin, rmax, off) = TIERS[ti];
    if rand01(ci, cj, gen.h.wrapping_add(off)) >= accept {
        return None;
    }
    let px = (ci as f64 + 0.5 + (rand01(ci, cj, gen.h.wrapping_add(off + 1)) - 0.5) * 0.5) * period;
    let pz = (cj as f64 + 0.5 + (rand01(ci, cj, gen.h.wrapping_add(off + 2)) - 0.5) * 0.5) * period;
    let rad = period * (rmin + (rmax - rmin) * rand01(ci, cj, gen.h.wrapping_add(off + 3)));
    let alt = ALT_LO + (ALT_HI - ALT_LO) * rand01(ci, cj, gen.h.wrapping_add(off + 4));
    let depth = 2.0 + DEPTH_MAX.min(rad * 0.55) * 1.15;
    Some(Island { px, pz, rad, alt, depth })
}

fn island_ok(gen: &Generator, cache: &mut TierCache, off: u64, ci: i64, cj: i64, px: f64, pz: f64, rad: f64, alt: f64, depth_max: f64) -> bool {
    if let Some(v) = cache.ok.get(&(off, ci, cj)) {
        return *v;
    }
    let mut pts = vec![(0.0, 0.0)];
    for ring in [0.45, 0.8, 1.05] {
        for a in 0..10 {
            let ang = a as f64 * std::f64::consts::PI / 5.0 + ring;
            pts.push((ang.cos() * ring, ang.sin() * ring));
        }
    }
    let lo = alt - depth_max - CLEAR;
    let hi = alt + 8.0 + CLEAR;
    let mut clash = false;
    for (u, w) in pts {
        let x = px + rad * u;
        let z = pz + rad * w;
        let rr = z / (HEX * 1.5);
        let qq = x / (HEX * SQ3) - rr * 0.5;
        let q = qq.round() as i64;
        let r = rr.round() as i64;
        let col = *cache.cols.entry((q, r)).or_insert_with(|| gen.sample(q, r));
        if col.land && col.top as f64 + TREE_ROOM >= lo && col.bottom as f64 - CLEAR <= hi {
            clash = true;
            break;
        }
    }
    cache.ok.insert((off, ci, cj), !clash);
    !clash
}

pub(crate) fn accepted(gen: &Generator, cache: &mut TierCache, ti: usize, ci: i64, cj: i64) -> Option<Island> {
    if let Some(v) = cache.acc.get(&(ti, ci, cj)) {
        return *v;
    }
    let c = cand(gen, ti, ci, cj);
    let mut res = None;
    if let Some(c) = c {
        let mut ok = island_ok(gen, cache, TIERS[ti].5, ci, cj, c.px, c.pz, c.rad, c.alt, c.depth);
        if ok {
            let lo = c.alt - c.depth - CLEAR;
            let hi = c.alt + 8.0 + CLEAR + TREE_ROOM;
            'outer: for tj in 0..ti {
                let pj = TIERS[tj].1;
                let reach = c.rad + TIERS[tj].4 * pj + 0.25 * pj + 4.0;
                let a0 = ((c.px - reach) / pj).floor() as i64;
                let a1 = ((c.px + reach) / pj).floor() as i64;
                let b0 = ((c.pz - reach) / pj).floor() as i64;
                let b1 = ((c.pz + reach) / pj).floor() as i64;
                for a in a0..=a1 {
                    for b in b0..=b1 {
                        if let Some(o) = accepted(gen, cache, tj, a, b) {
                            let dx = o.px - c.px;
                            let dz = o.pz - c.pz;
                            if (dx * dx + dz * dz).sqrt() > c.rad + o.rad + 3.0 {
                                continue;
                            }
                            if o.alt - o.depth - CLEAR <= hi && o.alt + 8.0 + CLEAR + TREE_ROOM >= lo {
                                ok = false;
                                break 'outer;
                            }
                        }
                    }
                }
            }
        }
        if ok {
            res = Some(c);
        }
    }
    cache.acc.insert((ti, ci, cj), res);
    res
}

fn realm_surface(realm: i64) -> (u8, u8, u8) {
    match realm {
        3 | 14 | 18 => (id::SNOW, id::PALE_STONE, id::PALE_STONE),
        6 | 19 => (id::SAND, id::SANDSTONE, id::SANDSTONE),
        12 => (id::CHALK, id::CHALK, id::CHALK),
        11 | 4 => (id::TURF, id::LOAM, id::BASALT),
        13 => (id::TURF, id::STARSTONE, id::STARSTONE),
        _ => (id::TURF, id::LOAM, id::STONE),
    }
}

pub fn stamp(gen: &Generator, cq: i32, cr: i32, chunk: &mut Chunk) {
    let mut cache = TierCache::new();
    let q0 = cq as i64 * CHUNK as i64;
    let r0 = cr as i64 * CHUNK as i64;
    let mut xz = [(0.0, 0.0); (CHUNK * CHUNK) as usize];
    let mut x0 = f64::MAX;
    let mut x1 = f64::MIN;
    let mut z0 = f64::MAX;
    let mut z1 = f64::MIN;
    for i in 0..CHUNK {
        for k in 0..CHUNK {
            let q = q0 + i as i64;
            let r = r0 + k as i64;
            let (x, z) = crate::hex::center(q, r);
            xz[(i * CHUNK + k) as usize] = (x, z);
            x0 = x0.min(x);
            x1 = x1.max(x);
            z0 = z0.min(z);
            z1 = z1.max(z);
        }
    }
    for ti in 0..TIERS.len() {
        let (_, period, _, _, rmax, off) = TIERS[ti];
        let reach = rmax * period * 1.2 + 0.25 * period;
        let mut best_u = vec![9.0; (CHUNK * CHUNK) as usize];
        let mut best_alt = vec![0.0; (CHUNK * CHUNK) as usize];
        let mut best_rad = vec![1.0; (CHUNK * CHUNK) as usize];
        let mut best_id = vec![0i64; (CHUNK * CHUNK) as usize];
        let mut any = false;
        let ci0 = ((x0 - reach) / period).floor() as i64;
        let ci1 = ((x1 + reach) / period).floor() as i64;
        let cj0 = ((z0 - reach) / period).floor() as i64;
        let cj1 = ((z1 + reach) / period).floor() as i64;
        for ci in ci0..=ci1 {
            for cj in cj0..=cj1 {
                let Some(c) = accepted(gen, &mut cache, ti, ci, cj) else { continue };
                let cx = c.px.clamp(x0, x1);
                let cz = c.pz.clamp(z0, z1);
                if ((cx - c.px).hypot(cz - c.pz)) > c.rad * 1.15 {
                    continue;
                }
                any = true;
                for i in 0..CHUNK {
                    for k in 0..CHUNK {
                        let (x, z) = xz[(i * CHUNK + k) as usize];
                        let wn = gen.fbm_detail(x / 11.0 + off as f64, z / 11.0 - off as f64, 2);
                        let dx = x - c.px;
                        let dz = z - c.pz;
                        let warp = 0.12 * c.rad * wn;
                        let u = ((dx * dx + dz * dz).sqrt() + warp) / c.rad;
                        let ix = (i * CHUNK + k) as usize;
                        if u < best_u[ix] {
                            best_u[ix] = u;
                            best_alt[ix] = c.alt;
                            best_rad[ix] = c.rad;
                            best_id[ix] = ci * 7919 + cj + off as i64;
                        }
                    }
                }
            }
        }
        if !any {
            continue;
        }
        let mut placed_col = vec![false; (CHUNK * CHUNK) as usize];
        for i in 0..CHUNK {
            for k in 0..CHUNK {
                let ix = (i * CHUNK + k) as usize;
                if best_u[ix] >= 1.0 {
                    continue;
                }
                let (x, z) = xz[ix];
                let e = (1.0 - best_u[ix]).clamp(0.0, 1.0);
                let dome = e.sqrt();
                let hill = 3.0 * gen.fbm_hill(x / 40.0 + off as f64, z / 40.0, 2) * e;
                let mut top = (best_alt[ix] + 2.0 * dome + hill).floor() as i32;
                let tail = 0.5 * (1.0 - (std::f64::consts::PI * e).cos());
                let depth = 2.0
                    + tail
                        * DEPTH_MAX.min(best_rad[ix] * 0.55)
                        * (0.85 + 0.3 * gen.fbm_depth(x / 20.0, z / 20.0, 2));
                top = top.clamp(8, TOP_CAP);
                let bot = (top - depth.floor() as i32).max(4);
                let mut clash = false;
                for y in (bot - CLEAR as i32)..=(top + CLEAR as i32) {
                    if !(0..LAYERS).contains(&y) {
                        continue;
                    }
                    if solid_near(chunk, i, y, k) {
                        clash = true;
                        break;
                    }
                }
                if clash {
                    continue;
                }
                let realm = best_id[ix].rem_euclid(20);
                let (surf, mid, body) = realm_surface(realm);
                for y in bot..=top {
                    if !(0..LAYERS).contains(&y) {
                        continue;
                    }
                    let mat = if y == top {
                        surf
                    } else if y >= top - 2 {
                        mid
                    } else {
                        body
                    };
                    chunk.set(i, y, k, mat);
                }
                placed_col[ix] = true;
                if surf == id::TURF && e > 0.25 {
                    let hsh = (rand01(q0 + i as i64, r0 + k as i64, gen.h.wrapping_add(off + 9)) * 1.0e9) as i64;
                    if (1..CHUNK - 1).contains(&i) && (1..CHUNK - 1).contains(&k) && hsh.rem_euclid(1000) < 22 {
                        let h = 3 + (hsh.rem_euclid(4) as i32);
                        if top + h + 3 < LAYERS {
                            for y in top + 1..=top + h {
                                chunk.set(i, y, k, id::HEARTWOOD);
                            }
                            for (dq, dr) in DIRS {
                                for y in [top + h, top + h + 1] {
                                    if chunk.get(i + dq, y, k + dr) == 0 {
                                        chunk.set(i + dq, y, k + dr, id::CANOPY);
                                    }
                                }
                            }
                            chunk.set(i, top + h + 1, k, id::CANOPY);
                            chunk.set(i, top + h + 2, k, id::CANOPY);
                        }
                    }
                    if hsh.rem_euclid(1000) > 900 && top + 1 < LAYERS && chunk.get(i, top + 1, k) == 0 {
                        let mat = if hsh.rem_euclid(3) > 0 { id::GRASS } else { id::WILDFLOWER };
                        chunk.set(i, top + 1, k, mat);
                    }
                }
            }
        }
        let _ = placed_col;
    }
}

fn solid_near(chunk: &Chunk, i: i32, y: i32, k: i32) -> bool {
    if chunk.get(i, y, k) > 0 {
        return true;
    }
    for (dq, dr) in DIRS {
        let a = i + dq;
        let b = k + dr;
        if (0..CHUNK).contains(&a) && (0..CHUNK).contains(&b) && chunk.get(a, y, b) > 0 {
            return true;
        }
    }
    false
}

/// Size classes of accepted tier islands inside a grid window. `n` is cells of the finest tier.
pub fn tier_classes(gen: &Generator, n: i64) -> Vec<SizeClass> {
    let mut cache = TierCache::new();
    let mut out = Vec::new();
    for ti in 0..TIERS.len() {
        let period = TIERS[ti].1;
        let reach = (n as f64 / period).ceil() as i64 + 1;
        for ci in -reach..=reach {
            for cj in -reach..=reach {
                if let Some(c) = accepted(gen, &mut cache, ti, ci, cj) {
                    out.push(size_class(c.rad));
                }
            }
        }
    }
    out
}

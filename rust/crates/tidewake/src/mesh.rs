//! Hex-prism meshes. Near chunks are one prism per cell. Far chunks are one
//! prism per vertical run, so stacked islands stay separate in the fog.

use tidewake_core::chunk::Chunk;
use tidewake_core::config::{CHUNK, LAYER};
use tidewake_core::hex::{self, center};
use tidewake_core::materials::{self, hides_face};

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
pub struct Vert {
    pub pos: [f32; 3],
    pub nrm: [f32; 3],
    pub col: [f32; 3],
    /// Atlas UV inside one 64×64 tile.
    pub uv: [f32; 2],
    /// x = material id, y = 0 top / 1 side. Negative material means untextured.
    pub tex: [f32; 2],
}

impl Vert {
    pub fn plain(pos: [f32; 3], nrm: [f32; 3], col: [f32; 3]) -> Self {
        Self { pos, nrm, col, uv: [0.0, 0.0], tex: [-1.0, 0.0] }
    }
}

pub struct CpuMesh {
    pub verts: Vec<Vert>,
    pub idx: Vec<u32>,
}

/// A rolling sheet at the cloud-sea layer, camera-relative so it can use a zero offset.
pub fn cloud_sea(time: f32, cam: [f64; 3]) -> CpuMesh {
    let n = 40i32;
    let step = 10.0f32;
    let base = (12.0 * 0.85) as f32;
    let mut verts = Vec::new();
    let mut idx = Vec::new();
    let col = [0.93, 0.95, 0.98];
    let h = |x: f32, z: f32| base + (x * 0.05 + time * 0.15).sin() * 1.4 + (z * 0.04 - time * 0.1).cos() * 1.1;
    for iz in -n..n {
        for ix in -n..n {
            let x0 = ix as f32 * step;
            let z0 = iz as f32 * step;
            let x1 = x0 + step;
            let z1 = z0 + step;
            let p = |x: f32, z: f32| -> [f32; 3] {
                [x - cam[0] as f32, h(x, z) - cam[1] as f32, z - cam[2] as f32]
            };
            let b = verts.len() as u32;
            for pos in [p(x0, z0), p(x1, z0), p(x1, z1), p(x0, z1)] {
                verts.push(Vert::plain(pos, [0.0, 1.0, 0.0], col));
            }
            idx.extend([b, b + 1, b + 2, b, b + 2, b + 3]);
        }
    }
    CpuMesh { verts, idx }
}

pub fn build(chunk: &Chunk, neighbors: NeighborFn<'_>, lod: bool) -> CpuMesh {
    let mut verts = Vec::new();
    let mut idx = Vec::new();
    let q0 = chunk.cq as i64 * CHUNK as i64;
    let r0 = chunk.cr as i64 * CHUNK as i64;
    let (ox, oz) = center(q0, r0);
    let corners = hex::corners();
    let layer = LAYER as f32;

    for lq in 0..CHUNK {
        for lr in 0..CHUNK {
            let (cx, cz) = center(q0 + lq as i64, r0 + lr as i64);
            let dx = (cx - ox) as f32;
            let dz = (cz - oz) as f32;
            if lod {
                let mut y = 0;
                while y < tidewake_core::config::LAYERS {
                    let id = chunk.get(lq, y, lr);
                    if !draw_id(id) {
                        y += 1;
                        continue;
                    }
                    let y0 = y;
                    let mut y1 = y;
                    while y + 1 < tidewake_core::config::LAYERS && chunk.get(lq, y + 1, lr) == id {
                        y += 1;
                        y1 = y;
                    }
                    y += 1;
                    prism(&mut verts, &mut idx, &corners, dx, dz, y0, y1, layer, id, id);
                }
            } else {
                for y in 0..tidewake_core::config::LAYERS {
                    let id = chunk.get(lq, y, lr);
                    if !draw_id(id) {
                        continue;
                    }
                    let up = neighbors(lq, y + 1, lr);
                    let dn = neighbors(lq, y - 1, lr);
                    if !hides_face(up, id) {
                        cap(&mut verts, &mut idx, &corners, dx, dz, (y + 1) as f32 * layer, true, materials::get(id).top, id, 0.0);
                    }
                    if !hides_face(dn, id) {
                        cap(&mut verts, &mut idx, &corners, dx, dz, y as f32 * layer, false, materials::get(id).side, id, 1.0);
                    }
                    for (d, (dq, dr)) in hex::DIRS.iter().enumerate() {
                        let nid = neighbors(lq + dq, y, lr + dr);
                        if hides_face(nid, id) {
                            continue;
                        }
                        side(&mut verts, &mut idx, &corners, dx, dz, y as f32 * layer, (y + 1) as f32 * layer, d, materials::get(id).side, id);
                    }
                }
            }
        }
    }
    CpuMesh { verts, idx }
}

pub type NeighborFn<'a> = &'a dyn Fn(i32, i32, i32) -> u8;

fn draw_id(id: u8) -> bool {
    id != 0 && (materials::is_solid(id) || id == materials::id::WATER)
}

fn prism(verts: &mut Vec<Vert>, idx: &mut Vec<u32>, corners: &[(f64, f64); 6], dx: f32, dz: f32, y0: i32, y1: i32, layer: f32, top_id: u8, side_id: u8) {
    let yb = y0 as f32 * layer;
    let yt = (y1 + 1) as f32 * layer;
    cap(verts, idx, corners, dx, dz, yt, true, materials::get(top_id).top, top_id, 0.0);
    cap(verts, idx, corners, dx, dz, yb, false, materials::get(side_id).side, side_id, 1.0);
    for d in 0..6 {
        side(verts, idx, corners, dx, dz, yb, yt, d, materials::get(side_id).side, side_id);
    }
}

fn hex_uv(dx: f32, dz: f32) -> [f32; 2] {
    [0.5 + dx / 1.7320508, 0.5 + dz * 0.5]
}

fn cap(verts: &mut Vec<Vert>, idx: &mut Vec<u32>, corners: &[(f64, f64); 6], dx: f32, dz: f32, y: f32, up: bool, col: [f32; 3], mat: u8, side_flag: f32) {
    let n = if up { [0.0, 1.0, 0.0] } else { [0.0, -1.0, 0.0] };
    let mut p = [[0.0; 3]; 6];
    let mut uv = [[0.0; 2]; 6];
    for i in 0..6 {
        let ox = corners[i].0 as f32;
        let oz = corners[i].1 as f32;
        p[i] = [dx + ox, y, dz + oz];
        uv[i] = hex_uv(ox, oz);
    }
    let order = if up { [0, 1, 2, 3, 4, 5] } else { [0, 5, 4, 3, 2, 1] };
    let b = verts.len() as u32;
    for i in order {
        verts.push(Vert { pos: p[i], nrm: n, col, uv: uv[i], tex: [mat as f32, side_flag] });
    }
    for i in 1..5 {
        idx.extend([b, b + i, b + i + 1]);
    }
}

fn side(verts: &mut Vec<Vert>, idx: &mut Vec<u32>, corners: &[(f64, f64); 6], dx: f32, dz: f32, yb: f32, yt: f32, d: usize, col: [f32; 3], mat: u8) {
    let i1 = (d + 1) % 6;
    let a = [dx + corners[d].0 as f32, yb, dz + corners[d].1 as f32];
    let b = [dx + corners[i1].0 as f32, yb, dz + corners[i1].1 as f32];
    let c = [dx + corners[i1].0 as f32, yt, dz + corners[i1].1 as f32];
    let e = [dx + corners[d].0 as f32, yt, dz + corners[d].1 as f32];
    let n = {
        let ex = b[0] - a[0];
        let ez = b[2] - a[2];
        let len = (ex * ex + ez * ez).sqrt().max(1e-5);
        [ez / len, 0.0, -ex / len]
    };
    // Outward normal points away from the centre. Corners are CCW from above,
    // so the right-hand side of a->b is outward in a Y-up system when XZ is
    // viewed from above... flip if the normal points inward.
    let mid_x = (a[0] + b[0]) * 0.5 - dx;
    let mid_z = (a[2] + b[2]) * 0.5 - dz;
    let n = if n[0] * mid_x + n[2] * mid_z < 0.0 { [-n[0], 0.0, -n[2]] } else { n };
    quad(verts, idx, n, col, [a, e, c, b], [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]], mat);
}

fn quad(verts: &mut Vec<Vert>, idx: &mut Vec<u32>, n: [f32; 3], col: [f32; 3], p: [[f32; 3]; 4], uv: [[f32; 2]; 4], mat: u8) {
    let b = verts.len() as u32;
    for i in 0..4 {
        verts.push(Vert { pos: p[i], nrm: n, col, uv: uv[i], tex: [mat as f32, 1.0] });
    }
    idx.extend([b, b + 1, b + 2, b, b + 2, b + 3]);
}

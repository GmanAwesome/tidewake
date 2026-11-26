//! The wanderer, copied from `tidewake/models.py` `wanderer`.
//!
//! Plain unclothed base figure. Feet at y = 0, face toward local -z, back toward +z.
//! The glutes are stepped boxes sunk into the recessed pelvis. The front of the
//! hips stays the smooth pelvis prism: no genitals and no frontal bulge.

use crate::mesh::{CpuMesh, Vert};
use tidewake_core::hex;

const SKIN: [f32; 3] = [0.90, 0.74, 0.62];
const HAIR: [f32; 3] = [0.28, 0.20, 0.18];

pub fn wanderer(time: f32, walking: bool) -> CpuMesh {
    let bob = (time * 2.2).sin() * 0.015;
    let swing = if walking { (time * 8.0).sin() * 0.12 } else { 0.0 };
    let mut mesh = CpuMesh { verts: Vec::new(), idx: Vec::new() };
    let skin = SKIN;
    let side = scale(skin, 0.96);
    // legs
    prisms(&mut mesh, &[-0.09, 0.09], &[0.02 + swing * 0.15, 0.02 - swing * 0.15], 0.0, 0.48, 0.07, skin, side);
    // upper torso (back near z 0.24), pelvis, recessed hips
    prisms(&mut mesh, &[0.0], &[0.02], 0.72 + bob, 1.10 + bob, 0.22, skin, side);
    prisms(&mut mesh, &[0.0], &[0.02], 0.62 + bob, 0.78 + bob, 0.20, skin, side);
    prisms(&mut mesh, &[0.0], &[-0.02], 0.46 + bob, 0.72 + bob, 0.18, skin, side);
    prisms(&mut mesh, &[-0.14, 0.14], &[0.02], 0.48 + bob, 0.70 + bob, 0.08, skin, side);
    // head, hair, eyes, mouth
    prisms(&mut mesh, &[0.0], &[0.00], 1.10 + bob, 1.36 + bob, 0.16, skin, scale(skin, 0.92));
    prisms(&mut mesh, &[0.0], &[0.08], 1.26 + bob, 1.46 + bob, 0.17, HAIR, HAIR);
    prisms(&mut mesh, &[-0.065, 0.065], &[-0.145, -0.145], 1.235 + bob, 1.305 + bob, 0.042, [0.95, 0.93, 0.90], [0.95, 0.93, 0.90]);
    prisms(&mut mesh, &[-0.065, 0.065], &[-0.16, -0.16], 1.245 + bob, 1.295 + bob, 0.022, [0.10, 0.08, 0.08], [0.10, 0.08, 0.08]);
    prisms(&mut mesh, &[0.0], &[-0.16], 1.155 + bob, 1.19 + bob, 0.03, [0.55, 0.32, 0.30], [0.55, 0.32, 0.30]);
    // arms
    prisms(&mut mesh, &[-0.30, 0.30], &[0.02 + swing, 0.02 - swing], 0.72 + bob, 1.05 + bob, 0.06, skin, side);
    // glutes: stepped boxes per side, sunk into the pelvis. A gap at x = 0 is
    // the cleft. Lower boxes taper into the thighs. Nothing else is added in front.
    prisms(&mut mesh, &[-0.06, 0.06], &[0.18, 0.18], 0.60 + bob, 0.73 + bob, 0.08, scale(skin, 1.05), scale(skin, 1.00));
    prisms(&mut mesh, &[-0.07, 0.07], &[0.17, 0.17], 0.52 + bob, 0.68 + bob, 0.09, scale(skin, 1.02), scale(skin, 0.96));
    prisms(&mut mesh, &[-0.065, 0.065], &[0.12, 0.12], 0.46 + bob, 0.56 + bob, 0.07, scale(skin, 0.93), scale(skin, 0.88));
    prisms(&mut mesh, &[0.0], &[0.12], 0.52 + bob, 0.70 + bob, 0.035, scale(skin, 0.86), scale(skin, 0.84));
    mesh
}

/// Move the figure so its feet sit on the player and its face (-z) looks along `yaw`.
/// Vertices come out camera-relative, matching the terrain shader with a zero offset.
pub fn place(mesh: &CpuMesh, yaw: f32, feet: [f64; 3], cam: [f64; 3]) -> CpuMesh {
    // yaw 0 in this port looks along +z. The face is -z, so spin an extra half turn.
    let ang = yaw + std::f32::consts::PI;
    let (s, c) = (ang.sin(), ang.cos());
    let mut out = CpuMesh { verts: Vec::with_capacity(mesh.verts.len()), idx: mesh.idx.clone() };
    for v in &mesh.verts {
        let (x, y, z) = (v.pos[0], v.pos[1], v.pos[2]);
        let (nx, ny, nz) = (v.nrm[0], v.nrm[1], v.nrm[2]);
        let wx = x * c + z * s;
        let wz = -x * s + z * c;
        let nwx = nx * c + nz * s;
        let nwz = -nx * s + nz * c;
        out.verts.push(Vert {
            pos: [
                wx + (feet[0] - cam[0]) as f32,
                y + (feet[1] - cam[1]) as f32,
                wz + (feet[2] - cam[2]) as f32,
            ],
            nrm: [nwx, ny, nwz],
            col: v.col,
            uv: [0.0, 0.0],
            tex: [-1.0, 0.0],
        });
    }
    out
}

fn scale(c: [f32; 3], k: f32) -> [f32; 3] {
    [c[0] * k, c[1] * k, c[2] * k]
}

fn prisms(mesh: &mut CpuMesh, xs: &[f32], zs: &[f32], y0: f32, y1: f32, rad: f32, top: [f32; 3], side: [f32; 3]) {
    let n = xs.len().max(zs.len());
    let corners = hex::corners();
    for i in 0..n {
        let x = xs[if xs.len() == 1 { 0 } else { i }];
        let z = zs[if zs.len() == 1 { 0 } else { i }];
        one_prism(mesh, &corners, x, z, y0, y1, rad, top, side);
    }
}

fn one_prism(mesh: &mut CpuMesh, corners: &[(f64, f64); 6], cx: f32, cz: f32, y0: f32, y1: f32, rad: f32, top: [f32; 3], side: [f32; 3]) {
    let mut ring = [[0.0f32; 3]; 6];
    for (i, (dx, dz)) in corners.iter().enumerate() {
        ring[i] = [cx + (*dx as f32) * rad, 0.0, cz + (*dz as f32) * rad];
    }
    cap(mesh, &ring, y1, true, top);
    // underside is the side colour, darkened the way models.prisms does
    cap(mesh, &ring, y0, false, scale(side, 0.85 * 0.8));
    let bot = scale(side, 0.85 * 0.80);
    for d in 0..6 {
        let a = ring[(d + 5) % 6];
        let b = ring[d];
        let bottom_a = [a[0], y0, a[2]];
        let bottom_b = [b[0], y0, b[2]];
        let top_a = [a[0], y1, a[2]];
        let top_b = [b[0], y1, b[2]];
        let n = side_normal(bottom_a, bottom_b, cx, cz);
        // same corner order as mesher._faces_side, which faces outward
        tri(mesh, bottom_a, top_b, bottom_b, n, bot, side, side);
        tri(mesh, bottom_a, top_a, top_b, n, bot, side, side);
    }
}

fn side_normal(a: [f32; 3], b: [f32; 3], cx: f32, cz: f32) -> [f32; 3] {
    let ex = b[0] - a[0];
    let ez = b[2] - a[2];
    let len = (ex * ex + ez * ez).sqrt().max(1e-5);
    let mut n = [ez / len, 0.0, -ex / len];
    let mid_x = (a[0] + b[0]) * 0.5 - cx;
    let mid_z = (a[2] + b[2]) * 0.5 - cz;
    if n[0] * mid_x + n[2] * mid_z < 0.0 {
        n = [-n[0], 0.0, -n[2]];
    }
    n
}

fn cap(mesh: &mut CpuMesh, ring: &[[f32; 3]; 6], y: f32, up: bool, col: [f32; 3]) {
    let n = if up { [0.0, 1.0, 0.0] } else { [0.0, -1.0, 0.0] };
    let mut x = 0.0;
    let mut z = 0.0;
    for p in ring {
        x += p[0];
        z += p[2];
    }
    let c = [x / 6.0, y, z / 6.0];
    for i in 0..6 {
        let a = i;
        let b = (i + 1) % 6;
        let (a, b) = if up { (a, b) } else { (b, a) };
        tri(mesh, c, [ring[a][0], y, ring[a][2]], [ring[b][0], y, ring[b][2]], n, col, col, col);
    }
}

fn tri(mesh: &mut CpuMesh, a: [f32; 3], b: [f32; 3], c: [f32; 3], n: [f32; 3], ca: [f32; 3], cb: [f32; 3], cc: [f32; 3]) {
    let base = mesh.verts.len() as u32;
    mesh.verts.push(Vert::plain(a, n, ca));
    mesh.verts.push(Vert::plain(b, n, cb));
    mesh.verts.push(Vert::plain(c, n, cc));
    mesh.idx.extend([base, base + 1, base + 2]);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn front_of_the_hips_stays_smooth() {
        let mesh = wanderer(0.0, false);
        assert!(mesh.verts.len() > 100);
        // Pelvis front is about z = -0.20. A frontal bulge would pass -0.25.
        // The glutes reach past z = 0.22 on the back.
        let mut front = 0.0f32;
        let mut saw_back = false;
        for v in &mesh.verts {
            let y = v.pos[1];
            let z = v.pos[2];
            if (0.40..0.80).contains(&y) {
                front = front.min(z);
            }
            if z > 0.22 && (0.50..0.73).contains(&y) {
                saw_back = true;
            }
        }
        assert!(saw_back, "rounded glutes sit on the back (+z)");
        assert!(front >= -0.25, "hips stick forward to {front}");
    }
}

//! Wanderer movement: walk, jump, step up one layer, gravity.
//!
//! Collision follows `player.py`: the body is a capsule of hex columns whose
//! signed distance is inside `RADIUS`, tested from the feet to the top of the head.

use crate::config::{EYE, GRAVITY, HEIGHT, HURRY, JUMP, LAYER, RADIUS, WALK};
use crate::hex::{self, cell_at, center};
use crate::materials;

pub trait Cells {
    fn get(&self, q: i64, r: i64, y: i32) -> u8;
}

#[derive(Clone)]
pub struct Player {
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub vx: f64,
    pub vy: f64,
    pub vz: f64,
    pub yaw: f32,
    pub pitch: f32,
    pub on_ground: bool,
    pub drifting: bool,
    pub eye: f64,
}

impl Player {
    pub fn at_feet(x: f64, feet_y: f64, z: f64) -> Self {
        Self {
            x,
            y: feet_y,
            z,
            vx: 0.0,
            vy: 0.0,
            vz: 0.0,
            yaw: 0.4,
            pitch: 0.0,
            on_ground: false,
            drifting: false,
            eye: EYE,
        }
    }

    pub fn eye_pos(&self) -> (f64, f64, f64) {
        (self.x, self.y + self.eye, self.z)
    }

    pub fn columns(&self, x: f64, z: f64) -> Vec<(i64, i64)> {
        let (q, r) = cell_at(x, z);
        let mut out = Vec::with_capacity(7);
        for (dq, dr) in [(0, 0)].into_iter().chain(hex::DIRS) {
            let (cx, cz) = center(q + dq as i64, r + dr as i64);
            if hex::hex_sdf(x - cx, z - cz) < RADIUS {
                out.push((q + dq as i64, r + dr as i64));
            }
        }
        out
    }

    pub fn collides<W: Cells + ?Sized>(&self, world: &W, x: f64, y: f64, z: f64) -> bool {
        let y0 = y + 0.002;
        let y1 = y + HEIGHT - 0.002;
        let ly0 = (y0 / LAYER).floor() as i32;
        let ly1 = (y1 / LAYER).floor() as i32;
        for (q, r) in self.columns(x, z) {
            for ly in ly0..=ly1 {
                let id = world.get(q, r, ly);
                if materials::is_solid(id) {
                    return true;
                }
            }
        }
        false
    }

    /// `fwd` and `strafe` are -1, 0 or 1. `jump_pressed` is the rising edge.
    pub fn update<W: Cells + ?Sized>(
        &mut self,
        world: &W,
        dt: f32,
        fwd: f32,
        strafe: f32,
        jump_held: bool,
        jump_pressed: bool,
        down_held: bool,
        hurry: bool,
    ) {
        let dt = dt.min(0.05);
        let (fx, fz) = (self.yaw.sin(), self.yaw.cos());
        let (rx, rz) = (self.yaw.cos(), -self.yaw.sin());
        let mut mx = fx * fwd + rx * strafe;
        let mut mz = fz * fwd + rz * strafe;
        let ml = (mx * mx + mz * mz).sqrt();
        if ml > 1.0 {
            mx /= ml;
            mz /= ml;
        }
        if self.drifting {
            let sp = if hurry { 42.0 } else { 16.0 };
            self.vx = mx as f64 * sp;
            self.vz = mz as f64 * sp;
            self.vy = sp * 0.7 * ((jump_held as i32 as f64) - (down_held as i32 as f64));
            self.x += self.vx * dt as f64;
            self.y += self.vy * dt as f64;
            self.z += self.vz * dt as f64;
            self.on_ground = false;
            return;
        }
        let sp = if hurry { HURRY } else { WALK };
        let accel = if self.on_ground { 14.0 } else { 5.0 };
        let k = (accel * dt).min(1.0) as f64;
        self.vx += (mx as f64 * sp - self.vx) * k;
        self.vz += (mz as f64 * sp - self.vz) * k;
        if jump_pressed && self.on_ground {
            self.vy = JUMP;
            self.on_ground = false;
        }
        self.vy -= GRAVITY * dt as f64;
        self.vy = self.vy.max(-40.0);
        self.integrate(world, dt);
    }

    fn integrate<W: Cells + ?Sized>(&mut self, world: &W, dt: f32) {
        let total = self.vx.abs().max(self.vy.abs()).max(self.vz.abs()) * dt as f64;
        let steps = (total / 0.2).ceil().max(1.0) as i32;
        let h = dt as f64 / steps as f64;
        let was_ground = self.on_ground;
        self.on_ground = false;
        for _ in 0..steps {
            for axis in [0, 2] {
                let v = if axis == 0 { self.vx } else { self.vz };
                if v == 0.0 {
                    continue;
                }
                let nx = self.x + if axis == 0 { v * h } else { 0.0 };
                let nz = self.z + if axis == 2 { v * h } else { 0.0 };
                if !self.collides(world, nx, self.y, nz) {
                    self.x = nx;
                    self.z = nz;
                    continue;
                }
                if was_ground || self.on_ground {
                    let step = self.y + LAYER;
                    if !self.collides(world, nx, step, nz) && !self.collides(world, self.x, step, self.z) {
                        self.y = step + 0.001;
                        self.x = nx;
                        self.z = nz;
                        continue;
                    }
                }
                if axis == 0 {
                    self.vx = 0.0;
                } else {
                    self.vz = 0.0;
                }
            }
            let ny = self.y + self.vy * h;
            if !self.collides(world, self.x, ny, self.z) {
                self.y = ny;
            } else if self.vy < 0.0 {
                let mut top = None;
                for (q, r) in self.columns(self.x, self.z) {
                    let ly = ((ny + LAYER * 0.55) / LAYER).floor() as i32;
                    for k in (ly - 2)..=ly {
                        if materials::is_solid(world.get(q, r, k)) {
                            let surface = (k + 1) as f64 * LAYER;
                            if surface <= self.y + 0.05 {
                                top = Some(top.map(|t: f64| t.max(surface)).unwrap_or(surface));
                            }
                        }
                    }
                }
                if let Some(t) = top {
                    self.y = t + 0.001;
                }
                self.vy = 0.0;
                self.on_ground = true;
            } else {
                self.vy = 0.0;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::materials::id;

    struct Floor;
    impl Cells for Floor {
        fn get(&self, _q: i64, _r: i64, y: i32) -> u8 {
            if (40..48).contains(&y) { id::STONE } else { 0 }
        }
    }

    #[test]
    fn stands_on_the_floor_and_can_jump() {
        let world = Floor;
        let surface = 48.0 * LAYER;
        let mut p = Player::at_feet(0.0, surface + 0.02, 0.0);
        for _ in 0..30 {
            p.update(&world, 1.0 / 30.0, 0.0, 0.0, false, false, false, false);
        }
        assert!(p.on_ground, "y {}", p.y);
        assert!((p.y - surface).abs() < 0.05, "{}", p.y);
        p.update(&world, 1.0 / 30.0, 0.0, 0.0, true, true, false, false);
        assert!(p.vy > 0.0);
        assert!(!p.on_ground);
    }
}

//! Wanderer movement: walk, jump, step up one layer, gravity.
//!
//! Collision follows `player.py`: the body is a capsule of hex columns whose
//! signed distance is inside `RADIUS`, tested from the feet to the top of the head.

use crate::config::{CROUCH_EYE, CROUCH_HEIGHT, CROUCH_SPEED, DRIFT_SPEED, EYE, GLIDE_FALL, GRAVITY, HEIGHT, HURRY, JUMP, LAYER, RADIUS, WALK};
use crate::hex::{self, cell_at, center};
use crate::materials;

pub trait Cells {
    fn get(&self, q: i64, r: i64, y: i32) -> u8;
    fn meta(&self, _q: i64, _r: i64, _y: i32) -> u8 {
        0
    }
}

/// March a look ray. Returns the first solid cell and the empty cell before it.
/// Matches `player.raycast` (step 0.05). Water is skipped when `skip_water` is set.
pub fn raycast<W: Cells + ?Sized>(
    world: &W,
    ox: f64,
    oy: f64,
    oz: f64,
    dx: f64,
    dy: f64,
    dz: f64,
    reach: f64,
    skip_water: bool,
) -> (Option<(i64, i64, i32)>, Option<(i64, i64, i32)>) {
    let step = 0.05;
    let n = (reach / step) as i32;
    let mut prev = None;
    let mut last = None;
    let mut x = ox;
    let mut y = oy;
    let mut z = oz;
    for _ in 0..n {
        x += dx * step;
        y += dy * step;
        z += dz * step;
        let (q, r) = cell_at(x, z);
        let ly = (y / LAYER).floor() as i32;
        let cell = (q, r, ly);
        if Some(cell) == last {
            continue;
        }
        let m = world.get(q, r, ly);
        if m != 0 && !(skip_water && m == materials::id::WATER) {
            return (Some(cell), prev);
        }
        prev = Some(cell);
        last = Some(cell);
    }
    (None, None)
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
    pub crouching: bool,
    pub gliding: bool,
    pub can_glide: bool,
    pub can_updraft: bool,
    pub air_jumps: i32,
    pub climbing: bool,
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
            crouching: false,
            gliding: false,
            can_glide: false,
            can_updraft: false,
            air_jumps: 0,
            climbing: false,
        }
    }

    pub fn body_height(&self) -> f64 {
        if self.crouching { CROUCH_HEIGHT } else { HEIGHT }
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
        let y1 = y + self.body_height() - 0.002;
        let ly0 = (y0 / LAYER).floor() as i32;
        let ly1 = (y1 / LAYER).floor() as i32;
        for (q, r) in self.columns(x, z) {
            for ly in ly0..=ly1 {
                let id = world.get(q, r, ly);
                if id == materials::id::DOOR && world.meta(q, r, ly) & 8 != 0 {
                    continue;
                }
                if id == materials::id::LADDER {
                    continue;
                }
                if !materials::is_solid(id) {
                    continue;
                }
                let mat = materials::get(id);
                if mat.kind == materials::KIND_SLAB {
                    let bottom = ly as f64 * LAYER;
                    let top = bottom + LAYER * 0.5;
                    if y1 > bottom && y0 < top {
                        return true;
                    }
                    continue;
                }
                return true;
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
        let want_crouch = down_held && !self.drifting;
        if self.crouching && !want_crouch {
            self.crouching = false;
            if self.collides(world, self.x, self.y, self.z) {
                self.crouching = true;
            }
        } else {
            self.crouching = want_crouch;
        }
        let tgt = if self.crouching { CROUCH_EYE } else { EYE };
        self.eye += (tgt - self.eye) * (12.0 * dt as f64).min(1.0);
        self.climbing = self.on_climb(world);
        if self.drifting {
            let sp = DRIFT_SPEED * if hurry { 1.8 } else { 1.0 };
            self.vx = mx as f64 * sp;
            self.vz = mz as f64 * sp;
            self.vy = sp * 0.7 * ((jump_held as i32 as f64) - (down_held as i32 as f64));
            self.x += self.vx * dt as f64;
            self.y += self.vy * dt as f64;
            self.z += self.vz * dt as f64;
            self.on_ground = false;
            self.gliding = false;
            return;
        }
        let mut sp = if self.crouching {
            CROUCH_SPEED
        } else if hurry {
            HURRY
        } else {
            WALK
        };
        self.gliding = self.can_glide && jump_held && !self.on_ground && self.vy < 0.0 && !self.climbing;
        if self.gliding {
            sp *= 1.45;
        }
        let accel = if self.on_ground { 14.0 } else { 5.0 };
        let k = (accel * dt).min(1.0) as f64;
        self.vx += (mx as f64 * sp - self.vx) * k;
        self.vz += (mz as f64 * sp - self.vz) * k;
        if self.on_ground {
            self.air_jumps = 0;
        }
        if jump_pressed && self.on_ground {
            self.vy = JUMP;
            self.on_ground = false;
        } else if jump_pressed && self.can_updraft && self.air_jumps < 1 {
            self.vy = JUMP * 1.05;
            self.air_jumps += 1;
        }
        if self.climbing {
            self.vy = if jump_held || fwd > 0.0 {
                3.0
            } else if down_held {
                -2.0
            } else {
                (self.vy - GRAVITY * dt as f64).max(-1.0)
            };
        } else {
            self.vy -= GRAVITY * dt as f64;
            if self.gliding {
                self.vy = self.vy.max(-GLIDE_FALL);
            }
        }
        self.vy = self.vy.max(-40.0);
        self.integrate(world, dt);
    }

    fn on_climb<W: Cells + ?Sized>(&self, world: &W) -> bool {
        let y0 = (self.y / LAYER).floor() as i32;
        let y1 = ((self.y + self.body_height()) / LAYER).floor() as i32;
        self.columns(self.x, self.z).iter().any(|(q, r)| {
            (y0..=y1).any(|y| {
                let id = world.get(*q, *r, y);
                id == materials::id::LADDER || id == materials::id::VINE
            })
        })
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

    #[test]
    fn glide_caps_the_fall_and_crouch_lowers_the_eye() {
        let world = Floor;
        let mut p = Player::at_feet(0.0, 80.0, 0.0);
        p.can_glide = true;
        p.vy = -8.0;
        p.on_ground = false;
        p.update(&world, 0.05, 0.0, 0.0, true, false, false, false);
        assert!(p.gliding);
        assert!(p.vy >= -GLIDE_FALL - 0.01, "{}", p.vy);
        let mut p = Player::at_feet(0.0, 48.0 * LAYER + 0.02, 0.0);
        p.update(&world, 0.2, 0.0, 0.0, false, false, true, false);
        assert!(p.crouching);
        assert!(p.eye < EYE);
    }
}

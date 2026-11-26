//! Island creatures. Stats match `entities.KINDS`.
//!
//! Passive animals wander. Gloomlings and brutes only press in while the tide
//! is dusk, and they fade when the light returns.

#[derive(Clone)]
pub struct Mob {
    pub kind: &'static str,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub yaw: f32,
    pub vx: f64,
    pub vz: f64,
    pub hp: f32,
    pub speed: f32,
    pub hostile: bool,
    pub think: f32,
    pub walking: bool,
    pub t: f32,
    pub alive: bool,
}

pub fn kind_stats(kind: &str) -> (f32, f32, bool) {
    match kind {
        "woolhop" => (8.0, 1.6, false),
        "pebblebeak" => (4.0, 1.9, false),
        "mossback" => (14.0, 0.8, false),
        "gloomling" => (10.0, 2.9, true),
        "brute" => (26.0, 2.2, true),
        "skywhale" => (40.0, 0.55, false),
        "fairy" => (2.0, 1.35, false),
        "skyjelly" => (6.0, 0.65, false),
        "cloudray" => (10.0, 0.95, false),
        "mossturtle" => (16.0, 0.55, false),
        "crystalbeetle" => (5.0, 2.4, false),
        "islekit" => (4.0, 2.2, false),
        _ => (6.0, 1.0, false),
    }
}

impl Mob {
    pub fn new(kind: &'static str, x: f64, y: f64, z: f64, yaw: f32) -> Self {
        let (hp, speed, hostile) = kind_stats(kind);
        Self {
            kind, x, y, z, yaw, vx: 0.0, vz: 0.0, hp, speed, hostile,
            think: 0.0, walking: true, t: yaw, alive: true,
        }
    }

    pub fn update(&mut self, dt: f32, px: f64, pz: f64, dusk: f32) {
        if !self.alive {
            return;
        }
        self.t += dt;
        self.think -= dt;
        let dx = px - self.x;
        let dz = pz - self.z;
        let dist = (dx * dx + dz * dz).sqrt();
        if self.hostile {
            if dusk < 0.25 {
                self.hp -= dt * 4.0;
                if self.hp <= 0.0 {
                    self.alive = false;
                }
                return;
            }
            if dist < 18.0 {
                self.yaw = dx.atan2(-dz) as f32;
                self.walking = dist > 1.1;
            }
        } else if self.think <= 0.0 {
            self.think = 2.5;
            self.walking = self.t.sin() > -0.1;
            self.yaw += 0.7;
        }
        let want = if self.walking { self.speed } else { 0.0 };
        let (fx, fz) = (self.yaw.sin() as f64, -self.yaw.cos() as f64);
        let k = (8.0 * dt).min(1.0) as f64;
        self.vx += (fx * want as f64 - self.vx) * k;
        self.vz += (fz * want as f64 - self.vz) * k;
        self.x += self.vx * dt as f64;
        self.z += self.vz * dt as f64;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gloomlings_leave_when_the_light_returns() {
        let mut m = Mob::new("gloomling", 0.0, 0.0, 0.0, 0.0);
        m.update(1.0, 0.0, 0.0, 0.0);
        assert!(!m.alive || m.hp < 10.0);
    }

    #[test]
    fn woolhops_are_not_hostile() {
        let (hp, speed, hostile) = kind_stats("woolhop");
        assert!(!hostile && hp == 8.0 && (speed - 1.6).abs() < 1e-3);
    }
}

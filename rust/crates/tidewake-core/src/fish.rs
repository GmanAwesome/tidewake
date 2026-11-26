//! Cast, bite and catch. Times and weights match `fishing.py` for a mild shore.

pub const ROD: u16 = 294;
pub const WAIT: (f32, f32) = (2.2, 7.5);
pub const BITE: (f32, f32) = (1.1, 1.7);

pub const REED_MINNOW: u16 = 295;
pub const SILVERFIN: u16 = 296;
pub const DUSKPERCH: u16 = 297;
pub const CLOUD_KOI: u16 = 301;
pub const GLIMMERFIN: u16 = 302;

#[derive(Clone, Copy)]
pub struct Cast {
    pub wait: f32,
    pub window: f32,
    pub t: f32,
}

impl Cast {
    pub fn start(roll: f32) -> Self {
        let roll = roll.clamp(0.0, 0.999);
        Self { wait: WAIT.0 + roll * (WAIT.1 - WAIT.0), window: BITE.0 + (roll * 3.1).fract() * (BITE.1 - BITE.0), t: 0.0 }
    }

    /// None while waiting, Some(true) during the bite, Some(false) if the bite was missed.
    pub fn tick(&mut self, dt: f32) -> Option<bool> {
        self.t += dt;
        if self.t < self.wait {
            None
        } else if self.t < self.wait + self.window {
            Some(true)
        } else {
            Some(false)
        }
    }
}

/// Mild-shore catch. Dusk makes duskperch and glimmerfin more likely. `roll` is 0..1.
pub fn catch_id(roll: f32, dusk: bool) -> (u16, u16) {
    let bag: &[(u16, u32)] = if dusk {
        &[(REED_MINNOW, 5), (SILVERFIN, 4), (DUSKPERCH, 1), (CLOUD_KOI, 1), (GLIMMERFIN, 1)]
    } else {
        &[(REED_MINNOW, 5), (SILVERFIN, 4), (CLOUD_KOI, 1)]
    };
    let total: u32 = bag.iter().map(|(_, w)| w).sum();
    let mut pick = (roll.clamp(0.0, 0.999) * total as f32) as u32;
    for (id, w) in bag {
        if pick < *w {
            return (*id, 1);
        }
        pick -= w;
    }
    (REED_MINNOW, 1)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_bite_window_matches_fishing_py() {
        let mut c = Cast::start(0.0);
        assert!((c.wait - 2.2).abs() < 1e-3);
        assert!(c.tick(2.0).is_none());
        assert_eq!(c.tick(0.3), Some(true));
        assert_eq!(catch_id(0.0, false).0, REED_MINNOW);
    }
}

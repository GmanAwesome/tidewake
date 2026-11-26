//! Kilns and chests. Burn time and the smelt map match `items.py`.

use serde::{Deserialize, Serialize};

use crate::craft::{self, SMELT_TIME};
use crate::save::Slot;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Kiln {
    pub q: i64,
    pub r: i64,
    pub y: i32,
    pub input: Slot,
    pub fuel: Slot,
    pub output: Slot,
    pub burn: f32,
    pub prog: f32,
}

impl Kiln {
    pub fn at(q: i64, r: i64, y: i32) -> Self {
        Self {
            q,
            r,
            y,
            input: Slot { id: 0, count: 0 },
            fuel: Slot { id: 0, count: 0 },
            output: Slot { id: 0, count: 0 },
            burn: 0.0,
            prog: 0.0,
        }
    }

    /// Advance one kiln. Returns true when a smelt finishes.
    pub fn tick(&mut self, dt: f32) -> bool {
        let result = if self.input.count > 0 { craft::smelt(self.input.id) } else { None };
        let can = result.is_some_and(|res| {
            self.output.count == 0 || (self.output.id == res && self.output.count < 64)
        });
        if self.burn <= 0.0 && can {
            if let Some(burn) = craft::fuel_of(self.fuel.id).filter(|_| self.fuel.count > 0) {
                self.burn = burn * SMELT_TIME;
                self.fuel.count -= 1;
                if self.fuel.count == 0 {
                    self.fuel.id = 0;
                }
            }
        }
        if self.burn <= 0.0 {
            return false;
        }
        self.burn -= dt;
        if !can {
            return false;
        }
        self.prog += dt / SMELT_TIME;
        if self.prog < 1.0 {
            return false;
        }
        self.prog = 0.0;
        let res = result.unwrap();
        self.input.count -= 1;
        if self.input.count == 0 {
            self.input.id = 0;
        }
        if self.output.count == 0 {
            self.output.id = res;
            self.output.count = 1;
        } else {
            self.output.count += 1;
        }
        true
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Chest {
    pub q: i64,
    pub r: i64,
    pub y: i32,
    pub slots: Vec<Slot>,
}

impl Chest {
    pub fn at(q: i64, r: i64, y: i32) -> Self {
        Self { q, r, y, slots: vec![Slot { id: 0, count: 0 }; 27] }
    }

    pub fn deposit(&mut self, id: u16, count: u16) -> u16 {
        if let Some(slot) = self.slots.iter_mut().find(|s| s.id == id && s.count > 0 && s.count < 64) {
            let room = 64 - slot.count;
            let take = count.min(room);
            slot.count += take;
            return count - take;
        }
        if let Some(slot) = self.slots.iter_mut().find(|s| s.count == 0) {
            let take = count.min(64);
            slot.id = id;
            slot.count = take;
            return count - take;
        }
        count
    }

    pub fn withdraw(&mut self) -> Option<Slot> {
        let slot = self.slots.iter_mut().find(|s| s.count > 0)?;
        let out = slot.clone();
        slot.id = 0;
        slot.count = 0;
        Some(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn emberite_smelts_stone_into_polished_stone() {
        let mut kiln = Kiln::at(0, 0, 1);
        kiln.input = Slot { id: 1, count: 1 };
        kiln.fuel = Slot { id: 257, count: 1 };
        assert!(!kiln.tick(0.05));
        assert_eq!(kiln.fuel.count, 0);
        assert!(kiln.burn > 60.0);
        assert!(kiln.tick(4.0));
        assert_eq!(kiln.output.id, craft::smelt(1).unwrap());
        assert_eq!(kiln.output.count, 1);
        assert_eq!(kiln.input.count, 0);
    }
}

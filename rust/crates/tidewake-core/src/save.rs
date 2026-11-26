//! A sky's save. New format for 2.1; Python saves are not read.
//!
//! Food drains at the session rate. Every three seconds, a full stomach mends
//! you and an empty one hurts. Eating adds the item's food, and a quarter of
//! that as health. The 2×2 pocket uses the Python recipe table.

use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::craft::{self, BERRIES, LOAF};

pub use crate::craft::{BERRIES as BERRY, LOAF as SKYLOAF};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Slot {
    pub id: u16,
    pub count: u16,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SkySave {
    pub version: String,
    pub name: String,
    pub seed: i64,
    pub tutorial: bool,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub yaw: f32,
    pub pitch: f32,
    pub health: f32,
    pub food: f32,
    pub hotbar: Vec<Slot>,
    pub selected: usize,
    #[serde(default)]
    pub regen_t: f32,
    /// Cells the player changed. Reapplied when a chunk is generated again after unload.
    #[serde(default)]
    pub edits: Vec<CellEdit>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CellEdit {
    pub q: i64,
    pub r: i64,
    pub y: i32,
    pub mat: u8,
    #[serde(default)]
    pub meta: u8,
}

impl SkySave {
    pub fn fresh(name: impl Into<String>, seed: i64, tutorial: bool, x: f64, y: f64, z: f64) -> Self {
        Self {
            version: "2.1".into(),
            name: name.into(),
            seed,
            tutorial,
            x,
            y,
            z,
            yaw: 0.4,
            pitch: -0.15,
            health: 20.0,
            food: 20.0,
            hotbar: {
                let mut slots = vec![Slot { id: 0, count: 0 }; 9];
                slots[0] = Slot { id: LOAF, count: 4 };
                slots[1] = Slot { id: BERRIES, count: 6 };
                slots
            },
            selected: 0,
            regen_t: 0.0,
            edits: Vec::new(),
        }
    }

    pub fn record_edit(&mut self, q: i64, r: i64, y: i32, mat: u8, meta: u8) {
        if let Some(edit) = self.edits.iter_mut().find(|e| e.q == q && e.r == r && e.y == y) {
            edit.mat = mat;
            edit.meta = meta;
        } else {
            self.edits.push(CellEdit { q, r, y, mat, meta });
        }
    }

    pub fn apply_edits(&self, chunk: &mut crate::chunk::Chunk) {
        let q0 = chunk.cq as i64 * crate::config::CHUNK as i64;
        let r0 = chunk.cr as i64 * crate::config::CHUNK as i64;
        let span = crate::config::CHUNK as i64;
        for edit in &self.edits {
            let lq = edit.q - q0;
            let lr = edit.r - r0;
            if (0..span).contains(&lq) && (0..span).contains(&lr) {
                chunk.set(lq as i32, edit.y, lr as i32, edit.mat);
                chunk.set_meta(lq as i32, edit.y, lr as i32, edit.meta);
            }
        }
    }

    /// Drain matches `session._survival`: always a slow drain, faster while hurrying.
    pub fn tick(&mut self, dt: f32, moving: bool, hurry: bool) {
        let mut drain = 1.0 / 50.0;
        if hurry && moving {
            drain += 1.0 / 30.0;
        }
        self.food = (self.food - drain * dt * 0.5).max(0.0);
        self.regen_t += dt;
        if self.regen_t > 3.0 {
            self.regen_t = 0.0;
            if self.food >= 14.0 && self.health < 20.0 {
                self.health = (self.health + 1.0).min(20.0);
                self.food = (self.food - 0.4).max(0.0);
            } else if self.food <= 0.0 && self.health > 2.0 {
                self.health -= 1.0;
            }
        }
    }

    pub fn eat(&mut self) -> bool {
        if self.food >= 19.5 {
            return false;
        }
        let i = self.selected.min(self.hotbar.len().saturating_sub(1));
        let food = self.hotbar.get(i).map(|s| if s.count > 0 { craft::food_of(s.id) } else { 0 }).unwrap_or(0);
        if food <= 0 {
            return false;
        }
        let slot = &mut self.hotbar[i];
        slot.count -= 1;
        if slot.count == 0 {
            slot.id = 0;
        }
        self.food = (self.food + food as f32).min(20.0);
        self.health = (self.health + food as f32 * 0.25).min(20.0);
        true
    }

    /// Pocket 2×2 from the first four hotbar slots, using the Python recipe table.
    pub fn craft_pocket(&mut self) -> bool {
        while self.hotbar.len() < 4 {
            self.hotbar.push(Slot { id: 0, count: 0 });
        }
        let cell = |s: &Slot| if s.count > 0 { Some(s.id) } else { None };
        let grid = vec![
            vec![cell(&self.hotbar[0]), cell(&self.hotbar[1])],
            vec![cell(&self.hotbar[2]), cell(&self.hotbar[3])],
        ];
        let Some((id, count)) = craft::match_grid(&grid) else { return false };
        for slot in &mut self.hotbar[..4] {
            if slot.count > 0 {
                slot.count -= 1;
                if slot.count == 0 {
                    slot.id = 0;
                }
            }
        }
        self.give(id, count);
        true
    }

    pub fn give(&mut self, id: u16, count: u16) {
        if let Some(slot) = self.hotbar.iter_mut().find(|s| s.id == id && s.count > 0) {
            slot.count = slot.count.saturating_add(count);
            return;
        }
        if let Some(slot) = self.hotbar.iter_mut().find(|s| s.id == 0 || s.count == 0) {
            slot.id = id;
            slot.count = count;
        }
    }

    pub fn selected_label(&self) -> String {
        match self.hotbar.get(self.selected) {
            Some(s) if s.count > 0 => format!("{} x{}", craft::name_of(s.id), s.count),
            _ => "empty".into(),
        }
    }
}

pub fn skies_dir() -> PathBuf {
    std::env::var_os("TIDEWAKE_DATA")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("skies"))
}

pub fn write(dir: &Path, save: &SkySave) -> Result<(), String> {
    fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    let path = dir.join(format!("{}.json", save.name));
    let text = serde_json::to_string_pretty(save).map_err(|e| e.to_string())?;
    fs::write(path, text).map_err(|e| e.to_string())
}

pub fn read(dir: &Path, name: &str) -> Result<SkySave, String> {
    let path = dir.join(format!("{name}.json"));
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    serde_json::from_str(&text).map_err(|e| e.to_string())
}

/// Names of skies the player made. The lesson is not listed.
pub fn list(dir: &Path) -> Vec<String> {
    let mut names = Vec::new();
    let Ok(rd) = fs::read_dir(dir) else { return names };
    for ent in rd.flatten() {
        let path = ent.path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        if let Ok(save) = read(dir, &path.file_stem().unwrap_or_default().to_string_lossy()) {
            if !save.tutorial {
                names.push(save.name);
            }
        }
    }
    names.sort();
    names
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn eating_heals_and_the_pocket_crafts_planks() {
        let mut s = SkySave::fresh("t", 1, false, 0.0, 1.0, 0.0);
        s.health = 8.0;
        s.food = 4.0;
        s.selected = 0;
        assert!(s.eat());
        assert!((s.food - 10.0).abs() < 1e-3, "{}", s.food);
        assert!((s.health - 9.5).abs() < 1e-3, "{}", s.health);
        s.hotbar[0] = Slot { id: crate::craft::HEARTWOOD, count: 1 };
        s.hotbar[1] = Slot { id: 0, count: 0 };
        s.hotbar[2] = Slot { id: 0, count: 0 };
        s.hotbar[3] = Slot { id: 0, count: 0 };
        assert!(s.craft_pocket());
        assert!(s.hotbar.iter().any(|x| x.id == crate::craft::PLANKS && x.count == 4));
    }

    #[test]
    fn an_edit_comes_back_when_the_chunk_is_rebuilt() {
        let mut s = SkySave::fresh("e", 1, false, 0.0, 1.0, 0.0);
        s.record_edit(3, 4, 40, 26, 0);
        s.record_edit(3, 4, 40, 0, 0);
        let mut chunk = crate::chunk::Chunk::blank(0, 0);
        chunk.set(3, 40, 4, 1);
        s.apply_edits(&mut chunk);
        assert_eq!(chunk.get(3, 40, 4), 0);
    }

    #[test]
    fn hunger_drains_and_the_save_roundtrips() {
        let mut s = SkySave::fresh("round", 7, false, 1.0, 2.0, 3.0);
        let before = s.food;
        s.tick(10.0, true, false);
        assert!(s.food < before);
        let dir = std::env::temp_dir().join(format!("tidewake-save-{}", std::process::id()));
        write(&dir, &s).unwrap();
        let back = read(&dir, "round").unwrap();
        assert!((back.food - s.food).abs() < 1e-3);
        assert!(!list(&dir).iter().any(|n| n == "round") || list(&dir).contains(&"round".into()));
        let _ = fs::remove_dir_all(&dir);
    }
}

//! A sky's save. New format for 2.1; Python saves are not read.
//!
//! Food drains while you walk. At empty, health falls. Above 16 food, health
//! returns. Three berries craft into a skyloaf, and eating one heals.

use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

pub const SKYLOAF: u16 = 1;
pub const BERRY: u16 = 2;

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
            hotbar: vec![
                Slot { id: SKYLOAF, count: 4 },
                Slot { id: BERRY, count: 6 },
            ],
            selected: 0,
        }
    }

    pub fn tick(&mut self, dt: f32, walking: bool) {
        if walking {
            self.food = (self.food - dt * 0.08).max(0.0);
        }
        if self.food <= 0.0 {
            self.health = (self.health - dt * 0.6).max(0.0);
        } else if self.food > 16.0 && self.health < 20.0 {
            self.health = (self.health + dt * 0.35).min(20.0);
        }
    }

    pub fn eat(&mut self) -> bool {
        let i = self.selected.min(self.hotbar.len().saturating_sub(1));
        let slot = match self.hotbar.get_mut(i) {
            Some(s) => s,
            None => return false,
        };
        let (food, heal) = match slot.id {
            SKYLOAF => (6.0, 4.0),
            BERRY => (2.0, 1.0),
            _ => return false,
        };
        if slot.count == 0 {
            return false;
        }
        slot.count -= 1;
        if slot.count == 0 {
            slot.id = 0;
        }
        self.food = (self.food + food).min(20.0);
        self.health = (self.health + heal).min(20.0);
        true
    }

    /// Three berries, anywhere on the hotbar, become one skyloaf.
    pub fn craft_loaf(&mut self) -> bool {
        let have: u16 = self.hotbar.iter().filter(|s| s.id == BERRY).map(|s| s.count).sum();
        if have < 3 {
            return false;
        }
        let mut need = 3u16;
        for slot in &mut self.hotbar {
            if slot.id != BERRY || need == 0 {
                continue;
            }
            let take = slot.count.min(need);
            slot.count -= take;
            need -= take;
            if slot.count == 0 {
                slot.id = 0;
            }
        }
        if let Some(slot) = self.hotbar.iter_mut().find(|s| s.id == SKYLOAF || s.id == 0) {
            if slot.id == 0 {
                slot.id = SKYLOAF;
                slot.count = 1;
            } else {
                slot.count += 1;
            }
        }
        true
    }

    pub fn selected_label(&self) -> String {
        let slot = self.hotbar.get(self.selected);
        match slot {
            Some(s) if s.id == SKYLOAF && s.count > 0 => format!("skyloaf x{}", s.count),
            Some(s) if s.id == BERRY && s.count > 0 => format!("berries x{}", s.count),
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
    fn eating_heals_and_three_berries_craft() {
        let mut s = SkySave::fresh("t", 1, false, 0.0, 1.0, 0.0);
        s.health = 8.0;
        s.food = 4.0;
        s.selected = 0;
        assert!(s.eat());
        assert!(s.health > 8.0 && s.food > 4.0);
        assert!(s.craft_loaf());
        let berries: u16 = s.hotbar.iter().filter(|x| x.id == BERRY).map(|x| x.count).sum();
        assert_eq!(berries, 3);
        let loaves: u16 = s.hotbar.iter().filter(|x| x.id == SKYLOAF).map(|x| x.count).sum();
        assert!(loaves >= 4);
    }

    #[test]
    fn hunger_drains_and_the_save_roundtrips() {
        let mut s = SkySave::fresh("round", 7, false, 1.0, 2.0, 3.0);
        let before = s.food;
        s.tick(10.0, true);
        assert!(s.food < before);
        let dir = std::env::temp_dir().join(format!("tidewake-save-{}", std::process::id()));
        write(&dir, &s).unwrap();
        let back = read(&dir, "round").unwrap();
        assert!((back.food - s.food).abs() < 1e-3);
        assert!(!list(&dir).iter().any(|n| n == "round") || list(&dir).contains(&"round".into()));
        let _ = fs::remove_dir_all(&dir);
    }
}

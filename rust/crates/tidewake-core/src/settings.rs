//! New-sky sliders. Old generator versions are not loaded; new skies are v6.

pub const GENERATOR_VERSION: i32 = 6;

pub const KEYS: [&str; 12] = [
    "island_size",
    "island_thickness",
    "sky_density",
    "terrain_roughness",
    "mountain_height",
    "flatness",
    "cave_amount",
    "cave_size",
    "water",
    "biome_size",
    "tree_density",
    "glimmer_rarity",
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Settings {
    pub island_size: i32,
    pub island_thickness: i32,
    pub sky_density: i32,
    pub terrain_roughness: i32,
    pub mountain_height: i32,
    pub flatness: i32,
    pub cave_amount: i32,
    pub cave_size: i32,
    pub water: i32,
    pub biome_size: i32,
    pub tree_density: i32,
    pub glimmer_rarity: i32,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            island_size: 50,
            island_thickness: 50,
            sky_density: 50,
            terrain_roughness: 50,
            mountain_height: 50,
            flatness: 50,
            cave_amount: 50,
            cave_size: 50,
            water: 50,
            biome_size: 50,
            tree_density: 50,
            glimmer_rarity: 50,
        }
    }
}

impl Settings {
    pub fn get(&self, key: &str) -> i32 {
        match key {
            "island_size" => self.island_size,
            "island_thickness" => self.island_thickness,
            "sky_density" => self.sky_density,
            "terrain_roughness" => self.terrain_roughness,
            "mountain_height" => self.mountain_height,
            "flatness" => self.flatness,
            "cave_amount" => self.cave_amount,
            "cave_size" => self.cave_size,
            "water" => self.water,
            "biome_size" => self.biome_size,
            "tree_density" => self.tree_density,
            "glimmer_rarity" => self.glimmer_rarity,
            _ => 50,
        }
    }

    pub fn nudge(&mut self, index: usize, delta: i32) {
        let slot = match index % KEYS.len() {
            0 => &mut self.island_size,
            1 => &mut self.island_thickness,
            2 => &mut self.sky_density,
            3 => &mut self.terrain_roughness,
            4 => &mut self.mountain_height,
            5 => &mut self.flatness,
            6 => &mut self.cave_amount,
            7 => &mut self.cave_size,
            8 => &mut self.water,
            9 => &mut self.biome_size,
            10 => &mut self.tree_density,
            _ => &mut self.glimmer_rarity,
        };
        *slot = (*slot + delta).clamp(0, 100);
    }
}

/// Map a 0–100 slider to a multiplier: 0→lo, 50→mid, 100→hi.
pub fn scale(data: &Settings, key: &str, lo: f64, mid: f64, hi: f64) -> f64 {
    let t = data.get(key).clamp(0, 100) as f64 / 100.0;
    if t <= 0.5 {
        lo + (mid - lo) * (t / 0.5)
    } else {
        mid + (hi - mid) * ((t - 0.5) / 0.5)
    }
}

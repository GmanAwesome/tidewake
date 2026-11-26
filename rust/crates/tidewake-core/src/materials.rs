//! Block kinds from Tidewake 1.4.6. Ids match `tidewake/materials.py`.
//! Generated from that table plus `palette.py`. Do not renumber.

pub const KIND_AIR: u8 = 0;
pub const KIND_FULL: u8 = 1;
pub const KIND_WATER: u8 = 2;
pub const KIND_DECO: u8 = 3;
pub const KIND_GLASS: u8 = 4;
pub const KIND_SLAB: u8 = 5;
#[derive(Clone, Copy)]
pub struct Mat {
    pub name: &'static str,
    pub kind: u8,
    pub top: [f32; 3],
    pub side: [f32; 3],
    pub emit: f32,
    pub solid: bool,
}
pub const N: usize = 252;
pub static MATS: [Mat; N] = [
    Mat { name: "Air", kind: 0, top: [0.0000, 0.0000, 0.0000], side: [0.0000, 0.0000, 0.0000], emit: 0.000, solid: false },
    Mat { name: "Stone", kind: 1, top: [0.8000, 0.7800, 0.7200], side: [0.7400, 0.7100, 0.6600], emit: 0.000, solid: true },
    Mat { name: "Loam", kind: 1, top: [0.5800, 0.4500, 0.3600], side: [0.5500, 0.4200, 0.3400], emit: 0.000, solid: true },
    Mat { name: "Turf", kind: 1, top: [0.5500, 0.7800, 0.4200], side: [0.5500, 0.4200, 0.3400], emit: 0.000, solid: true },
    Mat { name: "Sand", kind: 1, top: [0.9400, 0.8600, 0.6800], side: [0.9000, 0.8100, 0.6200], emit: 0.000, solid: true },
    Mat { name: "Snow", kind: 1, top: [0.9500, 0.9700, 1.0000], side: [0.8800, 0.9100, 0.9600], emit: 0.000, solid: true },
    Mat { name: "Ice", kind: 1, top: [0.7200, 0.8800, 0.9700], side: [0.6200, 0.8000, 0.9300], emit: 0.000, solid: true },
    Mat { name: "Basalt", kind: 1, top: [0.3300, 0.3500, 0.4200], side: [0.2700, 0.2900, 0.3500], emit: 0.000, solid: true },
    Mat { name: "Rosestone", kind: 1, top: [0.9300, 0.6600, 0.5800], side: [0.9000, 0.6200, 0.5500], emit: 0.000, solid: true },
    Mat { name: "Heartwood", kind: 1, top: [0.6600, 0.5200, 0.4000], side: [0.5200, 0.3800, 0.3000], emit: 0.000, solid: true },
    Mat { name: "Canopy", kind: 1, top: [0.4000, 0.6800, 0.3800], side: [0.3600, 0.6200, 0.3500], emit: 0.000, solid: true },
    Mat { name: "Water", kind: 2, top: [0.3600, 0.6600, 0.8600], side: [0.3200, 0.6000, 0.8200], emit: 0.000, solid: false },
    Mat { name: "Crystal", kind: 3, top: [0.6600, 0.8800, 1.0000], side: [0.5500, 0.8000, 0.9800], emit: 0.900, solid: false },
    Mat { name: "Vine", kind: 3, top: [0.3400, 0.6200, 0.3400], side: [0.3000, 0.5600, 0.3100], emit: 0.000, solid: false },
    Mat { name: "Bloom", kind: 3, top: [1.0000, 0.6200, 0.7800], side: [0.4500, 0.7000, 0.4000], emit: 0.700, solid: false },
    Mat { name: "Clay", kind: 1, top: [0.8600, 0.5400, 0.4000], side: [0.8000, 0.4800, 0.3600], emit: 0.000, solid: true },
    Mat { name: "Mossrock", kind: 1, top: [0.4600, 0.6800, 0.4200], side: [0.6200, 0.6600, 0.5600], emit: 0.000, solid: true },
    Mat { name: "Cloudstuff", kind: 1, top: [0.9900, 0.9800, 1.0000], side: [0.9300, 0.9300, 0.9900], emit: 0.150, solid: true },
    Mat { name: "Lantern", kind: 3, top: [1.0000, 0.8600, 0.5200], side: [1.0000, 0.8000, 0.4500], emit: 1.000, solid: false },
    Mat { name: "Sprout", kind: 3, top: [0.5600, 0.8600, 0.4400], side: [0.4400, 0.7200, 0.3600], emit: 0.000, solid: false },
    Mat { name: "Glowcap", kind: 3, top: [0.5200, 0.9600, 0.8600], side: [0.9200, 0.9000, 0.8400], emit: 0.850, solid: false },
    Mat { name: "Plinth", kind: 1, top: [0.7600, 0.7400, 0.8400], side: [0.6600, 0.6400, 0.7600], emit: 0.000, solid: true },
    Mat { name: "Dormant Spire", kind: 1, top: [0.4400, 0.4200, 0.5600], side: [0.3800, 0.3600, 0.5000], emit: 0.000, solid: true },
    Mat { name: "Awake Spire", kind: 1, top: [0.9000, 0.8600, 1.0000], side: [0.8000, 0.7600, 0.9800], emit: 0.450, solid: true },
    Mat { name: "Lumen Shard", kind: 3, top: [0.8000, 0.6800, 1.0000], side: [0.7200, 0.6000, 0.9800], emit: 0.900, solid: false },
    Mat { name: "Petals", kind: 3, top: [1.0000, 0.9600, 0.8000], side: [0.4500, 0.7000, 0.4000], emit: 0.000, solid: false },
    Mat { name: "Planks", kind: 1, top: [0.8600, 0.6800, 0.4800], side: [0.7800, 0.6000, 0.4200], emit: 0.000, solid: true },
    Mat { name: "Tinker Bench", kind: 1, top: [0.9200, 0.7400, 0.5000], side: [0.6200, 0.4400, 0.3200], emit: 0.000, solid: true },
    Mat { name: "Kiln", kind: 1, top: [0.9800, 0.6200, 0.3800], side: [0.5800, 0.5400, 0.5600], emit: 0.250, solid: true },
    Mat { name: "Chest", kind: 1, top: [0.8000, 0.5600, 0.3600], side: [0.7000, 0.4600, 0.3000], emit: 0.000, solid: true },
    Mat { name: "Glass", kind: 4, top: [0.8400, 0.9400, 1.0000], side: [0.8000, 0.9200, 1.0000], emit: 0.050, solid: true },
    Mat { name: "Bricks", kind: 1, top: [0.8200, 0.4600, 0.4000], side: [0.7400, 0.4000, 0.3600], emit: 0.000, solid: true },
    Mat { name: "Fluff Block", kind: 1, top: [0.9900, 0.9500, 0.9000], side: [0.9500, 0.9000, 0.8600], emit: 0.000, solid: true },
    Mat { name: "Bedroll", kind: 3, top: [0.9400, 0.5200, 0.5600], side: [0.9900, 0.9500, 0.9000], emit: 0.000, solid: false },
    Mat { name: "Glowstick", kind: 3, top: [1.0000, 0.7800, 0.4000], side: [0.6000, 0.4400, 0.3000], emit: 1.000, solid: false },
    Mat { name: "Berry Bush", kind: 3, top: [0.3600, 0.6200, 0.4000], side: [0.3600, 0.6200, 0.4000], emit: 0.000, solid: false },
    Mat { name: "Emberite Ore", kind: 1, top: [0.9800, 0.5200, 0.3000], side: [0.4000, 0.3800, 0.4200], emit: 0.300, solid: true },
    Mat { name: "Verdigris Ore", kind: 1, top: [0.3800, 0.8600, 0.7200], side: [0.5800, 0.6000, 0.6000], emit: 0.120, solid: true },
    Mat { name: "Silverine Ore", kind: 1, top: [0.8800, 0.9200, 1.0000], side: [0.5600, 0.5600, 0.6400], emit: 0.200, solid: true },
    Mat { name: "Aetherite Ore", kind: 1, top: [0.8000, 0.5600, 1.0000], side: [0.4200, 0.3800, 0.5200], emit: 0.600, solid: true },
    Mat { name: "Polished Stone", kind: 1, top: [0.9000, 0.8800, 0.8400], side: [0.8000, 0.7800, 0.7400], emit: 0.000, solid: true },
    Mat { name: "Mossy Bricks", kind: 1, top: [0.5600, 0.7000, 0.4600], side: [0.6800, 0.4800, 0.4200], emit: 0.000, solid: true },
    Mat { name: "Lumen Lamp", kind: 1, top: [1.0000, 0.9200, 0.7000], side: [0.9800, 0.8400, 0.6000], emit: 1.000, solid: true },
    Mat { name: "Door", kind: 3, top: [0.8600, 0.6800, 0.4800], side: [0.6200, 0.4400, 0.3000], emit: 0.000, solid: false },
    Mat { name: "Ladder", kind: 3, top: [0.7800, 0.5800, 0.3800], side: [0.7000, 0.5000, 0.3200], emit: 0.000, solid: false },
    Mat { name: "Cedar Heartwood", kind: 1, top: [0.4800, 0.3000, 0.2200], side: [0.3600, 0.2200, 0.1600], emit: 0.000, solid: true },
    Mat { name: "Pale Heartwood", kind: 1, top: [0.8600, 0.7800, 0.6200], side: [0.7400, 0.6600, 0.5000], emit: 0.000, solid: true },
    Mat { name: "Dark Heartwood", kind: 1, top: [0.3600, 0.2400, 0.1800], side: [0.2600, 0.1600, 0.1200], emit: 0.000, solid: true },
    Mat { name: "Cedar Planks", kind: 1, top: [0.6400, 0.4000, 0.2800], side: [0.5600, 0.3400, 0.2400], emit: 0.000, solid: true },
    Mat { name: "Pale Planks", kind: 1, top: [0.9200, 0.8600, 0.7000], side: [0.8600, 0.7800, 0.6200], emit: 0.000, solid: true },
    Mat { name: "Dark Planks", kind: 1, top: [0.4800, 0.3200, 0.2400], side: [0.4000, 0.2600, 0.2000], emit: 0.000, solid: true },
    Mat { name: "Cobble", kind: 1, top: [0.6200, 0.6000, 0.5600], side: [0.5600, 0.5400, 0.5000], emit: 0.000, solid: true },
    Mat { name: "Slate", kind: 1, top: [0.4000, 0.4400, 0.5000], side: [0.3400, 0.3800, 0.4400], emit: 0.000, solid: true },
    Mat { name: "Chalk", kind: 1, top: [0.9400, 0.9300, 0.8800], side: [0.8800, 0.8600, 0.8000], emit: 0.000, solid: true },
    Mat { name: "Sandstone", kind: 1, top: [0.8600, 0.7200, 0.4800], side: [0.7800, 0.6400, 0.4200], emit: 0.000, solid: true },
    Mat { name: "Cinder", kind: 1, top: [0.2800, 0.2400, 0.2400], side: [0.2200, 0.1800, 0.1800], emit: 0.000, solid: true },
    Mat { name: "Starstone", kind: 1, top: [0.2200, 0.1800, 0.3600], side: [0.1600, 0.1400, 0.2800], emit: 0.180, solid: true },
    Mat { name: "Salt Block", kind: 1, top: [0.9600, 0.9600, 0.9400], side: [0.9000, 0.9200, 0.9000], emit: 0.000, solid: true },
    Mat { name: "Pale Stone", kind: 1, top: [0.8600, 0.8600, 0.8400], side: [0.7800, 0.7800, 0.7600], emit: 0.000, solid: true },
    Mat { name: "Polished Basalt", kind: 1, top: [0.4000, 0.4200, 0.4800], side: [0.3200, 0.3400, 0.4000], emit: 0.000, solid: true },
    Mat { name: "Polished Rosestone", kind: 1, top: [0.9600, 0.7400, 0.6800], side: [0.9000, 0.6600, 0.6000], emit: 0.000, solid: true },
    Mat { name: "Polished Slate", kind: 1, top: [0.5000, 0.5400, 0.6000], side: [0.4200, 0.4600, 0.5200], emit: 0.000, solid: true },
    Mat { name: "Polished Chalk", kind: 1, top: [0.9800, 0.9700, 0.9400], side: [0.9200, 0.9000, 0.8600], emit: 0.000, solid: true },
    Mat { name: "Polished Sandstone", kind: 1, top: [0.9200, 0.8000, 0.5800], side: [0.8600, 0.7400, 0.5200], emit: 0.000, solid: true },
    Mat { name: "Polished Starstone", kind: 1, top: [0.3000, 0.2600, 0.4800], side: [0.2400, 0.2000, 0.4000], emit: 0.220, solid: true },
    Mat { name: "Polished Pale Stone", kind: 1, top: [0.9400, 0.9400, 0.9200], side: [0.8600, 0.8600, 0.8400], emit: 0.000, solid: true },
    Mat { name: "Stone Bricks", kind: 1, top: [0.7600, 0.7400, 0.6800], side: [0.6800, 0.6600, 0.6000], emit: 0.000, solid: true },
    Mat { name: "Basalt Bricks", kind: 1, top: [0.3600, 0.3800, 0.4400], side: [0.3000, 0.3200, 0.3800], emit: 0.000, solid: true },
    Mat { name: "Rosestone Bricks", kind: 1, top: [0.9000, 0.6000, 0.5200], side: [0.8200, 0.5200, 0.4600], emit: 0.000, solid: true },
    Mat { name: "Slate Bricks", kind: 1, top: [0.4400, 0.4800, 0.5400], side: [0.3800, 0.4200, 0.4800], emit: 0.000, solid: true },
    Mat { name: "Sandstone Bricks", kind: 1, top: [0.8400, 0.6800, 0.4400], side: [0.7600, 0.6000, 0.3800], emit: 0.000, solid: true },
    Mat { name: "Chalk Bricks", kind: 1, top: [0.9200, 0.9000, 0.8400], side: [0.8400, 0.8200, 0.7600], emit: 0.000, solid: true },
    Mat { name: "Cinder Bricks", kind: 1, top: [0.3400, 0.2800, 0.2600], side: [0.2800, 0.2200, 0.2000], emit: 0.000, solid: true },
    Mat { name: "Snow Bricks", kind: 1, top: [0.9400, 0.9600, 0.9800], side: [0.8600, 0.8800, 0.9200], emit: 0.000, solid: true },
    Mat { name: "Dusk Bricks", kind: 1, top: [0.4000, 0.4200, 0.6200], side: [0.3400, 0.3600, 0.5400], emit: 0.000, solid: true },
    Mat { name: "Lavender Bricks", kind: 1, top: [0.7200, 0.5800, 0.7800], side: [0.6400, 0.5000, 0.7000], emit: 0.000, solid: true },
    Mat { name: "Verdigris Bricks", kind: 1, top: [0.3200, 0.7000, 0.6200], side: [0.2600, 0.6200, 0.5400], emit: 0.000, solid: true },
    Mat { name: "Stone Tiles", kind: 1, top: [0.7800, 0.7600, 0.7200], side: [0.7000, 0.6800, 0.6400], emit: 0.000, solid: true },
    Mat { name: "Basalt Tiles", kind: 1, top: [0.3800, 0.4000, 0.4600], side: [0.3200, 0.3400, 0.4000], emit: 0.000, solid: true },
    Mat { name: "Rosestone Tiles", kind: 1, top: [0.9400, 0.6800, 0.6200], side: [0.8600, 0.6000, 0.5400], emit: 0.000, solid: true },
    Mat { name: "Slate Tiles", kind: 1, top: [0.4600, 0.5000, 0.5600], side: [0.4000, 0.4400, 0.5000], emit: 0.000, solid: true },
    Mat { name: "Sandstone Tiles", kind: 1, top: [0.8800, 0.7400, 0.5200], side: [0.8000, 0.6600, 0.4600], emit: 0.000, solid: true },
    Mat { name: "Chalk Tiles", kind: 1, top: [0.9600, 0.9500, 0.9000], side: [0.8800, 0.8600, 0.8000], emit: 0.000, solid: true },
    Mat { name: "Clay Tiles", kind: 1, top: [0.8400, 0.5000, 0.3800], side: [0.7600, 0.4400, 0.3200], emit: 0.000, solid: true },
    Mat { name: "Starstone Tiles", kind: 1, top: [0.2800, 0.2200, 0.4200], side: [0.2200, 0.1800, 0.3400], emit: 0.160, solid: true },
    Mat { name: "Verdigris Tiles", kind: 1, top: [0.3000, 0.7200, 0.6400], side: [0.2400, 0.6400, 0.5600], emit: 0.000, solid: true },
    Mat { name: "Lavender Tiles", kind: 1, top: [0.7600, 0.6200, 0.8200], side: [0.6800, 0.5400, 0.7400], emit: 0.000, solid: true },
    Mat { name: "Thatch", kind: 1, top: [0.8200, 0.6800, 0.3600], side: [0.7200, 0.5800, 0.2800], emit: 0.000, solid: true },
    Mat { name: "Shingles", kind: 1, top: [0.7000, 0.3800, 0.3200], side: [0.6200, 0.3200, 0.2800], emit: 0.000, solid: true },
    Mat { name: "Carved Stone", kind: 1, top: [0.8400, 0.8000, 0.7200], side: [0.7400, 0.7000, 0.6400], emit: 0.000, solid: true },
    Mat { name: "Mosaic", kind: 1, top: [0.7000, 0.6600, 0.7200], side: [0.6200, 0.5800, 0.6400], emit: 0.000, solid: true },
    Mat { name: "Packed Earth", kind: 1, top: [0.6200, 0.4800, 0.3400], side: [0.5600, 0.4200, 0.3000], emit: 0.000, solid: true },
    Mat { name: "Wattle", kind: 1, top: [0.7800, 0.6800, 0.5000], side: [0.7000, 0.6000, 0.4400], emit: 0.000, solid: true },
    Mat { name: "Linen", kind: 1, top: [0.9000, 0.8600, 0.7600], side: [0.8200, 0.7800, 0.6800], emit: 0.000, solid: true },
    Mat { name: "Crimson Cloth", kind: 1, top: [0.7200, 0.2200, 0.2600], side: [0.6200, 0.1600, 0.2000], emit: 0.000, solid: true },
    Mat { name: "Dusk Cloth", kind: 1, top: [0.3200, 0.3000, 0.4800], side: [0.2600, 0.2400, 0.4000], emit: 0.000, solid: true },
    Mat { name: "Heather", kind: 1, top: [0.6200, 0.4800, 0.7000], side: [0.4200, 0.5000, 0.3600], emit: 0.000, solid: true },
    Mat { name: "Ember Lamp", kind: 1, top: [1.0000, 0.6200, 0.3200], side: [0.7000, 0.4000, 0.2800], emit: 1.000, solid: true },
    Mat { name: "Aether Lamp", kind: 1, top: [0.7800, 0.5600, 1.0000], side: [0.4800, 0.3600, 0.7000], emit: 1.000, solid: true },
    Mat { name: "Verdigris Lamp", kind: 1, top: [0.4000, 0.9200, 0.7800], side: [0.3000, 0.5800, 0.5200], emit: 1.000, solid: true },
    Mat { name: "Green Glass", kind: 4, top: [0.5500, 0.9000, 0.6200], side: [0.4500, 0.8400, 0.5500], emit: 0.040, solid: true },
    Mat { name: "Amber Glass", kind: 4, top: [1.0000, 0.8200, 0.4200], side: [0.9600, 0.7400, 0.3200], emit: 0.040, solid: true },
    Mat { name: "Violet Glass", kind: 4, top: [0.7200, 0.5200, 0.9600], side: [0.6200, 0.4200, 0.9000], emit: 0.040, solid: true },
    Mat { name: "Stone Slab", kind: 5, top: [0.8000, 0.7800, 0.7200], side: [0.7400, 0.7100, 0.6600], emit: 0.000, solid: true },
    Mat { name: "Cobble Slab", kind: 5, top: [0.6200, 0.6000, 0.5600], side: [0.5600, 0.5400, 0.5000], emit: 0.000, solid: true },
    Mat { name: "Planks Slab", kind: 5, top: [0.8600, 0.6800, 0.4800], side: [0.7800, 0.6000, 0.4200], emit: 0.000, solid: true },
    Mat { name: "Cedar Planks Slab", kind: 5, top: [0.6400, 0.4000, 0.2800], side: [0.5600, 0.3400, 0.2400], emit: 0.000, solid: true },
    Mat { name: "Pale Planks Slab", kind: 5, top: [0.9200, 0.8600, 0.7000], side: [0.8600, 0.7800, 0.6200], emit: 0.000, solid: true },
    Mat { name: "Dark Planks Slab", kind: 5, top: [0.4800, 0.3200, 0.2400], side: [0.4000, 0.2600, 0.2000], emit: 0.000, solid: true },
    Mat { name: "Bricks Slab", kind: 5, top: [0.8200, 0.4600, 0.4000], side: [0.7400, 0.4000, 0.3600], emit: 0.000, solid: true },
    Mat { name: "Stone Bricks Slab", kind: 5, top: [0.7600, 0.7400, 0.6800], side: [0.6800, 0.6600, 0.6000], emit: 0.000, solid: true },
    Mat { name: "Sandstone Slab", kind: 5, top: [0.8600, 0.7200, 0.4800], side: [0.7800, 0.6400, 0.4200], emit: 0.000, solid: true },
    Mat { name: "Slate Slab", kind: 5, top: [0.4000, 0.4400, 0.5000], side: [0.3400, 0.3800, 0.4400], emit: 0.000, solid: true },
    Mat { name: "Thatch Slab", kind: 5, top: [0.8200, 0.6800, 0.3600], side: [0.7200, 0.5800, 0.2800], emit: 0.000, solid: true },
    Mat { name: "Shingles Slab", kind: 5, top: [0.7000, 0.3800, 0.3200], side: [0.6200, 0.3200, 0.2800], emit: 0.000, solid: true },
    Mat { name: "Polished Stone Slab", kind: 5, top: [0.9000, 0.8800, 0.8400], side: [0.8000, 0.7800, 0.7400], emit: 0.000, solid: true },
    Mat { name: "Waystone", kind: 1, top: [0.8600, 0.8000, 0.9800], side: [0.6200, 0.5600, 0.7800], emit: 0.550, solid: true },
    Mat { name: "Tidewell", kind: 1, top: [1.0000, 0.9000, 0.5800], side: [0.7200, 0.6200, 0.7800], emit: 0.850, solid: true },
    Mat { name: "Farmland", kind: 1, top: [0.5200, 0.3800, 0.2600], side: [0.4800, 0.3600, 0.2400], emit: 0.000, solid: true },
    Mat { name: "Skywheat", kind: 3, top: [0.8200, 0.7200, 0.3800], side: [0.4600, 0.6200, 0.3200], emit: 0.000, solid: false },
    Mat { name: "Sweetroot Crop", kind: 3, top: [0.6200, 0.4800, 0.3000], side: [0.4000, 0.6200, 0.3400], emit: 0.000, solid: false },
    Mat { name: "Berry Crop", kind: 3, top: [0.3600, 0.6200, 0.4000], side: [0.3600, 0.6200, 0.4000], emit: 0.000, solid: false },
    Mat { name: "Grass", kind: 3, top: [0.5000, 0.7800, 0.3600], side: [0.4000, 0.6200, 0.3000], emit: 0.000, solid: false },
    Mat { name: "Wildflower", kind: 3, top: [0.9200, 0.5500, 0.7800], side: [0.4200, 0.6800, 0.3600], emit: 0.000, solid: false },
    Mat { name: "Mushroom", kind: 3, top: [0.7800, 0.4200, 0.3200], side: [0.8600, 0.8000, 0.7000], emit: 0.000, solid: false },
    Mat { name: "Pebble", kind: 3, top: [0.6200, 0.6000, 0.5600], side: [0.5600, 0.5400, 0.5000], emit: 0.000, solid: false },
    Mat { name: "Shrub", kind: 3, top: [0.3200, 0.5200, 0.3000], side: [0.3200, 0.5200, 0.3000], emit: 0.000, solid: false },
    Mat { name: "Reeds", kind: 3, top: [0.4600, 0.6200, 0.3400], side: [0.3800, 0.5200, 0.2800], emit: 0.000, solid: false },
    Mat { name: "Signpost", kind: 3, top: [0.7200, 0.5400, 0.3400], side: [0.6200, 0.4400, 0.2800], emit: 0.000, solid: false },
    Mat { name: "Snow Patterned Tile", kind: 1, top: [0.8916, 0.8840, 0.8564], side: [0.8024, 0.7956, 0.7708], emit: 0.000, solid: true },
    Mat { name: "Pearl Patterned Tile", kind: 1, top: [0.7924, 0.7848, 0.7820], side: [0.7132, 0.7063, 0.7038], emit: 0.000, solid: true },
    Mat { name: "Ash Patterned Tile", kind: 1, top: [0.6064, 0.5988, 0.6084], side: [0.5458, 0.5389, 0.5476], emit: 0.000, solid: true },
    Mat { name: "Ink Patterned Tile", kind: 1, top: [0.3956, 0.3756, 0.3852], side: [0.3560, 0.3380, 0.3467], emit: 0.000, solid: true },
    Mat { name: "Rose Patterned Tile", kind: 1, top: [0.8296, 0.4624, 0.4968], side: [0.7466, 0.4162, 0.4471], emit: 0.000, solid: true },
    Mat { name: "Ember Patterned Tile", kind: 1, top: [0.8668, 0.5492, 0.3728], side: [0.7801, 0.4943, 0.3355], emit: 0.000, solid: true },
    Mat { name: "Honey Patterned Tile", kind: 1, top: [0.8916, 0.7724, 0.4100], side: [0.8024, 0.6952, 0.3690], emit: 0.000, solid: true },
    Mat { name: "Leaf Patterned Tile", kind: 1, top: [0.5568, 0.7352, 0.4472], side: [0.5011, 0.6617, 0.4025], emit: 0.000, solid: true },
    Mat { name: "Moss Patterned Tile", kind: 1, top: [0.4824, 0.5988, 0.4472], side: [0.4342, 0.5389, 0.4025], emit: 0.000, solid: true },
    Mat { name: "Tide Patterned Tile", kind: 1, top: [0.4080, 0.7228, 0.6952], side: [0.3672, 0.6505, 0.6257], emit: 0.000, solid: true },
    Mat { name: "Sky Patterned Tile", kind: 1, top: [0.5568, 0.7228, 0.8564], side: [0.5011, 0.6505, 0.7708], emit: 0.000, solid: true },
    Mat { name: "Indigo Patterned Tile", kind: 1, top: [0.4700, 0.4996, 0.7200], side: [0.4230, 0.4496, 0.6480], emit: 0.000, solid: true },
    Mat { name: "Violet Patterned Tile", kind: 1, top: [0.6560, 0.4996, 0.7572], side: [0.5904, 0.4496, 0.6815], emit: 0.000, solid: true },
    Mat { name: "Orchid Patterned Tile", kind: 1, top: [0.7800, 0.5120, 0.7076], side: [0.7020, 0.4608, 0.6368], emit: 0.000, solid: true },
    Mat { name: "Blush Patterned Tile", kind: 1, top: [0.8916, 0.6732, 0.7200], side: [0.8024, 0.6059, 0.6480], emit: 0.000, solid: true },
    Mat { name: "Cocoa Patterned Tile", kind: 1, top: [0.5940, 0.4872, 0.4100], side: [0.5346, 0.4385, 0.3690], emit: 0.000, solid: true },
    Mat { name: "Snow Terrazzo", kind: 1, top: [0.9220, 0.9144, 0.8868], side: [0.8482, 0.8412, 0.8159], emit: 0.000, solid: true },
    Mat { name: "Pearl Terrazzo", kind: 1, top: [0.8228, 0.8152, 0.8124], side: [0.7570, 0.7500, 0.7474], emit: 0.000, solid: true },
    Mat { name: "Ash Terrazzo", kind: 1, top: [0.6368, 0.6292, 0.6388], side: [0.5859, 0.5789, 0.5877], emit: 0.000, solid: true },
    Mat { name: "Ink Terrazzo", kind: 1, top: [0.4260, 0.4060, 0.4156], side: [0.3919, 0.3735, 0.3824], emit: 0.000, solid: true },
    Mat { name: "Rose Terrazzo", kind: 1, top: [0.8600, 0.4928, 0.5272], side: [0.7912, 0.4534, 0.4850], emit: 0.000, solid: true },
    Mat { name: "Ember Terrazzo", kind: 1, top: [0.8972, 0.5796, 0.4032], side: [0.8254, 0.5332, 0.3709], emit: 0.000, solid: true },
    Mat { name: "Honey Terrazzo", kind: 1, top: [0.9220, 0.8028, 0.4404], side: [0.8482, 0.7386, 0.4052], emit: 0.000, solid: true },
    Mat { name: "Leaf Terrazzo", kind: 1, top: [0.5872, 0.7656, 0.4776], side: [0.5402, 0.7044, 0.4394], emit: 0.000, solid: true },
    Mat { name: "Moss Terrazzo", kind: 1, top: [0.5128, 0.6292, 0.4776], side: [0.4718, 0.5789, 0.4394], emit: 0.000, solid: true },
    Mat { name: "Tide Terrazzo", kind: 1, top: [0.4384, 0.7532, 0.7256], side: [0.4033, 0.6929, 0.6676], emit: 0.000, solid: true },
    Mat { name: "Sky Terrazzo", kind: 1, top: [0.5872, 0.7532, 0.8868], side: [0.5402, 0.6929, 0.8159], emit: 0.000, solid: true },
    Mat { name: "Indigo Terrazzo", kind: 1, top: [0.5004, 0.5300, 0.7504], side: [0.4604, 0.4876, 0.6904], emit: 0.000, solid: true },
    Mat { name: "Violet Terrazzo", kind: 1, top: [0.6864, 0.5300, 0.7876], side: [0.6315, 0.4876, 0.7246], emit: 0.000, solid: true },
    Mat { name: "Orchid Terrazzo", kind: 1, top: [0.8104, 0.5424, 0.7380], side: [0.7456, 0.4990, 0.6790], emit: 0.000, solid: true },
    Mat { name: "Blush Terrazzo", kind: 1, top: [0.9220, 0.7036, 0.7504], side: [0.8482, 0.6473, 0.6904], emit: 0.000, solid: true },
    Mat { name: "Cocoa Terrazzo", kind: 1, top: [0.6244, 0.5176, 0.4404], side: [0.5744, 0.4762, 0.4052], emit: 0.000, solid: true },
    Mat { name: "Snow Woven Panel", kind: 1, top: [0.8688, 0.8384, 0.7728], side: [0.7645, 0.7378, 0.6801], emit: 0.000, solid: true },
    Mat { name: "Pearl Woven Panel", kind: 1, top: [0.7696, 0.7392, 0.6984], side: [0.6772, 0.6505, 0.6146], emit: 0.000, solid: true },
    Mat { name: "Ash Woven Panel", kind: 1, top: [0.5836, 0.5532, 0.5248], side: [0.5136, 0.4868, 0.4618], emit: 0.000, solid: true },
    Mat { name: "Ink Woven Panel", kind: 1, top: [0.3728, 0.3300, 0.3016], side: [0.3281, 0.2904, 0.2654], emit: 0.000, solid: true },
    Mat { name: "Rose Woven Panel", kind: 1, top: [0.8068, 0.4168, 0.4132], side: [0.7100, 0.3668, 0.3636], emit: 0.000, solid: true },
    Mat { name: "Ember Woven Panel", kind: 1, top: [0.8440, 0.5036, 0.2892], side: [0.7427, 0.4432, 0.2545], emit: 0.000, solid: true },
    Mat { name: "Honey Woven Panel", kind: 1, top: [0.8688, 0.7268, 0.3264], side: [0.7645, 0.6396, 0.2872], emit: 0.000, solid: true },
    Mat { name: "Leaf Woven Panel", kind: 1, top: [0.5340, 0.6896, 0.3636], side: [0.4699, 0.6068, 0.3200], emit: 0.000, solid: true },
    Mat { name: "Moss Woven Panel", kind: 1, top: [0.4596, 0.5532, 0.3636], side: [0.4044, 0.4868, 0.3200], emit: 0.000, solid: true },
    Mat { name: "Tide Woven Panel", kind: 1, top: [0.3852, 0.6772, 0.6116], side: [0.3390, 0.5959, 0.5382], emit: 0.000, solid: true },
    Mat { name: "Sky Woven Panel", kind: 1, top: [0.5340, 0.6772, 0.7728], side: [0.4699, 0.5959, 0.6801], emit: 0.000, solid: true },
    Mat { name: "Indigo Woven Panel", kind: 1, top: [0.4472, 0.4540, 0.6364], side: [0.3935, 0.3995, 0.5600], emit: 0.000, solid: true },
    Mat { name: "Violet Woven Panel", kind: 1, top: [0.6332, 0.4540, 0.6736], side: [0.5572, 0.3995, 0.5928], emit: 0.000, solid: true },
    Mat { name: "Orchid Woven Panel", kind: 1, top: [0.7572, 0.4664, 0.6240], side: [0.6663, 0.4104, 0.5491], emit: 0.000, solid: true },
    Mat { name: "Blush Woven Panel", kind: 1, top: [0.8688, 0.6276, 0.6364], side: [0.7645, 0.5523, 0.5600], emit: 0.000, solid: true },
    Mat { name: "Cocoa Woven Panel", kind: 1, top: [0.5712, 0.4416, 0.3264], side: [0.5027, 0.3886, 0.2872], emit: 0.000, solid: true },
    Mat { name: "Snow Stained Glass", kind: 4, top: [0.9080, 0.9320, 0.9320], side: [0.8626, 0.8854, 0.8854], emit: 0.100, solid: true },
    Mat { name: "Pearl Stained Glass", kind: 4, top: [0.7800, 0.8040, 0.8360], side: [0.7410, 0.7638, 0.7942], emit: 0.100, solid: true },
    Mat { name: "Ash Stained Glass", kind: 4, top: [0.5400, 0.5640, 0.6120], side: [0.5130, 0.5358, 0.5814], emit: 0.100, solid: true },
    Mat { name: "Ink Stained Glass", kind: 4, top: [0.2680, 0.2760, 0.3240], side: [0.2546, 0.2622, 0.3078], emit: 0.100, solid: true },
    Mat { name: "Rose Stained Glass", kind: 4, top: [0.8280, 0.3880, 0.4680], side: [0.7866, 0.3686, 0.4446], emit: 0.100, solid: true },
    Mat { name: "Ember Stained Glass", kind: 4, top: [0.8760, 0.5000, 0.3080], side: [0.8322, 0.4750, 0.2926], emit: 0.100, solid: true },
    Mat { name: "Honey Stained Glass", kind: 4, top: [0.9080, 0.7880, 0.3560], side: [0.8626, 0.7486, 0.3382], emit: 0.100, solid: true },
    Mat { name: "Leaf Stained Glass", kind: 4, top: [0.4760, 0.7400, 0.4040], side: [0.4522, 0.7030, 0.3838], emit: 0.100, solid: true },
    Mat { name: "Moss Stained Glass", kind: 4, top: [0.3800, 0.5640, 0.4040], side: [0.3610, 0.5358, 0.3838], emit: 0.100, solid: true },
    Mat { name: "Tide Stained Glass", kind: 4, top: [0.2840, 0.7240, 0.7240], side: [0.2698, 0.6878, 0.6878], emit: 0.100, solid: true },
    Mat { name: "Sky Stained Glass", kind: 4, top: [0.4760, 0.7240, 0.9320], side: [0.4522, 0.6878, 0.8854], emit: 0.100, solid: true },
    Mat { name: "Indigo Stained Glass", kind: 4, top: [0.3640, 0.4360, 0.7560], side: [0.3458, 0.4142, 0.7182], emit: 0.100, solid: true },
    Mat { name: "Violet Stained Glass", kind: 4, top: [0.6040, 0.4360, 0.8040], side: [0.5738, 0.4142, 0.7638], emit: 0.100, solid: true },
    Mat { name: "Orchid Stained Glass", kind: 4, top: [0.7640, 0.4520, 0.7400], side: [0.7258, 0.4294, 0.7030], emit: 0.100, solid: true },
    Mat { name: "Blush Stained Glass", kind: 4, top: [0.9080, 0.6600, 0.7560], side: [0.8626, 0.6270, 0.7182], emit: 0.100, solid: true },
    Mat { name: "Cocoa Stained Glass", kind: 4, top: [0.5240, 0.4200, 0.3560], side: [0.4978, 0.3990, 0.3382], emit: 0.100, solid: true },
    Mat { name: "Snow Crystal Lamp", kind: 1, top: [0.9780, 0.9780, 0.9670], side: [0.8313, 0.8313, 0.8219], emit: 1.000, solid: true },
    Mat { name: "Pearl Crystal Lamp", kind: 1, top: [0.8900, 0.8900, 0.9010], side: [0.7565, 0.7565, 0.7659], emit: 1.000, solid: true },
    Mat { name: "Ash Crystal Lamp", kind: 1, top: [0.7250, 0.7250, 0.7470], side: [0.6162, 0.6162, 0.6350], emit: 1.000, solid: true },
    Mat { name: "Ink Crystal Lamp", kind: 1, top: [0.5380, 0.5270, 0.5490], side: [0.4573, 0.4479, 0.4666], emit: 1.000, solid: true },
    Mat { name: "Rose Crystal Lamp", kind: 1, top: [0.9230, 0.6040, 0.6480], side: [0.7845, 0.5134, 0.5508], emit: 1.000, solid: true },
    Mat { name: "Ember Crystal Lamp", kind: 1, top: [0.9560, 0.6810, 0.5380], side: [0.8126, 0.5788, 0.4573], emit: 1.000, solid: true },
    Mat { name: "Honey Crystal Lamp", kind: 1, top: [0.9780, 0.8790, 0.5710], side: [0.8313, 0.7471, 0.4853], emit: 1.000, solid: true },
    Mat { name: "Leaf Crystal Lamp", kind: 1, top: [0.6810, 0.8460, 0.6040], side: [0.5788, 0.7191, 0.5134], emit: 1.000, solid: true },
    Mat { name: "Moss Crystal Lamp", kind: 1, top: [0.6150, 0.7250, 0.6040], side: [0.5227, 0.6162, 0.5134], emit: 1.000, solid: true },
    Mat { name: "Tide Crystal Lamp", kind: 1, top: [0.5490, 0.8350, 0.8240], side: [0.4666, 0.7097, 0.7004], emit: 1.000, solid: true },
    Mat { name: "Sky Crystal Lamp", kind: 1, top: [0.6810, 0.8350, 0.9670], side: [0.5788, 0.7097, 0.8219], emit: 1.000, solid: true },
    Mat { name: "Indigo Crystal Lamp", kind: 1, top: [0.6040, 0.6370, 0.8460], side: [0.5134, 0.5414, 0.7191], emit: 1.000, solid: true },
    Mat { name: "Violet Crystal Lamp", kind: 1, top: [0.7690, 0.6370, 0.8790], side: [0.6536, 0.5414, 0.7471], emit: 1.000, solid: true },
    Mat { name: "Orchid Crystal Lamp", kind: 1, top: [0.8790, 0.6480, 0.8350], side: [0.7471, 0.5508, 0.7097], emit: 1.000, solid: true },
    Mat { name: "Blush Crystal Lamp", kind: 1, top: [0.9780, 0.7910, 0.8460], side: [0.8313, 0.6723, 0.7191], emit: 1.000, solid: true },
    Mat { name: "Cocoa Crystal Lamp", kind: 1, top: [0.7140, 0.6260, 0.5710], side: [0.6069, 0.5321, 0.4853], emit: 1.000, solid: true },
    Mat { name: "Snow Banner", kind: 3, top: [0.9220, 0.7472, 0.7348], side: [0.7376, 0.5978, 0.5878], emit: 0.000, solid: false },
    Mat { name: "Pearl Banner", kind: 3, top: [0.8228, 0.6480, 0.6604], side: [0.6582, 0.5184, 0.5283], emit: 0.000, solid: false },
    Mat { name: "Ash Banner", kind: 3, top: [0.6368, 0.4620, 0.4868], side: [0.5094, 0.3696, 0.3894], emit: 0.000, solid: false },
    Mat { name: "Ink Banner", kind: 3, top: [0.4260, 0.2388, 0.2636], side: [0.3408, 0.1910, 0.2109], emit: 0.000, solid: false },
    Mat { name: "Rose Banner", kind: 3, top: [0.8600, 0.3256, 0.3752], side: [0.6880, 0.2605, 0.3002], emit: 0.000, solid: false },
    Mat { name: "Ember Banner", kind: 3, top: [0.8972, 0.4124, 0.2512], side: [0.7178, 0.3299, 0.2010], emit: 0.000, solid: false },
    Mat { name: "Honey Banner", kind: 3, top: [0.9220, 0.6356, 0.2884], side: [0.7376, 0.5085, 0.2307], emit: 0.000, solid: false },
    Mat { name: "Leaf Banner", kind: 3, top: [0.5872, 0.5984, 0.3256], side: [0.4698, 0.4787, 0.2605], emit: 0.000, solid: false },
    Mat { name: "Moss Banner", kind: 3, top: [0.5128, 0.4620, 0.3256], side: [0.4102, 0.3696, 0.2605], emit: 0.000, solid: false },
    Mat { name: "Tide Banner", kind: 3, top: [0.4384, 0.5860, 0.5736], side: [0.3507, 0.4688, 0.4589], emit: 0.000, solid: false },
    Mat { name: "Sky Banner", kind: 3, top: [0.5872, 0.5860, 0.7348], side: [0.4698, 0.4688, 0.5878], emit: 0.000, solid: false },
    Mat { name: "Indigo Banner", kind: 3, top: [0.5004, 0.3628, 0.5984], side: [0.4003, 0.2902, 0.4787], emit: 0.000, solid: false },
    Mat { name: "Violet Banner", kind: 3, top: [0.6864, 0.3628, 0.6356], side: [0.5491, 0.2902, 0.5085], emit: 0.000, solid: false },
    Mat { name: "Orchid Banner", kind: 3, top: [0.8104, 0.3752, 0.5860], side: [0.6483, 0.3002, 0.4688], emit: 0.000, solid: false },
    Mat { name: "Blush Banner", kind: 3, top: [0.9220, 0.5364, 0.5984], side: [0.7376, 0.4291, 0.4787], emit: 0.000, solid: false },
    Mat { name: "Cocoa Banner", kind: 3, top: [0.6244, 0.3504, 0.2884], side: [0.4995, 0.2803, 0.2307], emit: 0.000, solid: false },
    Mat { name: "Ivory Plaster", kind: 1, top: [0.9400, 0.9000, 0.8400], side: [0.8800, 0.8400, 0.7800], emit: 0.000, solid: true },
    Mat { name: "Blush Plaster", kind: 1, top: [0.9000, 0.7200, 0.7400], side: [0.8200, 0.6400, 0.6600], emit: 0.000, solid: true },
    Mat { name: "Sage Plaster", kind: 1, top: [0.7000, 0.7800, 0.6800], side: [0.6000, 0.7000, 0.5800], emit: 0.000, solid: true },
    Mat { name: "Dusk Plaster", kind: 1, top: [0.4600, 0.4400, 0.5600], side: [0.3800, 0.3600, 0.4800], emit: 0.000, solid: true },
    Mat { name: "Pewter", kind: 1, top: [0.6200, 0.6400, 0.6800], side: [0.5000, 0.5200, 0.5600], emit: 0.000, solid: true },
    Mat { name: "Brass", kind: 1, top: [0.8200, 0.6600, 0.3200], side: [0.7000, 0.5400, 0.2400], emit: 0.080, solid: true },
    Mat { name: "Copper", kind: 1, top: [0.7800, 0.4200, 0.2800], side: [0.6600, 0.3400, 0.2200], emit: 0.000, solid: true },
    Mat { name: "Wrought Iron", kind: 1, top: [0.2800, 0.2800, 0.3000], side: [0.2000, 0.2000, 0.2200], emit: 0.000, solid: true },
    Mat { name: "Ochre Bricks", kind: 1, top: [0.7800, 0.5200, 0.2800], side: [0.6800, 0.4400, 0.2200], emit: 0.000, solid: true },
    Mat { name: "Ink Bricks", kind: 1, top: [0.2800, 0.2600, 0.3200], side: [0.2200, 0.2000, 0.2600], emit: 0.000, solid: true },
    Mat { name: "Wood Lattice", kind: 4, top: [0.7800, 0.6000, 0.4200], side: [0.7000, 0.5200, 0.3600], emit: 0.000, solid: true },
    Mat { name: "Pale Lattice", kind: 4, top: [0.9000, 0.8400, 0.7000], side: [0.8200, 0.7600, 0.6200], emit: 0.000, solid: true },
    Mat { name: "Rose Jelly", kind: 1, top: [0.9200, 0.4200, 0.5800], side: [0.8000, 0.3200, 0.4800], emit: 0.200, solid: true },
    Mat { name: "Tide Jelly", kind: 1, top: [0.3000, 0.8200, 0.8000], side: [0.2200, 0.7000, 0.6800], emit: 0.200, solid: true },
    Mat { name: "Honey Jelly", kind: 1, top: [0.9600, 0.7800, 0.3000], side: [0.8600, 0.6600, 0.2200], emit: 0.200, solid: true },
    Mat { name: "Violet Jelly", kind: 1, top: [0.6200, 0.4000, 0.8600], side: [0.5000, 0.3000, 0.7400], emit: 0.200, solid: true },
    Mat { name: "Ink Checker", kind: 1, top: [0.1800, 0.1600, 0.2000], side: [0.9000, 0.9000, 0.8800], emit: 0.000, solid: true },
    Mat { name: "Rose Checker", kind: 1, top: [0.8200, 0.3200, 0.4000], side: [0.9600, 0.9000, 0.8800], emit: 0.000, solid: true },
    Mat { name: "Rose Stripe", kind: 1, top: [0.9000, 0.3600, 0.4400], side: [0.9800, 0.9400, 0.9200], emit: 0.000, solid: true },
    Mat { name: "Sky Stripe", kind: 1, top: [0.3600, 0.6200, 0.9000], side: [0.9800, 0.9400, 0.9200], emit: 0.000, solid: true },
    Mat { name: "Shimmer Cloud", kind: 1, top: [0.9000, 0.9400, 1.0000], side: [0.7800, 0.8400, 0.9800], emit: 0.350, solid: true },
    Mat { name: "Cosmic Star", kind: 1, top: [0.1800, 0.1400, 0.4000], side: [0.1000, 0.0800, 0.2400], emit: 1.000, solid: true },
    Mat { name: "Blossom Canopy", kind: 1, top: [0.9800, 0.7200, 0.8400], side: [0.9000, 0.6200, 0.7600], emit: 0.000, solid: true },
    Mat { name: "Autumn Canopy", kind: 1, top: [0.9400, 0.4800, 0.2200], side: [0.8400, 0.4000, 0.1800], emit: 0.000, solid: true },
    Mat { name: "Frost Canopy", kind: 1, top: [0.7000, 0.8800, 0.9800], side: [0.6000, 0.7800, 0.9000], emit: 0.000, solid: true },
    Mat { name: "Violet Canopy", kind: 1, top: [0.6600, 0.4600, 0.9000], side: [0.5600, 0.3800, 0.8000], emit: 0.000, solid: true },
    Mat { name: "Golden Canopy", kind: 1, top: [0.9800, 0.8200, 0.3000], side: [0.8800, 0.7200, 0.2400], emit: 0.000, solid: true },
];
pub mod id {
    pub const AIR: u8 = 0;
    pub const STONE: u8 = 1;
    pub const LOAM: u8 = 2;
    pub const TURF: u8 = 3;
    pub const SAND: u8 = 4;
    pub const SNOW: u8 = 5;
    pub const ICE: u8 = 6;
    pub const BASALT: u8 = 7;
    pub const ROSESTONE: u8 = 8;
    pub const HEARTWOOD: u8 = 9;
    pub const CANOPY: u8 = 10;
    pub const WATER: u8 = 11;
    pub const CRYSTAL: u8 = 12;
    pub const VINE: u8 = 13;
    pub const BLOOM: u8 = 14;
    pub const CLAY: u8 = 15;
    pub const MOSSROCK: u8 = 16;
    pub const CLOUDSTUFF: u8 = 17;
    pub const LANTERN: u8 = 18;
    pub const SPROUT: u8 = 19;
    pub const GLOWCAP: u8 = 20;
    pub const PLINTH: u8 = 21;
    pub const DORMANT_SPIRE: u8 = 22;
    pub const AWAKE_SPIRE: u8 = 23;
    pub const LUMEN_SHARD: u8 = 24;
    pub const PETALS: u8 = 25;
    pub const PLANKS: u8 = 26;
    pub const TINKER_BENCH: u8 = 27;
    pub const KILN: u8 = 28;
    pub const CHEST: u8 = 29;
    pub const GLASS: u8 = 30;
    pub const BRICKS: u8 = 31;
    pub const FLUFF_BLOCK: u8 = 32;
    pub const BEDROLL: u8 = 33;
    pub const GLOWSTICK: u8 = 34;
    pub const BERRY_BUSH: u8 = 35;
    pub const EMBERITE_ORE: u8 = 36;
    pub const VERDIGRIS_ORE: u8 = 37;
    pub const SILVERINE_ORE: u8 = 38;
    pub const AETHERITE_ORE: u8 = 39;
    pub const POLISHED_STONE: u8 = 40;
    pub const MOSSY_BRICKS: u8 = 41;
    pub const LUMEN_LAMP: u8 = 42;
    pub const DOOR: u8 = 43;
    pub const LADDER: u8 = 44;
    pub const CEDAR_HEARTWOOD: u8 = 45;
    pub const PALE_HEARTWOOD: u8 = 46;
    pub const DARK_HEARTWOOD: u8 = 47;
    pub const CEDAR_PLANKS: u8 = 48;
    pub const PALE_PLANKS: u8 = 49;
    pub const DARK_PLANKS: u8 = 50;
    pub const COBBLE: u8 = 51;
    pub const SLATE: u8 = 52;
    pub const CHALK: u8 = 53;
    pub const SANDSTONE: u8 = 54;
    pub const CINDER: u8 = 55;
    pub const STARSTONE: u8 = 56;
    pub const SALT_BLOCK: u8 = 57;
    pub const PALE_STONE: u8 = 58;
    pub const POLISHED_BASALT: u8 = 59;
    pub const POLISHED_ROSESTONE: u8 = 60;
    pub const POLISHED_SLATE: u8 = 61;
    pub const POLISHED_CHALK: u8 = 62;
    pub const POLISHED_SANDSTONE: u8 = 63;
    pub const POLISHED_STARSTONE: u8 = 64;
    pub const POLISHED_PALE_STONE: u8 = 65;
    pub const STONE_BRICKS: u8 = 66;
    pub const BASALT_BRICKS: u8 = 67;
    pub const ROSESTONE_BRICKS: u8 = 68;
    pub const SLATE_BRICKS: u8 = 69;
    pub const SANDSTONE_BRICKS: u8 = 70;
    pub const CHALK_BRICKS: u8 = 71;
    pub const CINDER_BRICKS: u8 = 72;
    pub const SNOW_BRICKS: u8 = 73;
    pub const DUSK_BRICKS: u8 = 74;
    pub const LAVENDER_BRICKS: u8 = 75;
    pub const VERDIGRIS_BRICKS: u8 = 76;
    pub const STONE_TILES: u8 = 77;
    pub const BASALT_TILES: u8 = 78;
    pub const ROSESTONE_TILES: u8 = 79;
    pub const SLATE_TILES: u8 = 80;
    pub const SANDSTONE_TILES: u8 = 81;
    pub const CHALK_TILES: u8 = 82;
    pub const CLAY_TILES: u8 = 83;
    pub const STARSTONE_TILES: u8 = 84;
    pub const VERDIGRIS_TILES: u8 = 85;
    pub const LAVENDER_TILES: u8 = 86;
    pub const THATCH: u8 = 87;
    pub const SHINGLES: u8 = 88;
    pub const CARVED_STONE: u8 = 89;
    pub const MOSAIC: u8 = 90;
    pub const PACKED_EARTH: u8 = 91;
    pub const WATTLE: u8 = 92;
    pub const LINEN: u8 = 93;
    pub const CRIMSON_CLOTH: u8 = 94;
    pub const DUSK_CLOTH: u8 = 95;
    pub const HEATHER: u8 = 96;
    pub const EMBER_LAMP: u8 = 97;
    pub const AETHER_LAMP: u8 = 98;
    pub const VERDIGRIS_LAMP: u8 = 99;
    pub const GREEN_GLASS: u8 = 100;
    pub const AMBER_GLASS: u8 = 101;
    pub const VIOLET_GLASS: u8 = 102;
    pub const STONE_SLAB: u8 = 103;
    pub const COBBLE_SLAB: u8 = 104;
    pub const PLANKS_SLAB: u8 = 105;
    pub const CEDAR_PLANKS_SLAB: u8 = 106;
    pub const PALE_PLANKS_SLAB: u8 = 107;
    pub const DARK_PLANKS_SLAB: u8 = 108;
    pub const BRICKS_SLAB: u8 = 109;
    pub const STONE_BRICKS_SLAB: u8 = 110;
    pub const SANDSTONE_SLAB: u8 = 111;
    pub const SLATE_SLAB: u8 = 112;
    pub const THATCH_SLAB: u8 = 113;
    pub const SHINGLES_SLAB: u8 = 114;
    pub const POLISHED_STONE_SLAB: u8 = 115;
    pub const WAYSTONE: u8 = 116;
    pub const TIDEWELL: u8 = 117;
    pub const FARMLAND: u8 = 118;
    pub const SKYWHEAT: u8 = 119;
    pub const SWEETROOT_CROP: u8 = 120;
    pub const BERRY_CROP: u8 = 121;
    pub const GRASS: u8 = 122;
    pub const WILDFLOWER: u8 = 123;
    pub const MUSHROOM: u8 = 124;
    pub const PEBBLE: u8 = 125;
    pub const SHRUB: u8 = 126;
    pub const REEDS: u8 = 127;
    pub const SIGNPOST: u8 = 128;
    pub const SNOW_PATTERNED_TILE: u8 = 129;
    pub const PEARL_PATTERNED_TILE: u8 = 130;
    pub const ASH_PATTERNED_TILE: u8 = 131;
    pub const INK_PATTERNED_TILE: u8 = 132;
    pub const ROSE_PATTERNED_TILE: u8 = 133;
    pub const EMBER_PATTERNED_TILE: u8 = 134;
    pub const HONEY_PATTERNED_TILE: u8 = 135;
    pub const LEAF_PATTERNED_TILE: u8 = 136;
    pub const MOSS_PATTERNED_TILE: u8 = 137;
    pub const TIDE_PATTERNED_TILE: u8 = 138;
    pub const SKY_PATTERNED_TILE: u8 = 139;
    pub const INDIGO_PATTERNED_TILE: u8 = 140;
    pub const VIOLET_PATTERNED_TILE: u8 = 141;
    pub const ORCHID_PATTERNED_TILE: u8 = 142;
    pub const BLUSH_PATTERNED_TILE: u8 = 143;
    pub const COCOA_PATTERNED_TILE: u8 = 144;
    pub const SNOW_TERRAZZO: u8 = 145;
    pub const PEARL_TERRAZZO: u8 = 146;
    pub const ASH_TERRAZZO: u8 = 147;
    pub const INK_TERRAZZO: u8 = 148;
    pub const ROSE_TERRAZZO: u8 = 149;
    pub const EMBER_TERRAZZO: u8 = 150;
    pub const HONEY_TERRAZZO: u8 = 151;
    pub const LEAF_TERRAZZO: u8 = 152;
    pub const MOSS_TERRAZZO: u8 = 153;
    pub const TIDE_TERRAZZO: u8 = 154;
    pub const SKY_TERRAZZO: u8 = 155;
    pub const INDIGO_TERRAZZO: u8 = 156;
    pub const VIOLET_TERRAZZO: u8 = 157;
    pub const ORCHID_TERRAZZO: u8 = 158;
    pub const BLUSH_TERRAZZO: u8 = 159;
    pub const COCOA_TERRAZZO: u8 = 160;
    pub const SNOW_WOVEN_PANEL: u8 = 161;
    pub const PEARL_WOVEN_PANEL: u8 = 162;
    pub const ASH_WOVEN_PANEL: u8 = 163;
    pub const INK_WOVEN_PANEL: u8 = 164;
    pub const ROSE_WOVEN_PANEL: u8 = 165;
    pub const EMBER_WOVEN_PANEL: u8 = 166;
    pub const HONEY_WOVEN_PANEL: u8 = 167;
    pub const LEAF_WOVEN_PANEL: u8 = 168;
    pub const MOSS_WOVEN_PANEL: u8 = 169;
    pub const TIDE_WOVEN_PANEL: u8 = 170;
    pub const SKY_WOVEN_PANEL: u8 = 171;
    pub const INDIGO_WOVEN_PANEL: u8 = 172;
    pub const VIOLET_WOVEN_PANEL: u8 = 173;
    pub const ORCHID_WOVEN_PANEL: u8 = 174;
    pub const BLUSH_WOVEN_PANEL: u8 = 175;
    pub const COCOA_WOVEN_PANEL: u8 = 176;
    pub const SNOW_STAINED_GLASS: u8 = 177;
    pub const PEARL_STAINED_GLASS: u8 = 178;
    pub const ASH_STAINED_GLASS: u8 = 179;
    pub const INK_STAINED_GLASS: u8 = 180;
    pub const ROSE_STAINED_GLASS: u8 = 181;
    pub const EMBER_STAINED_GLASS: u8 = 182;
    pub const HONEY_STAINED_GLASS: u8 = 183;
    pub const LEAF_STAINED_GLASS: u8 = 184;
    pub const MOSS_STAINED_GLASS: u8 = 185;
    pub const TIDE_STAINED_GLASS: u8 = 186;
    pub const SKY_STAINED_GLASS: u8 = 187;
    pub const INDIGO_STAINED_GLASS: u8 = 188;
    pub const VIOLET_STAINED_GLASS: u8 = 189;
    pub const ORCHID_STAINED_GLASS: u8 = 190;
    pub const BLUSH_STAINED_GLASS: u8 = 191;
    pub const COCOA_STAINED_GLASS: u8 = 192;
    pub const SNOW_CRYSTAL_LAMP: u8 = 193;
    pub const PEARL_CRYSTAL_LAMP: u8 = 194;
    pub const ASH_CRYSTAL_LAMP: u8 = 195;
    pub const INK_CRYSTAL_LAMP: u8 = 196;
    pub const ROSE_CRYSTAL_LAMP: u8 = 197;
    pub const EMBER_CRYSTAL_LAMP: u8 = 198;
    pub const HONEY_CRYSTAL_LAMP: u8 = 199;
    pub const LEAF_CRYSTAL_LAMP: u8 = 200;
    pub const MOSS_CRYSTAL_LAMP: u8 = 201;
    pub const TIDE_CRYSTAL_LAMP: u8 = 202;
    pub const SKY_CRYSTAL_LAMP: u8 = 203;
    pub const INDIGO_CRYSTAL_LAMP: u8 = 204;
    pub const VIOLET_CRYSTAL_LAMP: u8 = 205;
    pub const ORCHID_CRYSTAL_LAMP: u8 = 206;
    pub const BLUSH_CRYSTAL_LAMP: u8 = 207;
    pub const COCOA_CRYSTAL_LAMP: u8 = 208;
    pub const SNOW_BANNER: u8 = 209;
    pub const PEARL_BANNER: u8 = 210;
    pub const ASH_BANNER: u8 = 211;
    pub const INK_BANNER: u8 = 212;
    pub const ROSE_BANNER: u8 = 213;
    pub const EMBER_BANNER: u8 = 214;
    pub const HONEY_BANNER: u8 = 215;
    pub const LEAF_BANNER: u8 = 216;
    pub const MOSS_BANNER: u8 = 217;
    pub const TIDE_BANNER: u8 = 218;
    pub const SKY_BANNER: u8 = 219;
    pub const INDIGO_BANNER: u8 = 220;
    pub const VIOLET_BANNER: u8 = 221;
    pub const ORCHID_BANNER: u8 = 222;
    pub const BLUSH_BANNER: u8 = 223;
    pub const COCOA_BANNER: u8 = 224;
    pub const IVORY_PLASTER: u8 = 225;
    pub const BLUSH_PLASTER: u8 = 226;
    pub const SAGE_PLASTER: u8 = 227;
    pub const DUSK_PLASTER: u8 = 228;
    pub const PEWTER: u8 = 229;
    pub const BRASS: u8 = 230;
    pub const COPPER: u8 = 231;
    pub const WROUGHT_IRON: u8 = 232;
    pub const OCHRE_BRICKS: u8 = 233;
    pub const INK_BRICKS: u8 = 234;
    pub const WOOD_LATTICE: u8 = 235;
    pub const PALE_LATTICE: u8 = 236;
    pub const ROSE_JELLY: u8 = 237;
    pub const TIDE_JELLY: u8 = 238;
    pub const HONEY_JELLY: u8 = 239;
    pub const VIOLET_JELLY: u8 = 240;
    pub const INK_CHECKER: u8 = 241;
    pub const ROSE_CHECKER: u8 = 242;
    pub const ROSE_STRIPE: u8 = 243;
    pub const SKY_STRIPE: u8 = 244;
    pub const SHIMMER_CLOUD: u8 = 245;
    pub const COSMIC_STAR: u8 = 246;
    pub const BLOSSOM_CANOPY: u8 = 247;
    pub const AUTUMN_CANOPY: u8 = 248;
    pub const FROST_CANOPY: u8 = 249;
    pub const VIOLET_CANOPY: u8 = 250;
    pub const GOLDEN_CANOPY: u8 = 251;
}

/// Resolve a `materials.py` snake_case id (`ink_terrazzo`) to the stable material id.
pub fn id_named(name: &str) -> Option<u8> {
    let want = name.replace('_', " ");
    MATS.iter().position(|m| m.name.eq_ignore_ascii_case(&want)).map(|i| i as u8)
}

#[inline]
pub fn get(id: u8) -> &'static Mat {
    &MATS[id as usize]
}

#[inline]
pub fn is_solid(id: u8) -> bool {
    id != 0 && MATS[id as usize].solid
}

/// Water hides water. Opaque solids hide each other. Glass and decorations do not.
#[inline]
pub fn hides_face(neighbor: u8, self_id: u8) -> bool {
    if neighbor == 0 || self_id == 0 {
        return false;
    }
    if self_id == id::WATER {
        return neighbor == id::WATER;
    }
    let n = &MATS[neighbor as usize];
    n.solid && n.kind != KIND_GLASS
}
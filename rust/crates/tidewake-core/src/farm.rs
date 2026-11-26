//! Till, plant and harvest. Stages and yields match `farming.py`.

pub const HOE: u16 = 311;
pub const GRAIN_SEEDS: u16 = 312;
pub const ROOT_SEEDS: u16 = 313;
pub const BERRY_SEEDS: u16 = 314;
pub const WHEAT: u16 = 315;
pub const STAGES: u8 = 4;

pub fn plant_of(seed: u16) -> Option<u8> {
    use crate::materials::id;
    match seed {
        GRAIN_SEEDS => Some(id::SKYWHEAT),
        ROOT_SEEDS => Some(id::SWEETROOT_CROP),
        BERRY_SEEDS => Some(id::BERRY_CROP),
        _ => None,
    }
}

pub fn tillable(mat: u8) -> bool {
    use crate::materials::id;
    mat == id::TURF || mat == id::LOAM || crate::materials::id_named("packed_earth") == Some(mat) || crate::materials::id_named("heather") == Some(mat)
}

/// Seconds until the next growth try. Wet beds try twice as often, matching the sim.
pub fn grow_interval(wet: bool) -> f32 {
    if wet { 6.0 } else { 12.0 }
}

/// Drops for a crop at this stage. Ripe plants give produce and a seed.
pub fn harvest(mat: u8, meta: u8) -> Vec<(u16, u16)> {
    use crate::materials::id;
    let Some((produce, n, seed)) = crop(mat) else { return Vec::new() };
    if meta >= STAGES - 1 {
        vec![(produce, n), (seed, 1)]
    } else {
        vec![(seed, 1)]
    }
}

fn crop(mat: u8) -> Option<(u16, u16, u16)> {
    use crate::materials::id;
    if mat == id::SKYWHEAT {
        Some((WHEAT, 2, GRAIN_SEEDS))
    } else if mat == id::SWEETROOT_CROP {
        Some((317, 1, ROOT_SEEDS))
    } else if mat == id::BERRY_CROP {
        Some((crate::craft::BERRIES, 2, BERRY_SEEDS))
    } else {
        None
    }
}

pub fn is_crop(mat: u8) -> bool {
    crop(mat).is_some()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::materials::id;

    #[test]
    fn ripe_wheat_yields_grain_and_a_seed() {
        let drops = harvest(id::SKYWHEAT, 3);
        assert!(drops.iter().any(|d| d.0 == WHEAT));
        assert!(drops.iter().any(|d| d.0 == GRAIN_SEEDS));
        assert!(harvest(id::SKYWHEAT, 1).iter().all(|d| d.0 == GRAIN_SEEDS));
    }
}

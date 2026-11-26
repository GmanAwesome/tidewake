//! The twenty landscapes, in the same order as `materials.REALMS`.

pub const MEADOW: i64 = 0;
pub const AMBER: i64 = 1;
pub const ROSE: i64 = 2;
pub const FROST: i64 = 3;
pub const BASALT: i64 = 4;
pub const FEN: i64 = 5;
pub const DUNE: i64 = 6;
pub const LUMEN: i64 = 7;
pub const SALTWIND: i64 = 8;
pub const CEDAR: i64 = 9;
pub const LAVENDER: i64 = 10;
pub const CINDER: i64 = 11;
pub const CHALK: i64 = 12;
pub const STARFALL: i64 = 13;
pub const CLOUDSTEP: i64 = 14;
pub const VERDIGRIS: i64 = 15;
pub const BLOSSOM: i64 = 16;
pub const AUTUMN: i64 = 17;
pub const AZURE: i64 = 18;
pub const GOLDEN: i64 = 19;

pub const N_REALMS: usize = 20;

pub const REALM_NAMES: [&str; N_REALMS] = [
    "Meadow Isles",
    "Amberwood",
    "Rose Mesas",
    "Frostglass",
    "Basalt Steps",
    "Mossfen",
    "Duneglass",
    "Lumen Grove",
    "Saltwind Flats",
    "Cedar Highlands",
    "Lavender Downs",
    "Cinder Spires",
    "Chalk Barrens",
    "Starfall Veil",
    "Cloudstep Isles",
    "Verdigris Canyons",
    "Blossom Vale",
    "Autumn Wilds",
    "Azure Fields",
    "Golden Steppe",
];

#[inline]
pub fn one_of(realm: i64, set: &[i64]) -> bool {
    set.contains(&realm)
}

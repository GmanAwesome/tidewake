//! The Path. Node titles and the counts that unlock them match `achievements.py`.

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Stats {
    pub mined: u32,
    pub crafted: u32,
    pub placed: u32,
    pub doors: u32,
    pub motes: u32,
    pub fished: u32,
    pub tilled: u32,
    pub farmed: u32,
    pub smelted: u32,
    pub spires: u32,
    pub gifts: u32,
    pub play: f32,
    pub waystones: u32,
    pub tinker: u32,
    pub achieved: Vec<String>,
}

impl Default for Stats {
    fn default() -> Self {
        Self {
            mined: 0,
            crafted: 0,
            placed: 0,
            doors: 0,
            motes: 0,
            fished: 0,
            tilled: 0,
            farmed: 0,
            smelted: 0,
            spires: 0,
            gifts: 0,
            play: 0.0,
            waystones: 0,
            tinker: 0,
            achieved: Vec::new(),
        }
    }
}

/// id, title, parent, how
const NODES: &[(&str, &str, Option<&str>, &str)] = &[
    ("first", "First steps", None, "Mine a block, or wander for a moment."),
    ("gather", "Gatherer", Some("first"), "Mine 24 cells."),
    ("craft", "Crafter", Some("first"), "Craft something at the pocket grid."),
    ("tinker", "Tinker", Some("craft"), "Place a Tinker Bench."),
    ("kiln", "Kiln tender", Some("tinker"), "Smelt something."),
    ("build", "Builder", Some("craft"), "Place 20 blocks."),
    ("hatch", "Doors and ladders", Some("build"), "Place or open a door."),
    ("wander", "Mote catcher", Some("first"), "Catch a mote of Glimmer."),
    ("shrine", "Wayfarer", Some("wander"), "Attune a waystone."),
    ("font", "Tidewell gift", Some("shrine"), "Buy a Tidewell gift."),
    ("angler", "Angler", Some("first"), "Catch a fish."),
    ("plant", "Planter", Some("first"), "Till a bed."),
    ("harvest", "Harvest", Some("plant"), "Harvest a ripe crop."),
    ("spire", "Spire waker", Some("first"), "Wake a spire."),
];

fn earned(s: &Stats, id: &str) -> bool {
    match id {
        "first" => s.mined >= 1 || s.play > 20.0,
        "gather" => s.mined >= 24,
        "craft" => s.crafted >= 1,
        "tinker" => s.tinker >= 1,
        "kiln" => s.smelted >= 1,
        "build" => s.placed >= 20,
        "hatch" => s.doors >= 1,
        "wander" => s.motes >= 1,
        "shrine" => s.waystones >= 1,
        "font" => s.gifts >= 1,
        "angler" => s.fished >= 1,
        "plant" => s.tilled >= 1,
        "harvest" => s.farmed >= 1,
        "spire" => s.spires >= 1,
        _ => false,
    }
}

/// Unlock every node whose parent is already earned. Returns new titles.
pub fn poll(stats: &mut Stats) -> Vec<&'static str> {
    let mut titles = Vec::new();
    loop {
        let mut added = false;
        for (id, title, parent, _) in NODES {
            if stats.achieved.iter().any(|a| a == id) {
                continue;
            }
            if let Some(p) = parent {
                if !stats.achieved.iter().any(|a| a == p) {
                    continue;
                }
            }
            if earned(stats, id) {
                stats.achieved.push((*id).into());
                titles.push(*title);
                added = true;
            }
        }
        if !added {
            break;
        }
    }
    titles
}

pub fn lines(stats: &Stats) -> Vec<String> {
    NODES
        .iter()
        .map(|(id, title, _, how)| {
            let mark = if stats.achieved.iter().any(|a| a == id) { "done" } else { "open" };
            format!("{mark}  {title} — {how}")
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mining_opens_first_steps_then_gatherer() {
        let mut s = Stats::default();
        s.mined = 1;
        assert_eq!(poll(&mut s), vec!["First steps"]);
        s.mined = 24;
        assert_eq!(poll(&mut s), vec!["Gatherer"]);
    }
}

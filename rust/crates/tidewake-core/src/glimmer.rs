//! Glimmer, waystones and the Tidewell. Costs match `glimmer.py`.

pub const WAYSTONE_COST: i32 = 1;

/// id, title, cost. Cheapest first, as in the Python list.
pub const GIFTS: &[(&str, &str, i32)] = &[
    ("sense", "Mote Sense", 2),
    ("reach", "Keen Reach", 3),
    ("lightfoot", "Lightfoot", 3),
    ("breath", "Deep Breath", 3),
    ("brightwake", "Brightwake", 4),
];

#[derive(Clone, Debug)]
pub struct Glimmer {
    pub motes: i32,
    gifts: [bool; 5],
    pub waystones: i32,
}

impl Default for Glimmer {
    fn default() -> Self {
        Self { motes: 0, gifts: [false; 5], waystones: 0 }
    }
}

impl Glimmer {
    pub fn catch_mote(&mut self) {
        self.motes += 1;
    }

    pub fn attune(&mut self) -> bool {
        if self.motes < WAYSTONE_COST {
            return false;
        }
        self.motes -= WAYSTONE_COST;
        self.waystones += 1;
        true
    }

    pub fn buy(&mut self, id: &str) -> bool {
        let Some(i) = GIFTS.iter().position(|g| g.0 == id) else { return false };
        if self.gifts[i] || self.motes < GIFTS[i].2 {
            return false;
        }
        self.motes -= GIFTS[i].2;
        self.gifts[i] = true;
        true
    }

    pub fn has(&self, id: &str) -> bool {
        GIFTS.iter().position(|g| g.0 == id).map(|i| self.gifts[i]).unwrap_or(false)
    }

    /// The cheapest gift this sky does not already have.
    pub fn next_gift(&self) -> Option<&'static str> {
        GIFTS.iter().find(|g| !self.has(g.0)).map(|g| g.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tidewell_costs_match_the_python_list() {
        assert_eq!(WAYSTONE_COST, 1);
        assert_eq!(GIFTS[0].2, 2);
        assert_eq!(GIFTS[4].2, 4);
        let mut g = Glimmer { motes: 1, ..Glimmer::default() };
        assert!(!g.buy("sense"));
        assert!(g.attune());
        assert_eq!(g.motes, 0);
        g.motes = 2;
        assert!(g.buy("sense"));
        assert!(g.has("sense"));
        assert!(!g.buy("sense"));
        assert_eq!(g.next_gift(), Some("reach"));
    }
}

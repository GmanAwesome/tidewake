# Tidewake 1.4 — progress notes

Short plain-English notes as each Phase 1 piece lands, so it's easy to follow along. Screenshots live in `screenshots-final/v1.4-phase1/` (they're play-test captures, not in the git tree).

---

## November 25, 2026, 2:36 PM EST — Scale

The player is now about two blocks tall. Blocks themselves are a little taller (each layer is 0.85 units instead of 0.7), and you stand just under two layers high so you can still walk through a 2-block door or tunnel. Jump was raised so it still clears a single block. Mining reach is the same in world units, so gathering still feels close and comfortable.

Screenshot: `screenshots-final/v1.4-phase1/01_scale_door.png` (standing eye-height in front of a 2-block doorway).

## November 25, 2026, 2:37 PM EST — Kiln counts

The kiln was showing the wrong number of items: if two slots had the same count (for example two stacks of 16), they fought over one label and one of them would vanish or jump. Labels now remember where they are on the screen, and the kiln always writes the count, even for a single item. Loading a sky no longer breaks if a stack had no "uses" value.

Screenshot: `screenshots-final/v1.4-phase1/08_kiln_counts.png` (sand, fuel and glass all showing 16 in the right places).

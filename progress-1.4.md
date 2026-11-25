# Tidewake 1.4 — progress notes

Short plain-English notes as each Phase 1 piece lands, so it's easy to follow along. Screenshots live in `screenshots-final/v1.4-phase1/` (they're play-test captures, not in the git tree).

---

## November 25, 2026, 2:36 PM EST — Scale

The player is now about two blocks tall. Blocks themselves are a little taller (each layer is 0.85 units instead of 0.7), and you stand just under two layers high so you can still walk through a 2-block door or tunnel. Jump was raised so it still clears a single block. Mining reach is the same in world units, so gathering still feels close and comfortable.

Screenshot: `screenshots-final/v1.4-phase1/01_scale_door.png` (standing eye-height in front of a 2-block doorway).

## November 25, 2026, 2:37 PM EST — Kiln counts

The kiln was showing the wrong number of items: if two slots had the same count (for example two stacks of 16), they fought over one label and one of them would vanish or jump. Labels now remember where they are on the screen, and the kiln always writes the count, even for a single item. Loading a sky no longer breaks if a stack had no "uses" value.

Screenshot: `screenshots-final/v1.4-phase1/08_kiln_counts.png` (sand, fuel and glass all showing 16 in the right places).

## November 25, 2026, 2:37 PM EST — Creatures standing still

Woolhops and other creatures were bouncing up and down in place. Gravity was still being applied after they had already landed, so they kept sinking into the ground and popping back up. They now rest on the surface when they're standing, and only fall when they're actually in the air.

Screenshot: `screenshots-final/v1.4-phase1/11_mob.png` (a woolhop standing calmly on the grass).

## November 25, 2026, 2:38 PM EST — Rain

Rain used to fall in stiff, perfectly straight lines that lined up with the hex grid, so it looked like a cage of water. Drops now start at their own scattered places around you, drift with a little wind, and each one wobbles slightly. They also draw as short streaks, so a shower is easy to see against the sky.

Screenshot: `screenshots-final/v1.4-phase1/09_rain.png`.

## November 25, 2026, 2:38 PM EST — Held tools

A pick or hatchet in your hand was pointed off to the side, not toward the block you were aiming at. Tools now line up with your look, and the swing pitches the head forward the way you'd actually strike.

Screenshot: `screenshots-final/v1.4-phase1/10_held_tool.png`.

## November 25, 2026, 2:38 PM EST — Falling off the world

If you walked off an island, the clouds used to set you down right on the grass, which felt like a hard teleport. They now carry you back high in the air (ten layers above the land) so you drop in and land on your feet.

Screenshot: `screenshots-final/v1.4-phase1/12_fall_respawn.png` (the view from that high drop-in).

## November 25, 2026, 2:39 PM EST — Crouch

You can crouch by holding Shift. The camera drops, you walk more slowly, and you won't step off a ledge while you're crouched (the way sneaking works in similar games). Hurry is now Ctrl, so Shift can stay on crouch. If you're flying, Shift still also moves you down, like you'd expect.

Screenshot: `screenshots-final/v1.4-phase1/02_crouch_door.png` (same doorway as the standing shot, camera lower, more ground in view).

## November 25, 2026, 2:39 PM EST — Doors

Doors are in the game. Craft three from six planks (a 2×3 of planks at the Tinker Bench). A door is two blocks tall, faces you when you place it, and right-click opens or closes it. Closed doors block the way; open doors you can walk through. They have a thin wooden panel and a little handle, not a solid cube, and they swing when they open.

Screenshot: `screenshots-final/v1.4-phase1/01_scale_door.png` and `03_doors.png` (a closed door in a hut, and a second doorway standing open).

## November 25, 2026, 2:40 PM EST — Ladders

Ladders are craftable too: an H-shape of sticks at the bench makes three of them. Place a ladder against a wall and it hangs there with the rungs toward you. Climb it the same way you climb vines — hold jump to go up, and you can come down it as well.

Screenshot: `screenshots-final/v1.4-phase1/04_ladder.png` and `05_ladder_wall.png`.

## November 25, 2026, 2:40 PM EST — Leaf decay

Leaves no longer float forever after you chop a tree. If a canopy block can't reach a log (heartwood) through other leaves, within about four blocks, it withers away. Chopping a trunk or leaves wakes the nearby canopy, so a tree comes down naturally from the cut outward.

Screenshot: `screenshots-final/v1.4-phase1/06_leaves_before.png` and `07_leaves_after.png` (same view, before and after the trunk was removed).

## November 25, 2026, 2:41 PM EST — Pre-release posted

Phase 1 is up as a pre-release so you can play it on Windows without it replacing 1.3.4 as the usual download. Grab `Tidewake-1.4-phase1-Windows.zip` from https://github.com/GmanAwesome/tidewake/releases/tag/v1.4-phase1 (about 76.6 MB). The play-test screenshots are attached on that page too.

Known leftover: the first launch still takes about a minute to compose the music (same as 1.3.3+). That's not new, and you can play while it works.

## November 25, 2026, 2:57 PM EST — Terrain variety

New skies no longer feel like the same rolling bump repeated. Each region now leans toward plains, rolling hills, cut valleys, or a mountain range — and the mountains themselves come in a few styles (sharp ridges, broader alpine slopes, or stepped plateaus). Older skies keep their original generator so already-explored land doesn’t change.

Screenshot: `screenshots-final/v1.4-phase2a/07_cloudstep_isles.png` (high, broken ranges over the cloud sea).

## November 25, 2026, 2:57 PM EST — Thicker islands

Islands are much thicker in most places — about three times the old depth on a typical new sky — and the thickness clearly varies from the rim to the heart of an island. Each island also sits at its own height: some hang lower over the clouds, some much higher. You can push this further with the Island thickness slider (thin about 28 layers, thick about 62).

Screenshot: `screenshots-final/v1.4-phase2a/10_thick_island.png` (a cut through the inside of a thick island).

## November 25, 2026, 2:58 PM EST — Bigger, more connected caves

Caves under new islands are more open and less like a single narrow worm. You’ll find winding tunnels, wider rooms of a few different sizes, the occasional tall fissure, and longer “highways” that stitch chambers together. Cave amount and Cave size on the new-sky screen change how often they appear and how roomy they feel.

Screenshot: `screenshots-final/v1.4-phase2a/10_thick_island.png` and `12_cave.png`.

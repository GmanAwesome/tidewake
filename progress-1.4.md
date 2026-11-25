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

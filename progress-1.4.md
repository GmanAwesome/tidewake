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

## November 25, 2026, 2:58 PM EST — Eight new landscapes

Eight new biomes join the original eight, using existing blocks with new colors, plants and layouts (no new block types yet). The real-world-inspired ones are Saltwind Flats, Cedar Highlands, Lavender Downs, Cinder Spires and Chalk Barrens. The fictional ones are Starfall Veil, Cloudstep Isles and Verdigris Canyons. Each has its own turf color, trees or crystals, and a little gameplay flavor (wood, clay, ores, high overlooks, and so on).

Screenshots: `screenshots-final/v1.4-phase2a/01_lavender_downs.png` through `08_verdigris_canyons.png`.

## November 25, 2026, 2:58 PM EST — World creation sliders

Dreaming a new sky now opens a proper setup screen with twelve labeled sliders: island size, island thickness, sky density, terrain roughness, mountain height, flatness, cave amount, cave size, water, biome size, tree density and Glimmer rarity. 50 is the usual mid setting, Reset puts them all back, and the values are saved with the sky so they come back the next time you play it.

Screenshot: `screenshots-final/v1.4-phase2a/00_sliders.png`.

## November 25, 2026, 2:59 PM EST — Pre-release posted

Phase 2a is up as a pre-release, so it doesn’t replace 1.3.4 as the usual download. Grab `Tidewake-1.4-phase2a-Windows.zip` from https://github.com/GmanAwesome/tidewake/releases/tag/v1.4-phase2a (about 76.6 MB). The play-test screenshots are on that page too.

Older skies still use the previous generator. Brand-new skies get the new land, caves, biomes and sliders. First launch still spends about a minute composing the music, same as before.

## November 25, 2026, 3:02 PM EST — Less holey ground

Arches and cave mouths no longer punch holes just under the grass. New skies keep a solid five-layer roof over both, and arches themselves are rarer, so you can walk a meadow without dropping into a pocket every few steps. Caves still open up once you dig down. Older skies are unchanged.


## November 25, 2026, 3:10 PM EST — New blocks

The block list is much bigger now: cedar, pale and dark woods (and their planks), a stone family (cobble, slate, chalk, sandstone, cinder, starstone, salt, pale stone) with polished, brick and tile versions in many colours, plus thatch, shingles, carved stone, mosaic, wattle, cloth, heather, coloured lamps, tinted glass, and slabs you can actually stand on. Everything is still drawn with our own procedural textures — the inspiration folder was only a style reference, no pixels were copied. Each new block has a crafting recipe, and the new biomes now use their own stone and wood (chalk, sandstone, cinder, starstone, cedar and pale logs, heather, salt). Glass — clear and tinted — is nearly see-through from every angle, with just a faint rim.


## November 25, 2026, 3:16 PM EST — Structures

New skies can now grow points of interest that feel like they belong on the islands. A small framework places modular pieces with rules for slope, island thickness, biome and spacing, then weathers them as intact, abandoned, ruined or overgrown (debris, lamps, vines, loot). There are three families to start: settlements (a single hut up to a little village with paths, a well and a shed), ruins (a temple, a ring of standing stones, or a buried chamber with rarer things in the chest), and a sky boat moored at an island edge with a walkway back to land. Each one gives you a reason to stop — a bed, a bench or kiln, or a chest of supplies. Older skies are unchanged.


## November 25, 2026, 3:25 PM EST — Pre-release posted

Phase 2b is up as a pre-release, so it doesn’t replace 1.3.4 as the usual download. Grab `Tidewake-1.4-phase2b-Windows.zip` from https://github.com/GmanAwesome/tidewake/releases/tag/v1.4-phase2b (about 73 MB). The play-test screenshots are on that page too (block palette, glass, a village, a temple, standing stones, a buried chamber, and a sky boat).

Older skies still use the previous generator and have no generated structures. Brand-new skies get the new blocks in the world, the new recipes, and the settlements, ruins and sky boats.

## November 25, 2026, 3:46 PM EST — Glimmer rarer, waystones, and the Font

Glimmer motes are much rarer now. On a mid setting you see about a third of what you used to, and even a "common" slider is tighter. Catch them at dusk, or spend one at a waystone so the shrine remembers you. After that, right-click any attuned waystone to travel to another you have found. Temples, standing stones, and deep chambers already hold one.

You can also craft a waystone (carved stone and Glimmer) or a Glimmer Font (polished stone and Glimmer). At a Font you spend Glimmer for lasting attunements that save with the sky: Keen Reach, Lightfoot, Deep Breath, Mote Sense, and Brightwake.

## November 25, 2026, 3:49 PM EST — Fishing

Craft a fishing rod from three sticks and a scrap of linen, then right-click a still pool. The bobber sits and waits; when it dips, right-click again to reel. Pull too early, wander off, or miss the dip and the fish gets away. What you catch depends on the landscape and the tide — reed minnows in gentle water, saltskippers on the flats, frostfin in Frostglass, duskperch and the rare glimmerfin after the light fades — and sometimes the line brings up treasure instead. Raw fish are a light snack; roast them in a kiln for a proper meal.

## November 25, 2026, 3:52 PM EST — Farming

A hoe (two sticks and any stone) turns turf, loam, packed earth or heather into a tilled bed. Plant grain, root or duskberry seeds on it; the plants grow through four stages, faster in the light and faster still if a pool is close by. Ripe skywheat, sweetroot and berry bushes give food and more seeds — pick them early and you may only get the seed back. Three ears of skywheat bake into a loaf at the tinker bench, and sweetroot roasts in the kiln. Turning turf, breaking petals or digging loam sometimes turns up seeds to start with, and unused dry beds slowly rest back to loam.

## November 25, 2026, 3:55 PM EST — The Path (achievement tree)

Press P, or open The Path from the rest menu, to see a tree of goals for this sky. Each node tells you what to do and how — mining, crafting, the kiln, doors and ladders, catching Glimmer, waystones and the Font, fishing, farming, and waking a spire. What you have already done is remembered with the sky, and a little note appears when a new step is earned.


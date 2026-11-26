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

## November 25, 2026, 4:00 PM EST — Tutorial island

The title screen has a Learn to play button. It opens a small hand-built island called The Lesson, separate from the wandering skies. Friendly people stand along a path and talk in simple bubbles — walking and looking, mining a grove, a tinker bench, a kiln, doors and ladders, a fishing dock, a little farm, and a Glimmer shrine with two waystones and a Font. Chests at each stop hold what you need, a few practice motes drift by the shrine, and gloomlings stay away. If you already started the lesson, the same island is waiting for you.

## November 25, 2026, 4:04 PM EST — Phase 3 tour

Play-test shots for Phase 3 are in `screenshots-final/v1.4-phase3/`: the title screen with Learn to play, the lesson island from above and along the path (welcome, trees, the bench and kiln, doors and ladders, the fishing dock, the farm, and the Glimmer shrine), plus the Path tree and the Font. A few frames were retaken so the yard, the pool, the tilled beds and the Path all read clearly. The version string is now 1.4-phase3.

## November 25, 2026, 4:09 PM EST — Pre-release posted

Phase 3 is up as a pre-release, so it doesn’t replace 1.3.4 as the usual download. Grab `Tidewake-1.4-phase3-Windows.zip` from https://github.com/GmanAwesome/tidewake/releases/tag/v1.4-phase3 (about 74 MB). The play-test screenshots are on that page too (title and Learn to play, the lesson island, the Path, and the Font).

Older skies still use the previous generator. Brand-new skies get rarer Glimmer, waystones and the Font, fishing, farming, and the Path. The lesson island is a separate sky, launched from the title screen.

## November 25, 2026, 4:11 PM EST — Brighter lesson huts, a clear door, and a quiet island

The lesson huts are pale planks now, with glass windows and a lamp inside, so they no longer read as dark caves. Mira's practice door stands in a little frame and sits slightly ajar, so the leaf and handle are obvious. Woolhops and the other wandering creatures stay off the lesson island — it's just you and the guides.

## November 25, 2026, 4:23 PM EST — Skywhales and fairies

Two new creatures share the open air. Skywhales are huge, slow, and peaceful; they drift between islands and only climb if a peak gets in the way. Fairies are tiny glows that hover near flowers, and they come out a little more as dusk comes on. Neither one fights back — they just slip away if you startle them. They stay off the lesson island, like the woolhops.

## November 25, 2026, 4:25 PM EST — More music, in the same family

Four new songs join the procedural soundtrack, and the music cache is now v9 so they build on first listen. Firstlight is a gentle C major piece for the lesson island, with the same public-domain Korobeiniki hint the other songs use. Undertide is slow and watery in F-sharp minor, and comes in when you swim. Rainwake is a soft G minor for rainy weather. Highmere is a brighter A major day song that takes its turn in the daytime rotation. Minecraft and Donkey Kong were style references only — none of their tunes are in here.

## November 25, 2026, 4:26 PM EST — Taller trees you can walk under

Trees got taller, and their leaves start higher up the trunk. You can walk under most canopies now without the leaves sitting on your head. Grown sprouts follow the same idea, and the little grove on the lesson island does too.

## November 25, 2026, 4:27 PM EST — Third-person view

F5 now cycles the camera the way it does in many sandbox games: first person, then behind you, then looking at you, then back again. The camera stops short of walls so it does not slip into the ground. In third person you see a simple figure of yourself, and only what you are actually holding — no default tools or worn loot appear just because the camera moved behind you. The admin panel moved to F7 (still needs dev mode).

## November 25, 2026, 4:28 PM EST — Sleeping fades into a dawn

Resting on a bedroll in the dusk no longer snaps the light back in a blink. The world fades to black, then the tide eases through a dawn and the picture comes back with the morning. Gloomlings are still gone when you wake, and this is still where you will wake if you fall.

## November 25, 2026, 4:28 PM EST — Dreamer middle-click lets go of an item

In Dreamer mode (and while dev mode is on), a middle-click takes an item out of your inventory. Click a slot in the backpack to clear it, or middle-click in the world to let go of whatever you are holding. Wanderer mode is unchanged.

## November 25, 2026, 4:30 PM EST — A rotating title sky

The main menu no longer shows just the lighthouse cottage. It now takes turns through that build and a handful of strong seeds run on the current generator — Bright Arch, Saltwind Bay, Windward Isle, Ember Croft, Sky 4096 and Hardy 1729. Each one orbits for a little while, then the next sky fades into place.

## November 25, 2026, 4:31 PM EST — A new mark, and typography to match

The title screen has a real animated logo now: a pulsing hex crest, wake rings that swell and fade, and the Tidewake wordmark drawn letter by letter so the name itself breathes. A gold tide-line sits under it. Menu type is a little larger and clearer — titles use the display face more confidently, and the buttons have more room. The version string is 1.4-phase4.

## November 25, 2026, 4:35 PM EST — Phase 4 play-test shots

Play-test shots for Phase 4 are in `screenshots-final/v1.4-phase4/`: the new animated title and a seed showcase, the brighter lesson huts and the practice door, trees you can walk under, skywhales, fairies, third-person (behind and looking at you), and the dawn after a rest. The version string is 1.4-phase4.

## November 25, 2026, 4:37 PM EST — Phase 4 pre-release posted

Phase 4 is up as a pre-release, so it doesn’t replace 1.3.4 as the usual download. Grab `Tidewake-1.4-phase4-Windows.zip` from https://github.com/GmanAwesome/tidewake/releases/tag/v1.4-phase4 (about 73 MB). The play-test screenshots are on that page too. This Windows build embeds the Common Controls v6 manifest in the exe (the first Phase 3 zip was missing it; that one has been replaced as well).


## November 25, 2026, 4:42 PM EST — A more whale-like skywhale

Skywhales were reading as a stack of chunky hexes. Their body is longer and flatter now, with a tapered head and tail, thin swept-back fins, a small dorsal ridge, and a horizontal fluke instead of a boxy wing. They still drift the same way; they just look more like a whale in the air.


## November 25, 2026, 4:43 PM EST — A face when the camera looks at you

The third-person figure used to be a blank head with hair all the way around, so the “looking at you” camera mostly showed the back of a head. Hair now sits further back, and there are simple eyes and a mouth on the front. The lesson-island guides got the same treatment, so people in the world read as faces from the front.


## November 25, 2026, 4:43 PM EST — Third-person toasts no longer sit on the figure

The first-session controls hint was drawn near the top of the screen, right over the tide dial, the wayfinder, and any toast that appeared — and in third person those toasts also fought with the “looking at you” figure. The hint now sits just above the hotbar, and toasts tuck under the top chrome instead of covering the middle of the view.


## November 25, 2026, 4:43 PM EST — Buried chambers have light again

A buried chamber often went up without a lamp, because ruined or abandoned rooms skipped the usual light roll, and one hanging lamp was easy to miss in the dark stone. Each chamber now always has a lumen lamp on the ceiling and an ember lamp by the chest, so the room reads as a place you can see, not a black pit at the bottom of the shaft.


## November 25, 2026, 4:44 PM EST — Max cave sliders no longer lace the islands

Turning cave amount and cave size all the way up used to Swiss-cheese the islands: the walking surface held, but the cliffs opened into a lace of holes. The top of those sliders is a little gentler now, rooms stay rooms instead of eating everything, and a solid shell is kept around the outside of each island so caves can still open wide inside without turning the land into cheese.


## November 25, 2026, 4:45 PM EST — A balance pass on Glimmer, food and fishing

Glimmer at the usual mid setting was quietly disappearing in the daytime, because the target count was rounded down to zero. Mid-rarity skies now keep a light daytime trickle, and dusk still feels like the richer time to gather. Fishing bites stay open a little longer, so a fair hook is easier to catch. Food was already in a sensible place: a full bar lasts around half an hour of walking, and a handful of berries or a roast is a real meal, so that was left alone.


## November 25, 2026, 4:47 PM EST — A playtest pass

A scripted play-through now walks the title, the lesson island, a freshly generated sky, and an older 1.3-style sky. It looks for a real tree you can stand under in a generated world (not just the lesson grove), checks that the lesson island stays free of woolhops, and visits a lit buried chamber. Generation of a handful of chunks stays comfortably quick.


## November 25, 2026, 4:49 PM EST — The front view needed a closer look

Eyes on the wanderer were too small to read at the usual camera distance, so the “looking at you” view still felt like a blank head. The eyes are larger now, with a little white around a dark pupil, the hair sits further back, and that camera stands closer so a face is actually visible.


## November 25, 2026, 4:50 PM EST — A real under-canopy shot

The first play-test pass missed a tree in a generated sky, because the wanderer had been left on a bare cinder ridge. The search now looks through the loaded chunks for a trunk and a walkable cell under the leaves, and the tour stands in the Bright Arch grove so the shot is taken under a real canopy in a generated world.


## November 25, 2026, 4:51 PM EST — Version 1.4

The version string is 1.4, and a changelog now covers the whole 1.4 work — new landscapes and sliders, structures and blocks, the lesson island, Glimmer, fishing, farming, the Path, skywhales and fairies, the new songs, taller trees, the third-person camera, a dawn after you rest, and the cohesion fixes.


## November 25, 2026, 4:53 PM EST — A proper GitHub page for 1.4

The README is rewritten as a straightforward front page: a clean title hero, a short pitch, a features overview with screenshots, Windows install (extract the zip, double-click the exe), a controls table, a link to the changelog, and credits that note the music is original and that Korobeiniki is public domain. The pre-release notes are gone. Screenshot originals for the release live in `screenshots-final/v1.4/`; the images the README uses are in `docs/v1.4/`.


## November 25, 2026, 4:55 PM EST — Tidewake 1.4 is out

1.4 is posted as the usual Latest download, not a pre-release. Grab `Tidewake-1.4-Windows.zip` from https://github.com/GmanAwesome/tidewake/releases/tag/v1.4 (about 73 MB). The play-test screenshots are on that page too, and the same set lives in `screenshots-final/v1.4/`. This Windows build embeds the Common Controls v6 manifest and the icon in the exe, checked with pefile. Skies from 1.3 still load and keep their old terrain.


# 1.4.1

## November 25, 2026, 5:09 PM EST — The title menu no longer has gray boxes

The title screen was drawing a big rounded dark panel behind the buttons, and a bar along the bottom, over the showcase sky. Those were the gray boxes. They are gone, so the menu sits cleanly on the sky.


## November 25, 2026, 5:10 PM EST — Lesson NPCs wait to be asked

Walking up to someone on the lesson island used to open their speech on its own. They now only talk when you right-click them. If you are close, a small “Right-click to talk” hint appears, and the conversation closes again when you walk away.


## November 25, 2026, 5:10 PM EST — A different title sky each launch

The title screen always used to open on the same showcase (the Lighthouse Cottage) and only then start taking turns. It now picks a random backdrop when the game starts, and it remembers the last one so the next launch starts somewhere else. After that, the usual rotation continues as before.


## November 25, 2026, 5:12 PM EST — Creatures no longer bounce in place

Creatures were shaking up and down even on flat ground. Two things were stacking: they snapped to a layer-grid line instead of the real top of the block they were standing on (which could throw them up a whole layer), and then each frame they were treated as off the ground because their feet were already clear of the floor, so gravity pulled them in and the snap threw them back up. They now settle to the actual floor top and a short probe under the feet keeps them there. A frame-by-frame y-trace on still and walking woolhops, at a few frame rates, stays flat after landing.


## November 25, 2026, 5:14 PM EST — Lanterns and lamps light their surroundings

Lamps were working in some rooms and not others. The light itself was only collected from the nearest forty chunks, and in a cave full of glowcaps a lantern could be dropped from the short list the shader uses. A lamp placed just inside a chunk also failed to remesh anything but the border neighbour. Lights are now gathered from every loaded chunk, real lamps are kept first, the shader prefers a lantern over a closer glowcap, and placing or breaking a lamp dirties every chunk its light can reach.



## November 25, 2026, 5:17 PM EST — Textures sit in hex space, and log ends are centred

The seams on block tops and sides were not a painted line in most tiles. Tops were mapped from world XZ, so a wrap in the middle of a hex cut through the face, and a log's end-grain rings were off-centre. Sides used world Y divided by 0.7, but a block is 0.85 tall, so a wrap line sat mid-block. Tops now use a UV local to the hex, with (0.5, 0.5) at the column centre, and the tile fits the hex exactly. Sides take V from the vertices, 0 at the bottom of the cell and 1 at the top, and the sample is clamped so the top edge does not wrap back to 0. Heartwood and other wood tops draw their rings in that same hex space so the centre sits on the hex centre. Boards, bricks and grout are still meant to show joints; the mid-face wrap is what is gone.


## November 25, 2026, 5:20 PM EST — Doors are a thin double leaf through the hex

A door used to be a short, offset hexagonal pillar that rotated to one side when opened, so a wall with a doorway did not read as a solid face. It is now a thin plane through the middle of the hex, lined up with neighbouring wall blocks, made of two halves. Opening it swings the halves apart and back, leaving a walkable path. Closed doors still block the cell; open doors are passable. Right-click still opens and closes both halves together.


## November 25, 2026, 5:31 PM EST — Islands hang at many heights, with teardrop undersides and sealed caves

New skies now spread islands across a much wider range of altitudes, from just over the cloud sea to near the top of the world, so looking up can show islands far above and looking down can show them far below. Each island stays on one shelf, and you still spawn on a mid-height island, a short walk from a spire when one is nearby.

The islands themselves are no longer flat slabs. The rim is a short rounded lip, and the underside is an inverted dome that tapers to a teardrop, with the odd stalactite drip. Old skies are unchanged.

Caves no longer punch through hillside faces or leave black gashes on the flanks. Any cave that opens onto the outside is filled back in, the walking surface keeps a solid roof, and a few cobble-framed mouths are cut so the caves can still be entered.


## November 25, 2026, 5:38 PM EST — Richer ground cover, and a roomier lesson island

Each landscape now grows a mix of its own plants and stones: grasses, wildflowers, mushrooms, pebbles, shrubs and reeds, in clusters, with patchy ground-cover like heather and moss. The textures are still drawn by the game, not taken from anywhere else. Old skies keep their original scatter.

The lesson island is larger, with a wide packed-earth path and signposts from station to station. The next person is easier to see, and nobody stands inside a hut, a chest, or a waystone any more — they wait in the open beside their work.


## November 25, 2026, 5:40 PM EST — Version string is 1.4.1-test

The title and the in-game version line now say 1.4.1-test, ready for a pre-release the player can try before the real 1.4.1.


## November 25, 2026, 5:42 PM EST — 1.4.1-test is up as a pre-release

The play-test build is at https://github.com/GmanAwesome/tidewake/releases/tag/v1.4.1-test (not Latest; 1.4 stays the recommended download). The Windows zip is `Tidewake-1.4.1-test-Windows.zip`, about 73 MB, with the Common Controls v6 manifest and icon checked by pefile. After screenshots are in `screenshots-final/v1.4.1/` and also attached to the release.


## November 25, 2026, 5:56 PM EST — Title showcases, now with real player builds

The title screen needed more than one cottage, and the orbit was allowed to fly through leaves and hills. There are now eight hand-built scenes on the new (v2) generator, each meant to look like a player made them: the Lighthouse Cottage rebuilt on a Saltwind cape (seed keeper-of-tides, 79, 3), a fen-side Cliffside Tavern (tavern-cliff, 115, -2), a Windmill Farm with wheat and a little house (salt-wind-bay, 103, -1), a Sky-boat Dock on Windward Isle (168, -35), a High Keep up on a Cloudstep shelf (lantern-point, -62, -24), a Rose Temple and garden above Saltwind Bay (67, 25), a Cedar Treehouse at Ember Croft (74, 123), and a Twin Isles Bridge spanning a short gap (twin-isles, -95, 21 to -87, 21). They use the 1.4 roster — glass, lamps, doors, ladders, slabs, cloth, farmland, decorations.

Each orbit was sampled all the way around (including leaves). If the path clipped a hill or hid the build, the camera was raised, shifted, or limited to a clear arc. The windmill, and a couple of the seed-only skies, use a clear arc so they never duck through a neighbouring canopy. The six seed-only skies stay as extras, with their sites moved onto the current generator so the camera isn't aimed at a vanished hill. Launch still picks a random showcase and skips the one from last time.

A unit test now stamps every showcase and checks the camera path for solid cells.



## November 25, 2026, 6:08 PM EST — Camera paths checked again, more carefully

A first pass of screenshots showed a couple of orbits still grazing a cliff or looking at the build through a wall of leaves. The path check now also rejects a solid sitting close in front of the camera, tree-clearing around the leafy sites was widened, and a few cameras were raised or limited to a clearer arc. Pausing the orbit (or taking a still) no longer snaps an arc camera back to the middle of its swing.




## November 25, 2026, 6:12 PM EST — 1.4.1 is the real release

The version line is 1.4.1, without -test. The changelog and the README download link are updated, and this is going out as a full Latest release rather than another pre-release. The sky-boat dock and Twin Isles Bridge still have room to improve; that is left for a later update.




# 1.4.2

## November 25, 2026, 6:18 PM EST — Starting 1.4.2 from the playtest

Playing 1.4.1 on seed -1740201319, the new altitude bands are making huge straight cliffs, 30–60 layers tall, where two landmasses of different heights still touch. They look like a bug, not a landscape. Islands are also still quite low (the ceiling is 128 layers) and the ground is too flat. This update will give new skies a generator v3 so 1.4.1 worlds stay as they were, pull those bands apart with real sky gaps, let some surfaces reach about layer 300, and put real hills and mountains on the big islands. Before shots are being taken at the places from the playtest.

## November 25, 2026, 6:31 PM EST — Generator v3: gaps instead of walls, surfaces at 300

New skies now use generator version 3. A 1.4.1 save with no version field still means version 2, so those worlds keep their terrain, and the lesson island stays pinned to v2 as well. The column height is 360 (the old 128-layer chunks grow on load), but v1 and v2 still clip to the old ceiling.

v3 pulls land back from a Worley cell edge when the two cells sit on different shelves, so the old 30–60-layer vertical seams become sky. A metric test counts neighbouring land columns whose surface differs by more than 6 layers, over a 180-cell window on two seeds plus the five playtest sites on seed -1740201319: 2,533 such pairs in v2, none in v3 (100% reduction, well past the 90% bar). The steepest remaining v3 step in those windows is 4 layers, so the ground stays mostly 1–2-layer steps, with longer hills, ridged ranges, and eroded mesa skirts instead of a flat shelf.

Shelf centers run from the mid-thirties up to about 292, and relief takes some surfaces to layer 300–304 (seed 7 reached 303, the playtest seed 304, with thousands of columns in the high two-nineties). Spawn on the playtest seed lands at q -4, r 501, surface 105, in the mid window (80–170). A peak on that seed sits at q -192, r -224, surface 304.

Generating and meshing 49 chunks took about 4.5–5 ms each on v3, no slower than v2. A 25-chunk ring around the mid spawn and around that peak both took about 0.25 s. Far-distance LOD still builds (about 0.6 ms per chunk). Lighting, mobs, and the save format follow the new column height; old chunks are padded with empty air above 128. Camera fog is still tied to the load radius, so a 300-high island is in view if it is loaded. Updraft columns between tiers were left for later if travel feels too hard; waystones, glide, and sky boats are unchanged.

## November 25, 2026, 6:38 PM EST — Title showcases on the new sky

The eight player builds and the seed-only title skies now sit on generator v3. The Sky-boat Dock has a much larger boat (a long wide hull, a tall mast and a broad linen sail) and a cleared quay, the Twin Isles Bridge is a 20-hex crossing with wider abutments and a longer covered mid-span, and tree-clearing now removes every kind of heartwood, so leftover trunks no longer stand in the Lighthouse Cottage's inland view (the clear radius there is also wider). Every orbit still passes the camera-path test.

## November 25, 2026, 6:51 PM EST — 1.4.2-test pre-release is ready

The version line is 1.4.2-test. After shots are in `screenshots-final/v1.4.2/`: comparable views at the five playtest sites, a look-up at the tall islands, a look-down from a 292 cliff edge on the high island (lower isles visible far below), and elevated wide shots of the hills, ridges, and sky gaps. Title showcases were photographed on v3 as well. This goes out as a pre-release so 1.4.1 stays Latest.

## November 25, 2026, 6:59 PM EST — 1.4.2 is the real release

The version line is 1.4.2, without -test. The changelog and the README download link are updated, and the title hero and landscape shots on the README now show the new sky. This is going out as a full Latest release rather than another pre-release.

# 1.4.3

## November 25, 2026, 7:13 PM EST — Starting 1.4.3 from the playtest

The lesson island is much slower than a normal sky, some islands still show straight cutoffs where they meet or overlap, and the wanderer should appear unclothed until something is crafted or found and put on. Profiling the tutorial first, then the cut faces, then the default figure.



## November 25, 2026, 7:28 PM EST — Tutorial slowness, cutoffs, and the unclothed wanderer

The tutorial was not remeshing, restamping, or leaking dirty flags. A 5s stand-still profile (vsync off, fps_limit 0, 1280×720) on the lesson island was 13.2 fps (p50 75 ms). Nearly all of that extra time was in `session.dynamic_models`: all 8 lesson NPCs call `models.guide()` every frame, which rebuilds prism meshes from scratch (`models.prisms` / `_faces_side`, 64 prism batches per frame, 3.26 s of a 5 s sample). Jobs, remesh, set() and collect exceptions were all zero; 258 chunks had already settled, 9 lights. A normal v3 sky on this box was also heavy to draw (frame times hit the 100 ms dt clamp, so reported fps was 10), but it spent almost nothing in figure meshing — on a machine where a normal sky is 60 fps, that ~65 ms/frame of prism work is what makes the lesson feel uniquely slow. Guide and wanderer poses are now cached.

Straight cutoffs on seed -857535443 were Worley cell-edge pullbacks (`need_gap` along f2-f1, a square XZ grid, so long walls ran along hex axes) slicing one landmass, plus natural e=0 coasts that happened to be ruler-straight, plus low islands whose underside was clipped to a flat plane at layer 2. Different-band shelves already had a sky gap, but the margin was a straight Voronoi plane. Height-blending those shelves reintroduced 28-layer steps, so 1.4.3 keeps a gap for separated shelves and makes the margin wander, nibbles only the land mask (never adds a cell, so walkable steps stay ≤6), and compresses a too-deep underside instead of slicing it flat at the floor. Overlapping [bottom, top] volumes in the reported windows went to 0. The 25-cell wall at Cloudstep Isles is gone; remaining hex-axis coasts are ≤17 cells. `tests/test_phase143.py` flags 18+ cell ruler walls, 16+ cell canyons, and volume overlaps. 1.4.2 sheer-cliff tests still pass (0 v3 seams).

The third-person wanderer is a uniform skin-tone mannequin with no outfit colours, plus two simple cheek blocks on the back of the hips. Gear still attaches only when a crafted or found item is held. Lesson guides keep their clothes.

## November 25, 2026, 7:32 PM EST — 1.4.3-test numbers and shots

Same measurement in both worlds, vsync off, fps_limit 0, 1280×720, wall-clock frames/seconds after settle:

- Tutorial before: 13.2 fps still / 11.3 walk (p50 75–86 ms). `dynamic_models` rebuilt 8 NPC prism meshes every frame (3.26 s of a 5 s stand, 64 prism batches/frame). No remesh, dirty, or job leak.
- Tutorial after (cached poses): 42.7 fps still / 47.1 walk.
- Normal v3 world (seed -1740201319) after: 7.1 fps still / 7.8 walk (76 chunks drawn, 32 lights). Before, frame_times were clamped at 100 ms so it read as 10 fps; wall-clock is the fair figure. The lesson is now faster than a normal sky on this box, which is what we wanted.

Cutoff after-shots for seed -857535443 were taken at the seven reported positions (debug HUD has the same x,y,z, cell, and seed). The 25-cell Cloudstep wall is gone; coasts look irregular and undersides are domed. A few hex-axis beaches of up to 17 cells can still appear, which the test allows (it flags 18+ and volume overlaps, both zero). The wanderer back-view shows a plain skin-tone figure with a small hip bulge and no outfit. Shots are in `screenshots-final/v1.4.3/`. Version string is 1.4.3-test; next step is the Windows pre-release, with 1.4.2 staying Latest.

## November 25, 2026, 7:35 PM EST — 1.4.3-test pre-release is up

https://github.com/GmanAwesome/tidewake/releases/tag/v1.4.3-test is a pre-release (target `main` / `42d3967`). 1.4.2 remains Latest. Assets: `Tidewake-1.4.3-test-Windows.zip` (manifest 1294 bytes, comctl32 v6, RT_ICON 6 + RT_GROUP_ICON 1) and `Tidewake-1.4.3-test-screenshots.zip`, plus a few individual shots (wanderer back/front, tutorial before/after, two cutoff afters).

## November 25, 2026, 7:48 PM EST — 1.4.3 round 2 starts

The first after-shots were not usable: too few chunks were drawn, the views were hazy and distant, and some still said 1.4.2. Round 2 redoes the cutoff check at the user's seven positions with a long view distance (about 1310 loaded, jobs 0, drawn in the same range as theirs), then, if straight cuts remain, switches new skies to generator v4: discrete islands with spacing so volumes do not intersect, no Worley shelf cut planes, and no chunk or region clamps. v1–v3 stay for old saves; the lesson island stays pinned. The wanderer's hips should read as part of the body (cheeks partly sunk into the torso, centre cleft, rounded lift, no z-fighting). Before-shots of the current v3 at full load are starting now.

## November 25, 2026, 8:24 PM EST — 1.4.3 round 2 (v4 islands, embedded hips)

Full-load v3 before-shots at the seven reported sites (seed `-857535443`, exact xyz, view_distance 20 / far 35) settled to 1243–1306 loaded, jobs 0, and 165–252 drawn, at 1280×720, labelled 1.4.3-test. The leftover cuts are clear: a long straight canyon at Chalk Barrens high, a vertical cut plane at Cloudstep far, and a flat-sliced underside in the Cloudstep side/under views. Exact user yaw/pitch were never recovered from the original HUD shots; these pairs use the same positions, a framed look at the leftover cuts, plus closer side and underside cameras. Tours live in `screenshots-final/v1.4.3/round2/before/` and `after/`.

Root cause: v3 still places islands on grid-aligned Worley shelves. When neighbouring cells have different altitude bands, the pullback along the Voronoi edge draws a long hex-axis wall (up to 17 cells on this seed). Height-blending those shelves in round 1 reintroduced 28-layer cliffs, so v3 kept a noisy gap and a nibble instead. That was not enough for a 12-cell bar, so new skies move to generator v4.

v4 (CURRENT=4): each island is a discrete object on one of three jittered grids (continents, medium, small) with a reserved radius smaller than the minimum centre gap, so footprints cannot meet and there is no Worley cut plane and no chunk/region/layer clamp. Large islands are lobed and nibble-only along the coast (not uniform spheroids), with a wide walkable plateau, trees and biome cover, and tops to about 300; undersides are rounded cosine domes compressed above layer 2. Skerries stay in the open water. v1–v3 stay for old saves; the lesson island is still the pinned hand-built one. Title JSON and seed showcases are pinned to generator v3 and still have land at their original site tops (dtop=0 on all 14).

Tests (`PYTHONPATH=. venv/bin/python tests/test_phase143.py` and `tests/test_phase142.py`): 18 seeds × two windows, 0 runs of 12+ on walls, coasts or undersides, 0 volume overlaps, neighbour steps ≤ 6, peaks 301–302. Size mix includes continents of 148–155 cells across (10k+ columns) plus medium and small islands. All 1.4.2 v3 cliff/height tests still pass (0 v3 seams, 100% reduction).

The first v4 after-shots at those same cameras were too small and too round (many similar blob islets). The three-scale grid brings the spread back: e.g. seed 7’s Lumen Grove continent in `v4_aerial_wide.png` and `v4_tall_islands_lookup_wide.png` (1254–1300 loaded, 190/156 drawn), comparable to the 1.4.2 `aerial_wide_2` / `tall_islands_lookup_wide` showcases. After-shots at the seven sites were retaken; Chalk Barrens high now looks out from a large chalk landmass (1303 loaded, 220 drawn) instead of a field of blobs, with no straight cuts.

Wanderer hips: cheeks are several stepped, shaded skin-tone boxes, narrowed to sit inside the hip width, raised to the base of the torso, and sunk into a recessed pelvis so they read as one butt from the back, three-quarter and side (`wanderer_back.png`, `wanderer_three_quarter.png`, `wanderer_side.png`). Centre cleft and a slight lift kept; no other anatomical detail. The glute reference image was private to this subagent, so the shape follows the written brief only.

FPS (wall-clock, vsync off, fps_limit 0, 1280×720, after settle; `app.tick` still clamps dt at 0.1 so the HUD can read 10): tutorial still 46.4 / walk 51.3 (round 1 was 42.7 / 47.1 after the figure cache). Normal new v4 sky, seed `-1740201319`, still 11.7 / walk 12.6 (round 1 v3 at this seed was 7.1 / 7.8). Tutorial stays cached-fast.

Best screenshot paths (all under `screenshots-final/v1.4.3/round2/`):
- before/after cuts: `before/before_chalk_barrens_high.png` (straight canyon) vs `after/after_chalk_barrens_high.png` and `_b.png`; `before/before_cloudstep_isles_far.png` (vertical wall) vs `after/after_cloudstep_isles_far.png`; `before/before_cloudstep_isles_far_side.png` (flat underside).
- v4 landmasses: `v4_aerial_wide.png`, `v4_tall_islands_lookup_wide.png`, `v4_continent_surface.png`.
- figure: `wanderer_back.png`, `wanderer_three_quarter.png`, `wanderer_side.png`.

The v1.4.3-test pre-release will be replaced next (1.4.2 stays Latest).

## November 25, 2026, 8:26 PM EST — 1.4.3-test pre-release replaced

Round-2 Windows build and screenshots replaced the assets on https://github.com/GmanAwesome/tidewake/releases/tag/v1.4.3-test (still a pre-release, target `main` / `de897b3`). `Tidewake-1.4.3-test-Windows.zip` is 76,459,949 bytes (manifest 1294 bytes, comctl32 v6, RT_ICON 6 + RT_GROUP_ICON 1, layout `Tidewake/Tidewake.exe`). 1.4.2 remains Latest.

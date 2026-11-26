# Changelog

## 1.4.3 — 25 November 2026

The current release. Skies from 1.4, 1.4.1 and 1.4.2 still load and keep their original terrain. These changes apply to new skies (generator v4).

- The lesson island is no longer uniquely slow. Eight tutorial people were being remeshed from scratch every frame; their poses are cached now.
- New skies use generator v4: each island is a discrete, spaced object with its own centre, radius and a rounded underside, so volumes do not intersect and coasts no longer follow a grid-aligned cut plane. The sky mixes large irregular continents (hundreds of cells across, with walkable relief and trees) with medium and small islands. Older skies stay on v1–v3; the lesson island and title showcases stay on the land they were built for. Surfaces stay walkable, and peaks still reach about 300.
- The wanderer starts as a plain, unclothed base figure. The hips are part of the body: several stepped cheek boxes sit partly into the lower torso, with a centre cleft, a rounded lift, and a taper into the thighs. Clothing and gear appear only once crafted or found and equipped.

Windows builds still embed a Common Controls v6 manifest and the app icon in the exe.


## 1.4.2 — 25 November 2026

Skies from 1.4 and 1.4.1 still load and keep their original terrain. These changes apply to new skies (generator v3).

### Worlds

- Neighbouring islands at different heights are separated by sky, instead of sharing a tall vertical wall. The old 30–60-layer seams are gone in the metric test (2,533 such neighbouring pairs in 1.4.1 over the playtest windows, none in v3).
- Some island surfaces now reach layer 300, with a wide spread from low shelves in the thirties up to those peaks. The world column height is 360; older 128-layer chunks grow on load. You still spawn on mid-height land.
- Large islands have real relief: rolling hills, ridges, peaks, valleys, and mesas with eroded slopes, in mostly 1–2-layer steps.

### Presentation

- The eight hand-built title scenes sit on the new generator. The Sky-boat Dock is a larger, easier-to-spot boat with a cleared quay, the Twin Isles Bridge is a longer crossing, and leftover trunks are cleared from the Lighthouse Cottage's inland angle. Camera paths are still checked for clipping.

Windows builds still embed a Common Controls v6 manifest and the app icon in the exe.


## 1.4.1 — 25 November 2026

A polish release on top of 1.4. Skies from 1.3 still load and keep their original terrain. These changes apply to new skies.

### Worlds

- Islands sit at a much wider range of heights, each on its own shelf, so neighbouring isles can tower or drop away. You still spawn on mid-height land, not the tallest peak.
- Floating islands have rounded, tapering undersides and a solid lip, instead of thin or gappy bottoms.
- Caves no longer punch holes in the island sides. After carving, the hull is sealed, and only a few cobble-framed mouths open onto the walking surface.
- Biomes have richer ground cover: grass, wildflowers, mushrooms, pebbles, shrubs, reeds and the occasional signpost, clustered to suit each landscape.

### Play

- The lesson island is larger and more directed. Teachers stand in the open, not inside blocks, and they only start a conversation when you right-click them. A short hint can still point you at that.
- Creatures no longer bounce or shake in place. They sit on the real floor.
- Lanterns and lamps stay in the light list, so their glow no longer flickers out among many other lights.
- Doors hang as a thin double leaf through the middle of the hex and swing open as a pair.

### Presentation

- Block textures are mapped in hex space. Tops are centred on the cell, sides run cleanly from bottom to top, log end-grain sits in the middle of the hex, and the old wrapping seams are gone.
- The grey boxes on the title screen are gone.
- Each launch opens the title screen on a different showcase, skipping the one you saw last time, then rotates as before.
- Eight hand-built title scenes now sit on the current generator: the Lighthouse Cottage (rebuilt), a Cliffside Tavern, a Windmill Farm, a Sky-boat Dock, a High Keep, a Rose Temple, a Cedar Treehouse and a Twin Isles Bridge. Their camera paths are checked so the orbit does not clip through blocks or leaves, or hide the build behind a hill for long.

Windows builds still embed a Common Controls v6 manifest and the app icon in the exe.

## 1.4 — 25 November 2026

A full release. Skies from 1.3 still load and keep their original terrain. New skies use the 1.4 generator.

### Worlds

- Eight more landscapes: Saltwind Flats, Cedar Highlands, Lavender Downs, Cinder Spires, Chalk Barrens, Starfall Veil, Cloudstep Isles and Verdigris Canyons (sixteen in all).
- New skies are thicker and more varied, with sliders for island size and thickness, mountains, caves, water, trees, Glimmer and more (0–100, with 50 as the usual middle).
- A structure framework plants settlements, temples, standing stones, buried chambers and moored sky boats, weathered as intact, abandoned, ruined or overgrown.
- Many new blocks: woods and stones for the new landscapes, glass, slabs, stairs, walls, fences, doors, ladders, thatch, lamps and more. Material IDs were only appended, so older skies stay compatible.
- Trees are taller, with canopies high enough that you can walk underneath most of them.
- Cave amount and size can still be turned up, but the islands keep a solid shell so max settings no longer lace the cliffs.
- Buried chambers always have lamps, so the room is visible at the bottom of the shaft.

### Play

- A hand-built lesson island, opened from Learn to play, walks you through moving, gathering, crafting, doors, fishing, farming and Glimmer.
- Glimmer motes, waystones for travel, and the Glimmer Font for lasting gifts. At the usual mid setting, a light daytime trickle remains, and dusk is still the richer time to gather.
- Fishing with a craftable rod, bites that vary by landscape and tide, and a slightly more generous hook window.
- Farming: a hoe, tilled beds, skywheat, sweetroot and berry crops, with a chest of starters on the lesson island.
- The Path tracks what you have done and quietly points at what to try next.
- Skywhales drift between islands, and fairies glow near flowers as dusk comes on. Both are peaceful, and they stay off the lesson island.
- F5 cycles first person, third person and looking-at-you. The figure you see wears only what you actually hold or have found. The admin panel is on F7 (still needs dev mode).
- Sleeping on a bedroll at dusk fades to black, then eases through a dawn instead of snapping the light.
- In Dreamer mode, middle-click removes an item from your inventory.

### Presentation

- The title screen has an animated logo, clearer type, and a rotating backdrop: the Lighthouse Cottage and a handful of strong seeds on the new generator.
- Four new procedural songs join the soundtrack (Firstlight, Undertide, Rainwake, Highmere), in different keys and moods, including a lesson-island theme, swimming and rain. The music cache is v9.
- A cohesion pass on the HUD (toasts and the control hint no longer overlap), the skywhale silhouette, and the front-view face.

Windows builds embed a Common Controls v6 manifest and the app icon in the exe.

## 1.3.4

Title-screen showcase: the Lighthouse Cottage, a golden-hour orbit camera, and builds picked at random.

## 1.3.3 and earlier

The six-song soundtrack, procedural textures, far-island LOD, survival, crafting and the first hex sky. Older notes are on the [Releases](../../releases) page.

# Tidewake 2.1 roadmap

Rust rewrite of Tidewake 1.4.6. The Python tree stays in place as the spec until
this port matches it. The Rust project lives in `rust/` (a Cargo workspace).

Version string on the title screen and the debug line: **2.1**.

Legend: `[x]` done, `[~]` in progress, `[ ]` not started.

## Scaffold

- [x] Cargo workspace under `rust/`
- [x] Window opens and clears to the Lighttide sky (`winit` + `wgpu`)
- [x] Title screen shows version `2.1` (Learn to play, My Skies, Settings)
- [x] Debug line shows version `2.1` while playing
- [x] My Skies starts empty and offers New Sky
- [x] Loading screen; a failed chunk sets an error and Esc returns to the title
- [ ] Settings sliders (the screen is a placeholder)
- [x] Walk, jump and step-up on solid ground. F4 toggles flight
- [x] GitHub Actions workflow builds `Tidewake.exe` on `windows-latest` and uploads the zip
- [ ] Confirm the exe on a Windows machine (manifest and icon are embedded by the Windows build)

## World

- [x] Axial hex grid maths (pointy-top `q, r`, floor chunking, 500 layers, 16×16)
- [ ] Column storage, edits, chunk streaming, unload margin
- [~] v6 generator only (v1–v5 are not ported)
  - [x] Seed temperament and slider settings (matches Python MT19937)
  - [x] Main island scales (huge, large, medium, small) and skerries, checked against Python columns
  - [x] Sky tiers (`skytiers.py`) stacked through the column
  - [x] Tapered undersides on the main islands
  - [x] Waterfalls that end in the air (about 40 layers, not down to the cloud sea)
  - [x] Spike cleanup (tested: no 10-layer non-waterfall pillars inside a chunk)
  - [x] 20 biomes on the column field, including Blossom Vale, Autumn Wilds, Azure Fields, Golden Steppe
  - [x] Small and medium trees, including the v6 shapes (bush, blossom, autumn, cone, flat acacia)
  - [x] Huge trees (18–34 layers, drawn across chunks: oak, cone, willow, acacia, toadstool)
  - [x] Caves (worms, rooms, fissures, and cobble-framed mouths)
  - [x] Lakes (surface pools)
  - [x] Ores (emberite, verdigris, silverine, aetherite) and dormant spires
- [x] Grand structures at the 1.4.6 rate (54.6% of regions): balloons, sky city,
      fortress, world tree, colossus, megaspire, leviathan wreck, titan ruins,
      villages, airships, watchtowers
- [x] Smaller builds at 65% and skipped wherever a grand structure covers the chunk
      (huts, shrines, windmills, lighthouses, wells)
- [x] Rare wonders on about one in ten small rolls (clockwork tower, crystal nave,
      hanging keep)
- [x] Meshing (hex prisms, opaque and water)
- [x] LOD that draws each vertical run, so stacked islands stay separate
- [x] Distance fog (Lighttide clear)
- [x] Fly camera over a generated v6 sky (release: about 10 ms/chunk, ~40 fps on llvmpipe)

## Look

- [x] Every material and block from 1.4.6 (ids, kinds, colours, emission, solidity)
- [ ] Drops, hardness and decorative part shapes for those blocks
- [x] Procedural texture atlas from `tidewake/texpack.py` (our own tiles, not third-party pixels)
- [x] Lighting follows the tide: warm Lighttide sun, violet Dusktide
- [x] Sky gradient, a sun disc, and a cloud sea at the cloud layer
- [x] Player model kept exactly: nude wanderer, rounded glutes, smooth front,
      no genitals and no frontal bulge. F5 cycles first person / behind / in front

## Play

- [x] Walk, look, jump, hurry, and step up one layer. F4 flies
- [ ] Crouch and glide
- [ ] Fly and fall (Dreamer flight, cloud-sea rescue)
- [ ] Mine and place
- [x] Hotbar, eating, and one craft (3 berries make a skyloaf). Full 2×2 bench and kiln still open
- [x] Survival: food drains while walking, hunger hurts, eating heals, food above 16 regenerates health
- [ ] Doors, ladders, beds, chests
- [ ] Fishing and farming
- [x] Creatures wander (woolhops, pebblebeaks, mossbacks, islekits, fairies, sky jellies). Gloomlings fade when the tide is light
- [ ] Glimmer motes, waystones, Tidewell gifts
- [ ] Spires (Glide, Updraft, Tidecall) and the Path
- [ ] Tides (Lighttide / Dusktide)
- [~] Lesson island ("Learn to play") loads a hand-built disc with a path, pool, tree and cottage, and you can walk it
- [ ] The 1.4.6 showpiece builds and the friendly cast on that island
- [ ] Commands and Dreamer mode

## Shell

- [x] Title (version 2.1, Learn to play, My Skies, Settings)
- [x] My Skies starts empty; the lesson is not listed
- [x] New Sky (type a seed, or leave it blank)
- [ ] New Sky sliders
- [ ] Settings beyond the placeholder screen
- [x] Loading screen that shows world-gen errors and lets Esc return
- [ ] Pause / save and leave
- [x] Saves (new JSON format next to the game; the lesson is not listed; old Python saves are not loaded)
- [x] Korobeiniki plays when a sky starts (public domain). The rest of the soundtrack and sound effects are still open
- [ ] Journal

## Tests

- [x] Generator is deterministic per seed (chunk bytes match a second generate)
- [x] All 5 island tiers present (huge/large/medium/small on the main grids, tiny on sky tiers)
- [x] No thin non-waterfall pillars in a generated chunk
- [x] v6 columns match the Python generator on recorded seed-7 samples
- [ ] Other core logic (hex rounding, crafting, glimmer costs, saves)

## Notes

- Saves from 1.4.x are not loaded. Generator versions v1–v5 are not ported.
- Players need nothing installed: the Windows build is one statically linked exe.
- Do not publish a GitHub release from this port. The owner's assistant publishes releases.

# Tidewake 2.1 roadmap

Rust rewrite of Tidewake 1.4.6. The Python tree stays in place as the spec until
this port matches it. The Rust project lives in `rust/` (a Cargo workspace).

Version string on the title screen and the debug line: **2.1**.

Legend: `[x]` done, `[~]` in progress, `[ ]` not started.

## Scaffold

- [x] Cargo workspace under `rust/`
- [x] Window opens and clears to the Lighttide sky (`winit` + `wgpu`)
- [ ] Title screen shows version `2.1`
- [ ] Debug overlay shows version `2.1`
- [ ] Single-file Windows `Tidewake.exe` (no runtime to install)
- [ ] GitHub Actions workflow builds the exe on `windows-latest` and uploads it

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
  - [ ] Huge trees (18–34 layers, drawn across chunks)
  - [ ] Caves, lakes, ores, spires
- [ ] Grand structures: hot air balloons, sky city, floating fortress, world tree,
      colossus, megaspire, leviathan wreck, titan ruins, villages, airships,
      watchtowers
- [ ] Smaller found structures (hamlets, shrines, windmills, lighthouses, and the rest)
- [ ] Rare wonders (sky-whale skeleton, clockwork tower, hanging keep, ring harbor,
      crystal cathedral, waterfall temple)
- [x] Meshing (hex prisms, opaque and water)
- [x] LOD that draws each vertical run, so stacked islands stay separate
- [x] Distance fog (Lighttide clear)
- [x] Fly camera over a generated v6 sky (release: about 10 ms/chunk, ~40 fps on llvmpipe)

## Look

- [x] Every material and block from 1.4.6 (ids, kinds, colours, emission, solidity)
- [ ] Drops, hardness and decorative part shapes for those blocks
- [ ] Procedural textures from the repo's own generator (no third-party pixels)
- [ ] Lighting (sun, ambient, point lights, tide colours)
- [ ] Sky dome, cloud sea, dusk/light cycle
- [ ] Player model kept exactly: nude wanderer, rounded glutes, smooth front,
      no genitals and no frontal bulge

## Play

- [ ] Walk, look, jump, crouch, hurry, glide
- [ ] Fly and fall (Dreamer flight, cloud-sea rescue)
- [ ] Mine and place
- [ ] Inventory, hotbar, crafting (2×2 and Tinker Bench), kiln
- [ ] Survival: food, health, eating heals, regen
- [ ] Doors, ladders, beds, chests
- [ ] Fishing and farming
- [ ] Creatures (passive and Dusktide hostiles)
- [ ] Glimmer motes, waystones, Tidewell gifts
- [ ] Spires (Glide, Updraft, Tidecall) and the Path
- [ ] Tides (Lighttide / Dusktide)
- [ ] Lesson island ("Learn to play") with its showpiece builds and friendly cast
- [ ] Commands and Dreamer mode

## Shell

- [ ] Title
- [ ] My Skies (starts empty; the lesson is not listed)
- [ ] New Sky (seed and sliders)
- [ ] Settings
- [ ] Loading screen that shows world-gen errors
- [ ] Pause / save and leave
- [ ] Saves (new format; old Python saves are not loaded)
- [ ] Music (Korobeiniki is public domain) and sounds
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

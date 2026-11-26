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
- [ ] v6 generator only (v1–v5 are not ported)
  - [ ] Seed temperament and slider settings
  - [ ] Five island size tiers, random heights across the full vertical range
  - [ ] Sky tiers (`skytiers.py`)
  - [ ] Tapered undersides
  - [ ] Waterfalls that end in the air
  - [ ] Spike cleanup (no thin non-waterfall pillars)
  - [ ] 20 biomes, including Blossom Vale, Autumn Wilds, Azure Fields, Golden Steppe
  - [ ] Small, medium and huge trees
  - [ ] Caves, lakes, ores, spires
- [ ] Grand structures: hot air balloons, sky city, floating fortress, world tree,
      colossus, megaspire, leviathan wreck, titan ruins, villages, airships,
      watchtowers
- [ ] Smaller found structures (hamlets, shrines, windmills, lighthouses, and the rest)
- [ ] Rare wonders (sky-whale skeleton, clockwork tower, hanging keep, ring harbor,
      crystal cathedral, waterfall temple)
- [ ] Meshing
- [ ] LOD that draws stacked islands separately
- [ ] Distance fog

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

- [ ] Generator is deterministic per seed
- [ ] All 5 island tiers appear
- [ ] No thin non-waterfall pillars
- [ ] Other core logic (hex rounding, crafting, glimmer costs, saves)

## Notes

- Saves from 1.4.x are not loaded. Generator versions v1–v5 are not ported.
- Players need nothing installed: the Windows build is one statically linked exe.
- Do not publish a GitHub release from this port. The owner's assistant publishes releases.

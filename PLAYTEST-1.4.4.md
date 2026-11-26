# Tidewake 1.4.4 playtest

November 25, 2026, 10:10 PM EST. Scripted like a new wanderer on the published 1.4.4-test build (`2905216` and the playtest tour committed with this note). 1280×720, creatures and dusk critters on, seed `playtest-144` for the open sky. Shots are in `screenshots-final/v1.4.4/playtest/`. This is an honest pass, including the places the script had to cheat.

## What I did

- Started on the title screen, then dreamed a fresh lesson island (not a saved compact 1.4.3 one).
- Stood at spawn (yaw 0, pitch 4), walked forward, talked to Willow, walked the east path to Bram, opened his chest and took the heartwood, walked toward Lumen and the shrine knoll.
- Quit to the title and dreamed a new generator-v5 sky (`playtest-144`).
- Walked from spawn, held gather on a nearby tree, opened the backpack recipe book, filled Planks and Rose Dye, placed a small doodle of the new blocks, visited a generated structure, tried to reach a spire and fly, then forced dusktide and stood among the creatures.

## What worked

- The lesson opens well. From spawn the tiled plaza is underfoot, the citadel sits on the -Z horizon, and the welcome toast is clear (`01_tutorial_spawn.png`). A 3-second walk forward along the path stays on the ground and covers a sensible distance.
- All eight lesson NPCs have a solid cell underfoot and air at the body. Dialogue itself works: Willow mentions the citadel, Bram explains gathering, Lumen explains glimmer, and Bram's chest opened with 8 sticks and 8 heartwood that could be taken (`05_bram_chest.png`).
- The new v5 sky looks like a real place. Spawn on `playtest-144` is a sandy flowered shelf with a sleeping spire 24 m ahead and a hanging neighbour island in the sky (`10_v5_spawn.png`). Walking four seconds stayed on the ground. Held gather on a heartwood trunk produced a log.
- The backpack recipe book already sorts craftable recipes first. Filling "1 Heartwood → Planks x4" and "1 Bloom → Rose Dye x2" laid the grid correctly (`14_craft_planks.png`, `15_craft_rose_dye.png`). The new dyes show up on the first page once you have the ingredients.
- A generated structure was already in the loaded area: a pink patterned-tile pavilion with a chest on the roof, sitting as its own little isle between forested shelves (`18_visit_structure.png`, `19_structure_ground.png`). The new blocks read clearly in the wild.
- Dusktide spawned a healthy mix without a hitch: 2 skywhales, 2 mossbacks, 8 pebblebeaks, 6 fairies, 4 gloomlings and 1 brute (23 creatures, later 24). The player can stand among them (`21_dusk_creatures.png`, `22_dusk_survive.png`).

## Friction, bugs, and gaps

1. **Willow's greeting overflows the talk bubble.** The first line wraps onto "Right-click to hear more", so "jump with Space" reads as "Spacepre" (`03_talk_willow.png`). The bubble was a fixed 72-pixel height. Shorter later lines (Bram, Lumen) are fine. **Fixed:** the bubble grows to fit the wrapped text, and Willow's greeting is split so the controls are their own line.
2. **Talking to Bram was captured with the camera inside a Heartwood trunk** (`04_talk_bram.png`). Willow and Lumen had the same problem from the other side: standing on their cell fills the frame with a skin-tone hex. There is no body collision, so a player who walks up close talks from inside the subject. **Fixed:** starting a conversation steps you back onto open ground and looks at the NPC, so they stay in view.
3. **`07_shrine_knoll.png` is inside a Carved Stone block and is unusable.** The walk arrived (1.85 cells, on the ground) but the camera looked at a stone underfoot. The knoll itself is fine. **Retaken** from farther back so the whole shrine is the subject.
4. **`17_placed_new_blocks.png` is looking up a tree, not at placed new blocks.** The tour used `column_top`, which is the canopy, and one stained-glass cell landed ten layers up a trunk. **Retaken** after actually placing dyed and decorative blocks on the ground.
5. **Rose stained glass could not be crafted on the 2×2 backpack grid.** Filling the book entry put a Rose Dye on the grid and left the result empty, with the hint "Need a 3x3 grid? Place a Tinker Bench" (`16_craft_rose_glass.png`). That hint is the backpack's idle copy, not a real 3×3 requirement — but it reads as one. The real friction: colored stained glass was only a recolor of an existing stained-glass block (glass + dye made Snow Stained Glass, then you dyed that). A new player with Glass and Rose Dye cannot make Rose Stained Glass on the pack they already have open. **Fixed:** glass + any dye now makes that color of stained glass on the 2×2 grid, and the 3×3 hint only shows when the grid is empty.
6. **Falling off is frequent and punishing.** Cloud rescue works, but it stings every time. A straight walk from Bram toward Lumen left the lesson island; the toast "The clouds carry you back / They are gentle, but it still stings a little" fired and HP dropped from 20 to 15 during the Lumen talk (`06_talk_lumen.png`). On the v5 sky, a walk toward the nearest spire left the wanderer falling, and by dusk they were down to 1 heart (`21_dusk_creatures.png`, `22_dusk_survive.png`). Food barely moves; falls are what hurt. There was no warning at the shore. **Partly fixed:** the first cloud rescue in a sky no longer stings, and a short "The shore drops away" hint appears when the next step would leave the island. Later falls still sting, and this stays on the what's-next list — early exploration is still fall-risky before glide and updraft are earned.
7. **Filling a recipe does not take the result.** That's intended (click the output), but it is easy to close the pack and lose the filled grid — `return_grid` puts the ingredients back and the craft never happens. The tour logged "no Rose Dye" until it granted some. The book does not say "click the result."
8. **The recipe book lists 202 recipes.** Craftable ones float to the top, which is good, but browsing for a family you have never made yet is a long scroll. New 1.4.4 blocks are easy to miss until you already have the ingredients.
9. **Glide and updraft are far away when you need them most.** The nearest spire was 24 m at v5 spawn — close and well signed — but awakening two of them is a walk across gaps. This short playtest never naturally earned flight; abilities had to be granted. Early exploration is fall-risky before the gift exists.
10. **Hand-gathering is slow.** A several-second hold on a trunk yielded one Heartwood. Fine as a first lesson, slow if you want to actually build.
11. **A "what now" after the lesson is still thin.** The open sky is beautiful and already has structures and creatures, but the mid-game hook is still "find a spire, gather, don't fall." Memorable unique landmarks were scarce; wildlife was the same three passives plus flyers and dusk hostiles. This follow-on adds rare wonders and a few new sky-island creatures to fill that gap.

## What was granted (not earned)

- Bloom, glass, stone tiles, petals, sand, fluff and glowcap, so the new dye recipes could be tried.
- Rose stained glass, jelly, patterned tile and a banner after the tour failed to click the craft output, so a doodle could still be placed. (The placement itself used `world.set` on `column_top`, and one cell was a tree top ten layers up, so `17_placed_new_blocks.png` looks at a trunk. A player aiming at the ground would do better.)
- Glide and updraft, after an 8-second walk toward the nearest spire did not awaken two.

## What's needed next (priority)

1. ~~**Fix the talk bubble** so wrapped text grows the panel and never sits on the hint.~~ Done in this follow-on, including splitting Willow's greeting.
2. **Falling off is still the main way a new wanderer almost dies.** The first cloud rescue no longer stings, and the shore now hints before you step off, but later falls still cost 3 HP and by dusk this playtest was on 1 heart. Early crossings before glide and updraft are earned remain too punishing. Worth a softer second fall, or a clearer "you need a second spire to updraft" once the first is awake.
3. ~~**Give the mid-game something to notice from a distance**~~ — this follow-on adds rare wonders (a whale-bone isle, a clockwork tower, an upside-down keep, a ring harbor, a crystal cathedral, a waterfall temple) and new title-screen builds that use the 1.4.4 blocks.
4. ~~**Add a little more life**~~ — this follow-on adds sky jellyfish, cloud rays, moss turtles with gardens on their shells, crystal beetles, and skittish islekits, with simple AI and modest caps.
5. A bit more guidance on the lesson paths so a straight walk between stations does not leave the island (signposts help only if you are already on the tiles). The Lumen walk is how the tutorial itself triggered a cloud rescue.
6. Recipe-book discovery for families you cannot craft yet (a short "new in 1.4.4" list, or a search). Not blocking. Direct glass+dye stained glass is already in, which was the sharpest craft friction in this pass.
7. Optional later: NPC and trunk collision while walking, not only when a conversation starts.
8. Hand-gathering speed and a "click the result" hint on a filled craft grid are small quality-of-life leftovers.

1.4.3 stays Latest until a publish is asked for.

## Glimmer loop, in plain English (1.4.4 late)

- **Catch:** floating motes are Glimmer. Walk into one. More drift at dusk; waking a spire leaves some.
- **Waystones:** 1 Glimmer makes a waystone remember you. Attune two and right-click either to travel between them. Travel is free.
- **Tidewell** (the old Glimmer Font): spend 2–4 Glimmer on a lasting gift for this sky — Mote Sense 2, Keen Reach 3, Lightfoot 3, Deep Breath 3, Brightwake 4.
- On the lesson island Lumen explains all three, her chest holds 4 Glimmer, and motes drift around her court and the knoll, so you can attune both lesson waystones, travel, and buy a first gift. `tests/test_glimmer144.py` walks that loop end to end.

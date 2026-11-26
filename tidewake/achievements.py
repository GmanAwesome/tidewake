"""The Path: an achievement tree that also teaches how the sky works. Unlocks save with the world."""

# id, title, parent or None, column, row, short how-to, check(session) -> bool
def _nodes():
    return [
        ('first', 'First steps', None, 0, 2,
         'Hold left click on a tree or a block of turf to gather it. Wood comes off by hand; stone needs a pick.',
         lambda s: s.stats.get('mined', 0) >= 1 or s.play_time > 20),
        ('gather', 'Gatherer', 'first', 1, 0,
         'Mine 24 cells. Better picks dig faster and can collect Emberite, Verdigris, Silverine, and glowing Aetherite deeper in.',
         lambda s: s.stats.get('mined', 0) >= 24),
        ('craft', 'Crafter', 'first', 1, 2,
         'Press E to open your backpack. Turn Heartwood into Planks, and Planks into Sticks and a Tinker Bench.',
         lambda s: s.stats.get('crafted', 0) >= 1),
        ('tinker', 'Tinker', 'craft', 2, 1,
         'Place a Tinker Bench and right-click it for the full 3×3 grid. Click a recipe in the book to fill the grid for you.',
         lambda s: s.stats.get('tinker', 0) >= 1),
        ('kiln', 'Kiln tender', 'tinker', 3, 1,
         'A kiln is eight stone in a ring. Right-click it, add fuel (wood, sticks or Emberite) and an ore, sand, clay or raw food.',
         lambda s: s.stats.get('smelted', 0) >= 1),
        ('build', 'Builder', 'craft', 2, 3,
         'Place 20 blocks. Pick a hotbar slot with 1–9 or the wheel, then right-click. Slabs are short blocks you can stand on.',
         lambda s: s.stats.get('placed', 0) >= 20),
        ('hatch', 'Doors and ladders', 'build', 3, 3,
         'A door needs two empty cells, one above the other. Right-click to open it. Ladders hang on a wall — walk into them to climb.',
         lambda s: s.stats.get('doors', 0) >= 1),
        ('wander', 'Mote catcher', 'first', 1, 4,
         'Floating motes are Glimmer. Walk into one to catch it. Pale motes drift by day; golden ones come thick at dusk.',
         lambda s: s.stats.get('motes', 0) >= 1),
        ('shrine', 'Wayfarer', 'wander', 2, 4,
         'Right-click a waystone (in temples, standing stones, or one you crafted) and spend 1 Glimmer so it remembers you. Attune two, then right-click either to travel between them for free.',
         lambda s: any(v.get('attuned') for v in s.waystones.values())),
        ('font', 'Tidewell gift', 'shrine', 3, 4,
         'Right-click a Tidewell and spend 2-4 Glimmer on a lasting gift for this sky: Mote Sense, Keen Reach, Lightfoot, Deep Breath or Brightwake.',
         lambda s: len(getattr(s, 'attune', [])) >= 1),
        ('angler', 'Angler', 'first', 1, 5,
         'Craft a fishing rod from three sticks and linen. Right-click a still pool, wait for the bobber to dip, then reel. Catches change with the land and the tide.',
         lambda s: s.stats.get('fished', 0) >= 1),
        ('plant', 'Planter', 'first', 1, 6,
         'Craft a hoe (sticks and stone) and right-click turf or loam to till a bed. Plant grain, root or duskberry seeds. A nearby pool helps them grow.',
         lambda s: s.stats.get('tilled', 0) >= 1),
        ('harvest', 'Harvest', 'plant', 2, 6,
         'Crops grow through four stages. Break a ripe plant for food and more seeds. Three ears of skywheat bake into a loaf; sweetroot roasts in the kiln.',
         lambda s: s.stats.get('farmed', 0) >= 1),
        ('spire', 'Spire waker', 'first', 1, 7,
         'Dormant spires stand on old plinths. Place what each one longs for on the six cells around its base. The first gifts are Glide, then Updraft, then Tidecall.',
         lambda s: len(s.awakened) >= 1),
    ]


NODES = _nodes()
BY_ID = {n[0]: n for n in NODES}


def ready(ses, nid, have=None):
    """True if this node should unlock (parents already earned, and the check passes)."""
    have = have if have is not None else set(ses.achieved)
    rec = BY_ID[nid]
    parent = rec[2]
    if parent and parent not in have:
        return False
    try:
        return bool(rec[6](ses))
    except Exception:
        return False


def poll(ses):
    """Unlock any newly earned nodes. Returns their ids."""
    have = set(ses.achieved)
    new = []
    changed = True
    while changed:
        changed = False
        for nid, *_ in NODES:
            if nid in have:
                continue
            if ready(ses, nid, have):
                have.add(nid)
                ses.achieved.append(nid)
                new.append(nid)
                changed = True
    return new

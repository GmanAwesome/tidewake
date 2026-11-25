"""Fishing: a craftable rod, a cast / bob / bite / reel loop, and catches by biome and tide."""
import random

from . import items as I
from . import materials as MT
from . import tide as TIDE

# seconds to first bite, and how long the bite window stays open
WAIT = (2.2, 7.5)
BITE = (0.85, 1.35)


def biome_group(realm):
    name = MT.REALMS[int(realm) % len(MT.REALMS)].lower()
    if 'frost' in name:
        return 'frost'
    if any(w in name for w in ('dune', 'mesa', 'salt', 'chalk', 'cinder', 'canyon', 'basalt')):
        return 'arid'
    if 'moss' in name or 'fen' in name:
        return 'wet'
    if any(w in name for w in ('lumen', 'starfall', 'lavender')):
        return 'lumen'
    if 'cloud' in name:
        return 'sky'
    return 'mild'


def _w(table, dusk):
    """Weighted (item, weight) list for a biome group. Heavier at dusk for night fish."""
    fish = {
        'mild': [(I.REED_MINNOW, 5), (I.SILVERFIN, 4), (I.DUSKPERCH, 1 if dusk else 0), (I.CLOUD_KOI, 1)],
        'arid': [(I.SALTSKIPPER, 5), (I.SILVERFIN, 3), (I.REED_MINNOW, 1), (I.CLOUD_KOI, 1)],
        'wet':  [(I.MOSS_EEL, 5), (I.DUSKPERCH, 3 if dusk else 1), (I.SILVERFIN, 2), (I.CLOUD_KOI, 1)],
        'frost': [(I.FROSTFIN, 5), (I.SILVERFIN, 2), (I.CLOUD_KOI, 1)],
        'lumen': [(I.SILVERFIN, 3), (I.CLOUD_KOI, 3), (I.DUSKPERCH, 2 if dusk else 1), (I.GLIMMERFIN, 1 if dusk else 0)],
        'sky':  [(I.CLOUD_KOI, 4), (I.SILVERFIN, 3), (I.REED_MINNOW, 2), (I.GLIMMERFIN, 1 if dusk else 0)],
    }[table]
    return [(it, w) for it, w in fish if w > 0]


TREASURE = [
    # (item id, count, weight)
    (None, 1, 0),  # filled in after items exist; see treasure_table()
]


def treasure_table():
    return [
        (I.STICK.id, 1, 8),
        (I.FLUFF.id, 1, 4),
        (MT.ID['linen'], 1, 3),
        (I.PAIL.id, 1, 2),
        (I.BERRIES.id, 2, 3),
        (MT.ID['lumen_shard'], 1, 2),
        (I.GLIMMER.id, 1, 2),
        (I.SILVERINE.id, 1, 1),
        (I.AETHERITE.id, 1, 1),
    ]


def roll_catch(realm, phase, rng=None):
    """Return (iid, count, kind) where kind is 'fish' or 'treasure'."""
    rng = rng or random.Random()
    dusk = TIDE.dusk_amount(phase) > 0.45
    if rng.random() < (0.12 if dusk else 0.08):
        bag = treasure_table()
        total = sum(w for *_, w in bag)
        pick = rng.uniform(0, total)
        acc = 0
        for iid, n, w in bag:
            acc += w
            if pick <= acc:
                return iid, n, 'treasure'
    bag = _w(biome_group(realm), dusk)
    total = sum(w for _, w in bag)
    pick = rng.uniform(0, total)
    acc = 0
    for it, w in bag:
        acc += w
        if pick <= acc:
            return it.id, 1, 'fish'
    return bag[-1][0].id, 1, 'fish'


def start_wait(rng=None):
    rng = rng or random.Random()
    return rng.uniform(*WAIT), rng.uniform(*BITE)

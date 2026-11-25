"""Farming: till soil with a hoe, plant seeds, and harvest crops that grow over time."""
import random

from . import items as I
from . import materials as MT
from .hexgrid import DIRS, hex_distance

M = MT.ID
STAGES = 4
TILLABLE = {M['turf'], M['loam'], M['packed_earth'], M['heather']}


def crops():
    return {
        M['skywheat']: {'seed': I.GRAIN_SEEDS.id, 'produce': I.WHEAT.id, 'n': (1, 2)},
        M['sweetroot_crop']: {'seed': I.ROOT_SEEDS.id, 'produce': I.SWEETROOT.id, 'n': (1, 2)},
        M['berry_crop']: {'seed': I.BERRY_SEEDS.id, 'produce': I.BERRIES.id, 'n': (2, 4)},
    }


def plant_of(iid):
    for mat, rec in crops().items():
        if rec['seed'] == iid:
            return mat
    return None


def harvest(mat, meta, rng=None):
    """(iid, count) drops for a crop cell at this growth stage."""
    rng = rng or random.Random()
    rec = crops().get(mat)
    if rec is None:
        return []
    out = []
    if meta >= STAGES - 1:
        out.append((rec['produce'], rng.randint(*rec['n'])))
        out.append((rec['seed'], rng.randint(1, 2)))
    elif rng.random() < 0.5:
        out.append((rec['seed'], 1))
    return out


def hydrated(world, q, r, y):
    """True if still water is within two cells of this farmland (same level or just below)."""
    for dq in range(-2, 3):
        for dr in range(-2, 3):
            if hex_distance(0, 0, dq, dr) > 2:
                continue
            for dy in (0, -1):
                if world.get(q + dq, r + dr, y + dy) == M['water']:
                    return True
    return False

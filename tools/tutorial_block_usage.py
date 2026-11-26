"""List placeable blocks that the lesson island never uses.

    venv/bin/python tools/tutorial_block_usage.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import numpy as np  # noqa: E402

from tidewake import materials as MT  # noqa: E402
from tidewake import tutorial as T  # noqa: E402
from tidewake import tutorial_builds as TB  # noqa: E402
from tidewake.config import CHUNK  # noqa: E402


def island_counts():
    counts = np.zeros(256, np.int64)
    for cq in range(-50 // CHUNK - 1, 80 // CHUNK + 1):
        for cr in range(-76 // CHUNK - 1, 80 // CHUNK + 1):
            cells, _meta, _realm = T.generate_chunk(cq, cr)
            counts += np.bincount(cells.ravel(), minlength=256)
    return counts


def unused():
    c = island_counts()
    return [MT.NAMES[i] for i in TB.placeable_ids() if c[i] == 0], c


if __name__ == '__main__':
    t = time.time()
    missing, c = unused()
    used = sum(1 for i in TB.placeable_ids() if c[i])
    print(f'placeable blocks: {len(TB.placeable_ids())}  used on the lesson island: {used}  '
          f'unused: {len(missing)}  ({time.time() - t:.1f}s)')
    for n in missing:
        print('  unused:', n)
    print('gallery pedestals:', len(TB._CACHE.get('gallery', [])))

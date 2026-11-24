"""Jobs for the background worker processes (numpy only, no GL)."""
import os
import time

import numpy as np

from .generator import Generator
from .mesher import mesh_chunk

_gens = {}


def init_worker():
    pass


def _gen(seed):
    g = _gens.get(seed)
    if g is None:
        if len(_gens) > 3:
            _gens.clear()
        g = _gens[seed] = Generator(seed)
    return g


def generate_job(seed, cq, cr, saved_path):
    t = time.perf_counter()
    if saved_path and os.path.exists(saved_path):
        try:
            with np.load(saved_path) as f:
                return cq, cr, f['cells'].astype(np.uint8), f['meta'].astype(np.uint8), f['realm'].astype(np.uint8), \
                    True, time.perf_counter() - t
        except Exception:
            pass
    cells, meta, realm = _gen(seed).generate(cq, cr)
    return cq, cr, cells, meta, realm, False, time.perf_counter() - t


def mesh_job(cq, cr, token, padded, realm):
    t = time.perf_counter()
    o, w, L = mesh_chunk(padded, realm, cq, cr)
    return cq, cr, token, o, w, L, time.perf_counter() - t


def ping():
    return os.getpid()

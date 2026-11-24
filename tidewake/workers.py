"""Jobs for the background worker processes (numpy only, no GL)."""
import os
import time

import numpy as np

from .generator import Generator
from .mesher import mesh_chunk

_gens = {}


def init_worker():
    """Run world building at lower priority so the game and its audio thread always get CPU first."""
    try:
        if os.name == 'nt':
            import ctypes
            k = ctypes.windll.kernel32
            k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)     # BELOW_NORMAL_PRIORITY_CLASS
        else:
            os.nice(5)
    except Exception:
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


LOD_GROUP = 4      # far meshes are built per 4x4 chunks to keep draw calls low


def lod_job(seed, sq, sr, paths, step=2):
    """Generate (or load) a 4x4 block of chunks and build one far-away mesh.
    -> sq, sr, bytes, [(first_vertex, count)] per sub-chunk, dt"""
    from .mesher import lod_mesh, VERT
    from .hexgrid import chunk_origin
    t = time.perf_counter()
    ox, oz = chunk_origin(sq * LOD_GROUP, sr * LOD_GROUP)
    parts, ranges, first = [], [], 0
    for i in range(LOD_GROUP):
        for k in range(LOD_GROUP):
            cq, cr = sq * LOD_GROUP + i, sr * LOD_GROUP + k
            _, _, cells, meta, realm, _, _ = generate_job(seed, cq, cr, paths.get((cq, cr)) if paths else None)
            x, z = chunk_origin(cq, cr)
            v = lod_mesh(cells, realm, x - ox, z - oz, step)
            parts.append(v)
            ranges.append((first, len(v)))
            first += len(v)
    data = np.concatenate(parts).tobytes() if first else b''
    return sq, sr, data, ranges, time.perf_counter() - t, step

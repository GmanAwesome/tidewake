"""Streams hex chunks around the wanderer using a pool of worker processes.

Each frame update(): collect finished jobs, queue new ones closest-first, upload a few
meshes, re-mesh chunks changed by play or by the living simulation, unload far chunks.
"""
import math
import time
from collections import deque

import numpy as np

from .config import CHUNK, LAYERS, MAX_JOBS_IN_FLIGHT, UPLOADS_PER_FRAME, UNLOAD_MARGIN
from .hexgrid import cell_at, center, chunk_of
from . import materials as MT
from .mesher import mesh_chunk, pad_chunk
from . import workers
from .workers import LOD_GROUP

COARSE_FROM = 18           # far groups beyond this many chunks use the coarser (4x) far mesh

CHUNK_SPAN = 24.0          # world units used to turn "view distance in chunks" into a radius


class Chunk:
    __slots__ = ('cq', 'cr', 'cells', 'meta', 'realm', 'modified', 'mesh', 'state', 'token', 'from_save')

    def __init__(self, cq, cr, cells, meta, realm, from_save=False):
        self.cq, self.cr = cq, cr
        self.cells, self.meta, self.realm = cells, meta, realm
        self.modified = False
        self.mesh = None
        self.state = 'none'
        self.token = 0
        self.from_save = from_save


class World:
    def __init__(self, seed, storage, renderer, pool, view_distance=8, far_distance=16, gen_settings=None):
        self.seed = seed
        self.gen_settings = gen_settings
        self.storage = storage
        self.renderer = renderer
        self.pool = pool
        self.chunks = {}
        self.gen_jobs = {}
        self.mesh_jobs = {}
        self.uploads = deque()
        self.dirty = set()
        self.timings = {'gen': deque(maxlen=200), 'mesh': deque(maxlen=200)}
        self.center = (0, 0)
        self.closed = False
        self.on_chunk_loaded = None
        self.set_view_distance(view_distance, far_distance)

    def set_view_distance(self, vd, far=None):
        """vd: full-detail chunks. far: how far the simple far-away terrain reaches (chunks)."""
        far = max(vd, far if far is not None else vd)
        self.view_distance, self.far_distance = vd, far
        self.lod_radius = far * CHUNK_SPAN
        R = vd * CHUNK_SPAN
        n = vd + 3
        mesh = []
        for a in range(-n * 2, n * 2 + 1):
            for b in range(-n * 2, n * 2 + 1):
                x, z = center(a * CHUNK, b * CHUNK)
                d = math.hypot(x, z)
                if d <= R:
                    mesh.append((d, a, b))
        mesh.sort()
        self.mesh_offsets = [(a, b) for _, a, b in mesh]
        mset = set(self.mesh_offsets)
        data = {(a + i, b + k) for a, b in mset for i in (-1, 0, 1) for k in (-1, 0, 1)}
        self.data_offsets = sorted(data, key=lambda o: math.hypot(*center(o[0] * CHUNK, o[1] * CHUNK)))
        self.mesh_set = mset
        self.keep_radius = R + CHUNK_SPAN * (1 + UNLOAD_MARGIN)
        self.radius = R
        self._sector = None
        # far LOD groups (LOD_GROUP x LOD_GROUP chunks each)
        G = LOD_GROUP
        m = int(self.lod_radius / (CHUNK_SPAN * G)) + 3
        lod = []
        for a in range(-m * 2, m * 2 + 1):
            for b in range(-m * 2, m * 2 + 1):
                x, z = center(a * G * CHUNK + G * CHUNK / 2, b * G * CHUNK + G * CHUNK / 2)
                d = math.hypot(x, z)
                if R - G * CHUNK_SPAN < d <= self.lod_radius + G * CHUNK_SPAN * 0.7:
                    lod.append((d, a, b))
        lod.sort()
        self.lod_offsets = [(a, b) for _, a, b in lod] if self.lod_radius > R else []
        if not hasattr(self, 'lod'):
            self.lod, self.lod_jobs = {}, {}

    # ------------------------------------------------------------------ cell access
    def get(self, q, r, y):
        if y < 0 or y >= LAYERS:
            return 0
        c = self.chunks.get((q // CHUNK, r // CHUNK))
        if c is None:
            return -1                    # unknown
        return int(c.cells[q % CHUNK, y, r % CHUNK])

    def get_meta(self, q, r, y):
        if y < 0 or y >= LAYERS:
            return 0
        c = self.chunks.get((q // CHUNK, r // CHUNK))
        return 0 if c is None else int(c.meta[q % CHUNK, y, r % CHUNK])

    def set(self, q, r, y, mat, meta=0, now=False):
        if not 0 <= y < LAYERS:
            return False
        key = (q // CHUNK, r // CHUNK)
        c = self.chunks.get(key)
        if c is None:
            return False
        lq, lr = q % CHUNK, r % CHUNK
        old = int(c.cells[lq, y, lr])
        c.cells[lq, y, lr] = mat
        c.meta[lq, y, lr] = meta
        c.modified = True
        keys = {key}
        if lq == 0: keys.add((key[0] - 1, key[1]))
        if lq == CHUNK - 1: keys.add((key[0] + 1, key[1]))
        if lr == 0: keys.add((key[0], key[1] - 1))
        if lr == CHUNK - 1: keys.add((key[0], key[1] + 1))
        if lq == 0 and lr == CHUNK - 1: keys.add((key[0] - 1, key[1] + 1))
        if lq == CHUNK - 1 and lr == 0: keys.add((key[0] + 1, key[1] - 1))
        # a lamp must remesh every chunk its light can reach, not just a border neighbour
        rad = 0.0
        if old in MT.LIGHTS:
            rad = max(rad, MT.LIGHTS[old][1])
        if mat in MT.LIGHTS:
            rad = max(rad, MT.LIGHTS[mat][1])
        if rad > 0:
            keys |= self._chunks_within(q, r, rad)
        if now:
            for k in keys:
                self._remesh_now(k)
        else:
            self.dirty |= keys
        return True

    def _chunks_within(self, q, r, radius):
        """Chunk keys whose columns can sit inside a world-space radius of (q, r)."""
        from .hexgrid import HEX, SQ3
        reach = int(max(1, radius / max(0.1, HEX) + 2))
        keys = set()
        for dq in range(-reach, reach + 1):
            for dr in range(-reach, reach + 1):
                keys.add(((q + dq) // CHUNK, (r + dr) // CHUNK))
        return keys

    def set_meta(self, q, r, y, meta):
        c = self.chunks.get((q // CHUNK, r // CHUNK))
        if c is not None and 0 <= y < LAYERS:
            c.meta[q % CHUNK, y, r % CHUNK] = meta
            c.modified = True

    def _have_neighbours(self, cq, cr):
        ch = self.chunks
        return all((cq + a, cr + b) in ch for a in (-1, 0, 1) for b in (-1, 0, 1))

    def _padded(self, cq, cr):
        ch = self.chunks
        return pad_chunk(lambda a, b: ch[a, b].cells if (a, b) in ch else None, cq, cr)

    def _padded_meta(self, cq, cr):
        ch = self.chunks
        return pad_chunk(lambda a, b: ch[a, b].meta if (a, b) in ch else None, cq, cr)

    def _remesh_now(self, key):
        c = self.chunks.get(key)
        if c is None:
            return
        if c.state != 'ready':
            if c.state == 'pending':
                c.token += 1          # the job in flight saw old cells; its result will be dropped
                c.state = 'dirty'
            return
        if not self._have_neighbours(*key):
            return
        c.token += 1
        self._install(c, *mesh_chunk(self._padded(*key), c.realm, *key, Pm=self._padded_meta(*key)))

    def _install(self, c, o, w, L):
        from .renderer import ChunkMesh
        if c.mesh:
            c.mesh.release()
        c.mesh = ChunkMesh(self.renderer, c.cq, c.cr, o, w, L)
        c.state = 'ready'

    # ------------------------------------------------------------------ streaming
    def update(self, x, z, budget=UPLOADS_PER_FRAME, yaw=None):
        if self.closed:
            return
        q, r = cell_at(x, z)
        self.center = chunk_of(q, r)
        if yaw is not None:
            sector = int((yaw % 360) // 30)
            if sector != getattr(self, '_sector', None):
                self._sector = sector
                self._view_sort(math.radians(sector * 30 + 15))
        self._collect()
        self._schedule()
        self._collect_lod()
        near_busy = len(self.gen_jobs) + len(self.mesh_jobs)
        self._schedule_lod(min(3, MAX_JOBS_IN_FLIGHT - near_busy) - len(self.lod_jobs))
        self._upload(budget)
        n = 0
        while self.dirty and n < 2:
            self._remesh_now(self.dirty.pop())
            n += 1
        self._unload()

    def _view_sort(self, a):
        """Load/mesh what you're looking at first: weight distance by angle to view direction."""
        fx, fz = math.sin(a), -math.cos(a)

        def score(o):
            x, z = center(o[0] * CHUNK + CHUNK / 2, o[1] * CHUNK + CHUNK / 2)
            d = math.hypot(x, z)
            if d < 30:
                return d * 0.5
            return d * (1.0 + 0.7 * (1.0 - (x * fx + z * fz) / d))
        self.mesh_offsets = sorted(self.mesh_offsets, key=score)
        self.data_offsets = sorted(self.data_offsets, key=score)
        self.lod_offsets = sorted(self.lod_offsets, key=lambda o: score((o[0] * LOD_GROUP, o[1] * LOD_GROUP)))

    def _dist(self, key):
        x, z = center((key[0] - self.center[0]) * CHUNK, (key[1] - self.center[1]) * CHUNK)
        return math.hypot(x, z)

    def _collect(self):
        for key, fut in list(self.gen_jobs.items()):
            if fut.done():
                del self.gen_jobs[key]
                if fut.cancelled():
                    continue
                try:
                    cq, cr, cells, meta, realm, saved, dt = fut.result()
                except Exception:
                    continue
                self.timings['gen'].append(dt)
                if key not in self.chunks and self._dist(key) <= self.keep_radius:
                    self.chunks[key] = Chunk(cq, cr, cells, meta, realm, saved)
                    if self.on_chunk_loaded:
                        self.on_chunk_loaded(self.chunks[key])
        for key, fut in list(self.mesh_jobs.items()):
            if fut.done():
                del self.mesh_jobs[key]
                if fut.cancelled():
                    continue
                try:
                    cq, cr, token, o, w, L, dt = fut.result()
                except Exception:
                    continue
                self.timings['mesh'].append(dt)
                c = self.chunks.get(key)
                if c is not None and token == c.token and c.state == 'pending':
                    self.uploads.append((key, token, o, w, L))
                elif c is not None and c.state == 'pending':
                    c.state = 'dirty'

    def _lod_center(self):
        cq0, cr0 = self.center
        return (cq0 // LOD_GROUP, cr0 // LOD_GROUP)

    def _lod_dist(self, key):
        sq0, sr0 = self._lod_center()
        x, z = center((key[0] - sq0) * LOD_GROUP * CHUNK, (key[1] - sr0) * LOD_GROUP * CHUNK)
        return math.hypot(x, z)

    def _collect_lod(self, budget=2):
        from .renderer import LodMesh
        for key, fut in list(self.lod_jobs.items()):
            if budget <= 0:
                break
            if fut.done():
                del self.lod_jobs[key]
                try:
                    sq, sr, data, ranges, dt, step = fut.result()
                except Exception:
                    continue
                self.timings.setdefault('lod', deque(maxlen=200)).append(dt)
                if self._lod_dist(key) <= self.lod_radius + 3 * LOD_GROUP * CHUNK_SPAN:
                    old = self.lod.pop(key, None)
                    if old:
                        old.release()
                    self.lod[key] = LodMesh(self.renderer, sq, sr, data, ranges)
                    self.lod[key].step = step
                    budget -= 1
        # unload far ones
        for key in [k for k in self.lod if self._lod_dist(k) > self.lod_radius + 3 * LOD_GROUP * CHUNK_SPAN]:
            self.lod.pop(key).release()

    def _schedule_lod(self, budget):
        if budget <= 0 or not self.lod_offsets:
            return
        sq0, sr0 = self._lod_center()
        for a, b in self.lod_offsets:
            if budget <= 0:
                break
            key = (sq0 + a, sr0 + b)
            if key in self.lod_jobs:
                continue
            if key in self.lod and self.lod[key].step <= (4 if self._lod_dist(key) > COARSE_FROM * CHUNK_SPAN else 2):
                continue
            want = 4 if self._lod_dist(key) > COARSE_FROM * CHUNK_SPAN else 2
            paths = None
            if self.storage:
                paths = {(key[0] * LOD_GROUP + i, key[1] * LOD_GROUP + k): self.storage.chunk_file(key[0] * LOD_GROUP + i, key[1] * LOD_GROUP + k)
                         for i in range(LOD_GROUP) for k in range(LOD_GROUP)}
            self.lod_jobs[key] = self.pool.submit(workers.lod_job, self.seed, key[0], key[1], paths, want, self.gen_settings)
            budget -= 1

    def _schedule(self):
        cq0, cr0 = self.center
        budget = MAX_JOBS_IN_FLIGHT - len(self.gen_jobs) - len(self.mesh_jobs)
        if budget <= 0:
            return
        # meshes first for chunks whose data is ready (closest first), then data
        for a, b in self.mesh_offsets:
            if budget <= 0:
                break
            key = (cq0 + a, cr0 + b)
            c = self.chunks.get(key)
            if c is not None and c.state in ('none', 'dirty') and key not in self.mesh_jobs and self._have_neighbours(*key):
                c.state = 'pending'
                self.mesh_jobs[key] = self.pool.submit(workers.mesh_job, key[0], key[1], c.token, self._padded(*key), c.realm, self._padded_meta(*key))
                budget -= 1
        for a, b in self.data_offsets:
            if budget <= 0:
                break
            key = (cq0 + a, cr0 + b)
            if key not in self.chunks and key not in self.gen_jobs:
                path = self.storage.chunk_file(*key) if self.storage else None
                self.gen_jobs[key] = self.pool.submit(workers.generate_job, self.seed, key[0], key[1], path, self.gen_settings)
                budget -= 1

    def _upload(self, budget):
        t0 = time.perf_counter()
        while self.uploads and budget > 0 and time.perf_counter() - t0 < 0.008:
            key, token, o, w, L = self.uploads.popleft()
            c = self.chunks.get(key)
            if c is not None and token == c.token:
                self._install(c, o, w, L)
                budget -= 1

    def _unload(self):
        cq0, cr0 = self.center
        for key, c in list(self.chunks.items()):
            d = self._dist(key)
            if d > self.keep_radius:
                if c.modified:
                    self.save_chunk(c)
                if c.mesh:
                    c.mesh.release()
                del self.chunks[key]
                self.dirty.discard(key)
            elif c.mesh and (key[0] - cq0, key[1] - cr0) not in self.mesh_set and d > self.radius + CHUNK_SPAN:
                c.mesh.release()
                c.mesh = None
                c.state = 'none'

    # ------------------------------------------------------------------ saving / queries
    def save_chunk(self, c):
        if self.storage:
            self.storage.save_chunk(c.cq, c.cr, c.cells, c.meta, c.realm)
        c.modified = False

    def save_modified(self):
        n = 0
        for c in self.chunks.values():
            if c.modified:
                self.save_chunk(c)
                n += 1
        return n

    def meshes(self):
        out = [c.mesh for c in self.chunks.values() if c.mesh is not None]
        ch = self.chunks
        G = LOD_GROUP
        for (sq, sr), m in self.lod.items():
            runs, cur = [], None
            for j, (first, cnt) in enumerate(m.ranges):
                i, k = divmod(j, G)
                c = ch.get((sq * G + i, sr * G + k))
                need = cnt > 0 and (c is None or c.mesh is None)
                if need:
                    if cur and cur[0] + cur[1] == first:
                        cur[1] += cnt
                    else:
                        cur = [first, cnt]
                        runs.append(cur)
            if runs:
                m.runs = runs
                out.append(m)
        return out

    def ready_at(self, x, z):
        q, r = cell_at(x, z)
        c = self.chunks.get(chunk_of(q, r))
        return c is not None and c.state == 'ready'

    def progress(self, x, z, radius_units=60.0):
        q, r = cell_at(x, z)
        cq0, cr0 = chunk_of(q, r)
        keys = [(cq0 + a, cr0 + b) for a, b in self.mesh_offsets if math.hypot(*center(a * CHUNK, b * CHUNK)) <= radius_units]
        done = sum(1 for k in keys if k in self.chunks and self.chunks[k].state == 'ready')
        return done / max(1, len(keys))

    def column_top(self, q, r, solid_only=True):
        c = self.chunks.get((q // CHUNK, r // CHUNK))
        if c is None:
            return None
        col = c.cells[q % CHUNK, :, r % CHUNK]
        idx = np.nonzero(MT.SOLID[col] if solid_only else col)[0]
        return int(idx[-1]) if len(idx) else -1

    def realm_at(self, q, r):
        c = self.chunks.get((q // CHUNK, r // CHUNK))
        return None if c is None else int(c.realm[q % CHUNK, r % CHUNK])

    def busy_lod(self):
        return len(self.lod_jobs)

    def busy(self):
        return len(self.gen_jobs) + len(self.mesh_jobs) + len(self.uploads)

    def close(self):
        self.closed = True
        for fut in list(self.gen_jobs.values()) + list(self.mesh_jobs.values()):
            fut.cancel()
        self.gen_jobs.clear()
        self.mesh_jobs.clear()
        self.uploads.clear()
        for c in self.chunks.values():
            if c.mesh:
                c.mesh.release()
        self.chunks.clear()
        for fut in self.lod_jobs.values():
            fut.cancel()
        self.lod_jobs.clear()
        for m in self.lod.values():
            m.release()
        self.lod.clear()

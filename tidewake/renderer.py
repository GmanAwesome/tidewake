"""Draws the sky, the cloud sea, island chunks, water, outlines and motes.

Camera-relative: chunk origins are float64 on the CPU; only (origin - camera) reaches
the GPU, so the world stays crisp no matter how far you wander.
"""
import math

import numpy as np
import moderngl

from . import shaders
from .config import CLOUD_SEA, LAYER, HEX, LAYERS
from .hexgrid import CORNERS, chunk_origin
from .mathutil import frustum_planes, boxes_visible
from .mesher import VERT
from . import materials as MT

FMT = [('3f 4f1 4f1 4f1', 'in_pos', 'in_col', 'in_nrm', 'in_mat')]
LIGHT_COL = {k: np.array(v[0]) for k, v in MT.LIGHTS.items()}
LIGHT_RAD = {k: v[1] for k, v in MT.LIGHTS.items()}


def _set(prog, name, value):
    if name in prog:
        prog[name].value = value


def _write(prog, name, data):
    if name in prog:
        prog[name].write(data)


def _mat(m):
    return np.ascontiguousarray(m.T, dtype='f4').tobytes()


class ChunkMesh:
    def __init__(self, renderer, cq, cr, opaque, water, lights):
        ctx, prog = renderer.ctx, renderer.chunk_prog
        self.cq, self.cr = cq, cr
        self.ox, self.oz = chunk_origin(cq, cr)
        self.n_o = len(opaque) // VERT.itemsize
        self.n_w = len(water) // VERT.itemsize
        self.vbo = self.vao = self.wvbo = self.wvao = None
        ys = []
        if self.n_o:
            self.vbo = ctx.buffer(opaque)
            self.vao = ctx.vertex_array(prog, [(self.vbo, '3f 4f1 4f1 4f1', 'in_pos', 'in_col', 'in_nrm', 'in_mat')])
            p = np.frombuffer(opaque, VERT)['p']
            ys += [p[:, 1].min(), p[:, 1].max()]
        if self.n_w:
            self.wvbo = ctx.buffer(water)
            self.wvao = ctx.vertex_array(prog, [(self.wvbo, '3f 4f1 4f1 4f1', 'in_pos', 'in_col', 'in_nrm', 'in_mat')])
            p = np.frombuffer(water, VERT)['p']
            ys += [p[:, 1].min(), p[:, 1].max()]
        self.y0, self.y1 = (float(min(ys)), float(max(ys))) if ys else (0.0, 0.0)
        self.lights = lights            # (M, 4): local x, y, z, material
        self.bytes = len(opaque) + len(water)

    def release(self):
        for o in (self.vao, self.vbo, self.wvao, self.wvbo):
            if o is not None:
                o.release()


class LodMesh(ChunkMesh):
    """A far-away 4x4-chunk mesh; `runs` (set by the world each frame) are the vertex ranges to draw."""
    def __init__(self, renderer, sq, sr, data, ranges):
        from .workers import LOD_GROUP
        super().__init__(renderer, sq * LOD_GROUP, sr * LOD_GROUP, data, b'', np.zeros((0, 4), np.float32))
        self.ranges = ranges
        self.runs = []
        self.span = LOD_GROUP


def _noise_texture(seed=7, n=256):
    """Tileable smooth noise (sum of integer-frequency waves), two channels."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n, 4), np.float32)
    u = np.arange(n) / n
    U, V = np.meshgrid(u, u, indexing='ij')
    for ch, (fmin, fmax, count) in enumerate(((1, 6, 26), (3, 14, 40))):
        acc = np.zeros((n, n))
        for _ in range(count):
            fx, fy = rng.integers(-fmax, fmax + 1, 2)
            if abs(fx) + abs(fy) < fmin:
                continue
            amp = 1.0 / math.hypot(fx, fy)
            acc += amp * np.sin(2 * math.pi * (fx * U + fy * V) + rng.uniform(0, 6.3))
        acc = (acc - acc.min()) / (acc.max() - acc.min())
        out[..., ch] = acc
    out[..., 3] = 1
    return (out * 255).astype(np.uint8)


class Renderer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.chunk_prog = ctx.program(vertex_shader=shaders.CHUNK_VS, fragment_shader=shaders.CHUNK_FS)
        self.sky_prog = ctx.program(vertex_shader=shaders.SKY_VS, fragment_shader=shaders.SKY_FS)
        self.cloud_prog = ctx.program(vertex_shader=shaders.CLOUD_VS, fragment_shader=shaders.CLOUD_FS)
        self.line_prog = ctx.program(vertex_shader=shaders.LINE_VS, fragment_shader=shaders.LINE_FS)
        self.point_prog = ctx.program(vertex_shader=shaders.POINT_VS, fragment_shader=shaders.POINT_FS)
        self.sky_vao = ctx.vertex_array(self.sky_prog, [])
        tex = _noise_texture()
        self.noise_tex = ctx.texture((256, 256), 4, tex.tobytes())
        self.noise_tex.repeat_x = self.noise_tex.repeat_y = True
        self.noise_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.cloud_prog['u_noise'] = 1
        # the texture pack: one atlas of detail tiles (see texpack.py), mipmapped
        from . import texpack
        from . import materials as _MT
        img, rows = texpack.atlas(len(_MT.NAMES))
        self.atlas_tex = ctx.texture((img.shape[1], img.shape[0]), 2, img.tobytes())
        self.atlas_tex.build_mipmaps(0, 5)
        self.atlas_tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        try:
            self.atlas_tex.anisotropy = 4.0
        except Exception:
            pass
        self.chunk_prog['u_atlas'] = 2
        self.chunk_prog['u_noise2'] = 1
        self.chunk_prog['u_atlas_rows'] = float(rows)
        self.chunk_prog['u_nmat'] = float(len(_MT.NAMES))
        glasses = [int(i) for i in __import__('numpy').where(_MT.IS_GLASS)[0][:8]]
        self.chunk_prog['u_n_glass'] = len(glasses)
        # pad the array uniform to the declared length
        padded = glasses + [0] * (8 - len(glasses))
        try:
            self.chunk_prog['u_glasses'].value = tuple(padded)
        except Exception:
            for i, g in enumerate(padded):
                try:
                    self.chunk_prog[f'u_glasses[{i}]'].value = g
                except Exception:
                    pass
        import os as _os
        self.detail = float(_os.environ.get('TIDEWAKE_DETAIL', '1'))
        self.cloud_step = 4.0
        self.set_cloud_grid(140)
        # hex prism outline (unit cell)
        lines = []
        for k in range(6):
            a, b = CORNERS[k], CORNERS[(k + 1) % 6]
            for y in (0.0, 1.0):
                lines += [(a[0], y, a[1]), (b[0], y, b[1])]
            lines += [(a[0], 0.0, a[1]), (a[0], 1.0, a[1])]
        self.outline = np.array(lines, dtype='f4')
        self.line_vbo = ctx.buffer(reserve=4 * 3 * 4096, dynamic=True)
        self.line_vao = ctx.vertex_array(self.line_prog, [(self.line_vbo, '3f', 'in_pos')])
        self.point_vbo = ctx.buffer(reserve=8 * 4 * 4096, dynamic=True)
        self.point_vao = ctx.vertex_array(self.point_prog, [(self.point_vbo, '3f 4f 1f', 'in_pos', 'in_col', 'in_size')])
        self.stats = {'drawn': 0, 'verts': 0}
        self.dyn_vbo = ctx.buffer(reserve=VERT.itemsize * 60000, dynamic=True)
        self.dyn_vao = ctx.vertex_array(self.chunk_prog, [(self.dyn_vbo, '3f 4f1 4f1 4f1', 'in_pos', 'in_col', 'in_nrm', 'in_mat')])
        self._lm_vbo = self._lm_vao = None
        self._lm_n = 0
        self._lm_key = None
        self.icon_tex = None
        self.icon_uv = {}

    def _draw_verts(self, verts):
        if verts is None or not len(verts):
            return
        data = np.ascontiguousarray(verts, VERT).tobytes()
        if len(data) > self.dyn_vbo.size:
            self.dyn_vbo.orphan(len(data))
        self.dyn_vbo.write(data)
        _set(self.chunk_prog, 'u_offset', (0.0, 0.0, 0.0))
        self.dyn_vao.render(moderngl.TRIANGLES, vertices=len(data) // VERT.itemsize)


    def draw_landmark(self, cam, verts):
        """Distant teaser mesh in world space; uploaded once, offset by the camera."""
        if verts is None or not len(verts):
            return
        key = id(verts)
        if self._lm_key != key or self._lm_vao is None:
            data = np.ascontiguousarray(verts, VERT).tobytes()
            if self._lm_vbo is None or len(data) > self._lm_vbo.size:
                self._lm_vbo = self.ctx.buffer(data)
                self._lm_vao = self.ctx.vertex_array(
                    self.chunk_prog, [(self._lm_vbo, '3f 4f1 4f1 4f1', 'in_pos', 'in_col', 'in_nrm', 'in_mat')])
            else:
                self._lm_vbo.write(data)
            self._lm_n = len(verts)
            self._lm_key = key
        _set(self.chunk_prog, 'u_offset', (-float(cam[0]), -float(cam[1]), -float(cam[2])))
        self._lm_vao.render(moderngl.TRIANGLES, vertices=self._lm_n)
        _set(self.chunk_prog, 'u_offset', (0.0, 0.0, 0.0))

    def draw_held(self, verts):
        """Draw the item in your hand (camera-relative), always in front of the world."""
        if verts is None or not len(verts):
            return
        ctx = self.ctx
        ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        _set(self.chunk_prog, 'u_alpha', 1.0)
        _set(self.chunk_prog, 'u_hand', 1.0)
        self._draw_verts(verts)
        _set(self.chunk_prog, 'u_hand', 0.0)
        ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

    def build_icons(self, models, cell=64, cols=16, art=None):
        """Render item models into an atlas texture. models: {id: (verts, yaw, pitch, scale)}"""
        from .mathutil import view_matrix
        ids = sorted(models)
        rows = (len(ids) + cols - 1) // cols
        W, H = cols * cell, rows * cell
        ctx = self.ctx
        tex = ctx.texture((W, H), 4)
        depth = ctx.depth_renderbuffer((W, H))
        fbo = ctx.framebuffer([tex], depth)
        fbo.use()
        fbo.clear(0, 0, 0, 0, 1.0)
        p = self.chunk_prog
        _set(p, 'u_sun_dir', tuple(np.array([0.45, 0.8, 0.35]) / np.linalg.norm([0.45, 0.8, 0.35])))
        _set(p, 'u_sun_col', (0.95, 0.90, 0.85))
        _set(p, 'u_amb_top', (0.75, 0.74, 0.80))
        _set(p, 'u_amb_bot', (0.45, 0.42, 0.50))
        _set(p, 'u_fog_col', (1, 1, 1))
        _set(p, 'u_cloud_col', (1, 1, 1))
        _set(p, 'u_fog_start', 1e6)
        _set(p, 'u_fog_end', 2e6)
        _set(p, 'u_cloud_y', -1e6)
        _set(p, 'u_glow', 0.8)
        _set(p, 'u_time', 0.0)
        _set(p, 'u_nl', 0)
        _set(p, 'u_alpha', 1.0)
        _set(p, 'u_hand', 0.0)
        ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        ctx.disable(moderngl.BLEND)
        s = 0.62
        proj = np.array([[1 / s, 0, 0, 0], [0, 1 / s, 0, 0], [0, 0, -0.1, 0], [0, 0, 0, 1]], dtype=np.float64)
        _set(p, 'u_detail', 1.0)
        _set(p, 'u_cam_y', 0.35)          # block icons span y -0.35..0.35 -> one texture layer
        _set(p, 'u_cam_mod', (0.3, 0.2))
        self.atlas_tex.use(2)
        self.noise_tex.use(1)
        for k, iid in enumerate(ids):
            verts, yaw, pitch, scale = models[iid]
            col, row = k % cols, k // cols
            ctx.viewport = (col * cell, H - (row + 1) * cell, cell, cell)
            vr = view_matrix((0, 0, 0), yaw, pitch)
            # camera sits back along its view; the model is at the origin
            from .mathutil import forward_vector
            fx, fy, fz = forward_vector(yaw, pitch)
            T = np.eye(4)
            T[:3, 3] = [fx * 5, fy * 5, fz * 5]
            _write(p, 'u_vp', _mat(proj @ vr @ T))
            v = verts.copy()
            v['p'] = v['p'] * scale
            self._draw_verts(v)
            self.icon_uv[iid] = (col * cell / W, 1 - (row + 1) * cell / H, (col + 1) * cell / W, 1 - row * cell / H)
            if art and iid in art:
                img = np.ascontiguousarray(art[iid][::-1])
                if img.shape[0] != cell:
                    k = max(1, cell // img.shape[0])
                    img = np.repeat(np.repeat(img, k, 0), k, 1)[:cell, :cell]
                tex.write(img.tobytes(), viewport=(col * cell, H - (row + 1) * cell, cell, cell))
        _set(p, 'u_detail', float(self.detail))
        ctx.screen.use()
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.build_mipmaps()
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        fbo.release()
        depth.release()
        self.icon_tex = tex
        self.icon_px = (W, H)

    def set_cloud_grid(self, n):
        s = self.cloud_step
        ax = (np.arange(n + 1) - n / 2) * s
        X, Z = np.meshgrid(ax, ax, indexing='ij')
        verts = np.stack([X, Z], -1).astype('f4')
        idx = []
        i = np.arange(n)[:, None] * (n + 1) + np.arange(n)[None, :]
        a, b, c, d = i, i + 1, i + n + 1, i + n + 2
        idx = np.stack([a, c, b, b, c, d], -1).reshape(-1).astype('i4')
        if hasattr(self, 'cloud_vao'):
            self.cloud_vao.release()
        self.cloud_vbo = self.ctx.buffer(verts.tobytes())
        self.cloud_ibo = self.ctx.buffer(idx.tobytes())
        self.cloud_vao = self.ctx.vertex_array(self.cloud_prog, [(self.cloud_vbo, '2f', 'in_pos')], self.cloud_ibo)

    # ------------------------------------------------------------------ frame
    def draw(self, cam, proj, view_rot, meshes, atmo, fog_end, time_, extra_lights=(), clouds=True, dynamic=None, landmark=None):
        """cam: float64 (x, y, z). view_rot: rotation-only view matrix. meshes: iterable of ChunkMesh."""
        ctx = self.ctx
        vp = proj @ view_rot
        cx, cy, cz = cam
        hzn = atmo['horizon']
        fog_col = hzn * 0.9 + atmo['zenith'] * 0.1
        cloud_y = CLOUD_SEA * LAYER + 1.5 - cy
        ctx.clear(*fog_col, 1.0)
        ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND)
        # sky
        sp = self.sky_prog
        _write(sp, 'u_inv', _mat(np.linalg.inv(vp)))
        _set(sp, 'u_zenith', tuple(atmo['zenith']))
        _set(sp, 'u_horizon', tuple(hzn))
        _set(sp, 'u_sun_dir', tuple(atmo['sun_dir']))
        _set(sp, 'u_sun_col', tuple(atmo['sun_col']))
        _set(sp, 'u_moon_dir', tuple(atmo['moon_dir']))
        _set(sp, 'u_dusk', float(atmo['dusk']))
        _set(sp, 'u_time', float(time_))
        self.sky_vao.render(moderngl.TRIANGLES, vertices=3)

        ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        p = self.chunk_prog
        _write(p, 'u_vp', _mat(vp))
        _set(p, 'u_sun_dir', tuple(atmo['light_dir']))
        _set(p, 'u_sun_col', tuple(atmo['sun_col'] * (1 - 0.45 * atmo['dusk'])))
        _set(p, 'u_amb_top', tuple(atmo['amb_top']))
        _set(p, 'u_amb_bot', tuple(atmo['amb_bot']))
        _set(p, 'u_fog_col', tuple(fog_col))
        _set(p, 'u_cloud_col', tuple(atmo['cloud_top'] * 0.92))
        _set(p, 'u_fog_start', fog_end * 0.45)
        _set(p, 'u_fog_end', fog_end)
        _set(p, 'u_cloud_y', cloud_y)
        _set(p, 'u_glow', float(atmo['glow']))
        _set(p, 'u_time', float(time_))
        _set(p, 'u_cam_mod', (float(cx % 1000.0), float(cz % 1000.0)))
        _set(p, 'u_cam_y', float(cy))
        _set(p, 'u_detail', float(self.detail))
        self.atlas_tex.use(2)
        self.noise_tex.use(1)

        # visible chunks
        meshes = [m for m in meshes if m.n_o or m.n_w]
        if meshes:
            ox = np.array([m.ox for m in meshes]) - cx
            oz = np.array([m.oz for m in meshes]) - cz
            sp = np.array([getattr(m, 'span', 1) for m in meshes], dtype=np.float64)
            mins = np.stack([ox - 2.0, np.array([m.y0 for m in meshes]) - cy, oz - 2.0], 1)
            maxs = np.stack([ox + 42.0 * sp, np.array([m.y1 for m in meshes]) - cy, oz + 24.0 * sp + 2], 1)
            # rhombus chunk: x spans [-1, 16*sqrt3 + 8*sqrt3], z spans [-1, 24]
            maxs[:, 0] = ox + HEX * 1.7320508 * 24 * sp + 1
            mins[:, 0] = ox - 1.0
            vis = boxes_visible(frustum_planes(vp), mins, maxs)
            dist = np.maximum(0.0, np.hypot(ox + 20 * sp, oz + 11 * sp) - 20 * (sp - 1))
            vis &= dist < fog_end + 60
            order = np.argsort(dist)
            meshes_v = [(meshes[i], ox[i], oz[i]) for i in order if vis[i]]
        else:
            meshes_v = []

        # lights: gather from every mesh (not just the closest 40), prefer real lamps
        lp, lc = [], []
        L = [np.column_stack([m.lights[:, 0] + ox_, m.lights[:, 1] - cy, m.lights[:, 2] + oz_, m.lights[:, 3]])
             for m, ox_, oz_ in meshes_v if len(m.lights)]
        # also pull lights from culled-but-nearby chunks so a lamp around a corner still lights the room
        visible_ids = {id(m) for m, _, _ in meshes_v}
        for m in meshes:
            if id(m) in visible_ids or not len(getattr(m, 'lights', ())):
                continue
            ox_, oz_ = m.ox - cx, m.oz - cz
            L.append(np.column_stack([m.lights[:, 0] + ox_, m.lights[:, 1] - cy, m.lights[:, 2] + oz_, m.lights[:, 3]]))
        L += [np.array(e, dtype=np.float64).reshape(-1, 4) for e in extra_lights if len(e)]
        if L:
            A = np.concatenate(L)
            d = np.linalg.norm(A[:, :3], axis=1)
            rad = np.array([LIGHT_RAD.get(int(m), 6.0) for m in A[:, 3]])
            # score by distance relative to radius so a lantern is not dropped for a closer glowcap
            score = d / np.maximum(rad, 1.0)
            sel = np.argsort(score)[:max(1, min(32, int(getattr(self, 'light_cap', 32))))]
            for i in sel:
                mid = int(A[i, 3])
                lp.append((A[i, 0], A[i, 1], A[i, 2], LIGHT_RAD.get(mid, 6.0)))
                lc.append(tuple(LIGHT_COL.get(mid, np.array([1, 0.8, 0.5])) * (0.45 + 0.75 * atmo['dusk'])))
        _set(p, 'u_nl', len(lp))
        if lp:
            _write(p, 'u_lp', np.array(lp + [(0, 0, 0, 1)] * (32 - len(lp)), 'f4').tobytes())
            _write(p, 'u_lc', np.array(lc + [(0, 0, 0)] * (32 - len(lc)), 'f4').tobytes())

        _set(p, 'u_alpha', 1.0)
        verts = 0
        for m, ox_, oz_ in meshes_v:
            if m.vao:
                _set(p, 'u_offset', (float(ox_), float(-cy), float(oz_)))
                runs = getattr(m, 'runs', None)
                if runs is None:
                    m.vao.render(moderngl.TRIANGLES)
                    verts += m.n_o
                else:
                    for first, cnt in runs:
                        m.vao.render(moderngl.TRIANGLES, vertices=cnt, first=first)
                        verts += cnt
        self._draw_verts(dynamic)
        if landmark is not None:
            self.draw_landmark(cam, landmark)
        # cloud sea
        if clouds:
            ctx.disable(moderngl.CULL_FACE)
            c = self.cloud_prog
            _write(c, 'u_vp', _mat(vp))
            s = self.cloud_step
            snap = (cx % s, cz % s)
            _set(c, 'u_snap', (float(snap[0]), float(snap[1])))
            _set(c, 'u_cam_mod', (float((cx - snap[0]) % 1024.0), float((cz - snap[1]) % 1024.0)))
            _set(c, 'u_cloud_y', cloud_y - 1.5)
            _set(c, 'u_time', float(time_ % 10000.0))
            _set(c, 'u_sun_col', tuple(atmo['sun_col']))
            _set(c, 'u_amb_top', tuple(atmo['amb_top']))
            _set(c, 'u_cloud_col', tuple(atmo['cloud_top']))
            _set(c, 'u_deep_col', tuple(atmo['cloud_deep']))
            _set(c, 'u_fog_col', tuple(fog_col))
            _set(c, 'u_fog_end', fog_end)
            _set(c, 'u_dusk', float(atmo['dusk']))
            self.noise_tex.use(1)
            self.cloud_vao.render(moderngl.TRIANGLES)
            ctx.enable(moderngl.CULL_FACE)
        # water
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        _set(p, 'u_alpha', 0.72)
        ctx.disable(moderngl.CULL_FACE)
        for m, ox_, oz_ in reversed(meshes_v):
            if m.wvao:
                _set(p, 'u_offset', (float(ox_), float(-cy), float(oz_)))
                m.wvao.render(moderngl.TRIANGLES)
        ctx.enable(moderngl.CULL_FACE)
        ctx.disable(moderngl.BLEND)
        self.stats = {'drawn': len(meshes_v), 'verts': verts, 'lights': len(lp)}
        self.vp = vp

    def draw_outline(self, rel, color=(1, 1, 1, 0.55), scale=1.0):
        """Outline a cell; rel = cell bottom-centre relative to the camera."""
        pts = self.outline.copy()
        pts[:, 0] *= 1.02 * scale
        pts[:, 2] *= 1.02 * scale
        pts[:, 1] = pts[:, 1] * (LAYER + 0.04) - 0.02
        self.line_vbo.write(pts.tobytes())
        _write(self.line_prog, 'u_vp', _mat(self.vp))
        _set(self.line_prog, 'u_offset', tuple(float(v) for v in rel))
        _set(self.line_prog, 'u_color', color)
        ctx = self.ctx
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.line_vao.render(moderngl.LINES, vertices=len(pts))
        ctx.disable(moderngl.BLEND)

    def draw_points(self, data):
        """data: (N, 8) float32 rel-camera pos, rgba, size."""
        if not len(data):
            return
        data = np.ascontiguousarray(data[:4096], 'f4')
        self.point_vbo.write(data.tobytes())
        _write(self.point_prog, 'u_vp', _mat(self.vp))
        _set(self.point_prog, 'u_scale', float(self.ctx.viewport[3]) * 0.6)
        ctx = self.ctx
        ctx.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE
        ctx.depth_mask = False
        self.point_vao.render(moderngl.POINTS, vertices=len(data))
        ctx.depth_mask = True
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        ctx.disable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)

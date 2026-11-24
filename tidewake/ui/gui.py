"""A small immediate-mode GUI: soft rounded panels, hexagon gems and text.

Shapes are drawn with signed-distance fields in one shader (crisp at any scale);
text uses pyglet labels with the bundled fonts. Call flush() to layer things.
"""
import math
import os
import sys
import time

import numpy as np
import moderngl
import pyglet

from .. import shaders

INK = (0.24, 0.22, 0.34, 1.0)          # deep plum text
PAPER = (0.99, 0.97, 0.94, 0.94)       # warm cream panels
ACCENT = (0.98, 0.62, 0.52, 1.0)       # peach
ACCENT2 = (0.55, 0.50, 0.86, 1.0)      # lavender
MUTED = (0.50, 0.47, 0.60, 1.0)
WHITE = (1, 1, 1, 1)

_fonts_loaded = False
FONT_TITLE = FONT_BODY = FONT_BOLD = None


def _resource(*parts):
    base = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


def load_fonts():
    """Bundled fonts first (same look everywhere), then common system fonts as a fallback."""
    global _fonts_loaded, FONT_TITLE, FONT_BODY, FONT_BOLD
    if _fonts_loaded:
        return
    _fonts_loaded = True
    names = {}
    for fname, fam in (('TidewakeTitle.ttf', 'Tidewake Title'), ('TidewakeBody.ttf', 'Tidewake Body'),
                       ('TidewakeBold.ttf', 'Tidewake Bold')):
        try:
            pyglet.font.add_file(_resource('assets', 'fonts', fname))
            if pyglet.font.have_font(fam):
                names[fam] = fam
        except Exception as e:
            print('font load failed', fname, e)
    fallback = None
    for name in ('Segoe UI', 'Tahoma', 'Arial', 'Verdana', 'DejaVu Sans', 'Liberation Sans', 'Noto Sans'):
        try:
            if pyglet.font.have_font(name):
                fallback = name
                break
        except Exception:
            pass
    FONT_TITLE = names.get('Tidewake Title', fallback)
    FONT_BODY = names.get('Tidewake Body', fallback)
    FONT_BOLD = names.get('Tidewake Bold', fallback)


def _c255(c):
    return tuple(int(max(0, min(1, v)) * 255) for v in (c if len(c) == 4 else (*c, 1.0)))


class Gui:
    def __init__(self, ctx):
        load_fonts()
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=shaders.UI_VS, fragment_shader=shaders.UI_FS)
        self.stride = 2 + 2 + 4 + 4 + 4
        self.vbo = ctx.buffer(reserve=self.stride * 4 * 6 * 4000, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, '2f 2f 4f 4f 4f', 'in_pos', 'in_local', 'in_shape', 'in_col', 'in_col2')])
        self.prog['u_tex'] = 0
        self.verts = []
        self.labels = {}
        self.used = set()
        self.queue = []
        self.textures = {}
        self.tex_queue = []
        self.mx = self.my = 0
        self.mouse_down = False
        self.clicks = []
        self.scroll = 0
        self.typed = ''
        self.keys = []
        self.focus = None
        self.active = None
        self.sound = None
        self.hovered = None
        self._last_hover = None
        self.w = self.h = 1
        self.s = 1.0
        self.t = time.time()

    # ------------------------------------------------------------------ frame
    def begin(self, width, height, scale):
        self.w, self.h, self.s = width, height, scale
        self.verts = []
        self.queue = []
        self.used = set()
        self.hovered = None
        self.t = time.time()

    def flush(self):
        ctx = self.ctx
        ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        if self.verts:
            data = np.array(self.verts, dtype='f4')
            if data.nbytes > self.vbo.size:
                self.vbo.orphan(data.nbytes)
            self.vbo.write(data.tobytes())
            self.prog['u_screen'].value = (float(self.w), float(self.h))
            # textured quads are drawn in sequence with their texture bound
            start = 0
            for (vstart, tex) in self.tex_queue + [(len(data) // 1, None)]:
                pass
            if not self.tex_queue:
                self.vao.render(moderngl.TRIANGLES, vertices=len(self.verts))
            else:
                cur = 0
                for vstart, tex in self.tex_queue:
                    if vstart > cur:
                        self.vao.render(moderngl.TRIANGLES, vertices=vstart - cur, first=cur)
                    tex.use(0)
                    self.vao.render(moderngl.TRIANGLES, vertices=6, first=vstart)
                    cur = vstart + 6
                if cur < len(self.verts):
                    self.vao.render(moderngl.TRIANGLES, vertices=len(self.verts) - cur, first=cur)
        for lab in self.queue:
            lab.draw()
        self.verts = []
        self.queue = []
        self.tex_queue = []
        ctx.enable(moderngl.BLEND)

    def end(self):
        self.flush()
        for k in list(self.labels):
            if k not in self.used:
                self.labels.pop(k).delete()
        if self.hovered != self._last_hover and self.hovered is not None and self.sound:
            self.sound('hover')
        self._last_hover = self.hovered
        self.clicks = []
        self.scroll = 0
        self.typed = ''
        self.keys = []

    # ------------------------------------------------------------------ shapes
    def _shape(self, cx, cy, hw, hh, radius, kind, color, border=(0, 0, 0, 0), pad=1.5):
        x0, x1 = cx - hw - pad, cx + hw + pad
        y0, y1 = cy - hh - pad, cy + hh + pad
        shape = (hw, hh, radius, kind)
        col = tuple(color) if len(color) == 4 else (*color, 1.0)
        b = tuple(border)
        for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y0), (x1, y1), (x0, y1)):
            self.verts.append((x, y, x - cx, y - cy, *shape, *col, *b))

    def rect(self, x, y, w, h, color, radius=0.0, border=None, border_w=0.0):
        r = min(radius, w / 2, h / 2)
        bc = (*border[:3], border_w) if border else (0, 0, 0, 0)
        self._shape(x + w / 2, y + h / 2, w / 2, h / 2, r, 0.0, color, bc)

    def shadow(self, x, y, w, h, radius=14.0, alpha=0.18, spread=10.0):
        sp = spread * self.s
        self.verts += []
        cx, cy = x + w / 2, y + h / 2 - sp * 0.4
        hw, hh = w / 2 + sp * 0.3, h / 2 + sp * 0.3
        x0, x1, y0, y1 = cx - hw - sp, cx + hw + sp, cy - hh - sp, cy + hh + sp
        for (px, py) in ((x0, y0), (x1, y0), (x1, y1), (x0, y0), (x1, y1), (x0, y1)):
            self.verts.append((px, py, px - cx, py - cy, hw, hh, sp, 3.0, 0.15, 0.10, 0.25, alpha, 0, 0, 0, 0))

    def hexagon(self, cx, cy, r, color, border=None, border_w=0.0):
        bc = (*border[:3], border_w) if border else (0, 0, 0, 0)
        self._shape(cx, cy, r, r, 0.0, 1.0, color, bc)

    def circle(self, cx, cy, r, color, border=None, border_w=0.0):
        bc = (*border[:3], border_w) if border else (0, 0, 0, 0)
        self._shape(cx, cy, r, r, 0.0, 2.0, color, bc)

    def image(self, key, rgba, x, y, w, h, color=(1, 1, 1, 1)):
        """Textured quad from an (h, w, 4) uint8 array (row 0 = top). Cached by key."""
        tex = self.textures.get(key)
        if tex is None:
            img = np.ascontiguousarray(rgba[::-1])
            tex = self.ctx.texture((img.shape[1], img.shape[0]), 4, img.tobytes())
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.textures[key] = tex
        self.tex_queue.append((len(self.verts), tex))
        uv = ((0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1))
        pts = ((x, y), (x + w, y), (x + w, y + h), (x, y), (x + w, y + h), (x, y + h))
        for (px, py), (u, v) in zip(pts, uv):
            self.verts.append((px, py, u, v, 0, 0, 0, 5.0, *color, 0, 0, 0, 0))

    def icon_tex(self, tex, uv, x, y, w, h, color=(1, 1, 1, 1)):
        """Quad from part of an existing texture. uv = (u0, v0, u1, v1), v0 at the bottom."""
        u0, v0, u1, v1 = uv
        self.tex_queue.append((len(self.verts), tex))
        uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v0), (u1, v1), (u0, v1))
        pts = ((x, y), (x + w, y), (x + w, y + h), (x, y), (x + w, y + h), (x, y + h))
        for (px, py), (u, v) in zip(pts, uvs):
            self.verts.append((px, py, u, v, 0, 0, 0, 5.0, *color, 0, 0, 0, 0))

    def drop_texture(self, key):
        t = self.textures.pop(key, None)
        if t:
            t.release()

    # ------------------------------------------------------------------ text
    def text(self, s, x, y, size=11, color=INK, anchor_x='left', anchor_y='baseline', font='body', width=None,
             align='left', key=None):
        fname = {'title': FONT_TITLE, 'bold': FONT_BOLD}.get(font, FONT_BODY)
        col = _c255(color)
        px = size * self.s
        k = key or (s, round(px, 1), col, anchor_x, anchor_y, fname, width, align)
        lab = self.labels.get(k)
        if lab is None:
            kw = dict(font_name=fname, font_size=px, color=col, anchor_x=anchor_x, anchor_y=anchor_y)
            if width:
                lab = pyglet.text.Label(s, x=x, y=y, width=width, multiline=True, align=align, **kw)
            else:
                lab = pyglet.text.Label(s, x=x, y=y, **kw)
            self.labels[k] = lab
        else:
            if key and lab.text != s:
                lab.text = s
            if lab.x != x or lab.y != y:
                lab.position = (x, y, 0)
        self.used.add(k)
        self.queue.append(lab)
        return lab

    def text_width(self, s, size=11, font='body'):
        lab = self.text(s, -9999, -9999, size, font=font)
        self.queue.pop()
        return lab.content_width

    # ------------------------------------------------------------------ input helpers
    def inside(self, x, y, w, h):
        return x <= self.mx <= x + w and y <= self.my <= y + h

    def clicked(self, x, y, w, h, button=1):
        for (cx, cy, b) in self.clicks:
            if x <= cx <= x + w and y <= cy <= y + h and b == button:
                return True
        return False

    def consume_click(self):
        self.clicks = []

    # ------------------------------------------------------------------ widgets
    def panel(self, x, y, w, h, color=PAPER, radius=18.0):
        self.shadow(x, y, w, h, radius * self.s)
        self.rect(x, y, w, h, color, radius * self.s)

    def button(self, x, y, w, h, label, enabled=True, primary=False, size=12, key=None):
        s = self.s
        hover = enabled and self.inside(x, y, w, h)
        if hover:
            self.hovered = key or label
        lift = 2 * s if hover else 0
        if primary:
            base = (0.98, 0.64, 0.54, 1) if enabled else (0.86, 0.80, 0.80, 1)
            top = (1.0, 0.72, 0.60, 1) if hover else base
            tcol = WHITE
        else:
            top = (1.0, 1.0, 1.0, 0.98) if hover else (0.99, 0.97, 0.95, 0.92)
            tcol = INK if enabled else (0.6, 0.58, 0.66, 1)
        self.rect(x, y - 2 * s, w, h, (0.30, 0.24, 0.40, 0.18), h / 2)
        self.rect(x, y + lift, w, h, top, h / 2, border=(1, 1, 1) if not primary else None,
                  border_w=1.2 * s if not primary else 0)
        if hover and not primary:
            self.rect(x, y + lift, w, h, (0, 0, 0, 0), h / 2, border=ACCENT, border_w=2.0 * s)
        self.text(label, x + w / 2, y + h / 2 + lift, size, tcol, 'center', 'center', font='bold')
        if enabled and self.clicked(x, y, w, h):
            if self.sound:
                self.sound('click')
            self.consume_click()
            return True
        return False

    def toggle(self, x, y, w, h, label, value):
        s = self.s
        hover = self.inside(x, y, w, h)
        if hover:
            self.hovered = label
        self.rect(x, y, w, h, (1, 1, 1, 0.96 if hover else 0.86), 12 * s)
        self.text(label, x + 14 * s, y + h / 2, 11, INK, 'left', 'center')
        kw, kh = 40 * s, 22 * s
        kx, ky = x + w - kw - 12 * s, y + (h - kh) / 2
        self.rect(kx, ky, kw, kh, ACCENT if value else (0.82, 0.80, 0.88, 1), kh / 2)
        self.circle(kx + (kw - kh / 2 if value else kh / 2), ky + kh / 2, kh / 2 - 3 * s, WHITE)
        if self.clicked(x, y, w, h):
            if self.sound:
                self.sound('click')
            self.consume_click()
            return not value
        return value

    def slider(self, x, y, w, h, label, value, lo, hi, fmt=None, step=1):
        s = self.s
        key = ('slider', label)
        hover = self.inside(x, y, w, h)
        if hover:
            self.hovered = label
        self.rect(x, y, w, h, (1, 1, 1, 0.96 if hover or self.active == key else 0.86), 12 * s)
        tx0, tx1 = x + w * 0.40, x + w - 84 * s
        ty = y + h / 2
        t = (value - lo) / (hi - lo) if hi > lo else 0
        self.rect(tx0, ty - 3 * s, tx1 - tx0, 6 * s, (0.85, 0.83, 0.91, 1), 3 * s)
        self.rect(tx0, ty - 3 * s, (tx1 - tx0) * t, 6 * s, ACCENT2, 3 * s)
        self.hexagon(tx0 + (tx1 - tx0) * t, ty, 10 * s, WHITE, border=ACCENT2, border_w=2.5 * s)
        shown = fmt(value) if fmt else str(value)
        self.text(f'{label}', x + 14 * s, ty, 11, INK, 'left', 'center')
        self.text(shown, x + w - 14 * s, ty, 10.5, MUTED, 'right', 'center', font='bold')
        if self.clicked(x, y, w, h):
            self.active = key
            self.consume_click()
        if self.active == key:
            if not self.mouse_down:
                self.active = None
            else:
                t = min(1, max(0, (self.mx - tx0) / (tx1 - tx0)))
                v = lo + t * (hi - lo)
                v = round(v / step) * step
                return type(value)(v)
        return value

    def textfield(self, x, y, w, h, key, value, placeholder='', maxlen=40):
        s = self.s
        focused = self.focus == key
        self.rect(x, y, w, h, (1, 1, 1, 1 if focused else 0.9), 12 * s,
                  border=ACCENT if focused else (0.86, 0.84, 0.92), border_w=2 * s)
        if self.clicked(x, y, w, h):
            self.focus = key
            self.consume_click()
        if focused:
            value = (value + self.typed)[:maxlen]
            for k in self.keys:
                if k == 'backspace':
                    value = value[:-1]
        shown = value if value else placeholder
        col = INK if value else (0.62, 0.60, 0.70, 1)
        lab = self.text(shown, x + 14 * s, y + h / 2, 12, col, 'left', 'center')
        if focused and int(time.time() * 2) % 2 == 0:
            cx = x + 14 * s + (lab.content_width if value else 0) + 2
            self.rect(cx, y + h * 0.25, 2 * s, h * 0.5, ACCENT, 1)
        return value

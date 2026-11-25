"""In-game screens for Glimmer stations (waystones and the Font)."""
from .gui import INK, MUTED, ACCENT, WHITE
from .screens import Screen, veil
from .. import glimmer as G
from .. import items as I
from ..hexgrid import center
from ..config import LAYER


class WaystoneScreen(Screen):
    def __init__(self, here_key):
        self.here = here_key
        self.scroll = 0

    def build(self, gui, app, w, h):
        s = gui.s
        ses = app.session
        veil(gui, w, h, 0.35)
        pw, ph = min(640 * s, w - 40 * s), min(480 * s, h - 40 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Waystone', px + 28 * s, py + ph - 36 * s, 22, INK, 'left', 'center', font='title')
        here = ses.waystones.get(self.here, {})
        gui.text(here.get('name', 'This shrine'), px + 28 * s, py + ph - 62 * s, 11, MUTED, 'left', 'center')
        attuned = [(k, v) for k, v in ses.waystones.items() if v.get('attuned') and k != self.here]
        attuned.sort(key=lambda kv: kv[1].get('name', ''))
        y = py + ph - 96 * s
        if not attuned:
            gui.text('No other attuned shrines yet. Find another waystone and spend 1 Glimmer to attune it.',
                     px + 28 * s, y, 12, MUTED, 'left', 'top', width=pw - 56 * s)
        else:
            gui.text('Travel to an attuned shrine.', px + 28 * s, y, 11, MUTED, 'left', 'center')
            y -= 28 * s
            vis = 7
            if gui.scroll:
                self.scroll = max(0, min(max(0, len(attuned) - vis), self.scroll - int(gui.scroll)))
            for k, rec in attuned[self.scroll:self.scroll + vis]:
                if gui.button(px + 28 * s, y - 18 * s, pw - 56 * s, 36 * s, rec.get('name', k), size=12):
                    if ses.travel_to_waystone(k):
                        app.set_screen(None)
                y -= 42 * s
        if gui.button(px + pw / 2 - 80 * s, py + 22 * s, 160 * s, 36 * s, 'Stay', primary=True):
            app.set_screen(None)

    def escape(self, app):
        app.set_screen(None)


class FontScreen(Screen):
    def build(self, gui, app, w, h):
        s = gui.s
        ses = app.session
        veil(gui, w, h, 0.35)
        pw, ph = min(720 * s, w - 40 * s), min(520 * s, h - 40 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Glimmer Font', px + 28 * s, py + ph - 36 * s, 22, INK, 'left', 'center', font='title')
        have = ses.inv.count(I.GLIMMER.id)
        gui.text(f'You have {have} Glimmer. Spend it here for lasting attunements, saved with this sky.',
                 px + 28 * s, py + ph - 64 * s, 11, MUTED, 'left', 'center', width=pw - 56 * s)
        y = py + ph - 100 * s
        for aid, title, cost, desc in G.ATTUNEMENTS:
            have_it = aid in ses.attune
            label = f'{title}  —  attuned' if have_it else f'{title}  —  {cost} Glimmer'
            if have_it:
                gui.text(label, px + 28 * s, y, 13, ACCENT, 'left', 'center', font='bold')
            elif gui.button(px + 28 * s, y - 16 * s, pw - 56 * s, 34 * s, label, enabled=have >= cost, size=12):
                if ses.buy_attunement(aid):
                    app.audio.play('awaken', 0.6)
            gui.text(desc, px + 40 * s, y - 28 * s, 10, MUTED, 'left', 'center', width=pw - 80 * s)
            y -= 64 * s
        if gui.button(px + pw / 2 - 80 * s, py + 22 * s, 160 * s, 36 * s, 'Done', primary=True):
            app.set_screen(None)

    def escape(self, app):
        app.set_screen(None)

class PathScreen(Screen):
    """The Path: a tree of goals that also explains how the sky works."""

    def __init__(self, parent=None):
        self.parent = parent
        self.sel = 'first'
        self.scroll = 0

    def build(self, gui, app, w, h):
        from .. import achievements as A
        s = gui.s
        ses = app.session
        veil(gui, w, h, 0.35)
        pw, ph = min(1040 * s, w - 20 * s), min(660 * s, h - 20 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        have = set(getattr(ses, 'achieved', [])) if ses else set()
        gui.text('The Path', px + 28 * s, py + ph - 36 * s, 22, INK, 'left', 'center', font='title')
        gui.text(f'{len(have)} of {len(A.NODES)} remembered with this sky',
                 px + 210 * s, py + ph - 36 * s, 11, MUTED, 'left', 'center')
        if gui.button(px + pw - 160 * s, py + ph - 54 * s, 128 * s, 36 * s, 'Close', primary=True):
            self.escape(app)

        nw, nh = 176 * s, 48 * s
        gap_x, gap_y = 22 * s, 16 * s
        ox = px + 28 * s
        oy = py + ph - 88 * s + self.scroll
        if gui.scroll:
            self.scroll = max(-480 * s, min(40 * s, self.scroll + int(gui.scroll) * 28 * s))

        pos = {}
        for nid, title, parent, col, row, how, _chk in A.NODES:
            pos[nid] = (ox + col * (nw + gap_x), oy - row * (nh + gap_y))
        for nid, title, parent, col, row, how, _chk in A.NODES:
            if not parent or parent not in pos:
                continue
            x0, y0 = pos[parent]
            x1, y1 = pos[nid]
            sx, sy = x0 + nw, y0 + nh / 2
            ex, ey = x1, y1 + nh / 2
            mx = (sx + ex) / 2
            colr = ACCENT if (parent in have and nid in have) else (0.80, 0.76, 0.84, 1)
            gui.rect(sx, sy - 1.2 * s, max(2 * s, mx - sx), 2.4 * s, colr)
            top, bot = min(sy, ey), max(sy, ey)
            gui.rect(mx - 1.2 * s, top, 2.4 * s, max(2.4 * s, bot - top), colr)
            gui.rect(mx, ey - 1.2 * s, max(2 * s, ex - mx), 2.4 * s, colr)

        for nid, title, parent, col, row, how, _chk in A.NODES:
            x, y = pos[nid]
            on = nid in have
            locked = bool(parent) and parent not in have
            sel = nid == self.sel
            if on:
                bg, ink = ACCENT, WHITE
            elif locked:
                bg, ink = (0.90, 0.88, 0.93, 1), (0.50, 0.46, 0.58, 1)
            else:
                bg, ink = (0.99, 0.97, 0.95, 1), INK
            border = ACCENT if sel else (1, 1, 1)
            if gui.clicked(x, y, nw, nh):
                self.sel = nid
                gui.consume_click()
            gui.rect(x, y, nw, nh, bg, 12 * s, border=border, border_w=(2.6 if sel else 1.1) * s)
            label = (('✓  ' if on else '') + title)
            gui.text(label, x + nw / 2, y + nh / 2, 11, ink, 'center', 'center', font='bold')

        rec = A.BY_ID.get(self.sel, A.NODES[0])
        dy, dh = py + 20 * s, 118 * s
        gui.rect(px + 24 * s, dy, pw - 48 * s, dh, (0.97, 0.95, 0.98, 1), 14 * s)
        if rec[0] in have:
            status = 'Remembered with this sky'
        elif rec[2] and rec[2] not in have:
            status = 'Locked until you finish the step before'
        else:
            status = 'Not yet — here is how'
        gui.text(rec[1], px + 40 * s, dy + dh - 22 * s, 16, INK, 'left', 'center', font='title')
        gui.text(status, px + pw - 64 * s, dy + dh - 22 * s, 10, ACCENT if rec[0] in have else MUTED, 'right', 'center')
        gui.text(rec[5], px + 40 * s, dy + dh - 50 * s, 11, INK, 'left', 'top', width=pw - 96 * s)

    def escape(self, app):
        app.set_screen(self.parent)

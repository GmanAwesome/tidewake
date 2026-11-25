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

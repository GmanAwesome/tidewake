"""Menus: title, your skies, dream a new sky, loading, settings, rest (pause), journal, whisper."""
import math
import random
import time

from .gui import INK, PAPER, ACCENT, ACCENT2, MUTED, WHITE
from .. import materials as MT
from ..materials import ELEMENTS, ELEMENT_COLORS, FORMS, FORM_HINTS
from ..noise import seed_from_text, random_seed
from ..settings import FPS_CHOICES
from ..storage import SkyStorage

SPLASHES = ['The clouds remember everything.', 'Every sky is new.', 'Hexagons all the way down.',
            'Mind the drifting spires.', 'Gather gently.', 'Listen for the hum.', 'No two tides alike.',
            'Waking the old stones since today.', 'Six sides to every story.', 'Soft landings guaranteed.']
WORDS_A = ['amber', 'velvet', 'hollow', 'drowsy', 'silver', 'quiet', 'lumen', 'misty', 'honey', 'tidal', 'frost',
           'rose', 'gentle', 'wandering', 'mossy', 'starlit', 'feather', 'dusky']
WORDS_B = ['moth', 'harbor', 'lantern', 'meadow', 'spire', 'drift', 'comet', 'orchard', 'reef', 'loom', 'hollow',
           'garden', 'kite', 'bell', 'tide', 'cairn', 'willow', 'atoll']


def dream_name():
    return f'{random.choice(WORDS_A)}-{random.choice(WORDS_B)}-{random.randint(1, 999)}'


class Screen:
    pauses = True
    initial_focus = None

    def build(self, gui, app, w, h):
        pass

    def escape(self, app):
        app.set_screen(None)


def title_block(gui, w, h, text, sub=None, y=None):
    s = gui.s
    y = y if y is not None else h - 70 * s
    gui.text(text, w / 2, y, 24, INK, 'center', 'center', font='title')
    if sub:
        gui.text(sub, w / 2, y - 30 * s, 11, MUTED, 'center', 'center')


def veil(gui, w, h, a=0.35):
    gui.rect(0, 0, w, h, (0.20, 0.16, 0.32, a))


# ---------------------------------------------------------------------- title
class TitleScreen(Screen):
    def __init__(self):
        self.splash = random.choice(SPLASHES)

    def build(self, gui, app, w, h):
        s = gui.s
        t = time.time()
        # logo: a gentle bobbing word with a hexagon cluster
        ly = h * 0.70 + math.sin(t * 0.8) * 4 * s
        for i, (dx, dy, c) in enumerate([(-1, 0, ELEMENT_COLORS[0]), (1, 0, ELEMENT_COLORS[1]), (-0.5, 0.866, ELEMENT_COLORS[2]),
                                         (0.5, 0.866, ELEMENT_COLORS[3]), (0, 0, (1, 1, 1))]):
            r = 13 * s
            gui.hexagon(w / 2 + dx * r * 1.8, ly + 64 * s + dy * r * 1.8 + math.sin(t * 1.3 + i) * 2 * s, r,
                        (*c[:3], 0.95), border=(1, 1, 1), border_w=2 * s)
        gui.text('Tidewake', w / 2 + 3 * s, ly - 4 * s, 54, (0.25, 0.18, 0.40, 0.35), 'center', 'center', font='title')
        gui.text('Tidewake', w / 2, ly, 54, WHITE, 'center', 'center', font='title')
        gui.text('a cozy sky of hexagons, tides and sleeping spires', w / 2, ly - 46 * s, 13, (1, 1, 1, 0.92), 'center', 'center')
        gui.flush()
        bw, bh = 250 * s, 42 * s
        x = w / 2 - bw / 2
        y = h * 0.36
        if gui.button(x, y, bw, bh, 'Wander', primary=True, size=14):
            app.set_screen(SkiesScreen(app))
        if gui.button(x, y - 52 * s, bw, bh, 'Settings'):
            app.set_screen(SettingsScreen(self))
        if gui.button(x, y - 104 * s, bw, bh, 'How to play'):
            app.set_screen(JournalScreen(self, tab=0, help_only=True))
        if gui.button(x, y - 156 * s, bw, bh, 'Leave'):
            app.quit()
        gui.text(self.splash, w / 2, 26 * s, 11, (1, 1, 1, 0.85), 'center', 'center')
        gui.text('Tidewake 1.0', 14 * s, 12 * s, 9, (1, 1, 1, 0.7))
        gui.text('Python + ModernGL. Every sound and shape is made by code.', w - 14 * s, 12 * s, 9, (1, 1, 1, 0.7), 'right')

    def escape(self, app):
        pass


# ---------------------------------------------------------------------- skies
class SkiesScreen(Screen):
    def __init__(self, app):
        self.skies = SkyStorage.list_skies(app.skies_dir)
        self.sel = 0 if self.skies else None
        self.scroll = 0
        self.last_click = (None, 0)

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.25)
        pw, ph = min(760 * s, w - 40 * s), min(560 * s, h - 40 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Your Skies', w / 2, py + ph - 36 * s, 22, INK, 'center', 'center', font='title')
        gui.text('Each sky is its own endless archipelago.', w / 2, py + ph - 62 * s, 10, MUTED, 'center', 'center')
        top, bottom = py + ph - 82 * s, py + 76 * s
        row_h = 74 * s
        vis = max(1, int((top - bottom) // row_h))
        if gui.scroll and self.skies:
            self.scroll = max(0, min(len(self.skies) - vis, self.scroll - int(gui.scroll)))
        if not self.skies:
            gui.text('No skies yet. Dream one up!', w / 2, (top + bottom) / 2, 13, MUTED, 'center', 'center')
        rx, rw = px + 24 * s, pw - 48 * s
        for i, sky in enumerate(self.skies[self.scroll:self.scroll + vis]):
            idx = i + self.scroll
            y = top - (i + 1) * row_h + 6 * s
            sel = idx == self.sel
            hover = gui.inside(rx, y, rw, row_h - 8 * s)
            col = (1.0, 0.93, 0.88, 1) if sel else ((1, 1, 1, 1) if hover else (0.97, 0.95, 0.97, 1))
            gui.rect(rx, y, rw, row_h - 8 * s, col, 14 * s, border=ACCENT if sel else None, border_w=2 * s if sel else 0)
            th = row_h - 20 * s
            tw = th * 16 / 9
            img = app.thumb(sky['folder'])
            if img is not None:
                gui.image(('thumb', sky['folder']), img, rx + 6 * s, y + 6 * s, tw, th)
            else:
                gui.rect(rx + 6 * s, y + 6 * s, tw, th, (0.80, 0.84, 0.96, 1), 10 * s)
                gui.hexagon(rx + 6 * s + tw / 2, y + 6 * s + th / 2, th * 0.3, (1, 1, 1, 0.9))
            tx = rx + tw + 20 * s
            gui.text(sky['name'], tx, y + row_h * 0.58, 13, INK, font='bold')
            mins = int(sky['play_time'] // 60)
            when = time.strftime('%b %d, %H:%M', time.localtime(sky['last_played']))
            info = f"{'Dreamer' if sky['mode'] == 'dreamer' else 'Wanderer'}  ·  {sky['awakened']} spires awake  ·  {mins} min  ·  {when}"
            gui.text(info, tx, y + row_h * 0.26, 9, MUTED)
            if gui.clicked(rx, y, rw, row_h - 8 * s):
                gui.consume_click()
                now = time.time()
                if self.last_click[0] == idx and now - self.last_click[1] < 0.4:
                    app.open_sky(sky['folder'])
                    return
                self.sel = idx
                self.last_click = (idx, now)
        bw, bh = (pw - 48 * s - 4 * 10 * s) / 5, 38 * s
        bx, by = px + 24 * s, py + 24 * s
        has = self.sel is not None
        if gui.button(bx, by, bw, bh, 'Enter', enabled=has, primary=True):
            app.open_sky(self.skies[self.sel]['folder'])
            return
        if gui.button(bx + (bw + 10 * s), by, bw, bh, 'New Sky'):
            app.set_screen(NewSkyScreen(self))
        if gui.button(bx + 2 * (bw + 10 * s), by, bw, bh, 'Rename', enabled=has):
            app.set_screen(RenameScreen(self, self.skies[self.sel]))
        if gui.button(bx + 3 * (bw + 10 * s), by, bw, bh, 'Let go', enabled=has):
            app.set_screen(ConfirmScreen(self, self.skies[self.sel]))
        if gui.button(bx + 4 * (bw + 10 * s), by, bw, bh, 'Back'):
            app.set_screen(TitleScreen())
        if 'enter' in gui.keys and has:
            app.open_sky(self.skies[self.sel]['folder'])

    def escape(self, app):
        app.set_screen(TitleScreen())


class NewSkyScreen(Screen):
    initial_focus = 'name'

    def __init__(self, parent):
        self.parent = parent
        self.name = 'My Sky'
        self.seed = ''
        self.mode = 'wanderer'

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.25)
        pw, ph = min(560 * s, w - 40 * s), min(520 * s, h - 30 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Dream a New Sky', w / 2, py + ph - 38 * s, 22, INK, 'center', 'center', font='title')
        fx, fw, fh = px + 36 * s, pw - 72 * s, 40 * s
        y = py + ph - 110 * s
        gui.text('Name', fx, y + fh + 8 * s, 10, MUTED, font='bold')
        self.name = gui.textfield(fx, y, fw, fh, 'name', self.name, 'My Sky', 36)
        y -= 82 * s
        gui.text('Seed: a word, a number, or empty for a surprise', fx, y + fh + 8 * s, 10, MUTED, font='bold')
        self.seed = gui.textfield(fx, y, fw - 130 * s, fh, 'seed', self.seed, 'surprise me', 40)
        if gui.button(fx + fw - 120 * s, y, 120 * s, fh, 'Roll'):
            self.seed = dream_name()
        y -= 70 * s
        gui.text('Way of play', fx, y + 46 * s, 10, MUTED, font='bold')
        cw = (fw - 12 * s) / 2
        for i, (mode, label, desc) in enumerate([('wanderer', 'Wanderer', 'gather essence, wake spires, earn gifts'),
                                                  ('dreamer', 'Dreamer', 'endless essence, free drifting, all gifts')]):
            cx = fx + i * (cw + 12 * s)
            on = self.mode == mode
            gui.rect(cx, y - 30 * s, cw, 68 * s, (1, 0.93, 0.88, 1) if on else (0.97, 0.95, 0.98, 1), 14 * s,
                     border=ACCENT if on else (0.88, 0.86, 0.93), border_w=2 * s)
            gui.text(label, cx + cw / 2, y + 16 * s, 13, INK, 'center', 'center', font='bold')
            gui.text(desc, cx + cw / 2, y - 8 * s, 8.5, MUTED, 'center', 'center')
            if gui.clicked(cx, y - 30 * s, cw, 68 * s):
                gui.consume_click()
                self.mode = mode
                if gui.sound:
                    gui.sound('click')
        bw = (fw - 12 * s) / 2
        if gui.button(fx, py + 26 * s, bw, 42 * s, 'Dream it', primary=True, size=13) or 'enter' in gui.keys:
            text = self.seed.strip()
            seed = seed_from_text(text) if text else random_seed()
            app.create_sky(self.name.strip() or 'My Sky', seed, text, self.mode)
            return
        if gui.button(fx + bw + 12 * s, py + 26 * s, bw, 42 * s, 'Back'):
            app.set_screen(self.parent)
        if 'tab' in gui.keys:
            gui.focus = 'seed' if gui.focus == 'name' else 'name'

    def escape(self, app):
        app.set_screen(self.parent)


class RenameScreen(Screen):
    initial_focus = 'rename'

    def __init__(self, parent, sky):
        self.parent, self.sky = parent, sky
        self.name = sky['name']

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.3)
        pw, ph = 480 * s, 220 * s
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Rename Sky', w / 2, py + ph - 36 * s, 18, INK, 'center', 'center', font='title')
        self.name = gui.textfield(px + 30 * s, py + 90 * s, pw - 60 * s, 40 * s, 'rename', self.name, '', 36)
        bw = (pw - 72 * s) / 2
        if gui.button(px + 30 * s, py + 26 * s, bw, 40 * s, 'Save', primary=True) or 'enter' in gui.keys:
            SkyStorage(app.skies_dir, self.sky['folder']).rename(self.name)
            app.set_screen(SkiesScreen(app))
            return
        if gui.button(px + 42 * s + bw, py + 26 * s, bw, 40 * s, 'Cancel'):
            app.set_screen(self.parent)

    def escape(self, app):
        app.set_screen(self.parent)


class ConfirmScreen(Screen):
    def __init__(self, parent, sky):
        self.parent, self.sky = parent, sky

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.35)
        pw, ph = 500 * s, 210 * s
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text(f'Let go of "{self.sky["name"]}"?', w / 2, py + ph - 44 * s, 16, INK, 'center', 'center', font='title')
        gui.text('This sky and everything you shaped in it will drift away for good.', w / 2, py + ph - 84 * s, 10,
                 MUTED, 'center', 'center')
        bw = (pw - 72 * s) / 2
        if gui.button(px + 30 * s, py + 28 * s, bw, 40 * s, 'Let it go', primary=True):
            app.drop_thumb(self.sky['folder'])
            SkyStorage(app.skies_dir, self.sky['folder']).delete()
            app.set_screen(SkiesScreen(app))
            return
        if gui.button(px + 42 * s + bw, py + 28 * s, bw, 40 * s, 'Keep it'):
            app.set_screen(self.parent)

    def escape(self, app):
        app.set_screen(self.parent)


# ---------------------------------------------------------------------- loading
class LoadingScreen(Screen):
    pauses = False

    def __init__(self, title):
        self.title = title
        self.progress = 0.0
        self.line = random.choice(['Gathering clouds', 'Waking the wind', 'Sorting hexagons', 'Tuning the tides',
                                   'Polishing crystals'])

    def build(self, gui, app, w, h):
        s = gui.s
        gui.rect(0, 0, w, h, (0.95, 0.88, 0.86, 1))
        gui.rect(0, 0, w, h * 0.5, (0.84, 0.82, 0.95, 0.6))
        t = time.time()
        for i in range(7):
            a = i / 7 * math.tau + t * 1.4
            on = i / 7 < self.progress
            gui.hexagon(w / 2 + math.cos(a) * 46 * s, h * 0.55 + math.sin(a) * 46 * s, 12 * s,
                        (*ELEMENT_COLORS[i % 4], 1.0 if on else 0.35), border=(1, 1, 1), border_w=2 * s)
        gui.text(self.title, w / 2, h * 0.36, 20, INK, 'center', 'center', font='title')
        gui.text(f'{self.line}...  {int(self.progress * 100)}%', w / 2, h * 0.36 - 34 * s, 11, MUTED, 'center', 'center')

    def escape(self, app):
        pass


# ---------------------------------------------------------------------- settings
class SettingsScreen(Screen):
    def __init__(self, parent):
        self.parent = parent

    def build(self, gui, app, w, h):
        s = gui.s
        st = app.settings
        veil(gui, w, h, 0.3)
        pw, ph = min(860 * s, w - 30 * s), min(470 * s, h - 30 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Settings', w / 2, py + ph - 38 * s, 22, INK, 'center', 'center', font='title')
        cw = (pw - 3 * 26 * s) / 2
        rh, gap = 40 * s, 10 * s
        x1, x2 = px + 26 * s, px + 52 * s + cw
        y = py + ph - 106 * s
        old = dict(st)
        st['view_distance'] = gui.slider(x1, y, cw, rh, 'View distance', st['view_distance'], 2, 12, lambda v: f'{v} chunks')
        st['fov'] = gui.slider(x2, y, cw, rh, 'Field of view', st['fov'], 50, 110, lambda v: f'{v}°')
        y -= rh + gap
        st['sensitivity'] = gui.slider(x1, y, cw, rh, 'Look speed', st['sensitivity'], 20, 300, lambda v: f'{v}%', 5)
        st['invert_y'] = gui.toggle(x2, y, cw, rh, 'Invert look', st['invert_y'])
        y -= rh + gap
        st['music'] = gui.slider(x1, y, cw, rh, 'Music', st['music'], 0, 100, lambda v: f'{v}%', 5)
        st['sounds'] = gui.slider(x2, y, cw, rh, 'Sounds', st['sounds'], 0, 100, lambda v: f'{v}%', 5)
        y -= rh + gap
        st['ui_scale'] = gui.slider(x1, y, cw, rh, 'Interface size', st['ui_scale'], 0, 4,
                                    lambda v: 'auto' if v == 0 else ['', 'small', 'medium', 'large', 'huge'][v])
        fi = FPS_CHOICES.index(st['fps_limit']) if st['fps_limit'] in FPS_CHOICES else 1
        fi = gui.slider(x2, y, cw, rh, 'Frame limit', fi, 0, len(FPS_CHOICES) - 1,
                        lambda v: 'none' if FPS_CHOICES[v] == 0 else f'{FPS_CHOICES[v]} fps')
        st['fps_limit'] = FPS_CHOICES[fi]
        y -= rh + gap
        st['fullscreen'] = gui.toggle(x1, y, cw, rh, 'Fullscreen', st['fullscreen'])
        st['vsync'] = gui.toggle(x2, y, cw, rh, 'VSync', st['vsync'])
        y -= rh + gap
        st['clouds'] = gui.toggle(x1, y, cw, rh, 'Cloud sea', st['clouds'])
        st['head_bob'] = gui.toggle(x2, y, cw, rh, 'Gentle head bob', st['head_bob'])
        y -= rh + gap
        st['motes'] = gui.toggle(x1, y, cw, rh, 'Floating motes', st['motes'])
        if dict(st) != old:
            app.apply_settings(old)
        if gui.button(w / 2 - 110 * s, py + 22 * s, 220 * s, 40 * s, 'Done', primary=True):
            self.escape(app)

    def escape(self, app):
        app.settings.save()
        app.set_screen(self.parent)


# ---------------------------------------------------------------------- in game
class RestScreen(Screen):
    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.35)
        ses = app.session
        gui.text('Resting', w / 2, h * 0.74, 30, WHITE, 'center', 'center', font='title')
        gui.text(f'{ses.name}  ·  {len(ses.awakened)} spires awake  ·  {int(ses.play_time // 60)} min wandered',
                 w / 2, h * 0.74 - 40 * s, 11, (1, 1, 1, 0.9), 'center', 'center')
        gui.flush()
        bw, bh = 260 * s, 42 * s
        x, y = w / 2 - bw / 2, h * 0.52
        if gui.button(x, y, bw, bh, 'Back to the sky', primary=True):
            app.set_screen(None)
        if gui.button(x, y - 52 * s, bw, bh, 'Journal'):
            app.set_screen(JournalScreen(self))
        if gui.button(x, y - 104 * s, bw, bh, 'Settings'):
            app.set_screen(SettingsScreen(self))
        if gui.button(x, y - 156 * s, bw, bh, 'Save and leave'):
            app.quit_to_title()


class JournalScreen(Screen):
    TABS = ['Tuning', 'Spires', 'Gifts', 'Controls']

    def __init__(self, parent=None, tab=0, help_only=False):
        self.parent = parent
        self.tab = tab
        self.help_only = help_only

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.35)
        pw, ph = min(860 * s, w - 30 * s), min(580 * s, h - 30 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Journal', px + 30 * s, py + ph - 42 * s, 22, INK, 'left', 'center', font='title')
        tw = 108 * s
        for i, name in enumerate(self.TABS):
            tx = px + pw - 30 * s - (len(self.TABS) - i) * (tw + 8 * s)
            on = i == self.tab
            if on:
                gui.rect(tx, py + ph - 60 * s, tw, 36 * s, ACCENT, 18 * s)
                gui.text(name, tx + tw / 2, py + ph - 42 * s, 11, WHITE, 'center', 'center', font='bold')
            elif gui.button(tx, py + ph - 60 * s, tw, 36 * s, name, size=11, key='tab' + name):
                self.tab = i
        ses = app.session if not self.help_only else None
        x0, y0 = px + 34 * s, py + ph - 100 * s
        if self.tab == 0:
            gui.text('Nothing here is mined or crafted. Gather a cell to draw out its elements, then tune a chord of one '
                     'or two elements (keys 1-4, or the mouse wheel) and shape it into the world.', x0, y0, 10.5, MUTED,
                     width=pw - 68 * s, anchor_y='top')
            y = y0 - 56 * s
            col_w = (pw - 68 * s) / 2
            for i, (chord, mat) in enumerate(FORMS.items()):
                cx = x0 + (i % 2) * col_w
                cy = y - (i // 2) * 54 * s
                for k, e in enumerate(chord):
                    gui.hexagon(cx + 14 * s + k * 26 * s, cy, 12 * s, ELEMENT_COLORS[e], border=(1, 1, 1), border_w=2 * s)
                ex = cx + 14 * s + len(chord) * 26 * s + 8 * s
                gui.text('→', ex, cy, 12, MUTED, 'left', 'center', font='title')
                gui.hexagon(ex + 30 * s, cy, 14 * s, (*MT.TOP[mat], 1), border=(1, 1, 1), border_w=2 * s)
                gui.text(MT.NAMES[mat], ex + 52 * s, cy + 7 * s, 12, INK, 'left', 'center', font='bold')
                gui.text(FORM_HINTS[mat], ex + 52 * s, cy - 10 * s, 9, MUTED, 'left', 'center')
        elif self.tab == 1:
            lines = ['Dormant spires stand on old plinths across every sky. Each one longs for certain tuned cells.',
                     'Shape those cells on the ring of six hexes right around its base, and it will wake.',
                     'Each awakening fills you with light and teaches you a gift. The wayfinder at the top of the '
                     'screen points to the nearest sleeping spire.']
            gui.text('\n\n'.join(lines), x0, y0, 11, INK, width=pw - 68 * s, anchor_y='top')
            if ses:
                gui.text(f'Spires awake in this sky: {len(ses.awakened)}', x0, y0 - 170 * s, 14, INK, font='bold')
                ns = ses.nearest_spire
                if ns:
                    sp, d = ns
                    _, missing = ses.spire_state(sp) if d < 120 else (None, sp['wants'])
                    want = ', '.join(MT.NAMES[m] for m in sp['wants'])
                    gui.text(f'The nearest sleeping spire ({d:.0f} m away) longs for: {want}', x0, y0 - 204 * s, 11, MUTED)
                    for k, m in enumerate(sp['wants']):
                        gui.hexagon(x0 + 16 * s + k * 34 * s, y0 - 240 * s, 14 * s, (*MT.TOP[m], 1), border=(1, 1, 1),
                                    border_w=2 * s)
        elif self.tab == 2:
            from ..session import ABILITIES
            n = len(ses.awakened) if ses else 0
            dreamer = ses and ses.mode == 'dreamer'
            for i, (name, desc) in enumerate(ABILITIES):
                y = y0 - i * 76 * s
                got = dreamer or n > i
                gui.rect(x0, y - 56 * s, pw - 68 * s, 64 * s, (1, 0.95, 0.90, 1) if got else (0.95, 0.94, 0.97, 1), 14 * s)
                gui.hexagon(x0 + 34 * s, y - 24 * s, 20 * s, ACCENT2 if got else (0.8, 0.79, 0.86, 1))
                gui.text(name if got else f'{name}  (wake {i + 1} spire{"s" if i else ""})', x0 + 70 * s, y - 14 * s, 13,
                         INK if got else MUTED, font='bold')
                gui.text(desc, x0 + 70 * s, y - 38 * s, 10, MUTED)
            gui.text('Dusk motes: walk through the golden motes of the dusk tide to gather Light.', x0, y0 - 250 * s, 10.5, INK)
            gui.text('Falling: the cloud sea always carries you back to the last solid ground.', x0, y0 - 276 * s, 10.5, INK)
        else:
            rows = [('W A S D / mouse', 'wander and look'), ('Space', 'jump · hold to glide · climb vines'),
                    ('Shift', 'hurry'), ('Left click', 'gather a cell into essence'),
                    ('Right click', 'shape your tuned form'), ('1  2  3  4', 'toggle Stone, Water, Light, Growth'),
                    ('Mouse wheel', 'cycle through forms'), ('J or Tab', 'journal'), ('T', 'tidecall (once learned)'),
                    ('F', 'drift freely (Dreamer skies)'), ('Enter or /', 'whisper a command (/tp x z, /tide dusk)'),
                    ('F1 · F2 · F3', 'hide HUD · snapshot · details'), ('Esc', 'rest')]
            for i, (k, d) in enumerate(rows):
                col, row = i % 2, i // 2
                cx = x0 + col * (pw - 68 * s) / 2
                cy = y0 - row * 46 * s
                kw = gui.text_width(k, 10, 'bold') + 20 * s
                gui.rect(cx, cy - 26 * s, kw, 28 * s, (0.95, 0.93, 0.98, 1), 9 * s)
                gui.text(k, cx + kw / 2, cy - 12 * s, 10, INK, 'center', 'center', font='bold')
                gui.text(d, cx + kw + 12 * s, cy - 12 * s, 10, MUTED, 'left', 'center')
        if gui.button(px + pw - 170 * s, py + 22 * s, 140 * s, 38 * s, 'Close', primary=True):
            self.escape(app)

    def escape(self, app):
        app.set_screen(self.parent if self.help_only else None)


class WhisperScreen(Screen):
    initial_focus = 'cmd'
    pauses = False

    def __init__(self, text=''):
        self.text = text

    def build(self, gui, app, w, h):
        s = gui.s
        gui.text('Whisper to the sky (try /tp 100000 0, /tide dusk, /spire, /seed)', 20 * s, 72 * s, 10, WHITE)
        self.text = gui.textfield(16 * s, 20 * s, w - 32 * s, 40 * s, 'cmd', self.text, '/', 80)
        if 'enter' in gui.keys:
            if app.session and self.text.strip():
                app.session.command(self.text)
            app.set_screen(None)

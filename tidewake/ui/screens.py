"""Menus: title, your skies, dream a new sky, loading, settings, rest (pause), journal, whisper."""
import math
import random
import time

from .gui import INK, PAPER, ACCENT, ACCENT2, MUTED, WHITE
from .. import materials as MT
from .. import items as I
ELEMENT_COLORS = [(0.80, 0.72, 0.62), (0.42, 0.70, 0.95), (1.00, 0.84, 0.45), (0.52, 0.82, 0.48)]
from ..noise import seed_from_text, random_seed
from ..settings import FPS_CHOICES
from ..storage import SkyStorage
from .. import gensettings as GS

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

def draw_logo(gui, cx, cy, t, s, word='Tidewake', size=64):
    """Animated wordmark: a pulsing crest, expanding wake rings, and letters that breathe."""
    # wake rings that swell and fade, like a tide spreading through hexes
    for k in range(3):
        phase = (t * 0.28 + k / 3.0) % 1.0
        rad = (22 + 70 * phase) * s
        a = max(0.0, 0.5 * (1.0 - phase) ** 1.2)
        gui.hexagon(cx, cy + 10 * s, rad, (1, 1, 1, 0), border=(0.98, 0.90, 0.72, a), border_w=2.2 * s)
    # crest: six hexes around a bright core, each bobbing on its own tide
    for i, (dx, dy, c) in enumerate([(-1, 0, ELEMENT_COLORS[0]), (1, 0, ELEMENT_COLORS[1]),
                                     (-0.5, 0.866, ELEMENT_COLORS[2]), (0.5, 0.866, ELEMENT_COLORS[3]),
                                     (-0.5, -0.866, ELEMENT_COLORS[0]), (0.5, -0.866, ELEMENT_COLORS[1])]):
        r = 11 * s
        pulse = 1.0 + 0.08 * math.sin(t * 1.6 + i * 0.9)
        gui.hexagon(cx + dx * r * 1.85, cy + 58 * s + dy * r * 1.85 + math.sin(t * 1.25 + i) * 2.4 * s,
                    r * pulse, (*c[:3], 0.96), border=(1, 1, 1), border_w=1.8 * s)
    gui.hexagon(cx, cy + 58 * s, 12 * s * (1.0 + 0.06 * math.sin(t * 2.0)), (1, 1, 1, 0.95),
                border=(0.98, 0.88, 0.70), border_w=2.2 * s)
    # wordmark, one letter at a time so the name itself moves
    widths = [gui.text_width(ch, size, font='title') for ch in word]
    gap = 1.5 * s
    total = sum(widths) + gap * (len(word) - 1)
    x = cx - total / 2
    for i, ch in enumerate(word):
        bob = math.sin(t * 1.7 + i * 0.45) * 3.2 * s
        gui.text(ch, x + 2.5 * s, cy - 6 * s + bob, size, (0.18, 0.12, 0.32, 0.40), font='title')
        gui.text(ch, x, cy - 2 * s + bob, size, WHITE, font='title')
        x += widths[i] + gap
    # a thin gold tide-line under the name
    lw = total * (0.72 + 0.08 * math.sin(t * 1.1))
    gui.rect(cx - lw / 2, cy - 36 * s, lw, 2.2 * s, (0.98, 0.86, 0.62, 0.85), 2 * s)


class TitleScreen(Screen):
    def __init__(self):
        self.splash = random.choice(SPLASHES)

    def build(self, gui, app, w, h):
        s = gui.s
        t = time.time()
        ly = h * 0.68
        draw_logo(gui, w / 2, ly, t, s)
        gui.text('a cozy sky of hexagons, tides and sleeping spires',
                 w / 2, ly - 58 * s, 13, (1, 1, 1, 0.88), 'center', 'center', font='body')
        gui.flush()
        bw, bh = 268 * s, 44 * s
        x = w / 2 - bw / 2
        y = h * 0.34
        gap = 54 * s
        if gui.button(x, y, bw, bh, 'Wander', primary=True, size=15):
            app.set_screen(SkiesScreen(app))
        if gui.button(x, y - gap, bw, bh, 'Learn to play', size=14):
            app.start_tutorial()
        if gui.button(x, y - 2 * gap, bw, bh, 'Settings', size=14):
            app.set_screen(SettingsScreen(self))
        if gui.button(x, y - 3 * gap, bw, bh, 'How to play', size=14):
            app.set_screen(JournalScreen(self, tab=0, help_only=True))
        if gui.button(x, y - 4 * gap, bw, bh, 'Leave', size=14):
            app.quit()
        gui.text(self.splash, w / 2, 30 * s, 12, (1, 1, 1, 0.86), 'center', 'center', font='body')
        gui.text('Tidewake 1.4.6', 16 * s, 14 * s, 10, (1, 1, 1, 0.72), font='bold')
        gui.text('Python + ModernGL. Every sound and shape is made by code.',
                 w - 16 * s, 14 * s, 10, (1, 1, 1, 0.72), 'right', font='body')
        sc = app.backdrop.get('showcase') if app.backdrop else None
        if sc is not None:
            label = ('A sky from the new generator  ·  ' if getattr(sc, 'kind', '') == 'seed'
                     else 'Built in Tidewake  ·  ')
            gui.text(label + sc.name, w - 14 * s, 28 * s, 10, (1, 1, 1, 0.85), 'right')

    def escape(self, app):
        pass


# ---------------------------------------------------------------------- skies
class SkiesScreen(Screen):
    def __init__(self, app):
        # the lesson island has its own button; My Skies lists only skies the player made
        self.skies = [w for w in SkyStorage.list_skies(app.skies_dir) if not w.get('tutorial')]
        self.sel = 0 if self.skies else None
        self.scroll = 0
        self.last_click = (None, 0)

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.25)
        pw, ph = min(760 * s, w - 40 * s), min(560 * s, h - 40 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Your Skies', w / 2, py + ph - 38 * s, 26, INK, 'center', 'center', font='title')
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
        self.gen = GS.defaults()
        self._hint = ''

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.25)
        pw, ph = min(1080 * s, w - 24 * s), min(680 * s, h - 20 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Dream a New Sky', px + 28 * s, py + ph - 30 * s, 26, INK, 'left', 'center', font='title')
        if gui.button(px + pw - 148 * s, py + ph - 46 * s, 120 * s, 32 * s, 'Reset', size=11):
            self.gen = GS.defaults()
            if gui.sound:
                gui.sound('click')
        # name, seed, way of play on one compact row
        fx, y = px + 28 * s, py + ph - 100 * s
        nw, sw = pw * 0.28, pw * 0.28
        gui.text('Name', fx, y + 28 * s, 9, MUTED, font='bold')
        self.name = gui.textfield(fx, y - 16 * s, nw, 36 * s, 'name', self.name, 'My Sky', 36)
        sx = fx + nw + 16 * s
        gui.text('Seed (or empty for a surprise)', sx, y + 28 * s, 9, MUTED, font='bold')
        self.seed = gui.textfield(sx, y - 16 * s, sw - 86 * s, 36 * s, 'seed', self.seed, 'surprise me', 40)
        if gui.button(sx + sw - 80 * s, y - 16 * s, 80 * s, 36 * s, 'Roll', size=11):
            self.seed = dream_name()
        mx = fx + nw + sw + 32 * s
        mw = px + pw - 28 * s - mx
        gui.text('Way of play', mx, y + 28 * s, 9, MUTED, font='bold')
        for i, (mode, label) in enumerate([('wanderer', 'Wanderer'), ('dreamer', 'Dreamer')]):
            cx = mx + i * (mw / 2 + 6 * s)
            cw = mw / 2 - 6 * s
            on = self.mode == mode
            gui.rect(cx, y - 16 * s, cw, 36 * s, (1, 0.93, 0.88, 1) if on else (0.97, 0.95, 0.98, 1), 10 * s,
                     border=ACCENT if on else (0.88, 0.86, 0.93), border_w=2 * s)
            gui.text(label, cx + cw / 2, y + 2 * s, 11, INK, 'center', 'center', font='bold')
            if gui.clicked(cx, y - 16 * s, cw, 36 * s):
                gui.consume_click()
                self.mode = mode
                if gui.sound:
                    gui.sound('click')
        # twelve sliders, two columns
        gui.text('World shape', fx, y - 42 * s, 11, INK, font='bold')
        sh = 34 * s
        gap = 8 * s
        col_w = (pw - 56 * s - 16 * s) / 2
        top = y - 58 * s
        self._hint = self._hint or 'These sliders are saved with the sky. 50 is the usual mid setting.'
        for i, (key, label, hint, lo, hi) in enumerate(GS.SLIDERS):
            col, row = i % 2, i // 2
            x = fx + col * (col_w + 16 * s)
            sy = top - row * (sh + gap)
            before = self.gen[key]
            self.gen[key] = int(gui.slider(x, sy - sh, col_w, sh, label, self.gen[key], 0, 100, fmt=lambda v, lo=lo, hi=hi: f'{int(v)}  {lo}–{hi}', step=1))
            # show this slider's hint when the handle is being dragged or hovered
            if gui.hovered == label or gui.active == ('slider', label):
                self._hint = hint
        gui.text(self._hint, fx, py + 86 * s, 10, MUTED, width=pw - 56 * s)
        bw = (pw - 56 * s - 12 * s) / 2
        if gui.button(fx, py + 26 * s, bw, 42 * s, 'Dream it', primary=True, size=13) or 'enter' in gui.keys:
            text = self.seed.strip()
            seed = seed_from_text(text) if text else random_seed()
            app.create_sky(self.name.strip() or 'My Sky', seed, text, self.mode, gen=self.gen)
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
        self.error = None        # (message, log path) when world generation keeps failing

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
        if self.error:
            msg, path = self.error
            gui.text('This sky could not be built.', w / 2, h * 0.36 - 34 * s, 13, (0.70, 0.20, 0.24, 1), 'center', 'center')
            gui.text(msg, w / 2, h * 0.36 - 58 * s, 10, MUTED, 'center', 'center')
            if path:
                gui.text(f'Details: {path}', w / 2, h * 0.36 - 78 * s, 9, MUTED, 'center', 'center')
            gui.text('Press Esc to go back to the title.', w / 2, h * 0.36 - 100 * s, 10, INK, 'center', 'center')
            return
        gui.text(f'{self.line}...  {int(self.progress * 100)}%', w / 2, h * 0.36 - 34 * s, 11, MUTED, 'center', 'center')

    def escape(self, app):
        if self.error:
            app.quit_to_title()


# ---------------------------------------------------------------------- settings
class SettingsScreen(Screen):
    def __init__(self, parent):
        self.parent = parent

    def build(self, gui, app, w, h):
        s = gui.s
        st = app.settings
        veil(gui, w, h, 0.3)
        pw, ph = min(860 * s, w - 30 * s), min(520 * s, h - 30 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Settings', w / 2, py + ph - 40 * s, 26, INK, 'center', 'center', font='title')
        cw = (pw - 3 * 26 * s) / 2
        rh, gap = 40 * s, 10 * s
        x1, x2 = px + 26 * s, px + 52 * s + cw
        y = py + ph - 106 * s
        old = dict(st)
        st['view_distance'] = gui.slider(x1, y, cw, rh, 'Detail distance', st['view_distance'], 3, 20, lambda v: f'{v} chunks')
        st['far_distance'] = gui.slider(x2, y, cw, rh, 'Far distance', max(st['far_distance'], st['view_distance']), 3, 35,
                                        lambda v: f'{v} chunks' if v > st['view_distance'] else 'off')
        if st['far_distance'] < st['view_distance']:
            st['far_distance'] = st['view_distance']
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
        st['creatures'] = gui.toggle(x2, y, cw, rh, 'Friendly creatures', st['creatures'])
        y -= rh + gap
        st['dusk_critters'] = gui.toggle(x1, y, cw, rh, 'Gloomlings at dusk', st['dusk_critters'])
        st['fov'] = gui.slider(x2, y, cw, rh, 'Field of view', st['fov'], 50, 110, lambda v: f'{v}°')
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
        gui.text('Resting', w / 2, h * 0.74, 34, WHITE, 'center', 'center', font='title')
        gui.text(f'{ses.name}  ·  {len(ses.awakened)} spires awake  ·  {int(ses.play_time // 60)} min wandered',
                 w / 2, h * 0.74 - 40 * s, 11, (1, 1, 1, 0.9), 'center', 'center')
        gui.flush()
        bw, bh = 260 * s, 42 * s
        x, y = w / 2 - bw / 2, h * 0.52
        if gui.button(x, y, bw, bh, 'Back to the sky', primary=True):
            app.set_screen(None)
        if gui.button(x, y - 52 * s, bw, bh, 'Journal'):
            app.set_screen(JournalScreen(self))
        if gui.button(x, y - 104 * s, bw, bh, 'The Path'):
            from .systems import PathScreen
            app.set_screen(PathScreen(self))
        if gui.button(x, y - 156 * s, bw, bh, 'Settings'):
            app.set_screen(SettingsScreen(self))
        if gui.button(x, y - 208 * s, bw, bh, 'Save and leave'):
            app.quit_to_title()


class JournalScreen(Screen):
    TABS = ['Basics', 'Crafting', 'Creatures', 'Spires', 'Controls']

    def __init__(self, parent=None, tab=0, help_only=False):
        self.parent = parent
        self.tab = tab
        self.help_only = help_only
        self.scroll = 0

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.35)
        pw, ph = min(920 * s, w - 30 * s), min(600 * s, h - 30 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Journal', px + 30 * s, py + ph - 44 * s, 26, INK, 'left', 'center', font='title')
        tw = 104 * s
        for i, name in enumerate(self.TABS):
            tx = px + pw - 30 * s - (len(self.TABS) - i) * (tw + 8 * s)
            on = i == self.tab
            if on:
                gui.rect(tx, py + ph - 60 * s, tw, 36 * s, ACCENT, 18 * s)
                gui.text(name, tx + tw / 2, py + ph - 42 * s, 11, WHITE, 'center', 'center', font='bold')
            elif gui.button(tx, py + ph - 60 * s, tw, 36 * s, name, size=11, key='tab' + name):
                self.tab = i
                self.scroll = 0
        ses = app.session if not self.help_only else None
        x0, y0 = px + 34 * s, py + ph - 96 * s
        tw_ = pw - 68 * s
        if self.tab == 0:
            lines = [
                ('Mine', 'Hold left click on a cell. Wood comes off by hand; stone needs a pick. Better picks dig faster and '
                         'can collect rarer ores: Emberite and Verdigris, then Silverine, then glowing Aetherite deep inside the islands.'),
                ('Build', 'Pick a hotbar slot with 1-9 or the mouse wheel, then right click to place it.'),
                ('Craft', 'Press E. Turn Heartwood into Planks, Planks into Sticks and a Tinker Bench. Right click a placed bench '
                          'for the full 3x3 grid. Click a recipe in the book to fill the grid for you.'),
                ('Smelt', 'A Kiln (8 stone in a ring) turns ores into ingots, sand into glass, clay into bricks, and cooks hopmeat. '
                          'Feed it Emberite, wood or sticks.'),
                ('Eat and rest', 'Hearts come back when you are well fed. Eat berries, eggs, roast hopmeat or pie (right click). '
                                 'Right click a Bedroll to set your waking spot and sleep through the dusk.'),
                ('Tides', 'The sky turns between Lighttide and Dusktide. In the dusk, gloomlings creep out (you can switch them '
                          'off in Settings) and golden motes drift by: catch them for Glimmer.'),
                ('Never lost', 'Fall into the clouds and they carry you back. If your hearts run out you wake at your bedroll '
                               'with everything you carried.'),
            ]
            y = y0
            for head, body in lines:
                gui.text(head, x0, y, 12, INK, font='bold', anchor_y='top')
                lab = gui.text(body, x0 + 130 * s, y, 10, MUTED, width=tw_ - 130 * s, anchor_y='top')
                y -= max(26 * s, lab.content_height + 12 * s)
        elif self.tab == 1:
            self._recipes(gui, app, x0, y0, tw_, py + 80 * s)
        elif self.tab == 2:
            rows = [('woolhop', 'Woolhop', 'Fluffy and calm. Drops Fluff (bedrolls, fluff blocks, cloudstuff) and hopmeat.'),
                    ('pebblebeak', 'Pebblebeak', 'A round little bird. Drops Plumes and lays Speckled Eggs.'),
                    ('mossback', 'Mossback', 'A slow, mossy tortoise. Drops Mossrock and Vines.'),
                    ('skywhale', 'Skywhale', 'A huge, peaceful drifter between the islands. Slow, quiet, and happy just to pass by.'),
                    ('fairy', 'Fairy', 'A tiny glow that lingers near flowers, especially as dusk comes on. Harmless, and it lights the grass.'),
                    ('gloomling', 'Gloomling', 'Comes out in the dusk and bumps into you. Fades in the light. Drops Gloom Dust.'),
                    ('brute', 'Gloom Brute', 'A big gloomling. Hits harder; drops more.')]
            for i, (k, name, desc) in enumerate(rows):
                y = y0 - i * 52 * s
                gui.rect(x0, y - 42 * s, tw_, 48 * s, (0.97, 0.95, 0.98, 1), 12 * s)
                col = {'woolhop': (0.99, 0.95, 0.90), 'pebblebeak': (0.98, 0.86, 0.70), 'mossback': (0.46, 0.68, 0.42),
                       'skywhale': (0.78, 0.88, 0.94), 'fairy': (1.0, 0.86, 0.55),
                       'gloomling': (0.30, 0.22, 0.46), 'brute': (0.30, 0.22, 0.46)}[k]
                gui.hexagon(x0 + 26 * s, y - 18 * s, 14 * s, (*col, 1), border=(1, 1, 1), border_w=2 * s)
                gui.text(name, x0 + 52 * s, y - 8 * s, 11, INK, font='bold')
                gui.text(desc, x0 + 52 * s, y - 28 * s, 9, MUTED)
        elif self.tab == 3:
            lines = ['Dormant spires stand on old plinths across every sky. Each one longs for certain cells.',
                     'Place those cells on the ring of six hexes right around its base, and it will wake.',
                     'Each awakening teaches you a gift (Glide, then Updraft, then Tidecall) and leaves you Aetherite and Glimmer. '
                     'The wayfinder at the top of the screen points to the nearest sleeping spire.']
            gui.text('\n\n'.join(lines), x0, y0, 11, INK, width=tw_, anchor_y='top')
            if ses:
                gui.text(f'Spires awake in this sky: {len(ses.awakened)}', x0, y0 - 170 * s, 14, INK, font='bold')
                ns = ses.nearest_spire
                if ns:
                    sp, d = ns
                    want = ', '.join(MT.NAMES[m] for m in sp['wants'])
                    gui.text(f'The nearest sleeping spire ({d:.0f} m away) longs for: {want}', x0, y0 - 204 * s, 11, MUTED)
        else:
            rows = [('W A S D / mouse', 'walk and look'), ('Space', 'jump · hold to glide · climb vines'),
                    ('Shift', 'crouch (sneak, no falling off edges)'), ('Ctrl', 'hurry'),
                    ('Left click (hold)', 'mine · hit creatures'),
                    ('Right click', 'place · use · eat'), ('1 - 9 / wheel', 'pick a hotbar slot'),
                    ('E', 'backpack and crafting'), ('Q', 'drop the held item'),
                    ('J', 'journal'), ('P', 'the Path (goals and how-to)'),
                    ('T', 'tidecall (once learned)'),
                    ('Enter or /', 'type a command (/help)'), ('F1 · F2 · F3', 'hide HUD · snapshot · details'),
                    ('Middle click', 'in Dreamer mode, remove the item you click (or the one in your hand)'),
                    ('F4', 'dev mode on / off'), ('F5', 'cycle first / third person'), ('F7', 'admin panel (dev mode)'),
                    ('F · N · [ ]', 'dev: fly · noclip · fly speed'), ('Esc', 'rest (pause)')]
            for i, (k, d) in enumerate(rows):
                col, row = i % 2, i // 2
                cx = x0 + col * tw_ / 2
                cy = y0 - row * 46 * s
                kw = gui.text_width(k, 10, 'bold') + 20 * s
                gui.rect(cx, cy - 26 * s, kw, 28 * s, (0.95, 0.93, 0.98, 1), 9 * s)
                gui.text(k, cx + kw / 2, cy - 12 * s, 10, INK, 'center', 'center', font='bold')
                gui.text(d, cx + kw + 12 * s, cy - 12 * s, 10, MUTED, 'left', 'center')
        if gui.button(px + pw - 170 * s, py + 22 * s, 140 * s, 38 * s, 'Close', primary=True):
            self.escape(app)

    def _recipes(self, gui, app, x0, y0, tw_, ybot):
        s = gui.s
        from .inventory_ui import draw_icon, recipe_rows
        rows = recipe_rows()
        per_row = 3
        cw = tw_ / per_row
        rh = 58 * s
        vis = max(1, int((y0 - ybot) // rh))
        total = (len(rows) + per_row - 1) // per_row
        if gui.scroll:
            self.scroll = max(0, min(total - vis, self.scroll - int(gui.scroll)))
        for k, (rec, res, cnt) in enumerate(rows[self.scroll * per_row:(self.scroll + vis) * per_row]):
            col, row = k % per_row, k // per_row
            x, y = x0 + col * cw, y0 - (row + 1) * rh + 8 * s
            gui.rect(x, y, cw - 10 * s, rh - 8 * s, (0.97, 0.95, 0.98, 1), 12 * s)
            draw_icon(gui, app, res, x + 6 * s, y + 4 * s, rh - 16 * s)
            name = I.get(res).name + (f' x{cnt}' if cnt > 1 else '')
            gui.text(name, x + rh, y + rh * 0.56, 10, INK, font='bold')
            need = I.recipe_needs(rec[0])
            txt = ', '.join(f'{n} {I.name_of(v)}' for v, n in need.items())
            gui.text(txt[:46], x + rh, y + rh * 0.24, 8, MUTED)
        if total > vis:
            gui.text(f'scroll for more  ·  {self.scroll + 1}-{min(total, self.scroll + vis)} of {total} rows',
                     x0, ybot - 10 * s, 9, MUTED)

    def escape(self, app):
        app.set_screen(self.parent if self.help_only else None)


class WhisperScreen(Screen):
    initial_focus = 'cmd'
    pauses = False

    def __init__(self, text=''):
        self.text = text

    def build(self, gui, app, w, h):
        s = gui.s
        gui.text('Whisper to the sky: /help lists every command (admin commands need dev mode, F4)', 20 * s, 72 * s, 10, WHITE)
        self.text = gui.textfield(16 * s, 20 * s, w - 32 * s, 40 * s, 'cmd', self.text, '/', 80)
        if 'enter' in gui.keys:
            if app.session and self.text.strip():
                app.session.command(self.text)
            app.set_screen(None)

"""Backpack, crafting (2x2 and the Tinker Bench's 3x3), chests, the kiln, the admin panel."""
import math
import time

from .gui import INK, ACCENT, ACCENT2, MUTED, WHITE
from .screens import Screen, veil
from .. import items as I
from .. import materials as MT
from ..inventory import Inventory, click_slot

SLOT_BG = (0.93, 0.91, 0.96, 1)
SLOT_HOVER = (1.0, 0.97, 0.92, 1)


def draw_icon(gui, app, iid, x, y, size, alpha=1.0):
    r = app.renderer
    uv = r.icon_uv.get(iid) if r.icon_tex is not None else None
    if uv:
        gui.icon_tex(r.icon_tex, uv, x, y, size, size, (1, 1, 1, alpha))
    else:
        it = I.get(iid)
        col = it.color if it else (1, 0, 1)
        gui.hexagon(x + size / 2, y + size / 2, size * 0.35, (*col, alpha), border=(1, 1, 1), border_w=1.5 * gui.s)


def draw_stack(gui, app, slot, x, y, size, show_count=True, always=False):
    if not slot:
        return
    draw_icon(gui, app, slot[0], x + size * 0.08, y + size * 0.08, size * 0.84)
    it = I.get(slot[0])
    if show_count and (slot[1] > 1 or always):
        gui.text(str(slot[1]), x + size - 4 * gui.s, y + 9 * gui.s, 10, (0.15, 0.1, 0.25, 0.8), 'right', 'center', font='bold')
        gui.text(str(slot[1]), x + size - 5 * gui.s, y + 10 * gui.s, 10, WHITE, 'right', 'center', font='bold')
    if it and it.kind == 'tool' and it.uses and slot[2] < it.uses:
        f = max(0.0, slot[2] / it.uses)
        bw = size - 12 * gui.s
        gui.rect(x + 6 * gui.s, y + 4 * gui.s, bw, 3.5 * gui.s, (0.2, 0.15, 0.3, 0.5), 2 * gui.s)
        gui.rect(x + 6 * gui.s, y + 4 * gui.s, bw * f, 3.5 * gui.s, (0.4 + 0.6 * (1 - f), 0.9 * f + 0.2, 0.4, 1), 2 * gui.s)


def recipe_rows(max_size=3):
    out = []
    seen = set()
    for rec in I.RECIPES:
        rows, (res, cnt), shapeless = rec
        if I.recipe_size(rows) > max_size:
            continue
        key = (res, str(rows))
        if key in seen:
            continue
        seen.add(key)
        out.append((rec, res, cnt))
    return out


def can_make(inv_slots, rows):
    have = {}
    for s in inv_slots:
        if s:
            have[s[0]] = have.get(s[0], 0) + s[1]
    for v, n in I.recipe_needs(rows).items():
        if v in I.GROUPS:
            if sum(have.get(m, 0) for m in I.GROUPS[v]) < n:
                return False
        elif have.get(v, 0) < n:
            return False
    return True


class SlotScreen(Screen):
    """Shared slot drawing and Minecraft-style clicking."""
    pauses = False

    def __init__(self):
        self.tip = None

    def slot(self, gui, app, slots, i, x, y, size, on_click=None, take_only=False, show_count=True, always_count=False):
        s = gui.s
        hover = gui.inside(x, y, size, size)
        gui.rect(x, y, size, size, SLOT_HOVER if hover else SLOT_BG, 10 * s,
                 border=ACCENT if hover else (1, 1, 1), border_w=(2 if hover else 1.2) * s)
        draw_stack(gui, app, slots[i], x, y, size, show_count=show_count, always=always_count)
        ses = app.session
        if hover and slots[i]:
            it = I.get(slots[i][0])
            extra = f'  ({slots[i][2]}/{it.uses} uses left)' if it.kind == 'tool' else ''
            self.tip = (it.name + extra, it.desc)
        for b in (1, 4, 2):
            if gui.clicked(x, y, size, size, b):
                gui.consume_click()
                if b == 2:
                    if ses.remove_inv_slot(slots, i):
                        app.audio.play('click', 0.3)
                    return True
                if on_click:
                    on_click(b == 4)
                    return True
                if take_only:
                    return True
                if app.keys_down_shift() and slots[i]:
                    self.quick_move(app, slots, i)
                else:
                    ses.cursor = click_slot(slots, i, ses.cursor, right=(b == 4))
                app.audio.play('click', 0.3)
                return True
        return False

    def quick_move(self, app, slots, i):
        """Shift-click: send a stack between the backpack and the open container."""
        ses = app.session
        s = slots[i]
        target = self.other(app, slots)
        if target is None:
            # inside the backpack: swap between hotbar and the rest
            inv = ses.inv.slots
            rng = range(9, 36) if i < 9 else range(0, 9)
            tmp = Inventory(0)
            tmp.slots = [inv[k] for k in rng]
            left = tmp.add(s[0], s[1], s[2])
            for k, v in zip(rng, tmp.slots):
                inv[k] = v
        else:
            tmp = Inventory(0)
            tmp.slots = target
            left = tmp.add(s[0], s[1], s[2])
        if left:
            s[1] = left
        else:
            slots[i] = None

    def other(self, app, slots):
        return None

    def backpack(self, gui, app, x, y, size, gap):
        inv = app.session.inv.slots
        for k in range(27):
            col, row = k % 9, k // 9
            self.slot(gui, app, inv, 9 + k, x + col * (size + gap), y + (2 - row) * (size + gap) + size + gap * 3, size)
        for k in range(9):
            self.slot(gui, app, inv, k, x + k * (size + gap), y, size)

    def finish(self, gui, app):
        s = gui.s
        ses = app.session
        if ses.cursor:
            draw_stack(gui, app, ses.cursor, gui.mx - 24 * s, gui.my - 24 * s, 48 * s)
        elif self.tip:
            name, desc = self.tip
            tw = max(gui.text_width(name, 10, 'bold'), gui.text_width(desc, 9) if desc else 0) + 20 * s
            th = 44 * s if desc else 28 * s
            tx, ty = gui.mx + 16 * s, gui.my - th - 6 * s
            gui.rect(tx, ty, tw, th, (0.24, 0.20, 0.34, 0.95), 8 * s)
            gui.text(name, tx + 10 * s, ty + th - 14 * s, 10, WHITE, 'left', 'center', font='bold')
            if desc:
                gui.text(desc, tx + 10 * s, ty + 12 * s, 9, (1, 1, 1, 0.8), 'left', 'center')
        self.tip = None
        # clicking outside the panel with something on the cursor drops it
        for (cx, cy, b) in gui.clicks:
            if ses.cursor and not (self.px <= cx <= self.px + self.pw and self.py <= cy <= self.py + self.ph):
                p = ses.player
                from ..entities import Drop
                from ..mathutil import forward_vector
                f = forward_vector(p.yaw, 0)
                d = Drop(ses.cursor[0], ses.cursor[1], p.x + f[0] * 1.2, p.y + 1.3, p.z + f[2] * 1.2, ses.cursor[2])
                d.age = -1.0
                ses.drops.append(d)
                ses.cursor = None
        gui.consume_click()

    def close(self, app):
        ses = app.session
        if ses.cursor:
            ses.give(ses.cursor[0], ses.cursor[1], ses.cursor[2], quiet=True)
            ses.cursor = None

    def escape(self, app):
        self.close(app)
        app.set_screen(None)


class CraftScreen(SlotScreen):
    def __init__(self, n=2):
        super().__init__()
        self.n = n
        self.grid = [None] * (n * n)
        self.scroll = 0

    def result(self):
        rows = [self.grid[r * self.n:(r + 1) * self.n] for r in range(self.n)]
        return I.match([[s[0] if s else None for s in row] for row in rows])

    def build(self, gui, app, w, h):
        s = gui.s
        ses = app.session
        veil(gui, w, h, 0.35)
        size, gap = 46 * s, 6 * s
        left_w = 9 * (size + gap) + 40 * s
        right_w = 330 * s
        pw = min(left_w + right_w + 30 * s, w - 20 * s)
        ph = min(5 * (size + gap) + 3 * (size + gap) + 170 * s, h - 20 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        self.px, self.py, self.pw, self.ph = px, py, pw, ph
        gui.panel(px, py, pw, ph)
        title = 'Tinker Bench' if self.n == 3 else 'Backpack'
        gui.text(title, px + 26 * s, py + ph - 34 * s, 18, INK, 'left', 'center', font='title')
        gui.text('Craft on the grid. Shift-click moves stacks; right-click splits.', px + 26 * s, py + ph - 58 * s, 9, MUTED)
        # grid
        gx = px + 26 * s + (3 - self.n) * (size + gap) / 2
        gy = py + ph - 80 * s - self.n * (size + gap)
        for k in range(self.n * self.n):
            c, r = k % self.n, k // self.n
            self.slot(gui, app, self.grid, k, gx + c * (size + gap), gy + (self.n - 1 - r) * (size + gap), size)
        ax = px + 26 * s + 3 * (size + gap) + 14 * s
        ay = gy + self.n * (size + gap) / 2 - size / 2
        gui.text('→', ax + 18 * s, ay + size / 2, 22, MUTED, 'center', 'center', font='title')
        res = self.result()
        ox = ax + 46 * s
        out = [[res[0], res[1], I.get(res[0]).uses] if res else None]

        def take(right):
            if not res:
                return
            if app.keys_down_shift():
                made = 0
                while self.result() == res and made < 64:
                    left = ses.inv.add(res[0], res[1])
                    ses.craft_take(self.grid, res)
                    made += 1
                    if left:
                        ses.give(res[0], left)
                        break
            else:
                it = I.get(res[0])
                if ses.cursor is None:
                    ses.cursor = [res[0], res[1], it.uses]
                elif ses.cursor[0] == res[0] and ses.cursor[1] + res[1] <= it.stack and it.kind != 'tool':
                    ses.cursor[1] += res[1]
                else:
                    return
                ses.craft_take(self.grid, res)
            app.audio.play('shape', 0.6)
        gui.rect(ox - 4 * s, ay - 4 * s, size + 8 * s, size + 8 * s, (1, 0.9, 0.82, 1), 12 * s)
        self.slot(gui, app, out, 0, ox, ay, size, on_click=take)
        if res:
            gui.text(I.get(res[0]).name, ox + size + 14 * s, ay + size / 2, 11, INK, 'left', 'center', font='bold')
        elif self.n == 2:
            gui.text('Need a 3x3 grid? Place a', ox + size + 14 * s, ay + size / 2 + 8 * s, 9, MUTED, 'left', 'center')
            gui.text('Tinker Bench and right-click it.', ox + size + 14 * s, ay + size / 2 - 8 * s, 9, MUTED, 'left', 'center')
        # backpack
        self.backpack(gui, app, px + 26 * s, py + 24 * s, size, gap)
        # recipe book
        self.book(gui, app, px + left_w + 10 * s, py + 24 * s, right_w, ph - 48 * s)
        self.finish(gui, app)

    def book(self, gui, app, x, y, w, h):
        s = gui.s
        ses = app.session
        gui.rect(x, y, w, h, (0.97, 0.95, 0.98, 1), 14 * s)
        gui.text('Recipe book', x + 14 * s, y + h - 20 * s, 12, INK, 'left', 'center', font='bold')
        gui.text('click one to fill the grid', x + w - 14 * s, y + h - 20 * s, 8.5, MUTED, 'right', 'center')
        rows = recipe_rows(self.n)
        allslots = ses.inv.slots + self.grid
        rows.sort(key=lambda r: (not can_make(allslots, r[0][0]),))
        rh = 40 * s
        top = y + h - 40 * s
        vis = int((h - 50 * s) // rh)
        if gui.scroll and gui.inside(x, y, w, h):
            self.scroll = max(0, min(len(rows) - vis, self.scroll - int(gui.scroll) * 2))
        for k, (rec, res, cnt) in enumerate(rows[self.scroll:self.scroll + vis]):
            ry = top - (k + 1) * rh
            ok = can_make(allslots, rec[0])
            hover = gui.inside(x + 8 * s, ry, w - 16 * s, rh - 4 * s)
            gui.rect(x + 8 * s, ry, w - 16 * s, rh - 4 * s, (1, 1, 1, 1) if hover else (1, 1, 1, 0.55), 9 * s,
                     border=ACCENT if hover and ok else None, border_w=2 * s)
            draw_icon(gui, app, res, x + 12 * s, ry + 2 * s, rh - 8 * s, 1.0 if ok else 0.4)
            nm = I.get(res).name + (f' x{cnt}' if cnt > 1 else '')
            gui.text(nm, x + 12 * s + rh, ry + rh * 0.62, 9.5, INK if ok else MUTED, font='bold')
            need = ', '.join(f'{n} {I.name_of(v)}' for v, n in I.recipe_needs(rec[0]).items())
            gui.text(need[:44], x + 12 * s + rh, ry + rh * 0.22, 7.5, MUTED)
            if hover and gui.clicked(x + 8 * s, ry, w - 16 * s, rh - 4 * s):
                gui.consume_click()
                if ok:
                    self.fill(app, rec)
                else:
                    ses.toast('Missing ingredients', need, 2.5)
        if len(rows) > vis:
            gui.text(f'scroll  ·  {self.scroll + 1}-{min(len(rows), self.scroll + vis)} of {len(rows)}', x + w / 2,
                     y + 10 * s, 8, MUTED, 'center', 'center')

    def fill(self, app, rec):
        """Move ingredients from the backpack onto the grid in the recipe's shape."""
        ses = app.session
        self.return_grid(app)
        rows = rec[0]
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v is None:
                    continue
                cands = I.GROUPS.get(v, {v})
                for i, sl in enumerate(ses.inv.slots):
                    if sl and sl[0] in cands:
                        self.grid[r * self.n + c] = [sl[0], 1, sl[2]]
                        ses.inv.take_from(i)
                        break
        app.audio.play('click', 0.5)

    def return_grid(self, app):
        ses = app.session
        for i, sl in enumerate(self.grid):
            if sl:
                ses.give(sl[0], sl[1], sl[2], quiet=True)
                self.grid[i] = None

    def close(self, app):
        self.return_grid(app)
        super().close(app)


class ChestScreen(SlotScreen):
    def __init__(self, chest):
        super().__init__()
        self.chest = chest

    def other(self, app, slots):
        return self.chest.slots if slots is app.session.inv.slots else app.session.inv.slots

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.35)
        size, gap = 46 * s, 6 * s
        pw = 9 * (size + gap) + 46 * s
        ph = 7 * (size + gap) + 150 * s
        px, py = (w - pw) / 2, (h - ph) / 2
        self.px, self.py, self.pw, self.ph = px, py, pw, ph
        gui.panel(px, py, pw, ph)
        gui.text('Chest', px + 26 * s, py + ph - 32 * s, 18, INK, 'left', 'center', font='title')
        top = py + ph - 60 * s
        for k in range(27):
            c, r = k % 9, k // 9
            self.slot(gui, app, self.chest.slots, k, px + 26 * s + c * (size + gap), top - (r + 1) * (size + gap), size)
        gui.text('Backpack', px + 26 * s, top - 3 * (size + gap) - 18 * s, 11, MUTED, font='bold')
        self.backpack(gui, app, px + 26 * s, py + 24 * s, size, gap)
        self.finish(gui, app)


class KilnScreen(SlotScreen):
    def __init__(self, kiln):
        super().__init__()
        self.kiln = kiln

    def other(self, app, slots):
        if slots is app.session.inv.slots:
            return None
        return app.session.inv.slots

    def quick_move(self, app, slots, i):
        ses = app.session
        sl = slots[i]
        if slots is ses.inv.slots:
            k = self.kiln['slots'].slots
            dest = 1 if sl[0] in I.FUEL and sl[0] not in I.SMELT else 0
            if k[dest] is None:
                k[dest] = sl
                slots[i] = None
            elif k[dest][0] == sl[0]:
                n = min(sl[1], I.get(sl[0]).stack - k[dest][1])
                k[dest][1] += n
                sl[1] -= n
                if sl[1] <= 0:
                    slots[i] = None
        else:
            left = ses.inv.add(sl[0], sl[1], sl[2])
            if left:
                sl[1] = left
            else:
                slots[i] = None

    def build(self, gui, app, w, h):
        s = gui.s
        veil(gui, w, h, 0.35)
        size, gap = 46 * s, 6 * s
        pw = 9 * (size + gap) + 46 * s
        ph = 4 * (size + gap) + 290 * s
        px, py = (w - pw) / 2, (h - ph) / 2
        self.px, self.py, self.pw, self.ph = px, py, pw, ph
        gui.panel(px, py, pw, ph)
        gui.text('Kiln', px + 26 * s, py + ph - 32 * s, 18, INK, 'left', 'center', font='title')
        gui.text('Top: what to smelt. Bottom: fuel (Emberite, wood, sticks, gloom dust).', px + 26 * s, py + ph - 56 * s, 9, MUTED)
        k = self.kiln
        sl = k['slots'].slots
        cx = px + pw / 2 - 90 * s
        top = py + ph - 90 * s
        self.slot(gui, app, sl, 0, cx, top - size, size, show_count=True, always_count=True)
        self.slot(gui, app, sl, 1, cx, top - size * 2 - 40 * s, size, show_count=True, always_count=True)
        gui.text('Smelt', cx - 12 * s, top - size / 2, 10, MUTED, 'right', 'center', font='bold')
        gui.text('Fuel', cx - 12 * s, top - size * 1.5 - 40 * s, 10, MUTED, 'right', 'center', font='bold')
        fl = k['burn'] / max(k['burn_max'], 0.01) if k['burn'] > 0 else 0
        fy = top - size - 30 * s
        gui.circle(cx + size / 2, fy + 5 * s, 9 * s, (0.85, 0.82, 0.88, 1))
        if fl > 0:
            gui.circle(cx + size / 2, fy + 5 * s, 9 * s * (0.4 + 0.6 * fl), (1.0, 0.6, 0.3, 1))
        ax = cx + size + 30 * s
        aw = 80 * s
        gui.rect(ax, top - size * 1.5 - 24 * s, aw, 10 * s, (0.85, 0.82, 0.88, 1), 5 * s)
        gui.rect(ax, top - size * 1.5 - 24 * s, aw * min(1, k['prog']), 10 * s, ACCENT, 5 * s)
        out_x = ax + aw + 30 * s
        gui.rect(out_x - 4 * s, top - size * 1.5 - 20 * s - size / 2 - 4 * s, size + 8 * s, size + 8 * s, (1, 0.9, 0.82, 1), 12 * s)
        self.slot(gui, app, sl, 2, out_x, top - size * 1.5 - 20 * s - size / 2, size, show_count=True, always_count=True)
        res = I.SMELT.get(sl[0][0]) if sl[0] else None
        hint = f'makes {I.get(res).name}' if res else ('this won\'t smelt' if sl[0] else 'ores, sand, clay, stone, hopmeat, wood')
        gui.text(hint, out_x + size + 14 * s, top - size * 1.5 - 20 * s, 9, MUTED, 'left', 'center')
        self.backpack(gui, app, px + 26 * s, py + 24 * s, size, gap)
        self.finish(gui, app)


class FadedScreen(Screen):
    pauses = False

    def __init__(self, why=''):
        self.why = why

    def build(self, gui, app, w, h):
        s = gui.s
        gui.rect(0, 0, w, h, (0.55, 0.30, 0.45, 0.45))
        gui.text('You drifted off...', w / 2, h * 0.62, 32, WHITE, 'center', 'center', font='title')
        msg = {'fall': 'That was a long way down.', 'gloomling': 'A gloomling bumped you once too often.',
               'brute': 'A gloom brute got you.'}.get(self.why, 'Rest a moment.')
        gui.text(msg + '  You keep everything you carry.', w / 2, h * 0.62 - 44 * s, 12, (1, 1, 1, 0.9), 'center', 'center')
        bw, bh = 240 * s, 44 * s
        if gui.button(w / 2 - bw / 2, h * 0.42, bw, bh, 'Wake again', primary=True):
            app.session.respawn()
            app.set_screen(None)
        if gui.button(w / 2 - bw / 2, h * 0.42 - 54 * s, bw, bh, 'Save and leave'):
            app.session.respawn()
            app.quit_to_title()

    def escape(self, app):
        pass


class AdminScreen(Screen):
    """Dev mode's admin panel: commands, quick switches and every item in the game."""
    pauses = False

    def __init__(self):
        self.scroll = 0
        self.page = 0

    def build(self, gui, app, w, h):
        s = gui.s
        ses = app.session
        p = ses.player
        veil(gui, w, h, 0.4)
        pw, ph = min(1180 * s, w - 20 * s), min(660 * s, h - 20 * s)
        px, py = (w - pw) / 2, (h - ph) / 2
        gui.panel(px, py, pw, ph)
        gui.text('Admin panel', px + 26 * s, py + ph - 34 * s, 20, INK, 'left', 'center', font='title')
        on = ses.dev
        tx = px + 230 * s
        gui.rect(tx, py + ph - 50 * s, 150 * s, 32 * s, ACCENT if on else (0.85, 0.82, 0.9, 1), 16 * s)
        gui.text('Dev mode ' + ('ON' if on else 'OFF'), tx + 75 * s, py + ph - 34 * s, 11, WHITE, 'center', 'center', font='bold')
        if gui.clicked(tx, py + ph - 50 * s, 150 * s, 32 * s):
            gui.consume_click()
            ses.set_dev(not on)
        gui.text('F4 toggles dev mode · F7 opens this panel · Enter or / to type a command', tx + 170 * s, py + ph - 34 * s,
                 9, MUTED, 'left', 'center')
        # commands list (left)
        cx0, cy0 = px + 26 * s, py + ph - 80 * s
        colw = 400 * s
        gui.rect(cx0 - 8 * s, py + 24 * s, colw, ph - 110 * s, (0.97, 0.95, 0.98, 1), 14 * s)
        gui.text('Commands', cx0 + 4 * s, cy0 - 6 * s, 12, INK, font='bold')
        for i, (c, d) in enumerate(ses.ADMIN_HELP):
            y = cy0 - 30 * s - i * 28 * s
            if y < py + 36 * s:
                break
            gui.text(c, cx0 + 4 * s, y, 9.5, INK, font='bold')
            gui.text(d, cx0 + 4 * s, y - 12 * s, 8, MUTED)
        # quick switches (middle)
        bx0 = px + 26 * s + colw + 10 * s
        bw, bh = 170 * s, 34 * s
        btns = [
            (('Flying: on' if p.drifting else 'Flying: off'), lambda: ses.command('/fly')),
            (('Noclip: on' if p.noclip else 'Noclip: off'), lambda: ses.command('/noclip')),
            (f'Speed - ({p.fly_speed:.0f})', lambda: ses.command(f'/speed {max(2, p.fly_speed - 5)}')),
            (f'Speed + ({p.fly_speed:.0f})', lambda: ses.command(f'/speed {p.fly_speed + 5}')),
            ('Lighttide', lambda: ses.command('/tide light')), ('Dusktide', lambda: ses.command('/tide dusk')),
            ('Rain' if ses.weather == 'clear' else 'Clear skies',
             lambda: ses.command('/weather ' + ('rain' if ses.weather == 'clear' else 'clear'))),
            ('Heal + feed', lambda: (ses.command('/heal'), ses.command('/feed'))),
            ('Clear creatures', lambda: ses.command('/killmobs')),
            ('Gloomlings: ' + ('on' if app.settings['dusk_critters'] else 'off'),
             lambda: ses.command('/mobs ' + ('off' if app.settings['dusk_critters'] else 'on'))),
            ('Spawn woolhop', lambda: ses.command('/spawn woolhop')),
            ('Spawn pebblebeak', lambda: ses.command('/spawn pebblebeak')),
            ('Spawn mossback', lambda: ses.command('/spawn mossback')),
            ('Spawn gloomling', lambda: ses.command('/spawn gloomling')),
            ('Go to spire', lambda: ses.command('/tp spire')),
            ('Set pos1 / pos2', lambda: ses.command('/pos1' if not ses.pos1 or ses.pos2 else '/pos2')),
            ('Undo last fill', lambda: ses.command('/undo')),
            ('Empty backpack', lambda: ses.command('/clearinv')),
        ]
        for i, (label, fn) in enumerate(btns):
            col, row = i % 2, i // 2
            x = bx0 + col * (bw + 8 * s)
            y = py + ph - 90 * s - row * (bh + 8 * s)
            if y < py + 24 * s:
                break
            if gui.button(x, y, bw, bh, label, size=9.5, key='adm' + str(i)):
                if not ses.dev and i not in ():
                    ses.set_dev(True)
                fn()
        # every item (right)
        ix0 = bx0 + 2 * (bw + 8 * s) + 14 * s
        iw = px + pw - 26 * s - ix0
        gui.rect(ix0 - 8 * s, py + 24 * s, iw + 16 * s, ph - 110 * s, (0.97, 0.95, 0.98, 1), 14 * s)
        gui.text('Every item  ·  click for a stack (right-click: one)', ix0 + 4 * s, cy0 - 6 * s, 10, INK, font='bold')
        size = 38 * s
        cols = max(1, int(iw // (size + 4 * s)))
        ids = sorted(I.ITEMS)
        top = cy0 - 26 * s
        rows_vis = int((top - py - 34 * s) // (size + 4 * s))
        total_rows = (len(ids) + cols - 1) // cols
        if gui.scroll and gui.inside(ix0, py + 24 * s, iw, ph - 110 * s):
            self.scroll = max(0, min(total_rows - rows_vis, self.scroll - int(gui.scroll)))
        tip = None
        for k, iid in enumerate(ids[self.scroll * cols:(self.scroll + rows_vis) * cols]):
            c, r = k % cols, k // cols
            x, y = ix0 + c * (size + 4 * s), top - (r + 1) * (size + 4 * s)
            hover = gui.inside(x, y, size, size)
            gui.rect(x, y, size, size, SLOT_HOVER if hover else (1, 1, 1, 0.8), 8 * s,
                     border=ACCENT if hover else None, border_w=2 * s)
            draw_icon(gui, app, iid, x + 3 * s, y + 3 * s, size - 6 * s)
            if hover:
                tip = I.get(iid).name
            for b in (1, 4):
                if gui.clicked(x, y, size, size, b):
                    gui.consume_click()
                    it = I.get(iid)
                    ses.give(iid, 1 if b == 4 else it.stack)
                    ses.toast('Gave ' + it.name, '', 1.2)
        if tip:
            tw = gui.text_width(tip, 10, 'bold') + 20 * s
            gui.rect(gui.mx + 14 * s, gui.my - 30 * s, tw, 26 * s, (0.24, 0.20, 0.34, 0.95), 8 * s)
            gui.text(tip, gui.mx + 24 * s, gui.my - 17 * s, 10, WHITE, 'left', 'center', font='bold')
        if gui.button(px + pw - 150 * s, py + ph - 52 * s, 124 * s, 36 * s, 'Close', primary=True):
            self.escape(app)

    def escape(self, app):
        app.set_screen(None)


class BackpackScreen(CraftScreen):
    def __init__(self):
        super().__init__(2)

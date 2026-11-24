"""The in-sky overlay: chord gems, wayfinder, tide dial, toasts and the hex reticle."""
import math
import time

from .gui import INK, ACCENT, ACCENT2, MUTED, WHITE
from .. import materials as MT
from ..materials import ELEMENTS, ELEMENT_COLORS, FORM_HINTS, chord_cost
from ..hexgrid import center, cell_at
from .. import tide as TIDE

SHADOW = (0.15, 0.10, 0.25, 0.45)


def soft_text(gui, s, x, y, size, color=WHITE, ax='left', ay='baseline', font='body'):
    gui.text(s, x + 1.2 * gui.s, y - 1.2 * gui.s, size, SHADOW, ax, ay, font=font)
    gui.text(s, x, y, size, color, ax, ay, font=font)


def draw_hud(gui, app, ses, w, h):
    s = gui.s
    p = ses.player
    # reticle
    gui.hexagon(w / 2, h / 2, 7 * s, (1, 1, 1, 0), border=(1, 1, 1), border_w=1.8 * s)
    gui.circle(w / 2, h / 2, 1.4 * s, (1, 1, 1, 0.9))
    if ses.target_name:
        soft_text(gui, ses.target_name, w / 2, h / 2 - 26 * s, 10, (1, 1, 1, 0.9), 'center', 'center')
        if ses.target:
            m = ses.world.get(*ses.target)
            if m == MT.ID['dormant_spire']:
                sp = _spire_for(ses, ses.target)
                if sp:
                    _, missing = ses.spire_state(sp)
                    soft_text(gui, 'It longs for: ' + ', '.join(MT.NAMES[x] for x in sp['wants']) +
                              '  (shape them around its base)', w / 2, h / 2 - 46 * s, 9.5, (1, 0.92, 0.8, 1), 'center', 'center')

    # chord gems
    n = 4
    r = 26 * s
    gap = 58 * s
    cy = 46 * s
    x0 = w / 2 - gap * (n - 1) / 2
    form = ses.form
    cost = chord_cost(ses.chord)
    gui.rect(w / 2 - 150 * s, 8 * s, 300 * s, 80 * s, (0.2, 0.15, 0.3, 0.22), 30 * s)
    for i in range(4):
        on = i in ses.chord
        cx = x0 + i * gap
        lift = 6 * s if on else 0
        col = ELEMENT_COLORS[i]
        gui.hexagon(cx, cy + lift - 2 * s, r + 3 * s, (0.15, 0.1, 0.25, 0.25))
        gui.hexagon(cx, cy + lift, r, (*col, 1.0 if on else 0.55), border=(1, 1, 1) if on else (0.95, 0.92, 1),
                    border_w=(3 if on else 1.5) * s)
        val = '∞' if ses.mode == 'dreamer' else str(ses.essence[i])
        gui.text(val, cx, cy + lift + 3 * s, 12, INK if on else (0.25, 0.22, 0.34, 0.8), 'center', 'center', font='bold')
        gui.text(f'{i + 1} {ELEMENTS[i]}', cx, cy + lift - 11 * s, 6.5, (0.25, 0.22, 0.34, 0.85), 'center', 'center')
    # tuned form
    afford = ses.can_afford()
    name = MT.NAMES[form]
    fy = cy + r + 40 * s
    gui.hexagon(w / 2 - gui.text_width(name, 15, 'title') / 2 - 18 * s, fy, 9 * s, (*MT.TOP[form], 1), border=(1, 1, 1),
                border_w=2 * s)
    soft_text(gui, name, w / 2, fy, 15, WHITE if afford else (1, 0.8, 0.8, 1), 'center', 'center', 'title')
    soft_text(gui, FORM_HINTS.get(form, ''), w / 2, fy - 20 * s, 9, (1, 1, 1, 0.85), 'center', 'center')

    # tide dial (top left)
    dx, dy = 44 * s, h - 44 * s
    dusk = TIDE.dusk_amount(ses.phase)
    gui.circle(dx, dy, 26 * s, (0.2, 0.15, 0.3, 0.30))
    gui.circle(dx, dy, 22 * s, (0.98, 0.88, 0.62, 1) if dusk < 0.5 else (0.62, 0.58, 0.92, 1), border=(1, 1, 1),
               border_w=2 * s)
    a = ses.phase * math.tau + math.pi / 2
    gui.circle(dx + math.cos(a) * 15 * s, dy + math.sin(a) * 15 * s, 4.5 * s, WHITE)
    soft_text(gui, TIDE.name(ses.phase), dx + 36 * s, dy + 4 * s, 12, WHITE, 'left', 'center', 'bold')
    soft_text(gui, f'{len(ses.awakened)} spire{"s" if len(ses.awakened) != 1 else ""} awake', dx + 36 * s, dy - 16 * s,
              9, (1, 1, 1, 0.85), 'left', 'center')
    gifts = []
    if p.can_glide: gifts.append('Glide')
    if p.can_updraft: gifts.append('Updraft')
    if ses.can_tidecall: gifts.append('Tidecall')
    if p.drifting: gifts.append('drifting')
    if gifts:
        soft_text(gui, '  ·  '.join(gifts), dx - 20 * s, dy - 44 * s, 9, (1, 0.95, 0.85, 0.9), 'left', 'center')

    # wayfinder (top centre)
    ww, wh = 380 * s, 26 * s
    wx, wy = w / 2 - ww / 2, h - 38 * s
    gui.rect(wx, wy, ww, wh, (0.2, 0.15, 0.3, 0.28), wh / 2)
    for k in range(-6, 7):
        tx = w / 2 + k * ww / 14
        gui.rect(tx - 0.7 * s, wy + 8 * s, 1.4 * s, 10 * s, (1, 1, 1, 0.35 if k else 0.8))
    ns = ses.nearest_spire
    if ns:
        sp, d = ns
        sx, sz = center(sp['q'], sp['r'])
        bearing = math.degrees(math.atan2(sx - p.x, -(sz - p.z)))
        rel = (bearing - p.yaw + 180) % 360 - 180
        t = max(-1, min(1, rel / 90))
        gx = w / 2 + t * (ww / 2 - 14 * s)
        pulse = 1 + 0.12 * math.sin(time.time() * 3)
        gui.hexagon(gx, wy + wh / 2, 9 * s * pulse, (0.75, 0.68, 1.0, 1), border=(1, 1, 1), border_w=2 * s)
        if abs(rel) > 90:
            soft_text(gui, '‹' if rel < 0 else '›', gx + (-16 if rel < 0 else 16) * s, wy + wh / 2, 12, WHITE, 'center', 'center')
        soft_text(gui, f'sleeping spire  ·  {d:,.0f} m', w / 2, wy - 12 * s, 9.5, (1, 1, 1, 0.9), 'center', 'center')
    else:
        soft_text(gui, 'no sleeping spire nearby: wander on', w / 2, wy - 12 * s, 9.5, (1, 1, 1, 0.8), 'center', 'center')

    # toasts
    ty = h - 110 * s
    for text, sub, left in reversed(ses.toasts):
        a = min(1.0, left / 0.6)
        tw = max(gui.text_width(text, 13, 'bold'), gui.text_width(sub, 9.5) if sub else 0) + 48 * s
        th = 56 * s if sub else 38 * s
        gui.rect(w / 2 - tw / 2, ty - th, tw, th, (0.99, 0.97, 0.94, 0.88 * a), 16 * s)
        gui.text(text, w / 2, ty - (18 if sub else 19) * s, 13, (*INK[:3], a), 'center', 'center', font='bold')
        if sub:
            gui.text(sub, w / 2, ty - 39 * s, 9.5, (*MUTED[:3], a), 'center', 'center')
        ty -= th + 8 * s

    # carried by the clouds: soft white-out
    if ses.carry > 0:
        a = 1 - abs(ses.carry - 0.8) / 0.8
        gui.rect(0, 0, w, h, (1, 0.98, 0.98, max(0, min(1, a * 1.3))))
    if time.perf_counter() - app.started < 40 and not app.show_debug:
        soft_text(gui, 'Left click gather  ·  Right click shape  ·  1-4 tune  ·  Space jump  ·  J journal  ·  Esc rest',
                  14 * s, 14 * s, 9, (1, 1, 1, 0.8))


def _spire_for(ses, cell):
    q, r, y = cell
    return ses.spire_at(q, r)

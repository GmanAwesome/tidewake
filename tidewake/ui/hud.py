"""The in-sky overlay: hotbar, hearts and food, wayfinder, tide dial, toasts and the hex reticle."""
import math
import time

from .gui import INK, ACCENT, ACCENT2, MUTED, WHITE
from .. import materials as MT
from .. import items as I
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
        nm = ses.target_name
        if ses.target_mob:
            nm += f'  {max(0, ses.target_mob.hp):.0f}/{ses.target_mob.max_hp}'
        soft_text(gui, nm, w / 2, h / 2 - 30 * s, 10, (1, 1, 1, 0.9), 'center', 'center')
        if ses.target:
            m = ses.world.get(*ses.target)
            if m == MT.ID['dormant_spire']:
                sp = _spire_for(ses, ses.target)
                if sp:
                    _, missing = ses.spire_state(sp)
                    soft_text(gui, 'It longs for: ' + ', '.join(MT.NAMES[x] for x in sp['wants']) +
                              '  (place them around its base)', w / 2, h / 2 - 46 * s, 9.5, (1, 0.92, 0.8, 1), 'center', 'center')

    # lesson-island talk: dialog only after a right-click; a small hint otherwise
    npc = ses.nearby_talk() if hasattr(ses, 'nearby_talk') else None
    if npc:
        lines = npc.get('lines') or ()
        if lines:
            i = int(npc.get('line', 0)) % len(lines)
            text = lines[i]
            bw = min(520 * s, w - 40 * s)
            # measure wrapped height so long lesson lines never sit on the hint
            probe = gui.text(text, -9999, -9999, 10, INK, 'left', 'top', width=bw - 32 * s)
            gui.queue.pop()
            th = max(getattr(probe, 'content_height', 16 * s) or 16 * s, 16 * s)
            hint_h = 22 * s if len(lines) > 1 else 10 * s
            bh = 20 * s + 18 * s + 10 * s + th + hint_h
            bx, by = w / 2 - bw / 2, h / 2 - 70 * s - bh
            gui.rect(bx, by, bw, bh, (1, 1, 1, 0.94), 14 * s, border=ACCENT, border_w=1.6 * s)
            soft_text(gui, npc['name'], bx + 16 * s, by + bh - 16 * s, 11, ACCENT, 'left', 'center', 'bold')
            gui.text(text, bx + 16 * s, by + bh - 36 * s, 10, INK, 'left', 'top', width=bw - 32 * s)
            if len(lines) > 1:
                gui.text('Right-click to hear more', bx + bw - 16 * s, by + 12 * s, 8, MUTED, 'right', 'center')
    elif getattr(ses, 'tutorial', False) and hasattr(ses, 'closest_npc'):
        hint = ses.closest_npc()
        if hint:
            soft_text(gui, 'Right-click to talk', w / 2, h / 2 - 86 * s, 11,
                      (1, 1, 1, 0.88), 'center', 'center', 'bold')

    # a quiet warning when the next step would leave the island
    if getattr(ses, 'edge_warn', 0) > 0:
        soft_text(gui, 'The shore drops away', w / 2, h / 2 - 64 * s, 11,
                  (1, 0.92, 0.8, 0.95), 'center', 'center', 'bold')

    # fishing prompt
    if getattr(ses, 'fishing', None):
        bite = ses.fishing['state'] == 'bite'
        msg = 'A bite!  Right-click to reel' if bite else 'Waiting…  the bobber will dip'
        soft_text(gui, msg, w / 2, h / 2 - 48 * s, 12,
                  (1.0, 0.85, 0.45, 1) if bite else (1, 1, 1, 0.9), 'center', 'center', 'bold')

    # mining progress ring
    if ses.mining and ses.mining[1] > 0:
        f = min(1.0, ses.mining[1])
        n = 18
        for k in range(n):
            a = math.pi / 2 - k / n * math.tau
            on = k / n < f
            gui.circle(w / 2 + math.cos(a) * 16 * s, h / 2 + math.sin(a) * 16 * s, 2.2 * s,
                       (1, 1, 1, 0.95) if on else (1, 1, 1, 0.25))

    # hotbar
    from .inventory_ui import draw_stack
    size, gap = 50 * s, 6 * s
    total = 9 * size + 8 * gap
    hx = w / 2 - total / 2
    hy = 14 * s
    gui.rect(hx - 8 * s, hy - 8 * s, total + 16 * s, size + 16 * s, (0.2, 0.15, 0.3, 0.30), 18 * s)
    for k in range(9):
        x = hx + k * (size + gap)
        sel = k == ses.hot
        gui.rect(x, hy + (4 * s if sel else 0), size, size, (1, 1, 1, 0.92 if sel else 0.55), 12 * s,
                 border=ACCENT if sel else (1, 1, 1), border_w=(3 if sel else 1) * s)
        draw_stack(gui, app, ses.inv.slots[k], x, hy + (4 * s if sel else 0), size)
        gui.text(str(k + 1), x + 6 * s, hy + size - 8 * s + (4 * s if sel else 0), 7, (0.3, 0.25, 0.4, 0.7), 'left', 'center')
    it = ses.held_item
    if it:
        lab = it.name
        if ses.dev:
            lab += '  ·  endless'
        soft_text(gui, lab, w / 2, hy + size + 26 * s, 12, WHITE, 'center', 'center', 'bold')
    # hearts and food
    by = hy + size + 46 * s
    if not ses.dev:
        hp = ses.hp
        for k in range(10):
            x = hx + k * 20 * s + 8 * s
            v = max(0.0, min(1.0, (hp - k * 2) / 2))
            gui.hexagon(x, by, 8 * s, (0.3, 0.2, 0.3, 0.45))
            if v > 0:
                shake = math.sin(time.time() * 40 + k) * 1.5 * s if ses.hurt_flash > 0 else 0
                gui.hexagon(x, by + shake, 7 * s * (0.55 + 0.45 * v), (1.0, 0.42, 0.52, 1), border=(1, 1, 1), border_w=1.2 * s)
        for k in range(10):
            x = hx + total - k * 20 * s - 8 * s
            v = max(0.0, min(1.0, (ses.food - k * 2) / 2))
            gui.circle(x, by, 7.5 * s, (0.3, 0.2, 0.3, 0.45))
            if v > 0:
                gui.circle(x, by, 6.5 * s * (0.55 + 0.45 * v), (1.0, 0.76, 0.40, 1), border=(1, 1, 1), border_w=1.2 * s)
    else:
        soft_text(gui, 'DEV MODE  ·  F fly  ·  N noclip  ·  [ ] speed  ·  F5 camera  ·  F7 admin panel', w / 2, by, 9.5,
                  (1, 0.9, 0.6, 1), 'center', 'center', 'bold')
        flags = []
        if p.drifting: flags.append(f'flying {p.fly_speed:.0f}')
        if p.noclip: flags.append('noclip')
        soft_text(gui, '  ·  '.join(flags), w / 2, by + 18 * s, 9, (1, 1, 1, 0.85), 'center', 'center')
    if ses.hurt_flash > 0:
        gui.rect(0, 0, w, h, (1.0, 0.3, 0.35, ses.hurt_flash * 0.4))
    if ses.weather == 'rain':
        gui.rect(0, 0, w, h, (0.45, 0.5, 0.65, 0.08))

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
    if gifts:
        soft_text(gui, '  ·  '.join(gifts), dx - 20 * s, dy - 44 * s, 9, (1, 0.95, 0.85, 0.9), 'left', 'center')

    # wayfinder (top centre) — hidden on the lesson island, which has no spires
    if not getattr(ses, 'tutorial', False):
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

    # toasts sit under the top chrome, not over the mid-screen figure or the tide dial
    ty = h - 78 * s
    if ses.mode == 'awaken':
        ty = min(ty, wy - 28 * s)
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
    # first-session hint lives above the hotbar, not over the tide dial or toasts
    if time.perf_counter() - app.started < 40 and not app.show_debug:
        soft_text(gui, 'Hold left click: mine  ·  Right click: place / use  ·  E backpack  ·  J journal  ·  F4 dev mode',
                  14 * s, 108 * s, 9, (1, 1, 1, 0.8))


def _spire_for(ses, cell):
    q, r, y = cell
    return ses.spire_at(q, r)

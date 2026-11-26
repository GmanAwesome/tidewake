"""Tour scripts (generators). Yield seconds to wait or a predicate to wait for."""
import math
import random

import numpy as np

from .config import LAYER, CHUNK, EYE
from .hexgrid import center, cell_at, ring
from .noise import seed_from_text
from . import materials as MT
from .ui import screens as S
from .ui import inventory_ui as IU
from . import items as I
from .hexgrid import spiral, DIRS

M = MT.ID


def title(app, log, shot, look_at, settled, arg):
    yield 2.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 1.0
    yield shot('title')
    yield 0.5


def showcase(app, log, shot, look_at, settled, arg):
    """Title-screen showcase: menu shot plus a few orbit angles without UI."""
    import time as _t
    t0 = _t.perf_counter()
    yield 1.0
    yield lambda: app.backdrop['world'].busy() == 0 and app.backdrop['world'].busy_lod() == 0
    log('showcase ready in', round(_t.perf_counter() - t0, 2), 's', 'chunks', len(app.backdrop['world'].chunks),
        'applied', len(app.backdrop['showcase'].applied))
    b = app.backdrop
    b['speed'] = 0.0
    b['ang'] = float(arg) if arg else 0.6
    yield 1.2
    yield shot('menu')
    keep = app.menu
    app.menu = None
    for k, ang in enumerate((3.0, 4.3, 5.4)):
        b['ang'] = ang
        yield 1.2
        yield shot(f'angle_{k + 1}')
    app.menu = keep
    yield 0.3


def play(app, log, shot, look_at, settled, arg):
    seed = seed_from_text(arg or 'honey-moth-7')
    yield 1.0
    app.create_sky('Tour Sky', seed, arg, 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    yield settled()
    yield 1.5
    yield shot('01_spawn')
    p = ses.player
    sp = ses.nearest_spire[0] if ses.nearest_spire else None
    log('spawn', p.x, p.y, p.z, 'spire', sp)
    app.show_debug = True
    yield 0.5
    yield shot('02_debug')
    app.show_debug = False
    # walk forward for a bit
    app.test_input = {'fwd': 1}
    yield 3.0
    app.test_input = {}
    yield 0.5
    yield shot('03_walked')
    log('after walk', p.x, p.y, p.z, p.on_ground)


def _stand(ses, q, r, look=None, up=0, dist_pitch=None):
    """Put the wanderer on top of column (q, r)."""
    p = ses.player
    top = ses.world.column_top(q, r)
    x, z = center(q, r)
    p.x, p.z = x, z
    p.y = (top + 1 + up) * LAYER + 0.001
    p.vx = p.vy = p.vz = 0
    return top


def realms(app, log, shot, look_at, settled, arg):
    """Visit one spot of each realm, plus a skerry field and a waterfall."""
    seed = seed_from_text(arg or 'realm-tour')
    yield 0.5
    app.create_sky('Realm Tour', seed, arg, 'dreamer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    p.drifting = True
    app.hide_hud = True
    g = ses.gen
    step = 6
    n = 260
    qs = (np.arange(n) - n // 2) * step
    Q, R = np.meshgrid(qs, qs, indexing='ij')
    c = g.columns(Q, R)
    targets = []
    for realm in range(len(MT.REALMS)):
        m = (c['realm'] == realm) & c['land'] & (c['e'] > 0.12) & ~c['skerry']
        idx = np.argwhere(m)
        if len(idx):
            d = (Q[m] ** 2 + R[m] ** 2)
            i = idx[np.argmin(d)]
            targets.append((MT.REALMS[realm].replace(' ', '_').lower(), int(Q[tuple(i)]), int(R[tuple(i)]), int(c['top'][tuple(i)])))
    f = np.argwhere(c['fall'])
    if len(f):
        i = f[np.argmin(np.abs(Q[c['fall']]) + np.abs(R[c['fall']]))]
        targets.append(('waterfall', int(Q[tuple(i)]), int(R[tuple(i)]), int(c['top'][tuple(i)])))
    log('targets', targets)
    for k, (name, q, r, top) in enumerate(targets):
        tx, tz = center(q, r)
        ang = k * 1.3
        dist = 34 if name != 'waterfall' else 40
        p.x, p.z = tx + math.cos(ang) * dist, tz + math.sin(ang) * dist
        p.y = (top + (16 if name != 'waterfall' else 4)) * LAYER
        look_at(p, tx, (top - (0 if name != 'waterfall' else 20)) * LAYER, tz)
        ses.phase = [0.05, 0.12, 0.2, 0.3, 0.08, 0.15, 0.25, 0.6, 0.1][k % 9]
        yield 0.3
        yield settled()
        yield 1.0
        yield shot('realm_' + name)
    # high overview
    q, r = cell_at(p.x, p.z)
    p.y += 50
    p.pitch = -30
    ses.phase = 0.28
    yield settled()
    yield 1.0
    yield shot('realm_overview')


def perf(app, log, shot, look_at, settled, arg):
    import cProfile, pstats, io, time
    seed = seed_from_text('perf')
    yield 0.5
    app.create_sky('Perf', seed, '', 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    yield settled()
    app.test_input = {'fwd': 1, 'hurry': True}
    pr = cProfile.Profile()
    pr.enable()
    t0 = time.perf_counter()
    yield 8.0
    pr.disable()
    ft = app.frame_times[-60:]
    log('fps', len(ft) / sum(ft))
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(22)
    log(s.getvalue())
    yield shot('perf_view')


def seeds(app, log, shot, look_at, settled, arg):
    """Overviews of several random seeds (to show how different skies feel)."""
    from .noise import random_seed
    yield 1.0
    for k in range(6):
        seed = random_seed()
        app.create_sky(f'Seed {k}', seed, '', 'dreamer')
        yield lambda: app.mode == 'game'
        ses = app.session
        p = ses.player
        p.drifting = True
        app.hide_hud = True
        p.y += 22
        p.pitch = -24
        ses.phase = [0.05, 0.2, 0.3, 0.1, 0.62, 0.15][k]
        yield settled()
        yield 1.0
        log('seed', k, seed)
        yield shot(f'seed_{k}')
        app.hide_hud = False
        app.quit_to_title()
        yield 0.5


def _find(ses, mats, radius=14, ylo=-3, yhi=8):
    p = ses.player
    q0, r0 = cell_at(p.x, p.z)
    y0 = math.floor(p.y / LAYER)
    best = None
    for a, b in spiral(q0, r0, radius):
        for y in range(y0 + ylo, y0 + yhi):
            if ses.world.get(a, b, y) in mats:
                return (a, b, y)
    return best


def _aim(look_at, ses, cell):
    q, r, y = cell
    x, z = center(q, r)
    look_at(ses.player, x, (y + 0.5) * LAYER, z)


def _stand_near(ses, cell, look_at, dist=2):
    """Stand on solid ground a couple of cells from a target cell, looking at it."""
    q, r, y = cell
    for k in (dist, dist + 1, 1, dist + 2):
        for a, b in ring(q, r, k):
            top = ses.world.column_top(a, b)
            if top is None or top < 0 or abs(top + 1 - y) > 3:
                continue
            if ses.world.get(a, b, top + 1) not in (0, M['petals']) or ses.world.get(a, b, top + 2) != 0 or ses.world.get(a, b, top + 3) != 0:
                continue
            p = ses.player
            p.x, p.z = center(a, b)
            p.y = (top + 1) * LAYER + 0.001
            p.vx = p.vy = p.vz = 0
            _aim(look_at, ses, cell)
            return True
    return False


def v11(app, log, shot, look_at, settled, arg):
    seed = seed_from_text(arg or 'clover-lantern-3')
    yield 1.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 0.5
    yield shot('00_title')
    app.set_screen(S.NewSkyScreen(S.SkiesScreen(app)))
    app.menu.name = 'Clover Lantern'
    app.menu.seed = arg or 'clover-lantern-3'
    yield 0.4
    yield shot('01_new_sky')
    app.create_sky('Clover Lantern', seed, arg or 'clover-lantern-3', 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    yield 1.0
    yield shot('10_spawn')
    log('spawn', p.x, p.y, p.z, 'mobs', len(ses.mobs))
    # --- mine a tree by hand
    wood = _find(ses, (M['heartwood'],), 30, -2, 6)
    log('wood', wood)
    if wood and _stand_near(ses, wood, look_at, 2):
        yield settled()
        yield 0.3
        app.test_input = {'gather': True, 'hold': True}
        yield 1.0
        yield shot('11_mining_wood')
        for _ in range(60):
            yield 0.1
            if ses.inv.count(M['heartwood']) >= 1 and not ses.drops:
                break
        app.test_input = {}
        yield 0.6
        for dr in list(ses.drops):
            p.x, p.z = dr.x, dr.z
            yield 0.5
        yield 0.5
        log('heartwood', ses.inv.count(M['heartwood']), 'drops', len(ses.drops))
        yield shot('12_mined_wood')
    # --- craft: backpack with planks
    ses.give(M['heartwood'], 6, quiet=True)
    app.set_screen(IU.BackpackScreen())
    yield 0.3
    rec = next(r for r in I.RECIPES if r[1][0] == M['planks'])
    app.menu.fill(app, rec)
    yield 0.4
    yield shot('13_backpack_craft')
    app.menu.escape(app)
    # give a decent kit for the rest of the tour
    for iid, n in ((M['planks'], 40), (I.STICK.id, 12), (M['stone'], 30), (I.EMBERITE.id, 10), (M['verdigris_ore'], 6),
                   (M['tinker_bench'], 1), (M['kiln'], 1), (M['chest'], 1), (M['glowstick'], 12), (M['glass'], 12),
                   (I.FLUFF.id, 6), (M['bedroll'], 1)):
        ses.give(iid, n, quiet=True)
    ses.give(I.TOOLS[('pick', 1)].id, 1, quiet=True)
    app.set_screen(IU.CraftScreen(3))
    yield 0.3
    rec = next(r for r in I.RECIPES if r[1][0] == I.TOOLS[('pick', 1)].id)
    app.menu.fill(app, rec)
    yield 0.4
    yield shot('14_bench_craft')
    app.menu.escape(app)
    yield 0.3
    # --- build a little camp: bench, kiln, chest, glowsticks
    q0, r0 = cell_at(p.x, p.z)
    camp = (q0, r0)
    top = ses.world.column_top(q0, r0)
    y = top + 1
    placed = []
    for (dq, dr), mat in zip(DIRS, (M['tinker_bench'], M['kiln'], M['chest'], M['glowstick'], M['bedroll'], M['lumen_lamp'])):
        a, b = q0 + dq * 2, r0 + dr * 2
        t = ses.world.column_top(a, b)
        if t is not None and t >= 0 and ses.world.get(a, b, t + 1) in (0, M['petals']):
            from .hexgrid import DIR_NORMALS
            ax, az = center(a, b)
            vx, vz = np.subtract(center(q0 - 5, r0 + 3), (ax, az))
            face = max(range(6), key=lambda d: DIR_NORMALS[d][0] * vx + DIR_NORMALS[d][1] * vz)
            ses.world.set(a, b, t + 1, mat, face if mat in (M['tinker_bench'], M['kiln'], M['chest']) else 0, now=True)
            placed.append((a, b, t + 1, mat))
            if mat == M['chest']:
                from .inventory import Inventory
                ses.chests[f'{a},{b},{t + 1}'] = Inventory(27)
                ses.chests[f'{a},{b},{t + 1}'].add(I.AETHERITE.id, 3)
                ses.chests[f'{a},{b},{t + 1}'].add(M['planks'], 20)
            if mat == M['kiln']:
                from .inventory import Inventory
                ses.kilns[f'{a},{b},{t + 1}'] = {'slots': Inventory(3), 'burn': 5.0, 'burn_max': 5.0, 'prog': 0.0}
                ses.kilns[f'{a},{b},{t + 1}']['slots'].slots = [[M['verdigris_ore'], 5, 0], [I.EMBERITE.id, 4, 0], None]
    log('placed', placed)
    p.pitch = -25
    p.yaw = (p.yaw + 180) % 360
    yield settled()
    yield 0.5
    # back up and look at the camp
    p.x, p.z = center(q0 - 5, r0 + 3)
    p.drifting = True
    p.y = (y + 3) * LAYER
    look_at(p, *center(q0, r0)[:1], (y + 0.3) * LAYER, center(q0, r0)[1])
    x0, z0 = center(q0, r0)
    look_at(p, x0, (y + 0.2) * LAYER, z0)
    ses.select(6)
    yield settled()
    yield 1.0
    yield shot('20_camp')
    p.drifting = False
    _stand(ses, q0, r0)
    for (a, b, yy, mat) in placed:
        if mat == M['kiln']:
            ses.use_block(a, b, yy, mat)
            yield 1.5
            yield shot('21_kiln')
            app.menu.escape(app)
        if mat == M['chest']:
            ses.use_block(a, b, yy, mat)
            yield 0.4
            yield shot('22_chest')
            app.menu.escape(app)
    # --- creatures
    ses.mobs = []
    for kind in ('woolhop', 'woolhop', 'pebblebeak', 'mossback', 'pebblebeak'):
        ses._try_spawn(False, kind=kind, near=True)
    yield 2.0
    if ses.mobs:
        m0 = min(ses.mobs, key=lambda m: math.hypot(m.x - p.x, m.z - p.z))
        mx, mz = m0.x, m0.z
        dx, dz = p.x - mx, p.z - mz
        dd = math.hypot(dx, dz) or 1
        p.x, p.z = mx + dx / dd * 4, mz + dz / dd * 4
        p.drifting = True
        p.y = m0.y + 1.6
        for m in ses.mobs:
            m.think = 99
            m.walking = False
        look_at(p, mx, m0.y + 0.3, mz)
    yield 0.3
    yield shot('30_creatures')
    p.drifting = False
    log('mobs', [(m.kind, round(m.x, 1), round(m.z, 1)) for m in ses.mobs])
    # hit a woolhop until it drops something
    ses.select(0)
    ses.inv.slots[0] = [I.TOOLS[('blade', 2)].id, 1, I.TOOLS[('blade', 2)].uses]
    for _ in range(10):
        wl = [m for m in ses.mobs if m.kind == 'woolhop']
        if not wl:
            break
        m0 = wl[0]
        look_at(p, m0.x, m0.y + 0.5, m0.z)
        if math.hypot(m0.x - p.x, m0.z - p.z) > 3:
            p.x += (m0.x - p.x) * 0.6
            p.z += (m0.z - p.z) * 0.6
        app.test_input = {'gather': True, 'hold': True}
        yield 0.5
    app.test_input = {}
    yield 0.4
    log('drops after hunt', [(I.get(d.iid).name, d.count) for d in ses.drops])
    yield shot('31_drops')
    for dr in list(ses.drops):
        p.x, p.z = dr.x, dr.z
        p.y = max(p.y, dr.y)
        yield 0.4
    yield 1.0
    log('inv fluff', ses.inv.count(I.FLUFF.id), 'meat', ses.inv.count(I.HOPMEAT.id))
    # --- a cave: find an enclosed air pocket deep inside the island
    found = None
    q0, r0 = cell_at(p.x, p.z)
    for a, b in spiral(q0, r0, 40):
        top = ses.world.column_top(a, b)
        if top is None or top < 20:
            continue
        for yy in range(top - 4, top - 40, -1):
            if ses.world.get(a, b, yy) == 0 and all(MT.OPAQUE[max(0, ses.world.get(a, b, yy - k))] for k in (1, 2, 3, 4, 5)) \
                    and ses.world.get(a, b, yy + 1) == 0 and ses.world.get(a, b, yy + 2) == 0:
                # enclosed? solid somewhere above
                rock = (M['stone'], M['loam'], M['mossrock'], M['clay'], M['sand'], M['basalt'], M['rosestone'], M['turf']) + tuple(MT.ORES)
                if sum(1 for k in range(yy + 3, top + 1) if ses.world.get(a, b, k) in rock) >= 4:
                    ores = sum(1 for c, d in spiral(a, b, 5) for k in range(yy - 2, yy + 5) if ses.world.get(c, d, k) in MT.ORES)
                    if ores >= 3:
                        found = (a, b, yy, ores)
                        break
        if found:
            break
    log('cave', found)
    if found:
        a, b, yy, _ = found
        p.x, p.z = center(a, b)
        p.y = yy * LAYER + 0.001
        p.drifting = False
        # look at the nearest ore
        best = None
        for c, d in spiral(a, b, 5):
            for k in range(yy - 2, yy + 5):
                if ses.world.get(c, d, k) in MT.ORES:
                    best = (c, d, k)
                    break
            if best:
                break
        if best:
            _aim(look_at, ses, best)
        nb = ses.world.get(a + 1, b, yy)
        ses.world.set(a, b - 1, yy, M['glowstick'], now=True) if ses.world.get(a, b - 1, yy) == 0 and MT.SOLID[max(0, ses.world.get(a, b - 1, yy - 1))] else None
        ses.select(1)
        yield settled()
        yield 1.0
        yield shot('40_cave')
    # --- mountains vista
    q0, r0 = cell_at(p.x, p.z)
    best, bt = None, -1
    for a, b in spiral(q0, r0, 60)[::7]:
        t = ses.world.column_top(a, b)
        if t is not None and t > bt:
            best, bt = (a, b), t
    log('highest', best, bt)
    # --- dusk with gloomlings
    ses.phase = 0.5
    p.drifting = False
    _stand(ses, camp[0], camp[1])
    yield settled()
    ses.mobs = []
    for _ in range(4):
        ses._try_spawn(True, kind='gloomling', near=True)
    ses._try_spawn(True, kind='brute', near=True)
    for i, m in enumerate(ses.mobs):
        ang = math.radians(p.yaw + (i - 2) * 22)
        m.x, m.z = p.x + math.sin(ang) * (6 + i % 2), p.z - math.cos(ang) * (6 + i % 2)
        m.y = p.y + 2
    yield 0.6
    hs = [m for m in ses.mobs if m.hostile]
    if hs:
        look_at(p, hs[2 % len(hs)].x, p.y + 0.6, hs[2 % len(hs)].z)
    yield 0.2
    yield shot('50_dusk_gloomlings')
    for _ in range(5):
        yield 0.5
        log('gl', round(ses.phase, 3), [(m.kind, round(math.hypot(m.x - p.x, m.z - p.z), 2), round(m.y - p.y, 2), round(m.fade, 2), m.dead) for m in ses.mobs if m.hostile])
    log('hp after gloom', ses.hp)
    yield shot('51_bumped')
    # --- dev mode
    ses.set_dev(True)
    ses.mobs = [m for m in ses.mobs if not m.hostile]
    ses.phase = 0.12
    p.drifting = True
    p.y += 30
    p.pitch = -30
    yield settled()
    yield 1.0
    yield shot('60_dev_fly')
    app.set_screen(IU.AdminScreen())
    yield 0.4
    yield shot('61_admin_panel')
    app.set_screen(None)
    # fill a glass dome-ish box with commands
    q0, r0 = cell_at(p.x, p.z)
    t = ses.world.column_top(q0, r0) or 60
    ses.pos1 = (q0 - 3, r0 - 3, t + 1)
    ses.pos2 = (q0 + 3, r0 + 3, t + 6)
    ses.command('/fill glass')
    ses.pos1 = (q0 - 2, r0 - 2, t + 1)
    ses.pos2 = (q0 + 2, r0 + 2, t + 5)
    ses.command('/clear')
    ses.command('/give lumen lamp 4')
    ses.world.set(q0, r0, t + 1, M['lumen_lamp'], now=True)
    p.y = (t + 14) * LAYER
    x0, z0 = center(q0, r0)
    p.x, p.z = x0 + 9, z0 + 9
    look_at(p, x0, (t + 3) * LAYER, z0)
    yield settled()
    yield 1.0
    yield shot('62_fill_glass')
    if best:
        p.x, p.z = center(best[0] + 22, best[1] + 8)
        p.y = (bt - 6) * LAYER
        look_at(p, *center(*best)[:1], bt * LAYER, center(*best)[1])
        x0, z0 = center(*best)
        look_at(p, x0, (bt - 12) * LAYER, z0)
        app.hide_hud = True
        yield settled()
        yield 1.0
        yield shot('63_mountain')
        app.hide_hud = False
    ses.set_dev(False)
    # --- journal + faded screen
    app.set_screen(S.JournalScreen(tab=1))
    yield 0.4
    yield shot('70_journal_recipes')
    app.set_screen(S.JournalScreen(tab=4))
    yield 0.3
    yield shot('71_journal_controls')
    app.set_screen(None)
    ses.damage(50, 'gloomling')
    yield 0.4
    yield shot('72_faded')
    ses.respawn()
    app.set_screen(None)
    yield 0.5
    ses.save()
    app.quit_to_title()
    yield 1.0
    folder = app.thumb_cache and list(app.thumb_cache)[0]
    from .storage import SkyStorage
    sk = SkyStorage.list_skies(app.skies_dir)[0]
    app.open_sky(sk['folder'])
    yield lambda: app.mode == 'game'
    log('reloaded inv', [(I.get(s[0]).name, s[1]) for s in app.session.inv.slots if s][:12], 'chests', len(app.session.chests))
    yield 1.0
    yield shot('80_reloaded')


def vista(app, log, shot, look_at, settled, arg):
    """Far-view check: wait for LOD terrain, then a high shot and an eye-level shot."""
    import time, threading
    gaps = []

    def probe():          # how long can another thread (like the audio feeder) be starved of the GIL?
        last = time.perf_counter()
        while len(gaps) < 100000:
            time.sleep(0.01)
            now = time.perf_counter()
            gaps.append(now - last - 0.01)
            last = now
    threading.Thread(target=probe, daemon=True).start()
    yield 0.5
    app.create_sky('Vista', seed_from_text(arg or 'vista'), arg or 'vista', 'dreamer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    t0 = time.perf_counter()
    yield lambda: ses.world.busy() == 0 and ses.world.busy_lod() == 0 and len(ses.world.lod) > 10 or time.perf_counter() - t0 > 60
    yield 1.0
    from . import fast as _f
    log('numba', _f.ENABLED, 'audio', app.audio.backend, app.audio.enabled, 'music', app.audio.music_status,
        sorted(app.audio.music), {k: round(v[1], 3) for k, v in app.audio.chan.items()})
    log('lod groups', len(ses.world.lod), 'chunks', len(ses.world.chunks), 'wait', time.perf_counter() - t0,
        'lod ms', 1000 * sum(ses.world.timings['lod']) / max(1, len(ses.world.timings['lod'])),
        'gen ms', 1000 * sum(ses.world.timings['gen']) / max(1, len(ses.world.timings['gen'])))
    app.hide_hud = True
    # close-up texture shots: stone/ore cliff and a meadow with trees
    for name, mats in (('tex_stone', (M['stone'], M['mossrock'], M['basalt'], M['rosestone'])), ('tex_meadow', (M['turf'],))):
        cell = None
        q0, r0 = cell_at(p.x, p.z)
        for a, b in spiral(q0, r0, 70):
            tt = ses.world.column_top(a, b)
            if tt is not None and tt > 0 and ses.world.get(a, b, tt) in mats:
                cell = (a, b, tt)
                break
        if cell and _stand_near(ses, cell, look_at, 4):
            p.drifting = True
            p.y += 1.2
            _aim(look_at, ses, cell)
            p.pitch = max(-25, min(p.pitch, -8))
            yield settled()
            yield 1.0
            yield shot(name)
    p.pitch = -4
    yield 3.0
    ft = app.frame_times[-60:]
    log('fps eye', len(ft) / sum(ft))
    app.hide_hud = True
    yield shot('vista_eye')
    p.drifting = True
    p.y += 30
    p.pitch = -14
    yield 3.0
    ft = app.frame_times[-60:]
    log('fps high', len(ft) / sum(ft))
    g = sorted(gaps)
    log('gil stall ms max %.0f p99 %.0f, >250ms: %d' % (1000 * g[-1], 1000 * g[int(len(g) * 0.99)], sum(1 for x in g if x > 0.25)))
    yield shot('vista_high')


def blocks(app, log, shot, look_at, settled, arg):
    """Close-up of the functional blocks, each facing the camera."""
    from .hexgrid import DIR_NORMALS
    yield 0.5
    app.create_sky('Blocks', seed_from_text(arg or 'clover-lantern-3'), arg or 'clover-lantern-3', 'dreamer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    q0, r0 = cell_at(p.x, p.z)
    t0 = math.floor(p.y / LAYER + 0.01) - 1
    log('stage', q0, r0, t0, ses.world.column_top(q0, r0))
    # flatten a little stage
    for a, b in spiral(q0, r0, 7):
        for yy in range(t0 + 1, t0 + 8):
            ses.world.set(a, b, yy, 0, now=False)
        for yy in range(t0 - 3, t0 + 1):
            ses.world.set(a, b, yy, M['turf'] if yy == t0 else M['loam'], now=False)
    ses.phase = 0.12
    row = [(M['tinker_bench'], 0), (M['kiln'], 8), (M['chest'], 0), (M['lantern'], 0), (M['bedroll'], 0), (M['glowstick'], 0),
           (M['lumen_lamp'], 0), (M['bricks'], 0), (M['planks'], 0), (M['polished_stone'], 0)]
    cam = center(q0, r0 + 3)
    for i, (mat, extra) in enumerate(row):
        a, b = q0 - 5 + i, r0
        ax, az = center(a, b)
        vx, vz = 0.0, 1.0
        face = max(range(6), key=lambda d: DIR_NORMALS[d][0] * vx + DIR_NORMALS[d][1] * vz)
        ses.world.set(a, b, t0 + 1, mat, (face | extra) if mat in (M['tinker_bench'], M['kiln'], M['chest']) else 0, now=False)
    app.hide_hud = True
    yield settled()
    for k, (cq_, name) in enumerate(((q0 - 4, 'blocks_a'), (q0 - 0.5, 'blocks_b'), (q0 + 3, 'blocks_c'))):
        tx, tz = center(cq_, r0)
        p.drifting = True
        p.x, p.z = tx, tz + 3.6
        p.y = (t0 + 2.2) * LAYER
        look_at(p, tx, (t0 + 1.3) * LAYER, tz)
        log('cam', p.x, p.y, p.z, 'target', tx, tz)
        yield 1.5
        yield shot(name)



def phase1(app, log, shot, look_at, settled, arg):
    """1.4 Phase 1: scale, doors, ladders, crouch, leaves, kiln counts, rain, tools, mobs, fall-in."""
    from .hexgrid import DIR_NORMALS, DIRS
    from .inventory import Inventory
    from .entities import Mob
    from .config import HEIGHT, CROUCH_HEIGHT, CROUCH_EYE, FALL_RESPAWN_LAYERS, EYE
    from .ui import inventory_ui as IU

    yield 0.4
    app.create_sky('Phase1', seed_from_text(arg or 'tide-foundation'), arg or 'tide-foundation', 'dreamer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    q0, r0 = cell_at(p.x, p.z)
    t0 = math.floor(p.y / LAYER + 0.01) - 1
    log('stage', q0, r0, t0, 'height', HEIGHT, 'layer', LAYER)

    # a solid pad so we never look down into a cave
    for a, b in spiral(q0, r0, 12):
        for yy in range(t0 + 1, t0 + 18):
            ses.world.set(a, b, yy, 0, now=False)
        for yy in range(t0 - 8, t0 + 1):
            ses.world.set(a, b, yy, M['turf'] if yy == t0 else M['loam'], now=False)

    # a small plank hut: walls on three sides, door opening toward +r (camera)
    door_q, door_r = q0 - 3, r0
    hut = [
        (door_q - 1, door_r - 1), (door_q, door_r - 1), (door_q + 1, door_r - 1),
        (door_q - 1, door_r),                           (door_q + 1, door_r),
        (door_q - 1, door_r + 1),                       (door_q + 1, door_r + 1),
    ]
    for a, b in hut:
        ses.world.set(a, b, t0 + 1, M['planks'], now=False)
        ses.world.set(a, b, t0 + 2, M['planks'], now=False)
        ses.world.set(a, b, t0 + 3, M['planks'], now=False)  # roof / lintel
    # roof over the interior too
    for a, b in ((door_q, door_r), (door_q, door_r + 1)):
        ses.world.set(a, b, t0 + 3, M['planks'], now=False)
    cx_, cz_ = center(door_q, door_r)
    camx, camz = center(door_q, door_r + 4)
    vx, vz = camx - cx_, camz - cz_
    face = max(range(6), key=lambda d: DIR_NORMALS[d][0] * vx + DIR_NORMALS[d][1] * vz)
    ses.world.set(door_q, door_r, t0 + 1, M['door'], face, now=False)
    ses.world.set(door_q, door_r, t0 + 2, M['door'], face | 16, now=False)
    # a second, open door standing in a one-block frame to the right
    oq, or_ = q0 - 1, r0
    ses.world.set(oq - 1, or_, t0 + 1, M['planks'], now=False)
    ses.world.set(oq - 1, or_, t0 + 2, M['planks'], now=False)
    ses.world.set(oq + 1, or_, t0 + 1, M['planks'], now=False)
    ses.world.set(oq + 1, or_, t0 + 2, M['planks'], now=False)
    ses.world.set(oq, or_, t0 + 3, M['planks'], now=False)
    ses.world.set(oq, or_, t0 + 1, M['door'], face | 8, now=False)
    ses.world.set(oq, or_, t0 + 2, M['door'], face | 8 | 16, now=False)

    # stone tower with a ladder on the camera-facing side
    wq, wr = q0 + 4, r0
    for yy in range(t0 + 1, t0 + 9):
        ses.world.set(wq, wr, yy, M['stone'], now=False)
    ses.world.set(wq, wr + 1, t0 + 8, M['stone'], now=False)
    cam2x, cam2z = center(wq, wr + 4)
    best, best_d = None, 1e9
    for d, (dq, dr) in enumerate(DIRS):
        aq, ar = wq + dq, wr + dr
        ax, az = center(aq, ar)
        dist = (ax - cam2x) ** 2 + (az - cam2z) ** 2
        if dist < best_d:
            best_d, best = dist, (aq, ar)
    lq, lr = best
    face_l = 0
    for d, (dq, dr) in enumerate(DIRS):
        if (lq + dq, lr + dr) == (wq, wr):
            face_l = d
            break
    for yy in range(t0 + 1, t0 + 9):
        ses.world.set(lq, lr, yy, M['ladder'], face_l, now=False)

    # a modest tree (trunk + a tight canopy) out on the pad
    tq, tr = q0 + 1, r0 - 5
    for yy in range(t0 + 1, t0 + 5):
        ses.world.set(tq, tr, yy, M['heartwood'], now=False)
    for a, b in spiral(tq, tr, 1):
        ses.world.set(a, b, t0 + 5, M['canopy'], now=False)
        if (a, b) != (tq, tr):
            ses.world.set(a, b, t0 + 4, M['canopy'], now=False)
    ses.world.set(tq, tr, t0 + 6, M['canopy'], now=False)

    # kiln with two stacks of 16 (the old bug made those counts share one label)
    kq, kr = q0 + 2, r0
    kface = max(range(6), key=lambda d: DIR_NORMALS[d][0] * (camx - center(kq, kr)[0]) + DIR_NORMALS[d][1] * (camz - center(kq, kr)[1]))
    ses.world.set(kq, kr, t0 + 1, M['kiln'], kface | 8, now=False)
    kinv = Inventory(3)
    kinv.slots[0] = [M['sand'], 16, 0]
    kinv.slots[1] = [I.EMBERITE.id, 16, 0]
    kinv.slots[2] = [M['glass'], 16, 0]
    ses.kilns[f'{kq},{kr},{t0 + 1}'] = {'slots': kinv, 'burn': 0.0, 'burn_max': 5.0, 'prog': 0.0}

    hx, hz = center(q0 + 1, r0 + 2)
    ses.mobs = [Mob('woolhop', hx, (t0 + 1) * LAYER + 0.01, hz)]
    ses.mobs[0].walking = False
    ses.mobs[0].think = 99
    ses.mobs[0].vx = ses.mobs[0].vz = 0

    pick = I.TOOLS[('pick', 2)]
    ses.inv.slots[0] = [pick.id, 1, pick.uses]
    ses.hot = 0
    ses.phase = 0.16
    ses.dev = False
    p.drifting = False
    p.noclip = False
    ses.hold = True          # don't walk off while we pose
    app.hide_hud = False

    yield settled()
    ses.toasts = []
    p.update = lambda *a, **k: None   # keep posed eyes and feet still

    def stand_on(x, z, y_off=0.01):
        p.drifting = False
        p.x, p.z = x, z
        p.y = (t0 + 1) * LAYER + y_off
        p.vx = p.vy = p.vz = 0
        p.crouching = False
        p._eye = EYE

    # --- 01 scale: mid shot of the 2-block doorway, standing eye height
    dx, dz = center(door_q, door_r)
    stand_on(dx + 0.4, dz + 5.6)
    look_at(p, dx, (t0 + 2.0) * LAYER, dz)
    yaw_door, pitch_door = p.yaw, p.pitch
    yield 0.6
    yield shot('01_scale_door')

    # --- 02 crouch: same place and look, only the camera drops
    p.crouching = True
    p._eye = CROUCH_EYE
    p.yaw, p.pitch = yaw_door, pitch_door
    yield 0.4
    yield shot('02_crouch_door')
    p.crouching = False
    p._eye = EYE

    # --- 03 both doors, a little off to the side
    stand_on(*center(q0 - 2, r0 + 5))
    tx, tz = center(q0 - 2, r0)
    look_at(p, tx, (t0 + 1.7) * LAYER, tz)
    yield 0.8
    yield shot('03_doors')

    # --- 04 ladder close-up, mid climb
    lx, lz = center(lq, lr)
    wx, wz = center(wq, wr)
    p.drifting = False
    p.x, p.z = lx, lz
    p.y = (t0 + 4) * LAYER + 0.15
    look_at(p, wx, (t0 + 5.6) * LAYER, wz)
    yield 0.7
    yield shot('04_ladder')

    # --- 05 whole tower + ladder
    stand_on(*center(wq, wr + 5), y_off=LAYER * 1.2)
    p.y = (t0 + 2.2) * LAYER
    look_at(p, wx, (t0 + 4.6) * LAYER, wz)
    yield 0.8
    yield shot('05_ladder_wall')

    # --- 06 / 07 leaf decay, same camera
    tx, tz = center(tq, tr)
    p.drifting = True
    p.x, p.z = tx + 1.5, tz + 8.5
    p.y = (t0 + 3.4) * LAYER
    look_at(p, tx, (t0 + 4.0) * LAYER, tz)
    p.drifting = False
    yield 0.9
    yield shot('06_leaves_before')
    for yy in range(t0 + 1, t0 + 5):
        ses.world.set(tq, tr, yy, 0, now=True)
    ses.sim.wake_leaves(tq, tr, t0 + 4, 0.0)
    for _ in range(50):
        ses.sim.step(0.2, 0.0, budget=400)
    yield settled()
    yield 0.5
    yield shot('07_leaves_after')

    # --- 08 kiln counts (16 and 16 must both be visible)
    kinv.slots[0] = [M['sand'], 16, 0]
    kinv.slots[1] = [I.EMBERITE.id, 16, 0]
    kinv.slots[2] = [M['glass'], 16, 0]
    ses.kilns[f'{kq},{kr},{t0 + 1}']['burn'] = 0.0
    ses.kilns[f'{kq},{kr},{t0 + 1}']['prog'] = 0.0
    app.set_screen(IU.KilnScreen(ses.kilns[f'{kq},{kr},{t0 + 1}']))
    yield 0.8
    yield shot('08_kiln_counts')
    app.set_screen(None)

    # --- 09 rain against the sky
    ses.weather = 'rain'
    ses.time = 4.0
    p.drifting = False
    stand_on(*center(q0, r0 + 2))
    # look just above the horizon
    hx2, hz2 = center(q0, r0 - 8)
    look_at(p, hx2, (t0 + 6) * LAYER, hz2)
    yield 1.1
    yield shot('09_rain')
    ses.weather = 'clear'

    # --- 10 held tool aimed at the kiln
    ses.swing = 0.28
    stand_on(*center(kq, kr + 3))
    look_at(p, *center(kq, kr), (t0 + 1.45) * LAYER)
    # look_at arg order is (p, tx, ty, tz)
    look_at(p, center(kq, kr)[0], (t0 + 1.45) * LAYER, center(kq, kr)[1])
    yield 0.7
    yield shot('10_held_tool')
    ses.swing = 0

    # --- 11 woolhop standing still
    stand_on(hx, hz + 3.4)
    look_at(p, hx, (t0 + 1) * LAYER + 0.65, hz)
    yield 0.8
    yield shot('11_mob')

    # --- 12 fall-in from high above the pad
    p.drifting = True
    p.x, p.z = center(q0, r0)
    p.y = (t0 + FALL_RESPAWN_LAYERS) * LAYER + 0.01
    look_at(p, center(q0, r0)[0], (t0 + 1) * LAYER, center(q0, r0)[1])
    p.pitch = -72
    yield 0.9
    yield shot('12_fall_respawn')

    log('phase1 tour finished')


def phase2a(app, log, shot, look_at, settled, arg):
    """1.4 Phase 2a: slider screen, new biomes, thick islands, caves."""
    from .hexgrid import spiral
    from .ui.screens import NewSkyScreen, TitleScreen
    from . import gensettings as GS
    from . import materials as MT

    yield 0.5
    app.set_screen(NewSkyScreen(TitleScreen()))
    yield 0.8
    yield shot('00_sliders')

    seed = int(arg) if (arg or '').isdigit() else 5
    app.create_sky('Phase2a', seed, str(seed), 'dreamer', gen=GS.defaults())
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None
    log('spawn', cell_at(p.x, p.z), 'seed', seed)

    # locate nearby examples of each landscape
    g = ses.gen
    Q, R = np.mgrid[-90:90:2, -90:90:2]
    col = g.columns(Q, R)
    land = col['land'] & ~col['skerry']
    found = {}
    for a in range(Q.shape[0]):
        for b in range(Q.shape[1]):
            if not land[a, b]:
                continue
            rid = int(col['realm'][a, b])
            rec = (int(Q[a, b]), int(R[a, b]), int(col['top'][a, b]), int(col['bottom'][a, b]))
            if rid not in found:
                found[rid] = rec
            else:
                # prefer closer to origin
                if rec[0] * rec[0] + rec[1] * rec[1] < found[rid][0] ** 2 + found[rid][1] ** 2:
                    found[rid] = rec
    log('biomes found', {MT.REALMS[k]: found[k][:2] for k in sorted(found)})

    def pose(q, r, top, dist=9.0, up=3.2, look_y=1.4):
        x, z = center(q, r)
        p.x, p.z = x, z + dist
        p.y = (top + up) * LAYER
        look_at(p, x, (top + look_y) * LAYER, z)

    # several new biomes, plus a familiar one for contrast
    wanted = [
        (10, '01_lavender_downs'),
        (9, '02_cedar_highlands'),
        (8, '03_saltwind_flats'),
        (11, '04_cinder_spires'),
        (12, '05_chalk_barrens'),
        (13, '06_starfall_veil'),
        (14, '07_cloudstep_isles'),
        (15, '08_verdigris_canyons'),
        (0, '09_meadow_isles'),
    ]
    for rid, name in wanted:
        if rid not in found:
            log('missing biome', MT.REALMS[rid])
            continue
        q, r, top, bot = found[rid]
        pose(q, r, top)
        log('shot', name, MT.REALMS[rid], q, r, 'thick', top - bot)
        yield settled()
        yield 0.7
        yield shot(name)

    # a thick island from the side, mid-height, so you can see the depth
    thickest = max((found[k] for k in found), key=lambda rec: rec[2] - rec[3])
    q, r, top, bot = thickest
    x, z = center(q, r)
    mid = (top + bot) * 0.5
    p.x, p.z = x + 14.0, z + 2.0
    p.y = mid * LAYER
    look_at(p, x, mid * LAYER, z)
    log('thick island', q, r, 'top', top, 'bottom', bot, 'depth', top - bot)
    yield settled()
    yield 0.8
    yield shot('10_thick_island')

    # underside / hanging into the cloud sea
    p.x, p.z = x + 6.0, z + 6.0
    p.y = (bot - 4) * LAYER
    look_at(p, x, (bot + 2) * LAYER, z)
    yield 0.7
    yield shot('11_island_underside')

    # a cave: search loaded cells for a roomy interior void
    cave = None
    pq, pr = cell_at(p.x, p.z)
    # start near the thick island, then spawn
    for origin in ((q, r), cell_at(ses.player.x, ses.player.z) if False else (q, r)):
        for a, b in spiral(origin[0], origin[1], 48):
            topc = ses.world.column_top(a, b)
            if topc is None or topc < 8:
                continue
            # find a run of air under a roof
            for y in range(int(topc) - 3, max(3, int(topc) - 50), -1):
                if (ses.world.get(a, b, y) == 0 and ses.world.get(a, b, y + 1) != 0
                        and ses.world.get(a, b, y - 1) == 0 and ses.world.get(a, b, y - 2) != 0):
                    cave = (a, b, y - 1)
                    break
            if cave:
                break
        if cave:
            break
    if cave:
        cq, cr, cy = cave
        cx, cz = center(cq, cr)
        p.x, p.z = cx, cz
        p.y = cy * LAYER + 0.2
        look_at(p, cx + 4.0, cy * LAYER + 0.4, cz + 2.0)
        log('cave', cave)
        yield settled()
        yield 0.8
        yield shot('12_cave')
    else:
        log('no cave found')

    log('phase2a tour finished')



def phase2b(app, log, shot, look_at, settled, arg):
    """1.4 Phase 2b: block palette, glass, and the three structure families."""
    from .hexgrid import spiral
    from . import gensettings as GS
    from . import structures as ST
    from . import materials as MT

    yield 0.4
    seed = int(arg) if (arg or '').isdigit() else 21
    app.create_sky('Phase2b', seed, str(seed), 'dreamer', gen=GS.defaults())
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None
    q0, r0 = cell_at(p.x, p.z)
    t0 = math.floor(p.y / LAYER + 0.01) - 1
    if t0 < 8:
        t0 = 24
    log('stage', q0, r0, t0)

    # a wide solid pad
    for a, b in spiral(q0, r0, 22):
        for yy in range(t0 + 1, t0 + 18):
            ses.world.set(a, b, yy, 0, now=False)
        for yy in range(t0 - 16, t0 + 1):
            ses.world.set(a, b, yy, M['turf'] if yy == t0 else M['loam'], now=False)

    # ---- block palette (rows of the new roster) ----
    rows = [
        ['cedar_heartwood', 'cedar_planks', 'pale_heartwood', 'pale_planks',
         'dark_heartwood', 'dark_planks', 'thatch', 'shingles'],
        ['cobble', 'slate', 'chalk', 'sandstone', 'cinder', 'starstone', 'salt_block', 'pale_stone'],
        ['polished_stone', 'polished_basalt', 'polished_rosestone', 'polished_slate',
         'polished_chalk', 'polished_sandstone', 'polished_starstone', 'carved_stone'],
        ['stone_bricks', 'basalt_bricks', 'rosestone_bricks', 'chalk_bricks',
         'dusk_bricks', 'lavender_bricks', 'verdigris_bricks', 'snow_bricks'],
        ['stone_tiles', 'clay_tiles', 'starstone_tiles', 'lavender_tiles',
         'verdigris_tiles', 'mosaic', 'wattle', 'heather'],
        ['linen', 'crimson_cloth', 'dusk_cloth', 'packed_earth',
         'ember_lamp', 'aether_lamp', 'verdigris_lamp', 'lumen_lamp'],
        ['stone_slab', 'planks_slab', 'cedar_planks_slab', 'bricks_slab',
         'thatch_slab', 'shingles_slab', 'glass', 'violet_glass'],
    ]
    pq, pr = q0 - 3, r0 - 6
    for i, row in enumerate(rows):
        for j, name in enumerate(row):
            mid = M[name]
            ses.world.set(pq + j, pr - i, t0 + 1, mid, now=False)

    yield settled()
    # elevated three-quarter view of the palette
    tx, tz = center(pq + 3, pr - 3)
    p.x, p.z = tx + 2.0, tz + 11.0
    p.y = (t0 + 7.5) * LAYER
    look_at(p, tx, (t0 + 1.6) * LAYER, tz)
    yield 0.8
    yield shot('00_palette')

    # ---- glass: a clear window looking through to color ----
    gq, gr = q0 + 2, r0 + 6
    # solid pale-stone floor in front and behind so we don't look into a hole
    for a in range(-4, 5):
        for b in range(-3, 3):
            ses.world.set(gq + a, gr + b, t0, M['pale_stone'], now=False)
    for a in range(-3, 4):
        for yy in range(t0 + 1, t0 + 5):
            if abs(a) == 3 or yy == t0 + 4:
                ses.world.set(gq + a, gr, yy, M['pale_planks'], now=False)
            else:
                kind = M['glass'] if a == 0 else (M['violet_glass'] if a > 0 else M['amber_glass'] if a < -1 else M['green_glass'])
                ses.world.set(gq + a, gr, yy, kind, now=False)
    # colorful solid wall a little behind the glass, so the pane has something to show
    for a in range(-2, 3):
        for yy in range(t0 + 1, t0 + 4):
            ses.world.set(gq + a, gr - 2, yy, M['crimson_cloth'] if a < 0 else M['dusk_cloth'] if a > 0 else M['linen'], now=False)
        ses.world.set(gq + a, gr - 2, t0 + 2, M['ember_lamp'] if a == 0 else (M['aether_lamp'] if a == 1 else M['heather']), now=False)
    yield settled()
    tx, tz = center(gq, gr)
    bx, bz = center(gq, gr - 2)
    p.x, p.z = tx, tz + 6.5
    p.y = (t0 + 2.8) * LAYER
    look_at(p, bx, (t0 + 2.2) * LAYER, bz)
    yield 0.8
    yield shot('01_glass')

    # ---- structures, spaced around the pad ----
    # village (intact)
    vq, vr = q0 - 8, r0 + 2
    ST.stamp_world(ses.world, vq, vr, 'village', ST.INTACT, seed=21, realm=0)
    yield settled()
    tx, tz = center(vq, vr)
    p.x, p.z = tx + 2.0, tz + 14.0
    p.y = (t0 + 8.0) * LAYER
    look_at(p, tx, (t0 + 3.0) * LAYER, tz)
    yield 0.9
    yield shot('02_settlement')

    # temple (slightly ruined so it reads as a ruin)
    tq, tr = q0 + 10, r0 + 2
    ST.stamp_world(ses.world, tq, tr, 'temple', ST.RUINED, seed=21, realm=12)
    yield settled()
    tx, tz = center(tq, tr)
    p.x, p.z = tx - 3.0, tz + 15.0
    p.y = (t0 + 9.0) * LAYER
    look_at(p, tx, (t0 + 4.0) * LAYER, tz)
    yield 0.9
    yield shot('03_temple')

    # standing stones (chalk so the pillars read against the sky)
    sq, sr = q0 - 2, r0 - 16
    ST.stamp_world(ses.world, sq, sr, 'standing_stones', ST.OVERGROWN, seed=7, realm=12)
    yield settled()
    tx, tz = center(sq, sr)
    p.x, p.z = tx + 2.0, tz + 16.0
    p.y = (t0 + 9.0) * LAYER
    look_at(p, tx, (t0 + 3.5) * LAYER, tz)
    yield 0.9
    yield shot('04_standing_stones')

    # buried chamber: look down the shaft, then a lower peek inside
    cq, cr_ = q0 + 10, r0 - 10
    ST.stamp_world(ses.world, cq, cr_, 'chamber', ST.INTACT, seed=3, realm=4)
    yield settled()
    tx, tz = center(cq, cr_)
    p.x, p.z = tx + 0.2, tz + 4.2
    p.y = (t0 + 4.4) * LAYER
    look_at(p, tx, (t0 - 3.5) * LAYER, tz)
    yield 0.9
    yield shot('05_chamber')

    # sky boat at a made edge (clear outward cells so it sits off the island)
    bq, br = q0 - 8, r0 - 10
    # carve a drop just past the mooring
    from .hexgrid import DIRS as _DIRS
    # leave land at bq,br and drop cells in +r
    for a in range(-4, 6):
        for b in range(1, 8):
            for yy in range(t0 - 8, t0 + 10):
                ses.world.set(bq + a, br + b, yy, 0, now=False)
    ST.stamp_world(ses.world, bq, br, 'sky_boat', ST.INTACT, seed=5, realm=14)
    yield settled()
    hits = []
    for a in range(-6, 10):
        for b in range(-4, 12):
            for yy in range(t0 - 1, t0 + 8):
                m = ses.world.get(bq + a, br + b, yy)
                if m in (M['linen'], M['dusk_cloth'], M['pale_planks'], M['planks'], M['bedroll']):
                    hits.append((bq + a, br + b, yy))
    log('boat cells', len(hits), hits[:6])
    if hits:
        aq = sum(c[0] for c in hits) / len(hits)
        ar = sum(c[1] for c in hits) / len(hits)
        ay = sum(c[2] for c in hits) / len(hits)
        tx, tz = center(int(round(aq)), int(round(ar)))
        p.x, p.z = tx + 11.0, tz + 6.0
        p.y = (ay + 5.0) * LAYER
        look_at(p, tx, (ay + 0.6) * LAYER, tz)
    else:
        tx, tz = center(bq, br + 2)
        p.x, p.z = tx + 11.0, tz + 6.0
        p.y = (t0 + 7.0) * LAYER
        look_at(p, tx, (t0 + 3.0) * LAYER, tz)
    yield 0.9
    yield shot('06_sky_boat')

    log('phase2b tour finished')



def phase2b_fix(app, log, shot, look_at, settled, arg):
    """Retake glass, standing stones, and the sky boat with cleaner framing."""
    from .hexgrid import spiral
    from . import gensettings as GS
    from . import structures as ST

    yield 0.4
    seed = int(arg) if (arg or '').isdigit() else 21
    app.create_sky('Phase2bFix', seed, str(seed), 'dreamer', gen=GS.defaults())
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None
    q0, r0 = cell_at(p.x, p.z)
    t0 = math.floor(p.y / LAYER + 0.01) - 1
    if t0 < 8:
        t0 = 24
    log('stage', q0, r0, t0)
    for a, b in spiral(q0, r0, 24):
        for yy in range(t0 + 1, t0 + 18):
            ses.world.set(a, b, yy, 0, now=False)
        for yy in range(t0 - 16, t0 + 1):
            ses.world.set(a, b, yy, M['turf'] if yy == t0 else M['loam'], now=False)

    # glass with a windowsill so the floor doesn't read as a hole
    gq, gr = q0, r0
    for a in range(-5, 6):
        for b in range(-3, 4):
            ses.world.set(gq + a, gr + b, t0, M['pale_stone'], now=False)
            ses.world.set(gq + a, gr + b, t0 - 1, M['pale_stone'], now=False)
    for a in range(-3, 4):
        ses.world.set(gq + a, gr, t0 + 1, M['pale_planks'], now=False)  # sill
        for yy in range(t0 + 2, t0 + 5):
            if abs(a) == 3 or yy == t0 + 4:
                ses.world.set(gq + a, gr, yy, M['pale_planks'], now=False)
            else:
                kind = M['glass'] if a == 0 else (M['violet_glass'] if a > 0 else M['amber_glass'] if a < -1 else M['green_glass'])
                ses.world.set(gq + a, gr, yy, kind, now=False)
    for a in range(-2, 3):
        for yy in range(t0 + 1, t0 + 4):
            ses.world.set(gq + a, gr - 2, yy, M['crimson_cloth'] if a < 0 else M['dusk_cloth'] if a > 0 else M['linen'], now=False)
        if a == 0:
            ses.world.set(gq, gr - 2, t0 + 2, M['ember_lamp'], now=False)
    yield settled()
    tx, tz = center(gq, gr)
    bx, bz = center(gq, gr - 2)
    p.x, p.z = tx, tz + 7.0
    p.y = (t0 + 3.0) * LAYER
    look_at(p, bx, (t0 + 2.4) * LAYER, bz)
    yield 0.8
    yield shot('01_glass')

    # standing stones on their own pad, well away, then frame from a found pillar ring
    sq, sr = q0 + 14, r0
    ST.stamp_world(ses.world, sq, sr, 'standing_stones', ST.OVERGROWN, seed=7, realm=12)
    yield settled()
    cols = []
    for a, b in spiral(sq, sr, 6):
        h = 0
        for yy in range(t0 + 1, t0 + 12):
            if ses.world.get(a, b, yy) in (M['carved_stone'], M['chalk'], M['stone'], M['slate'], M['plinth']):
                h += 1
        if h >= 2:
            cols.append((a, b, h))
    log('stone pillars', cols)
    if cols:
        aq = sum(c[0] for c in cols) / len(cols)
        ar = sum(c[1] for c in cols) / len(cols)
    else:
        aq, ar = sq, sr
    tx, tz = center(int(round(aq)), int(round(ar)))
    p.x, p.z = tx + 3.0, tz + 18.0
    p.y = (t0 + 10.0) * LAYER
    look_at(p, tx, (t0 + 3.8) * LAYER, tz)
    yield 0.9
    yield shot('04_standing_stones')

    # sky boat at a carved edge, aim using sail cloth only
    bq, br = q0 - 14, r0
    for a in range(-5, 7):
        for b in range(1, 10):
            for yy in range(t0 - 8, t0 + 12):
                ses.world.set(bq + a, br + b, yy, 0, now=False)
    ST.stamp_world(ses.world, bq, br, 'sky_boat', ST.INTACT, seed=5, realm=14)
    yield settled()
    hits = []
    for a in range(-6, 12):
        for b in range(-1, 12):
            for yy in range(t0 - 1, t0 + 10):
                m = ses.world.get(bq + a, br + b, yy)
                if m in (M['linen'], M['dusk_cloth']):
                    hits.append((bq + a, br + b, yy))
    if not hits:
        for a in range(-6, 12):
            for b in range(0, 12):
                for yy in range(t0, t0 + 6):
                    if ses.world.get(bq + a, br + b, yy) in (M['pale_planks'], M['bedroll']):
                        hits.append((bq + a, br + b, yy))
    log('boat cells', len(hits), hits[:8])
    if hits:
        aq = sum(c[0] for c in hits) / len(hits)
        ar = sum(c[1] for c in hits) / len(hits)
        ay = sum(c[2] for c in hits) / len(hits)
        tx, tz = center(int(round(aq)), int(round(ar)))
        p.x, p.z = tx + 12.0, tz + 3.0
        p.y = (ay + 3.5) * LAYER
        look_at(p, tx, (ay - 0.2) * LAYER, tz)
    yield 0.9
    yield shot('06_sky_boat')
    log('phase2b_fix finished')



def phase2b_boat(app, log, shot, look_at, settled, arg):
    from .hexgrid import spiral
    from . import gensettings as GS
    from . import structures as ST
    yield 0.3
    app.create_sky('Phase2bBoat', 21, '21', 'dreamer', gen=GS.defaults())
    yield lambda: app.mode == 'game'
    ses, p = app.session, app.session.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None
    q0, r0 = cell_at(p.x, p.z)
    t0 = math.floor(p.y / LAYER + 0.01) - 1
    if t0 < 8:
        t0 = 24
    for a, b in spiral(q0, r0, 16):
        for yy in range(t0 + 1, t0 + 14):
            ses.world.set(a, b, yy, 0, now=False)
        for yy in range(t0 - 10, t0 + 1):
            ses.world.set(a, b, yy, M['turf'] if yy == t0 else M['loam'], now=False)
    bq, br = q0, r0
    # drop just past +r
    for a in range(-6, 7):
        for b in range(1, 10):
            for yy in range(t0 - 8, t0 + 12):
                ses.world.set(bq + a, br + b, yy, 0, now=False)
    ST.stamp_world(ses.world, bq, br, 'sky_boat', ST.INTACT, seed=5, realm=14)
    yield settled()
    hits = []
    for a in range(-8, 10):
        for b in range(-4, 12):
            for yy in range(t0 - 1, t0 + 10):
                m = ses.world.get(bq + a, br + b, yy)
                if m in (M['linen'], M['dusk_cloth'], M['pale_planks'], M['bedroll']):
                    hits.append((bq + a, br + b, yy, m))
    log('boat', len(hits), hits[:10])
    # centroid of the hull / sail
    pts = [(a, b, y) for a, b, y, m in hits]
    aq = sum(c[0] for c in pts) / max(1, len(pts))
    ar = sum(c[1] for c in pts) / max(1, len(pts))
    ay = sum(c[2] for c in pts) / max(1, len(pts))
    tx, tz = center(int(round(aq)), int(round(ar)))
    # side-on, slightly above
    p.x, p.z = tx - 9.0, tz + 11.0
    p.y = (ay + 5.5) * LAYER
    look_at(p, tx, (ay + 1.2) * LAYER, tz)
    yield 0.9
    yield shot('06_sky_boat')
    log('done')


def phase3(app, log, shot, look_at, settled, arg):
    """1.4 Phase 3: tutorial island, fishing, farming, Glimmer shrines, and the Path."""
    from . import tutorial as TUT
    from .ui.systems import PathScreen, WaystoneScreen, FontScreen
    from . import glimmer as G

    yield 0.5
    yield lambda: bool(app.backdrop and app.backdrop.get('world') and app.backdrop['world'].busy() == 0)
    yield 0.8
    yield shot('00_title')

    app.start_tutorial()
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None
    log('tutorial ready', p.x, p.y, p.z, 'npcs', len(ses.npcs))

    # aerial of the whole lesson island
    ox, oz = center(0, 0)
    p.x, p.z = ox + 4.0, oz + 22.0
    p.y = (TUT.SURF + 16) * LAYER
    look_at(p, ox, (TUT.SURF + 2) * LAYER, oz)
    yield settled()
    yield 0.8
    yield shot('01_lesson_island')

    # Willow at spawn, with talk bubble
    app.hide_hud = False
    if ses.npcs:
        ses.talk = 'Willow'
        ses.npcs[0]['line'] = 0
    wx, wz = center(0, 0)
    p.x, p.z = wx + 2.4, wz + 4.2
    p.y = (TUT.SURF + 2.2) * LAYER
    look_at(p, wx, (TUT.SURF + 1.6) * LAYER, wz)
    yield 0.7
    yield shot('02_welcome')

    # mining grove
    app.hide_hud = True
    tx, tz = center(5, -1)
    p.x, p.z = tx + 1.5, tz + 8.0
    p.y = (TUT.SURF + 5.5) * LAYER
    look_at(p, tx, (TUT.SURF + 2.4) * LAYER, tz)
    yield 0.7
    yield shot('03_mining_grove')

    # tinker hut + kiln along the path
    tx, tz = center(9, 1)
    p.x, p.z = tx + 1.0, tz + 9.5
    p.y = (TUT.SURF + 6.0) * LAYER
    look_at(p, tx, (TUT.SURF + 2.2) * LAYER, tz)
    yield 0.7
    yield shot('04_bench_and_kiln')

    # doors and ladders
    tx, tz = center(13, -2)
    p.x, p.z = tx - 1.0, tz + 8.0
    p.y = (TUT.SURF + 5.0) * LAYER
    look_at(p, tx, (TUT.SURF + 2.4) * LAYER, tz)
    yield 0.7
    yield shot('05_doors_and_ladders')

    # fishing dock + bobber
    tx, tz = center(6, 8)
    p.x, p.z = tx + 1.2, tz + 8.5
    p.y = (TUT.SURF + 4.2) * LAYER
    look_at(p, tx, (TUT.SURF + 0.6) * LAYER, tz)
    ses.fishing = {'state': 'bite', 't': 0.2, 'wait': 1, 'window': 1,
                   'pos': (tx, (TUT.SURF + 0.15) * LAYER, tz), 'realm': 0, 'cell': (6, 8, TUT.SURF - 1)}
    app.hide_hud = False
    yield 0.7
    yield shot('06_fishing')

    # farm
    app.hide_hud = True
    ses.fishing = None
    tx, tz = center(3, 6)
    p.x, p.z = tx + 1.0, tz + 7.5
    p.y = (TUT.SURF + 4.5) * LAYER
    look_at(p, tx, (TUT.SURF + 1.4) * LAYER, tz)
    yield 0.7
    yield shot('07_farm')

    # glimmer shrine + font + motes
    tx, tz = center(0, -7)
    p.x, p.z = tx + 2.0, tz + 9.0
    p.y = (TUT.SURF + 5.5) * LAYER
    look_at(p, tx, (TUT.SURF + 2.0) * LAYER, tz)
    yield 0.7
    yield shot('08_glimmer_shrine')

    # the Path (a few steps already remembered)
    ses.achieved = ['first', 'gather', 'craft', 'wander']
    app.set_screen(PathScreen())
    yield 0.5
    yield shot('09_path')
    app.set_screen(None)
    yield 0.2

    # Font screen
    ses.give(I.GLIMMER.id, 8, quiet=True)
    app.set_screen(FontScreen())
    yield 0.5
    yield shot('10_font')
    app.set_screen(None)

    log('phase3 tour finished')



def phase3_fix(app, log, shot, look_at, settled, arg):
    """Retake doors, fishing, the farm, and the Path with tighter framing."""
    from . import tutorial as TUT
    from .ui.systems import PathScreen
    app.start_tutorial()
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None

    # doors and ladders: stand in the yard, look at the wall and door
    tx, tz = center(13, -2)
    p.x, p.z = tx - 3.2, tz + 2.8
    p.y = (TUT.SURF + 3.6) * LAYER
    look_at(p, tx + 0.6, (TUT.SURF + 2.2) * LAYER, tz)
    yield 0.7
    yield shot('05_doors_and_ladders')

    # fishing: low over the pool, bobber biting, HUD on
    tx, tz = center(6, 8)
    p.x, p.z = tx + 0.4, tz + 5.2
    p.y = (TUT.SURF + 3.0) * LAYER
    look_at(p, tx, (TUT.SURF + 0.3) * LAYER, tz)
    ses.fishing = {'state': 'bite', 't': 0.2, 'wait': 1, 'window': 1,
                   'pos': (tx, (TUT.SURF - 0.15) * LAYER, tz), 'realm': 0, 'cell': (6, 8, TUT.SURF - 1)}
    app.hide_hud = False
    yield 0.7
    yield shot('06_fishing')

    # farm: look down on the tilled beds
    app.hide_hud = True
    ses.fishing = None
    tx, tz = center(3, 6)
    p.x, p.z = tx - 1.5, tz + 5.0
    p.y = (TUT.SURF + 4.0) * LAYER
    look_at(p, tx, (TUT.SURF + 1.1) * LAYER, tz)
    yield 0.7
    yield shot('07_farm')

    ses.achieved = ['first', 'gather', 'craft', 'wander']
    app.set_screen(PathScreen())
    yield 0.5
    yield shot('09_path')
    app.set_screen(None)
    log('phase3_fix finished')


def phase4(app, log, shot, look_at, settled, arg):
    """Title logo, a seed showcase, brighter lesson huts, flyers, tall trees, third person, dawn."""
    from . import tutorial as TUT
    from . import showcase as SC
    from .entities import Mob
    from . import items as I

    yield 1.2
    yield lambda: app.backdrop is not None and app.backdrop['world'].busy() == 0
    yield 1.4
    yield shot('00_title')

    SC._index = 1
    app.start_backdrop()
    yield 1.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 1.6
    yield shot('01_title_seed')
    keep = app.menu
    app.menu = None
    app.backdrop['speed'] = 0
    yield 1.1
    yield shot('02_showcase_sky')
    app.menu = keep

    app.start_tutorial()
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None

    # brighter huts: look into Tess and Cole's rooms
    tx, tz = center(9, 2)
    p.x, p.z = tx - 1.0, tz + 7.0
    p.y = (TUT.SURF + 3.8) * LAYER
    look_at(p, tx + 1.2, (TUT.SURF + 1.6) * LAYER, tz - 0.4)
    yield 0.8
    yield shot('03_lesson_huts')

    # practice door, slightly ajar in its frame
    tx, tz = center(13, -1)
    p.x, p.z = tx - 3.4, tz + 2.6
    p.y = (TUT.SURF + 3.4) * LAYER
    look_at(p, tx + 0.3, (TUT.SURF + 2.0) * LAYER, tz)
    yield 0.8
    yield shot('04_practice_door')

    # quiet lesson island (no woolhops), trees you can walk under
    tx, tz = center(5, -2)
    p.x, p.z = tx - 4.5, tz + 6.5
    p.y = (TUT.SURF + 2.2) * LAYER
    look_at(p, tx, (TUT.SURF + 3.5) * LAYER, tz)
    yield 0.8
    yield shot('05_lesson_trees')

    # a new sky for flyers, tall trees, third person, dawn
    app.set_screen(None)
    app.create_sky('Phase 4', 1729, '1729', 'dreamer')
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = True
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None
    ses.phase = 0.12
    ses.mobs = [m for m in ses.mobs if m.kind in ('skywhale', 'fairy')]

    # place two skywhales in front of the camera
    q, r = cell_at(p.x, p.z)
    tx, tz = p.x + 18, p.z - 8
    p.y = p.y + 14
    ses.mobs.append(Mob('skywhale', tx, p.y - 1.5, tz))
    ses.mobs.append(Mob('skywhale', tx + 10, p.y + 2.0, tz - 6))
    ses.mobs[-2].yaw = 220
    ses.mobs[-1].yaw = 200
    look_at(p, tx + 4, p.y, tz - 2)
    yield settled()
    yield 1.0
    yield shot('06_skywhales')

    # fairies at dusk, near the player, glowing
    ses.phase = 0.48
    ses.mobs = [m for m in ses.mobs if m.kind == 'skywhale']
    fx, fz = p.x + 3.5, p.z + 1.2
    for i, (dx, dz, dy) in enumerate(((-0.8, 1.2, 0.4), (1.1, 0.6, 0.8), (0.2, -0.9, 0.3), (1.8, 1.6, 1.1))):
        ses.mobs.append(Mob('fairy', fx + dx, p.y - 6 + dy, fz + dz))
    p.y = p.y - 5
    look_at(p, fx, p.y - 0.2, fz)
    yield 0.9
    yield shot('07_fairies')

    # walkable canopy: find a nearby tree and stand under it
    WOOD = {M['heartwood'], M['cedar_heartwood'], M['pale_heartwood'], M['dark_heartwood']}
    pq, pr = cell_at(p.x, p.z)
    found = None
    for rad in range(1, 40):
        for aq, ar in ring(pq, pr, rad):
            top = ses.world.column_top(aq, ar)
            if top is None:
                continue
            if ses.world.get(aq, ar, top + 1) in WOOD:
                found = (aq, ar, top)
                break
        if found:
            break
    if found:
        aq, ar, top = found
        tx, tz = center(aq, ar)
        # stand a couple cells off the trunk, look through the under-canopy
        p.x, p.z = tx + 2.6, tz + 2.2
        p.y = (top + 1) * LAYER + 0.05
        look_at(p, tx, (top + 5.5) * LAYER, tz)
        log('tree', found)
        yield settled()
        yield 0.9
        yield shot('08_under_canopy')
    else:
        log('no tree found')

    # third person, holding a crafted pick
    ses.inv.clear()
    ses.inv.add(I.TOOLS[('pick', 2)].id, 1)
    ses.hot = 0
    app.cam_view = 1
    app.hide_hud = False
    p.y = (ses.world.column_top(*cell_at(p.x, p.z)) + 1) * LAYER + 0.05
    p.pitch = -12
    # camera behind: look slightly down at the figure
    yield 0.8
    yield shot('09_third_person')
    app.cam_view = 2
    yield 0.7
    yield shot('10_third_person_front')
    app.cam_view = 1
    app.hide_hud = True

    # dawn sleep transition (mid fade-in)
    ses.sleeping = {'stage': 'dawn', 't': 0.8}
    ses.phase = 0.88
    yield 0.4
    yield shot('11_dawn_sleep')
    ses.sleeping = None
    ses.phase = 0.0
    log('phase4 finished')



def phase4_fix(app, log, shot, look_at, settled, arg):
    """Clearer skywhales and a cleaner third-person shot in the light."""
    from .entities import Mob
    from . import items as I
    app.create_sky('Phase 4 fix', 1729, '1729', 'dreamer')
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = True
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    ses.last_tide_name = 'Lighttide'
    ses.phase = 0.08
    ses.weather = 'clear'
    app.hide_hud = True
    p.update = lambda *a, **k: None
    ses.mobs = []
    # stand in open air looking at a pair of drifting whales
    p.x, p.y, p.z = p.x, p.y + 18, p.z
    ses.mobs.append(Mob('skywhale', p.x + 10, p.y - 1.0, p.z - 16))
    ses.mobs.append(Mob('skywhale', p.x + 22, p.y + 3.0, p.z - 22))
    ses.mobs[-2].yaw = 40
    ses.mobs[-1].yaw = 20
    look_at(p, p.x + 14, p.y + 0.5, p.z - 18)
    yield settled()
    yield 1.0
    yield shot('06_skywhales')

    # fairies over a grassy shelf at early dusk, close up
    ses.phase = 0.42
    ses.mobs = []
    top = ses.world.column_top(*cell_at(p.x, p.z)) or int(p.y / LAYER)
    p.y = (top + 3) * LAYER
    fx, fy, fz = p.x + 3.0, p.y + 0.2, p.z - 2.0
    for dx, dz, dy in ((-0.6, 0.8, 0.2), (0.9, 0.3, 0.5), (0.1, -0.7, 0.15), (1.4, 1.1, 0.7)):
        ses.mobs.append(Mob('fairy', fx + dx, fy + dy, fz + dz))
    look_at(p, fx, fy + 0.2, fz)
    yield 0.9
    yield shot('07_fairies')

    # third person on open ground, holding a pick, no toasts
    ses.phase = 0.10
    ses.last_tide_name = 'Lighttide'
    ses.toasts = []
    ses.mobs = []
    ses.inv.clear()
    ses.inv.add(I.TOOLS[('pick', 2)].id, 1)
    ses.hot = 0
    top = ses.world.column_top(*cell_at(p.x, p.z)) or int(p.y / LAYER)
    p.x, p.z = p.x, p.z
    p.y = (top + 1) * LAYER + 0.05
    p.pitch = -8
    p.yaw = 200
    app.cam_view = 1
    app.hide_hud = False
    yield 0.8
    yield shot('09_third_person')
    app.cam_view = 2
    yield 0.7
    yield shot('10_third_person_front')
    log('phase4_fix finished')


def _find_under_canopy(ses, origin=None, reach=80):
    """A walkable ground cell beside a trunk, with canopy at least 3 layers overhead."""
    WOOD = {M['heartwood'], M['cedar_heartwood'], M['pale_heartwood'], M['dark_heartwood']}
    LEAF = {M['canopy']}
    pq, pr = origin or cell_at(ses.player.x, ses.player.z)
    trunks = []
    for ch in list(ses.world.chunks.values()):
        hits = np.argwhere(np.isin(ch.cells, list(WOOD)))
        for a, y, b in hits:
            q = ch.cq * CHUNK + int(a)
            r = ch.cr * CHUNK + int(b)
            if abs(q - pq) + abs(r - pr) > reach * 2:
                continue
            trunks.append((q, r, int(y)))
    trunks.sort(key=lambda t: abs(t[0] - pq) + abs(t[1] - pr))
    for aq, ar, trunk_y in trunks:
        leaf_y = None
        for y in range(trunk_y + 1, trunk_y + 14):
            if ses.world.get(aq, ar, y) in LEAF:
                leaf_y = y
                break
        if leaf_y is None:
            continue
        for dq, dr in list(DIRS) + [(0, 0)]:
            nq, nr = aq + dq, ar + dr
            gt = ses.world.column_top(nq, nr)
            if gt is None:
                continue
            cap = ses.world.get(nq, nr, gt)
            if cap in WOOD or cap in LEAF:
                continue
            overhead = None
            for y in range(gt + 3, gt + 14):
                if ses.world.get(nq, nr, y) in LEAF or (nq == aq and ses.world.get(aq, ar, y) in LEAF):
                    overhead = y
                    break
            # also accept canopy on the trunk column hanging over this neighbor
            if overhead is None and leaf_y >= gt + 3:
                overhead = leaf_y
            if overhead is not None:
                return nq, nr, gt, aq, ar, overhead
    return None


def _find_chamber(ses):
    """A buried lumen lamp well below the surface, from the loaded chunks."""
    for ch in list(ses.world.chunks.values()):
        hits = np.argwhere(ch.cells == M['lumen_lamp'])
        for a, y, b in hits:
            q = ch.cq * CHUNK + int(a)
            r = ch.cr * CHUNK + int(b)
            top = ses.world.column_top(q, r)
            if top is not None and int(top) - int(y) >= 5:
                return q, r, int(y)
    return None


def phase5(app, log, shot, look_at, settled, arg):
    """Playtest and cohesion: title, lesson, under-canopy, whales, face, lit chamber, a legacy sky."""
    import json
    import os
    import time as _t
    from . import tutorial as TUT
    from . import showcase as SC
    from .entities import Mob
    from . import items as I
    from .generator import Generator
    from .session import find_spawn
    from .storage import SkyStorage
    from .structures import Stamp, build_chamber, INTACT

    app.started = _t.perf_counter() - 60
    yield 1.2
    yield lambda: app.backdrop is not None and app.backdrop['world'].busy() == 0
    yield 1.4
    yield shot('00_title')

    SC._index = 1
    app.start_backdrop()
    yield 1.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 1.6
    yield shot('01_title_seed')
    keep = app.menu
    app.menu = None
    app.backdrop['speed'] = 0
    yield 1.1
    yield shot('02_hero_sky')
    app.menu = keep

    app.start_tutorial()
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    app.started = _t.perf_counter() - 60
    p.update = lambda *a, **k: None
    if any(m.kind in ('woolhop', 'skywhale', 'fairy') for m in ses.mobs):
        log('WARN tutorial still has creatures', [m.kind for m in ses.mobs])
    ses.mobs = []

    tx, tz = center(9, 2)
    p.x, p.z = tx - 1.0, tz + 7.0
    p.y = (TUT.SURF + 3.8) * LAYER
    look_at(p, tx + 1.2, (TUT.SURF + 1.6) * LAYER, tz - 0.4)
    yield 0.8
    yield shot('03_lesson_huts')

    tx, tz = center(13, -1)
    p.x, p.z = tx - 3.4, tz + 2.6
    p.y = (TUT.SURF + 3.4) * LAYER
    look_at(p, tx + 0.3, (TUT.SURF + 2.0) * LAYER, tz)
    yield 0.8
    yield shot('04_practice_door')

    # a new generated sky — stand under a real canopy before flying off
    app.set_screen(None)
    seed = seed_from_text('bright-arch')
    app.create_sky('Phase 5', seed, 'bright-arch', 'dreamer')
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    # the Bright Arch grove (lavender trees you can walk under)
    tx, tz = center(-63, 22)
    p.x, p.z = tx, tz
    p.y = 49 * LAYER
    yield settled()
    ses.dev = True
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    app.cam_view = 0
    app.started = _t.perf_counter() - 60
    p.update = lambda *a, **k: None
    ses.phase = 0.12

    found = _find_under_canopy(ses, cell_at(p.x, p.z), 72)
    if found:
        nq, nr, gt, aq, ar, overhead = found
        tx, tz = center(aq, ar)
        gx, gz = center(nq, nr)
        p.x, p.z = gx + (gx - tx) * 0.15, gz + (gz - tz) * 0.15
        p.y = (gt + 1) * LAYER + 0.05
        look_at(p, tx, (overhead + 0.2) * LAYER, tz)
        log('under_canopy', found)
        yield settled()
        yield 1.0
        yield shot('05_under_canopy')
    else:
        log('no tree found')

    # skywhales in profile so the long silhouette reads
    q, r = cell_at(p.x, p.z)
    top = ses.world.column_top(q, r) or 50
    p.x, p.z = p.x, p.z
    p.y = (top + 16) * LAYER
    tx, tz = p.x + 16, p.z - 2
    ses.mobs = [Mob('skywhale', tx, p.y - 1.0, tz), Mob('skywhale', tx + 12, p.y + 2.2, tz - 7)]
    ses.mobs[0].yaw = 270
    ses.mobs[1].yaw = 250
    look_at(p, tx + 5, p.y, tz - 3)
    yield settled()
    yield 1.0
    yield shot('06_skywhales')

    # third person and a clear front face
    ses.mobs = []
    # stand on solid ground near spawn island
    found = _find_under_canopy(ses, cell_at(p.x, p.z), 80)
    if found:
        nq, nr, gt, *_ = found
        p.x, p.z = center(nq, nr)
        p.y = (gt + 1) * LAYER + 0.05
    else:
        q, r = cell_at(p.x, p.z)
        gt = ses.world.column_top(q, r) or int(p.y / LAYER)
        p.y = (gt + 1) * LAYER + 0.05
    ses.inv.clear()
    ses.inv.add(I.TOOLS[('pick', 2)].id, 1)
    ses.hot = 0
    p.yaw = 200
    p.pitch = -8
    app.cam_view = 1
    app.hide_hud = False
    ses.toasts = []
    app.started = _t.perf_counter() - 60
    yield 0.9
    yield shot('07_third_person')
    app.cam_view = 2
    yield 0.8
    yield shot('08_looking_at_you')
    app.cam_view = 0
    app.hide_hud = True

    # lit buried chamber — find one, or stamp a demo under thick land
    ch = _find_chamber(ses)
    if ch is None:
        pq, pr = cell_at(p.x, p.z)
        for rad in range(2, 40):
            for aq, ar in ring(pq, pr, rad):
                gt = ses.world.column_top(aq, ar)
                bot = None
                if gt is None:
                    continue
                for y in range(gt, max(0, gt - 24), -1):
                    if ses.world.get(aq, ar, y) == 0 and y < gt - 8:
                        break
                    bot = y
                if gt is not None and bot is not None and gt - bot >= 14:
                    pal = dict(brick=M['stone_bricks'], tile=M['stone_tiles'], stone=M['stone'],
                               lamp=M['ember_lamp'], planks=M['planks'], log=M['heartwood'],
                               cloth=M['linen'], cobble=M['cobble'])
                    st = Stamp(None, None, None, None, None, None, 0, 0,
                               random.Random(1), INTACT, pal, world=ses.world)
                    build_chamber(st, aq, ar, gt)
                    ses.world.mark_dirty(aq, ar) if hasattr(ses.world, 'mark_dirty') else None
                    ch = (aq, ar, gt - 8)
                    log('stamped chamber', ch)
                    break
            if ch:
                break
    if ch:
        cq, cr, cy = ch
        tx, tz = center(cq, cr)
        p.x, p.z = tx + 1.6, tz + 2.2
        p.y = (cy + 1.2) * LAYER
        look_at(p, tx, (cy + 1.4) * LAYER, tz)
        log('chamber', ch)
        yield settled()
        yield 1.0
        yield shot('09_chamber')
    else:
        log('no chamber found')

    # a 1.3-style sky with no gen settings still loads
    g = Generator(7)
    q, r, top, sp = find_spawn(g)
    x, z = center(q, r)
    folder = SkyStorage.unique_folder(app.skies_dir, 'Legacy Sky')
    st = SkyStorage(app.skies_dir, folder)
    os.makedirs(st.path, exist_ok=True)
    st.save({
        'name': 'Legacy Sky', 'seed': 7, 'seed_text': 'legacy-7', 'mode': 'wanderer',
        'gen': None,
        'player': {'x': x, 'y': (top + 1) * LAYER + 0.001, 'z': z, 'yaw': 20, 'pitch': 4},
    })
    app.set_screen(None)
    if app.session:
        app.session.close()
        app.session = None
    app.open_sky(folder)
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    yield settled()
    log('legacy', 'version', ses.gen.version, 'pos', p.x, p.y, p.z)
    if ses.gen.version != 1:
        log('WARN legacy gen version', ses.gen.version)
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None
    p.y = p.y + 10 * LAYER
    p.pitch = -18
    yield settled()
    yield 1.0
    yield shot('10_legacy_sky')
    log('phase5 finished')


def phase5_fix(app, log, shot, look_at, settled, arg):
    """Retake under-canopy, closer whales, and a readable front face in a generated grove."""
    import time as _t
    from .entities import Mob
    from . import items as I

    app.started = _t.perf_counter() - 60
    yield 0.8
    seed = seed_from_text('bright-arch')
    app.create_sky('Phase 5 Fix', seed, 'bright-arch', 'dreamer')
    yield lambda: app.mode == 'game' and app.session and app.session.ready
    ses = app.session
    p = ses.player
    tx, tz = center(-63, 22)
    p.x, p.z = tx, tz
    p.y = 49 * LAYER
    p.drifting = True
    p.noclip = True
    ses.dev = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    app.cam_view = 0
    p.update = lambda *a, **k: None
    ses.phase = 0.12
    yield settled()

    found = _find_under_canopy(ses, (-63, 22), 80)
    if found:
        nq, nr, gt, aq, ar, overhead = found
        tx, tz = center(aq, ar)
        gx, gz = center(nq, nr)
        p.x = gx + (gx - tx) * 0.2
        p.z = gz + (gz - tz) * 0.2
        p.y = (gt + 1) * LAYER + 0.05
        look_at(p, tx, (overhead + 0.15) * LAYER, tz)
        log('under_canopy', found)
        yield settled()
        yield 1.1
        yield shot('05_under_canopy')
        stand = (p.x, p.y, p.z, nq, nr, gt)
    else:
        log('no tree found')
        stand = (p.x, p.y, p.z, -63, 22, 48)

    # whales in profile, close enough to read the long silhouette
    bx, bz = center(-63, 22)
    p.x, p.z = bx - 2, bz + 14
    p.y = 62 * LAYER
    ses.mobs = [
        Mob('skywhale', bx + 8, 60 * LAYER, bz + 2),
        Mob('skywhale', bx + 18, 63 * LAYER, bz - 6),
    ]
    ses.mobs[0].yaw = 280
    ses.mobs[1].yaw = 260
    look_at(p, bx + 12, 61 * LAYER, bz - 1)
    yield settled()
    yield 1.0
    yield shot('06_skywhales')
    ses.mobs = []

    # face and third person on the grove floor
    sx, sy, sz, nq, nr, gt = stand
    p.x, p.z = sx, sz
    p.y = (gt + 1) * LAYER + 0.05
    ses.inv.clear()
    ses.inv.add(I.TOOLS[('pick', 2)].id, 1)
    ses.hot = 0
    p.yaw = 30
    p.pitch = -6
    app.cam_view = 1
    app.hide_hud = False
    ses.toasts = []
    app.started = _t.perf_counter() - 60
    yield 0.9
    yield shot('07_third_person')
    app.cam_view = 2
    yield 0.8
    yield shot('08_looking_at_you')
    app.cam_view = 0
    app.hide_hud = True
    log('phase5_fix finished')


def v14_title(app, log, shot, look_at, settled, arg):
    """Title and Bright Arch hero for the 1.4 README, after the version bump."""
    from . import showcase as SC
    yield 1.2
    yield lambda: app.backdrop is not None and app.backdrop['world'].busy() == 0
    yield 1.5
    yield shot('00_title')
    SC._index = 1
    app.start_backdrop()
    yield 1.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 1.6
    yield shot('01_title_seed')
    keep = app.menu
    app.menu = None
    app.backdrop['speed'] = 0
    yield 1.1
    yield shot('02_hero_sky')
    app.menu = keep
    log('v14_title finished')

def phase141(app, log, shot, look_at, settled, arg):
    """1.4.1 playtest: title, lesson path, island heights, teardrop hulls, caves, doors, textures, plants."""
    from .hexgrid import center
    from . import materials as MT
    from . import gensettings as GS
    from .config import LAYER
    from .tutorial import NPCS, SURF, SPAWN

    yield 1.0
    yield lambda: app.backdrop is not None and app.backdrop['world'].busy() == 0
    yield 1.2
    yield shot('00_title')

    app.start_tutorial()
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None

    # spawn and the path toward Willow, so signposts and open ground read clearly
    x, z = center(0, 0)
    p.x, p.z, p.y = x - 2.0, z - 3.5, (SURF + 3.2) * LAYER
    look_at(p, x + 3.0, (SURF + 1.6) * LAYER, z + 2.0)
    yield settled()
    yield 0.7
    yield shot('01_tutorial_path')

    # Mira's door in the open yard
    x, z = center(22, -5)
    p.x, p.z, p.y = x - 4.5, z + 0.2, (SURF + 2.2) * LAYER
    look_at(p, x, (SURF + 1.6) * LAYER, z)
    yield settled()
    yield 0.6
    yield shot('02_door_open')

    # a new sky for terrain, plants, caves
    app.create_sky('Phase141', 7, '7', 'dreamer', gen=GS.defaults())
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    ses.dev = False
    p.drifting = True
    p.noclip = True
    ses.hold = True
    ses.toasts = []
    app.hide_hud = True
    p.update = lambda *a, **k: None

    g = ses.gen
    Q, R = np.mgrid[-80:80:2, -80:80:2]
    col = g.columns(Q, R)
    land = col['land'] & ~col['skerry']
    recs = []
    for a in range(Q.shape[0]):
        for b in range(Q.shape[1]):
            if land[a, b] and col['e'][a, b] > 0.08:
                recs.append((int(Q[a, b]), int(R[a, b]), int(col['top'][a, b]),
                             int(col['bottom'][a, b]), float(col['com'][a, b])))
    recs.sort(key=lambda r: r[4])
    log('com range', recs[0][4] if recs else None, recs[-1][4] if recs else None, 'n', len(recs))

    # look up from a low island toward higher ones
    if recs:
        lo = recs[len(recs)//5]
        q, r, top, bot, com = lo
        x, z = center(q, r)
        p.x, p.z, p.y = x + 6.0, z + 8.0, (top + 4) * LAYER
        look_at(p, x, (top + 18) * LAYER, z - 20)
        yield settled()
        yield 0.8
        yield shot('03_islands_above')
        # teardrop underside from the side
        mid = (top + bot) * 0.5
        p.x, p.z, p.y = x + 16.0, z + 2.0, mid * LAYER
        look_at(p, x, mid * LAYER, z)
        yield settled()
        yield 0.8
        yield shot('04_teardrop_underside')

    # a meadow close-up for the new plants
    meadow = None
    for a in range(Q.shape[0]):
        for b in range(Q.shape[1]):
            if land[a, b] and int(col['realm'][a, b]) == 0 and col['e'][a, b] > 0.06:
                meadow = (int(Q[a, b]), int(R[a, b]), int(col['top'][a, b]))
                break
        if meadow:
            break
    if meadow:
        q, r, top = meadow
        x, z = center(q, r)
        p.x, p.z, p.y = x + 3.5, z + 4.0, (top + 2.2) * LAYER
        look_at(p, x, (top + 0.4) * LAYER, z)
        yield settled()
        yield 0.7
        yield shot('05_ground_cover')

    # hunt a cobble-framed cave mouth in loaded chunks
    mouth = None
    cobble = MT.ID['cobble']
    for (cq, cr), ch in list(ses.world.chunks.items()):
        cells = ch.cells
        A, Y, B = cells.shape
        hits = np.argwhere(cells == cobble)
        if len(hits):
            a, y, b = hits[len(hits)//2]
            mouth = (cq * 16 + int(a), cr * 16 + int(b), int(y))
            break
    if mouth:
        q, r, y = mouth
        x, z = center(q, r)
        p.x, p.z, p.y = x + 5.0, z + 3.0, (y + 1.2) * LAYER
        look_at(p, x, (y + 0.6) * LAYER, z)
        yield settled()
        yield 0.7
        yield shot('06_cave_mouth')
    else:
        log('no cave mouth in view')

    # heartwood end-grain and a closed mid-hex door, placed at the feet
    if recs:
        q, r, top, bot, com = recs[len(recs)//2]
        ses.world.set(q, r, top + 1, MT.ID['heartwood'], 0, now=True)
        ses.world.set(q + 2, r, top + 1, MT.ID['door'], 0, now=True)
        ses.world.set(q + 2, r, top + 2, MT.ID['door'], 16, now=True)
        # a little wall so the door reads in a doorway
        ses.world.set(q + 2, r - 1, top + 1, MT.ID['pale_planks'], 0, now=True)
        ses.world.set(q + 2, r - 1, top + 2, MT.ID['pale_planks'], 0, now=True)
        ses.world.set(q + 2, r + 1, top + 1, MT.ID['pale_planks'], 0, now=True)
        ses.world.set(q + 2, r + 1, top + 2, MT.ID['pale_planks'], 0, now=True)
        x, z = center(q, r)
        p.x, p.z, p.y = x + 0.1, z + 2.4, (top + 3.4) * LAYER
        look_at(p, x, (top + 1.15) * LAYER, z)
        yield settled()
        yield 0.7
        yield shot('07_log_end_grain')
        x, z = center(q + 2, r)
        p.x, p.z, p.y = x - 3.6, z + 0.2, (top + 2.4) * LAYER
        look_at(p, x, (top + 1.7) * LAYER, z)
        yield settled()
        yield 0.7
        yield shot('08_door_closed')
        ses.world.set_meta(q + 2, r, top + 1, 0 | 8)
        ses.world.set_meta(q + 2, r, top + 2, 16 | 8)
        from .config import CHUNK
        ses.world.dirty.add(((q + 2) // CHUNK, r // CHUNK))
        yield settled()
        yield 0.5
        yield shot('09_door_swung_open')

    log('phase141 finished')


def showcases141(app, log, shot, look_at, settled, arg):
    """Two clear angles of every 1.4.1 title showcase (player builds, then seed skies)."""
    from . import showcase as SC
    items = SC.catalog()
    keep = app.menu
    for i, (kind, payload) in enumerate(items):
        SC._index = i
        app.start_backdrop()
        yield 0.8
        yield lambda: app.backdrop and app.backdrop['world'].busy() == 0 and app.backdrop['world'].busy_lod() == 0
        yield 0.8
        b = app.backdrop
        sc = b['showcase']
        b['speed'] = 0.0
        a0, a1 = SC.orbit_span(sc)
        span = a1 - a0
        angs = (a0 + span * 0.22, a0 + span * 0.72)
        slug = sc.name.lower().replace(' ', '_').replace("'", '').replace('-', '_')
        log('showcase', i, kind, sc.name, 'seed', sc.seed_text, 'site', sc.q, sc.r, sc.top, 'cam', sc.camera)
        app.menu = None
        for k, ang in enumerate(angs, 1):
            b['ang'] = ang
            yield 1.3
            yield shot(f'{slug}_{k}')
        app.menu = keep
    log('showcases141 finished')


def phase142_before(app, log, shot, look_at, settled, arg):
    """1.4.2 playtest befores: seed -1740201319 at the reported sheer-cliff sites."""
    from .hexgrid import cell_at
    from .config import LAYER
    seed = -1740201319
    yield 0.8
    app.create_sky('Before 142', seed, str(seed), 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    log('spawn', p.x, p.y, p.z, 'top', ses.world.column_top(*cell_at(p.x, p.z)))

    def stand(x, z, yaw, pitch, up=2.2):
        q, r = cell_at(x, z)
        top = ses.world.column_top(q, r)
        if top is None:
            top = 60
        p.x, p.z = float(x), float(z)
        p.y = top * LAYER + up
        p.yaw, p.pitch = yaw, pitch
        log('stand', x, z, 'qr', q, r, 'top', top, 'yaw', yaw, 'pitch', pitch)

    sites = [
        ('chalk_barrens', -3246, -1298),
        ('cinder_spires', -2296, 223),
        ('rose_mesas', 1376, 1522),
        ('lumen_grove', 1383, 1647),
        ('cloudstep_isles', 411, 2057),
    ]
    views = ((0, -8), (90, -8), (180, -6), (270, -10), (45, -18))
    for name, x, z in sites:
        for i, (yaw, pitch) in enumerate(views):
            stand(x, z, yaw, pitch)
            yield settled()
            yield 0.9
            yield shot(f'{name}_{i}')
        # pull back and look slightly down to show the wall in context
        stand(x, z, 120, -16, up=8)
        yield settled()
        yield 0.9
        yield shot(f'{name}_wide')
    log('phase142_before finished')


def phase142_after(app, log, shot, look_at, settled, arg):
    """Comparable afters on v3, plus a look-up at tall islands and a view down from ~300."""
    import math
    from .hexgrid import cell_at, center
    from .config import LAYER
    seed = -1740201319
    yield 0.8
    app.create_sky('After 142', seed, str(seed), 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    log('spawn', p.x, p.y, p.z, 'top', ses.world.column_top(*cell_at(p.x, p.z)))

    p.drifting = True

    def park(x, z, yaw, pitch):
        """Move the camera so the world starts loading this column."""
        p.x, p.z = float(x), float(z)
        p.y = 330 * LAYER
        p.vy = 0
        p.yaw, p.pitch = yaw, pitch

    def snap(x, z, yaw, pitch, up=2.2):
        q, r = cell_at(x, z)
        top = ses.world.column_top(q, r)
        if top is None or top < 0:
            top = 60
        p.x, p.z = float(x), float(z)
        p.y = top * LAYER + up
        p.vy = 0
        p.yaw, p.pitch = yaw, pitch
        log('stand', x, z, 'qr', q, r, 'top', top, 'yaw', yaw, 'pitch', pitch)
        return top

    def goto(x, z, yaw, pitch, up=2.2):
        park(x, z, yaw, pitch)
        yield settled()
        yield 0.5
        top = snap(x, z, yaw, pitch, up)
        yield settled()
        yield 0.8
        return top

    sites = [
        ('chalk_barrens', -3246, -1298),
        ('cinder_spires', -2296, 223),
        ('rose_mesas', 1376, 1522),
        ('lumen_grove', 1383, 1647),
        ('cloudstep_isles', 411, 2057),
    ]
    views = ((0, -8), (90, -8), (180, -6), (270, -10), (45, -18))
    for name, x, z in sites:
        for i, (yaw, pitch) in enumerate(views):
            yield from goto(x, z, yaw, pitch)
            yield shot(f'{name}_{i}')
        yield from goto(x, z, 120, -16, up=8)
        yield shot(f'{name}_wide')

    # from a mid island, look up at the 300-high peak (q -192, r -224)
    px, pz = center(-192, -224)
    vx, vz = center(-59, -224)
    yaw = math.degrees(math.atan2(px - vx, -(pz - vz))) % 360
    t = yield from goto(vx, vz, yaw, 16, up=2.4)
    log('lookup from', t, 'toward peak')
    yield 0.4
    yield shot('tall_islands_lookup')
    yield from goto(vx, vz, yaw, 8, up=10)
    yield shot('tall_islands_lookup_wide')

    t = yield from goto(px, pz, 40, -28, up=2.2)
    log('lookdown from', t)
    yield 0.4
    yield shot('peak300_lookdown')
    yield from goto(px, pz, 200, -18, up=3.0)
    yield shot('peak300_lookdown_2')
    log('phase142_after finished')


def phase142_showcases(app, log, shot, look_at, settled, arg):
    """Two clear angles of every 1.4.2 title showcase on generator v3."""
    from . import showcase as SC
    items = SC.catalog()
    keep = app.menu
    for i, (kind, payload) in enumerate(items):
        SC._index = i
        app.start_backdrop()
        yield 0.8
        yield lambda: app.backdrop and app.backdrop['world'].busy() == 0 and app.backdrop['world'].busy_lod() == 0
        yield 0.8
        b = app.backdrop
        sc = b['showcase']
        b['speed'] = 0.0
        a0, a1 = SC.orbit_span(sc)
        span = a1 - a0
        angs = (a0 + span * 0.22, a0 + span * 0.72)
        slug = sc.name.lower().replace(' ', '_').replace("'", '').replace('-', '_')
        log('showcase', i, kind, sc.name, 'seed', sc.seed_text, 'site', sc.q, sc.r, sc.top, 'cam', sc.camera)
        app.menu = None
        for k, ang in enumerate(angs, 1):
            b['ang'] = ang
            yield 1.3
            yield shot(f'{slug}_{k}')
        app.menu = keep
    log('phase142_showcases finished')


def phase142_heights(app, log, shot, look_at, settled, arg):
    """Retake the ~300 look-down from a cliff edge, plus elevated wide afters."""
    import math
    from .hexgrid import center, cell_at
    from .config import LAYER
    seed = -1740201319
    yield 0.8
    app.create_sky('After 142', seed, str(seed), 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.6
    ses = app.session
    p = ses.player
    p.drifting = True
    app.hide_hud = False

    def park(x, z, y, yaw, pitch):
        p.x, p.z, p.y = float(x), float(z), float(y)
        p.vy = p.vx = p.vz = 0
        p.yaw, p.pitch = yaw, pitch

    def snap_edge(q, r, yaw, pitch, up=3.0):
        x, z = center(q, r)
        park(x, z, 330 * LAYER, yaw, pitch)
        yield settled()
        yield 0.5
        top = ses.world.column_top(q, r)
        if top is None or top < 0:
            top = 292
        park(x, z, top * LAYER + up, yaw, pitch)
        log('edge', q, r, 'top', top, 'yaw', yaw, 'pitch', pitch)
        yield settled()
        yield 0.9
        return top

    # Saltwind rim of the high island (few trees), looking out over the drop
    yield from snap_edge(-213, -201, 150.0, -35, up=3.2)
    yield shot('peak300_lookdown')
    yield from snap_edge(-213, -201, 165.0, -38, up=3.4)
    yield shot('peak300_lookdown_2')

    # Elevated wide 1: fly above the high cinder shelf and look out over the gaps
    cx, cz = -2296.0, 223.0
    park(cx, cz, 330 * LAYER, 120, -12)
    yield settled()
    yield 0.6
    q, r = cell_at(cx, cz)
    top = ses.world.column_top(q, r) or 292
    # sit well above the surface, pitched down so hills, ridges and lower shelves read
    park(cx - 18, cz + 10, (top + 48) * LAYER, 125, -32)
    log('aerial cinder from', top + 48)
    yield settled()
    yield 1.0
    yield shot('aerial_wide_1')

    # Elevated wide 2: off the ~300 island, looking back so the peak and lower shelves show
    px, pz = center(-237, -245)
    park(px + 70, pz + 90, 250 * LAYER, 210, -28)
    log('aerial peak approach')
    yield settled()
    yield 1.0
    yield shot('aerial_wide_2')
    log('phase142_heights finished')


def phase142_aerial2(app, log, shot, look_at, settled, arg):
    """Second elevated after: above the ~300 island, looking down at ridges and lower shelves."""
    from .hexgrid import center, cell_at
    from .config import LAYER
    yield 0.6
    app.create_sky('After 142', -1740201319, '-1740201319', 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    ses = app.session
    p = ses.player
    p.drifting = True
    # stand off the high island's south-east rim, well ABOVE the 294 surface
    qx, qz = center(-213, -201)
    p.x, p.z = qx + 55, qz + 40
    p.y = 350 * LAYER
    p.vy = p.vx = p.vz = 0
    # look back at the high island and down toward the lower shelves
    p.yaw, p.pitch = 300.0, -30.0
    yield settled()
    yield 1.0
    yield shot('aerial_wide_2')
    # a second try from farther back and a little lower so more land fills the frame
    p.x, p.z = qx + 85, qz + 25
    p.y = 340 * LAYER
    p.yaw, p.pitch = 290.0, -28.0
    yield settled()
    yield 1.0
    yield shot('aerial_wide_2b')
    log('phase142_aerial2 finished')



def phase143_perf(app, log, shot, look_at, settled, arg):
    """Profile tutorial vs a normal v3 world with the same measurement."""
    import cProfile, pstats, io, time as _t, traceback

    def uncap():
        old = dict(app.settings)
        app.settings['vsync'] = False
        app.settings['fps_limit'] = 0
        app.apply_settings(old)
        app.set_vsync(False)
        log('uncapped vsync', app.settings['vsync'], 'fps_limit', app.settings['fps_limit'])

    def sample(label, seconds=5.0):
        ses = app.session
        w = ses.world
        counts = {'remesh': 0, 'collect_exc': 0, 'set': 0, 'tut_gen': 0, 'dirty_max': 0, 'busy_max': 0,
                  'jobs_max': 0, 'lights_max': 0, 'living_max': 0}
        orig_remesh = w._remesh_now
        orig_collect = w._collect
        orig_set = w.set

        def remesh(key):
            counts['remesh'] += 1
            return orig_remesh(key)

        def collect():
            try:
                return orig_collect()
            except Exception:
                counts['collect_exc'] += 1
                log('collect exc', traceback.format_exc())
                raise

        def wset(*a, **k):
            counts['set'] += 1
            return orig_set(*a, **k)

        w._remesh_now = remesh
        w._collect = collect
        w.set = wset
        # tick/draw split via wrapping app methods
        t_tick = [0.0]
        t_draw = [0.0]
        t_dyn = [0.0]
        orig_tick = app.tick
        orig_draw = app.draw
        orig_dyn = ses.dynamic_models

        def tick(dt):
            t0 = _t.perf_counter()
            try:
                return orig_tick(dt)
            finally:
                t_tick[0] += _t.perf_counter() - t0

        def draw():
            t0 = _t.perf_counter()
            try:
                return orig_draw()
            finally:
                t_draw[0] += _t.perf_counter() - t0

        def dyn(cam):
            t0 = _t.perf_counter()
            try:
                return orig_dyn(cam)
            finally:
                t_dyn[0] += _t.perf_counter() - t0

        app.tick = tick
        app.draw = draw
        ses.dynamic_models = dyn

        # also count leftover dirty / pending each frame
        pending_seen = [0]
        orig_on = app.on_frame

        def probe(dt):
            counts['dirty_max'] = max(counts['dirty_max'], len(w.dirty))
            counts['busy_max'] = max(counts['busy_max'], w.busy())
            counts['jobs_max'] = max(counts['jobs_max'], len(w.gen_jobs) + len(w.mesh_jobs))
            pending_seen[0] += sum(1 for c in w.chunks.values() if c.state in ('dirty', 'pending'))
            st = app.renderer.stats
            counts['lights_max'] = max(counts['lights_max'], int(st.get('lights') or 0))
            counts['living_max'] = max(counts['living_max'], len(ses.sim.active))
            if orig_on:
                orig_on(dt)

        # don't replace on_frame (tour driver lives there); hook after by wrapping later? 
        # We'll poll at the end; mid-sample hook via session.update is enough for remesh/set.
        app.frame_times = []
        pr = cProfile.Profile()
        pr.enable()
        t0 = _t.perf_counter()
        # yield control back to the tour runner for `seconds`
        state = {'t0': t0, 'sec': seconds}
        def done():
            if _t.perf_counter() - state['t0'] < state['sec']:
                # keep sampling dirty while we wait
                counts['dirty_max'] = max(counts['dirty_max'], len(w.dirty))
                counts['busy_max'] = max(counts['busy_max'], w.busy())
                counts['jobs_max'] = max(counts['jobs_max'], len(w.gen_jobs) + len(w.mesh_jobs))
                st = app.renderer.stats
                counts['lights_max'] = max(counts['lights_max'], int(st.get('lights') or 0))
                counts['living_max'] = max(counts['living_max'], len(ses.sim.active))
                pending_seen[0] += sum(1 for c in w.chunks.values() if getattr(c, 'state', '') in ('dirty', 'pending'))
                return False
            return True

        return {
            'done': done,
            'finish': lambda: _finish_sample(label, pr, app, ses, w, counts, t_tick, t_draw, t_dyn,
                                             orig_remesh, orig_collect, orig_set, orig_tick, orig_draw, orig_dyn,
                                             pending_seen, log, shot),
        }

    def _finish_sample(label, pr, app, ses, w, counts, t_tick, t_draw, t_dyn,
                       orig_remesh, orig_collect, orig_set, orig_tick, orig_draw, orig_dyn,
                       pending_seen, log, shot):
        pr.disable()
        w._remesh_now = orig_remesh
        w._collect = orig_collect
        w.set = orig_set
        app.tick = orig_tick
        app.draw = orig_draw
        ses.dynamic_models = orig_dyn
        ft = list(app.frame_times)
        # last ~sample window: frame_times is last 120
        n = max(1, len(ft))
        s = sum(ft) if ft else 1e-6
        fps = n / s
        ms = [t * 1000.0 for t in ft]
        ms.sort()
        def pct(p):
            if not ms:
                return 0
            i = min(len(ms) - 1, int(round((p / 100.0) * (len(ms) - 1))))
            return ms[i]
        gen = (sum(w.timings['gen']) / len(w.timings['gen']) * 1000) if w.timings['gen'] else 0
        mesh = (sum(w.timings['mesh']) / len(w.timings['mesh']) * 1000) if w.timings['mesh'] else 0
        st = app.renderer.stats
        log(f'PERF {label}')
        log(f'  fps={fps:.1f}  frames={n}  frame_ms p50={pct(50):.2f} p95={pct(95):.2f} p99={pct(99):.2f} max={max(ms) if ms else 0:.2f}')
        log(f'  tick_s={t_tick[0]:.3f} draw_s={t_draw[0]:.3f} dyn_s={t_dyn[0]:.3f}')
        log(f'  chunks={len(w.chunks)} drawn={st.get("drawn")} lights={st.get("lights")} lights_max={counts["lights_max"]}')
        log(f'  gen_ms={gen:.2f} mesh_ms={mesh:.2f} living={len(ses.sim.active)} living_max={counts["living_max"]} npcs={len(getattr(ses, "npcs", []) or [])}')
        log(f'  remesh={counts["remesh"]} set={counts["set"]} collect_exc={counts["collect_exc"]} dirty_max={counts["dirty_max"]} busy_max={counts["busy_max"]} jobs_max={counts["jobs_max"]} pending_hits={pending_seen[0]}')
        log(f'  tutorial={bool(getattr(ses, "tutorial", False))} seed={ses.seed}')
        buf = io.StringIO()
        pstats.Stats(pr, stream=buf).sort_stats('tottime').print_stats(25)
        log(buf.getvalue())
        return fps

    uncap()
    yield 0.4

    # --- tutorial ---
    app.start_tutorial()
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    app.hide_hud = False
    app.show_debug = True
    yield shot('perf_tutorial_still')
    tut_still = sample('tutorial_still', 5.0)
    yield tut_still['done']
    fps_tut_still = tut_still['finish']()
    app.test_input = {'fwd': 1, 'hurry': True}
    tut_walk = sample('tutorial_walk', 5.0)
    yield tut_walk['done']
    fps_tut_walk = tut_walk['finish']()
    app.test_input = {}
    yield shot('perf_tutorial_walk')
    log('TUTORIAL fps still', round(fps_tut_still, 2), 'walk', round(fps_tut_walk, 2))

    # leave the lesson, start a normal v3 sky
    app.quit_to_title()
    yield 0.8
    from .noise import seed_from_text
    # playtest seed used in 1.4.2, a typical mid-spawn v3 world
    seed = -1740201319
    app.create_sky('Perf Normal', seed, '', 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    app.show_debug = True
    yield shot('perf_normal_still')
    n_still = sample('normal_still', 5.0)
    yield n_still['done']
    fps_n_still = n_still['finish']()
    app.test_input = {'fwd': 1, 'hurry': True}
    n_walk = sample('normal_walk', 5.0)
    yield n_walk['done']
    fps_n_walk = n_walk['finish']()
    app.test_input = {}
    yield shot('perf_normal_walk')
    log('NORMAL fps still', round(fps_n_still, 2), 'walk', round(fps_n_walk, 2))
    log('COMPARE tutorial/normal still', round(fps_tut_still, 2), '/', round(fps_n_still, 2),
        'walk', round(fps_tut_walk, 2), '/', round(fps_n_walk, 2))
    log('phase143_perf finished')


def phase143_after(app, log, shot, look_at, settled, arg):
    """After-fix fps (wall clock) plus cutoff and unclothed-wanderer shots."""
    import time as _t
    from .hexgrid import cell_at, center
    from .config import LAYER

    def uncap():
        old = dict(app.settings)
        app.settings['vsync'] = False
        app.settings['fps_limit'] = 0
        app.apply_settings(old)
        app.set_vsync(False)

    def measure(label, seconds=5.0):
        app.frame_times = []
        n = {'frames': 0}
        t0 = _t.perf_counter()

        def done():
            n['frames'] += 1
            return (_t.perf_counter() - t0) >= seconds

        def finish():
            elapsed = _t.perf_counter() - t0
            fps = n['frames'] / max(elapsed, 1e-6)
            ft = list(app.frame_times)
            s = sum(ft) if ft else 1e-6
            fps_ft = len(ft) / s if ft else 0
            ses = app.session
            st = app.renderer.stats
            log(f'AFTER {label} wall_fps={fps:.2f} frames={n["frames"]} elapsed={elapsed:.3f}s '
                f'ft_fps={fps_ft:.2f} (ft may clamp at 10) chunks={len(ses.world.chunks)} '
                f'drawn={st.get("drawn")} lights={st.get("lights")} '
                f'npcs={len(getattr(ses, "npcs", []) or [])} living={len(ses.sim.active)}')
            return fps

        return {'done': done, 'finish': finish}

    uncap()
    yield 0.3
    app.start_tutorial()
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.8
    app.show_debug = True
    yield shot('after_tutorial_still')
    m = measure('tutorial_still', 5.0)
    yield m['done']
    fps_ts = m['finish']()
    app.test_input = {'fwd': 1, 'hurry': True}
    m = measure('tutorial_walk', 5.0)
    yield m['done']
    fps_tw = m['finish']()
    app.test_input = {}
    # third-person back view of the unclothed wanderer, empty hands
    ses = app.session
    ses.hot = 2
    p = ses.player
    p.pitch = -8.0
    p.yaw = 20.0
    app.cam_view = 1
    app.hide_hud = False
    yield 0.8
    yield shot('wanderer_back')
    app.cam_view = 2
    p.pitch = 6.0
    yield 0.8
    yield shot('wanderer_front')
    app.cam_view = 1
    p.yaw = 200.0
    p.pitch = -12.0
    yield 0.8
    yield shot('wanderer_back_hips')
    app.cam_view = 0
    app.hide_hud = False
    log('AFTER tutorial fps still', round(fps_ts, 2), 'walk', round(fps_tw, 2))

    app.quit_to_title()
    yield 0.8
    seed = -1740201319
    app.create_sky('Perf Normal After', seed, '', 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.8
    app.show_debug = True
    yield shot('after_normal_still')
    m = measure('normal_still', 5.0)
    yield m['done']
    fps_ns = m['finish']()
    app.test_input = {'fwd': 1, 'hurry': True}
    m = measure('normal_walk', 5.0)
    yield m['done']
    fps_nw = m['finish']()
    app.test_input = {}
    log('AFTER normal fps still', round(fps_ns, 2), 'walk', round(fps_nw, 2))
    log('COMPARE after tutorial/normal still', round(fps_ts, 2), '/', round(fps_ns, 2),
        'walk', round(fps_tw, 2), '/', round(fps_nw, 2))

    app.quit_to_title()
    yield 0.8
    CUTS = [
        ('cedar_highlands', -29.99, 147.56, -46.92, 120.0, -18.0),
        ('frostglass', -245.28, 134.03, 43.43, 80.0, -16.0),
        ('chalk_barrens_near', -264.17, 136.97, -23.51, 100.0, -20.0),
        ('cloudstep_isles_far', 2512.22, 177.32, -1386.21, 200.0, -22.0),
        ('chalk_barrens_high', 2415.93, 304.31, -1112.58, 220.0, -28.0),
        ('cloudstep_low', 97.86, 25.25, -107.82, 30.0, 18.0),
        ('verdigris_canyons', -4.06, 147.56, -61.76, 160.0, -18.0),
    ]
    app.create_sky('Cutoff After', -857535443, '', 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    ses = app.session
    p = ses.player
    p.drifting = True
    p.noclip = True
    app.show_debug = True
    app.hide_hud = False
    for name, x, y, z, yaw, pitch in CUTS:
        p.x, p.y, p.z = x, y, z
        p.vx = p.vy = p.vz = 0
        p.yaw, p.pitch = yaw, pitch
        ses.hold = True
        yield settled()
        yield 0.7
        yield shot('after_' + name)
        # a second angle, looking more along a likely hex-axis wall
        p.yaw = (yaw + 70.0) % 360
        p.pitch = pitch - 6.0
        yield 0.5
        yield shot('after_' + name + '_b')
        log('shot', name, 'at', x, y, z, 'cell', cell_at(x, z))
    log('phase143_after finished')


def phase143_figure(app, log, shot, look_at, settled, arg):
    yield 0.3
    app.start_tutorial()
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.2
    ses = app.session
    ses.hot = 2
    p = ses.player
    app.show_debug = True
    app.hide_hud = False
    # back view, slight downward look so the hip bulge reads
    app.cam_view = 1
    p.yaw = 25.0
    p.pitch = -14.0
    yield 0.8
    yield shot('wanderer_back')
    p.yaw = 200.0
    p.pitch = -18.0
    yield 0.7
    yield shot('wanderer_back_hips')
    app.cam_view = 2
    p.yaw = 20.0
    p.pitch = 8.0
    yield 0.7
    yield shot('wanderer_front')
    log('phase143_figure finished')



def phase143_r2_before(app, log, shot, look_at, settled, arg):
    """Full-load v3 before-shots at the seven reported cutoff sites."""
    # user-position vista + closer side / underside. vd=20 ~1310 loaded.
    SITES = [
        # name, x,y,z, vista_yaw, vista_pitch,
        # side cam and look, under cam and look
        dict(name='cedar_highlands', x=-29.99, y=147.56, z=-46.92,
             yaw=312.94, pitch=-34.06,
             sx=-146.2, sy=19.7, sz=-179.7, syaw=222.94, spitch=27.01,
             ux=-146.2, uy=8.0, uz=-179.7, uyaw=222.94, upitch=-20.0,
             # also a mid-height look toward the high coast
             yaw2=227.2, pitch2=20.0),
        dict(name='frostglass', x=-245.28, y=134.03, z=43.43,
             yaw=294.69, pitch=-18.06,
             sx=-364.9, sy=87.7, sz=-31.4, syaw=204.69, spitch=2.15,
             ux=-364.9, uy=73.9, uz=-31.4, uyaw=204.69, upitch=21.25,
             yaw2=18.53, pitch2=-30.0),
        dict(name='chalk_barrens_near', x=-264.17, y=136.97, z=-23.51,
             yaw=265.5, pitch=-24.1,
             sx=-373.8, sy=87.7, sz=-32.9, syaw=175.5, spitch=2.15,
             ux=-373.8, uy=73.9, uz=-32.9, uyaw=175.5, upitch=21.25,
             yaw2=344.17, pitch2=-35.0),
        dict(name='cloudstep_isles_far', x=2512.22, y=177.32, z=-1386.21,
             yaw=283.92, pitch=-14.62,
             sx=2438.7, sy=140.0, sz=-1423.0, syaw=193.92, spitch=12.0,
             ux=2438.7, uy=120.0, uz=-1423.0, uyaw=193.92, upitch=8.0,
             yaw2=303.91, pitch2=-17.29),
        dict(name='chalk_barrens_high', x=2415.93, y=304.31, z=-1112.58,
             yaw=268.44, pitch=-37.29,
             sx=2265.9, sy=200.0, sz=-1126.5, syaw=178.44, spitch=-10.0,
             ux=2265.9, uy=150.0, uz=-1126.5, uyaw=178.44, upitch=8.0,
             yaw2=74.15, pitch2=-35.0),
        dict(name='cloudstep_low', x=97.86, y=25.25, z=-107.82,
             # from under/beside the high island, look up at its underside
             yaw=200.0, pitch=28.0,
             sx=140.0, sy=180.0, sz=-70.0, syaw=240.0, spitch=5.0,
             ux=140.0, uy=160.0, uz=-70.0, uyaw=240.0, upitch=18.0,
             yaw2=343.01, pitch2=8.0),
        dict(name='verdigris_canyons', x=-4.06, y=147.56, z=-61.76,
             yaw=304.15, pitch=-32.45,
             sx=-148.4, sy=19.7, sz=-181.4, syaw=214.15, spitch=27.01,
             ux=-148.4, uy=8.0, uz=-181.4, uyaw=214.15, upitch=-20.0,
             yaw2=225.3, pitch2=-40.0),
    ]

    def uncap_and_far():
        old = dict(app.settings)
        app.settings['vsync'] = False
        app.settings['fps_limit'] = 0
        app.settings['view_distance'] = 20
        app.settings['far_distance'] = 35
        app.apply_settings(old)
        app.set_vsync(False)
        log('vd', app.settings['view_distance'], 'far', app.settings['far_distance'])

    def parked(s, x, y, z, yaw, pitch):
        p = s.player
        p.x, p.y, p.z = x, y, z
        p.yaw, p.pitch = yaw, pitch
        p.vx = p.vy = p.vz = 0
        p.drifting = True
        p.noclip = True
        s.hold = True

    def loaded():
        s = app.session
        w = s.world
        return (w.busy() == 0 and w.busy_lod() == 0 and len(w.chunks) >= 1000)

    uncap_and_far()
    yield 0.3
    app.create_sky('R2 Before', -857535443, '', 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    app.show_debug = True
    app.hide_hud = False
    # jump to the first site immediately so we don't spend the first load at spawn
    s0 = SITES[0]
    parked(ses, s0['x'], s0['y'], s0['z'], s0['yaw'], s0['pitch'])
    yield loaded
    yield 1.0
    for s in SITES:
        parked(ses, s['x'], s['y'], s['z'], s['yaw'], s['pitch'])
        yield loaded
        yield 0.8
        st = app.renderer.stats
        log('SITE', s['name'], 'loaded', len(ses.world.chunks),
            'drawn', st.get('drawn'), 'jobs', ses.world.busy(),
            'lod', ses.world.busy_lod(), 'lights', st.get('lights'))
        yield shot('before_' + s['name'])
        parked(ses, s['x'], s['y'], s['z'], s['yaw2'], s['pitch2'])
        yield 0.6
        yield shot('before_' + s['name'] + '_b')
        parked(ses, s['sx'], s['sy'], s['sz'], s['syaw'], s['spitch'])
        yield loaded
        yield 0.6
        st = app.renderer.stats
        log('SIDE', s['name'], 'loaded', len(ses.world.chunks), 'drawn', st.get('drawn'))
        yield shot('before_' + s['name'] + '_side')
        parked(ses, s['ux'], s['uy'], s['uz'], s['uyaw'], s['upitch'])
        yield 0.6
        yield shot('before_' + s['name'] + '_under')
    log('phase143_r2_before finished')



def phase143_r2_after(app, log, shot, look_at, settled, arg):
    """Full-load v4 after-shots at the same seven positions and angles."""
    SITES = [
        dict(name='cedar_highlands', x=-29.99, y=147.56, z=-46.92,
             yaw=312.94, pitch=-34.06,
             sx=-146.2, sy=19.7, sz=-179.7, syaw=222.94, spitch=27.01,
             ux=-146.2, uy=8.0, uz=-179.7, uyaw=222.94, upitch=-20.0,
             yaw2=227.2, pitch2=20.0),
        dict(name='frostglass', x=-245.28, y=134.03, z=43.43,
             yaw=294.69, pitch=-18.06,
             sx=-364.9, sy=87.7, sz=-31.4, syaw=204.69, spitch=2.15,
             ux=-364.9, uy=73.9, uz=-31.4, uyaw=204.69, upitch=21.25,
             yaw2=18.53, pitch2=-30.0),
        dict(name='chalk_barrens_near', x=-264.17, y=136.97, z=-23.51,
             yaw=265.5, pitch=-24.1,
             sx=-373.8, sy=87.7, sz=-32.9, syaw=175.5, spitch=2.15,
             ux=-373.8, uy=73.9, uz=-32.9, uyaw=175.5, upitch=21.25,
             yaw2=344.17, pitch2=-35.0),
        dict(name='cloudstep_isles_far', x=2512.22, y=177.32, z=-1386.21,
             yaw=283.92, pitch=-14.62,
             sx=2438.7, sy=140.0, sz=-1423.0, syaw=193.92, spitch=12.0,
             ux=2438.7, uy=120.0, uz=-1423.0, uyaw=193.92, upitch=8.0,
             yaw2=303.91, pitch2=-17.29),
        dict(name='chalk_barrens_high', x=2415.93, y=304.31, z=-1112.58,
             yaw=268.44, pitch=-37.29,
             sx=2265.9, sy=200.0, sz=-1126.5, syaw=178.44, spitch=-10.0,
             ux=2265.9, uy=150.0, uz=-1126.5, uyaw=178.44, upitch=8.0,
             yaw2=74.15, pitch2=-35.0),
        dict(name='cloudstep_low', x=97.86, y=25.25, z=-107.82,
             yaw=200.0, pitch=28.0,
             sx=140.0, sy=180.0, sz=-70.0, syaw=240.0, spitch=5.0,
             ux=140.0, uy=160.0, uz=-70.0, uyaw=240.0, upitch=18.0,
             yaw2=343.01, pitch2=8.0),
        dict(name='verdigris_canyons', x=-4.06, y=147.56, z=-61.76,
             yaw=304.15, pitch=-32.45,
             sx=-148.4, sy=19.7, sz=-181.4, syaw=214.15, spitch=27.01,
             ux=-148.4, uy=8.0, uz=-181.4, uyaw=214.15, upitch=-20.0,
             yaw2=225.3, pitch2=-40.0),
    ]

    def uncap_and_far():
        old = dict(app.settings)
        app.settings['vsync'] = False
        app.settings['fps_limit'] = 0
        app.settings['view_distance'] = 20
        app.settings['far_distance'] = 35
        app.apply_settings(old)
        app.set_vsync(False)
        log('vd', app.settings['view_distance'], 'far', app.settings['far_distance'])

    def parked(s, x, y, z, yaw, pitch):
        p = s.player
        p.x, p.y, p.z = x, y, z
        p.yaw, p.pitch = yaw, pitch
        p.vx = p.vy = p.vz = 0
        p.drifting = True
        p.noclip = True
        s.hold = True

    def loaded():
        s = app.session
        w = s.world
        return (w.busy() == 0 and w.busy_lod() == 0 and len(w.chunks) >= 1000)

    uncap_and_far()
    yield 0.3
    app.create_sky('R2 After', -857535443, '', 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    app.show_debug = True
    app.hide_hud = False
    ver = (ses.world.gen_settings or {}).get('generator_version')
    log('generator_version', ver)
    s0 = SITES[0]
    parked(ses, s0['x'], s0['y'], s0['z'], s0['yaw'], s0['pitch'])
    yield loaded
    yield 1.0
    for s in SITES:
        parked(ses, s['x'], s['y'], s['z'], s['yaw'], s['pitch'])
        yield loaded
        yield 0.8
        st = app.renderer.stats
        log('SITE', s['name'], 'loaded', len(ses.world.chunks),
            'drawn', st.get('drawn'), 'jobs', ses.world.busy(),
            'lod', ses.world.busy_lod(), 'gen', ver)
        yield shot('after_' + s['name'])
        parked(ses, s['x'], s['y'], s['z'], s['yaw2'], s['pitch2'])
        yield 0.6
        yield shot('after_' + s['name'] + '_b')
        parked(ses, s['sx'], s['sy'], s['sz'], s['syaw'], s['spitch'])
        yield loaded
        yield 0.6
        st = app.renderer.stats
        log('SIDE', s['name'], 'loaded', len(ses.world.chunks), 'drawn', st.get('drawn'))
        yield shot('after_' + s['name'] + '_side')
        parked(ses, s['ux'], s['uy'], s['uz'], s['uyaw'], s['upitch'])
        yield 0.6
        yield shot('after_' + s['name'] + '_under')
    log('phase143_r2_after finished')


def phase143_r2_figure(app, log, shot, look_at, settled, arg):
    """Back, three-quarter and side shots of the embedded wanderer hips."""
    import math
    from tidewake.mathutil import forward_vector

    yield 0.3
    app.start_tutorial()
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.8
    ses = app.session
    p = ses.player
    p.vx = p.vy = p.vz = 0
    p.drifting = True
    p.noclip = True
    ses.hold = True
    app.show_debug = False
    app.hide_hud = True
    app.cam_view = 1
    p.yaw = 20.0
    p.pitch = 0.0

    def look_at_hips(bearing, dist=3.15, cam_up=0.28, hip_up=0.52):
        def camera():
            fx, fy, fz = forward_vector(p.yaw, 0.0)
            rx, rz = -fz, fx
            ang = math.radians(bearing)
            ox = -fx * math.cos(ang) * dist + rx * math.sin(ang) * dist
            oz = -fz * math.cos(ang) * dist + rz * math.sin(ang) * dist
            tx, ty, tz = p.x, p.y + hip_up, p.z
            cx, cy, cz = tx + ox, ty + cam_up, tz + oz
            yaw = math.degrees(math.atan2(tx - cx, -(tz - cz))) % 360.0
            pitch = math.degrees(math.atan2(ty - cy, math.hypot(tx - cx, tz - cz)))
            return (cx, cy, cz), yaw, pitch, ses.phase, ses.world
        app.camera = camera

    look_at_hips(0.0, dist=1.85, cam_up=0.22)
    yield 0.7
    yield shot('wanderer_back')
    look_at_hips(6.0, dist=1.45, cam_up=0.12, hip_up=0.52)
    yield 0.6
    yield shot('wanderer_back_hips')
    look_at_hips(62.0, dist=1.90, cam_up=0.20)
    yield 0.6
    yield shot('wanderer_three_quarter')
    look_at_hips(90.0, dist=1.85, cam_up=0.18)
    yield 0.6
    yield shot('wanderer_side')
    look_at_hips(-90.0, dist=1.85, cam_up=0.18)
    yield 0.6
    yield shot('wanderer_side_left')
    log('phase143_r2_figure finished')



def phase143_r2_perf(app, log, shot, look_at, settled, arg):
    """Wall-clock fps in the tutorial and a normal v4 sky (uncapped)."""
    import time as _t

    def uncap():
        old = dict(app.settings)
        app.settings['vsync'] = False
        app.settings['fps_limit'] = 0
        app.apply_settings(old)
        app.set_vsync(False)
        log('uncapped vsync', app.settings['vsync'], 'fps_limit', app.settings['fps_limit'])

    def sample(label, seconds=5.0):
        state = {'t0': _t.perf_counter(), 'frames': 0, 'sec': seconds}

        def done():
            state['frames'] += 1
            return (_t.perf_counter() - state['t0']) >= state['sec']

        def finish():
            elapsed = _t.perf_counter() - state['t0']
            frames = max(1, state['frames'] - 1)
            fps = frames / elapsed if elapsed > 0 else 0.0
            st = app.renderer.stats
            ses = app.session
            log('PERF', label, 'fps=%.1f' % fps, 'frames', frames, 'elapsed=%.3f' % elapsed,
                'chunks', len(ses.world.chunks), 'drawn', st.get('drawn'),
                'lights', st.get('lights'), 'tutorial', bool(getattr(ses, 'tutorial', False)),
                'seed', ses.seed, 'gen', (ses.world.gen_settings or {}).get('generator_version'))
            return fps

        return {'done': done, 'finish': finish}

    uncap()
    yield 0.4
    app.start_tutorial()
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    app.show_debug = True
    app.hide_hud = False
    yield shot('perf_tutorial_still')
    tut_still = sample('tutorial_still', 5.0)
    yield tut_still['done']
    fps_tut_still = tut_still['finish']()
    app.test_input = {'fwd': 1, 'hurry': True}
    tut_walk = sample('tutorial_walk', 5.0)
    yield tut_walk['done']
    fps_tut_walk = tut_walk['finish']()
    app.test_input = {}
    yield shot('perf_tutorial_walk')
    log('TUTORIAL fps still', round(fps_tut_still, 2), 'walk', round(fps_tut_walk, 2))

    app.quit_to_title()
    yield 0.8
    app.create_sky('Perf Normal v4', -1740201319, '', 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    app.show_debug = True
    yield shot('perf_normal_still')
    n_still = sample('normal_still', 5.0)
    yield n_still['done']
    fps_n_still = n_still['finish']()
    app.test_input = {'fwd': 1, 'hurry': True}
    n_walk = sample('normal_walk', 5.0)
    yield n_walk['done']
    fps_n_walk = n_walk['finish']()
    app.test_input = {}
    yield shot('perf_normal_walk')
    log('NORMAL fps still', round(fps_n_still, 2), 'walk', round(fps_n_walk, 2))
    log('COMPARE tutorial/normal still', round(fps_tut_still, 2), '/', round(fps_n_still, 2),
        'walk', round(fps_tut_walk, 2), '/', round(fps_n_walk, 2))
    log('phase143_r2_perf finished')



def phase143_r2_vistas(app, log, shot, look_at, settled, arg):
    """v4 aerial and lookup shots, comparable to the 1.4.2 wide showcases."""
    from tidewake.hexgrid import center
    from tidewake.config import LAYER

    def uncap_and_far():
        old = dict(app.settings)
        app.settings['vsync'] = False
        app.settings['fps_limit'] = 0
        app.settings['view_distance'] = 20
        app.settings['far_distance'] = 35
        app.apply_settings(old)
        app.set_vsync(False)

    def parked(s, x, y, z, yaw, pitch):
        p = s.player
        p.x, p.y, p.z = x, y, z
        p.yaw, p.pitch = yaw, pitch
        p.vx = p.vy = p.vz = 0
        p.drifting = True
        p.noclip = True
        s.hold = True

    def loaded():
        w = app.session.world
        return w.busy() == 0 and w.busy_lod() == 0 and len(w.chunks) >= 1000

    uncap_and_far()
    yield 0.3
    # seed 7 has a ~155-cell, nearly-300 continent — a fair compare to 1.4.2 aerial_wide_2
    app.create_sky('R2 Vistas', 7, '', 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    app.show_debug = True
    app.hide_hud = False
    px, pz = center(11, 132)
    parked(ses, px + 80, (286 + 52) * LAYER, pz + 50, 300.0, -28.0)
    yield loaded
    yield 1.0
    st = app.renderer.stats
    log('aerial', 'loaded', len(ses.world.chunks), 'drawn', st.get('drawn'),
        'jobs', ses.world.busy(), 'gen', (ses.world.gen_settings or {}).get('generator_version'))
    yield shot('v4_aerial_wide')
    parked(ses, px + 110, (286 + 40) * LAYER, pz + 20, 290.0, -26.0)
    yield 0.8
    yield shot('v4_aerial_wide_b')
    # lookup from a mid island toward the high continent
    mx, mz = center(13, 59)
    parked(ses, mx, 226 * LAYER + 8.0, mz, 200.0, 14.0)
    yield loaded
    yield 0.8
    yield shot('v4_tall_islands_lookup')
    parked(ses, mx, 226 * LAYER + 16.0, mz, 200.0, 8.0)
    yield 0.7
    yield shot('v4_tall_islands_lookup_wide')
    # stand on the continent and look across its surface
    parked(ses, px, 286 * LAYER + 3.0, pz, 40.0, -12.0)
    yield 0.8
    yield shot('v4_continent_surface')
    log('phase143_r2_vistas finished')


# ---------------------------------------------------------------------------
# 1.4.4
# ---------------------------------------------------------------------------

def _144_uncap(app, log, view=16, far=24):
    old = dict(app.settings)
    app.settings['vsync'] = False
    app.settings['fps_limit'] = 0
    app.settings['view_distance'] = view
    app.settings['far_distance'] = far
    app.apply_settings(old)
    app.set_vsync(False)
    log('vd', app.settings['view_distance'], 'far', app.settings['far_distance'])


def _144_park(ses, x, y, z, yaw, pitch):
    p = ses.player
    p.x, p.y, p.z = x, y, z
    p.yaw, p.pitch = yaw, pitch
    p.vx = p.vy = p.vz = 0
    p.drifting = True
    p.noclip = True
    ses.hold = True


def _144_loaded(app, min_chunks=0):
    def ok():
        s = app.session
        if s is None or app.mode != 'game':
            return False
        w = s.world
        return (w.busy() == 0 and w.busy_lod() == 0 and not w.dirty
                and len(w.chunks) >= min_chunks)
    return ok


def _144_hud(app, debug=False, hide=True):
    app.show_debug = debug
    app.hide_hud = hide


def phase144_tutorial(app, log, shot, look_at, settled, arg):
    """Lesson island from spawn (distant landmark visible) and an aerial."""
    from . import tutorial as T
    from . import landmark as LM
    from .hexgrid import center as hx
    _144_uncap(app, log, view=16, far=24)
    yield 0.3
    app.create_sky('Lesson 144', 1, 'lesson', 'wanderer', tutorial=True)
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    # Canonical spawn pose: yaw 0 looks -Z at the citadel, pitch slightly up.
    q, r, top = T.SPAWN
    x, z = hx(q, r)
    _144_park(ses, x, (top + 1) * LAYER + 0.001, z, 0.0, 4.0)
    yield _144_loaded(app)
    yield 1.2
    _144_hud(app, debug=False, hide=True)
    yield shot('tutorial_spawn')
    _144_hud(app, debug=True, hide=False)
    yield 0.3
    yield shot('tutorial_spawn_debug')
    # A step to the side so Willow and the plaza sit in frame with the citadel
    _144_park(ses, x + 4.0, (top + 1) * LAYER + 0.001, z + 2.0, 350.0, 6.0)
    yield _144_loaded(app)
    yield 0.8
    _144_hud(app, debug=False, hide=True)
    yield shot('tutorial_plaza')
    # Look along the path toward Bram
    _144_park(ses, x, (top + 1.2) * LAYER, z, 70.0, 2.0)
    yield 0.8
    yield shot('tutorial_path_east')
    # Shrine knoll, citadel still beyond
    sx, _, sz = T.shrine_pos()
    _144_park(ses, sx, (T.SURF + 6) * LAYER, sz + 6, 0.0, 8.0)
    yield _144_loaded(app)
    yield 0.8
    yield shot('tutorial_shrine_knoll')
    # From the north, looking south over the lobes toward the plaza, knoll, and citadel
    _144_park(ses, 15.0, 85.0, 110.0, 0.0, -28.0)
    yield _144_loaded(app)
    yield 1.2
    yield shot('tutorial_aerial')
    # Higher and a little east, still looking south so the citadel stays in frame
    _144_park(ses, 25.0, 120.0, 80.0, 10.0, -42.0)
    yield _144_loaded(app)
    yield 1.0
    yield shot('tutorial_aerial_wide')
    # From the east, looking west across the workshop, kiln, house and farm
    _144_park(ses, 90.0, 85.0, 40.0, 270.0, -28.0)
    yield _144_loaded(app)
    yield 1.0
    yield shot('tutorial_aerial_east')
    log('landmark pos', LM.POS, 'verts', len(LM.mesh()), 'spawn yaw 0 pitch 4')
    log('phase144_tutorial finished')


def phase144_islands(app, log, shot, look_at, settled, arg):
    """v5 scale versus v4, plus a huge-continent aerial on seed 7."""
    from .hexgrid import center as hx
    from . import gensettings as GS

    def tour_version(ver, label):
        _144_uncap(app, log, view=20, far=35)
        yield 0.3
        app.create_sky(label, 7, 'seven', 'wanderer',
                       gen=GS.normalize({'generator_version': ver}))
        yield lambda: app.mode == 'game'
        yield settled()
        yield 1.0
        ses = app.session
        log('version', (ses.world.gen_settings or {}).get('generator_version'), 'seed', ses.seed)
        # Origin cluster aerial
        _144_park(ses, 0.0, 280.0, 180.0, 180.0, -55.0)
        yield _144_loaded(app, min_chunks=200)
        yield 1.2
        _144_hud(app, debug=False, hide=True)
        yield shot(f'{label}_origin_aerial')
        _144_hud(app, debug=True, hide=False)
        yield 0.3
        yield shot(f'{label}_origin_aerial_debug')
        # A slightly lower look at near-origin islands
        _144_park(ses, 40.0, 200.0, 80.0, 210.0, -28.0)
        yield _144_loaded(app)
        yield 1.0
        _144_hud(app, debug=False, hide=True)
        yield shot(f'{label}_origin_vista')

    # v5 first
    for step in tour_version(5, 'v5'):
        yield step
    ses = app.session
    # Huge continent around (527, -352)
    hx_x, hx_z = hx(527, -352)
    log('huge centre xz', hx_x, hx_z)
    _144_park(ses, hx_x, 420.0, hx_z + 220.0, 180.0, -55.0)
    yield _144_loaded(app, min_chunks=200)
    yield 1.4
    _144_hud(app, debug=False, hide=True)
    yield shot('v5_huge_aerial')
    _144_hud(app, debug=True, hide=False)
    yield 0.3
    yield shot('v5_huge_aerial_debug')
    # Closer aerial, shallower pitch
    _144_park(ses, hx_x - 80.0, 320.0, hx_z + 160.0, 160.0, -38.0)
    yield _144_loaded(app)
    yield 1.2
    _144_hud(app, debug=False, hide=True)
    yield shot('v5_huge_aerial_low')
    # Surface on the continent
    top = ses.world.column_top(527, -352) or 120
    _144_park(ses, hx_x, (top + 8) * LAYER, hx_z + 18, 200.0, -8.0)
    yield _144_loaded(app)
    yield 1.0
    yield shot('v5_huge_surface')
    # Peak look (known high point near 627, -204)
    px, pz = hx(627, -204)
    ptop = ses.world.column_top(627, -204) or 200
    _144_park(ses, px, (ptop + 6) * LAYER, pz, 220.0, -18.0)
    yield _144_loaded(app)
    yield 1.0
    yield shot('v5_huge_peak')

    app.quit_to_title()
    yield 1.0
    # v4 of the same seed, for scale comparison (this is the 1.4.3 generator)
    for step in tour_version(4, 'v4'):
        yield step
    # The 1.4.3 "continent" reference cell (11, 132)
    ses = app.session
    cx, cz = hx(11, 132)
    ctop = ses.world.column_top(11, 132) or 120
    _144_park(ses, cx, 320.0, cz + 160.0, 180.0, -50.0)
    yield _144_loaded(app)
    yield 1.2
    _144_hud(app, debug=False, hide=True)
    yield shot('v4_ref_continent_aerial')
    log('phase144_islands finished')


def phase144_blocks(app, log, shot, look_at, settled, arg):
    """Palette swatch board and tight close-ups of the fun / decorative blocks."""
    from . import palette as PAL
    from . import gensettings as GS
    from .hexgrid import center as hx
    _144_uncap(app, log, view=12, far=16)
    yield 0.3
    app.create_sky('Palette 144', 7, 'seven', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.6
    ses = app.session
    ses.phase = 0.08
    ses.weather = 'clear'
    # A high open pad at a known cell. Load those chunks first: world.set no-ops if unloaded.
    q0, r0, y0 = 8, 8, 140
    bx, bz = hx(q0 + 8, r0 + 5)
    _144_park(ses, bx, (y0 + 10) * LAYER, bz, 0.0, -20.0)
    yield _144_loaded(app)
    yield 0.8
    dyes = [d[0] for d in PAL.DYES]
    families = ['patterned_tile', 'terrazzo', 'woven_panel', 'stained_glass',
                'crystal_lamp', 'banner']
    uniques = [
        'ivory_plaster', 'blush_plaster', 'sage_plaster', 'dusk_plaster',
        'pewter', 'brass', 'copper', 'wrought_iron',
        'ochre_bricks', 'ink_bricks', 'wood_lattice', 'pale_lattice',
        'rose_jelly', 'tide_jelly', 'honey_jelly', 'violet_jelly',
        'ink_checker', 'rose_checker', 'rose_stripe', 'sky_stripe',
        'shimmer_cloud', 'cosmic_star',
    ]
    floor = M.get('dusk_plaster', M.get('ink_bricks', M['stone']))
    placed = 0
    missed = 0

    def put(q, r, y, mat):
        nonlocal placed, missed
        if mat is None:
            missed += 1
            return
        ok = ses.world.set(q, r, y, mat)
        if ok:
            placed += 1
        else:
            missed += 1

    # Dark pad so the swatches read clearly, lit from above
    width, depth = 20, 20
    for dq in range(-2, width):
        for dr in range(-2, depth):
            q, r = q0 + dq, r0 + dr
            for yy in range(y0 - 2, y0):
                put(q, r, yy, M['stone'])
            put(q, r, y0, floor)
            for yy in range(y0 + 1, y0 + 10):
                put(q, r, yy, 0)
    # Family rows: 4-high pillars, one row per family, a gap between rows
    for fi, fam in enumerate(families):
        for di, dye in enumerate(dyes):
            key = PAL.id_key(PAL.dyed_name(fam, dye)) if hasattr(PAL, 'dyed_name') else f'{dye}_{fam}'
            mat = M.get(key, M.get(f'{dye}_{fam}'))
            rr = r0 + fi * 2
            for h in range(1, 5):
                put(q0 + di, rr, y0 + h, mat)
    # Unique / fun pillars, two rows below the families
    uniq_r = r0 + len(families) * 2 + 2
    for i, key in enumerate(uniques):
        mat = M.get(key)
        for h in range(1, 5):
            put(q0 + (i % 16), uniq_r + i // 16, y0 + h, mat)
    # A few extra lamps over the board so it stays well lit
    lamp = M.get('honey_crystal_lamp', M.get('ember_lamp', M['lantern']))
    for dq, dr in ((-1, 3), (16, 3), (7, -1), (7, 14)):
        put(q0 + dq, r0 + dr, y0 + 6, lamp)
    log('palette stamped', 'placed', placed, 'missed', missed,
        'families', families, 'uniques', len(uniques),
        'sample', int(ses.world.get(q0, r0, y0 + 2) or 0))
    if placed < 100:
        log('ERROR palette stamp too sparse — aborting shots')
        return
    yield settled()
    yield 1.0
    ses.phase = 0.08
    ses.weather = 'clear'
    _144_hud(app, debug=False, hide=True)

    def frame(q, r, y, back=8.0, up=3.5, side=0.0):
        tx, tz = hx(q, r)
        ty = y * LAYER + 0.4
        _144_park(ses, tx + side, ty + up, tz + back, 0.0, -20.0)
        look_at(ses.player, tx, ty, tz)

    # Full swatch board, close enough that the pillars fill the frame
    mid_r = r0 + 5
    frame(q0 + 8, mid_r, y0 + 2, back=14.0, up=6.0, side=1.0)
    yield _144_loaded(app)
    yield 0.9
    yield shot('palette_board')
    frame(q0 + 8, mid_r, y0 + 2, back=9.0, up=4.0, side=0.5)
    yield 0.8
    yield shot('palette_board_close')

    # Tight close-ups: fill the frame with the actual blocks
    close = [
        ('fun_jelly', q0 + 12, uniq_r, y0 + 2, 4.2, 1.8, 0.4),           # rose/tide/honey/violet jelly
        ('fun_checker_stripe', q0 + 2, uniq_r + 1, y0 + 2, 4.2, 1.8, 0.4),  # checkers + stripes
        ('fun_metal_plaster', q0 + 4, uniq_r, y0 + 2, 4.6, 1.9, 0.2),      # plasters into pewter/brass/copper/iron
        ('fun_crystal_lamps', q0 + 8, r0 + 8, y0 + 2, 4.4, 1.8, 0.3),      # crystal lamp row
        ('fun_stained_glass', q0 + 8, r0 + 6, y0 + 2, 4.4, 1.8, 0.3),      # stained glass row
        ('fun_cosmic_cloud', q0 + 4, uniq_r + 1, y0 + 2, 4.2, 1.8, 0.3),   # shimmer cloud + cosmic star
    ]
    for name, q, r, y, back, up, side in close:
        frame(q, r, y, back=back, up=up, side=side)
        yield _144_loaded(app)
        yield 0.7
        yield shot(name)
    log('phase144_blocks finished')


def phase144_blocks_fix(app, log, shot, look_at, settled, arg):
    """Retake metal/plaster and stained-glass close-ups from angles that are not blocked."""
    from . import palette as PAL
    from . import gensettings as GS
    from .hexgrid import center as hx
    _144_uncap(app, log, view=12, far=16)
    yield 0.3
    app.create_sky('Palette 144 fix', 7, 'seven', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.5
    ses = app.session
    ses.phase = 0.08
    ses.weather = 'clear'
    q0, r0, y0 = 8, 8, 140
    bx, bz = hx(q0 + 8, r0 + 5)
    _144_park(ses, bx, (y0 + 10) * LAYER, bz, 0.0, -20.0)
    yield _144_loaded(app)
    yield 0.6
    dyes = [d[0] for d in PAL.DYES]
    families = ['patterned_tile', 'terrazzo', 'woven_panel', 'stained_glass',
                'crystal_lamp', 'banner']
    uniques = [
        'ivory_plaster', 'blush_plaster', 'sage_plaster', 'dusk_plaster',
        'pewter', 'brass', 'copper', 'wrought_iron',
        'ochre_bricks', 'ink_bricks', 'wood_lattice', 'pale_lattice',
        'rose_jelly', 'tide_jelly', 'honey_jelly', 'violet_jelly',
        'ink_checker', 'rose_checker', 'rose_stripe', 'sky_stripe',
        'shimmer_cloud', 'cosmic_star',
    ]
    floor = M.get('dusk_plaster', M['stone'])

    def put(q, r, y, mat):
        if mat is not None:
            ses.world.set(q, r, y, mat)

    for dq in range(-2, 20):
        for dr in range(-2, 20):
            q, r = q0 + dq, r0 + dr
            for yy in range(y0 - 2, y0):
                put(q, r, yy, M['stone'])
            put(q, r, y0, floor)
            for yy in range(y0 + 1, y0 + 10):
                put(q, r, yy, 0)
    for fi, fam in enumerate(families):
        for di, dye in enumerate(dyes):
            key = PAL.id_key(PAL.dyed_name(fam, dye))
            mat = M.get(key, M.get(f'{dye}_{fam}'))
            for h in range(1, 5):
                put(q0 + di, r0 + fi * 2, y0 + h, mat)
    uniq_r = r0 + len(families) * 2 + 2
    for i, key in enumerate(uniques):
        mat = M.get(key)
        for h in range(1, 5):
            put(q0 + (i % 16), uniq_r + i // 16, y0 + h, mat)
    lamp = M.get('honey_crystal_lamp', M['lantern'])
    for dq, dr in ((-1, 3), (16, 3), (7, -1), (7, 14)):
        put(q0 + dq, r0 + dr, y0 + 6, lamp)
    yield settled()
    yield 1.0
    ses.phase = 0.08
    ses.weather = 'clear'
    _144_hud(app, debug=False, hide=True)

    def frame_from(q, r, y, back, up, side, toward=+1):
        """toward=+1: camera at +Z looking -Z (yaw 0). toward=-1: camera at -Z looking +Z (yaw 180)."""
        tx, tz = hx(q, r)
        ty = y * LAYER + 0.4
        _144_park(ses, tx + side, ty + up, tz + toward * back, 0.0, 0.0)
        look_at(ses.player, tx, ty, tz)

    # Metal + plaster: view from -Z so the checker row is behind the subject, not in front
    frame_from(q0 + 4, uniq_r, y0 + 2, back=4.8, up=1.8, side=0.2, toward=-1)
    yield _144_loaded(app)
    yield 0.8
    yield shot('fun_metal_plaster')
    # Stained glass: view from -Z so lamps/banners sit behind the glass as a glow, not in front
    frame_from(q0 + 8, r0 + 6, y0 + 2, back=4.6, up=1.7, side=0.3, toward=-1)
    yield _144_loaded(app)
    yield 0.8
    yield shot('fun_stained_glass')
    log('phase144_blocks_fix finished')


def phase144_structures(app, log, shot, look_at, settled, arg):
    """Stamp and photograph the new landscape and sky structures."""
    from . import structures as ST
    from . import gensettings as GS
    _144_uncap(app, log, view=14, far=20)
    yield 0.3
    app.create_sky('Structures 144', 11, 'structure-row', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.6
    ses = app.session
    # High terrace; load the site first because world.set skips unloaded chunks.
    q0, r0, y0 = 4, 4, 140
    ox, oz = center(q0 + 36, r0)
    _144_park(ses, ox, (y0 + 16) * LAYER, oz, 0.0, -10.0)
    yield _144_loaded(app)
    yield 0.6
    for dq in range(-8, 80):
        for dr in range(-10, 16):
            q, r = q0 + dq, r0 + dr
            for yy in range(y0 - 3, y0):
                ses.world.set(q, r, yy, M['stone'])
            ses.world.set(q, r, y0, M.get('ivory_plaster', M['pale_planks']))
            for yy in range(y0 + 1, y0 + 16):
                ses.world.set(q, r, yy, 0)
    yield settled()
    ground_types = ['hamlet', 'watchtower', 'shrine', 'windmill', 'lighthouse',
                    'market', 'garden', 'observatory', 'ruin_tower']
    sky_types = ['sky_temple', 'airship_wreck', 'chain_fort', 'balloon_platform',
                 'crystal_pinnacle', 'lantern_cluster']
    # Place ground types along the terrace
    for i, name in enumerate(ground_types):
        q, r = q0 + 6 + i * 8, r0
        try:
            ST.stamp_world(ses.world, q, r, name, cond=ST.INTACT, seed=20 + i, realm=0)
            log('stamped', name, 'at', q, r)
        except Exception as e:
            log('stamp failed', name, e)
    # Cloud pads + sky types beside / above the terrace
    for i, name in enumerate(sky_types):
        q, r = q0 + 6 + i * 8, r0 + 10
        pad = M.get('shimmer_cloud', M['stone'])
        for dq in range(-3, 4):
            for dr in range(-3, 4):
                ses.world.set(q + dq, r + dr, y0 + 8, pad)
        try:
            ST.stamp_world(ses.world, q, r, name, cond=ST.INTACT, seed=40 + i, realm=7)
            log('stamped sky', name, 'at', q, r)
        except Exception as e:
            log('stamp failed', name, e)
    yield settled()
    yield 1.2
    ses.phase = 0.08
    ses.weather = 'clear'
    _144_hud(app, debug=False, hide=True)
    # Overview of the row: stand +Z of the terrace and look -Z at the builds
    ox, oz = center(q0 + 36, r0)
    _144_park(ses, ox, (y0 + 18) * LAYER, oz + 28, 0.0, -22.0)
    look_at(ses.player, ox, (y0 + 6) * LAYER, oz)
    yield _144_loaded(app)
    yield 1.0
    yield shot('structures_row')
    # Each ground type
    for i, name in enumerate(ground_types):
        q, r = q0 + 6 + i * 8, r0
        x, z = center(q, r)
        tx, tz = x, z
        _144_park(ses, x + 2, (y0 + 9) * LAYER, z + 14, 0.0, -12.0)
        look_at(ses.player, tx, (y0 + 4) * LAYER, tz)
        yield _144_loaded(app)
        yield 0.7
        yield shot(f'structure_{name}')
    # Each sky type
    for i, name in enumerate(sky_types):
        q, r = q0 + 6 + i * 8, r0 + 10
        x, z = center(q, r)
        _144_park(ses, x + 2, (y0 + 16) * LAYER, z + 14, 0.0, -10.0)
        look_at(ses.player, x, (y0 + 11) * LAYER, z)
        yield _144_loaded(app)
        yield 0.7
        yield shot(f'structure_{name}')
    # A couple of natural placements in a live v5 seed-7 sky
    app.quit_to_title()
    yield 1.0
    app.create_sky('Natural 144', 7, 'seven', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    # Hunt loaded chunks for new decorative blocks
    found = []
    banner_ids = {M[k] for k in M if k.endswith('_banner')}
    lamp_ids = {M[k] for k in M if k.endswith('_crystal_lamp')}
    markers = set(banner_ids) | set(lamp_ids) | {M.get('shimmer_cloud', 0), M.get('cosmic_star', 0),
                                                 M.get('ivory_plaster', 0), M['chest']}
    markers.discard(0)
    for (cq, cr), ch in list(ses.world.chunks.items()):
        cells = ch.cells
        hits = 0
        for mid in markers:
            hits += int((cells == mid).sum())
        if hits >= 4:
            # pick a cell
            for lq in range(0, CHUNK, 2):
                for lr in range(0, CHUNK, 2):
                    col = cells[lq, :, lr]
                    ys = np.where(np.isin(col, list(markers)))[0]
                    if len(ys):
                        found.append((cq * CHUNK + lq, cr * CHUNK + lr, int(ys[-1]), hits))
                        break
                else:
                    continue
                break
        if len(found) >= 8:
            break
    log('natural sites', found[:8])
    for i, (q, r, y, hits) in enumerate(found[:6]):
        x, z = center(q, r)
        _144_park(ses, x - 8, (y + 8) * LAYER, z + 14, 155.0, -10.0)
        yield _144_loaded(app)
        yield 0.8
        _144_hud(app, debug=False, hide=True)
        yield shot(f'natural_{i}')
    log('phase144_structures finished')


def phase144_structures_close(app, log, shot, look_at, settled, arg):
    """Farther-back close-ups so each named structure is fully in frame."""
    from . import structures as ST
    from . import gensettings as GS
    _144_uncap(app, log, view=14, far=20)
    yield 0.3
    app.create_sky('Structures 144 close', 13, 'structure-close', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.5
    ses = app.session
    ses.phase = 0.08
    ses.weather = 'clear'
    q0, r0, y0 = 4, 4, 150
    spacing = 22
    names = ['hamlet', 'watchtower', 'shrine', 'windmill', 'market',
             'airship_wreck', 'balloon_platform']
    # Load a long terrace first
    mid_q = q0 + (len(names) // 2) * spacing
    ox, oz = center(mid_q, r0)
    _144_park(ses, ox, (y0 + 20) * LAYER, oz, 0.0, -20.0)
    yield _144_loaded(app)
    yield 0.8
    # Wide flatten so each stamp has room
    for dq in range(-8, len(names) * spacing + 8):
        for dr in range(-10, 14):
            q, r = q0 + dq, r0 + dr
            for yy in range(y0 - 3, y0):
                ses.world.set(q, r, yy, M['stone'])
            ses.world.set(q, r, y0, M.get('ivory_plaster', M['pale_planks']))
            for yy in range(y0 + 1, y0 + 20):
                ses.world.set(q, r, yy, 0)
    yield settled()
    for i, name in enumerate(names):
        q, r = q0 + 8 + i * spacing, r0
        if name in ('airship_wreck', 'balloon_platform'):
            pad = M.get('shimmer_cloud', M['stone'])
            for dq in range(-4, 5):
                for dr in range(-4, 5):
                    ses.world.set(q + dq, r + dr, y0 + 6, pad)
            try:
                ST.stamp_world(ses.world, q, r, name, cond=ST.INTACT, seed=80 + i, realm=0)
                log('stamped', name, 'at', q, r)
            except Exception as e:
                log('stamp failed', name, e)
        else:
            try:
                ST.stamp_world(ses.world, q, r, name, cond=ST.INTACT, seed=80 + i, realm=0)
                log('stamped', name, 'at', q, r)
            except Exception as e:
                log('stamp failed', name, e)
    yield settled()
    yield 1.2
    _144_hud(app, debug=False, hide=True)
    # (back, up, side) in world units — far enough to fit the whole build
    frames = {
        'hamlet': (22.0, 9.0, 6.0),
        'watchtower': (20.0, 12.0, 5.0),
        'shrine': (16.0, 8.0, 4.0),
        'windmill': (22.0, 11.0, 6.0),
        'market': (20.0, 8.0, 5.0),
        'airship_wreck': (20.0, 9.0, 7.0),
        'balloon_platform': (22.0, 8.0, 6.0),
    }
    for i, name in enumerate(names):
        q, r = q0 + 8 + i * spacing, r0
        x, z = center(q, r)
        back, up, side = frames[name]
        # sky types sit on a pad a little above the terrace
        base = (y0 + 6) if name in ('airship_wreck', 'balloon_platform') else y0
        _144_park(ses, x + side, (base + up) * LAYER, z + back, 0.0, -18.0)
        look_at(ses.player, x, (base + 4) * LAYER, z)
        yield _144_loaded(app)
        yield 0.9
        yield shot(f'structure_{name}')
        log('framed', name, 'at', x, z)
    log('phase144_structures_close finished')


def phase144_perf(app, log, shot, look_at, settled, arg):
    """Wall-clock fps on the new lesson island (uncapped), still and walk."""
    import time as _t
    from . import tutorial as T
    from .hexgrid import center as hx

    def uncap():
        old = dict(app.settings)
        app.settings['vsync'] = False
        app.settings['fps_limit'] = 0
        # Match the 1.4.3 tutorial measurement window as closely as we can.
        app.settings['view_distance'] = app.settings.get('view_distance', 8)
        app.apply_settings(old)
        app.set_vsync(False)
        log('uncapped vsync', app.settings['vsync'], 'fps_limit', app.settings['fps_limit'],
            'vd', app.settings['view_distance'], 'far', app.settings['far_distance'])

    def sample(label, seconds=5.0):
        state = {'t0': _t.perf_counter(), 'frames': 0, 'sec': seconds}

        def done():
            state['frames'] += 1
            return (_t.perf_counter() - state['t0']) >= state['sec']

        def finish():
            elapsed = _t.perf_counter() - state['t0']
            frames = max(1, state['frames'] - 1)
            fps = frames / elapsed if elapsed > 0 else 0.0
            st = app.renderer.stats
            ses = app.session
            w = ses.world
            log('PERF', label, 'fps=%.1f' % fps, 'frames', frames, 'elapsed=%.3f' % elapsed,
                'chunks', len(w.chunks), 'drawn', st.get('drawn'),
                'lights', st.get('lights'), 'busy', w.busy(), 'lod', w.busy_lod(),
                'jobs', len(w.gen_jobs) + len(w.mesh_jobs),
                'verts_landmark', 0, 'tutorial', bool(getattr(ses, 'tutorial', False)))
            return fps

        return {'done': done, 'finish': finish}

    uncap()
    yield 0.4
    # Fresh lesson, never reopen a saved compact 1.4.3 island
    app.create_sky('Lesson Perf 144', 1, 'lesson', 'wanderer', tutorial=True)
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.2
    ses = app.session
    q, r, top = T.SPAWN
    x, z = hx(q, r)
    _144_park(ses, x, (top + 1) * LAYER + 0.001, z, 0.0, 4.0)
    ses.player.drifting = False
    ses.player.noclip = False
    ses.hold = False
    yield settled()
    yield 1.0
    app.show_debug = True
    app.hide_hud = False
    yield shot('perf_tutorial_still')
    tut_still = sample('tutorial_still', 5.0)
    yield tut_still['done']
    fps_tut_still = tut_still['finish']()
    app.test_input = {'fwd': 1, 'hurry': True}
    tut_walk = sample('tutorial_walk', 5.0)
    yield tut_walk['done']
    fps_tut_walk = tut_walk['finish']()
    app.test_input = {}
    yield shot('perf_tutorial_walk')
    log('TUTORIAL fps still', round(fps_tut_still, 2), 'walk', round(fps_tut_walk, 2),
        'target ~46/51 from 1.4.3')
    log('phase144_perf finished')


def _pt_state(ses, log, tag):
    p = ses.player
    q, r = cell_at(p.x, p.z)
    under = ses.world.get(q, r, math.floor(p.y / LAYER) - 1) if ses.world else None
    feet = ses.world.get(q, r, math.floor(p.y / LAYER)) if ses.world else None
    log(tag,
        'pos', round(p.x, 2), round(p.y, 2), round(p.z, 2),
        'cell', q, r, 'yaw', round(p.yaw, 1), 'pitch', round(p.pitch, 1),
        'ground', p.on_ground, 'drift', p.drifting, 'hp', getattr(ses, 'hp', None),
        'food', getattr(ses, 'food', None), 'feet', feet, 'under', under,
        'mobs', len(getattr(ses, 'mobs', []) or []),
        'inv', [(I.get(s[0]).name, s[1]) for s in ses.inv.slots if s])


def _pt_walk_toward(app, ses, tx, tz, seconds, hurry=True):
    """Face (tx, tz) and walk. Caller must yield the returned seconds."""
    p = ses.player
    p.drifting = False
    p.noclip = False
    ses.hold = False
    dx, dz = tx - p.x, tz - p.z
    p.yaw = math.degrees(math.atan2(dx, -dz)) % 360
    p.pitch = 0.0
    app.test_input = {'fwd': 1, 'hurry': hurry}
    return seconds


def _pt_npc_clearance(ses, log):
    issues = []
    for npc in getattr(ses, 'npcs', []) or []:
        q, r = npc['q'], npc['r']
        y = int(round(npc['y'] / LAYER))
        feet = ses.world.get(q, r, y)
        body = ses.world.get(q, r, y + 1)
        under = ses.world.get(q, r, y - 1)
        stuck = (feet not in (0, M.get('petals', -1))) or (body not in (0, M.get('petals', -1)))
        missing = under in (0, None)
        log('npc', npc['name'], 'at', q, r, 'y', y, 'feet', feet, 'body', body, 'under', under,
            'STUCK' if stuck else ('NO_FLOOR' if missing else 'ok'))
        if stuck:
            issues.append((npc['name'], 'stuck', feet, body))
        if missing:
            issues.append((npc['name'], 'no_floor', under))
    return issues


def _pt_scan_structures(ses, log, limit=12):
    """Find likely generated structures in loaded chunks (chests, banners, lamps, thatch clusters)."""
    names = [k for k in M if any(s in k for s in (
        'banner', 'stained_glass', 'crystal_lamp', 'thatch', 'woven_panel',
        'patterned_tile', 'terrazzo', 'ivory_plaster', 'brass', 'pewter',
        'wrought_iron', 'rose_stripe', 'sky_stripe', 'cosmic_star'))]
    ids = {M[k] for k in names if k in M}
    ids.add(M['chest'])
    hits = []
    for (cq, cr), ch in list(ses.world.chunks.items()):
        cells = getattr(ch, 'cells', None)
        if cells is None:
            continue
        mask = np.isin(cells, list(ids))
        if not mask.any():
            continue
        ys, counts = np.unique(np.where(mask)[1], return_counts=True)  # wait, shape is (lq, y, lr)
        # actually np.where on (16, LAYERS, 16) returns lq, y, lr
        lq, yy, lr = np.where(mask)
        if len(lq) < 6 and M['chest'] not in cells:
            continue
        q = cq * CHUNK + int(np.median(lq))
        r = cr * CHUNK + int(np.median(lr))
        y = int(np.median(yy))
        n = int(len(lq))
        has_chest = bool(np.any(cells == M['chest']))
        hits.append((n, has_chest, q, r, y, cq, cr))
    hits.sort(reverse=True)
    out = hits[:limit]
    log('structure_hits', [(n, 'chest' if c else 'deco', q, r, y) for n, c, q, r, y, *_ in out])
    return out


def phase144_playtest(app, log, shot, look_at, settled, arg):
    """Play 1.4.4 like a new wanderer: lesson island, then a fresh v5 sky."""
    from . import tutorial as T
    from . import tide as TIDE
    from .hexgrid import center as hx

    findings = []

    def note(msg):
        log('FINDING', msg)
        findings.append(msg)

    app.settings['creatures'] = True
    app.settings['dusk_critters'] = True
    _144_hud(app, debug=False, hide=False)
    yield 0.8
    yield shot('00_title')

    # ------------------------------------------------------------------ lesson
    app.create_sky('Playtest 144 Lesson', 1, 'lesson', 'wanderer', tutorial=True)
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    q, r, top = T.SPAWN
    x, z = hx(q, r)
    # stand as a new player: no noclip, default yaw 0 pitch 4
    p.x, p.y, p.z = x, (top + 1) * LAYER + 0.001, z
    p.yaw, p.pitch = 0.0, 4.0
    p.vx = p.vy = p.vz = 0
    p.drifting = False
    p.noclip = False
    ses.hold = False
    yield settled()
    yield 0.8
    yield shot('01_tutorial_spawn')
    _pt_state(ses, log, 'tutorial_spawn')
    issues = _pt_npc_clearance(ses, log)
    if issues:
        note('NPC clearance issues: ' + str(issues))
    else:
        log('all 8 lesson NPCs have air at the body and a floor underfoot')

    # walk forward (yaw 0 looks -Z, toward the shrine / citadel)
    app.test_input = {'fwd': 1}
    yield 3.0
    app.test_input = {}
    yield 0.4
    yield shot('02_tutorial_walk_forward')
    _pt_state(ses, log, 'after_forward_walk')
    if not p.on_ground:
        note('player left the ground after a 3s forward walk from spawn')
    if math.hypot(p.x - x, p.z - z) < 2.0:
        note('3s walk from spawn barely moved; possible snag or blocked first step')

    # walk to Willow and talk
    wx, wz = hx(6, 2)
    yield _pt_walk_toward(app, ses, wx, wz, 4.0)
    app.test_input = {}
    yield 0.3
    if math.hypot(p.x - wx, p.z - wz) > 4.5:
        note('walk to Willow did not arrive (dist %.1f); standing nearby to talk' % math.hypot(p.x - wx, p.z - wz))
        _stand(ses, 6, 2)
        p.y = (T.SURF + 1) * LAYER + 0.001
        p.drifting = False
        p.noclip = False
    look_at(p, wx, (T.SURF + 2) * LAYER, wz)
    yield 0.2
    willow = next((n for n in ses.npcs if n['name'] == 'Willow'), None)
    talked = False
    if willow:
        talked = bool(ses.talk_npc(willow))
        log('willow_talk', talked, 'line', willow.get('line'), 'text', (willow.get('lines') or [None])[willow.get('line', 0)])
    else:
        note('Willow NPC record missing after lesson load')
    yield 0.6
    yield shot('03_talk_willow')
    if not talked:
        note('could not start Willow dialogue')

    # walk the east path toward Bram (gather station)
    bx, bz = hx(34, -8)
    yield _pt_walk_toward(app, ses, bx, bz, 10.0)
    # mid-walk: if still far, keep walking a bit more
    if math.hypot(p.x - bx, p.z - bz) > 8:
        yield _pt_walk_toward(app, ses, bx, bz, 6.0)
    app.test_input = {}
    yield 0.3
    bram_dist = math.hypot(p.x - bx, p.z - bz)
    log('bram_walk_dist', round(bram_dist, 2), 'on_ground', p.on_ground)
    if bram_dist > 6:
        note('walk to Bram did not arrive (dist %.1f); standing nearby' % bram_dist)
        _stand(ses, 34, -8)
        p.y = (T.SURF + 1) * LAYER + 0.001
        p.drifting = False
        p.noclip = False
    look_at(p, bx, (T.SURF + 2) * LAYER, bz)
    bram = next((n for n in ses.npcs if n['name'] == 'Bram'), None)
    if bram:
        ses.talk_npc(bram)
        log('bram_talk', (bram.get('lines') or [None])[bram.get('line', 0)])
    yield 0.5
    yield shot('04_talk_bram')

    # open Bram's chest (33, -10)
    cq, cr, cy = 33, -10, T.SURF + 1
    if not _stand_near(ses, (cq, cr, cy), look_at, 2):
        _stand(ses, 32, -10)
        p.y = (T.SURF + 1) * LAYER + 0.001
        look_at(p, *hx(cq, cr)[:1], (cy + 0.4) * LAYER, hx(cq, cr)[1])
        # look_at already used correctly below
    cx, cz = hx(cq, cr)
    look_at(p, cx, (cy + 0.4) * LAYER, cz)
    p.drifting = False
    p.noclip = False
    yield 0.3
    before = ses.inv.count(M['heartwood'])
    opened = ses.use_block(cq, cr, cy, M['chest'])
    log('open_bram_chest', opened, 'key', f'{cq},{cr},{cy}', 'in_chests', f'{cq},{cr},{cy}' in ses.chests)
    yield 0.5
    yield shot('05_bram_chest')
    if app.menu:
        app.menu.escape(app)
    # take the heartwood from the chest into the pack (player-like: add then empty chest slot)
    key = f'{cq},{cr},{cy}'
    if key in ses.chests:
        invc = ses.chests[key]
        took = 0
        for i, s in enumerate(list(invc.slots)):
            if s and s[0] == M['heartwood']:
                n = s[1]
                left = ses.inv.add(s[0], n)
                if left < n:
                    if left:
                        s[1] = left
                    else:
                        invc.slots[i] = None
                    took += n - left
        log('took_heartwood_from_chest', took, 'inv_now', ses.inv.count(M['heartwood']))
        if took == 0 and ses.inv.count(M['heartwood']) == before:
            note('Bram chest had no heartwood to take, or add failed')
    else:
        note('Bram chest was not in session.chests after use_block')

    # walk south to Lumen, then the shrine knoll
    lx, lz = hx(6, -32)
    yield _pt_walk_toward(app, ses, lx, lz, 12.0)
    if math.hypot(p.x - lx, p.z - lz) > 8:
        yield _pt_walk_toward(app, ses, lx, lz, 6.0)
    app.test_input = {}
    yield 0.3
    if math.hypot(p.x - lx, p.z - lz) > 6:
        note('walk to Lumen did not arrive (dist %.1f); standing nearby' % math.hypot(p.x - lx, p.z - lz))
        _stand(ses, 6, -32)
        p.y = (T.SURF + 1) * LAYER + 0.001
        p.drifting = False
        p.noclip = False
    look_at(p, lx, (T.SURF + 2) * LAYER, lz)
    lumen = next((n for n in ses.npcs if n['name'] == 'Lumen'), None)
    if lumen:
        ses.talk_npc(lumen)
        log('lumen_talk', (lumen.get('lines') or [None])[lumen.get('line', 0)])
    yield 0.5
    yield shot('06_talk_lumen')

    sx, sy, sz = T.shrine_pos()
    yield _pt_walk_toward(app, ses, sx, sz, 10.0)
    if math.hypot(p.x - sx, p.z - sz) > 8:
        yield _pt_walk_toward(app, ses, sx, sz, 6.0)
    app.test_input = {}
    yield 0.3
    shrine_dist = math.hypot(p.x - sx, p.z - sz)
    log('shrine_walk_dist', round(shrine_dist, 2), 'on_ground', p.on_ground)
    if shrine_dist > 8 or not p.on_ground:
        note('walk to the shrine knoll did not arrive cleanly (dist %.1f, ground %s)' % (shrine_dist, p.on_ground))
        p.x, p.z = sx, sz
        topk = ses.world.column_top(*cell_at(sx, sz))
        p.y = ((topk + 1) if topk is not None else T.SURF + 4) * LAYER + 0.001
        p.drifting = False
        p.noclip = False
        p.vx = p.vy = p.vz = 0
    look_at(p, sx, sy + 2.0, sz)
    yield settled()
    yield 0.6
    yield shot('07_shrine_knoll')
    _pt_state(ses, log, 'at_shrine')

    # leave the lesson
    app.quit_to_title()
    yield 1.0
    yield lambda: app.mode == 'title'
    yield 0.6

    # ------------------------------------------------------------------ new v5 sky
    seed = seed_from_text(arg or 'playtest-144')
    app.create_sky('Playtest 144 Sky', seed, arg or 'playtest-144', 'wanderer')
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.2
    ses = app.session
    p = ses.player
    p.drifting = False
    p.noclip = False
    ses.hold = False
    yield shot('10_v5_spawn')
    _pt_state(ses, log, 'v5_spawn')
    log('gen_version', getattr(ses.gen, 'version', None),
        'seed', ses.seed if hasattr(ses, 'seed') else seed,
        'spire', ses.nearest_spire)
    if getattr(ses.gen, 'version', None) != 5:
        note('new sky was not generator v5 (got %s)' % getattr(ses.gen, 'version', None))

    # walk like a player, then look around
    app.test_input = {'fwd': 1}
    yield 4.0
    app.test_input = {}
    yield 0.4
    yield shot('11_v5_walked')
    _pt_state(ses, log, 'v5_after_walk')
    if not p.on_ground:
        note('player left the ground after a 4s walk from v5 spawn (may have walked off a shore)')
    if p.y < 14:
        note('player fell toward the cloud sea after the first v5 walk')

    # gather wood
    wood = _find(ses, (M['heartwood'], M['cedar_heartwood'], M['pale_heartwood'], M['dark_heartwood']), 36, -2, 10)
    log('wood_target', wood)
    gathered = 0
    if wood and _stand_near(ses, wood, look_at, 2):
        p.drifting = False
        p.noclip = False
        yield 0.3
        before = ses.inv.count(wood and ses.world.get(*wood))
        mat = ses.world.get(*wood)
        app.test_input = {'gather': True, 'hold': True}
        yield 0.8
        yield shot('12_gather_wood')
        for _ in range(40):
            yield 0.15
            if ses.inv.count(mat) > before or (ses.world.get(*wood) == 0 and ses.drops):
                break
        app.test_input = {}
        # pick up drops
        for _ in range(8):
            if not ses.drops:
                break
            dr = ses.drops[0]
            p.x, p.z = dr.x, dr.z
            p.y = max(p.y, dr.y)
            yield 0.35
        gathered = ses.inv.count(mat)
        log('gathered_wood', I.get(mat).name if I.get(mat) else mat, gathered, 'drops', len(ses.drops))
        if gathered <= 0:
            note('held gather on a tree for several seconds but got no heartwood')
    else:
        note('no nearby tree found within 36 cells of spawn, or no stand-near cell')
    yield shot('13_after_gather')

    # craft planks in the backpack (real UI)
    if ses.inv.count(M['heartwood']) < 1:
        ses.give(M['heartwood'], 6, quiet=True)
        note('gave 6 Heartwood so the plank craft could be tried (gather had not produced any)')
    app.set_screen(IU.BackpackScreen())
    yield 0.3
    rec = next((r for r in I.RECIPES if r[1][0] == M['planks']), None)
    if rec and app.menu and hasattr(app.menu, 'fill'):
        app.menu.fill(app, rec)
        yield 0.5
        yield shot('14_craft_planks')
        log('crafted_planks_inv', ses.inv.count(M['planks']))
    else:
        note('BackpackScreen.fill could not run the planks recipe')
    if app.menu:
        app.menu.escape(app)
    yield 0.3

    # craft a 1.4.4 dye and a stained-glass block (ingredients granted, logged)
    for iid, n, why in (
        (M['bloom'], 4, 'rose dye'),
        (M['glass'], 4, 'stained glass'),
        (M['stone_tiles'], 8, 'patterned tile'),
        (M['petals'], 2, 'honey dye'),
        (M['sand'], 2, 'honey dye'),
        (I.FLUFF.id, 4, 'jelly / stripe'),
        (M['glowcap'], 2, 'jelly'),
    ):
        ses.give(iid, n, quiet=True)
    note('granted bloom, glass, stone tiles, petals, sand, fluff and glowcap to try the new 1.4.4 recipes')
    app.set_screen(IU.BackpackScreen())
    yield 0.3
    rec = next((r for r in I.RECIPES if r[1][0] == I.DYE['rose'].id), None)
    if rec and app.menu and hasattr(app.menu, 'fill'):
        app.menu.fill(app, rec)
        yield 0.5
        yield shot('15_craft_rose_dye')
        log('rose_dye', ses.inv.count(I.DYE['rose'].id))
        if ses.inv.count(I.DYE['rose'].id) < 1:
            note('rose dye recipe filled but the pack still has no Rose Dye')
    else:
        note('could not fill the Rose Dye recipe in the backpack')
    if app.menu:
        app.menu.escape(app)
    yield 0.2
    # stained glass may need the 3x3 bench; try backpack first, then CraftScreen
    if ses.inv.count(I.DYE['rose'].id) < 1:
        ses.give(I.DYE['rose'].id, 2, quiet=True)
    app.set_screen(IU.BackpackScreen())
    yield 0.25
    rec = next((r for r in I.RECIPES if r[1][0] == M['rose_stained_glass']), None)
    filled = False
    if rec and app.menu and hasattr(app.menu, 'fill'):
        try:
            app.menu.fill(app, rec)
            filled = True
        except Exception as e:
            log('stain_fill_err', e)
    if app.menu:
        yield 0.4
        yield shot('16_craft_rose_glass')
        app.menu.escape(app)
    log('rose_stained_glass', ses.inv.count(M['rose_stained_glass']), 'filled', filled)
    if ses.inv.count(M['rose_stained_glass']) < 1:
        # 2-ingredient shapeless should work in the backpack; if not, that's a finding
        note('Rose Stained Glass craft did not add the block to the pack')
        ses.give(M['rose_stained_glass'], 8, quiet=True)
        ses.give(M['rose_jelly'], 4, quiet=True)
        ses.give(M['snow_patterned_tile'], 8, quiet=True)
        ses.give(M['rose_banner'], 2, quiet=True)
        note('granted rose glass, jelly, patterned tile and a banner so a build could still be placed')
    else:
        if ses.inv.count(M['rose_jelly']) < 1:
            # try jelly recipe too if we have the mats
            app.set_screen(IU.BackpackScreen())
            yield 0.2
            rec = next((r for r in I.RECIPES if r[1][0] == M['rose_jelly']), None)
            if rec and app.menu and hasattr(app.menu, 'fill'):
                app.menu.fill(app, rec)
                yield 0.3
            if app.menu:
                app.menu.escape(app)

    # place a small new-block doodle beside the player
    q0, r0 = cell_at(p.x, p.z)
    top0 = ses.world.column_top(q0, r0) or math.floor(p.y / LAYER)
    placed = []
    palette_build = (
        ((1, 0), M['rose_stained_glass']),
        ((2, 0), M['rose_stained_glass']),
        ((1, 1), M.get('rose_jelly', M['rose_stained_glass'])),
        ((2, 1), M.get('snow_patterned_tile', M['planks'])),
        ((3, 0), M.get('rose_banner', M['planks'])),
    )
    for (dq, dr), mat in palette_build:
        a, b = q0 + dq, r0 + dr
        t = ses.world.column_top(a, b)
        if t is None:
            continue
        if ses.world.get(a, b, t + 1) in (0, M['petals'], M['sprout'], M['bloom']):
            ok = ses.world.set(a, b, t + 1, mat, 0, now=True)
            placed.append((a, b, t + 1, mat, ok))
    log('placed_doodle', placed)
    if not placed:
        note('could not place the new-block doodle; neighbouring columns were full or unloaded')
    # step back and look at it
    p.x, p.z = hx(q0 - 3, r0 + 1)
    tstand = ses.world.column_top(*cell_at(p.x, p.z))
    if tstand is not None:
        p.y = (tstand + 1) * LAYER + 0.001
    p.drifting = False
    p.noclip = False
    tx, tz = hx(q0 + 2, r0)
    look_at(p, tx, (top0 + 2) * LAYER, tz)
    yield settled()
    yield 0.7
    yield shot('17_placed_new_blocks')

    # visit a generated structure if one is in the loaded area
    hits = _pt_scan_structures(ses, log)
    if hits:
        n, has_c, sq, sr, sy, scq, scr = hits[0]
        sx, sz = hx(sq, sr)
        # park a little way back so the whole build can be the subject
        p.drifting = True
        p.x, p.z = sx + 18, sz + 10
        p.y = (sy + 8) * LAYER
        look_at(p, sx, (sy + 2) * LAYER, sz)
        yield _144_loaded(app, 20)
        yield 1.0
        yield shot('18_visit_structure')
        # also stand on it like a player
        p.drifting = False
        p.noclip = False
        top_s = ses.world.column_top(sq, sr)
        if top_s is not None:
            p.x, p.z = sx, sz
            p.y = (top_s + 1) * LAYER + 0.001
            p.pitch = -8
            yield settled()
            yield 0.6
            yield shot('19_structure_ground')
            _pt_state(ses, log, 'on_structure')
        log('visited_structure', 'count', n, 'chest', has_c, 'at', sq, sr, sy)
    else:
        note('no generated structure (chest / new decorative cluster) in the loaded area around spawn')
        yield shot('18_no_structure_nearby')

    # fly / updraft / glide. Try the nearest spire first; grant abilities if we cannot reach two.
    sp = ses.nearest_spire[0] if ses.nearest_spire else None
    log('nearest_spire', sp, 'awakened', list(ses.awakened))
    if sp:
        qx, qz = hx(sp['q'], sp['r']) if 'q' in sp else (sp.get('x'), sp.get('z'))
        if qx is not None:
            yield _pt_walk_toward(app, ses, qx, qz, 8.0)
            app.test_input = {}
            log('spire_walk_dist', round(math.hypot(p.x - qx, p.z - qz), 2) if qx is not None else None)
    if len(ses.awakened) < 2:
        ses.awakened = list(ses.awakened) + ['playtest-a', 'playtest-b']
        ses.apply_abilities()
        note('granted glide + updraft (did not awaken two spires during this playtest)')
    log('abilities', 'glide', p.can_glide, 'updraft', p.can_updraft, 'tidecall', ses.can_tidecall)

    # find a nearby edge and step off, then updraft + glide
    pq, pr = cell_at(p.x, p.z)
    edge = None
    for a, b in spiral(pq, pr, 24):
        if ses.world.column_top(a, b) is None:
            # previous ring cell with land is an edge
            continue
        for dq, dr in DIRS:
            if ses.world.column_top(a + dq, b + dr) is None:
                edge = (a, b, dq, dr)
                break
        if edge:
            break
    log('edge', edge)
    if edge:
        a, b, dq, dr = edge
        _stand(ses, a, b)
        p.drifting = False
        p.noclip = False
        ses.hold = False
        p.yaw = math.degrees(math.atan2(*( (hx(a + dq, b + dr)[0] - p.x, -(hx(a + dq, b + dr)[1] - p.z)) ))) % 360
        # simpler face
        tx, tz = hx(a + dq * 3, b + dr * 3)
        p.yaw = math.degrees(math.atan2(tx - p.x, -(tz - p.z))) % 360
        p.pitch = -12
        app.test_input = {'fwd': 1, 'jump': True, 'jump_pressed': True}
        yield 0.35
        app.test_input = {'fwd': 1, 'jump': True, 'jump_pressed': True}
        yield 0.35
        app.test_input = {'fwd': 1, 'jump': True}
        yield 1.6
        yield shot('20_updraft_glide')
        log('after_flight', 'y', round(p.y, 2), 'vy', round(p.vy, 2), 'ground', p.on_ground,
            'gliding', p.gliding, 'air_jumps', p.air_jumps, 'hp', ses.hp)
        app.test_input = {}
        if p.air_jumps < 1 and p.can_updraft:
            note('updraft did not fire (air_jumps stayed 0) after two mid-air jump presses')
        # land if still falling
        for _ in range(20):
            if p.on_ground or p.y < 8:
                break
            yield 0.2
        if not p.on_ground:
            # snap back to the edge so we can continue
            _stand(ses, a, b)
            p.drifting = False
            p.noclip = False
            note('had to snap back to the shore after the flight test (did not land on its own)')
    else:
        note('no nearby island edge to test updraft / glide from')

    _pt_state(ses, log, 'after_flight')

    # dusk: wait for gloomlings
    ses.phase = 0.5
    log('tide', TIDE.name(ses.phase), 'dusk', round(TIDE.dusk_amount(ses.phase), 3))
    # give creatures a few spawn ticks (1s interval)
    kinds_before = {}
    yield 5.5
    kinds = {}
    for m in ses.mobs:
        kinds[m.kind] = kinds.get(m.kind, 0) + 1
    log('mobs_at_dusk', kinds, 'total', len(ses.mobs))
    if not any(m.kind in ('gloomling', 'brute') for m in ses.mobs):
        # they spawn 14-28 away; wait a little more and also try a forced nearby spawn to confirm AI
        yield 3.0
        kinds = {}
        for m in ses.mobs:
            kinds[m.kind] = kinds.get(m.kind, 0) + 1
        log('mobs_at_dusk_2', kinds)
        if not any(m.kind in ('gloomling', 'brute') for m in ses.mobs):
            note('no gloomlings or brutes spawned after several seconds of dusktide near the player')
            ok = ses._try_spawn(True)
            log('forced_hostile_spawn', ok)
            note('forced a hostile spawn to photograph dusk critters (natural spawn had not happened yet)')
    # frame a nearby mob if any
    if ses.mobs:
        m0 = min(ses.mobs, key=lambda m: math.hypot(m.x - p.x, m.z - p.z))
        dx, dz = p.x - m0.x, p.z - m0.z
        dd = math.hypot(dx, dz) or 1
        p.x = m0.x + dx / dd * 5.5
        p.z = m0.z + dz / dd * 5.5
        p.y = m0.y + 1.5
        p.drifting = True
        look_at(p, m0.x, m0.y + 0.4, m0.z)
        yield 0.6
        yield shot('21_dusk_creatures')
        p.drifting = False
        log('featured_mob', m0.kind, round(m0.x, 1), round(m0.y, 1), round(m0.z, 1), 'hostile', m0.hostile)
    else:
        note('no creatures at all were present at dusktide')
        yield shot('21_dusk_empty')

    # survive a few seconds of dusk on the ground
    if not p.on_ground:
        pq, pr = cell_at(p.x, p.z)
        top = ses.world.column_top(pq, pr)
        if top is None:
            # find any land
            for a, b in spiral(pq, pr, 20):
                top = ses.world.column_top(a, b)
                if top is not None:
                    pq, pr = a, b
                    break
        if top is not None:
            _stand(ses, pq, pr)
            p.drifting = False
            p.noclip = False
    hp0 = ses.hp
    yield 4.0
    log('dusk_survive', 'hp0', hp0, 'hp', ses.hp, 'food', ses.food, 'ground', p.on_ground)
    yield shot('22_dusk_survive')
    if ses.hp <= 0:
        note('player died during a short dusktide stand')
    elif ses.hp < hp0:
        log('took_dusk_damage', hp0 - ses.hp)

    _pt_state(ses, log, 'playtest_end')
    log('FINDINGS', len(findings))
    for msg in findings:
        log('FINDING', msg)
    log('phase144_playtest finished')


def phase144_playtest_retake(app, log, shot, look_at, settled, arg):
    """Retake the unusable playtest shots: Willow and Bram in view, shrine from
    farther back, new blocks actually placed on the ground, rose glass on the 2x2."""
    from . import tutorial as T
    from .hexgrid import center as hx
    from .materials import support_top

    _144_uncap(app, log, view=14, far=20)
    _144_hud(app, debug=False, hide=False)
    yield 0.4
    app.create_sky('Playtest 144 Retake Lesson', 1, 'lesson', 'wanderer', tutorial=True)
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    p.drifting = False
    p.noclip = False
    ses.hold = False

    # Willow: stand on her cell first (the old failure), then talk — framing should step back
    willow = next((n for n in ses.npcs if n['name'] == 'Willow'), None)
    _stand(ses, 6, 2)
    p.y = (T.SURF + 1) * LAYER + 0.001
    p.drifting = False
    p.noclip = False
    p.yaw, p.pitch = 180.0, 8.0
    yield 0.2
    if willow:
        ses.talk_npc(willow)
        log('willow_framed', round(p.x, 2), round(p.y, 2), round(p.z, 2),
            'dist', round(ses._npc_dist(willow), 2), 'yaw', round(p.yaw, 1), 'pitch', round(p.pitch, 1))
    yield 0.7
    yield shot('03_talk_willow')

    # Bram: start next to the heartwood we talked into last time, then talk
    bram = next((n for n in ses.npcs if n['name'] == 'Bram'), None)
    # there is a tree near Bram's station; stand on a nearby column first
    if not _stand_near(ses, (34, -8, T.SURF + 1), look_at, 1):
        _stand(ses, 34, -8)
    p.drifting = False
    p.noclip = False
    yield 0.2
    if bram:
        ses.talk_npc(bram)
        log('bram_framed', round(p.x, 2), round(p.z, 2), 'dist', round(ses._npc_dist(bram), 2),
            'target', getattr(ses, 'target_name', None))
    yield 0.8
    yield shot('04_talk_bram')

    # shrine knoll from farther back, looking at the shrine, not a wall
    sx, sy, sz = T.shrine_pos()
    # stand north of the knoll, a bit up, looking south at the shrine
    p.drifting = True
    p.noclip = True
    p.x, p.y, p.z = sx + 4.0, sy + 6.5, sz + 16.0
    p.vx = p.vy = p.vz = 0
    look_at(p, sx, sy + 1.6, sz)
    ses.talk = None
    _144_hud(app, debug=False, hide=False)
    yield settled()
    yield 0.9
    yield shot('07_shrine_knoll')
    log('shrine_cam', round(p.x, 1), round(p.y, 1), round(p.z, 1), 'yaw', round(p.yaw, 1), 'pitch', round(p.pitch, 1))

    app.quit_to_title()
    yield 1.0
    yield lambda: app.mode == 'title'
    yield 0.4

    # a v5 pad for placing new blocks and crafting rose glass
    from . import gensettings as GS
    app.create_sky('Playtest 144 Retake Build', seed_from_text('playtest-144-retake'),
                   'playtest-144-retake', 'wanderer', gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    # flatten a small ground pad around the player, no trees
    q0, r0 = cell_at(p.x, p.z)
    top = ses.world.column_top(q0, r0) or 80
    # find a true ground top (skip canopy): walk down from column_top until a full block that isn't wood/canopy
    woods = {M['heartwood'], M['pale_heartwood'], M['dark_heartwood'], M['cedar_heartwood'],
             M['canopy'], M.get('pale_canopy', -1), M.get('cedar_canopy', -1)}
    ypad = top
    for y in range(top, max(2, top - 20), -1):
        m = ses.world.get(q0, r0, y)
        if m and m not in woods and MT.KIND[m] == 'full':
            ypad = y
            break
    for dq in range(-6, 7):
        for dr in range(-6, 7):
            q, r = q0 + dq, r0 + dr
            for yy in range(ypad - 2, ypad):
                if ses.world.get(q, r, yy) == 0:
                    ses.world.set(q, r, yy, M['loam'], now=True)
            ses.world.set(q, r, ypad, M['snow_patterned_tile'] if dq == 0 and dr == 0 else M['ivory_plaster'], now=True)
            for yy in range(ypad + 1, ypad + 16):
                ses.world.set(q, r, yy, 0, now=True)
    # place a doodle of new dyed / decorative blocks on the pad
    doodle = [
        ((-2, -1), M['rose_stained_glass']),
        ((-1, -1), M['rose_stained_glass']),
        ((0, -1), M['sky_stained_glass'] if 'sky_stained_glass' in M else M['rose_stained_glass']),
        ((-2, 0), M['rose_jelly']),
        ((-1, 0), M['honey_jelly'] if 'honey_jelly' in M else M['rose_jelly']),
        ((0, 0), M['ink_checker'] if 'ink_checker' in M else M['snow_patterned_tile']),
        ((1, 0), M['rose_checker'] if 'rose_checker' in M else M['snow_patterned_tile']),
        ((-2, 1), M['rose_banner']),
        ((-1, 1), M['blush_plaster'] if 'blush_plaster' in M else M['ivory_plaster']),
        ((0, 1), M['brass'] if 'brass' in M else M['pewter']),
        ((1, 1), M['rose_crystal_lamp'] if 'rose_crystal_lamp' in M else M['lumen_lamp']),
        ((-1, 2), M['shimmer_cloud']),
        ((0, 2), M['cosmic_star']),
    ]
    placed = []
    for (dq, dr), mat in doodle:
        ok = ses.world.set(q0 + dq, r0 + dr, ypad + 1, mat, 0, now=True)
        placed.append((dq, dr, mat, ok))
    log('placed_doodle', placed)
    # stand back and look at the whole doodle
    p.drifting = True
    p.noclip = True
    cx, cz = hx(q0, r0)
    p.x, p.y, p.z = cx + 2.0, (ypad + 4) * LAYER, cz + 9.5
    look_at(p, cx, (ypad + 2.0) * LAYER, cz)
    ses.talk = None
    _144_hud(app, debug=False, hide=False)
    yield settled()
    yield 1.0
    yield shot('17_placed_new_blocks')

    # craft rose glass on the 2x2 from glass + rose dye
    ses.inv.slots[:] = [None] * len(ses.inv.slots)
    ses.give(M['glass'], 4, quiet=True)
    ses.give(I.DYE['rose'].id, 4, quiet=True)
    app.set_screen(IU.BackpackScreen())
    yield 0.3
    rec = None
    for r in I.RECIPES:
        if r[1][0] == M['rose_stained_glass'] and I.recipe_size(r[0]) <= 2:
            need = I.recipe_needs(r[0])
            if M['glass'] in need and I.DYE['rose'].id in need:
                rec = r
                break
    if rec is None:
        rec = next((r for r in I.RECIPES
                    if r[1][0] == M['rose_stained_glass'] and I.recipe_size(r[0]) <= 2), None)
    if rec and app.menu and hasattr(app.menu, 'fill'):
        app.menu.fill(app, rec)
        log('rose_fill', 'grid', list(app.menu.grid), 'result', getattr(app.menu, 'result', lambda: None)())
    yield 0.5
    yield shot('16_craft_rose_glass')
    if app.menu:
        app.menu.escape(app)
    log('phase144_playtest_retake finished')


def phase144_wonders(app, log, shot, look_at, settled, arg):
    """Farther-back portraits of the new 1.4.4 wonders."""
    from . import structures as ST
    from . import gensettings as GS
    _144_uncap(app, log, view=14, far=22)
    yield 0.3
    app.create_sky('Wonders 144', 21, 'wonders-144', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.5
    ses = app.session
    ses.phase = 0.08
    ses.weather = 'clear'
    names = ['whale_skeleton', 'clockwork_tower', 'upside_castle',
             'ring_harbor', 'crystal_cathedral', 'waterfall_temple']
    q0, r0, y0 = 4, 4, 150
    spacing = 40
    mid_q = q0 + (len(names) // 2) * spacing
    ox, oz = center(mid_q, r0)
    _144_park(ses, ox, (y0 + 24) * LAYER, oz, 0.0, -22.0)
    yield _144_loaded(app)
    yield 0.8
    for dq in range(-10, len(names) * spacing + 10):
        for dr in range(-12, 16):
            q, r = q0 + dq, r0 + dr
            for yy in range(y0 - 4, y0):
                ses.world.set(q, r, yy, M['stone'])
            ses.world.set(q, r, y0, M.get('ivory_plaster', M['pale_planks']))
            for yy in range(y0 + 1, y0 + 28):
                ses.world.set(q, r, yy, 0)
    yield settled()
    for i, name in enumerate(names):
        q, r = q0 + 10 + i * spacing, r0
        try:
            ST.stamp_world(ses.world, q, r, name, cond=ST.INTACT, seed=90 + i, realm=7)
            log('stamped', name, 'at', q, r)
        except Exception as e:
            log('stamp failed', name, e)
    yield settled()
    yield 1.2
    _144_hud(app, debug=False, hide=True)
    # cam/look offsets in cells; cam_dy is the desired EYE height (we subtract EYE)
    frames = {
        'whale_skeleton':    dict(dx=2.0,  dy=6.0,  dz=16.0, ldx=0.0, ldy=5.0,  ldz=0.0),
        'clockwork_tower':   dict(dx=8.0,  dy=16.0, dz=22.0, ldx=0.0, ldy=9.0,  ldz=0.0),
        'upside_castle':     dict(dx=14.0, dy=9.0,  dz=18.0, ldx=0.0, ldy=11.0, ldz=0.0),
        'ring_harbor':       dict(dx=8.0,  dy=11.0, dz=18.0, ldx=0.0, ldy=2.0,  ldz=0.0),
        'crystal_cathedral': dict(dx=11.0, dy=15.0, dz=24.0, ldx=2.0, ldy=10.0, ldz=0.0),
        # close, in front of the +q cascade, mid-fall, temple in frame
        'waterfall_temple':  dict(dx=14.0, dy=9.0,  dz=22.0, ldx=1.0, ldy=11.0, ldz=0.0),
    }
    for i, name in enumerate(names):
        q, r = q0 + 10 + i * spacing, r0
        x, z = center(q, r)
        f = frames[name]
        _144_park(ses, x + f['dx'], (y0 + f['dy']) * LAYER - EYE, z + f['dz'], 0.0, -18.0)
        look_at(ses.player, x + f['ldx'], (y0 + f['ldy']) * LAYER, z + f['ldz'])
        yield _144_loaded(app)
        yield 1.0
        yield shot(f'wonder_{name}')
        log('framed', name)
    log('phase144_wonders finished')


def phase144_mobs(app, log, shot, look_at, settled, arg):
    """Close, well-lit portraits of the new 1.4.4 creatures."""
    from . import gensettings as GS
    from .entities import Mob
    _144_uncap(app, log, view=12, far=18)
    yield 0.3
    app.create_sky('Mobs 144', 21, 'mobs-144', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.8
    ses = app.session
    ses.phase = 0.12
    ses.weather = 'clear'
    p = ses.player
    q0, r0 = cell_at(p.x, p.z)
    top = ses.world.column_top(q0, r0) or 80
    woods = {M['heartwood'], M['pale_heartwood'], M['dark_heartwood'], M['cedar_heartwood'], M['canopy']}
    ypad = top
    for y in range(top, max(2, top - 20), -1):
        m = ses.world.get(q0, r0, y)
        if m and m not in woods and MT.KIND[m] == 'full':
            ypad = y
            break
    for dq in range(-8, 9):
        for dr in range(-8, 9):
            q, r = q0 + dq, r0 + dr
            for yy in range(ypad - 2, ypad):
                if ses.world.get(q, r, yy) == 0:
                    ses.world.set(q, r, yy, M['loam'], now=True)
            ses.world.set(q, r, ypad, M['turf'], now=True)
            for yy in range(ypad + 1, ypad + 12):
                cur = ses.world.get(q, r, yy)
                if cur in woods or cur in (M['sprout'], M['petals'], M['bloom'], M['berry_bush'], M['canopy']):
                    ses.world.set(q, r, yy, 0, now=True)
    yield settled()
    yield 0.6
    ses.mobs = []
    # (kind, side, hover, cam_dx, cam_dy, cam_dz) — close-ups for the smaller / flatter ones
    # (kind, side, hover, cam_dx, cam_eye_dy, cam_dz) — cam_eye_dy is where the EYE should sit
    kinds = [
        ('skyjelly', 0, 3.2, 2.4, 1.15, 4.6),
        # medium distance, slightly below, whole body against the sky (not inside the wings)
        ('cloudray', 3, 10.0, 2.8, 0.05, 6.8),
        ('mossturtle', -3, 0.0, 2.4, 1.15, 4.6),
        ('crystalbeetle', 2, 0.0, 0.70, 0.20, 1.05),
        ('islekit', -2, 0.0, 0.80, 0.28, 1.20),
    ]
    look_h = {'crystalbeetle': 0.16, 'islekit': 0.24, 'cloudray': 0.22}
    _144_hud(app, debug=False, hide=True)
    cx, cz = center(q0, r0)
    for kind, side, up, cdx, cdy, cdz in kinds:
        ses.mobs = []
        mx, mz = cx + side * 1.1, cz - 3.2
        mob = Mob(kind, mx, (ypad + 1) * LAYER + 0.001 + up, mz)
        mob.yaw = 200
        mob.walking = True
        mob.think = 99
        ses.mobs.append(mob)
        def _frame():
            p.drifting = True
            p.noclip = True
            ses.hold = True
            p.vx = p.vy = p.vz = 0
            p._eye = EYE
            p.x, p.y, p.z = mx + cdx, mob.y + cdy - EYE, mz + cdz
            look_at(p, mx, mob.y + look_h.get(kind, 0.28), mz)
        _frame()
        yield settled()
        _frame()
        yield 0.35
        yield shot(f'mob_{kind}')
        log('mob', kind, 'at', round(mx, 1), round(mob.y, 1), round(mz, 1))
    # group shot
    ses.mobs = []
    for i, (kind, side, up, *_rest) in enumerate(kinds):
        mx, mz = cx + (i - 2) * 2.0, cz - 3.0
        mob = Mob(kind, mx, (ypad + 1) * LAYER + 0.001 + up, mz)
        mob.yaw = 200
        mob.walking = True
        mob.think = 99
        ses.mobs.append(mob)
    p.x, p.y, p.z = cx, (ypad + 5) * LAYER - EYE, cz + 8.5
    look_at(p, cx, (ypad + 2.2) * LAYER, cz - 3.0)
    yield 0.8
    yield shot('mobs_group')
    log('phase144_mobs finished')

def phase144_waterfall_retake(app, log, shot, look_at, settled, arg):
    """Side-on waterfall temple: cliff, falling water, and the temple together."""
    from . import structures as ST
    from . import gensettings as GS
    _144_uncap(app, log, view=14, far=22)
    yield 0.3
    app.create_sky('Wonders 144', 21, 'wonders-144', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.4
    ses = app.session
    ses.phase = 0.08
    ses.weather = 'clear'
    q0, r0, y0 = 4, 4, 150
    ox, oz = center(q0, r0)
    _144_park(ses, ox, (y0 + 24) * LAYER - EYE, oz, 0.0, -22.0)
    yield _144_loaded(app)
    yield 0.6
    for dq in range(-16, 20):
        for dr in range(-16, 20):
            q, r = q0 + dq, r0 + dr
            for yy in range(y0 - 4, y0):
                ses.world.set(q, r, yy, M['stone'])
            ses.world.set(q, r, y0, M.get('ivory_plaster', M['pale_planks']))
            for yy in range(y0 + 1, y0 + 28):
                ses.world.set(q, r, yy, 0)
    yield settled()
    ST.stamp_world(ses.world, q0, r0, 'waterfall_temple', cond=ST.INTACT, seed=94, realm=7)
    log('stamped waterfall_temple at', q0, r0)
    yield settled()
    yield 1.0
    _144_hud(app, debug=False, hide=True)
    x, z = center(q0, r0)
    # 3/4 view from the cascade side: temple on the mesa, sheet of water, basin
    _144_park(ses, x + 14.0, (y0 + 9.0) * LAYER - EYE, z + 22.0, 0.0, -18.0)
    look_at(ses.player, x + 1.0, (y0 + 11.0) * LAYER, z)
    yield _144_loaded(app)
    _144_park(ses, x + 14.0, (y0 + 9.0) * LAYER - EYE, z + 22.0, 0.0, -18.0)
    look_at(ses.player, x + 1.0, (y0 + 11.0) * LAYER, z)
    yield 0.5
    yield shot('wonder_waterfall_temple')
    log('framed waterfall_temple retake')
    log('phase144_waterfall_retake finished')


def phase144_mobs_close(app, log, shot, look_at, settled, arg):
    """Close, centered retakes of cloudray, crystalbeetle and islekit on a clean pad."""
    from . import gensettings as GS
    from .entities import Mob
    _144_uncap(app, log, view=12, far=18)
    yield 0.3
    app.create_sky('Mobs 144 close', 21, 'mobs-144-close', 'wanderer',
                   gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.4
    ses = app.session
    ses.phase = 0.12
    ses.weather = 'clear'
    p = ses.player
    q0, r0, y0 = 8, 8, 150
    ox, oz = center(q0, r0)
    _144_park(ses, ox, (y0 + 8) * LAYER - EYE, oz + 8, 0.0, -8.0)
    yield _144_loaded(app)
    yield 0.5
    turf = M.get('turf', M['loam'])
    for dq in range(-10, 11):
        for dr in range(-10, 11):
            q, r = q0 + dq, r0 + dr
            for yy in range(y0 - 3, y0):
                ses.world.set(q, r, yy, M['stone'])
            ses.world.set(q, r, y0, turf)
            for yy in range(y0 + 1, y0 + 16):
                ses.world.set(q, r, yy, 0)
    yield settled()
    _144_hud(app, debug=False, hide=True)
    cx, cz = center(q0, r0)

    def frame(mx, my, mz, cdx, cdy, cdz, ly):
        p.drifting = True
        p.noclip = True
        ses.hold = True
        p.vx = p.vy = p.vz = 0
        p._eye = EYE
        _144_park(ses, mx + cdx, my + cdy - EYE, mz + cdz, 0.0, 0.0)
        look_at(p, mx, my + ly, mz)

    shots = [
        # medium distance, slightly below, whole ray against the sky
        ('cloudray', 10.0, 2.6, 0.05, 6.6, 0.22, 15),
        # close, centered, eye at mid-height
        ('crystalbeetle', 0.0, 0.70, 0.20, 1.05, 0.16, 200),
        ('islekit', 0.0, 0.80, 0.28, 1.20, 0.24, 200),
    ]
    for kind, hover, cdx, cdy, cdz, ly, yaw in shots:
        ses.mobs = []
        mx, mz = cx, cz
        mob = Mob(kind, mx, (y0 + 1) * LAYER + 0.001 + hover, mz)
        mob.yaw = yaw
        mob.walking = True
        mob.think = 99
        ses.mobs.append(mob)
        frame(mx, mob.y, mz, cdx, cdy, cdz, ly)
        yield settled()
        frame(mx, mob.y, mz, cdx, cdy, cdz, ly)
        yield 0.4
        yield shot(f'mob_{kind}')
        log('mob', kind, 'at', round(mx, 1), round(mob.y, 1), round(mz, 1),
            'cam', round(p.x, 2), round(p.y, 2), round(p.z, 2))
    log('phase144_mobs_close finished')


def phase144_craft_rose(app, log, shot, look_at, settled, arg):
    """Backpack 2x2: glass + rose dye makes Rose Stained Glass."""
    from . import gensettings as GS
    _144_uncap(app, log, view=8, far=14)
    yield 0.3
    app.create_sky('Rose Glass 144', seed_from_text('playtest-144-rose'),
                   'playtest-144-rose', 'wanderer', gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 0.6
    ses = app.session
    ses.inv.slots[:] = [None] * len(ses.inv.slots)
    ses.give(M['glass'], 4, quiet=True)
    ses.give(I.DYE['rose'].id, 4, quiet=True)
    app.set_screen(IU.BackpackScreen())
    yield 0.3
    rec = None
    for r in I.RECIPES:
        if r[1][0] == M['rose_stained_glass'] and I.recipe_size(r[0]) <= 2:
            need = I.recipe_needs(r[0])
            if M['glass'] in need and I.DYE['rose'].id in need:
                rec = r
                break
    if rec and app.menu and hasattr(app.menu, 'fill'):
        app.menu.fill(app, rec)
        res = app.menu.result() if hasattr(app.menu, 'result') else None
        log('rose_fill', 'grid', list(app.menu.grid), 'result', res)
    yield 0.5
    yield shot('16_craft_rose_glass')
    if app.menu:
        app.menu.escape(app)
    log('phase144_craft_rose finished')


def phase144_tutorial2(app, log, shot, look_at, settled, arg):
    """Rebuilt lesson island: spawn, aerials, each showpiece, gardens, creatures, Tidewell UI."""
    from . import tutorial as T
    from . import tutorial_builds as TB
    from .hexgrid import center as hx
    from .ui.systems import TidewellScreen, WaystoneScreen
    only = set(a for a in (arg or '').split(',') if a)
    _144_uncap(app, log, view=16, far=24)
    yield 0.3
    app.create_sky('Lesson Builds 144', 1, 'lesson', 'wanderer', tutorial=True)
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    S0 = T.SURF

    def frame(q, r, ty, dist, az, elev):
        """Camera `dist` from the target at hex (q, r), `ty` layers above the surface.
        az: compass degrees the camera sits at, measured like yaw; elev: degrees up."""
        tx, tz = hx(q, r)
        tyw = (S0 + ty) * LAYER
        a, e = math.radians(az), math.radians(elev)
        cx = tx + math.sin(a) * math.cos(e) * dist
        cz = tz - math.cos(a) * math.cos(e) * dist
        cy = tyw + math.sin(e) * dist
        _144_park(ses, cx, cy - EYE, cz, 0.0, 0.0)
        look_at(p, tx, tyw, tz)

    def want(n):
        return not only or n in only

    _144_hud(app, debug=False, hide=True)
    # spawn
    if want('spawn'):
        q, r, top = T.SPAWN
        x, z = hx(q, r)
        _144_park(ses, x, (top + 1) * LAYER + 0.001, z, 0.0, 4.0)
        yield _144_loaded(app)
        yield 1.5
        yield shot('spawn')
        # spawn turned toward the plaza and clocktower
        _144_park(ses, x, (top + 1) * LAYER + 0.001, z, 0.0, 0.0)
        look_at(p, *[hx(28, 20)[0], (S0 + 16) * LAYER, hx(28, 20)[1]])
        yield _144_loaded(app)
        yield 1.0
        yield shot('spawn_toward_clocktower')
    shots = [
        # name, q, r, target height (layers), distance, azimuth, elevation
        ('aerial_overview', 18, 18, 0, 150, 200, 38),
        ('aerial_south', 18, 14, 0, 140, 160, 30),
        ('clocktower_plaza', 28, 20, 18, 62, 215, 14),
        ('bazaar_ring', 28, 20, 4, 30, 140, 22),
        ('hall_of_stones', 47, 22, 9, 44, 120, 16),
        ('glass_conservatory', 10, 36, 5, 30, 200, 18),
        ('conservatory_garden', 10, 36, 2, 7, 160, 35),
        ('mossback_monument', 12, 12, 4, 22, 230, 18),
        ('sky_funfair', 26, 4, 14, 46, 230, 16),
        ('starwatch_observatory', 22, -24, 11, 38, 250, 10),
        ('treehouse_grove', 24, 66, 10, 58, 15, 24),
        ('windmill', 61, -11, 12, 46, 200, 12),
        ('hedge_maze', -3, 29, 0, 26, 170, 50),
        ('woolhop_statue', 34, 39, 8, 30, 120, 14),
        ('sky_castle', -16, 18, 40, 62, 150, 8),
        ('frost_and_ember', -35, 30, 3, 30, 270, 22),
        ('tidewell_sanctuary', 6, -32, 4, 20, 160, 18),
        ('block_gallery', -18, 3, 2, 14, 270, 24),
    ]
    mob_shots = [('mob_woolhop', 'woolhop', 5.0, 20), ('mob_mossturtle', 'mossturtle', 5.5, 18),
                 ('mob_islekit', 'islekit', 3.2, 20), ('mob_crystalbeetle', 'crystalbeetle', 2.6, 25),
                 ('mob_pebblebeak', 'pebblebeak', 3.4, 18), ('mob_skyjelly', 'skyjelly', 6.5, 5),
                 ('mob_cloudray', 'cloudray', 12.0, 8)]
    for name, q, r, ty, dist, az, elev in shots:
        if not want(name):
            continue
        frame(q, r, ty, dist, az, elev)
        yield _144_loaded(app)
        yield 2.0
        frame(q, r, ty, dist, az, elev)
        yield 0.4
        yield shot(name)
    for name, kind, dist, elev in mob_shots:
        if not want(name):
            continue
        home = next((m for m in TB.MOBS if m[0] == kind), None)
        if not home:
            continue
        hx_, hz_ = hx(home[1], home[2])
        _144_park(ses, hx_ + 6, (S0 + 8 + home[3]) * LAYER, hz_ + 6, 0.0, -30.0)
        ses.hold = False
        yield _144_loaded(app)
        yield 2.5
        mobs = [m for m in ses.mobs if m.kind == kind]
        if not mobs:
            log('no mob', kind)
            continue
        mob = min(mobs, key=lambda m: math.hypot(m.x - hx_, m.z - hz_))
        from .entities import solid_at as _solid
        best = None
        mh = mob.height * mob.scale * 0.5
        e = math.radians(elev)
        for k in range(12):
            a = math.radians(mob.yaw + 40 + k * 30)
            cx = mob.x + math.sin(a) * math.cos(e) * dist
            cz = mob.z - math.cos(a) * math.cos(e) * dist
            cy = mob.y + mh + math.sin(e) * dist
            clear = all(not _solid(ses.world, mob.x + (cx - mob.x) * t, mob.y + mh + (cy - mob.y - mh) * t,
                                   mob.z + (cz - mob.z) * t) for t in (0.25, 0.4, 0.55, 0.7, 0.85, 1.0))
            if clear:
                best = (cx, cy, cz)
                break
        if best is None:
            best = (cx, cy, cz)
        for _ in range(2):
            mob.vx = mob.vz = 0.0
            mob.think = 30.0
            mob.walking = False
            _144_park(ses, best[0], best[1] - EYE, best[2], 0.0, 0.0)
            look_at(p, mob.x, mob.y + mh, mob.z)
            yield 0.5
        yield shot(name)
    ses.hold = True
    # Glimmer: Tidewell screen and waystone screen
    if want('ui'):
        frame(6, -32, 2, 9, 160, 20)
        yield _144_loaded(app)
        yield 1.0
        ses.give(I.GLIMMER.id, 5, quiet=True)
        app.set_screen(TidewellScreen())
        yield 0.6
        yield shot('tidewell_screen')
        app.set_screen(None)
        yield 0.3
        key = f'8,-32,{S0 + 1}'
        ses.waystones[key] = {'name': ses._waystone_name(8, -32), 'attuned': True}
        ses.waystones[f'10,-58,{S0 + 4}'] = {'name': ses._waystone_name(10, -58), 'attuned': True}
        try:
            app.set_screen(WaystoneScreen(key))
            yield 0.6
            yield shot('waystone_screen')
        except Exception as e:
            log('waystone screen error', e)
        app.set_screen(None)
        yield 0.3
        _144_hud(app, debug=False, hide=False)
        ses.toast('You caught Glimmer!', '1 Glimmer attunes a waystone. 2-4 buys a lasting gift at a Tidewell.', 8)
        yield 0.6
        yield shot('glimmer_toast')
        _144_hud(app, debug=False, hide=True)
    log('mobs', [(m.kind, round(m.x, 1), round(m.z, 1)) for m in ses.mobs])
    log('gallery', len(TB._CACHE.get('gallery', [])), 'light_cap', getattr(app.renderer, 'light_cap', None))
    log('phase144_tutorial2 finished')


def phase144_grand(app, log, shot, look_at, settled, arg):
    """Generator v6: island aerials and seeded grand structures found in the world (not stamped)."""
    from .hexgrid import center as hx
    from . import gensettings as GS
    from . import grand as GR
    from .entities import solid_at as _solid
    args = dict(kv.split('=') for kv in (arg or '').split(',') if '=' in kv)
    seed = int(args.get('seed', 7))
    per = int(args.get('per', 1))
    balloons = int(args.get('balloons', 6))
    only = set(args.get('only', '').split('+')) - {''}
    _144_uncap(app, log, view=int(args.get('vd', 12)), far=int(args.get('far', 22)))
    yield 0.3
    app.create_sky(f'Grand {seed}', seed, str(seed), 'wanderer', gen=GS.normalize({'generator_version': 6}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    gen = ses.world.gen if hasattr(ses.world, 'gen') else None
    from .generator import Generator
    gen = Generator(ses.seed, GS.normalize({'generator_version': 6}))
    log('version', gen.version, 'seed', ses.seed)
    _144_hud(app, debug=False, hide=True)
    ses.phase = float(args.get('phase', 0.03))
    ses.hold = True
    if not only or 'islands' in only:
        sx, sy, sz = p.x, p.y, p.z
        log('spawn', round(sx, 1), round(sy, 1), round(sz, 1))
        from .hexgrid import cell_at as _ca
        q0, r0 = _ca(sx, sz)
        qs = np.arange(q0 - 260, q0 + 260, 6)
        Q, R = np.meshgrid(qs, np.arange(r0 - 260, r0 + 260, 6), indexing='ij')
        c = gen.columns(Q.ravel(), R.ravel())
        land = c['land']
        tops = c['top'][land]
        mid = float(np.median(tops)) * LAYER if len(tops) else sy
        log('window tops', int(tops.min()), int(np.median(tops)), int(tops.max()))
        poses = (
            # wide side view: layered shelves from the cloud sea up to ~440
            ('v6_layers_side', (sx, mid - 20.0, sz + 420.0), (sx, mid + 20.0, sz)),
            ('v6_aerial', (sx + 120.0, mid + 230.0, sz + 300.0), (sx, mid, sz)),
            ('v6_spawn_vista', (sx + 40.0, sy + 30.0, sz + 70.0), (sx, sy - 5.0, sz)),
        )
        for name, (cx, cy, cz), (tx, ty, tz) in poses:
            _144_park(ses, cx, cy - EYE, cz, 0.0, 0.0)
            look_at(p, tx, ty, tz)
            ses.phase = float(args.get('phase', 0.03))
            yield _144_loaded(app, min_chunks=100)
            yield 1.5
            look_at(p, tx, ty, tz)
            yield 0.2
            yield shot(name)
    if 'trees' in only:
        # huge v6 trees and the new landscapes: one per realm/form
        seen = set()
        trees = []
        for gi in range(-24, 24):
            for gj in range(-24, 24):
                t = GR._tree_site(gen, gi, gj)
                if t:
                    trees.append((abs(gi) + abs(gj), t['info']))
        trees.sort(key=lambda t: t[0])
        n = 0
        for _, info in trees:
            sig = (info['realm'], info['form'])
            if sig in seen or n >= int(args.get('trees', 6)):
                continue
            seen.add(sig)
            n += 1
            tx, tz = hx(info['q'], info['r'])
            tyw = (info['top'] + info['H'] * 0.55) * LAYER
            dist = info['H'] * LAYER * 2.6 + 12
            best = None
            for k in range(12):
                a = math.radians(200 + k * 30)
                cx, cz, cy = tx + math.sin(a) * dist, tz - math.cos(a) * dist, tyw + dist * 0.18
                _144_park(ses, cx, cy - EYE, cz, 0.0, 0.0)
                if k == 0:
                    yield _144_loaded(app)
                    yield 1.0
                clear = all(not _solid(ses.world, tx + (cx - tx) * t, tyw + (cy - tyw) * t, tz + (cz - tz) * t)
                            for t in (0.45, 0.6, 0.75, 0.9, 1.0))
                if clear:
                    best = (cx, cy, cz)
                    break
            best = best or (cx, cy, cz)
            _144_park(ses, best[0], best[1] - EYE, best[2], 0.0, 0.0)
            look_at(p, tx, tyw, tz)
            ses.phase = float(args.get('phase', 0.03))
            yield _144_loaded(app)
            yield 1.5
            look_at(p, tx, tyw, tz)
            yield 0.3
            from . import materials as _MT
            name = f"tree_{_MT.REALMS[info['realm']].split()[0].lower()}_{info['form']}"
            yield shot(name)
            log('SHOT', name, info)
    sites = []
    for rq in range(-6, 6):
        for rr in range(-6, 6):
            s = GR.site(gen, rq, rr)
            if s:
                sites.append((abs(rq) + abs(rr), rq, rr, s))
    sites.sort(key=lambda t: t[0])
    counts = {}
    for _, rq, rr, s in sites:
        kind = s['kind']
        lim = balloons if kind == 'hot_air_balloon' else per
        if only and kind not in only:
            continue
        if counts.get(kind, 0) >= lim:
            continue
        b = GR.build(gen, rq, rr)
        if not b:
            continue
        info = b['info']
        if kind == 'hot_air_balloon':
            # several seeded variants: skip repeats of the same shape and pattern
            sig = (info['shape'], info['pattern'])
            seen = counts.setdefault('_sig', set())
            if sig in seen and len(seen) < 5:
                continue
            seen.add(sig)
        counts[kind] = counts.get(kind, 0) + 1
        q, r, y = s['q'], s['r'], s['y']
        if kind == 'hot_air_balloon':
            ty = (info['top'] + info['bottom']) / 2
            dist = info['R'] * SQ3_ * 3.3
            elev = 6
        elif kind == 'sky_city':
            ty, dist, elev = y + 18, 88, 16
        elif kind == 'floating_fortress':
            ty, dist, elev = y + 8, info['R'] * SQ3_ * 2.5, 12
        elif kind == 'airship':
            ty, dist, elev = y, info['length'] * SQ3_ * 1.5, 10
        elif kind == 'world_tree':
            ty, dist, elev = y + info['height'] * 0.55, info['height'] * LAYER * 1.7, 8
        elif kind == 'colossus':
            ty, dist, elev = y + info['height'] * 0.55, info['height'] * LAYER * 1.55, 6
        elif kind == 'megaspire':
            ty, dist, elev = y + info['height'] * 0.5, info['height'] * LAYER * 1.35, 5
        elif kind == 'leviathan_wreck':
            ty, dist, elev = y + 6, info['length'] * SQ3_ * 0.6, 24
        else:
            ty, dist, elev = y + 22, 115, 20
        tx, tz = hx(q, r)
        tyw = ty * LAYER
        _144_park(ses, tx, tyw + 30, tz + dist * 0.5, 0.0, -20.0)
        yield _144_loaded(app)
        yield 1.5
        best = None
        e = math.radians(elev)
        for k in range(12):
            a = math.radians(200 + k * 30)
            cx = tx + math.sin(a) * math.cos(e) * dist
            cz = tz - math.cos(a) * math.cos(e) * dist
            cy = tyw + math.sin(e) * dist
            clear = all(not _solid(ses.world, tx + (cx - tx) * t, tyw + (cy - tyw) * t, tz + (cz - tz) * t)
                        for t in (0.55, 0.65, 0.75, 0.85, 0.95, 1.0))
            if clear:
                best = (cx, cy, cz)
                break
        if best is None:
            best = (cx, cy, cz)
        _144_park(ses, best[0], best[1] - EYE, best[2], 0.0, 0.0)
        look_at(p, tx, tyw, tz)
        ses.phase = float(args.get('phase', 0.03))
        yield _144_loaded(app)
        yield 2.0
        look_at(p, tx, tyw, tz)
        yield 0.3
        name = f'grand_{kind}_{counts[kind]}'
        yield shot(name)
        log('SHOT', name, 'q', q, 'r', r, 'y', y, 'info', info, 'cells', b['cells'],
            'cam', [round(v, 1) for v in best])
    log('phase144_grand finished', {k: v for k, v in counts.items() if k != '_sig'})


SQ3_ = 3 ** 0.5


def phase144_showcase5(app, log, shot, look_at, settled, arg):
    """The favourite seed, as generator v5 makes it (old saves stay byte-identical)."""
    from . import gensettings as GS
    args = dict(kv.split('=') for kv in (arg or '').split(',') if '=' in kv)
    seed = int(args.get('seed', -1565669544))
    x0, z0 = float(args.get('x', -1603)), float(args.get('z', -2679))
    _144_uncap(app, log, view=int(args.get('vd', 12)), far=int(args.get('far', 24)))
    yield 0.3
    app.create_sky(f'Showcase {seed}', seed, str(seed), 'wanderer', gen=GS.normalize({'generator_version': 5}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    from .generator import Generator
    from .hexgrid import cell_at as _ca
    gen = Generator(ses.seed, GS.normalize({'generator_version': 5}))
    q0, r0 = _ca(x0, z0)
    c = gen.columns(np.array([q0]), np.array([r0]))
    ground = (int(c['top'][0]) + 1) * LAYER if bool(c['land'][0]) else 160.0
    log('version', gen.version, 'ground', ground, 'realm', int(c['realm'][0]))
    _144_hud(app, debug=False, hide=True)
    ses.hold = True
    poses = (('seed5_cedar_vista', (x0 + 60, ground + 28, z0 + 80), (x0, ground, z0)),
             ('seed5_cedar_high', (x0 - 140, ground + 90, z0 + 150), (x0, ground - 10, z0)),
             ('seed5_cedar_ground', (x0 + 18, ground + 6, z0 + 22), (x0 - 20, ground + 4, z0 - 30)))
    for name, (cx, cy, cz), (tx, ty, tz) in poses:
        _144_park(ses, cx, cy - EYE, cz, 0.0, 0.0)
        look_at(p, tx, ty, tz)
        ses.phase = float(args.get('phase', 0.03))
        yield _144_loaded(app, min_chunks=80)
        yield 1.5
        look_at(p, tx, ty, tz)
        yield 0.3
        yield shot(name)
    log('phase144_showcase5 finished')


def phase145_lookup(app, log, shot, look_at, settled, arg):
    """v6 stacked sky tiers: look up from mid-height and from the spawn surface."""
    from . import gensettings as GS
    args = dict(kv.split('=') for kv in (arg or '').split(',') if '=' in kv)
    seed = int(args.get('seed', 7))
    _144_uncap(app, log, view=int(args.get('vd', 10)), far=int(args.get('far', 20)))
    yield 0.3
    app.create_sky(f'Lookup {seed}', seed, str(seed), 'wanderer', gen=GS.normalize({'generator_version': 6}))
    yield lambda: app.mode == 'game'
    yield settled()
    yield 1.0
    ses = app.session
    p = ses.player
    _144_hud(app, debug=False, hide=True)
    ses.hold = True
    sx, sy, sz = p.x, p.y, p.z
    poses = (('lookup_low', (sx + 30.0, 90 * LAYER, sz + 30.0), 30.0),
             ('lookup_mid', (sx + 30.0, 250 * LAYER, sz + 30.0), 30.0),
             ('level_mid', (sx + 30.0, 250 * LAYER, sz + 30.0), 4.0),
             ('lookup_high', (sx + 30.0, 420 * LAYER, sz + 30.0), 25.0),
             ('down_high', (sx + 30.0, 440 * LAYER, sz + 30.0), -30.0),
             ('down_mid', (sx + 30.0, 250 * LAYER, sz + 30.0), -28.0),
             ('level_high', (sx + 30.0, 440 * LAYER, sz + 30.0), 2.0))
    for name, (cx, cy, cz), pitch in poses:
        _144_park(ses, cx, cy - EYE, cz, 0.0, pitch)
        ses.phase = float(args.get('phase', 0.03))
        yield _144_loaded(app, min_chunks=120)
        yield 2.0
        p.pitch = pitch
        yield 0.3
        yield shot(name)
    if args.get('perf', '1') == '1':
        import time as _t
        for label, (cx, cy, cz), pitch in (('ground', (sx, sy + 0.5, sz), 0.0), ('mid_air', (sx + 30.0, 250 * LAYER, sz + 30.0), 4.0)):
            _144_park(ses, cx, cy - EYE, cz, 0.0, pitch)
            yield _144_loaded(app, min_chunks=120)
            yield 1.0
            st = {'t0': _t.perf_counter(), 'n': 0}

            def done(st=st):
                st['n'] += 1
                return _t.perf_counter() - st['t0'] >= 5.0
            yield done
            el = _t.perf_counter() - st['t0']
            w = ses.world
            gen_t = list(w.timings.get('gen', []))
            log('PERF', label, 'fps=%.1f' % ((st['n'] - 1) / el), 'chunks', len(w.chunks),
                'gen_ms_mean=%.0f' % (1000 * np.mean(gen_t) if gen_t else -1))
    log('phase145_lookup finished')

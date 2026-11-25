"""Tour scripts (generators). Yield seconds to wait or a predicate to wait for."""
import math
import random

import numpy as np

from .config import LAYER, CHUNK
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


def _find_under_canopy(ses, origin=None, reach=64):
    """A walkable ground cell beside a trunk, with canopy at least 3 layers overhead."""
    WOOD = {M['heartwood'], M['cedar_heartwood'], M['pale_heartwood'], M['dark_heartwood']}
    LEAF = {M['canopy']}
    pq, pr = origin or cell_at(ses.player.x, ses.player.z)
    for rad in range(0, reach + 1):
        cells = [(pq, pr)] if rad == 0 else list(ring(pq, pr, rad))
        for aq, ar in cells:
            top = ses.world.column_top(aq, ar)
            if top is None:
                continue
            trunk_y = None
            leaf_y = None
            for y in range(top, max(0, top - 18), -1):
                mat = ses.world.get(aq, ar, y)
                if mat in LEAF and leaf_y is None:
                    leaf_y = y
                if mat in WOOD:
                    trunk_y = y
                    break
            if trunk_y is None or leaf_y is None:
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
                for y in range(gt + 3, gt + 12):
                    if ses.world.get(nq, nr, y) in LEAF or ses.world.get(aq, ar, y) in LEAF:
                        overhead = y
                        break
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
    app.create_sky('Phase 5', 1729, '1729', 'dreamer')
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

"""The window: title backdrop, menus, the open sky, input and drawing."""
import math
import multiprocessing as mp
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pyglet
from pyglet.window import key, mouse
import moderngl

from . import config as C
from .audio import Audio
from .config import LAYER
from .generator import Generator
from .hexgrid import center, cell_at, chunk_of
from .mathutil import perspective, view_matrix
from .noise import random_seed, seed_from_text
from . import showcase
from .renderer import Renderer
from .screenshot import capture, png_bytes
from .session import Session, find_spawn
from .settings import Settings
from .storage import SkyStorage
from . import tide as TIDE
from . import materials as MT
from .ui.gui import Gui
from .ui.hud import draw_hud
from .ui import screens as S
from .ui import inventory_ui as IU
from . import items as IT
from . import models as MD
from .world import World
from . import workers


class App(pyglet.window.Window):
    def __init__(self, base_dir, size=C.WINDOW_SIZE, workers_count=4):
        self.base_dir = base_dir
        self.skies_dir = os.path.join(base_dir, 'skies')
        self.shots_dir = os.path.join(base_dir, 'snapshots')
        os.makedirs(self.skies_dir, exist_ok=True)
        self.settings = Settings(os.path.join(base_dir, 'settings.json'))
        cfg = pyglet.gl.Config(major_version=3, minor_version=3, forward_compatible=True, depth_size=24,
                               double_buffer=True)
        super().__init__(size[0], size[1], caption='Tidewake', resizable=True, vsync=self.settings['vsync'], config=cfg)
        self.set_minimum_size(800, 480)
        self.ctx = moderngl.create_context()
        self.renderer = Renderer(self.ctx)
        self._build_icons()
        self.gui = Gui(self.ctx)
        self.audio = Audio(self.settings['sounds'] / 100, self.settings['music'] / 100)
        self.gui.sound = lambda n: self.audio.play(n, 0.5)
        self._set_icon()
        self.pool = ProcessPoolExecutor(max_workers=workers_count, mp_context=mp.get_context('spawn'),
                                        initializer=workers.init_worker)
        self.audio.start_music(os.path.join(base_dir, 'music-cache'))
        self._under, self._under_t = 0.0, 0.0
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.session = None
        self.backdrop = None
        self.menu = None
        self.mode = 'title'
        self.captured = False
        self.buttons = set()
        self.swallow_text = False
        self.show_debug = False
        self.hide_hud = False
        self.cam_view = 0          # 0 first person, 1 behind, 2 in front
        self.frame_times = []
        self.started = time.perf_counter()
        self.clock_t = 0.0
        self.jump_pressed = False
        self.shot_queue = []
        self.thumb_cache = {}
        self.want_thumb = False
        self.test_input = None
        self.on_frame = None
        self._scheduled = False
        last = self.settings.get('title_showcase', '')
        chosen = showcase.choose_launch(last)
        if chosen:
            self.settings['title_showcase'] = chosen
            self.settings.save()
        self.start_backdrop()
        self.set_screen(S.TitleScreen())
        if self.settings['fullscreen']:
            self.set_fullscreen(True)
        self.schedule_frames()

    def _build_icons(self):
        models = {}
        for iid, it in IT.ITEMS.items():
            v = MD.cached_item(iid)
            if it.model in ('block', 'deco'):
                models[iid] = (v, 30.0, -30.0, 0.95 if it.model == 'block' else 1.15)
            elif it.model in MD.SPRITES:
                models[iid] = (v, 18.0, -8.0, 1.05)
            else:
                models[iid] = (v, 30.0, -32.0, 1.55)
        try:
            from . import icons2d
            art = {iid: icons2d.render(it) for iid, it in IT.ITEMS.items()}
            self.renderer.build_icons(models, art={k: v for k, v in art.items() if v is not None})
        except Exception as e:
            print('icons failed:', e)
        self.ctx.viewport = (0, 0, *self.get_framebuffer_size())

    def keys_down_shift(self):
        return bool(self.keys[key.LSHIFT] or self.keys[key.RSHIFT])

    def on_faded(self, why):
        self.set_screen(IU.FadedScreen(why))

    def _set_icon(self):
        try:
            from .icon import icon_images
            self.set_icon(*icon_images())
        except Exception as e:
            print('icon:', e)

    # ------------------------------------------------------------------ loop & settings
    def schedule_frames(self):
        if self._scheduled:
            pyglet.clock.unschedule(self._frame)
        lim = self.settings['fps_limit']
        if lim:
            pyglet.clock.schedule_interval(self._frame, 1.0 / lim)
        else:
            pyglet.clock.schedule(self._frame)
        self._scheduled = True

    def _frame(self, dt):
        if self.has_exit:
            return
        self.tick(dt)
        if not self.has_exit:
            self.draw()

    def apply_settings(self, old=None):
        st = self.settings
        old = old or {}
        if old.get('vsync') != st['vsync']:
            self.set_vsync(st['vsync'])
        if bool(self.fullscreen) != st['fullscreen']:
            self.set_fullscreen(st['fullscreen'])
        if old.get('view_distance') != st['view_distance'] or old.get('far_distance') != st['far_distance']:
            if self.session:
                self.session.world.set_view_distance(st['view_distance'], st['far_distance'])
            if self.backdrop:
                self.backdrop['world'].set_view_distance(min(st['view_distance'], 6))
        self.audio.set_volumes(st['sounds'] / 100, st['music'] / 100)
        if old.get('fps_limit') != st['fps_limit']:
            self.schedule_frames()

    def ui_scale(self, w, h):
        g = self.settings['ui_scale']
        if g:
            return [1, 0.8, 1.0, 1.25, 1.5][g]
        return max(0.7, min(2.5, min(w / 1280, h / 720)))

    # ------------------------------------------------------------------ screens / modes
    def set_screen(self, screen):
        self.menu = screen
        self.gui.focus = getattr(screen, 'initial_focus', None)
        self.set_capture(screen is None and self.mode == 'game')
        if isinstance(screen, S.RestScreen) and self.session:
            self.want_thumb = True

    def set_capture(self, on):
        self.captured = on
        try:
            self.set_exclusive_mouse(on)
        except Exception:
            pass
        if not on:
            self.buttons.clear()

    def start_backdrop(self):
        try:
            sc = showcase.pick()
        except Exception as e:
            print('showcase unavailable:', e)
            sc = None
        old = self.backdrop
        if sc is not None:
            # JSON builds keep their original sky; seed showcases use the current generator.
            world = World(seed_from_text(sc.seed_text), None, self.renderer, self.pool, min(self.settings['view_distance'], 6),
                          far_distance=10, gen_settings=getattr(sc, 'gen', None))
            world.on_chunk_loaded = sc.apply_chunk
            cam = sc.camera
            x, z = sc.focus()
            arc = cam.get('arc')
            if arc and len(arc) >= 2:
                a0, a1 = float(arc[0]), float(arc[1])
                ang0 = (a0 + a1) / 2.0
                arc_t = (a0, a1)
            else:
                ang0 = random.uniform(0, 6.28)
                arc_t = None
            self.backdrop = dict(world=world, x=x, z=z, y=(sc.top + cam.get('height', 13)) * LAYER,
                                 ty=(sc.top + cam.get('target_dy', 5)) * LAYER, rad=cam.get('radius', 30.0),
                                 speed=cam.get('speed', 0.035), ang=ang0, ang_t=0.0, arc=arc_t,
                                 phase=cam.get('phase', 0.2), showcase=sc, yaw_off=cam.get('yaw_offset', 0.0),
                                 rotate_in=time.perf_counter() + 24.0)
            if old:
                try:
                    old['world'].close()
                except Exception:
                    pass
            return
        seed = random_seed()
        from . import gensettings as GS
        gen = Generator(seed, GS.normalize({}, new=True))
        q, r, top, sp = find_spawn(gen)
        if sp:
            q, r, top = sp['q'], sp['r'], sp['top']
        x, z = center(q, r)
        world = World(seed, None, self.renderer, self.pool, min(self.settings['view_distance'], 5),
                      gen_settings=GS.normalize({}, new=True))
        self.backdrop = dict(world=world, x=x, z=z, y=(top + 26) * LAYER, ty=(top + 6) * LAYER,
                             ang=random.uniform(0, 6.28), phase=random.choice([0.06, 0.16, 0.27, 0.33, 0.72]),
                             rotate_in=time.perf_counter() + 24.0)
        if old:
            try:
                old['world'].close()
            except Exception:
                pass

    def stop_backdrop(self):
        if self.backdrop:
            self.backdrop['world'].close()
            self.backdrop = None

    def create_sky(self, name, seed, seed_text, mode, gen=None, tutorial=False):
        folder = SkyStorage.unique_folder(self.skies_dir, name)
        st = SkyStorage(self.skies_dir, folder)
        from . import gensettings as GS
        ses = Session(self, st, create=dict(name=name, seed=seed, seed_text=seed_text, mode=mode,
                                           gen=GS.normalize(gen, new=True), tutorial=tutorial),
                      view_distance=self.settings['view_distance'], far_distance=self.settings['far_distance'])
        self.begin(ses, 'Dreaming ' + name)

    def start_tutorial(self):
        """Open the lesson island, or dream a fresh one if none is saved yet."""
        for row in SkyStorage.list_skies(self.skies_dir):
            try:
                d = SkyStorage(self.skies_dir, row['folder']).load()
            except Exception:
                continue
            if d.get('tutorial'):
                self.open_sky(row['folder'])
                return
        self.create_sky('The Lesson', 1, 'lesson', 'wanderer', tutorial=True)

    def open_sky(self, folder):
        ses = Session(self, SkyStorage(self.skies_dir, folder), view_distance=self.settings['view_distance'], far_distance=self.settings['far_distance'])
        self.begin(ses, 'Returning to ' + ses.name)

    def begin(self, ses, title):
        self.stop_backdrop()
        self.session = ses
        self.mode = 'loading'
        self.load_started = time.perf_counter()
        self.set_screen(S.LoadingScreen(title))

    def quit_to_title(self):
        if self.session:
            self.session.close()
            self.drop_thumb(self.session.storage.folder)
            self.session = None
        self.mode = 'title'
        self.start_backdrop()
        self.set_screen(S.TitleScreen())

    def quit(self):
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                print('save failed', e)
            self.session = None
        self.stop_backdrop()
        self.settings.save()
        self.audio.shutdown()
        self.pool.shutdown(wait=False, cancel_futures=True)
        pyglet.app.exit()
        self.has_exit = True

    def on_close(self):
        self.quit()

    def thumb(self, folder):
        if folder not in self.thumb_cache:
            self.thumb_cache[folder] = SkyStorage(self.skies_dir, folder).load_thumb()
        return self.thumb_cache[folder]

    def drop_thumb(self, folder):
        self.thumb_cache.pop(folder, None)
        self.gui.drop_texture(('thumb', folder))

    # ------------------------------------------------------------------ input
    def _gui_pos(self, x, y):
        fw, fh = self.get_framebuffer_size()
        return x * fw / max(1, self.width), y * fh / max(1, self.height)

    def on_key_press(self, symbol, modifiers):
        g = self.gui
        if symbol in (key.ENTER, key.NUM_ENTER):
            g.keys.append('enter')
        elif symbol == key.TAB:
            g.keys.append('tab')
        if symbol == key.ESCAPE:
            if self.menu is not None:
                self.menu.escape(self)
            elif self.mode == 'game':
                self.set_screen(S.RestScreen())
            return pyglet.event.EVENT_HANDLED
        if symbol == key.F2:
            self.snapshot()
        elif symbol == key.F11:
            self.settings['fullscreen'] = not self.settings['fullscreen']
            self.apply_settings({'fullscreen': not self.settings['fullscreen']})
        if self.mode != 'game' or not self.session:
            return pyglet.event.EVENT_HANDLED
        ses = self.session
        if self.menu is not None:
            if isinstance(self.menu, S.JournalScreen) and symbol in (key.J, key.TAB):
                self.set_screen(None)
            elif isinstance(self.menu, IU.SlotScreen) and symbol == key.E:
                self.menu.escape(self)
            elif isinstance(self.menu, IU.AdminScreen) and symbol == key.F7:
                self.set_screen(None)
            elif isinstance(self.menu, IU.SlotScreen) and key._1 <= symbol <= key._9:
                # hotkey swap: put the hovered stack into that hotbar slot (handled simply: select it)
                ses.select(symbol - key._1)
            return pyglet.event.EVENT_HANDLED
        if key._1 <= symbol <= key._9:
            ses.select(symbol - key._1)
        elif symbol == key.SPACE:
            self.jump_pressed = True
        elif symbol == key.F3:
            self.show_debug = not self.show_debug
        elif symbol == key.F1:
            self.hide_hud = not self.hide_hud
        elif symbol == key.F4:
            ses.set_dev(not ses.dev)
            self.audio.play('chord', 0.7)
        elif symbol == key.F5:
            self.cam_view = (self.cam_view + 1) % 3
            ses.toast(('First person', 'Third person', 'Looking at you')[self.cam_view],
                      'F5 cycles the camera, like in many sandbox games.', 2.2)
        elif symbol == key.F7:
            if not ses.dev:
                ses.toast('Dev mode is off', 'Press F4 to turn it on, then F7 for the admin panel.', 3)
            else:
                self.set_screen(IU.AdminScreen())
        elif symbol == key.E:
            self.set_screen(IU.BackpackScreen())
            self.audio.play('step_wood', 0.5)
        elif symbol == key.Q:
            sl = ses.held
            if sl:
                from .entities import Drop
                from .mathutil import forward_vector
                p = ses.player
                f = forward_vector(p.yaw, p.pitch)
                n = sl[1] if modifiers & key.MOD_CTRL else 1
                d = Drop(sl[0], n, p.x + f[0] * 0.8, p.y + 1.3, p.z + f[2] * 0.8, sl[2], vy=2 + f[1] * 3)
                d.vx, d.vz = f[0] * 5, f[2] * 5
                d.age = -1.0
                ses.drops.append(d)
                ses.inv.take_from(ses.hot, n)
        elif symbol == key.F and ses.dev:
            ses.player.drifting = not ses.player.drifting
            ses.player.vy = 0
            ses.toast('Flying' if ses.player.drifting else 'Walking', 'Space up, Ctrl / C down, Shift faster' if ses.player.drifting else '', 1.5)
        elif symbol == key.N and ses.dev:
            ses.command('/noclip')
        elif symbol in (key.BRACKETLEFT, key.BRACKETRIGHT) and ses.dev:
            p = ses.player
            p.fly_speed = max(2.0, min(120.0, p.fly_speed * (1.25 if symbol == key.BRACKETRIGHT else 0.8)))
            ses.toast(f'Flying speed {p.fly_speed:.0f}', '', 1.2)
        elif symbol == key.T:
            if ses.can_tidecall:
                ses.tide_rush = 30.0
                ses.toast('You call the tide', 'The sky hurries toward the next tide.', 3)
                self.audio.play('tide', 0.7)
            else:
                ses.toast('Tidecall is not yours yet', 'Wake three spires to learn it.', 2.5)
        elif symbol in (key.J, key.TAB):
            self.set_screen(S.JournalScreen())
        elif symbol == key.P:
            from .ui.systems import PathScreen
            self.set_screen(PathScreen())
        elif symbol in (key.SLASH, key.ENTER, key.NUM_ENTER):
            self.swallow_text = symbol != key.SLASH
            self.set_screen(S.WhisperScreen('/' if symbol == key.SLASH else ''))
            self.swallow_text = True
        return pyglet.event.EVENT_HANDLED

    def on_text(self, text):
        if self.swallow_text:
            self.swallow_text = False
            if text in ('/', '\r', '\n'):
                return
        if self.menu is not None and text not in ('\r', '\n', '\t'):
            self.gui.typed += text

    def on_text_motion(self, motion):
        if motion == key.MOTION_BACKSPACE:
            self.gui.keys.append('backspace')

    def on_mouse_press(self, x, y, button, modifiers):
        self.gui.mx, self.gui.my = self._gui_pos(x, y)
        if self.menu is not None or self.mode != 'game':
            if button == mouse.LEFT:
                self.gui.clicks.append((self.gui.mx, self.gui.my, 1))
                self.gui.mouse_down = True
            elif button == mouse.RIGHT:
                self.gui.clicks.append((self.gui.mx, self.gui.my, 4))
            elif button == mouse.MIDDLE:
                self.gui.clicks.append((self.gui.mx, self.gui.my, 2))
            return
        if not self.captured:
            self.set_capture(True)
            return
        self.buttons.add(button)
        if self.session:
            self.session.cooldown = 0
            if button == mouse.MIDDLE and self.session.remove_inv_slot():
                self.audio.play('click', 0.4)
                self.session.toast('That item is gone', 'Middle-click removes things in Dreamer mode.', 2.2)

    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            self.gui.mouse_down = False
        self.buttons.discard(button)

    def on_mouse_motion(self, x, y, dx, dy):
        self.gui.mx, self.gui.my = self._gui_pos(x, y)
        if self.captured and self.session and self.menu is None:
            sens = 0.12 * self.settings['sensitivity'] / 100
            p = self.session.player
            p.yaw = (p.yaw + dx * sens) % 360
            p.pitch = max(-89, min(89, p.pitch + dy * sens * (-1 if self.settings['invert_y'] else 1)))

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.on_mouse_motion(x, y, dx, dy)

    def on_mouse_scroll(self, x, y, sx, sy):
        if self.menu is not None or self.mode != 'game':
            self.gui.scroll += sy
        elif self.session:
            self.session.cycle_hot(-1 if sy > 0 else 1)

    def on_deactivate(self):
        if self.mode == 'game' and self.menu is None:
            self.set_screen(S.RestScreen())

    # ------------------------------------------------------------------ update
    def tick(self, dt):
        dt = min(dt, 0.1)
        self.clock_t += dt
        self.frame_times.append(dt)
        self.frame_times = self.frame_times[-120:]
        if self.on_frame:
            self.on_frame(dt)
        dusk = 0.3
        if self.mode == 'title' and self.backdrop:
            b = self.backdrop
            if b.get('arc') and b.get('speed', 0.05):
                a0, a1 = b['arc']
                b['ang_t'] = b.get('ang_t', 0.0) + dt * b.get('speed', 0.05)
                mid, half = (a0 + a1) / 2.0, (a1 - a0) / 2.0
                b['ang'] = mid + half * math.sin(b['ang_t'])
            elif not b.get('arc'):
                b['ang'] += dt * b.get('speed', 0.05)
            b['world'].update(b['x'], b['z'], 4)
            dusk = TIDE.dusk_amount(b['phase'])
            if time.perf_counter() >= b.get('rotate_in', 1e18) and self.menu and self.menu.__class__.__name__ == 'TitleScreen':
                self.start_backdrop()
        elif self.mode == 'loading' and self.session:
            prog = self.session.load_progress()
            if isinstance(self.menu, S.LoadingScreen):
                self.menu.progress = prog
            if (prog >= 0.98 and time.perf_counter() - self.load_started > 0.8) or time.perf_counter() - self.load_started > 60:
                self.session.finish_loading()
                self.mode = 'game'
                self.set_screen(None)
        elif self.mode == 'game' and self.session:
            ses = self.session
            paused = self.menu is not None and self.menu.pauses
            if not paused:
                k = self.keys
                ti = self.test_input or {}
                free = self.menu is None or isinstance(self.menu, S.WhisperScreen)
                if not free:
                    k = {}
                    k = key.KeyStateHandler()
                inp = dict(
                    fwd=ti.get('fwd', (1 if k[key.W] or k[key.UP] else 0) - (1 if k[key.S] or k[key.DOWN] else 0)),
                    strafe=ti.get('strafe', (1 if k[key.D] or k[key.RIGHT] else 0) - (1 if k[key.A] or k[key.LEFT] else 0)),
                    jump=ti.get('jump', bool(k[key.SPACE])) if self.menu is None else False,
                    jump_pressed=ti.get('jump_pressed', self.jump_pressed),
                    down=ti.get('down', bool(k[key.C] or (k[key.LSHIFT] and (self.session.player.drifting if self.session else False)))),
                    hurry=ti.get('hurry', bool(k[key.LCTRL] or k[key.RCTRL])),
                    crouch=ti.get('crouch', bool(k[key.LSHIFT] or k[key.RSHIFT])),
                    gather=ti.get('gather', mouse.LEFT in self.buttons and self.menu is None),
                    shape=ti.get('shape', mouse.RIGHT in self.buttons and self.menu is None))
                if self.test_input:
                    self.test_input.pop('jump_pressed', None)
                    if not self.test_input.get('hold'):
                        self.test_input.pop('gather', None)
                    self.test_input.pop('shape', None)
                ses.update(dt, inp)
            else:
                ses.world.update(ses.player.x, ses.player.z, yaw=ses.player.yaw)
            dusk = TIDE.dusk_amount(ses.phase)
        self.jump_pressed = False
        self._water = 0.0
        if self.mode == 'game' and self.session:
            self._under_t -= dt
            if self._under_t <= 0:                    # enclosed above and below -> underground
                self._under_t = 0.5
                try:
                    self._under = 1.0 if self.session.sky_at(*self.session.player.eye) < 0.3 else 0.0
                except Exception:
                    self._under = 0.0
            try:
                from .hexgrid import cell_at
                from .materials import ID as _MID
                ex, ey, ez = self.session.player.eye
                q, r = cell_at(ex, ez)
                if self.session.world.get(q, r, math.floor(ey / LAYER)) == _MID['water']:
                    self._water = 1.0
            except Exception:
                self._water = 0.0
        else:
            self._under = 0.0
        rain = bool(self.session and getattr(self.session, 'weather', '') == 'rain')
        tutorial = bool(self.session and getattr(self.session, 'tutorial', False))
        self.audio.update(dt, dusk, 'game' if self.mode == 'game' else 'menu', self._under,
                          rain=rain, tutorial=tutorial, water=self._water > 0.5)

    # ------------------------------------------------------------------ draw
    def camera(self):
        if self.mode == 'game' and self.session:
            p = self.session.player
            x, y, z = p.eye
            if self.settings['head_bob'] and p.on_ground:
                y += math.sin(self.session.walk * 2.2) * 0.04
            yaw, pitch = p.yaw, p.pitch
            if self.cam_view:
                from .mathutil import forward_vector
                from .entities import solid_at
                fwd = forward_vector(p.yaw, p.pitch)
                sign = 1.0 if self.cam_view == 2 else -1.0
                # look-at-you sits closer so the face can actually be read
                dist, best = (2.6 if self.cam_view == 2 else 4.0), (x, y, z)
                for i in range(1, 17):
                    tlen = dist * i / 16
                    nx, ny, nz = x + sign * fwd[0] * tlen, y + sign * fwd[1] * tlen, z + sign * fwd[2] * tlen
                    if solid_at(self.session.world, nx, ny, nz):
                        break
                    best = (nx, ny, nz)
                x, y, z = best
                if self.cam_view == 2:
                    yaw = (p.yaw + 180.0) % 360
                    pitch = -p.pitch
            return (x, y, z), yaw, pitch, self.session.phase, self.session.world
        b = self.backdrop
        if b:
            rad = b.get('rad', 46.0)
            x = b['x'] + math.cos(b['ang']) * rad
            z = b['z'] + math.sin(b['ang']) * rad
            yaw = math.degrees(math.atan2(b['x'] - x, -(b['z'] - z)))
            if self.menu is not None:
                yaw += b.get('yaw_off', 0.0)          # frame the build beside the menu, not behind it
            pitch = math.degrees(math.atan2(b['ty'] - b['y'], rad)) + 4
            return (x, b['y'], z), yaw, pitch, b['phase'], b['world']
        return None

    def draw(self):
        self.switch_to()
        ctx = self.ctx
        fw, fh = self.get_framebuffer_size()
        ctx.viewport = (0, 0, fw, fh)
        cam = self.camera()
        if cam is not None and self.mode != 'loading':
            (cx, cy, cz), yaw, pitch, phase, world = cam
            atmo = TIDE.atmosphere(phase)
            fog_end = max(world.radius, getattr(world, 'lod_radius', 0)) * 0.98
            proj = perspective(self.settings['fov'], fw / max(1, fh), 0.08, fog_end * 2.5 + 200)
            vr = view_matrix((0, 0, 0), yaw, pitch)
            extra = self.session.extra_lights((cx, cy, cz)) if self.mode == 'game' and self.session else []
            dyn = self.session.dynamic_models((cx, cy, cz)) if self.mode == 'game' and self.session else None
            self.renderer.draw((cx, cy, cz), proj, vr, world.meshes(), atmo, fog_end, self.clock_t, extra,
                               clouds=self.settings['clouds'], dynamic=dyn)
            if self.mode == 'game' and self.session:
                ses = self.session
                if ses.target and not self.hide_hud and self.menu is None:
                    q, r, y = ses.target
                    tx, tz = center(q, r)
                    self.renderer.draw_outline((tx - cx, y * LAYER - cy, tz - cz))
                self.renderer.draw_points(ses.point_data((cx, cy, cz)))
                if not self.hide_hud and self.menu is None and not ses.dead and not self.cam_view:
                    bob = math.sin(ses.walk * 2.2) * 0.015 if self.settings['head_bob'] else 0.0
                    self.renderer.draw_held(ses.held_model((cx, cy, cz), bob))
                if self.want_thumb:
                    self.want_thumb = False
                    self._save_thumb()
        else:
            ctx.clear(0.95, 0.88, 0.86, 1.0)
        # UI
        w, h = fw, fh
        g = self.gui
        g.begin(w, h, self.ui_scale(w, h))
        if self.mode == 'game' and self.session and getattr(self.session, 'sleeping', None):
            a = self.session.sleep_fade()
            if a > 0.01:
                g.rect(0, 0, w, h, (0.03, 0.03, 0.08, a))
                g.flush()
        if self.mode == 'game' and self.session and not self.hide_hud and (self.menu is None or isinstance(self.menu, S.WhisperScreen)):
            draw_hud(g, self, self.session, w, h)
            if self.show_debug:
                self._debug(g, w, h)
            g.flush()
        if self.menu is not None:
            self.menu.build(g, self, w, h)
        g.end()
        if self.shot_queue:
            path = self.shot_queue.pop(0)
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            capture(ctx, path)
        self.flip()

    def on_draw(self):
        pass

    def _save_thumb(self):
        try:
            fw, fh = self.get_framebuffer_size()
            data = self.ctx.screen.read(viewport=(0, 0, fw, fh), components=3, alignment=1)
            _ = self.ctx.error
            img = np.frombuffer(data, np.uint8).reshape(fh, fw, 3)[::-1]
            th, tw = 108, 192
            ys = (np.arange(th) * fh / th).astype(int)
            xs = (np.arange(tw) * fw / tw).astype(int)
            small = img[ys][:, xs]
            rgba = np.concatenate([small, np.full((th, tw, 1), 255, np.uint8)], 2)
            self.session.storage.save_thumb(rgba)
            self.drop_thumb(self.session.storage.folder)
        except Exception as e:
            print('thumbnail failed:', e)

    def snapshot(self, path=None):
        os.makedirs(self.shots_dir, exist_ok=True)
        path = path or os.path.join(self.shots_dir, time.strftime('tidewake-%Y%m%d-%H%M%S.png'))
        self.shot_queue.append(path)
        if self.session:
            self.session.toast('Snapshot saved', os.path.basename(path), 2.5)

    def _debug(self, g, w, h):
        ses = self.session
        p = ses.player
        ft = self.frame_times[-60:] or [1]
        fps = len(ft) / max(sum(ft), 1e-6)
        q, r = cell_at(p.x, p.z)
        cq, cr = chunk_of(q, r)
        realm = ses.world.realm_at(q, r)
        avg = lambda d: (sum(d) / len(d) * 1000) if d else 0
        st = self.renderer.stats
        lines = [f'Tidewake 1.4.2-test   {fps:.0f} fps   creatures {len(ses.mobs)}   drops {len(ses.drops)}',
                 f'position  x {p.x:,.2f}   y {p.y:.2f}   z {p.z:,.2f}',
                 f'cell  q {q:,}  r {r:,}  layer {math.floor(p.y / LAYER)}   chunk {cq:,} {cr:,}',
                 f'realm  {MT.REALMS[realm] if realm is not None else "?"}   tide {ses.phase:.3f} ({TIDE.name(ses.phase)})',
                 f'chunks  {len(ses.world.chunks)} loaded, {st.get("drawn", 0)} drawn, jobs {ses.world.busy()}',
                 f'gen {avg(ses.world.timings["gen"]):.1f} ms   mesh {avg(ses.world.timings["mesh"]):.1f} ms   lights {st.get("lights", 0)}',
                 f'living cells {len(ses.sim.active)}   seed {ses.seed}']
        y = h - 110 * g.s
        for ln in lines:
            tw = g.text_width(ln, 9) + 16 * g.s
            g.rect(10 * g.s, y - 6 * g.s, tw, 22 * g.s, (0.15, 0.1, 0.25, 0.55), 8 * g.s)
            g.text(ln, 18 * g.s, y + 5 * g.s, 9, (1, 1, 1, 1), 'left', 'center')
            y -= 25 * g.s

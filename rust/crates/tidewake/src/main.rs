//! Tidewake 2.1. Fly a generated v6 sky: hex islands, fog, near and far meshes.

mod figure;
mod gpu;
mod mesh;
mod music;
mod text;

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use glam::{Mat4, Vec3};
use tidewake_core::chunk::{self, Chunk};
use tidewake_core::columns::Generator;
use tidewake_core::config::{CHUNK, FOV_DEG, LAYER, REACH, VERSION};
use tidewake_core::hex::{center, cell_at, chunk_of};
use tidewake_core::lesson;
use tidewake_core::mobs::Mob;
use tidewake_core::mine;
use tidewake_core::player::{raycast, Cells, Player};
use tidewake_core::glimmer::Glimmer;
use tidewake_core::save::{self, SkySave};
use tidewake_core::stations::{Chest, Kiln};
use tidewake_core::tide;
use tidewake_core::farm;
use tidewake_core::fish;
use tidewake_core::path;
use tidewake_core::settings::Settings;
use winit::application::ApplicationHandler;
use winit::dpi::LogicalSize;
use winit::event::{DeviceEvent, ElementState, MouseButton, WindowEvent};
use winit::event_loop::{ActiveEventLoop, EventLoop};
use winit::keyboard::{KeyCode, PhysicalKey};
use winit::window::{CursorGrabMode, Window, WindowId};

use gpu::{FrameUni, Gpu, GpuMesh};
use text::{Button, Fonts, Writer};
const VIEW: i32 = 5;
const LOD_AT: i32 = 3;
const GEN_PER_FRAME: usize = 2;
const UPLOAD_PER_FRAME: usize = 3;

struct Keys {
    w: bool,
    a: bool,
    s: bool,
    d: bool,
    up: bool,
    down: bool,
    fast: bool,
    mine: bool,
    place: bool,
}

struct Cam {
    x: f64,
    y: f64,
    z: f64,
    yaw: f32,
    pitch: f32,
}

struct Slot {
    cpu: Chunk,
    gpu: Option<GpuMesh>,
    lod: bool,
    dirty: bool,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Screen {
    Title,
    Skies,
    NewSky,
    Settings,
    Loading,
    Play,
    Pause,
}

struct Game {
    gen: Generator,
    cam: Cam,
    keys: Keys,
    grabbed: bool,
    chunks: HashMap<(i32, i32), Slot>,
    last: Instant,
    fps_t: f32,
    fps_n: u32,
    shown_fps: f32,
    gen_ms: f32,
    screen: Screen,
    player: Player,
    tutorial: bool,
    fonts: Fonts,
    mouse: [f32; 2],
    clicked: bool,
    seed_text: String,
    load_err: Option<String>,
    quit: bool,
    jump_edge: bool,
    /// 0 first person, 1 behind, 2 in front. Starts behind so the wanderer is in view.
    cam_view: u8,
    time: f32,
    figure_gpu: Option<GpuMesh>,
    save: SkySave,
    spawn: (f64, f64, f64),
    listed: Vec<String>,
    music: Option<music::Music>,
    mobs: Vec<Mob>,
    mobs_ready: bool,
    cloud_gpu: Option<GpuMesh>,
    mob_gpu: Option<GpuMesh>,
    glimmer: Glimmer,
    motes: Vec<(f64, f64, f64)>,
    mining: Option<((i64, i64, i32), f32)>,
    panel: Option<Panel>,
    settings: Settings,
    slider: usize,
    cast: Option<fish::Cast>,
    command: Option<String>,
    journal: bool,
    crops: Vec<(i64, i64, i32, f32)>,
}

#[derive(Clone, Copy)]
enum Panel {
    Kiln(usize),
    Chest(usize),
}

struct App {
    window: Option<Arc<Window>>,
    gpu: Option<Gpu>,
    game: Option<Game>,
    frames: u32,
    frame_limit: Option<u32>,
}

impl App {
    fn new() -> Self {
        let frame_limit = std::env::var("TIDEWAKE_FRAMES").ok().and_then(|s| s.parse().ok());
        Self { window: None, gpu: None, game: None, frames: 0, frame_limit }
    }
}

impl Cells for Game {
    fn get(&self, q: i64, r: i64, y: i32) -> u8 {
        let (cq, cr) = chunk_of(q, r);
        let lq = q.rem_euclid(CHUNK as i64) as i32;
        let lr = r.rem_euclid(CHUNK as i64) as i32;
        self.chunks.get(&(cq, cr)).map(|s| s.cpu.get(lq, y, lr)).unwrap_or(0)
    }

    fn meta(&self, q: i64, r: i64, y: i32) -> u8 {
        let (cq, cr) = chunk_of(q, r);
        let lq = q.rem_euclid(CHUNK as i64) as i32;
        let lr = r.rem_euclid(CHUNK as i64) as i32;
        self.chunks.get(&(cq, cr)).map(|s| s.cpu.get_meta(lq, y, lr)).unwrap_or(0)
    }
}

impl Game {
    fn boot() -> Self {
        let mut game = Self {
            gen: Generator::new(7, Settings::default()),
            cam: Cam { x: 0.0, y: 40.0, z: 0.0, yaw: 0.4, pitch: 0.0 },
            keys: Keys { w: false, a: false, s: false, d: false, up: false, down: false, fast: false, mine: false, place: false },
            grabbed: false,
            chunks: HashMap::new(),
            last: Instant::now(),
            fps_t: 0.0,
            fps_n: 0,
            shown_fps: 0.0,
            gen_ms: 0.0,
            screen: Screen::Title,
            player: Player::at_feet(0.0, 40.0, 0.0),
            tutorial: false,
            fonts: Fonts::load(),
            mouse: [0.0, 0.0],
            clicked: false,
            seed_text: String::new(),
            load_err: None,
            quit: false,
            jump_edge: false,
            cam_view: 1,
            time: 0.0,
            figure_gpu: None,
            save: SkySave::fresh("unsaved", 7, false, 0.0, 40.0, 0.0),
            spawn: (0.0, 40.0, 0.0),
            listed: Vec::new(),
            music: None,
            mobs: Vec::new(),
            mobs_ready: false,
            cloud_gpu: None,
            mob_gpu: None,
            glimmer: Glimmer::default(),
            motes: Vec::new(),
            mining: None,
            panel: None,
            settings: Settings::default(),
            slider: 0,
            cast: None,
            command: None,
            journal: false,
            crops: Vec::new(),
        };
        match std::env::var("TIDEWAKE_PLAY").ok().as_deref() {
            Some("tutorial") => game.begin(true, 1),
            Some("sky") => game.begin(false, 7),
            _ => {}
        }
        game
    }

    fn begin(&mut self, tutorial: bool, seed: i64) {
        self.tutorial = tutorial;
        self.chunks.clear();
        self.load_err = None;
        self.screen = Screen::Loading;
        if tutorial {
            let (x, y, z) = lesson::spawn();
            self.player = Player::at_feet(x, y, z);
            log::info!("lesson island at {x:.1}, {y:.1}, {z:.1}");
        } else {
            self.gen = Generator::new(seed, self.settings);
            let (x, _y, z) = chunk::find_spawn(&self.gen);
            let (q, r) = cell_at(x, z);
            let col = self.gen.sample(q, r);
            let feet = (col.top as f64 + 1.0) * LAYER + 0.02;
            self.player = Player::at_feet(x, feet, z);
            log::info!("new sky seed {seed} at {x:.1}, feet {feet:.1}, {z:.1}");
        }
        self.player.yaw = 0.4;
        self.player.pitch = -0.15;
        self.spawn = (self.player.x, self.player.y, self.player.z);
        let name = if tutorial { "the-lesson".into() } else { format!("sky-{seed}") };
        self.save = SkySave::fresh(name, seed, tutorial, self.player.x, self.player.y, self.player.z);
        if self.music.is_none() {
            self.music = music::Music::start();
        }
        self.sync_cam();
    }

    fn store_player_in_save(&mut self) {
        self.save.x = self.player.x;
        self.save.y = self.player.y;
        self.save.z = self.player.z;
        self.save.yaw = self.player.yaw;
        self.save.pitch = self.player.pitch;
    }

    fn apply_save_to_player(&mut self) {
        self.player.x = self.save.x;
        self.player.y = self.save.y;
        self.player.z = self.save.z;
        self.player.yaw = self.save.yaw;
        self.player.pitch = self.save.pitch;
        self.sync_cam();
    }

    fn load_named(&mut self, name: &str) {
        let Ok(saved) = save::read(&save::skies_dir(), name) else { return };
        self.begin(saved.tutorial, saved.seed);
        self.save = saved;
        self.apply_save_to_player();
    }

    fn write_save(&mut self) {
        if self.save.tutorial {
            return;
        }
        self.store_player_in_save();
        if let Err(err) = save::write(&save::skies_dir(), &self.save) {
            log::warn!("could not save: {err}");
        }
    }

    fn sync_cam(&mut self) {
        let (x, y, z) = self.player.eye_pos();
        self.cam.x = x;
        self.cam.y = y;
        self.cam.z = z;
        self.cam.yaw = self.player.yaw;
        self.cam.pitch = self.player.pitch;
    }

    fn step(&mut self, gpu: &Gpu, dt: f32) {
        if self.screen != Screen::Play && self.screen != Screen::Loading {
            return;
        }
        self.time += dt;
        if self.screen == Screen::Play && self.load_err.is_none() {
            let fwd = (self.keys.w as i32 as f32) - (self.keys.s as i32 as f32);
            let strafe = (self.keys.d as i32 as f32) - (self.keys.a as i32 as f32);
            let jump_pressed = self.jump_edge;
            self.jump_edge = false;
            let mut player = self.player.clone();
            player.update(self, dt, fwd, strafe, self.keys.up, jump_pressed, self.keys.down, self.keys.fast);
            self.player = player;
            if !self.player.drifting {
                let moving = self.player.vx.abs() + self.player.vz.abs() > 0.2;
                let moving = moving || self.keys.w || self.keys.a || self.keys.s || self.keys.d;
                self.save.tick(dt, moving, self.keys.fast);
                if self.save.health <= 0.0 {
                    self.player.x = self.spawn.0;
                    self.player.y = self.spawn.1;
                    self.player.z = self.spawn.2;
                    self.player.vx = 0.0;
                    self.player.vy = 0.0;
                    self.player.vz = 0.0;
                    self.save.health = 20.0;
                    self.save.food = 12.0;
                }
                if self.player.landed > 0.0 {
                    self.save.health = (self.save.health - self.player.landed).max(1.0);
                    self.player.landed = 0.0;
                }
                let cloud = tidewake_core::config::CLOUD_SEA as f64 * LAYER - 2.0;
                if self.player.y < cloud && !self.player.drifting {
                    self.player.x = self.spawn.0;
                    self.player.y = self.spawn.1;
                    self.player.z = self.spawn.2;
                    self.player.vx = 0.0;
                    self.player.vy = 0.0;
                    self.player.vz = 0.0;
                    if !self.save.dreamer {
                        self.save.health = (self.save.health - 3.0).max(1.0);
                    }
                }
            }
            self.save.stats.play += dt;
            self.grow_crops(dt);
            self.tick_cast(dt);
            let _ = path::poll(&mut self.save.stats);
            self.sync_cam();
            let dusk = ((self.time / 720.0) * std::f32::consts::TAU).sin().mul_add(0.5, 0.5);
            for mob in &mut self.mobs {
                let py = self.player.y;
                mob.update(dt, self.player.x, self.player.z, dusk);
                mob.y = py;
            }
        }
        if self.screen == Screen::Play && !self.mobs_ready {
            self.mobs_ready = true;
            let (x, y, z) = (self.player.x, self.player.y, self.player.z);
            for (i, kind) in ["woolhop", "pebblebeak", "mossback", "islekit", "woolhop", "fairy"].into_iter().enumerate() {
                let ang = i as f64 * 1.05;
                self.mobs.push(Mob::new(kind, x + ang.cos() * 8.0, y, z + ang.sin() * 8.0, i as f32));
            }
            self.mobs.push(Mob::new("gloomling", x + 14.0, y, z, 0.0));
            self.mobs.push(Mob::new("skyjelly", x, y + 6.0, z + 10.0, 1.0));
            self.motes.clear();
            for i in 0..10 {
                let ang = i as f64 * 0.9;
                let dist = 4.0 + (i % 4) as f64 * 2.0;
                self.motes.push((x + ang.cos() * dist, y + 1.2, z + ang.sin() * dist));
            }
        }
        if self.screen == Screen::Play {
            let mut smelted = 0;
            for kiln in &mut self.save.kilns {
                if kiln.tick(dt) {
                    smelted += 1;
                }
            }
            self.save.stats.smelted += smelted;
        }
        if self.screen == Screen::Play && self.keys.mine {
            self.dig(dt);
        } else {
            self.mining = None;
        }
        if self.screen == Screen::Play && self.keys.place {
            self.keys.place = false;
            self.place_block();
        }
        if self.screen == Screen::Play {
            let (px, py, pz) = (self.player.x, self.player.y + 1.0, self.player.z);
            self.motes.retain(|(x, y, z)| {
                let d = ((x - px).powi(2) + (y - py).powi(2) + (z - pz).powi(2)).sqrt();
                if d < 1.4 {
                    self.glimmer.catch_mote();
                    self.save.stats.motes += 1;
                    false
                } else {
                    true
                }
            });
        }

        let (cq, cr) = chunk_of_cam(self.cam.x, self.cam.z);
        let mut want = Vec::new();
        for a in (cq - VIEW)..=(cq + VIEW) {
            for b in (cr - VIEW)..=(cr + VIEW) {
                if (a - cq).abs().max((b - cr).abs()) <= VIEW {
                    want.push((a, b));
                }
            }
        }
        want.sort_by_key(|(a, b)| (a - cq).abs().max((b - cr).abs()));
        let mut made = 0;
        for key in &want {
            if self.chunks.contains_key(key) {
                continue;
            }
            if made >= GEN_PER_FRAME {
                break;
            }
            let t = Instant::now();
            let cpu = self.make_chunk(key.0, key.1);
            self.gen_ms = t.elapsed().as_secs_f64() as f32 * 1000.0;
            if self.load_err.is_some() {
                break;
            }
            let lod = (key.0 - cq).abs().max((key.1 - cr).abs()) >= LOD_AT;
            self.chunks.insert(*key, Slot { cpu, gpu: None, lod, dirty: true });
            for (dq, dr) in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)] {
                if let Some(n) = self.chunks.get_mut(&(key.0 + dq, key.1 + dr)) {
                    n.dirty = true;
                }
            }
            made += 1;
        }
        // Drop chunks that have scrolled away.
        self.chunks.retain(|k, _| (k.0 - cq).abs().max((k.1 - cr).abs()) <= VIEW + 1);

        let mut uploaded = 0;
        let keys: Vec<(i32, i32)> = self.chunks.iter().filter(|(_, s)| s.dirty).map(|(k, _)| *k).collect();
        for key in keys {
            if uploaded >= UPLOAD_PER_FRAME {
                break;
            }
            let lod = (key.0 - cq).abs().max((key.1 - cr).abs()) >= LOD_AT;
            let owned = self.chunks.get(&key).unwrap().cpu.clone();
            let nb = |lq: i32, y: i32, lr: i32| -> u8 {
                let (ncq, nlq) = shift(key.0, lq);
                let (ncr, nlr) = shift(key.1, lr);
                self.chunks.get(&(ncq, ncr)).map(|s| s.cpu.get(nlq, y, nlr)).unwrap_or(0)
            };
            let cpu_mesh = mesh::build(&owned, &nb, lod);
            let gpu_mesh = if cpu_mesh.idx.is_empty() {
                None
            } else {
                Some(gpu.upload(&cpu_mesh.verts, &cpu_mesh.idx))
            };
            if let Some(slot) = self.chunks.get_mut(&key) {
                slot.gpu = gpu_mesh;
                slot.lod = lod;
                slot.dirty = false;
            }
            uploaded += 1;
        }

        self.fps_t += dt;
        self.fps_n += 1;
        if self.fps_t >= 0.5 {
            self.shown_fps = self.fps_n as f32 / self.fps_t;
            self.fps_t = 0.0;
            self.fps_n = 0;
        }
        if self.screen == Screen::Loading && self.load_err.is_none() {
            let ready = self.chunks.keys().filter(|(a, b)| (a - cq).abs().max((b - cr).abs()) <= 1).count();
            if ready >= 9 {
                self.screen = Screen::Play;
                log::info!("sky ready, walking");
            }
        }
    }

    fn make_chunk(&mut self, cq: i32, cr: i32) -> Chunk {
        let mut chunk = if self.tutorial {
            lesson::generate(cq, cr)
        } else {
            let gen = &self.gen;
            match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| chunk::generate(gen, cq, cr))) {
                Ok(chunk) => chunk,
                Err(_) => {
                    self.load_err = Some("This sky failed to grow. Esc returns to the title.".into());
                    Chunk::blank(cq, cr)
                }
            }
        };
        self.save.apply_edits(&mut chunk);
        chunk
    }

    fn reach(&self) -> f64 {
        REACH + if self.glimmer.has("reach") { 1.5 } else { 0.0 }
    }

    fn aim(&self) -> ((f64, f64, f64), (f64, f64, f64)) {
        let (ex, ey, ez) = self.player.eye_pos();
        let (fx, fy, fz) = look(self.player.yaw, self.player.pitch);
        ((ex, ey, ez), (fx as f64, fy as f64, fz as f64))
    }

    fn set_cell(&mut self, q: i64, r: i64, y: i32, mat: u8, meta: u8) {
        let (cq, cr) = chunk_of(q, r);
        let lq = q.rem_euclid(CHUNK as i64) as i32;
        let lr = r.rem_euclid(CHUNK as i64) as i32;
        if let Some(slot) = self.chunks.get_mut(&(cq, cr)) {
            slot.cpu.set(lq, y, lr, mat);
            slot.cpu.set_meta(lq, y, lr, meta);
            slot.dirty = true;
        }
        let edge = [(lq == 0, -1, 0), (lq == CHUNK - 1, 1, 0), (lr == 0, 0, -1), (lr == CHUNK - 1, 0, 1)];
        for (on, dq, dr) in edge {
            if on {
                if let Some(n) = self.chunks.get_mut(&(cq + dq, cr + dr)) {
                    n.dirty = true;
                }
            }
        }
        self.save.record_edit(q, r, y, mat, meta);
    }

    fn dig(&mut self, dt: f32) {
        let ((ex, ey, ez), (dx, dy, dz)) = self.aim();
        let (hit, _) = raycast(self, ex, ey, ez, dx, dy, dz, self.reach(), true);
        let Some((q, r, y)) = hit else {
            self.mining = None;
            return;
        };
        let mat = self.get(q, r, y);
        if mat == 0 || mine::unbreakable(mat) {
            self.mining = None;
            return;
        }
        let held = self.save.hotbar.get(self.save.selected).map(|s| if s.count > 0 { s.id } else { 0 }).unwrap_or(0);
        let (secs, drops) = mine::mine_time(mat, held);
        let prog = match self.mining {
            Some((cell, p)) if cell == (q, r, y) => p,
            _ => 0.0,
        } + dt / secs;
        if prog < 1.0 {
            self.mining = Some(((q, r, y), prog));
            return;
        }
        let meta = self.meta(q, r, y);
        self.set_cell(q, r, y, 0, 0);
        if farm::is_crop(mat) {
            for (id, n) in farm::harvest(mat, meta) {
                self.save.give(id, n);
            }
            if meta >= farm::STAGES - 1 {
                self.save.stats.farmed += 1;
            }
        } else if drops {
            let roll = ((q.wrapping_mul(13) ^ r.wrapping_mul(7) ^ y as i64) as u32 % 1000) as f32 / 1000.0;
            for (id, n) in mine::drops_for(mat, roll) {
                if id != 0 {
                    self.save.give(id, n);
                }
            }
        }
        self.save.stats.mined += 1;
        self.mining = None;
    }

    fn place_block(&mut self) {
        let ((ex, ey, ez), (dx, dy, dz)) = self.aim();
        let (hit, prev) = raycast(self, ex, ey, ez, dx, dy, dz, self.reach(), true);
        if self.cast.is_some() {
            self.reel();
            return;
        }
        if self.try_tool() {
            return;
        }
        if !self.keys.down {
            if let Some((q, r, y)) = hit {
                let mat = self.get(q, r, y);
                if self.use_block(q, r, y, mat) {
                    return;
                }
            }
        }
        let Some((q, r, y)) = prev else { return };
        if y < 1 || y >= tidewake_core::config::LAYERS - 1 {
            return;
        }
        let cur = self.get(q, r, y);
        let petals = tidewake_core::materials::id_named("petals").unwrap_or(0);
        if cur != 0 && cur != tidewake_core::materials::id::WATER && cur != petals {
            return;
        }
        let sel = self.save.selected;
        let Some(slot) = self.save.hotbar.get(sel) else { return };
        if slot.count == 0 || slot.id == 0 || slot.id >= 256 {
            return;
        }
        let mat = slot.id as u8;
        let feet = (self.player.y / LAYER).floor() as i32;
        let head = ((self.player.y + self.player.eye) / LAYER).floor() as i32;
        if (feet..=head).contains(&y) && self.player.columns(self.player.x, self.player.z).contains(&(q, r)) && tidewake_core::materials::is_solid(mat)
        {
            return;
        }
        if mat == tidewake_core::materials::id::DOOR {
            let above = self.get(q, r, y + 1);
            if above != 0 && above != tidewake_core::materials::id::WATER {
                return;
            }
            self.set_cell(q, r, y, mat, 0);
            self.set_cell(q, r, y + 1, mat, 16);
        } else {
            self.set_cell(q, r, y, mat, 0);
        }
        let slot = &mut self.save.hotbar[sel];
        slot.count -= 1;
        if slot.count == 0 {
            slot.id = 0;
        }
        self.save.stats.placed += 1;
        if mat == tidewake_core::materials::id::DOOR {
            self.save.stats.doors += 1;
        }
        if mat == tidewake_core::materials::id::TINKER_BENCH {
            self.save.stats.tinker += 1;
        }
        self.stir_spire(q, r, y);
    }

    fn held_id(&self) -> u16 {
        self.save.hotbar.get(self.save.selected).map(|s| if s.count > 0 { s.id } else { 0 }).unwrap_or(0)
    }

    fn try_tool(&mut self) -> bool {
        let held = self.held_id();
        if held == fish::ROD {
            return self.cast_line();
        }
        if held == farm::HOE {
            return self.till();
        }
        if farm::plant_of(held).is_some() {
            return self.sow(held);
        }
        false
    }

    fn cast_line(&mut self) -> bool {
        if self.cast.is_some() {
            return false;
        }
        let ((ex, ey, ez), (dx, dy, dz)) = self.aim();
        let (hit, _) = raycast(self, ex, ey, ez, dx, dy, dz, self.reach(), false);
        let Some((q, r, y)) = hit else { return false };
        if self.get(q, r, y) != tidewake_core::materials::id::WATER {
            return false;
        }
        self.cast = Some(fish::Cast::start(((q as u32).wrapping_mul(17) ^ (r as u32)) as f32 / 1000.0 % 1.0));
        true
    }

    fn till(&mut self) -> bool {
        let ((ex, ey, ez), (dx, dy, dz)) = self.aim();
        let (hit, _) = raycast(self, ex, ey, ez, dx, dy, dz, self.reach(), true);
        let Some((q, r, y)) = hit else { return false };
        if !farm::tillable(self.get(q, r, y)) {
            return false;
        }
        self.set_cell(q, r, y, tidewake_core::materials::id::FARMLAND, 0);
        self.save.stats.tilled += 1;
        true
    }

    fn sow(&mut self, seed: u16) -> bool {
        let ((ex, ey, ez), (dx, dy, dz)) = self.aim();
        let (hit, _) = raycast(self, ex, ey, ez, dx, dy, dz, self.reach(), true);
        let Some((q, r, y)) = hit else { return false };
        if self.get(q, r, y) != tidewake_core::materials::id::FARMLAND {
            return false;
        }
        if self.get(q, r, y + 1) != 0 {
            return false;
        }
        let Some(crop) = farm::plant_of(seed) else { return false };
        self.set_cell(q, r, y + 1, crop, 0);
        self.crops.push((q, r, y + 1, 0.0));
        let sel = self.save.selected;
        let slot = &mut self.save.hotbar[sel];
        slot.count -= 1;
        if slot.count == 0 {
            slot.id = 0;
        }
        true
    }

    fn tick_cast(&mut self, dt: f32) {
        let Some(cast) = self.cast.as_mut() else { return };
        if cast.tick(dt) == Some(false) {
            self.cast = None;
        }
    }

    fn reel(&mut self) {
        let Some(cast) = self.cast else { return };
        if cast.t >= cast.wait && cast.t < cast.wait + cast.window {
            let dusk = tide::atmosphere(self.time).dusk > 0.45;
            let (id, n) = fish::catch_id(cast.t.fract(), dusk);
            self.save.give(id, n);
            self.save.stats.fished += 1;
        }
        self.cast = None;
    }

    fn grow_crops(&mut self, dt: f32) {
        let mut grown = Vec::new();
        for crop in &mut self.crops {
            crop.3 += dt;
            if crop.3 >= farm::grow_interval(false) {
                crop.3 = 0.0;
                grown.push((crop.0, crop.1, crop.2));
            }
        }
        for (q, r, y) in grown {
            let mat = self.get(q, r, y);
            if !farm::is_crop(mat) {
                continue;
            }
            let meta = self.meta(q, r, y);
            if meta + 1 < farm::STAGES {
                self.set_cell(q, r, y, mat, meta + 1);
            }
        }
        let keep: Vec<bool> = self.crops.iter().map(|(q, r, y, _)| farm::is_crop(self.get(*q, *r, *y))).collect();
        let mut i = 0;
        self.crops.retain(|_| {
            let ok = keep[i];
            i += 1;
            ok
        });
    }

    fn stir_spire(&mut self, q: i64, r: i64, y: i32) {
        use tidewake_core::hex::DIRS;
        use tidewake_core::materials::id;
        for (dq, dr) in DIRS {
            let (sq, sr) = (q + dq as i64, r + dr as i64);
            if self.get(sq, sr, y) != id::DORMANT_SPIRE {
                continue;
            }
            let full = DIRS.iter().all(|(aq, ar)| self.get(sq + *aq as i64, sr + *ar as i64, y) != 0);
            if !full {
                continue;
            }
            let mut yy = y;
            while self.get(sq, sr, yy) == id::DORMANT_SPIRE {
                self.set_cell(sq, sr, yy, id::AWAKE_SPIRE, 0);
                yy += 1;
            }
            self.save.give(263, 6);
            self.save.give(260, 1);
            self.save.stats.spires += 1;
            match self.save.stats.spires {
                1 => self.player.can_glide = true,
                2 => self.player.can_updraft = true,
                _ => {}
            }
        }
    }

    fn use_block(&mut self, q: i64, r: i64, y: i32, mat: u8) -> bool {
        use tidewake_core::materials::id;
        if mat == id::DOOR {
            let mt = self.meta(q, r, y);
            let opened = mt ^ 8;
            self.set_cell(q, r, y, mat, opened);
            let other_y = if mt & 16 != 0 { y - 1 } else { y + 1 };
            if self.get(q, r, other_y) == id::DOOR {
                let omt = self.meta(q, r, other_y);
                self.set_cell(q, r, other_y, id::DOOR, (omt & !8) | (opened & 8) | (omt & 16));
            }
            return true;
        }
        if mat == id::BEDROLL {
            let (x, z) = center(q, r);
            self.spawn = (x, (y as f64 + 1.0) * LAYER + 0.01, z);
            let dusk = tide::atmosphere(self.time).dusk;
            if dusk > 0.4 {
                self.time = 720.0 * self.time.div_euclid(720.0);
            }
            return true;
        }
        if mat == id::KILN {
            let idx = if let Some(i) = self.save.kilns.iter().position(|k| k.q == q && k.r == r && k.y == y) {
                i
            } else {
                self.save.kilns.push(Kiln::at(q, r, y));
                self.save.kilns.len() - 1
            };
            self.panel = Some(Panel::Kiln(idx));
            return true;
        }
        if mat == id::CHEST {
            let idx = if let Some(i) = self.save.chests.iter().position(|c| c.q == q && c.r == r && c.y == y) {
                i
            } else {
                self.save.chests.push(Chest::at(q, r, y));
                self.save.chests.len() - 1
            };
            self.panel = Some(Panel::Chest(idx));
            return true;
        }
        if mat == id::WAYSTONE {
            if self.glimmer.attune() {
                self.save.stats.waystones += 1;
            }
            return true;
        }
        false
    }

    fn deposit_held(&mut self) {
        let sel = self.save.selected;
        let Some(slot) = self.save.hotbar.get(sel).cloned() else { return };
        if slot.count == 0 {
            return;
        }
        match self.panel {
            Some(Panel::Kiln(i)) => {
                let kiln = &mut self.save.kilns[i];
                let dest = if tidewake_core::craft::fuel_of(slot.id).is_some() && kiln.input.count > 0 {
                    &mut kiln.fuel
                } else {
                    &mut kiln.input
                };
                if dest.count == 0 {
                    *dest = slot.clone();
                    self.save.hotbar[sel] = tidewake_core::save::Slot { id: 0, count: 0 };
                } else if dest.id == slot.id {
                    dest.count = dest.count.saturating_add(slot.count);
                    self.save.hotbar[sel] = tidewake_core::save::Slot { id: 0, count: 0 };
                }
            }
            Some(Panel::Chest(i)) => {
                let left = self.save.chests[i].deposit(slot.id, slot.count);
                if left == 0 {
                    self.save.hotbar[sel] = tidewake_core::save::Slot { id: 0, count: 0 };
                } else {
                    self.save.hotbar[sel].count = left;
                }
            }
            None => {}
        }
    }

    fn run_command(&mut self) {
        let line = self.command.take().unwrap_or_default();
        let mut parts = line.split_whitespace();
        match parts.next() {
            Some("fly") => self.player.drifting = !self.player.drifting,
            Some("dreamer") => {
                self.save.dreamer = !self.save.dreamer;
                self.player.drifting = self.save.dreamer;
                self.player.can_glide = true;
                self.player.can_updraft = true;
            }
            Some("tide") => self.time += 180.0,
            Some("give") => {
                let name = parts.next().unwrap_or("").replace('_', " ");
                let n: u16 = parts.next().and_then(|s| s.parse().ok()).unwrap_or(1);
                for id in 1..400u16 {
                    if tidewake_core::craft::name_of(id).eq_ignore_ascii_case(&name) {
                        self.save.give(id, n);
                        break;
                    }
                }
            }
            _ => {}
        }
    }

    fn panel_line(&self) -> Option<String> {
        match self.panel? {
            Panel::Kiln(i) => {
                let k = self.save.kilns.get(i)?;
                Some(format!(
                    "Kiln   in {} x{}   fuel {} x{}   out {} x{}   burn {:.0}s",
                    tidewake_core::craft::name_of(k.input.id),
                    k.input.count,
                    tidewake_core::craft::name_of(k.fuel.id),
                    k.fuel.count,
                    tidewake_core::craft::name_of(k.output.id),
                    k.output.count,
                    k.burn.max(0.0)
                ))
            }
            Panel::Chest(i) => {
                let chest = self.save.chests.get(i)?;
                let n: u16 = chest.slots.iter().map(|s| s.count).sum();
                let first = chest.slots.iter().find(|s| s.count > 0);
                let name = first.map(|s| tidewake_core::craft::name_of(s.id)).unwrap_or_else(|| "empty".into());
                Some(format!("Chest   {n} items   next {name}   F store   V take"))
            }
        }
    }

    fn withdraw_panel(&mut self) {
        let taken = match self.panel {
            Some(Panel::Kiln(i)) => {
                let out = self.save.kilns[i].output.clone();
                if out.count > 0 {
                    self.save.kilns[i].output = tidewake_core::save::Slot { id: 0, count: 0 };
                    Some(out)
                } else {
                    None
                }
            }
            Some(Panel::Chest(i)) => self.save.chests[i].withdraw(),
            None => None,
        };
        if let Some(slot) = taken {
            self.save.give(slot.id, slot.count);
        }
    }

    fn ui(&mut self, fw: f32, fh: f32) -> Vec<text::UiVert> {
        let mut verts = Vec::new();
        let clicked = self.clicked;
        let (mx, my) = (self.mouse[0], self.mouse[1]);
        let ink = [0.96, 0.94, 0.90, 1.0];
        let muted = [0.82, 0.78, 0.90, 1.0];
        let paper = [0.95, 0.92, 0.86, 1.0];
        let accent = [0.36, 0.28, 0.55, 1.0];
        let panel = self.panel_line();
        {
            let mut ui = Writer { fonts: &mut self.fonts, verts: &mut verts, w: fw, h: fh };
            let bw = 280.0;
            let bh = 46.0;
            let bx = (fw - bw) * 0.5;
            match self.screen {
                Screen::Title => {
                    ui.text(0, "Tidewake", fw * 0.5, fh * 0.28, 72.0, [1.0, 0.97, 0.90, 1.0], true);
                    ui.text(1, "a sky of floating hexagon islands", fw * 0.5, fh * 0.36, 20.0, muted, true);
                    let labels = ["Learn to play", "My Skies", "Settings"];
                    for (i, label) in labels.iter().enumerate() {
                        let y = fh * 0.46 + i as f32 * 58.0;
                        let b = Button { x: bx, y, w: bw, h: bh };
                        ui.rect(b.x, b.y, b.w, b.h, if i == 0 { [0.55, 0.42, 0.22, 1.0] } else { accent });
                        ui.text(1, label, fw * 0.5, y + 32.0, 22.0, paper, true);
                        if clicked && b.hit(mx, my) {
                            // recorded below; the borrow of ui ends first
                            let _ = i;
                        }
                    }
                    ui.text(1, "Tidewake 2.1", 24.0, fh - 28.0, 16.0, muted, false);
                }
                Screen::Skies => {
                    ui.rect(fw * 0.2, fh * 0.16, fw * 0.6, fh * 0.68, [0.12, 0.09, 0.18, 0.92]);
                    ui.text(0, "My Skies", fw * 0.5, fh * 0.24, 40.0, ink, true);
                    if self.listed.is_empty() {
                        ui.text(1, "No skies yet. The lesson has its own button.", fw * 0.5, fh * 0.34, 18.0, muted, true);
                    } else {
                        ui.text(1, "Click a sky to return to it.", fw * 0.5, fh * 0.34, 18.0, muted, true);
                        for (i, name) in self.listed.iter().take(6).enumerate() {
                            let y = fh * 0.40 + i as f32 * 32.0;
                            ui.text(1, name, fw * 0.5, y, 18.0, ink, true);
                        }
                    }
                    ui.rect(bx, fh * 0.48, bw, bh, accent);
                    ui.text(1, "New Sky", fw * 0.5, fh * 0.48 + 32.0, 22.0, paper, true);
                    ui.rect(bx, fh * 0.60, bw, bh, accent);
                    ui.text(1, "Back", fw * 0.5, fh * 0.60 + 32.0, 22.0, paper, true);
                }
                Screen::NewSky => {
                    ui.rect(fw * 0.2, fh * 0.18, fw * 0.6, fh * 0.6, [0.12, 0.09, 0.18, 0.92]);
                    ui.text(0, "New Sky", fw * 0.5, fh * 0.28, 40.0, ink, true);
                    ui.text(1, "Type a seed. Arrows change the sky sliders.", fw * 0.5, fh * 0.34, 16.0, muted, true);
                    let key = tidewake_core::settings::KEYS[self.slider % 12];
                    ui.text(1, &format!("{key} {}", self.settings.get(key)), fw * 0.5, fh * 0.40, 16.0, ink, true);
                    let shown = if self.seed_text.is_empty() { "seed".to_string() } else { self.seed_text.clone() };
                    ui.rect(bx, fh * 0.44, bw, bh, [0.08, 0.06, 0.12, 1.0]);
                    ui.text(1, &shown, fw * 0.5, fh * 0.44 + 32.0, 22.0, ink, true);
                    ui.rect(bx, fh * 0.55, bw, bh, [0.55, 0.42, 0.22, 1.0]);
                    ui.text(1, "Dream", fw * 0.5, fh * 0.55 + 32.0, 22.0, paper, true);
                    ui.rect(bx, fh * 0.66, bw, bh, accent);
                    ui.text(1, "Back", fw * 0.5, fh * 0.66 + 32.0, 22.0, paper, true);
                }
                Screen::Settings => {
                    ui.rect(fw * 0.2, fh * 0.18, fw * 0.6, fh * 0.64, [0.12, 0.09, 0.18, 0.92]);
                    ui.text(0, "Settings", fw * 0.5, fh * 0.24, 40.0, ink, true);
                    let key = tidewake_core::settings::KEYS[self.slider % 12];
                    ui.text(1, &format!("{key}   {}", self.settings.get(key)), fw * 0.5, fh * 0.36, 22.0, ink, true);
                    ui.text(1, "Up and down choose a slider. Left and right change it.", fw * 0.5, fh * 0.44, 16.0, muted, true);
                    ui.rect(bx, fh * 0.62, bw, bh, accent);
                    ui.text(1, "Back", fw * 0.5, fh * 0.62 + 32.0, 22.0, paper, true);
                }
                Screen::Pause => {
                    ui.rect(fw * 0.3, fh * 0.28, fw * 0.4, fh * 0.4, [0.12, 0.09, 0.18, 0.94]);
                    ui.text(0, "Paused", fw * 0.5, fh * 0.36, 40.0, ink, true);
                    ui.rect(bx, fh * 0.46, bw, bh, [0.55, 0.42, 0.22, 1.0]);
                    ui.text(1, "Resume", fw * 0.5, fh * 0.46 + 32.0, 22.0, paper, true);
                    ui.rect(bx, fh * 0.56, bw, bh, accent);
                    ui.text(1, "Save and leave", fw * 0.5, fh * 0.56 + 32.0, 22.0, paper, true);
                }
                Screen::Loading => {
                    let msg = self.load_err.clone().unwrap_or_else(|| {
                        format!("Dreaming…  {} chunks", self.chunks.len())
                    });
                    ui.text(0, if self.tutorial { "The Lesson" } else { "New Sky" }, fw * 0.5, fh * 0.40, 42.0, ink, true);
                    ui.text(1, &msg, fw * 0.5, fh * 0.50, 20.0, muted, true);
                    if self.load_err.is_some() {
                        ui.text(1, "Esc returns to the title", fw * 0.5, fh * 0.58, 16.0, muted, true);
                    }
                }
                Screen::Play => {
                    let (x, y, z) = self.player.eye_pos();
                    let line = format!(
                        "Tidewake {VERSION}   {:.0} fps   {:.0}, {:.0}, {:.0}   layer {:.0}   hp {:.0}   food {:.0}   {}{}",
                        self.shown_fps,
                        x,
                        y,
                        z,
                        y / LAYER,
                        self.save.health,
                        self.save.food,
                        self.save.selected_label(),
                        if self.player.drifting { "   flying" } else { "" }
                    );
                    let tide_name = tide::atmosphere(self.time).name;
                    let gift = self.glimmer.next_gift().unwrap_or("all gifts");
                    ui.text(
                        1,
                        &format!("Glimmer {}   {}   G buys {gift}   motes {}", self.glimmer.motes, tide_name, self.motes.len()),
                        16.0,
                        70.0,
                        14.0,
                        muted,
                        false,
                    );
                    ui.text(1, &line, 16.0, 28.0, 16.0, [1.0, 1.0, 1.0, 0.9], false);
                    ui.text(1, "R eat   C craft   E use   F store   V take   Shift crouch   Esc leave", 16.0, 50.0, 14.0, muted, false);
                    if let Some(line) = panel.as_deref() {
                        ui.text(1, line, 16.0, 92.0, 15.0, [1.0, 0.95, 0.75, 1.0], false);
                    }
                    if self.cast.is_some() {
                        let biting = self.cast.is_some_and(|c| c.t >= c.wait && c.t < c.wait + c.window);
                        ui.text(1, if biting { "The bobber dips — press E" } else { "The line is out" }, 16.0, 114.0, 15.0, ink, false);
                    }
                    if let Some(cmd) = &self.command {
                        ui.text(1, &format!("/{cmd}"), 16.0, fh - 40.0, 16.0, ink, false);
                    }
                    if self.journal {
                        for (i, line) in path::lines(&self.save.stats).iter().take(8).enumerate() {
                            ui.text(1, line, 16.0, 140.0 + i as f32 * 18.0, 13.0, muted, false);
                        }
                    }
                }
            }
        }
        if clicked {
            self.click_at(mx, my, fw, fh);
        }
        self.clicked = false;
        verts
    }

    fn click_at(&mut self, mx: f32, my: f32, fw: f32, fh: f32) {
        let bw = 280.0;
        let bh = 46.0;
        let bx = (fw - bw) * 0.5;
        let hit = |i: usize| {
            let y = fh * 0.46 + i as f32 * 58.0;
            Button { x: bx, y, w: bw, h: bh }.hit(mx, my)
        };
        match self.screen {
            Screen::Title => {
                if hit(0) { self.begin(true, 1); }
                else if hit(1) {
                    self.listed = save::list(&save::skies_dir());
                    self.screen = Screen::Skies;
                }
                else if hit(2) { self.screen = Screen::Settings; }
            }
            Screen::Skies => {
                let mut hit_sky = None;
                for (i, name) in self.listed.iter().take(6).enumerate() {
                    let y = fh * 0.38 + i as f32 * 32.0;
                    if (Button { x: bx, y, w: bw, h: 30.0 }).hit(mx, my) {
                        hit_sky = Some(name.clone());
                    }
                }
                let neu = Button { x: bx, y: fh * 0.62, w: bw, h: bh };
                let back = Button { x: bx, y: fh * 0.72, w: bw, h: bh };
                if let Some(name) = hit_sky {
                    self.load_named(&name);
                } else if neu.hit(mx, my) {
                    self.screen = Screen::NewSky;
                    self.seed_text.clear();
                } else if back.hit(mx, my) {
                    self.screen = Screen::Title;
                }
            }
            Screen::NewSky => {
                let dream = Button { x: bx, y: fh * 0.55, w: bw, h: bh };
                let back = Button { x: bx, y: fh * 0.66, w: bw, h: bh };
                if dream.hit(mx, my) { self.dream(); }
                else if back.hit(mx, my) { self.screen = Screen::Skies; }
            }
            Screen::Settings => {
                let back = Button { x: bx, y: fh * 0.62, w: bw, h: bh };
                if back.hit(mx, my) { self.screen = Screen::Title; }
            }
            Screen::Pause => {
                let resume = Button { x: bx, y: fh * 0.46, w: bw, h: bh };
                let leave = Button { x: bx, y: fh * 0.56, w: bw, h: bh };
                if resume.hit(mx, my) {
                    self.screen = Screen::Play;
                } else if leave.hit(mx, my) {
                    self.write_save();
                    self.screen = Screen::Title;
                    self.chunks.clear();
                }
            }
            _ => {}
        }
    }

    fn dream(&mut self) {
        let seed = if self.seed_text.trim().is_empty() {
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos() as i64)
                .unwrap_or(7)
        } else {
            self.seed_text.trim().parse::<i64>().unwrap_or_else(|_| {
                self.seed_text.bytes().fold(0i64, |h, b| h.wrapping_mul(31).wrapping_add(b as i64))
            })
        };
        self.begin(false, seed);
    }

    fn view_cam(&self) -> (f64, f64, f64, f32, f32) {
        let (ex, ey, ez) = self.player.eye_pos();
        let yaw = self.player.yaw;
        let pitch = self.player.pitch;
        if self.cam_view == 0 || self.screen != Screen::Play {
            return (ex, ey, ez, yaw, pitch);
        }
        let (fx, fy, fz) = look(yaw, pitch);
        let sign = if self.cam_view == 2 { 1.0 } else { -1.0 };
        let dist = if self.cam_view == 2 { 2.6 } else { 4.0 };
        let mut best = (ex, ey, ez);
        for i in 1..=16 {
            let t = dist * i as f64 / 16.0;
            let nx = ex + sign * fx as f64 * t;
            let ny = ey + sign * fy as f64 * t;
            let nz = ez + sign * fz as f64 * t;
            let (q, r) = cell_at(nx, nz);
            let ly = (ny / LAYER).floor() as i32;
            if tidewake_core::materials::is_solid(self.get(q, r, ly)) {
                break;
            }
            best = (nx, ny, nz);
        }
        if self.cam_view == 2 {
            (best.0, best.1, best.2, yaw + std::f32::consts::PI, -pitch)
        } else {
            (best.0, best.1, best.2, yaw, pitch)
        }
    }

    fn draws(&self, gpu: &Gpu) -> Vec<&GpuMesh> {
        let aspect = gpu.aspect();
        let proj = Mat4::perspective_rh(FOV_DEG.to_radians(), aspect, 0.08, 800.0);
        let (cx, cy, cz, yaw, pitch) = self.view_cam();
        let (fx, fy, fz) = look(yaw, pitch);
        let view = Mat4::look_to_rh(Vec3::ZERO, Vec3::new(fx, fy, fz), Vec3::Y);
        let vp = proj * view;
        let mut out = Vec::new();
        for ((cq, cr), slot) in &self.chunks {
            let Some(mesh) = slot.gpu.as_ref() else { continue };
            let q0 = *cq as i64 * CHUNK as i64;
            let r0 = *cr as i64 * CHUNK as i64;
            let (ox, oz) = center(q0, r0);
            let atmo = tide::atmosphere(self.time);
            let horizon = atmo.horizon;
            let sun = atmo.sun;
            let uni = FrameUni {
                vp: vp.to_cols_array_2d(),
                offset: [(ox - cx) as f32, (0.0 - cy) as f32, (oz - cz) as f32, 28.0],
                fog: [horizon[0], horizon[1], horizon[2], if slot.lod { 220.0 } else { 150.0 }],
                sun: [sun[0], sun[1], sun[2], 0.0],
            };
            gpu.write_uni(mesh, &uni);
            out.push(mesh);
        }
        for mesh in [self.cloud_gpu.as_ref(), self.mob_gpu.as_ref(), self.figure_gpu.as_ref()].into_iter().flatten() {
            let atmo = tide::atmosphere(self.time);
            let horizon = atmo.horizon;
            let sun = atmo.sun;
            let uni = FrameUni {
                vp: vp.to_cols_array_2d(),
                offset: [0.0, 0.0, 0.0, 28.0],
                fog: [horizon[0], horizon[1], horizon[2], 150.0],
                sun: [sun[0], sun[1], sun[2], 0.0],
            };
            gpu.write_uni(mesh, &uni);
            out.push(mesh);
        }
        out
    }
}

fn shift(origin: i32, local: i32) -> (i32, i32) {
    let q = origin as i64 * CHUNK as i64 + local as i64;
    (q.div_euclid(CHUNK as i64) as i32, q.rem_euclid(CHUNK as i64) as i32)
}

fn chunk_of_cam(x: f64, z: f64) -> (i32, i32) {
    let (q, r) = tidewake_core::hex::cell_at(x, z);
    chunk_of(q, r)
}

fn look(yaw: f32, pitch: f32) -> (f32, f32, f32) {
    let cp = pitch.cos();
    (yaw.sin() * cp, pitch.sin(), yaw.cos() * cp)
}

impl ApplicationHandler for App {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        if self.window.is_some() {
            return;
        }
        let attrs = Window::default_attributes()
            .with_title(format!("Tidewake {VERSION}"))
            .with_inner_size(LogicalSize::new(1280.0, 720.0));
        let window = match event_loop.create_window(attrs) {
            Ok(w) => Arc::new(w),
            Err(err) => {
                log::error!("could not open a window: {err}");
                event_loop.exit();
                return;
            }
        };
        match Gpu::new(Arc::clone(&window)) {
            Ok(gpu) => {
                log::info!("Tidewake {VERSION} ({})", gpu.adapter_name());
                self.game = Some(Game::boot());
                self.gpu = Some(gpu);
                self.window = Some(window);
            }
            Err(err) => {
                log::error!("graphics init failed: {err}");
                event_loop.exit();
            }
        }
    }

    fn window_event(&mut self, event_loop: &ActiveEventLoop, _id: WindowId, event: WindowEvent) {
        let Some(window) = self.window.clone() else { return };
        match event {
            WindowEvent::CloseRequested => event_loop.exit(),
            WindowEvent::Resized(size) => {
                if let Some(gpu) = self.gpu.as_mut() {
                    gpu.resize(size.width, size.height);
                }
            }
            WindowEvent::CursorMoved { position, .. } => {
                if let Some(game) = self.game.as_mut() {
                    game.mouse = [position.x as f32, position.y as f32];
                }
            }
            WindowEvent::MouseInput { state, button, .. } => {
                if let Some(game) = self.game.as_mut() {
                    if game.screen == Screen::Play {
                        if !game.grabbed && state == ElementState::Pressed {
                            let _ = window.set_cursor_grab(CursorGrabMode::Locked);
                            window.set_cursor_visible(false);
                            game.grabbed = true;
                        } else if button == MouseButton::Left {
                            game.keys.mine = state == ElementState::Pressed;
                        } else if button == MouseButton::Right && state == ElementState::Pressed {
                            game.keys.place = true;
                        }
                    } else if state == ElementState::Pressed {
                        game.clicked = true;
                    }
                }
            }
            WindowEvent::KeyboardInput { event, .. } => {
                let down = event.state == ElementState::Pressed;
                let Some(game) = self.game.as_mut() else { return };
                if game.command.is_some() && down {
                    if let Some(text) = event.text.as_deref() {
                        if let Some(cmd) = game.command.as_mut() {
                            if text.chars().all(|c| c.is_ascii_graphic() || c == ' ') && cmd.len() < 48 {
                                cmd.push_str(text);
                            }
                        }
                    }
                } else if game.screen == Screen::NewSky && down {
                    if let Some(text) = event.text.as_deref() {
                        if text.chars().all(|c| c.is_ascii_digit() || c == '-') && game.seed_text.len() < 18 {
                            game.seed_text.push_str(text);
                        }
                    }
                }
                if let PhysicalKey::Code(code) = event.physical_key {
                    match code {
                        KeyCode::KeyW => game.keys.w = down,
                        KeyCode::KeyA => game.keys.a = down,
                        KeyCode::KeyS => game.keys.s = down,
                        KeyCode::KeyD => game.keys.d = down,
                        KeyCode::Space => {
                            game.keys.up = down;
                            if down { game.jump_edge = true; }
                        }
                        KeyCode::ShiftLeft | KeyCode::ShiftRight => game.keys.down = down,
                        KeyCode::ControlLeft | KeyCode::ControlRight => game.keys.fast = down,
                        KeyCode::F4 if down && game.screen == Screen::Play => {
                            game.player.drifting = !game.player.drifting;
                        }
                        KeyCode::F5 if down && game.screen == Screen::Play => {
                            game.cam_view = (game.cam_view + 1) % 3;
                        }
                        KeyCode::Enter | KeyCode::NumpadEnter if down && game.screen == Screen::NewSky => game.dream(),
                        KeyCode::Enter | KeyCode::NumpadEnter if down && game.command.is_some() => game.run_command(),
                        KeyCode::Backspace if down && game.screen == Screen::NewSky && game.command.is_none() => { game.seed_text.pop(); }
                        KeyCode::Backspace if down => { if let Some(cmd) = game.command.as_mut() { cmd.pop(); } }
                        KeyCode::ArrowUp if down && (game.screen == Screen::NewSky || game.screen == Screen::Settings) => {
                            game.slider = (game.slider + 11) % 12;
                        }
                        KeyCode::ArrowDown if down && (game.screen == Screen::NewSky || game.screen == Screen::Settings) => {
                            game.slider = (game.slider + 1) % 12;
                        }
                        KeyCode::ArrowLeft if down && (game.screen == Screen::NewSky || game.screen == Screen::Settings) => {
                            game.settings.nudge(game.slider, -5);
                        }
                        KeyCode::ArrowRight if down && (game.screen == Screen::NewSky || game.screen == Screen::Settings) => {
                            game.settings.nudge(game.slider, 5);
                        }
                        KeyCode::KeyR if down && game.screen == Screen::Play => { game.save.eat(); }
                        KeyCode::KeyC if down && game.screen == Screen::Play => {
                            if game.save.craft_pocket() {
                                game.save.stats.crafted += 1;
                            }
                        }
                        KeyCode::KeyJ if down && game.screen == Screen::Play => game.journal = !game.journal,
                        KeyCode::Slash if down && game.screen == Screen::Play => game.command = Some(String::new()),
                        KeyCode::KeyT if down && game.screen == Screen::Play && game.save.stats.spires >= 3 => {
                            game.time += 180.0;
                        }
                        KeyCode::KeyE if down && game.screen == Screen::Play => {
                            if game.cast.is_some() {
                                game.reel();
                            } else if !game.try_tool() {
                                let ((ex, ey, ez), (dx, dy, dz)) = game.aim();
                                let (hit, _) = raycast(game, ex, ey, ez, dx, dy, dz, game.reach(), true);
                                if let Some((q, r, y)) = hit {
                                    let mat = game.get(q, r, y);
                                    game.use_block(q, r, y, mat);
                                }
                            }
                        }
                        KeyCode::KeyF if down && game.screen == Screen::Play => game.deposit_held(),
                        KeyCode::KeyV if down && game.screen == Screen::Play => game.withdraw_panel(),
                        KeyCode::KeyG if down && game.screen == Screen::Play => {
                            if let Some(id) = game.glimmer.next_gift() {
                                if game.glimmer.buy(id) {
                                    game.save.stats.gifts += 1;
                                }
                            }
                        }
                        KeyCode::Digit1 if down => game.save.selected = 0,
                        KeyCode::Digit2 if down => game.save.selected = 1,
                        KeyCode::Digit3 if down => game.save.selected = 2,
                        KeyCode::Digit4 if down => game.save.selected = 3,
                        KeyCode::Digit5 if down => game.save.selected = 4,
                        KeyCode::Digit6 if down => game.save.selected = 5,
                        KeyCode::Digit7 if down => game.save.selected = 6,
                        KeyCode::Digit8 if down => game.save.selected = 7,
                        KeyCode::Digit9 if down => game.save.selected = 8,
                        KeyCode::Escape if down => {
                            if game.command.is_some() {
                                game.command = None;
                                return;
                            }
                            if game.journal {
                                game.journal = false;
                                return;
                            }
                            if game.panel.is_some() {
                                game.panel = None;
                                return;
                            }
                            if game.screen == Screen::Play {
                                game.screen = Screen::Pause;
                                let _ = window.set_cursor_grab(CursorGrabMode::None);
                                window.set_cursor_visible(true);
                                game.grabbed = false;
                                return;
                            }
                            if game.screen == Screen::Pause {
                                game.screen = Screen::Play;
                                return;
                            }
                            let _ = window.set_cursor_grab(CursorGrabMode::None);
                            window.set_cursor_visible(true);
                            game.grabbed = false;
                            if game.screen == Screen::Play {
                                game.write_save();
                            }
                            if game.screen != Screen::Title {
                                game.screen = Screen::Title;
                                game.chunks.clear();
                                game.load_err = None;
                            }
                        }
                        _ => {}
                    }
                }
            }
            WindowEvent::RedrawRequested => {
                let size = window.inner_size();
                let (pixels, shown_fps, gen_ms, cam_y, fps_n, quit) = {
                    let Some(game) = self.game.as_mut() else { return };
                    let Some(gpu) = self.gpu.as_ref() else { return };
                    let now = Instant::now();
                    let dt = (now - game.last).as_secs_f32().clamp(0.0, 0.05);
                    game.last = now;
                    game.step(gpu, dt);
                    let pixels = if game.fonts.dirty { Some(game.fonts.pixels.clone()) } else { None };
                    (pixels, game.shown_fps, game.gen_ms, game.cam.y, game.fps_n, game.quit)
                };
                if quit {
                    event_loop.exit();
                    return;
                }
                if let Some(px) = pixels {
                    if let Some(gpu) = self.gpu.as_ref() {
                        gpu.upload_atlas(&px);
                    }
                    if let Some(game) = self.game.as_mut() {
                        game.fonts.dirty = false;
                    }
                }
                let figure_cpu = {
                    let game = self.game.as_ref().unwrap();
                    if game.screen == Screen::Play && game.cam_view != 0 {
                        let walking = game.player.vx.abs() + game.player.vz.abs() > 0.15;
                        let (cx, cy, cz, _, _) = game.view_cam();
                        Some(figure::place(
                            &figure::wanderer(game.time, walking),
                            game.player.yaw,
                            [game.player.x, game.player.y, game.player.z],
                            [cx, cy, cz],
                        ))
                    } else {
                        None
                    }
                };
                if let Some(cpu) = figure_cpu {
                    let uploaded = self.gpu.as_ref().unwrap().upload(&cpu.verts, &cpu.idx);
                    self.game.as_mut().unwrap().figure_gpu = Some(uploaded);
                } else if let Some(game) = self.game.as_mut() {
                    game.figure_gpu = None;
                }
                let (cloud_cpu, mob_cpu) = {
                    let game = self.game.as_ref().unwrap();
                    if game.screen == Screen::Play || game.screen == Screen::Loading {
                        let (cx, cy, cz, _, _) = game.view_cam();
                        let cloud = mesh::cloud_sea(game.time, [cx, cy, cz]);
                        let mut mobs = crate::mesh::CpuMesh { verts: Vec::new(), idx: Vec::new() };
                        for mob in game.mobs.iter().filter(|m| m.alive) {
                            let walking = mob.vx.abs() + mob.vz.abs() > 0.1;
                            let body = figure::creature(mob.kind, mob.t, walking);
                            let placed = figure::place(&body, mob.yaw, [mob.x, mob.y, mob.z], [cx, cy, cz]);
                            let base = mobs.verts.len() as u32;
                            mobs.verts.extend(placed.verts);
                            mobs.idx.extend(placed.idx.into_iter().map(|i| i + base));
                        }
                        (Some(cloud), Some(mobs))
                    } else {
                        (None, None)
                    }
                };
                if let Some(cpu) = cloud_cpu {
                    self.game.as_mut().unwrap().cloud_gpu = Some(self.gpu.as_ref().unwrap().upload(&cpu.verts, &cpu.idx));
                }
                if let Some(cpu) = mob_cpu {
                    let gpu_mesh = if cpu.idx.is_empty() { None } else { Some(self.gpu.as_ref().unwrap().upload(&cpu.verts, &cpu.idx)) };
                    self.game.as_mut().unwrap().mob_gpu = gpu_mesh;
                }
                let ui = self.game.as_mut().unwrap().ui(size.width as f32, size.height as f32);
                let playing = self.game.as_ref().unwrap().screen == Screen::Play
                    || self.game.as_ref().unwrap().screen == Screen::Loading;
                let draws: Vec<&GpuMesh> = if playing {
                    self.game.as_ref().unwrap().draws(self.gpu.as_ref().unwrap())
                } else {
                    Vec::new()
                };
                let n = draws.len();
                let tris: u32 = draws.iter().map(|m| m.n_idx / 3).sum();
                let ui_quads = ui.len() / 6;
                let atmo = tide::atmosphere(self.game.as_ref().unwrap().time);
                let (zenith, horizon, sun) = (atmo.zenith, atmo.horizon, atmo.sun);
                let play_time = self.game.as_ref().unwrap().time;
                self.gpu.as_ref().unwrap().write_sky(zenith, horizon, sun, play_time);
                let clear = if playing {
                    wgpu::Color { r: horizon[0] as f64, g: horizon[1] as f64, b: horizon[2] as f64, a: 1.0 }
                } else {
                    wgpu::Color { r: 0.10, g: 0.08, b: 0.16, a: 1.0 }
                };
                if let Err(err) = self.gpu.as_mut().unwrap().render(clear, draws, &ui) {
                    log::error!("render failed: {err}");
                    event_loop.exit();
                    return;
                }
                if fps_n == 0 {
                    let _ = window.set_title(&format!(
                        "Tidewake {VERSION}  —  {:.0} fps  —  {} chunks  —  gen {:.1} ms",
                        shown_fps, n, gen_ms
                    ));
                }
                self.frames = self.frames.saturating_add(1);
                if self.frame_limit.is_some_and(|lim| self.frames >= lim) {
                    log::info!(
                        "drew {} frame(s) at {:.0} fps, {} chunks, {} tris, {} ui, last gen {:.1} ms, cam y {:.1} (layer {:.0})",
                        self.frames,
                        shown_fps,
                        n,
                        tris,
                        ui_quads,
                        gen_ms,
                        cam_y,
                        cam_y / LAYER
                    );
                    event_loop.exit();
                }
            }
            _ => {}
        }
    }

    fn device_event(&mut self, _event_loop: &ActiveEventLoop, _id: winit::event::DeviceId, event: DeviceEvent) {
        if let DeviceEvent::MouseMotion { delta } = event {
            if let Some(game) = self.game.as_mut() {
                if game.grabbed && game.screen == Screen::Play {
                    game.player.yaw += delta.0 as f32 * 0.0025;
                    game.player.pitch = (game.player.pitch - delta.1 as f32 * 0.0025).clamp(-1.45, 1.45);
                    game.sync_cam();
                }
            }
        }
    }

    fn about_to_wait(&mut self, _event_loop: &ActiveEventLoop) {
        if let Some(window) = self.window.as_ref() {
            window.request_redraw();
        }
    }
}

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();
    log::info!("Tidewake {VERSION}");
    let event_loop = EventLoop::new().expect("event loop");
    let mut app = App::new();
    event_loop.run_app(&mut app).expect("event loop run");
}

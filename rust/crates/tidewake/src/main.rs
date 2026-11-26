//! Tidewake 2.1. Fly a generated v6 sky: hex islands, fog, near and far meshes.

mod gpu;
mod mesh;

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use glam::{Mat4, Vec3};
use tidewake_core::chunk::{self, Chunk};
use tidewake_core::columns::Generator;
use tidewake_core::config::{CHUNK, FOV_DEG, LAYER, VERSION};
use tidewake_core::hex::{center, chunk_of};
use tidewake_core::settings::Settings;
use winit::application::ApplicationHandler;
use winit::dpi::LogicalSize;
use winit::event::{DeviceEvent, ElementState, KeyEvent, WindowEvent};
use winit::event_loop::{ActiveEventLoop, EventLoop};
use winit::keyboard::{KeyCode, PhysicalKey};
use winit::window::{CursorGrabMode, Window, WindowId};

use gpu::{FrameUni, Gpu, GpuMesh, FOG};
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

impl Game {
    fn boot() -> Self {
        let gen = Generator::new(7, Settings::default());
        let (x, y, z) = chunk::find_spawn(&gen);
        log::info!("spawn at {x:.1}, {y:.1}, {z:.1}");
        Self {
            gen,
            cam: Cam { x, y, z, yaw: 0.4, pitch: -0.45 },
            keys: Keys { w: false, a: false, s: false, d: false, up: false, down: false, fast: false },
            grabbed: false,
            chunks: HashMap::new(),
            last: Instant::now(),
            fps_t: 0.0,
            fps_n: 0,
            shown_fps: 0.0,
            gen_ms: 0.0,
        }
    }

    fn step(&mut self, gpu: &Gpu, dt: f32) {
        let (fx, _fy, fz) = look(self.cam.yaw, self.cam.pitch);
        let flat = Vec3::new(fx, 0.0, fz);
        let flat = if flat.length_squared() > 1e-6 { flat.normalize() } else { Vec3::Z };
        let right = Vec3::new(flat.z, 0.0, -flat.x);
        let mut wish = Vec3::ZERO;
        if self.keys.w { wish += flat; }
        if self.keys.s { wish -= flat; }
        if self.keys.d { wish += right; }
        if self.keys.a { wish -= right; }
        if self.keys.up { wish += Vec3::Y; }
        if self.keys.down { wish -= Vec3::Y; }
        if wish.length_squared() > 1e-6 {
            wish = wish.normalize();
        }
        let speed = if self.keys.fast { 42.0 } else { 16.0 };
        self.cam.x += wish.x as f64 * speed as f64 * dt as f64;
        self.cam.y += wish.y as f64 * speed as f64 * dt as f64;
        self.cam.z += wish.z as f64 * speed as f64 * dt as f64;

        let (cq, cr) = chunk_of_cam(self.cam.x, self.cam.z);
        let mut want = Vec::new();
        for a in (cq - VIEW)..=(cq + VIEW) {
            for b in (cr - VIEW)..=(cr + VIEW) {
                if (a - cq).abs().max((b - cr).abs()) <= VIEW {
                    want.push((a, b));
                }
            }
        }
        let mut made = 0;
        for key in &want {
            if self.chunks.contains_key(key) {
                continue;
            }
            if made >= GEN_PER_FRAME {
                break;
            }
            let t = Instant::now();
            let cpu = chunk::generate(&self.gen, key.0, key.1);
            self.gen_ms = t.elapsed().as_secs_f64() as f32 * 1000.0;
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
    }

    fn draws(&self, gpu: &Gpu) -> Vec<&GpuMesh> {
        let aspect = gpu.aspect();
        let proj = Mat4::perspective_rh(FOV_DEG.to_radians(), aspect, 0.08, 800.0);
        let (fx, fy, fz) = look(self.cam.yaw, self.cam.pitch);
        let view = Mat4::look_to_rh(Vec3::ZERO, Vec3::new(fx, fy, fz), Vec3::Y);
        let vp = proj * view;
        let mut out = Vec::new();
        for ((cq, cr), slot) in &self.chunks {
            let Some(mesh) = slot.gpu.as_ref() else { continue };
            let q0 = *cq as i64 * CHUNK as i64;
            let r0 = *cr as i64 * CHUNK as i64;
            let (ox, oz) = center(q0, r0);
            let uni = FrameUni {
                vp: vp.to_cols_array_2d(),
                offset: [(ox - self.cam.x) as f32, (0.0 - self.cam.y) as f32, (oz - self.cam.z) as f32, 28.0],
                fog: [FOG[0], FOG[1], FOG[2], if slot.lod { 220.0 } else { 150.0 }],
                sun: [0.35, 0.86, 0.28, 0.0],
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
            WindowEvent::MouseInput { state: ElementState::Pressed, .. } => {
                let _ = window.set_cursor_grab(CursorGrabMode::Locked);
                window.set_cursor_visible(false);
                if let Some(game) = self.game.as_mut() {
                    game.grabbed = true;
                }
            }
            WindowEvent::KeyboardInput { event: KeyEvent { physical_key, state, .. }, .. } => {
                let down = state == ElementState::Pressed;
                let Some(game) = self.game.as_mut() else { return };
                if let PhysicalKey::Code(code) = physical_key {
                    match code {
                        KeyCode::KeyW => game.keys.w = down,
                        KeyCode::KeyA => game.keys.a = down,
                        KeyCode::KeyS => game.keys.s = down,
                        KeyCode::KeyD => game.keys.d = down,
                        KeyCode::Space => game.keys.up = down,
                        KeyCode::ShiftLeft | KeyCode::ShiftRight => game.keys.down = down,
                        KeyCode::ControlLeft | KeyCode::ControlRight => game.keys.fast = down,
                        KeyCode::Escape if down => {
                            let _ = window.set_cursor_grab(CursorGrabMode::None);
                            window.set_cursor_visible(true);
                            game.grabbed = false;
                        }
                        _ => {}
                    }
                }
            }
            WindowEvent::RedrawRequested => {
                let Some(gpu) = self.gpu.as_mut() else { return };
                let Some(game) = self.game.as_mut() else { return };
                let now = Instant::now();
                let dt = (now - game.last).as_secs_f32().clamp(0.0, 0.05);
                game.last = now;
                game.step(gpu, dt);
                let draws: Vec<&GpuMesh> = game.draws(gpu);
                let n = draws.len();
                let tris: u32 = draws.iter().map(|m| m.n_idx / 3).sum();
                if let Err(err) = gpu.render(draws) {
                    log::error!("render failed: {err}");
                    event_loop.exit();
                    return;
                }
                if game.fps_n == 0 {
                    let _ = window.set_title(&format!(
                        "Tidewake {VERSION}  —  {:.0} fps  —  {} chunks  —  gen {:.1} ms",
                        game.shown_fps, n, game.gen_ms
                    ));
                }
                self.frames = self.frames.saturating_add(1);
                if self.frame_limit.is_some_and(|lim| self.frames >= lim) {
                    log::info!(
                        "drew {} frame(s) at {:.0} fps, {} chunks, {} tris, last gen {:.1} ms, cam y {:.1} (layer {:.0})",
                        self.frames,
                        game.shown_fps,
                        n,
                        tris,
                        game.gen_ms,
                        game.cam.y,
                        game.cam.y / LAYER
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
                if game.grabbed {
                    game.cam.yaw += delta.0 as f32 * 0.0025;
                    game.cam.pitch = (game.cam.pitch - delta.1 as f32 * 0.0025).clamp(-1.45, 1.45);
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

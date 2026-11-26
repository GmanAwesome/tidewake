//! Tidewake 2.1 window. Opens a window and clears it to the Lighttide sky.

mod gpu;

use std::sync::Arc;

use winit::application::ApplicationHandler;
use winit::dpi::LogicalSize;
use winit::event::WindowEvent;
use winit::event_loop::{ActiveEventLoop, EventLoop};
use winit::window::{Window, WindowId};

use gpu::Gpu;

const VERSION: &str = "2.1";

struct App {
    window: Option<Arc<Window>>,
    gpu: Option<Gpu>,
    frames: u32,
    frame_limit: Option<u32>,
}

impl App {
    fn new() -> Self {
        let frame_limit = std::env::var("TIDEWAKE_FRAMES")
            .ok()
            .and_then(|s| s.parse().ok());
        Self {
            window: None,
            gpu: None,
            frames: 0,
            frame_limit,
        }
    }
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
                log::info!("Tidewake {VERSION} window ready ({})", gpu.adapter_name());
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
        match event {
            WindowEvent::CloseRequested => event_loop.exit(),
            WindowEvent::Resized(size) => {
                if let Some(gpu) = self.gpu.as_mut() {
                    gpu.resize(size.width, size.height);
                }
            }
            WindowEvent::RedrawRequested => {
                if let Some(gpu) = self.gpu.as_mut() {
                    if let Err(err) = gpu.render() {
                        log::error!("render failed: {err}");
                        event_loop.exit();
                        return;
                    }
                }
                self.frames = self.frames.saturating_add(1);
                if self.frame_limit.is_some_and(|n| self.frames >= n) {
                    log::info!("drew {} frame(s); exiting", self.frames);
                    event_loop.exit();
                }
            }
            _ => {}
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

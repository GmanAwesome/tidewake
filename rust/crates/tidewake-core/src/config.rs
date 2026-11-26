//! Tuning constants from `tidewake/config.py`.

pub const HEX: f64 = 1.0;
pub const LAYER: f64 = 0.85;
pub const SQ3: f64 = 1.7320508075688772;
pub const CHUNK: i32 = 16;
pub const LAYERS: i32 = 500;
pub const CLOUD_SEA: i32 = 12;

pub const VIEW_DISTANCE: i32 = 6;
pub const LOD_DISTANCE: i32 = 4;

pub const WINDOW_W: u32 = 1280;
pub const WINDOW_H: u32 = 720;
pub const FOV_DEG: f32 = 70.0;

pub const RADIUS: f64 = 0.32;
pub const HEIGHT: f64 = 1.66;
pub const EYE: f64 = 1.48;
pub const CROUCH_HEIGHT: f64 = 1.25;
pub const CROUCH_EYE: f64 = 1.05;
pub const CROUCH_SPEED: f64 = 1.55;
pub const WALK: f64 = 4.6;
pub const HURRY: f64 = 7.4;
pub const DRIFT_SPEED: f64 = 13.0;
pub const GRAVITY: f64 = 24.0;
pub const JUMP: f64 = 8.6;
pub const GLIDE_FALL: f64 = 2.2;
pub const REACH: f64 = 8.0;

pub const VERSION: &str = "2.1";

pub const TOP_MIN: i32 = CLOUD_SEA + 12;
pub const TOP_MAX_V6: i32 = LAYERS - 18;

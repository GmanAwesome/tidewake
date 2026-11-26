//! Tidewake 2.1 simulation core: hex world, v6 generator, and the systems around them.
//!
//! The Python package remains the spec. This crate has no window and no GPU.

pub mod config;
pub mod hex;
pub mod materials;
pub mod noise;
pub mod pyrandom;
pub mod settings;

pub use config::VERSION;

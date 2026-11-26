//! Tidewake 2.1 simulation core: hex world, v6 generator, and the systems around them.
//!
//! The Python package remains the spec. This crate has no window and no GPU.

pub mod biomes;
pub mod chunk;
pub mod columns;
pub mod config;
pub mod craft;
pub mod glimmer;
pub mod hex;
pub mod lesson;
pub mod materials;
pub mod mine;
pub mod mobs;
pub mod player;
pub mod noise;
pub mod pyrandom;
pub mod save;
pub mod settings;
pub mod showpieces;
pub mod structures;
pub mod tide;
pub mod tiers;
pub mod trees;

pub use columns::{size_class, Column, Generator, SizeClass};

pub use config::VERSION;

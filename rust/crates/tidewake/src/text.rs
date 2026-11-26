//! Bitmap text from the repo's own Tidewake fonts.

use std::collections::HashMap;

use fontdue::{Font, FontSettings};

pub const ATLAS: u32 = 512;

#[derive(Clone, Copy)]
pub struct Glyph {
    pub u0: f32,
    pub v0: f32,
    pub u1: f32,
    pub v1: f32,
    pub w: f32,
    pub h: f32,
    pub advance: f32,
    pub ymin: f32,
}

pub struct Fonts {
    title: Font,
    body: Font,
    pub pixels: Vec<u8>,
    glyphs: HashMap<(u8, char), Glyph>,
    pen_x: u32,
    pen_y: u32,
    row_h: u32,
    pub dirty: bool,
}

impl Fonts {
    pub fn load() -> Self {
        let settings = FontSettings { scale: 40.0, ..FontSettings::default() };
        let title = Font::from_bytes(
            include_bytes!("../../../../assets/fonts/TidewakeTitle.ttf") as &[u8],
            settings,
        )
        .expect("title font");
        let body = Font::from_bytes(
            include_bytes!("../../../../assets/fonts/TidewakeBody.ttf") as &[u8],
            settings,
        )
        .expect("body font");
        let mut pixels = vec![0u8; (ATLAS * ATLAS) as usize];
        pixels[0] = 255; // 1×1 white texel for solid rectangles
        Self {
            title,
            body,
            pixels,
            glyphs: HashMap::new(),
            pen_x: 2,
            pen_y: 1,
            row_h: 1,
            dirty: true,
        }
    }

    fn font(&self, which: u8) -> &Font {
        if which == 0 { &self.title } else { &self.body }
    }

    pub fn glyph(&mut self, which: u8, ch: char, px: f32) -> Glyph {
        if let Some(g) = self.glyphs.get(&(which, ch)) {
            let scale = px / 40.0;
            return Glyph {
                w: g.w * scale,
                h: g.h * scale,
                advance: g.advance * scale,
                ymin: g.ymin * scale,
                ..*g
            };
        }
        let (metrics, bitmap) = self.font(which).rasterize(ch, 40.0);
        let gw = metrics.width as u32;
        let gh = metrics.height as u32;
        if self.pen_x + gw + 1 >= ATLAS {
            self.pen_x = 2;
            self.pen_y += self.row_h + 1;
            self.row_h = 1;
        }
        if gh > self.row_h {
            self.row_h = gh;
        }
        for row in 0..gh {
            let dst = ((self.pen_y + row) * ATLAS + self.pen_x) as usize;
            let src = (row * gw) as usize;
            if dst + gw as usize <= self.pixels.len() && !bitmap.is_empty() {
                self.pixels[dst..dst + gw as usize].copy_from_slice(&bitmap[src..src + gw as usize]);
            }
        }
        let g = Glyph {
            u0: self.pen_x as f32 / ATLAS as f32,
            v0: self.pen_y as f32 / ATLAS as f32,
            u1: (self.pen_x + gw) as f32 / ATLAS as f32,
            v1: (self.pen_y + gh) as f32 / ATLAS as f32,
            w: gw as f32,
            h: gh as f32,
            advance: metrics.advance_width,
            ymin: metrics.ymin as f32,
        };
        self.pen_x += gw + 1;
        self.glyphs.insert((which, ch), g);
        self.dirty = true;
        let scale = px / 40.0;
        Glyph {
            w: g.w * scale,
            h: g.h * scale,
            advance: g.advance * scale,
            ymin: g.ymin * scale,
            ..g
        }
    }

    pub fn width(&mut self, which: u8, text: &str, px: f32) -> f32 {
        text.chars().map(|ch| self.glyph(which, ch, px).advance).sum()
    }
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
pub struct UiVert {
    pub pos: [f32; 2],
    pub uv: [f32; 2],
    pub col: [f32; 4],
}

pub struct Writer<'a> {
    pub fonts: &'a mut Fonts,
    pub verts: &'a mut Vec<UiVert>,
    pub w: f32,
    pub h: f32,
}

impl Writer<'_> {
    fn clip(&self, x: f32, y: f32) -> [f32; 2] {
        [x / self.w * 2.0 - 1.0, 1.0 - y / self.h * 2.0]
    }

    pub fn rect(&mut self, x: f32, y: f32, w: f32, h: f32, col: [f32; 4]) {
        let uv = 0.5 / ATLAS as f32;
        self.quad(x, y, w, h, uv, uv, uv, uv, col);
    }

    pub fn text(&mut self, which: u8, text: &str, mut x: f32, y: f32, px: f32, col: [f32; 4], center: bool) {
        if center {
            x -= self.fonts.width(which, text, px) * 0.5;
        }
        for ch in text.chars() {
            let g = self.fonts.glyph(which, ch, px);
            let gy = y - g.ymin - g.h;
            if g.w > 0.0 && g.h > 0.0 {
                self.quad(x, gy, g.w, g.h, g.u0, g.v0, g.u1, g.v1, col);
            }
            x += g.advance;
        }
    }

    fn quad(&mut self, x: f32, y: f32, w: f32, h: f32, u0: f32, v0: f32, u1: f32, v1: f32, col: [f32; 4]) {
        let p = [
            self.clip(x, y),
            self.clip(x + w, y),
            self.clip(x + w, y + h),
            self.clip(x, y + h),
        ];
        let uv = [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
        let idx = [0, 1, 2, 0, 2, 3];
        for i in idx {
            self.verts.push(UiVert { pos: p[i], uv: uv[i], col });
        }
    }
}

pub struct Button {
    pub x: f32,
    pub y: f32,
    pub w: f32,
    pub h: f32,
}

impl Button {
    pub fn hit(&self, mx: f32, my: f32) -> bool {
        mx >= self.x && mx <= self.x + self.w && my >= self.y && my <= self.y + self.h
    }
}

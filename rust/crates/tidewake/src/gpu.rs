//! wgpu device, Lighttide clear, and the fogged hex terrain pipeline.

use std::sync::Arc;

use winit::window::Window;

use crate::mesh::Vert;
use crate::text::{UiVert, ATLAS};

/// Soft Lighttide sky. The Python renderer clears to a mix of horizon and zenith.
#[allow(dead_code)]
pub const SKY_CLEAR: wgpu::Color = wgpu::Color {
    r: 0.62,
    g: 0.78,
    b: 0.92,
    a: 1.0,
};

#[allow(dead_code)]
pub const FOG: [f32; 3] = [0.62, 0.78, 0.92];

/// Lighttide (t = 0) through Dusktide (t = 1). One full cycle is 720 seconds.
pub fn tide_colors(time: f32) -> ([f32; 3], [f32; 3], [f32; 3]) {
    let t = ((time / 720.0) * std::f32::consts::TAU).sin().mul_add(0.5, 0.5);
    let mix = |a: [f32; 3], b: [f32; 3]| {
        [
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t,
        ]
    };
    (
        mix([0.45, 0.66, 0.90], [0.16, 0.10, 0.32]),
        mix([0.72, 0.84, 0.96], [0.62, 0.34, 0.52]),
        mix([1.0, 0.96, 0.84], [0.90, 0.48, 0.58]),
    )
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
struct SkyUni {
    zenith: [f32; 4],
    horizon: [f32; 4],
    sun: [f32; 4],
    misc: [f32; 4],
}

#[repr(C)]
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
pub struct FrameUni {
    pub vp: [[f32; 4]; 4],
    /// xyz = chunk origin minus camera. w = fog start.
    pub offset: [f32; 4],
    /// rgb = fog colour. w = fog end.
    pub fog: [f32; 4],
    pub sun: [f32; 4],
}

pub struct GpuMesh {
    pub vbuf: wgpu::Buffer,
    pub ibuf: wgpu::Buffer,
    pub uni: wgpu::Buffer,
    pub bind: wgpu::BindGroup,
    pub n_idx: u32,
}

pub struct Gpu {
    surface: wgpu::Surface<'static>,
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    config: wgpu::SurfaceConfiguration,
    adapter_name: String,
    pipeline: wgpu::RenderPipeline,
    layout: wgpu::BindGroupLayout,
    depth: wgpu::TextureView,
    ui_pipeline: wgpu::RenderPipeline,
    ui_bind: wgpu::BindGroup,
    ui_tex: wgpu::Texture,
    sky_pipeline: wgpu::RenderPipeline,
    sky_bind: wgpu::BindGroup,
    sky_buf: wgpu::Buffer,
    atlas_view: wgpu::TextureView,
    atlas_sampler: wgpu::Sampler,
    _atlas: wgpu::Texture,
}

impl Gpu {
    pub fn new(window: Arc<Window>) -> Result<Self, String> {
        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
            backends: wgpu::Backends::all(),
            ..Default::default()
        });
        let surface = instance
            .create_surface(window.clone())
            .map_err(|e| format!("create surface: {e}"))?;
        let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            compatible_surface: Some(&surface),
            force_fallback_adapter: false,
        }))
        .ok_or_else(|| "no graphics adapter".to_string())?;
        let adapter_name = adapter.get_info().name;
        let (device, queue) = pollster::block_on(adapter.request_device(
            &wgpu::DeviceDescriptor {
                label: Some("tidewake"),
                required_features: wgpu::Features::empty(),
                required_limits: wgpu::Limits::default(),
                memory_hints: wgpu::MemoryHints::Performance,
            },
            None,
        ))
        .map_err(|e| format!("request device: {e}"))?;

        let caps = surface.get_capabilities(&adapter);
        let format = caps
            .formats
            .iter()
            .copied()
            .find(|f| f.is_srgb())
            .unwrap_or(caps.formats[0]);
        let size = window.inner_size();
        let config = wgpu::SurfaceConfiguration {
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            format,
            width: size.width.max(1),
            height: size.height.max(1),
            present_mode: wgpu::PresentMode::Fifo,
            alpha_mode: caps.alpha_modes[0],
            view_formats: vec![],
            desired_maximum_frame_latency: 2,
        };
        surface.configure(&device, &config);

        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("terrain"),
            source: wgpu::ShaderSource::Wgsl(SHADER.into()),
        });
        let (atlas, atlas_view, atlas_sampler) = load_atlas(&device, &queue);
        let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("frame"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX | wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Texture {
                        sample_type: wgpu::TextureSampleType::Float { filterable: true },
                        view_dimension: wgpu::TextureViewDimension::D2,
                        multisampled: false,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 2,
                    visibility: wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering),
                    count: None,
                },
            ],
        });
        let pipe_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("terrain"),
            bind_group_layouts: &[&layout],
            push_constant_ranges: &[],
        });
        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("terrain"),
            layout: Some(&pipe_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs"),
                buffers: &[wgpu::VertexBufferLayout {
                    array_stride: std::mem::size_of::<Vert>() as u64,
                    step_mode: wgpu::VertexStepMode::Vertex,
                    attributes: &wgpu::vertex_attr_array![0 => Float32x3, 1 => Float32x3, 2 => Float32x3, 3 => Float32x2, 4 => Float32x2],
                }],
                compilation_options: Default::default(),
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: Some("fs"),
                targets: &[Some(wgpu::ColorTargetState {
                    format,
                    blend: None,
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                cull_mode: Some(wgpu::Face::Back),
                front_face: wgpu::FrontFace::Ccw,
                ..Default::default()
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: wgpu::TextureFormat::Depth32Float,
                depth_write_enabled: true,
                depth_compare: wgpu::CompareFunction::Less,
                stencil: Default::default(),
                bias: Default::default(),
            }),
            multisample: Default::default(),
            multiview: None,
            cache: None,
        });
        let depth = depth_view(&device, config.width, config.height);
        let (ui_pipeline, ui_bind, ui_tex) = ui_pipeline(&device, format);
        let (sky_pipeline, sky_bind, sky_buf) = sky_pipeline(&device, format);

        Ok(Self {
            surface,
            device,
            queue,
            config,
            adapter_name,
            pipeline,
            layout,
            depth,
            ui_pipeline,
            ui_bind,
            ui_tex,
            sky_pipeline,
            sky_bind,
            sky_buf,
            atlas_view,
            atlas_sampler,
            _atlas: atlas,
        })
    }

    pub fn write_sky(&self, zenith: [f32; 3], horizon: [f32; 3], sun: [f32; 3], time: f32) {
        let uni = SkyUni {
            zenith: [zenith[0], zenith[1], zenith[2], 1.0],
            horizon: [horizon[0], horizon[1], horizon[2], 1.0],
            sun: [sun[0], sun[1], sun[2], 1.0],
            misc: [self.config.height as f32, time, self.config.width as f32, 0.0],
        };
        self.queue.write_buffer(&self.sky_buf, 0, bytemuck::bytes_of(&uni));
    }

    pub fn upload_atlas(&self, pixels: &[u8]) {
        self.queue.write_texture(
            wgpu::ImageCopyTexture {
                texture: &self.ui_tex,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            pixels,
            wgpu::ImageDataLayout {
                offset: 0,
                bytes_per_row: Some(ATLAS),
                rows_per_image: Some(ATLAS),
            },
            wgpu::Extent3d { width: ATLAS, height: ATLAS, depth_or_array_layers: 1 },
        );
    }

    pub fn adapter_name(&self) -> &str {
        &self.adapter_name
    }

    pub fn aspect(&self) -> f32 {
        self.config.width as f32 / self.config.height.max(1) as f32
    }

    pub fn resize(&mut self, width: u32, height: u32) {
        if width == 0 || height == 0 {
            return;
        }
        self.config.width = width;
        self.config.height = height;
        self.surface.configure(&self.device, &self.config);
        self.depth = depth_view(&self.device, width, height);
    }

    pub fn upload(&self, verts: &[Vert], idx: &[u32]) -> GpuMesh {
        use wgpu::util::DeviceExt;
        let vbuf = self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("chunk-v"),
            contents: bytemuck::cast_slice(verts),
            usage: wgpu::BufferUsages::VERTEX,
        });
        let ibuf = self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("chunk-i"),
            contents: bytemuck::cast_slice(idx),
            usage: wgpu::BufferUsages::INDEX,
        });
        let uni = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("chunk-u"),
            size: std::mem::size_of::<FrameUni>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let bind = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("chunk-bind"),
            layout: &self.layout,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: uni.as_entire_binding() },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: wgpu::BindingResource::TextureView(&self.atlas_view),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: wgpu::BindingResource::Sampler(&self.atlas_sampler),
                },
            ],
        });
        GpuMesh { vbuf, ibuf, uni, bind, n_idx: idx.len() as u32 }
    }

    pub fn write_uni(&self, mesh: &GpuMesh, uni: &FrameUni) {
        self.queue.write_buffer(&mesh.uni, 0, bytemuck::bytes_of(uni));
    }

    pub fn render<'a>(
        &mut self,
        clear: wgpu::Color,
        draws: impl IntoIterator<Item = &'a GpuMesh>,
        ui: &[UiVert],
    ) -> Result<(), String> {
        let frame = match self.surface.get_current_texture() {
            Ok(frame) => frame,
            Err(wgpu::SurfaceError::Lost | wgpu::SurfaceError::Outdated) => {
                self.surface.configure(&self.device, &self.config);
                return Ok(());
            }
            Err(wgpu::SurfaceError::Timeout) => return Ok(()),
            Err(wgpu::SurfaceError::OutOfMemory) => return Err("gpu out of memory".into()),
        };
        let view = frame.texture.create_view(&wgpu::TextureViewDescriptor::default());
        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("frame"),
        });
        {
            let mut sky = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("sky-dome"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(clear),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            sky.set_pipeline(&self.sky_pipeline);
            sky.set_bind_group(0, &self.sky_bind, &[]);
            sky.draw(0..3, 0..1);
        }
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("terrain"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Load,
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &self.depth,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Store,
                    }),
                    stencil_ops: None,
                }),
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            pass.set_pipeline(&self.pipeline);
            for mesh in draws {
                if mesh.n_idx == 0 {
                    continue;
                }
                pass.set_bind_group(0, &mesh.bind, &[]);
                pass.set_vertex_buffer(0, mesh.vbuf.slice(..));
                pass.set_index_buffer(mesh.ibuf.slice(..), wgpu::IndexFormat::Uint32);
                pass.draw_indexed(0..mesh.n_idx, 0, 0..1);
            }
        }
        if !ui.is_empty() {
            use wgpu::util::DeviceExt;
            let buf = self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                label: Some("ui"),
                contents: bytemuck::cast_slice(ui),
                usage: wgpu::BufferUsages::VERTEX,
            });
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("ui"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations { load: wgpu::LoadOp::Load, store: wgpu::StoreOp::Store },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            pass.set_pipeline(&self.ui_pipeline);
            pass.set_bind_group(0, &self.ui_bind, &[]);
            pass.set_vertex_buffer(0, buf.slice(..));
            pass.draw(0..ui.len() as u32, 0..1);
        }
        self.queue.submit(std::iter::once(encoder.finish()));
        frame.present();
        Ok(())
    }
}

fn depth_view(device: &wgpu::Device, w: u32, h: u32) -> wgpu::TextureView {
    let tex = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("depth"),
        size: wgpu::Extent3d { width: w, height: h, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Depth32Float,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
        view_formats: &[],
    });
    tex.create_view(&Default::default())
}

fn load_atlas(device: &wgpu::Device, queue: &wgpu::Queue) -> (wgpu::Texture, wgpu::TextureView, wgpu::Sampler) {
    const W: u32 = 1024;
    const H: u32 = 3072;
    let bytes = include_bytes!("../assets/atlas.bin");
    let tex = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("texpack"),
        size: wgpu::Extent3d { width: W, height: H, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rg8Unorm,
        usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
        view_formats: &[],
    });
    queue.write_texture(
        wgpu::ImageCopyTexture {
            texture: &tex,
            mip_level: 0,
            origin: wgpu::Origin3d::ZERO,
            aspect: wgpu::TextureAspect::All,
        },
        bytes,
        wgpu::ImageDataLayout { offset: 0, bytes_per_row: Some(W * 2), rows_per_image: Some(H) },
        wgpu::Extent3d { width: W, height: H, depth_or_array_layers: 1 },
    );
    let view = tex.create_view(&Default::default());
    let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
        label: Some("texpack"),
        mag_filter: wgpu::FilterMode::Linear,
        min_filter: wgpu::FilterMode::Linear,
        address_mode_u: wgpu::AddressMode::ClampToEdge,
        address_mode_v: wgpu::AddressMode::ClampToEdge,
        ..Default::default()
    });
    (tex, view, sampler)
}

fn sky_pipeline(
    device: &wgpu::Device,
    format: wgpu::TextureFormat,
) -> (wgpu::RenderPipeline, wgpu::BindGroup, wgpu::Buffer) {
    let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("sky"),
        source: wgpu::ShaderSource::Wgsl(SKY_SHADER.into()),
    });
    let buf = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("sky-u"),
        size: std::mem::size_of::<SkyUni>() as u64,
        usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("sky"),
        entries: &[wgpu::BindGroupLayoutEntry {
            binding: 0,
            visibility: wgpu::ShaderStages::FRAGMENT,
            ty: wgpu::BindingType::Buffer {
                ty: wgpu::BufferBindingType::Uniform,
                has_dynamic_offset: false,
                min_binding_size: None,
            },
            count: None,
        }],
    });
    let bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("sky"),
        layout: &layout,
        entries: &[wgpu::BindGroupEntry { binding: 0, resource: buf.as_entire_binding() }],
    });
    let pipe_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("sky"),
        bind_group_layouts: &[&layout],
        push_constant_ranges: &[],
    });
    let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
        label: Some("sky"),
        layout: Some(&pipe_layout),
        vertex: wgpu::VertexState {
            module: &shader,
            entry_point: Some("vs"),
            buffers: &[],
            compilation_options: Default::default(),
        },
        fragment: Some(wgpu::FragmentState {
            module: &shader,
            entry_point: Some("fs"),
            targets: &[Some(wgpu::ColorTargetState {
                format,
                blend: None,
                write_mask: wgpu::ColorWrites::ALL,
            })],
            compilation_options: Default::default(),
        }),
        primitive: Default::default(),
        depth_stencil: None,
        multisample: Default::default(),
        multiview: None,
        cache: None,
    });
    (pipeline, bind, buf)
}

const SKY_SHADER: &str = r#"
struct U {
    zenith: vec4<f32>,
    horizon: vec4<f32>,
    sun: vec4<f32>,
    misc: vec4<f32>,
}
@group(0) @binding(0) var<uniform> u: U;

@vertex
fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4<f32> {
    let x = f32(i32(i & 1u) * 4 - 1);
    let y = f32(i32(i & 2u) * 2 - 1);
    return vec4<f32>(x, y, 0.0, 1.0);
}

@fragment
fn fs(@builtin(position) pos: vec4<f32>) -> @location(0) vec4<f32> {
    let h = max(u.misc.x, 1.0);
    let t = clamp(pos.y / h, 0.0, 1.0);
    var col = mix(u.horizon.rgb, u.zenith.rgb, smoothstep(0.0, 0.75, 1.0 - t));
    let sun_uv = vec2<f32>(u.misc.z * 0.72, h * (0.28 + 0.25 * sin(u.misc.y * 0.008)));
    let d = length(pos.xy - sun_uv) / h;
    col = col + u.sun.rgb * smoothstep(0.08, 0.0, d);
    return vec4<f32>(col, 1.0);
}
"#;

fn ui_pipeline(
    device: &wgpu::Device,
    format: wgpu::TextureFormat,
) -> (wgpu::RenderPipeline, wgpu::BindGroup, wgpu::Texture) {
    let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("ui"),
        source: wgpu::ShaderSource::Wgsl(UI_SHADER.into()),
    });
    let tex = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("font"),
        size: wgpu::Extent3d { width: ATLAS, height: ATLAS, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::R8Unorm,
        usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
        view_formats: &[],
    });
    let view = tex.create_view(&Default::default());
    let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
        label: Some("font"),
        mag_filter: wgpu::FilterMode::Linear,
        min_filter: wgpu::FilterMode::Linear,
        ..Default::default()
    });
    let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("ui"),
        entries: &[
            wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::FRAGMENT,
                ty: wgpu::BindingType::Texture {
                    sample_type: wgpu::TextureSampleType::Float { filterable: true },
                    view_dimension: wgpu::TextureViewDimension::D2,
                    multisampled: false,
                },
                count: None,
            },
            wgpu::BindGroupLayoutEntry {
                binding: 1,
                visibility: wgpu::ShaderStages::FRAGMENT,
                ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering),
                count: None,
            },
        ],
    });
    let bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("ui"),
        layout: &layout,
        entries: &[
            wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(&view) },
            wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::Sampler(&sampler) },
        ],
    });
    let pipe_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("ui"),
        bind_group_layouts: &[&layout],
        push_constant_ranges: &[],
    });
    let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
        label: Some("ui"),
        layout: Some(&pipe_layout),
        vertex: wgpu::VertexState {
            module: &shader,
            entry_point: Some("vs"),
            buffers: &[wgpu::VertexBufferLayout {
                array_stride: std::mem::size_of::<UiVert>() as u64,
                step_mode: wgpu::VertexStepMode::Vertex,
                attributes: &wgpu::vertex_attr_array![0 => Float32x2, 1 => Float32x2, 2 => Float32x4],
            }],
            compilation_options: Default::default(),
        },
        fragment: Some(wgpu::FragmentState {
            module: &shader,
            entry_point: Some("fs"),
            targets: &[Some(wgpu::ColorTargetState {
                format,
                blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                write_mask: wgpu::ColorWrites::ALL,
            })],
            compilation_options: Default::default(),
        }),
        primitive: wgpu::PrimitiveState {
            topology: wgpu::PrimitiveTopology::TriangleList,
            cull_mode: None,
            ..Default::default()
        },
        depth_stencil: None,
        multisample: Default::default(),
        multiview: None,
        cache: None,
    });
    (pipeline, bind, tex)
}

const UI_SHADER: &str = r#"
@group(0) @binding(0) var font_tex: texture_2d<f32>;
@group(0) @binding(1) var font_samp: sampler;

struct Vin {
    @location(0) pos: vec2<f32>,
    @location(1) uv: vec2<f32>,
    @location(2) col: vec4<f32>,
}

struct Vout {
    @builtin(position) clip: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) col: vec4<f32>,
}

@vertex
fn vs(i: Vin) -> Vout {
    var o: Vout;
    o.clip = vec4<f32>(i.pos, 0.0, 1.0);
    o.uv = i.uv;
    o.col = i.col;
    return o;
}

@fragment
fn fs(i: Vout) -> @location(0) vec4<f32> {
    let a = textureSample(font_tex, font_samp, i.uv).r * i.col.a;
    return vec4<f32>(i.col.rgb, a);
}
"#;

const SHADER: &str = r#"
struct U {
    vp: mat4x4<f32>,
    offset: vec4<f32>,
    fog: vec4<f32>,
    sun: vec4<f32>,
}
@group(0) @binding(0) var<uniform> u: U;

struct Vin {
    @location(0) pos: vec3<f32>,
    @location(1) nrm: vec3<f32>,
    @location(2) col: vec3<f32>,
    @location(3) uv: vec2<f32>,
    @location(4) tex: vec2<f32>,
}
@group(0) @binding(1) var atlas: texture_2d<f32>;
@group(0) @binding(2) var atlas_samp: sampler;
struct Vout {
    @builtin(position) clip: vec4<f32>,
    @location(0) lit: vec3<f32>,
    @location(1) uv: vec2<f32>,
    @location(2) tex: vec2<f32>,
    @location(3) fogf: f32,
}

@vertex
fn vs(i: Vin) -> Vout {
    let p = i.pos + u.offset.xyz;
    var o: Vout;
    o.clip = u.vp * vec4<f32>(p, 1.0);
    let n = normalize(i.nrm);
    let sun = normalize(u.sun.xyz);
    let ndl = max(dot(n, sun), 0.0);
    let wrap = ndl * 0.5 + 0.5;
    let amb = mix(vec3<f32>(0.42, 0.48, 0.60), vec3<f32>(0.90, 0.93, 0.98), n.y * 0.5 + 0.5);
    o.lit = i.col * (amb * 0.62 + vec3<f32>(1.0, 0.96, 0.86) * (ndl * 0.55 + wrap * 0.12));
    o.uv = i.uv;
    o.tex = i.tex;
    o.fogf = smoothstep(u.offset.w, u.fog.w, length(p));
    return o;
}

@fragment
fn fs(i: Vout) -> @location(0) vec4<f32> {
    var detail = 1.0;
    if (i.tex.x >= 0.0) {
        let tile = i.tex.x * 2.0 + i.tex.y;
        let col_i = tile % 16.0;
        let row_i = floor(tile / 16.0);
        let suv = (vec2<f32>(col_i, row_i) + clamp(i.uv, vec2<f32>(0.001), vec2<f32>(0.999))) * vec2<f32>(64.0 / 1024.0, 64.0 / 3072.0);
        // Atlas stores brightness/2, so 0.5 means unchanged.
        detail = textureSample(atlas, atlas_samp, suv).r * 2.0;
    }
    let lit = i.lit * detail;
    return vec4<f32>(mix(lit, u.fog.xyz, i.fogf), 1.0);
}
"#;
